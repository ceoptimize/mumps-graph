"""Unit tests for Phase 3 graph builder extensions."""

from unittest.mock import MagicMock

import pytest

from src.graph.builder import GraphBuilder
from src.models.nodes import LabelNode, RoutineNode


class TestPhase3Builder:
    """Test suite for Phase 3 graph builder methods."""

    @pytest.fixture
    def mock_connection(self):
        """Create mock Neo4j connection."""
        connection = MagicMock()
        connection.execute_query.return_value = [{"count": 1}]
        return connection

    @pytest.fixture
    def builder(self, mock_connection):
        """Create builder with mock connection."""
        return GraphBuilder(mock_connection, batch_size=2)

    def test_create_routine_nodes(self, builder, mock_connection):
        """Test creation of routine nodes."""
        routines = [
            RoutineNode(
                name="DG10",
                package_name="Registration",
                prefix="DG",
                path="/path/to/DG10.m",
                lines_of_code=100
            ),
            RoutineNode(
                name="DG11",
                package_name="Registration",
                prefix="DG",
                path="/path/to/DG11.m",
                lines_of_code=150
            ),
        ]

        count = builder.create_routine_nodes(routines)

        # Should create nodes in batches
        assert mock_connection.execute_query.called
        assert count == 2

        # Check query structure
        call_args = mock_connection.execute_query.call_args_list[0]
        query = call_args[0][0]
        assert "MERGE (r:Routine {name: routine.name})" in query
        assert "ON CREATE SET" in query
        assert "routine_id = routine.routine_id" in query

    def test_create_label_nodes(self, builder, mock_connection):
        """Test creation of label nodes."""
        labels = [
            LabelNode(
                name="START",
                routine_name="DG10",
                line_number=10,
                is_entry_point=True,
                is_function=False
            ),
            LabelNode(
                name="EN",
                routine_name="DG10",
                line_number=20,
                is_entry_point=True,
                is_function=False,
                parameters=["DFN"]
            ),
        ]

        count = builder.create_label_nodes(labels)

        assert mock_connection.execute_query.called
        assert count == 2

        # Check query structure
        call_args = mock_connection.execute_query.call_args_list[0]
        query = call_args[0][0]
        assert "MERGE (l:Label {routine_name: label.routine_name, name: label.name})" in query
        assert "label_id = label.label_id" in query
        assert "is_entry_point = label.is_entry_point" in query

    def test_create_contains_label_relationships(self, builder, mock_connection):
        """Test creation of CONTAINS_LABEL relationships."""
        routines = [
            RoutineNode(
                name="DG10",
                package_name="Registration",
                prefix="DG",
                path="/path/to/DG10.m",
                lines_of_code=100
            ),
        ]

        labels = [
            LabelNode(
                name="START",
                routine_name="DG10",
                line_number=10,
                is_entry_point=True,
                is_function=False
            ),
            LabelNode(
                name="EN",
                routine_name="DG10",
                line_number=20,
                is_entry_point=True,
                is_function=False
            ),
        ]

        mock_connection.execute_query.return_value = [{"count": 2}]
        count = builder.create_contains_label_relationships(routines, labels)

        assert mock_connection.execute_query.called
        assert count == 2

        # Check relationship query
        call_args = mock_connection.execute_query.call_args_list[0]
        query = call_args[0][0]
        assert "MATCH (r:Routine {name: rel.routine_name})" in query
        assert "MATCH (l:Label {routine_name: rel.routine_name, name: rel.label_name})" in query
        assert "MERGE (r)-[:CONTAINS_LABEL {line_number: rel.line_number}]->(l)" in query

    def test_create_package_routine_relationships(self, builder, mock_connection):
        """Test creation of OWNS_ROUTINE relationships."""
        routines = [
            RoutineNode(
                name="DG10",
                package_name="Registration",
                prefix="DG",
                path="/path/to/DG10.m",
                lines_of_code=100
            ),
            RoutineNode(
                name="XM01",
                package_name="MailMan",
                prefix="XM",
                path="/path/to/XM01.m",
                lines_of_code=200
            ),
        ]

        mock_connection.execute_query.return_value = [{"count": 2}]
        count = builder.create_package_routine_relationships(routines)

        assert mock_connection.execute_query.called
        assert count == 2

        # Check relationship query
        call_args = mock_connection.execute_query.call_args_list[0]
        query = call_args[0][0]
        assert "MATCH (p:Package)" in query
        assert "WHERE routine.prefix IN p.prefixes" in query
        assert "MATCH (r:Routine {name: routine.name})" in query
        assert "MERGE (p)-[:OWNS_ROUTINE]->(r)" in query

        # Check batch data
        # call_args is a tuple of (args, kwargs)
        # We're passing the dict as second positional argument
        if len(call_args[0]) >= 2:
            params = call_args[0][1]  # Second positional argument
        else:
            params = call_args[1]  # Or in kwargs

        assert "routines" in params
        batch_data = params["routines"]
        assert len(batch_data) == 2
        assert batch_data[0]["name"] == "DG10"
        assert batch_data[0]["prefix"] == "DG"

    def test_empty_routines_handling(self, builder, mock_connection):
        """Test handling of empty routine list."""
        count = builder.create_routine_nodes([])
        assert count == 0
        assert not mock_connection.execute_query.called

    def test_empty_labels_handling(self, builder, mock_connection):
        """Test handling of empty label list."""
        count = builder.create_label_nodes([])
        assert count == 0
        assert not mock_connection.execute_query.called

    def test_no_matching_routines_for_labels(self, builder, mock_connection):
        """Test when labels don't match any routines."""
        routines = [
            RoutineNode(
                name="DG10",
                package_name="Registration",
                prefix="DG",
                path="/path/to/DG10.m",
                lines_of_code=100
            ),
        ]

        labels = [
            LabelNode(
                name="START",
                routine_name="XM01",  # Different routine
                line_number=10,
                is_entry_point=True,
                is_function=False
            ),
        ]

        count = builder.create_contains_label_relationships(routines, labels)
        assert count == 0

    def test_routines_without_prefix(self, builder, mock_connection):
        """Test routines without prefix don't create package relationships."""
        routines = [
            RoutineNode(
                name="TEST",
                package_name=None,
                prefix=None,  # No prefix
                path="/path/to/TEST.m",
                lines_of_code=50
            ),
        ]

        count = builder.create_package_routine_relationships(routines)
        assert count == 0

    def test_batch_processing(self, builder, mock_connection):
        """Test that large datasets are processed in batches."""
        # Create 5 routines with batch size of 2
        routines = [
            RoutineNode(
                name=f"DG{i:02d}",
                package_name="Registration",
                prefix="DG",
                path=f"/path/to/DG{i:02d}.m",
                lines_of_code=100
            )
            for i in range(5)
        ]

        builder.batch_size = 2
        builder.create_routine_nodes(routines)

        # Should be called 3 times (2 + 2 + 1)
        assert mock_connection.execute_query.call_count == 3

    def test_error_handling(self, builder, mock_connection):
        """Test graceful error handling."""
        mock_connection.execute_query.side_effect = Exception("Database error")

        routines = [
            RoutineNode(
                name="DG10",
                package_name="Registration",
                prefix="DG",
                path="/path/to/DG10.m",
                lines_of_code=100
            ),
        ]

        # Should not raise, but return 0
        count = builder.create_routine_nodes(routines)
        assert count == 0
