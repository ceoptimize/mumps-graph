"""Tests for graph builder."""

from unittest.mock import MagicMock

from src.graph.builder import GraphBuilder, chunks
from src.models.nodes import FieldNode, FileNode, PackageNode


class TestGraphBuilder:
    """Test graph builder functionality."""

    def test_chunks(self):
        """Test chunking utility function."""
        data = list(range(10))

        # Chunks of 3
        result = list(chunks(data, 3))
        assert len(result) == 4
        assert result[0] == [0, 1, 2]
        assert result[1] == [3, 4, 5]
        assert result[2] == [6, 7, 8]
        assert result[3] == [9]

        # Chunks of 5
        result = list(chunks(data, 5))
        assert len(result) == 2
        assert result[0] == [0, 1, 2, 3, 4]
        assert result[1] == [5, 6, 7, 8, 9]

        # Chunks larger than list
        result = list(chunks(data, 20))
        assert len(result) == 1
        assert result[0] == data

    def test_create_indexes(self, mock_neo4j_connection):
        """Test index creation."""
        builder = GraphBuilder(mock_neo4j_connection)

        # Mock execute_query to track calls
        mock_neo4j_connection.execute_query.return_value = [{"created": 1}]

        result = builder.create_indexes()

        assert result is True
        # Should create multiple indexes
        assert mock_neo4j_connection.execute_query.call_count > 0

    def test_batch_create_packages(self, mock_neo4j_connection):
        """Test batch creation of package nodes."""
        builder = GraphBuilder(mock_neo4j_connection, batch_size=2)

        packages = [
            PackageNode(name="Package1", directory="Dir1", prefixes=["P1"]),
            PackageNode(name="Package2", directory="Dir2", prefixes=["P2"]),
            PackageNode(name="Package3", directory="Dir3", prefixes=["P3"]),
        ]

        mock_neo4j_connection.execute_query.return_value = [{"created": 2}]

        count = builder.batch_create_packages(packages)

        assert count == 3
        assert builder.statistics["packages_created"] == 3
        # Should be called twice (batch size 2, so 2 batches for 3 items)
        assert mock_neo4j_connection.execute_query.call_count == 2

    def test_batch_create_files(self, mock_neo4j_connection):
        """Test batch creation of file nodes."""
        builder = GraphBuilder(mock_neo4j_connection, batch_size=2)

        files = [
            FileNode(file_number="2", name="PATIENT", global_root="^DPT"),
            FileNode(file_number="200", name="NEW PERSON", global_root="^VA(200,"),
            FileNode(file_number="120", name="GMRA", global_root="^GMRA"),
        ]

        mock_neo4j_connection.execute_query.return_value = [{"created": 2}]

        count = builder.batch_create_files(files)

        assert count == 3
        assert builder.statistics["files_created"] == 3

    def test_batch_create_fields(self, mock_neo4j_connection):
        """Test batch creation of field nodes."""
        builder = GraphBuilder(mock_neo4j_connection, batch_size=5)

        fields = [
            FieldNode(number=".01", name="NAME", file_number="2", data_type="F"),
            FieldNode(number=".02", name="SEX", file_number="2", data_type="S"),
            FieldNode(number=".03", name="DOB", file_number="2", data_type="D"),
        ]

        mock_neo4j_connection.execute_query.return_value = [{"created": 3}]

        count = builder.batch_create_fields(fields)

        assert count == 3
        assert builder.statistics["fields_created"] == 3

    def test_create_file_field_relationships(self, mock_neo4j_connection):
        """Test creation of CONTAINS_FIELD relationships."""
        builder = GraphBuilder(mock_neo4j_connection, batch_size=2)

        files = {
            "2": FileNode(file_id="file-1", file_number="2", name="PATIENT"),
            "200": FileNode(file_id="file-2", file_number="200", name="NEW PERSON"),
        }

        fields = [
            FieldNode(field_id="field-1", number=".01", name="NAME", file_number="2", data_type="F"),
            FieldNode(field_id="field-2", number=".02", name="SEX", file_number="2", data_type="S"),
            FieldNode(field_id="field-3", number=".01", name="NAME", file_number="200", data_type="F"),
        ]

        mock_neo4j_connection.execute_query.return_value = [{"created": 2}]

        count = builder.create_file_field_relationships(files, fields)

        assert count == 3
        assert builder.statistics["relationships_created"] == 3

    def test_create_pointer_relationships(self, mock_neo4j_connection):
        """Test creation of POINTS_TO relationships."""
        builder = GraphBuilder(mock_neo4j_connection)

        files = {
            "2": FileNode(file_id="file-1", file_number="2", name="PATIENT"),
            "200": FileNode(file_id="file-2", file_number="200", name="NEW PERSON"),
        }

        fields = [
            FieldNode(
                field_id="field-1",
                number="1901",
                name="PROVIDER",
                file_number="2",
                data_type="P",
                is_pointer=True,
                target_file="200"
            ),
            FieldNode(
                field_id="field-2",
                number=".01",
                name="NAME",
                file_number="2",
                data_type="F",
                is_pointer=False
            ),
        ]

        mock_neo4j_connection.execute_query.return_value = [{"created": 1}]

        count = builder.create_pointer_relationships(fields, files)

        assert count == 1
        assert builder.statistics["relationships_created"] == 1
        # Only one pointer field should create a relationship
        assert mock_neo4j_connection.execute_query.call_count == 1

    def test_create_package_file_relationships(self, mock_neo4j_connection):
        """Test creation of CONTAINS_FILE relationships."""
        builder = GraphBuilder(mock_neo4j_connection)

        packages = [
            PackageNode(
                package_id="pkg-1",
                name="VA FileMan",
                directory="VA FileMan",
                files_low="0.2",
                files_high="1.99999"
            ),
            PackageNode(
                package_id="pkg-2",
                name="PATIENT",
                directory="Patient",
                files_low="2",
                files_high="2.99"
            ),
        ]

        files = {
            "1": FileNode(file_id="file-1", file_number="1", name="FILE"),
            "2": FileNode(file_id="file-2", file_number="2", name="PATIENT"),
        }

        # Mock package mapper
        mock_mapper = MagicMock()
        mock_mapper.find_package_by_file_number.side_effect = lambda x: {
            "1": "VA FileMan",
            "2": "PATIENT"
        }.get(x)

        mock_neo4j_connection.execute_query.return_value = [{"created": 2}]

        count = builder.create_package_file_relationships(packages, files, mock_mapper)

        assert count == 2
        assert builder.statistics["relationships_created"] == 2

    def test_validate_graph(self, mock_neo4j_connection):
        """Test graph validation."""
        builder = GraphBuilder(mock_neo4j_connection)

        # Mock various validation queries
        mock_neo4j_connection.execute_query.side_effect = [
            [{"label": "Package", "count": 10}, {"label": "File", "count": 100}],  # Node counts
            [{"type": "CONTAINS_FIELD", "count": 1000}],  # Relationship counts
            [{"count": 5}],  # Orphan files
            [{"count": 3}],  # Dangling pointers
        ]

        validation = builder.validate_graph()

        assert validation["node_counts"]["Package"] == 10
        assert validation["node_counts"]["File"] == 100
        assert validation["relationship_counts"]["CONTAINS_FIELD"] == 1000
        assert validation["orphan_files"] == 5
        assert validation["dangling_pointers"] == 3

    def test_get_statistics(self):
        """Test getting build statistics."""
        builder = GraphBuilder(MagicMock())

        # Set some statistics
        builder.statistics = {
            "packages_created": 10,
            "files_created": 100,
            "fields_created": 1000,
            "relationships_created": 1500,
        }

        stats = builder.get_statistics()

        assert stats["packages_created"] == 10
        assert stats["files_created"] == 100
        assert stats["fields_created"] == 1000
        assert stats["relationships_created"] == 1500

    def test_error_handling_in_batch_operations(self, mock_neo4j_connection):
        """Test error handling during batch operations."""
        builder = GraphBuilder(mock_neo4j_connection, batch_size=2)

        packages = [
            PackageNode(name="Package1", directory="Dir1"),
            PackageNode(name="Package2", directory="Dir2"),
        ]

        # Simulate an error
        mock_neo4j_connection.execute_query.side_effect = Exception("Database error")

        count = builder.batch_create_packages(packages)

        # Should handle error gracefully and return 0
        assert count == 0
        assert builder.statistics["packages_created"] == 0
