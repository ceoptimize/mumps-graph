"""Cypher query templates for Neo4j operations."""

from typing import Dict, Optional


class GraphQueries:
    """Collection of Cypher query templates."""

    @staticmethod
    def batch_create_nodes(label: str) -> str:
        """
        Generate query for batch node creation.

        Args:
            label: Node label (e.g., Package, File, Field)

        Returns:
            Cypher query string
        """
        return f"""
        UNWIND $batch AS item
        CREATE (n:{label})
        SET n = item
        RETURN count(n) AS created
        """

    @staticmethod
    def batch_create_relationships(rel_type: str) -> str:
        """
        Generate query for batch relationship creation.

        Args:
            rel_type: Relationship type (e.g., CONTAINS_FIELD, POINTS_TO)

        Returns:
            Cypher query string
        """
        # Map relationship types to node labels
        rel_mapping = {
            "CONTAINS_FIELD": ("File", "file_id", "Field", "field_id"),
            "CONTAINS_FILE": ("Package", "package_id", "File", "file_id"),
            "POINTS_TO": ("Field", "field_id", "File", "file_id"),
            "COMPUTED_FROM": ("Field", "field_id", "Field", "field_id"),
            "SUBFILE_OF": ("File", "file_id", "File", "file_id"),
            "INDEXED_BY": ("Field", "field_id", "CrossReference", "xref_id"),
            "VARIABLE_POINTER": ("Field", "field_id", "File", "file_id"),
        }

        if rel_type not in rel_mapping:
            raise ValueError(f"Unknown relationship type: {rel_type}")

        from_label, from_prop, to_label, to_prop = rel_mapping[rel_type]

        return f"""
        UNWIND $batch AS item
        MATCH (from:{from_label} {{{from_prop}: item.from_id}})
        MATCH (to:{to_label} {{{to_prop}: item.to_id}})
        CREATE (from)-[r:{rel_type}]->(to)
        SET r = item.props
        RETURN count(r) AS created
        """

    @staticmethod
    def find_node_by_id(label: str, id_field: str) -> str:
        """
        Generate query to find a node by ID.

        Args:
            label: Node label
            id_field: ID field name

        Returns:
            Cypher query string
        """
        return f"""
        MATCH (n:{label} {{{id_field}: $id}})
        RETURN n
        """

    @staticmethod
    def find_nodes_by_property(label: str, property_name: str) -> str:
        """
        Generate query to find nodes by property value.

        Args:
            label: Node label
            property_name: Property name to search

        Returns:
            Cypher query string
        """
        return f"""
        MATCH (n:{label} {{{property_name}: $value}})
        RETURN n
        ORDER BY n.{property_name}
        """

    @staticmethod
    def get_node_count(label: Optional[str] = None) -> str:
        """
        Generate query to count nodes.

        Args:
            label: Optional node label to filter

        Returns:
            Cypher query string
        """
        if label:
            return f"MATCH (n:{label}) RETURN count(n) AS count"
        return "MATCH (n) RETURN count(n) AS count"

    @staticmethod
    def get_relationship_count(rel_type: Optional[str] = None) -> str:
        """
        Generate query to count relationships.

        Args:
            rel_type: Optional relationship type to filter

        Returns:
            Cypher query string
        """
        if rel_type:
            return f"MATCH ()-[r:{rel_type}]->() RETURN count(r) AS count"
        return "MATCH ()-[r]->() RETURN count(r) AS count"

    @staticmethod
    def get_file_with_fields(file_number: str) -> str:
        """
        Generate query to get a file with all its fields.

        Args:
            file_number: File number to retrieve

        Returns:
            Cypher query string
        """
        return """
        MATCH (f:File {number: $file_number})
        OPTIONAL MATCH (f)-[:CONTAINS_FIELD]->(field:Field)
        RETURN f AS file, collect(field) AS fields
        """

    @staticmethod
    def get_package_with_files(package_name: str) -> str:
        """
        Generate query to get a package with all its files.

        Args:
            package_name: Package name to retrieve

        Returns:
            Cypher query string
        """
        return """
        MATCH (p:Package {name: $package_name})
        OPTIONAL MATCH (p)-[:CONTAINS_FILE]->(file:File)
        RETURN p AS package, collect(file) AS files
        """

    @staticmethod
    def get_pointer_chain(field_id: str, max_depth: int = 5) -> str:
        """
        Generate query to follow pointer relationships.

        Args:
            field_id: Starting field ID
            max_depth: Maximum depth to traverse

        Returns:
            Cypher query string
        """
        return f"""
        MATCH path = (f:Field {{field_id: $field_id}})-[:POINTS_TO*1..{max_depth}]->(target)
        RETURN path
        """

    @staticmethod
    def find_orphan_files() -> str:
        """Generate query to find files not belonging to any package."""
        return """
        MATCH (f:File)
        WHERE NOT (f)<-[:CONTAINS_FILE]-(:Package)
        RETURN f.number AS file_number, f.name AS file_name
        ORDER BY f.number
        """

    @staticmethod
    def find_dangling_pointers() -> str:
        """Generate query to find pointer fields without targets."""
        return """
        MATCH (f:Field)
        WHERE f.is_pointer = true AND NOT (f)-[:POINTS_TO]->()
        RETURN f.file_number AS file_number,
               f.number AS field_number,
               f.name AS field_name,
               f.target_file AS target_file
        ORDER BY f.file_number, f.number
        """

    @staticmethod
    def get_graph_statistics() -> str:
        """Generate query to get overall graph statistics."""
        return """
        MATCH (n)
        WITH labels(n)[0] AS label, count(n) AS count
        WITH collect({label: label, count: count}) AS node_stats
        MATCH ()-[r]->()
        WITH node_stats, type(r) AS rel_type, count(r) AS count
        WITH node_stats, collect({type: rel_type, count: count}) AS rel_stats
        RETURN node_stats, rel_stats,
               reduce(s = 0, x IN node_stats | s + x.count) AS total_nodes,
               reduce(s = 0, x IN rel_stats | s + x.count) AS total_relationships
        """

    @staticmethod
    def clear_all_data() -> str:
        """Generate query to clear all nodes and relationships."""
        return """
        MATCH (n)
        DETACH DELETE n
        """

    @staticmethod
    def create_constraints() -> Dict[str, str]:
        """
        Generate constraint creation queries.

        Returns:
            Dictionary of constraint name to query
        """
        return {
            "unique_package_id": "CREATE CONSTRAINT unique_package_id IF NOT EXISTS "
            "FOR (p:Package) REQUIRE p.package_id IS UNIQUE",
            "unique_file_id": "CREATE CONSTRAINT unique_file_id IF NOT EXISTS "
            "FOR (f:File) REQUIRE f.file_id IS UNIQUE",
            "unique_field_id": "CREATE CONSTRAINT unique_field_id IF NOT EXISTS "
            "FOR (f:Field) REQUIRE f.field_id IS UNIQUE",
        }

    @staticmethod
    def validate_schema() -> str:
        """Generate query to validate the schema structure."""
        return """
        CALL db.schema.visualization() YIELD nodes, relationships
        RETURN nodes, relationships
        """

    @staticmethod
    def get_file_dependencies(file_number: str) -> str:
        """
        Generate query to get all files that a given file depends on.

        Args:
            file_number: File number to analyze

        Returns:
            Cypher query string
        """
        return """
        MATCH (f:File {number: $file_number})-[:CONTAINS_FIELD]->(field:Field)
        WHERE field.is_pointer = true
        MATCH (field)-[:POINTS_TO]->(target:File)
        RETURN DISTINCT target.number AS file_number,
                        target.name AS file_name,
                        count(field) AS reference_count
        ORDER BY reference_count DESC
        """

    @staticmethod
    def get_file_dependents(file_number: str) -> str:
        """
        Generate query to get all files that depend on a given file.

        Args:
            file_number: File number to analyze

        Returns:
            Cypher query string
        """
        return """
        MATCH (target:File {number: $file_number})
        MATCH (field:Field)-[:POINTS_TO]->(target)
        MATCH (source:File)-[:CONTAINS_FIELD]->(field)
        RETURN DISTINCT source.number AS file_number,
                        source.name AS file_name,
                        count(field) AS reference_count
        ORDER BY reference_count DESC
        """

    # Phase 2: Cross-reference and subfile specific queries

    @staticmethod
    def find_subfiles(parent_number: Optional[str] = None) -> str:
        """
        Generate query to find all subfiles or subfiles of a specific parent.

        Args:
            parent_number: Optional parent file number

        Returns:
            Cypher query string
        """
        if parent_number:
            return """
            MATCH (parent:File {number: $parent_number})
            MATCH (child:File)-[:SUBFILE_OF]->(parent)
            RETURN parent.name AS parent_name,
                   child.number AS subfile_number,
                   child.name AS subfile_name
            ORDER BY child.number
            """
        return """
        MATCH (child:File)-[r:SUBFILE_OF]->(parent:File)
        RETURN parent.number AS parent_number,
               parent.name AS parent_name,
               child.number AS subfile_number,
               child.name AS subfile_name,
               r.level AS nesting_level
        ORDER BY parent.number, child.number
        """

    @staticmethod
    def get_field_cross_references(file_number: str, field_number: str) -> str:
        """
        Generate query to get all cross-references for a specific field.

        Args:
            file_number: File number
            field_number: Field number

        Returns:
            Cypher query string
        """
        return """
        MATCH (f:Field {file_number: $file_number, number: $field_number})
        OPTIONAL MATCH (f)-[r:INDEXED_BY]->(x:CrossReference)
        RETURN f AS field,
               collect({
                   name: x.name,
                   type: x.xref_type,
                   set_logic: r.set_condition,
                   kill_logic: r.kill_condition
               }) AS cross_references
        """

    @staticmethod
    def get_variable_pointer_targets(field_id: str) -> str:
        """
        Generate query to get all targets of a variable pointer field.

        Args:
            field_id: Field ID

        Returns:
            Cypher query string
        """
        return """
        MATCH (f:Field {field_id: $field_id})
        WHERE f.data_type = 'V'
        MATCH (f)-[r:VARIABLE_POINTER]->(target:File)
        RETURN f.name AS field_name,
               collect({
                   file: target.number,
                   name: target.name,
                   global: r.target_global,
                   description: r.target_description
               }) AS targets
        """

    @staticmethod
    def count_cross_references_by_file() -> str:
        """Generate query to count cross-references per file."""
        return """
        MATCH (x:CrossReference)
        RETURN x.file_number AS file_number,
               count(x) AS xref_count
        ORDER BY xref_count DESC
        """

    @staticmethod
    def find_most_indexed_fields() -> str:
        """Generate query to find fields with the most cross-references."""
        return """
        MATCH (f:Field)-[:INDEXED_BY]->(x:CrossReference)
        WITH f, count(x) AS xref_count
        RETURN f.file_number AS file_number,
               f.number AS field_number,
               f.name AS field_name,
               xref_count
        ORDER BY xref_count DESC
        LIMIT 20
        """

    @staticmethod
    def get_subfile_hierarchy(root_file: Optional[str] = None) -> str:
        """
        Generate query to get the complete subfile hierarchy.

        Args:
            root_file: Optional root file to start from

        Returns:
            Cypher query string
        """
        if root_file:
            return """
            MATCH path = (root:File {number: $root_file})<-[:SUBFILE_OF*]-(sub:File)
            RETURN path
            ORDER BY length(path)
            """
        return """
        MATCH (f:File)
        WHERE NOT (f)-[:SUBFILE_OF]->()
        OPTIONAL MATCH path = (f)<-[:SUBFILE_OF*]-(sub:File)
        RETURN f.number AS root_file,
               f.name AS root_name,
               count(sub) AS subfile_count
        ORDER BY subfile_count DESC
        """

    @staticmethod
    def validate_phase2_relationships() -> str:
        """Generate query to validate Phase 2 relationships."""
        return """
        WITH [
            {type: 'INDEXED_BY', expected_min: 100},
            {type: 'SUBFILE_OF', expected_min: 10},
            {type: 'VARIABLE_POINTER', expected_min: 1}
        ] AS checks
        UNWIND checks AS check
        OPTIONAL MATCH ()-[r]->()
        WHERE type(r) = check.type
        WITH check, count(r) AS actual_count
        RETURN check.type AS relationship_type,
               check.expected_min AS expected_minimum,
               actual_count,
               CASE
                   WHEN actual_count >= check.expected_min THEN 'PASS'
                   ELSE 'FAIL'
               END AS status
        """
