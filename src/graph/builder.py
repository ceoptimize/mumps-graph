"""Graph builder for creating Neo4j database from VistA data."""

import logging
from typing import Any, Dict, Generator, List

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.graph.connection import Neo4jConnection
from src.graph.queries import GraphQueries
from src.models.nodes import (
    CrossReferenceNode,
    FieldNode,
    FileNode,
    PackageNode,
    SubfileNode,
)
from src.models.relationships import (
    ContainsFieldRel,
    ContainsFileRel,
    IndexedByRel,
    PointsToRel,
    SubfileOfRel,
    VariablePointerRel,
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

    # Phase 2: Enhanced relationship methods

    def create_cross_reference_nodes(
        self, xrefs: Dict[str, CrossReferenceNode]
    ) -> int:
        """
        Create cross-reference nodes in Neo4j.

        Args:
            xrefs: Dictionary of xref_id -> CrossReferenceNode

        Returns:
            Number of cross-reference nodes created
        """
        if not xrefs:
            logger.info("No cross-reference nodes to create")
            return 0

        xref_list = list(xrefs.values())
        count = 0

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(xref_list)} cross-reference nodes...",
                total=len(xref_list),
            )

            for batch in chunks(xref_list, self.batch_size):
                query = self.queries.batch_create_nodes("CrossReference")
                batch_data = [xref.dict_for_neo4j() for xref in batch]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create xref batch: {e}")

        logger.info(f"Created {count} CrossReference nodes")
        return count

    def create_indexed_by_relationships(
        self,
        xrefs: Dict[str, CrossReferenceNode],
        fields: List[FieldNode],
    ) -> int:
        """
        Create INDEXED_BY relationships between fields and cross-references.

        Args:
            xrefs: Dictionary of xref_id -> CrossReferenceNode
            fields: List of FieldNode objects

        Returns:
            Number of relationships created
        """
        if not xrefs or not fields:
            return 0

        relationships = []

        # Build relationships between fields and their xrefs
        for _xref_id, xref in xrefs.items():
            # Find matching field
            for field in fields:
                if (
                    field.file_number == xref.file_number
                    and field.number == xref.field_number
                ):
                    rel = IndexedByRel(
                        field_id=field.field_id,
                        xref_id=xref.xref_id,
                        xref_name=xref.name,
                        xref_type=xref.xref_type,
                        set_condition=xref.set_logic,
                        kill_condition=xref.kill_logic,
                    )
                    relationships.append(rel)
                    break

        if not relationships:
            return 0

        # Create in batches
        count = 0
        query = self.queries.batch_create_relationships("INDEXED_BY")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(relationships)} INDEXED_BY relationships...",
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
                    logger.error(f"Failed to create INDEXED_BY relationships: {e}")

        logger.info(f"Created {count} INDEXED_BY relationships")
        return count

    def create_subfile_relationships(
        self, subfiles: Dict[str, SubfileNode], files: Dict[str, FileNode]
    ) -> int:
        """
        Create SUBFILE_OF relationships between subfiles and parent files.

        Args:
            subfiles: Dictionary of subfile_number -> SubfileNode
            files: Dictionary of file_number -> FileNode

        Returns:
            Number of relationships created
        """
        if not subfiles:
            return 0

        relationships = []

        for _subfile_num, subfile in subfiles.items():
            # Find parent file
            parent_num = subfile.parent_file_number
            if parent_num in files:
                parent_file = files[parent_num]
                rel = SubfileOfRel(
                    subfile_id=subfile.file_id,
                    parent_file_id=parent_file.file_id,
                    parent_field=subfile.parent_field_number,
                    level=subfile.nesting_level,
                )
                relationships.append(rel)

        if not relationships:
            return 0

        # Create in batches
        count = 0
        query = self.queries.batch_create_relationships("SUBFILE_OF")

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
                logger.error(f"Failed to create SUBFILE_OF relationships: {e}")

        logger.info(f"Created {count} SUBFILE_OF relationships")
        return count

    def create_variable_pointer_relationships(
        self,
        v_pointers: Dict[str, List[Dict[str, str]]],
        fields: List[FieldNode],
        files: Dict[str, FileNode],
    ) -> int:
        """
        Create multiple POINTS_TO relationships for V-type fields.

        Args:
            v_pointers: Dict of field_key -> list of target info
            fields: List of FieldNode objects
            files: Dictionary of file_number -> FileNode

        Returns:
            Number of relationships created
        """
        if not v_pointers:
            return 0

        relationships = []

        for field_key, targets in v_pointers.items():
            # Parse field key
            file_num, field_num = field_key.split("_", 1)

            # Find matching field
            matching_field = None
            for field in fields:
                if field.file_number == file_num and field.number == field_num:
                    matching_field = field
                    break

            if not matching_field:
                continue

            # Create relationship for each target
            for target in targets:
                target_file_num = target.get("target_file", "")
                if target_file_num in files:
                    target_file = files[target_file_num]
                    rel = VariablePointerRel(
                        field_id=matching_field.field_id,
                        target_file_id=target_file.file_id,
                        target_file=target_file_num,
                        target_global=target.get("target_global", ""),
                        target_description=target.get("target_description"),
                        v_number=target.get("v_number"),
                    )
                    relationships.append(rel)

        if not relationships:
            return 0

        # Create in batches
        count = 0
        query = self.queries.batch_create_relationships("VARIABLE_POINTER")

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
                logger.error(f"Failed to create VARIABLE_POINTER relationships: {e}")

        logger.info(f"Created {count} VARIABLE_POINTER relationships")
        return count

    def enhance_pointer_relationships(self) -> int:
        """
        Enhance existing pointer relationships with additional metadata.

        Returns:
            Number of relationships enhanced
        """
        # This could be used to add laygo, required, and other pointer attributes
        # by querying additional DD entries and updating existing relationships
        logger.info("Pointer relationship enhancement - future enhancement")
        return 0
