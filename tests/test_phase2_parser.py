"""Tests for Phase 2 ZWR parser enhancements."""

from src.models.nodes import CrossReferenceNode, FileNode, SubfileNode
from src.parsers.zwr_parser import ZWRParser


class TestPhase2Parser:
    """Test Phase 2 parsing functionality."""

    def test_extract_cross_references_empty(self):
        """Test extracting cross-references from empty input."""
        parser = ZWRParser()
        xrefs = parser.extract_cross_references([])
        assert xrefs == {}

    def test_extract_cross_references_basic(self):
        """Test extracting basic cross-reference definitions."""
        parser = ZWRParser()
        lines = [
            '^DD(2,391,1,0)="^.1"',  # XRef header
            '^DD(2,391,1,991,0)="2^AVAFC391^MUMPS"',  # XRef definition
            '^DD(2,391,1,991,1)="SET logic here"',  # Set logic
            '^DD(2,391,1,991,2)="KILL logic here"',  # Kill logic
        ]

        xrefs = parser.extract_cross_references(lines)

        # Should find one cross-reference
        assert len(xrefs) == 1

        # Check the cross-reference details
        xref_id = "2_391_991"
        assert xref_id in xrefs

        xref = xrefs[xref_id]
        assert isinstance(xref, CrossReferenceNode)
        assert xref.name == "AVAFC391"
        assert xref.xref_type == "MUMPS"
        assert xref.file_number == "2"
        assert xref.field_number == "391"
        assert xref.set_logic == "SET logic here"
        assert xref.kill_logic == "KILL logic here"

    def test_extract_cross_references_multiple(self):
        """Test extracting multiple cross-references."""
        parser = ZWRParser()
        lines = [
            '^DD(2,391,1,0)="^.1"',
            '^DD(2,391,1,991,0)="2^B^REGULAR"',
            '^DD(2,391,1,992,0)="2^C^TRIGGER"',
            '^DD(3,100,1,0)="^.1"',
            '^DD(3,100,1,1,0)="3^AC^MUMPS"',
        ]

        xrefs = parser.extract_cross_references(lines)

        # Should find 3 cross-references
        assert len(xrefs) == 3
        assert "2_391_991" in xrefs
        assert "2_391_992" in xrefs
        assert "3_100_1" in xrefs

    def test_extract_subfiles_basic(self):
        """Test identifying basic subfiles."""
        parser = ZWRParser()

        # Create parent and subfile
        files = {
            "2": FileNode(number="2", name="PATIENT"),
            "2.01": FileNode(number="2.01", name="ALIAS"),
            "2.02": FileNode(number="2.02", name="RACE"),
            "3": FileNode(number="3", name="VISIT"),
        }

        subfiles = parser.extract_subfiles(files)

        # Should find 2 subfiles
        assert len(subfiles) == 2
        assert "2.01" in subfiles
        assert "2.02" in subfiles

        # Check subfile details
        subfile = subfiles["2.01"]
        assert isinstance(subfile, SubfileNode)
        assert subfile.parent_file_number == "2"
        assert subfile.nesting_level == 2  # ["2", "01"] = 2 parts
        assert subfile.is_subfile is True

    def test_extract_subfiles_nested(self):
        """Test identifying nested subfiles."""
        parser = ZWRParser()

        files = {
            "2": FileNode(number="2", name="PATIENT"),
            "2.01": FileNode(number="2.01", name="ALIAS"),
            "2.011": FileNode(number="2.011", name="ALIAS_COMMENT"),
        }

        subfiles = parser.extract_subfiles(files)

        assert len(subfiles) == 2

        # Check nested subfile
        if "2.011" in subfiles:
            nested = subfiles["2.011"]
            assert nested.parent_file_number == "2"
            assert nested.nesting_level == 2  # ["2", "011"] = 2 parts

    def test_extract_variable_pointers_empty(self):
        """Test extracting variable pointers from empty input."""
        parser = ZWRParser()
        v_pointers = parser.extract_variable_pointers([])
        assert v_pointers == {}

    def test_extract_variable_pointers_basic(self):
        """Test extracting basic variable pointer targets."""
        parser = ZWRParser()
        lines = [
            '^DD(2,100,"V",1,0)="200^VA(200,^NEW PERSON"',
            '^DD(2,100,"V",2,0)="2^DPT(^PATIENT"',
        ]

        v_pointers = parser.extract_variable_pointers(lines)

        # Should find one field with two targets
        assert len(v_pointers) == 1
        assert "2_100" in v_pointers

        targets = v_pointers["2_100"]
        assert len(targets) == 2

        # Check first target
        assert targets[0]["v_number"] == "1"
        assert targets[0]["target_file"] == "200"
        assert targets[0]["target_global"] == "VA(200,"
        assert targets[0]["target_description"] == "NEW PERSON"

        # Check second target
        assert targets[1]["v_number"] == "2"
        assert targets[1]["target_file"] == "2"

    def test_extract_variable_pointers_multiple_fields(self):
        """Test extracting variable pointers for multiple fields."""
        parser = ZWRParser()
        lines = [
            '^DD(2,100,"V",1,0)="200^VA(200,^NEW PERSON"',
            '^DD(3,200,"V",1,0)="4^DIC(4,^INSTITUTION"',
            '^DD(3,200,"V",2,0)="44^SC(^HOSPITAL LOCATION"',
        ]

        v_pointers = parser.extract_variable_pointers(lines)

        # Should find two fields with V-pointers
        assert len(v_pointers) == 2
        assert "2_100" in v_pointers
        assert "3_200" in v_pointers

        # First field has 1 target
        assert len(v_pointers["2_100"]) == 1

        # Second field has 2 targets
        assert len(v_pointers["3_200"]) == 2

    def test_is_xref_header(self):
        """Test identifying cross-reference headers."""
        parser = ZWRParser()

        # Valid xref header
        parsed = parser.parse_line('^DD(2,391,1,0)="^.1"')
        assert parser.is_xref_header(parsed) is True

        # Not an xref header
        parsed = parser.parse_line('^DD(2,391,0)="NAME^RF^^0;1^K:$L(X)>30 X"')
        assert parser.is_xref_header(parsed) is False

    def test_is_v_pointer_target(self):
        """Test identifying variable pointer targets."""
        parser = ZWRParser()

        # Valid V-pointer target
        parsed = parser.parse_line('^DD(2,100,"V",1,0)="200^VA(200,^NEW PERSON"')
        assert parser.is_v_pointer_target(parsed) is True

        # Not a V-pointer target
        parsed = parser.parse_line('^DD(2,100,0)="POINTER^V^^0;1^"')
        assert parser.is_v_pointer_target(parsed) is False

    def test_integration_phase2_extraction(self, sample_dd_lines):
        """Integration test for all Phase 2 extractions."""
        parser = ZWRParser()

        # Extract Phase 1 data first
        files, fields = parser.extract_file_definitions(sample_dd_lines)

        # Extract Phase 2 data
        xrefs = parser.extract_cross_references(sample_dd_lines)
        subfiles = parser.extract_subfiles(files)
        v_pointers = parser.extract_variable_pointers(sample_dd_lines)

        # Verify we got some data (actual counts depend on fixture)
        assert isinstance(xrefs, dict)
        assert isinstance(subfiles, dict)
        assert isinstance(v_pointers, dict)

        # All cross-references should be valid
        for xref in xrefs.values():
            assert isinstance(xref, CrossReferenceNode)
            assert xref.file_number
            assert xref.field_number
            assert xref.name

        # All subfiles should be valid
        for subfile in subfiles.values():
            assert isinstance(subfile, SubfileNode)
            assert subfile.parent_file_number
            assert subfile.is_subfile is True
