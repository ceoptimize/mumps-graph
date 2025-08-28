"""Tests for ZWR parser."""


from src.models.nodes import ParsedGlobal
from src.parsers.zwr_parser import ZWRParser


class TestZWRParser:
    """Test ZWR parser functionality."""

    def test_parse_simple_global(self):
        """Test parsing basic global line."""
        parser = ZWRParser()
        result = parser.parse_line('^DD(0,0)="ATTRIBUTE^N^999^41"')

        assert result is not None
        assert result.global_name == "DD"
        assert result.subscripts == ["0", "0"]
        assert result.value == "ATTRIBUTE^N^999^41"

    def test_parse_subscripts(self):
        """Test parsing various subscript formats."""
        parser = ZWRParser()

        # Simple subscripts
        subscripts = parser.parse_subscripts("1,2,3")
        assert subscripts == ["1", "2", "3"]

        # Subscripts with quotes
        subscripts = parser.parse_subscripts('"NAME",0')
        assert subscripts == ["NAME", "0"]

        # Empty subscripts
        subscripts = parser.parse_subscripts("")
        assert subscripts == []

    def test_unescape_value(self):
        """Test unescaping ZWR values."""
        parser = ZWRParser()

        # Doubled quotes
        unescaped = parser.unescape_value('TEST""VALUE')
        assert unescaped == 'TEST"VALUE'

        # Normal value
        unescaped = parser.unescape_value("NORMAL VALUE")
        assert unescaped == "NORMAL VALUE"

    def test_extract_file_definitions(self, sample_dd_lines):
        """Test extracting file nodes from DD."""
        parser = ZWRParser()
        files, fields = parser.extract_file_definitions(sample_dd_lines)

        # Check files
        assert len(files) == 2
        assert "2" in files
        assert "200" in files

        patient_file = files["2"]
        assert patient_file.name == "PATIENT"
        assert patient_file.global_root == "^DPT"
        assert not patient_file.is_subfile

        person_file = files["200"]
        assert person_file.name == "NEW PERSON"
        assert person_file.global_root == "^VA(200,"

    def test_extract_field_definitions(self, sample_dd_lines):
        """Test extracting field nodes from DD."""
        parser = ZWRParser()
        files, fields = parser.extract_field_definitions(sample_dd_lines)

        # Check fields
        assert len(fields) > 0

        # Find NAME field
        name_fields = [f for f in fields if f.name == "NAME" and f.file_number == "2"]
        assert len(name_fields) == 1
        name_field = name_fields[0]
        assert name_field.number == ".01"
        assert name_field.data_type == "R"
        assert name_field.required

        # Find SEX field
        sex_fields = [f for f in fields if f.name == "SEX"]
        assert len(sex_fields) == 1
        sex_field = sex_fields[0]
        assert sex_field.data_type == "S"  # Set of codes

        # Find DATE OF BIRTH field
        dob_fields = [f for f in fields if f.name == "DATE OF BIRTH"]
        assert len(dob_fields) == 1
        dob_field = dob_fields[0]
        assert dob_field.data_type == "D"  # Date

    def test_pointer_field_detection(self, sample_dd_lines):
        """Test detection of pointer fields."""
        parser = ZWRParser()
        files, fields = parser.extract_field_definitions(sample_dd_lines)

        # Find PROVIDER field (pointer to file 200)
        provider_fields = [f for f in fields if f.name == "PROVIDER"]
        assert len(provider_fields) == 1
        provider_field = provider_fields[0]
        assert provider_field.is_pointer
        assert provider_field.data_type == "P"
        assert provider_field.target_file == "200"

    def test_parse_file(self, sample_zwr_file):
        """Test parsing complete ZWR file."""
        parser = ZWRParser()
        files, fields = parser.parse_file(sample_zwr_file)

        assert len(files) == 2
        assert len(fields) > 0

        # Check statistics
        stats = parser.get_statistics()
        assert stats["total_files"] == 2
        assert stats["total_fields"] > 0
        assert stats["lines_processed"] > 0

    def test_stream_parse_file(self, sample_zwr_file):
        """Test streaming ZWR file parsing."""
        parser = ZWRParser()
        parsed_globals = list(parser.stream_parse_file(sample_zwr_file))

        assert len(parsed_globals) > 0

        # Check that we get ParsedGlobal objects
        assert all(isinstance(pg, ParsedGlobal) for pg in parsed_globals)

        # Check DD entries
        dd_entries = [pg for pg in parsed_globals if pg.is_dd_entry()]
        assert len(dd_entries) > 0

    def test_is_file_header(self):
        """Test file header detection."""
        parser = ZWRParser()

        # File header
        parsed = parser.parse_line('^DD(2,0)="PATIENT^DPT^^"')
        assert parsed.is_file_header()

        # Field definition (not a file header)
        parsed = parser.parse_line('^DD(2,.01,0)="NAME^RF^^"')
        assert not parsed.is_file_header()

    def test_is_field_definition(self):
        """Test field definition detection."""
        parser = ZWRParser()

        # Field definition
        parsed = parser.parse_line('^DD(2,.01,0)="NAME^RF^^"')
        assert parsed.is_field_definition()

        # File header (not a field)
        parsed = parser.parse_line('^DD(2,0)="PATIENT^DPT^^"')
        assert not parsed.is_field_definition()

    def test_handle_invalid_lines(self):
        """Test handling of invalid or non-matching lines."""
        parser = ZWRParser()

        # Empty line
        result = parser.parse_line("")
        assert result is None

        # GT.M header
        result = parser.parse_line("GT.M 26-MAR-2018")
        assert result is None

        # ZWR header
        result = parser.parse_line("ZWR")
        assert result is None

        # Non-matching pattern
        result = parser.parse_line("This is not a global")
        assert result is None

    def test_complex_value_parsing(self):
        """Test parsing complex values with special characters."""
        parser = ZWRParser()

        # Value with caret delimiters
        result = parser.parse_line('^DD(2,.301,0)="SERVICE CONNECTED PERCENTAGE^NJ3,0^^.3;1^K:+X"')
        assert result.value == "SERVICE CONNECTED PERCENTAGE^NJ3,0^^.3;1^K:+X"

        # Value with MUMPS code
        result = parser.parse_line('^DD(2,.03,0)="DATE OF BIRTH^D^^0;3^S %DT=""EX"" D ^%DT S X=Y K:Y<1 X"')
        assert "DATE OF BIRTH" in result.value
