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
    LabelNode,
    PackageNode,
    RoutineNode,
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

        # Build relationships directly from xrefs
        # We'll match on file_number and field_number in the query
        for _xref_id, xref in xrefs.items():
            # Create relationship with placeholder field_id
            # The actual matching will happen in the Cypher query
            rel = IndexedByRel(
                field_id="placeholder",  # Not used in new query
                xref_id=xref.xref_id,
                xref_name=xref.name,
                xref_type=xref.xref_type,
                set_condition=xref.set_logic,
                kill_condition=xref.kill_logic,
            )
            relationships.append(rel)

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
                # Special batch data format for INDEXED_BY relationships
                batch_data = []
                for rel in batch:
                    # Find the corresponding xref to get file_number and field_number
                    xref = next((x for x in xrefs.values() if x.xref_id == rel.to_id), None)
                    if xref:
                        batch_data.append({
                            "file_number": xref.file_number,
                            "field_number": xref.field_number,
                            "to_id": rel.to_id,
                            "props": rel.to_cypher_props(),
                        })

                if not batch_data:
                    continue

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    # Extract the actual count from the query result
                    if result and len(result) > 0 and "created" in result[0]:
                        created_count = result[0]["created"]
                        count += created_count
                        logger.debug(f"Created {created_count} INDEXED_BY relationships in this batch")
                    else:
                        logger.warning("No INDEXED_BY relationships created in this batch")
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

        for subfile_num, subfile in subfiles.items():
            # Store the subfile number and parent number for matching
            # We'll match on file numbers in the Cypher query
            parent_num = subfile.parent_file_number
            if parent_num:  # Check parent exists
                rel = SubfileOfRel(
                    subfile_id=subfile_num,  # Use file number as temporary ID
                    parent_file_id=parent_num,  # Use parent file number as temporary ID
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
            # Special batch data format for SUBFILE_OF relationships
            batch_data = [
                {
                    "from_number": rel.from_id,  # This is the subfile number
                    "to_number": rel.to_id,  # This is the parent file number
                    "props": rel.to_cypher_props(),
                }
                for rel in batch
            ]

            try:
                result = self.connection.execute_query(query, {"batch": batch_data})
                # Extract the actual count from the query result
                if result and len(result) > 0 and "created" in result[0]:
                    created_count = result[0]["created"]
                    count += created_count
                    logger.debug(f"Created {created_count} SUBFILE_OF relationships in this batch")
                else:
                    logger.warning("No SUBFILE_OF relationships created in this batch")
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
                # Extract the actual count from the query result
                if result and len(result) > 0 and "created" in result[0]:
                    created_count = result[0]["created"]
                    count += created_count
                    logger.debug(f"Created {created_count} VARIABLE_POINTER relationships in this batch")
                else:
                    logger.warning("No VARIABLE_POINTER relationships created in this batch")
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

    # Phase 3: Routine and Label Node Methods

    def create_routine_nodes(self, routines: List[RoutineNode]) -> int:
        """
        Create routine nodes in batches.

        Args:
            routines: List of RoutineNode objects

        Returns:
            Number of routines created
        """
        if not routines:
            return 0

        count = 0
        # Use MERGE to prevent duplicates based on routine name
        query = """
        UNWIND $batch as routine
        MERGE (r:Routine {name: routine.name})
        ON CREATE SET
            r.routine_id = routine.routine_id,
            r.package_name = routine.package_name,
            r.prefix = routine.prefix,
            r.path = routine.path,
            r.lines_of_code = routine.lines_of_code,
            r.last_modified = routine.last_modified,
            r.version = routine.version,
            r.patches = routine.patches,
            r.description = routine.description
        ON MATCH SET
            r.lines_of_code = routine.lines_of_code,
            r.last_modified = routine.last_modified,
            r.path = routine.path
        RETURN count(r) as count
        """

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(routines)} routine nodes...",
                total=len(routines),
            )

            for batch in chunks(routines, self.batch_size):
                batch_data = [routine.dict_for_neo4j() for routine in batch]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create routine batch: {e}")

        logger.info(f"Created {count} routine nodes")
        return count

    def create_label_nodes(self, labels: List[LabelNode]) -> int:
        """
        Create label nodes in batches.

        Args:
            labels: List of LabelNode objects

        Returns:
            Number of labels created
        """
        if not labels:
            return 0

        count = 0
        # Use MERGE to prevent duplicates based on routine_name + label name
        query = """
        UNWIND $batch as label
        MERGE (l:Label {routine_name: label.routine_name, name: label.name})
        ON CREATE SET
            l.label_id = label.label_id,
            l.line_number = label.line_number,
            l.is_entry_point = label.is_entry_point,
            l.is_function = label.is_function,
            l.parameters = label.parameters,
            l.comment = label.comment
        ON MATCH SET
            l.line_number = label.line_number,
            l.comment = label.comment
        RETURN count(l) as count
        """

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(labels)} label nodes...",
                total=len(labels),
            )

            for batch in chunks(labels, self.batch_size):
                batch_data = [label.dict_for_neo4j() for label in batch]

                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch_data}
                    )
                    if result:
                        count += len(batch)
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create label batch: {e}")

        logger.info(f"Created {count} label nodes")
        return count

    def create_contains_label_relationships(
        self, routines: List[RoutineNode], labels: List[LabelNode]
    ) -> int:
        """
        Create CONTAINS_LABEL relationships between routines and their labels.

        Args:
            routines: List of RoutineNode objects
            labels: List of LabelNode objects

        Returns:
            Number of relationships created
        """
        if not routines or not labels:
            return 0

        # Group labels by routine
        labels_by_routine = {}
        for label in labels:
            if label.routine_name not in labels_by_routine:
                labels_by_routine[label.routine_name] = []
            labels_by_routine[label.routine_name].append(label)

        # Build relationships data
        relationships = []
        for routine in routines:
            if routine.name in labels_by_routine:
                for label in labels_by_routine[routine.name]:
                    relationships.append({
                        "routine_name": routine.name,
                        "label_name": label.name,
                        "line_number": label.line_number
                    })

        if not relationships:
            return 0

        count = 0
        query = """
        UNWIND $batch as rel
        MATCH (r:Routine {name: rel.routine_name})
        MATCH (l:Label {routine_name: rel.routine_name, name: rel.label_name})
        MERGE (r)-[:CONTAINS_LABEL {line_number: rel.line_number}]->(l)
        RETURN count(*) as count
        """

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Creating {len(relationships)} routine-label relationships...",
                total=len(relationships),
            )

            for batch in chunks(relationships, self.batch_size):
                try:
                    result = self.connection.execute_query(
                        query, {"batch": batch}
                    )
                    if result and len(result) > 0:
                        batch_count = result[0].get("count", 0)
                        count += batch_count
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create CONTAINS_LABEL relationships: {e}")

        logger.info(f"Created {count} CONTAINS_LABEL relationships")
        return count

    def create_package_routine_relationships(self, routines: List[RoutineNode]) -> int:
        """
        Create OWNS_ROUTINE relationships between packages and routines.

        Args:
            routines: List of RoutineNode objects

        Returns:
            Number of relationships created
        """
        if not routines:
            return 0

        # Prepare routine data with prefixes
        routine_data = []
        for r in routines:
            if r.prefix:  # Only create relationships if we have a prefix
                routine_data.append({
                    "name": r.name,
                    "prefix": r.prefix
                })

        if not routine_data:
            return 0

        count = 0
        # Match packages by prefix and create relationships
        query = """
        UNWIND $routines as routine
        MATCH (p:Package)
        WHERE routine.prefix IN p.prefixes
        MATCH (r:Routine {name: routine.name})
        MERGE (p)-[:OWNS_ROUTINE]->(r)
        RETURN count(*) as count
        """

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Creating package-routine relationships...",
                total=len(routine_data),
            )

            for batch in chunks(routine_data, self.batch_size):
                try:
                    result = self.connection.execute_query(
                        query, {"routines": batch}
                    )
                    if result and len(result) > 0:
                        batch_count = result[0].get("count", 0)
                        count += batch_count
                    progress.advance(task, len(batch))
                except Exception as e:
                    logger.error(f"Failed to create OWNS_ROUTINE relationships: {e}")

        logger.info(f"Created {count} OWNS_ROUTINE relationships")
        return count
