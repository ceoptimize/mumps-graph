"""Graph builder for creating Neo4j database from VistA data."""

import logging
from typing import Any, Dict, Generator, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.graph.connection import Neo4jConnection
from src.graph.queries import GraphQueries
from src.models.nodes import FieldNode, FileNode, PackageNode
from src.models.relationships import (
    ContainsFieldRel,
    ContainsFileRel,
    PointsToRel,
)

logger = logging.getLogger(__name__)
console = Console()


def chunks(lst: List[Any], n: int) -> Generator:
    """Yield successive n-sized chunks from list."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]


class GraphBuilder:
    """Builds Neo4j graph from parsed VistA data."""

    def __init__(self, connection: Neo4jConnection, batch_size: int = 1000):
        """
        Initialize graph builder.

        Args:
            connection: Neo4j connection instance
            batch_size: Size of batches for bulk operations
        """
        self.connection = connection
        self.batch_size = batch_size
        self.queries = GraphQueries()
        self.statistics = {
            "packages_created": 0,
            "files_created": 0,
            "fields_created": 0,
            "relationships_created": 0,
        }

    def create_indexes(self) -> bool:
        """
        Create indexes for optimized queries.

        Returns:
            True if successful
        """
        index_queries = [
            # Package indexes
            "CREATE INDEX package_name IF NOT EXISTS FOR (p:Package) ON (p.name)",
            "CREATE INDEX package_id IF NOT EXISTS FOR (p:Package) ON (p.package_id)",
            # File indexes
            "CREATE INDEX file_number IF NOT EXISTS FOR (f:File) ON (f.number)",
            "CREATE INDEX file_id IF NOT EXISTS FOR (f:File) ON (f.file_id)",
            "CREATE INDEX file_name IF NOT EXISTS FOR (f:File) ON (f.name)",
            # Field indexes
            "CREATE INDEX field_id IF NOT EXISTS FOR (f:Field) ON (f.field_id)",
            "CREATE INDEX field_composite IF NOT EXISTS FOR (f:Field) ON (f.file_number, f.number)",
        ]

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("[cyan]Creating indexes...", total=len(index_queries))

            for query in index_queries:
                try:
                    self.connection.execute_query(query)
                    progress.advance(task)
                except Exception as e:
                    logger.error(f"Failed to create index: {e}")
                    return False

        logger.info("All indexes created successfully")
        return True

    def batch_create_packages(self, packages: List[PackageNode]) -> int:
        """
        Create package nodes in batches.

        Args:
            packages: List of PackageNode objects

        Returns:
            Number of packages created
        """
        count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(packages)} package nodes...",
                total=len(packages),
            )

            for batch in chunks(packages, self.batch_size):
                query = self.queries.batch_create_nodes("Package")
                batch_data = [pkg.dict_for_neo4j() for pkg in batch]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create package batch: {e}")

        self.statistics["packages_created"] = count
        logger.info(f"Created {count} package nodes")
        return count

    def batch_create_files(self, files: List[FileNode]) -> int:
        """
        Create file nodes in batches.

        Args:
            files: List of FileNode objects

        Returns:
            Number of files created
        """
        count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(files)} file nodes...",
                total=len(files),
            )

            for batch in chunks(files, self.batch_size):
                query = self.queries.batch_create_nodes("File")
                batch_data = [file.dict_for_neo4j() for file in batch]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create file batch: {e}")

        self.statistics["files_created"] = count
        logger.info(f"Created {count} file nodes")
        return count

    def batch_create_fields(self, fields: List[FieldNode]) -> int:
        """
        Create field nodes in batches.

        Args:
            fields: List of FieldNode objects

        Returns:
            Number of fields created
        """
        count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(fields)} field nodes...",
                total=len(fields),
            )

            for batch in chunks(fields, self.batch_size):
                query = self.queries.batch_create_nodes("Field")
                batch_data = [field.dict_for_neo4j() for field in batch]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create field batch: {e}")

        self.statistics["fields_created"] = count
        logger.info(f"Created {count} field nodes")
        return count

    def create_file_field_relationships(
        self, files: Dict[str, FileNode], fields: List[FieldNode]
    ) -> int:
        """
        Create CONTAINS_FIELD relationships between files and fields.

        Args:
            files: Dictionary of file number to FileNode
            fields: List of FieldNode objects

        Returns:
            Number of relationships created
        """
        relationships = []

        # Build relationships
        for field in fields:
            if field.file_number in files:
                file = files[field.file_number]
                rel = ContainsFieldRel(
                    file_id=file.file_id,
                    field_id=field.field_id,
                    field_number=field.number,
                )
                relationships.append(rel)

        # Create in batches
        count = 0
        query = self.queries.batch_create_relationships("CONTAINS_FIELD")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(relationships)} file-field relationships...",
                total=len(relationships),
            )

            for batch in chunks(relationships, self.batch_size):
                batch_data = [
                    {
                        "from_id": rel.from_id,
                        "to_id": rel.to_id,
                        "props": rel.to_cypher_props(),
                    }
                    for rel in batch
                ]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create relationship batch: {e}")

        self.statistics["relationships_created"] += count
        logger.info(f"Created {count} CONTAINS_FIELD relationships")
        return count

    def create_pointer_relationships(
        self, fields: List[FieldNode], files: Dict[str, FileNode]
    ) -> int:
        """
        Create POINTS_TO relationships for pointer fields.

        Args:
            fields: List of FieldNode objects
            files: Dictionary of file number to FileNode

        Returns:
            Number of relationships created
        """
        relationships = []

        # Build pointer relationships
        for field in fields:
            if field.is_pointer and field.target_file:
                if field.target_file in files:
                    target_file = files[field.target_file]
                    rel = PointsToRel(
                        field_id=field.field_id,
                        target_file_id=target_file.file_id,
                    )
                    relationships.append(rel)

        if not relationships:
            return 0

        # Create in batches
        count = 0
        query = self.queries.batch_create_relationships("POINTS_TO")

        for batch in chunks(relationships, self.batch_size):
            batch_data = [
                {
                    "from_id": rel.from_id,
                    "to_id": rel.to_id,
                    "props": rel.to_cypher_props(),
                }
                for rel in batch
            ]

            try:
                result = self.connection.execute_query(query, {"batch": batch_data})
                if result:
                    count += len(batch)
            except Exception as e:
                logger.error(f"Failed to create pointer relationships: {e}")

        self.statistics["relationships_created"] += count
        logger.info(f"Created {count} POINTS_TO relationships")
        return count

    def create_package_file_relationships(
        self,
        packages: List[PackageNode],
        files: Dict[str, FileNode],
        package_mapper: Any,
    ) -> int:
        """
        Create BELONGS_TO_PACKAGE relationships between files and packages.

        Args:
            packages: List of PackageNode objects
            files: Dictionary of file number to FileNode
            package_mapper: Package CSV parser with mapping functions

        Returns:
            Number of relationships created
        """
        relationships = []
        package_dict = {pkg.name: pkg for pkg in packages}

        # Map files to packages
        for file_num, file_node in files.items():
            package_name = package_mapper.find_package_by_file_number(file_num)
            if package_name and package_name in package_dict:
                package = package_dict[package_name]
                rel = ContainsFileRel(
                    package_id=package.package_id,
                    file_id=file_node.file_id,
                    confidence=0.8,  # Lower confidence for file range mapping
                )
                relationships.append(rel)

        if not relationships:
            return 0

        # Create in batches
        count = 0
        query = self.queries.batch_create_relationships("CONTAINS_FILE")

        for batch in chunks(relationships, self.batch_size):
            batch_data = [
                {
                    "from_id": rel.from_id,
                    "to_id": rel.to_id,
                    "props": rel.to_cypher_props(),
                }
                for rel in batch
            ]

            try:
                result = self.connection.execute_query(query, {"batch": batch_data})
                if result:
                    count += len(batch)
            except Exception as e:
                logger.error(f"Failed to create package-file relationships: {e}")

        self.statistics["relationships_created"] += count
        logger.info(f"Created {count} CONTAINS_FILE relationships")
        return count

    def get_statistics(self) -> Dict[str, Any]:
        """Get build statistics."""
        return self.statistics

    def validate_graph(self) -> Dict[str, Any]:
        """
        Validate the created graph.

        Returns:
            Dictionary with validation results
        """
        validation = {}

        # Check node counts
        node_counts = self.connection.execute_query(
            "MATCH (n) RETURN labels(n)[0] AS label, count(n) AS count"
        )
        if node_counts:
            validation["node_counts"] = {
                record["label"]: record["count"] for record in node_counts
            }

        # Check relationship counts
        rel_counts = self.connection.execute_query(
            "MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS count"
        )
        if rel_counts:
            validation["relationship_counts"] = {
                record["type"]: record["count"] for record in rel_counts
            }

        # Check orphan nodes
        orphan_files = self.connection.execute_query(
            "MATCH (f:File) WHERE NOT (()-[:CONTAINS_FIELD]->(f)) "
            "RETURN count(f) AS count"
        )
        if orphan_files:
            validation["orphan_files"] = orphan_files[0]["count"]

        # Check pointer integrity
        dangling_pointers = self.connection.execute_query(
            "MATCH (f:Field) WHERE f.is_pointer = true AND "
            "NOT (f)-[:POINTS_TO]->() RETURN count(f) AS count"
        )
        if dangling_pointers:
            validation["dangling_pointers"] = dangling_pointers[0]["count"]

        return validation
