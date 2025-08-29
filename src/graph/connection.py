"""Neo4j connection management."""

import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional

from neo4j import GraphDatabase, Result, Session
from neo4j.exceptions import Neo4jError, ServiceUnavailable

from src.config.settings import get_neo4j_config

logger = logging.getLogger(__name__)


class Neo4jConnection:
    """Manages Neo4j database connection with retry logic and connection pooling."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize Neo4j connection.

        Args:
            config: Optional configuration dict, defaults to settings
        """
        self.config = config or get_neo4j_config()
        self.driver = None
        self.max_retries = 3
        self.retry_delay = 2.0

    def connect(self) -> bool:
        """
        Establish connection to Neo4j.

        Returns:
            True if connection successful
        """
        try:
            self.driver = GraphDatabase.driver(
                self.config["uri"],
                auth=self.config["auth"],
                max_connection_lifetime=self.config.get("max_connection_lifetime", 3600),
                max_connection_pool_size=self.config.get("max_connection_pool_size", 50),
                connection_timeout=self.config.get("connection_timeout", 30.0),
            )

            # Test connection
            with self.driver.session() as session:
                result = session.run("RETURN 1 AS test")
                result.single()

            logger.info(f"Successfully connected to Neo4j at {self.config['uri']}")
            return True

        except ServiceUnavailable as e:
            logger.error(f"Neo4j service unavailable: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def disconnect(self):
        """Close the Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.driver = None
            logger.info("Disconnected from Neo4j")

    @contextmanager
    def session(self, database: Optional[str] = None) -> Generator[Session, None, None]:
        """
        Context manager for Neo4j sessions.

        Args:
            database: Optional database name

        Yields:
            Neo4j session
        """
        if not self.driver:
            raise RuntimeError("Not connected to Neo4j. Call connect() first.")

        session = self.driver.session(database=database or self.config.get("database", "neo4j"))
        try:
            yield session
        finally:
            session.close()

    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        database: Optional[str] = None,
    ) -> Optional[Result]:
        """
        Execute a Cypher query with retry logic.

        Args:
            query: Cypher query string
            parameters: Query parameters
            database: Optional database name

        Returns:
            Query result or None if failed
        """
        for attempt in range(self.max_retries):
            try:
                with self.session(database) as session:
                    result = session.run(query, parameters or {})
                    # Consume the result to ensure query completion
                    data = list(result)
                    return data

            except ServiceUnavailable as e:
                if attempt < self.max_retries - 1:
                    logger.warning(
                        f"Service unavailable, retrying in {self.retry_delay}s... "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(self.retry_delay)
                    # Try to reconnect
                    self.connect()
                else:
                    logger.error(f"Max retries reached. Query failed: {e}")
                    raise

            except Neo4jError as e:
                logger.error(f"Neo4j query error: {e}")
                raise

            except Exception as e:
                logger.error(f"Unexpected error executing query: {e}")
                raise

        return None

    def execute_transaction(
        self,
        transaction_func,
        database: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Execute a transaction function.

        Args:
            transaction_func: Function to execute in transaction
            database: Optional database name
            **kwargs: Additional arguments for transaction function

        Returns:
            Transaction result
        """
        with self.session(database) as session:
            return session.execute_write(transaction_func, **kwargs)

    def test_connection(self) -> bool:
        """
        Test if the connection is active.

        Returns:
            True if connection is active
        """
        try:
            result = self.execute_query("RETURN 1 AS test")
            return result is not None
        except Exception:
            return False

    def clear_database(self) -> bool:
        """
        Clear all nodes and relationships from the database.

        WARNING: This will delete all data!

        Returns:
            True if successful
        """
        try:
            # Delete all relationships first
            self.execute_query("MATCH ()-[r]-() DELETE r")
            # Then delete all nodes
            self.execute_query("MATCH (n) DELETE n")
            logger.info("Database cleared successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

    def get_database_info(self) -> Optional[Dict[str, Any]]:
        """
        Get database statistics and information.

        Returns:
            Dictionary with database info or None
        """
        try:
            # Get node counts by label
            node_query = """
            MATCH (n)
            RETURN labels(n) AS labels, count(n) AS count
            ORDER BY count DESC
            """
            node_results = self.execute_query(node_query)

            # Get relationship counts by type
            rel_query = """
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(r) AS count
            ORDER BY count DESC
            """
            rel_results = self.execute_query(rel_query)

            # Process results
            node_counts = {}
            if node_results:
                for record in node_results:
                    labels = record.get("labels", [])
                    if labels:
                        label = labels[0]  # Use first label
                        node_counts[label] = record.get("count", 0)

            rel_counts = {}
            if rel_results:
                for record in rel_results:
                    rel_type = record.get("type")
                    if rel_type:
                        rel_counts[rel_type] = record.get("count", 0)

            return {
                "nodes": node_counts,
                "relationships": rel_counts,
                "total_nodes": sum(node_counts.values()),
                "total_relationships": sum(rel_counts.values()),
            }

        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            return None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
