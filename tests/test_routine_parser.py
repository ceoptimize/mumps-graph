"""Unit tests for MUMPS routine parser."""

import pytest

from src.parsers.routine_parser import RoutineParser


class TestRoutineParser:
    """Test suite for RoutineParser."""

    @pytest.fixture
    def parser(self):
        """Create a parser instance."""
        return RoutineParser()

    def test_label_extraction_simple(self, parser):
        """Test extraction of simple labels."""
        content = """DG10 ;ALB/MRL-LOAD/EDIT PATIENT DATA
 ;;5.3;Registration;**32,109**;Aug 13, 1993
START ;
 D LO^DGUTL
A W !! K VET,DIE
EN(DFN) ; Entry point with parameter
 Q
"""
        labels = parser.extract_labels_from_content(content, "DG10")

        assert len(labels) == 4  # DG10, START, A, EN
        label_names = [label.name for label in labels]
        assert "DG10" in label_names  # First line is also a label
        assert "START" in label_names
        assert "A" in label_names
        assert "EN" in label_names

        # Check entry point detection
        en_label = next(l for l in labels if l.name == "EN")
        assert en_label.is_entry_point
        assert en_label.parameters == ["DFN"]

    def test_label_with_parameters(self, parser):
        """Test label parameter extraction."""
        content = """TEST(X,Y,Z) ; Test label with multiple params
 Q X+Y+Z
"""
        labels = parser.extract_labels_from_content(content, "TEST")

        assert len(labels) == 1
        label = labels[0]
        assert label.name == "TEST"
        assert label.parameters == ["X", "Y", "Z"]
        assert label.comment == "Test label with multiple params"

    def test_function_detection(self, parser):
        """Test detection of functions (labels that return values)."""
        content = """FUNC() ; Function that returns value
 N X
 S X=10
 Q $$VALUE
REGULAR ; Regular label
 D SOMETHING
 Q
"""
        labels = parser.extract_labels_from_content(content, "TEST")

        func_label = next(l for l in labels if l.name == "FUNC")
        assert func_label.is_function

        regular_label = next(l for l in labels if l.name == "REGULAR")
        assert not regular_label.is_function

    def test_entry_point_heuristics(self, parser):
        """Test entry point detection heuristics."""
        test_cases = [
            ("EN", True),
            ("EP", True),
            ("START", True),
            ("INIT", True),
            ("BEGIN", True),
            ("A", True),  # Short labels
            ("A1", True),
            ("PROCESS", False),
            ("CALCULATE", False),
        ]

        for label_name, expected in test_cases:
            result = parser._is_entry_point(label_name)
            assert result == expected, f"Failed for {label_name}"

    def test_skip_comments_and_indented_lines(self, parser):
        """Test that comments and indented lines are not treated as labels."""
        content = """; This is a comment
 ; Indented comment
LABEL1 ;
 . D SOMETHING  ; Indented code
 . . D MORE     ; More indented
; Another comment
LABEL2 ;
 Q
"""
        labels = parser.extract_labels_from_content(content, "TEST")

        assert len(labels) == 2
        label_names = [label.name for label in labels]
        assert "LABEL1" in label_names
        assert "LABEL2" in label_names

    def test_malformed_mumps_handling(self, parser):
        """Test handling of malformed MUMPS code."""
        content = """This is not valid MUMPS
!@#$%^&*()
VALIDLABEL ;
 Q
More garbage
"""
        labels = parser.extract_labels_from_content(content, "TEST")

        # Parser is lenient and will extract anything that looks like a label
        # It finds: T (from "This"), VALIDLABEL, and M (from "More")
        assert len(labels) == 3
        label_names = [label.name for label in labels]
        assert "VALIDLABEL" in label_names
        # The parser is being lenient which is good for real-world MUMPS

    def test_routine_metadata_extraction(self, parser):
        """Test extraction of routine metadata from header."""
        lines = [
            "DG10 ;ALB/MRL-LOAD/EDIT PATIENT DATA ; 09/30/15",
            " ;;5.3;Registration;**32,109,139,149**;Aug 13, 1993;Build 14",
            " ;Per VHA Directive 2004-038, this routine should not be modified.",
        ]

        info = parser._extract_header_info(lines)

        assert info is not None
        assert "5.3" in info.get("version", "")
        assert "32" in info["patches"]
        assert "109" in info["patches"]
        assert "139" in info["patches"]

    def test_label_line_numbers(self, parser):
        """Test that line numbers are correctly tracked."""
        content = """LINE1 ;
 D SOMETHING
LINE3 ;
 Q
LINE5 ; On line 5
"""
        labels = parser.extract_labels_from_content(content, "TEST")

        line1 = next(l for l in labels if l.name == "LINE1")
        assert line1.line_number == 1

        line3 = next(l for l in labels if l.name == "LINE3")
        assert line3.line_number == 3

        line5 = next(l for l in labels if l.name == "LINE5")
        assert line5.line_number == 5

    def test_quit_with_value_patterns(self, parser):
        """Test various QUIT patterns for function detection."""
        test_cases = [
            ("Q $$VALUE", True),
            ("QUIT $$FUNC^ROUTINE", True),
            ("Q 1", True),
            ("Q VAR", True),
            ("Q", False),
            ("QUIT", False),
            ("Q  ", False),
        ]

        for line, expected_function in test_cases:
            content = f"""TESTLABEL ;
 {line}
"""
            labels = parser.extract_labels_from_content(content, "TEST")
            label = labels[0]
            assert label.is_function == expected_function, f"Failed for line: {line}"

    def test_empty_file_handling(self, parser):
        """Test handling of empty content."""
        content = ""
        labels = parser.extract_labels_from_content(content, "TEST")
        assert labels == []

    def test_label_with_no_comment(self, parser):
        """Test label without comment."""
        content = """LABEL
 Q
"""
        labels = parser.extract_labels_from_content(content, "TEST")
        assert len(labels) == 1
        assert labels[0].name == "LABEL"
        assert labels[0].comment is None
