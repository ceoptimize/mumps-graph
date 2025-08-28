"""Tests for Phase 2 graph builder enhancements."""

import pytest
from unittest.mock import MagicMock, patch
from src.graph.builder import GraphBuilder
from src.models.nodes import CrossReferenceNode, FieldNode, FileNode, SubfileNode
from src.models.relationships import IndexedByRel, SubfileOfRel, VariablePointerRel


class TestPhase2Builder:
    """Test Phase 2 graph building functionality."""

    def test_create_cross_reference_nodes_empty(self):
        """Test creating cross-reference nodes with empty input."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        count = builder.create_cross_reference_nodes({})
        assert count == 0

    def test_create_cross_reference_nodes_basic(self):
        """Test creating basic cross-reference nodes."""
        connection = MagicMock()
        connection.execute_query.return_value = [{"created": 2}]
        
        builder = GraphBuilder(connection)
        
        xrefs = {
            "xref1": CrossReferenceNode(
                xref_id="xref1",
                name="B",
                file_number="2",
                field_number=".01",
                xref_type="regular",
                xref_number="1",
            ),
            "xref2": CrossReferenceNode(
                xref_id="xref2",
                name="SSN",
                file_number="2",
                field_number=".09",
                xref_type="MUMPS",
                xref_number="991",
            ),
        }
        
        with patch("src.graph.builder.console"):
            count = builder.create_cross_reference_nodes(xrefs)
        
        # Should have called execute_query
        assert connection.execute_query.called
        assert count == 2

    def test_create_indexed_by_relationships_empty(self):
        """Test creating INDEXED_BY relationships with empty input."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        # Empty xrefs
        count = builder.create_indexed_by_relationships({}, [])
        assert count == 0
        
        # Empty fields
        xrefs = {"xref1": MagicMock()}
        count = builder.create_indexed_by_relationships(xrefs, [])
        assert count == 0

    def test_create_indexed_by_relationships_matching(self):
        """Test creating INDEXED_BY relationships with matching fields."""
        connection = MagicMock()
        connection.execute_query.return_value = [{"created": 1}]
        
        builder = GraphBuilder(connection)
        
        # Create xref and matching field
        xref = CrossReferenceNode(
            xref_id="xref1",
            name="B",
            file_number="2",
            field_number=".01",
            xref_type="regular",
            xref_number="1",
            set_logic='SET ^DD(2,"B",$E(X,1,30),DA)=""',
            kill_logic='KILL ^DD(2,"B",$E(X,1,30),DA)',
        )
        
        field = FieldNode(
            field_id="field1",
            number=".01",
            name="NAME",
            file_number="2",
            data_type="F",
        )
        
        xrefs = {"xref1": xref}
        fields = [field]
        
        with patch("src.graph.builder.console"):
            count = builder.create_indexed_by_relationships(xrefs, fields)
        
        # Should create one relationship
        assert connection.execute_query.called
        assert count == 1

    def test_create_indexed_by_relationships_no_match(self):
        """Test INDEXED_BY relationships when fields do not match xrefs."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        # Create xref and non-matching field
        xref = CrossReferenceNode(
            xref_id="xref1",
            name="B",
            file_number="2",
            field_number=".01",
            xref_type="regular",
            xref_number="1",
        )
        
        field = FieldNode(
            field_id="field1",
            number=".02",  # Different field number
            name="SEX",
            file_number="2",
            data_type="S",
        )
        
        xrefs = {"xref1": xref}
        fields = [field]
        
        count = builder.create_indexed_by_relationships(xrefs, fields)
        
        # Should not create any relationships
        assert count == 0

    def test_create_subfile_relationships_empty(self):
        """Test creating SUBFILE_OF relationships with empty input."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        count = builder.create_subfile_relationships({}, {})
        assert count == 0

    def test_create_subfile_relationships_basic(self):
        """Test creating basic SUBFILE_OF relationships."""
        connection = MagicMock()
        connection.execute_query.return_value = [{"created": 1}]
        
        builder = GraphBuilder(connection)
        
        # Create parent and subfile
        parent = FileNode(
            file_id="file1",
            number="2",
            name="PATIENT",
        )
        
        subfile = SubfileNode(
            file_id="file2",
            number="2.01",
            name="ALIAS",
            parent_file_number="2",
            parent_field_number=".01",
            nesting_level=1,
        )
        
        files = {"2": parent}
        subfiles = {"2.01": subfile}
        
        count = builder.create_subfile_relationships(subfiles, files)
        
        # Should create one relationship
        assert connection.execute_query.called
        assert count == 1

    def test_create_subfile_relationships_missing_parent(self):
        """Test SUBFILE_OF relationships when parent does not exist."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        subfile = SubfileNode(
            file_id="file2",
            number="2.01",
            name="ALIAS",
            parent_file_number="99",  # Parent does not exist
            parent_field_number=".01",
            nesting_level=1,
        )
        
        files = {"2": FileNode(file_id="file1", number="2", name="PATIENT")}
        subfiles = {"2.01": subfile}
        
        count = builder.create_subfile_relationships(subfiles, files)
        
        # Should not create any relationships
        assert count == 0

    def test_create_variable_pointer_relationships_empty(self):
        """Test creating VARIABLE_POINTER relationships with empty input."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        count = builder.create_variable_pointer_relationships({}, [], {})
        assert count == 0

    def test_create_variable_pointer_relationships_basic(self):
        """Test creating basic VARIABLE_POINTER relationships."""
        connection = MagicMock()
        connection.execute_query.return_value = [{"created": 2}]
        
        builder = GraphBuilder(connection)
        
        # Create field with V-pointer
        field = FieldNode(
            field_id="field1",
            number="100",
            name="PROVIDER",
            file_number="2",
            data_type="V",
        )
        
        # Create target files
        file1 = FileNode(file_id="file200", number="200", name="NEW PERSON")
        file2 = FileNode(file_id="file4", number="4", name="INSTITUTION")
        
        # V-pointer targets
        v_pointers = {
            "2_100": [
                {
                    "v_number": "1",
                    "target_file": "200",
                    "target_global": "VA(200,",
                    "target_description": "NEW PERSON",
                },
                {
                    "v_number": "2",
                    "target_file": "4",
                    "target_global": "DIC(4,",
                    "target_description": "INSTITUTION",
                },
            ]
        }
        
        fields = [field]
        files = {"200": file1, "4": file2}
        
        count = builder.create_variable_pointer_relationships(v_pointers, fields, files)
        
        # Should create two relationships
        assert connection.execute_query.called
        assert count == 2

    def test_create_variable_pointer_relationships_missing_target(self):
        """Test V-pointer relationships when target file does not exist."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        field = FieldNode(
            field_id="field1",
            number="100",
            name="PROVIDER",
            file_number="2",
            data_type="V",
        )
        
        v_pointers = {
            "2_100": [
                {
                    "v_number": "1",
                    "target_file": "999",  # Does not exist
                    "target_global": "XXX(",
                    "target_description": "MISSING",
                }
            ]
        }
        
        fields = [field]
        files = {"200": FileNode(file_id="file200", number="200", name="NEW PERSON")}
        
        count = builder.create_variable_pointer_relationships(v_pointers, fields, files)
        
        # Should not create any relationships
        assert count == 0

    def test_enhance_pointer_relationships(self):
        """Test enhance_pointer_relationships (placeholder method)."""
        connection = MagicMock()
        builder = GraphBuilder(connection)
        
        count = builder.enhance_pointer_relationships()
        
        # Should return 0 (not implemented)
        assert count == 0

    @pytest.mark.integration
    def test_phase2_builder_integration(self):
        """Integration test for Phase 2 builder with mock connection."""
        connection = MagicMock()
        connection.execute_query.return_value = [{"created": 1}]
        
        builder = GraphBuilder(connection)
        
        # Create test data
        xref = CrossReferenceNode(
            xref_id="xref1",
            name="B",
            file_number="2",
            field_number=".01",
            xref_type="regular",
            xref_number="1",
        )
        
        field = FieldNode(
            field_id="field1",
            number=".01",
            name="NAME",
            file_number="2",
            data_type="F",
        )
        
        parent = FileNode(file_id="file1", number="2", name="PATIENT")
        
        subfile = SubfileNode(
            file_id="file2",
            number="2.01",
            name="ALIAS",
            parent_file_number="2",
            parent_field_number=".01",
            nesting_level=1,
        )
        
        # Execute Phase 2 methods
        with patch("src.graph.builder.console"):
            xref_count = builder.create_cross_reference_nodes({"xref1": xref})
            indexed_count = builder.create_indexed_by_relationships(
                {"xref1": xref}, [field]
            )
            subfile_count = builder.create_subfile_relationships(
                {"2.01": subfile}, {"2": parent}
            )
        
        # Verify all methods were called
        assert xref_count > 0
        assert indexed_count > 0
        assert subfile_count > 0
        assert connection.execute_query.called