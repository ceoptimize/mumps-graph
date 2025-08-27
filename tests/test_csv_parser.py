"""Tests for Package CSV parser."""

import pytest
from pathlib import Path

from src.parsers.csv_parser import PackageCSVParser
from src.models.nodes import PackageNode


class TestPackageCSVParser:
    """Test Package CSV parser functionality."""

    def test_parse_file(self, sample_csv_file):
        """Test parsing Packages.csv file."""
        parser = PackageCSVParser()
        packages = parser.parse_file(sample_csv_file)
        
        assert len(packages) == 3
        
        # Check Accounts Receivable package
        ar_package = next(p for p in packages if p.name == "Accounts Receivable")
        assert ar_package.directory == "Accounts Receivable"
        assert "PRC" in ar_package.prefixes
        assert "PRCA" in ar_package.prefixes
        assert ar_package.vdl_id == "36"
        assert ar_package.files_low == "430"
        assert ar_package.files_high == "430.9"
        
        # Check VA FileMan package
        fm_package = next(p for p in packages if p.name == "VA FileMan")
        assert fm_package.directory == "VA FileMan"
        assert "DI" in fm_package.prefixes
        assert "DIA" in fm_package.prefixes
        assert "DD" in fm_package.prefixes
        assert "DM" in fm_package.prefixes

    def test_extract_prefixes(self):
        """Test prefix extraction from CSV rows."""
        parser = PackageCSVParser()
        
        # Single prefix
        row = {"Prefixes": "ABC"}
        prefixes = parser._extract_prefixes(row)
        assert prefixes == ["ABC"]
        
        # Multiple prefixes with spaces
        row = {"Prefixes": "ABC DEF GHI"}
        prefixes = parser._extract_prefixes(row)
        assert prefixes == ["ABC", "DEF", "GHI"]
        
        # Multiple prefixes with commas
        row = {"Prefixes": "ABC,DEF,GHI"}
        prefixes = parser._extract_prefixes(row)
        assert prefixes == ["ABC", "DEF", "GHI"]
        
        # Mixed separators
        row = {"Prefixes": "ABC DEF, GHI JKL"}
        prefixes = parser._extract_prefixes(row)
        assert set(prefixes) == {"ABC", "DEF", "GHI", "JKL"}
        
        # Empty prefixes
        row = {"Prefixes": ""}
        prefixes = parser._extract_prefixes(row)
        assert prefixes == []
        
        # N/A prefix (should be filtered)
        row = {"Prefixes": "N/A"}
        prefixes = parser._extract_prefixes(row)
        assert prefixes == []

    def test_is_continuation_row(self):
        """Test detection of continuation rows."""
        parser = PackageCSVParser()
        
        # Continuation row (empty directory, has prefixes)
        row = {"Directory Name": "", "Prefixes": "ABC DEF"}
        assert parser._is_continuation_row(row)
        
        # Continuation row (spaces only in directory)
        row = {"Directory Name": "  ", "Prefixes": "ABC"}
        assert parser._is_continuation_row(row)
        
        # Normal row
        row = {"Directory Name": "Test Package", "Prefixes": "ABC"}
        assert not parser._is_continuation_row(row)
        
        # Empty row
        row = {"Directory Name": "", "Prefixes": ""}
        assert not parser._is_continuation_row(row)

    def test_process_package_row(self):
        """Test processing individual package rows."""
        parser = PackageCSVParser()
        
        # Complete row
        row = {
            "Directory Name": "Test Package",
            "Package Name": "Test Package System",
            "Prefixes": "TST TSTA",
            "VDL ID": "100",
            "File Numbers Low": "500",
            "File Numbers High": "599.99"
        }
        package = parser._process_package_row(row)
        
        assert package is not None
        assert package.name == "Test Package System"
        assert package.directory == "Test Package"
        assert "TST" in package.prefixes
        assert "TSTA" in package.prefixes
        assert package.vdl_id == "100"
        assert package.files_low == "500"
        assert package.files_high == "599.99"
        
        # Row with missing package name (uses directory name)
        row = {
            "Directory Name": "Test Dir",
            "Package Name": "",
            "Prefixes": "TD",
        }
        package = parser._process_package_row(row)
        assert package.name == "Test Dir"
        
        # Row with no directory (should return None)
        row = {"Directory Name": "", "Package Name": "Invalid"}
        package = parser._process_package_row(row)
        assert package is None

    def test_find_package_by_prefix(self, sample_csv_file):
        """Test finding packages by prefix."""
        parser = PackageCSVParser()
        parser.parse_file(sample_csv_file)
        
        # Find by exact prefix
        assert parser.find_package_by_prefix("PRC") == "Accounts Receivable"
        assert parser.find_package_by_prefix("GMRA") == "Adverse Reaction Tracking"
        assert parser.find_package_by_prefix("DD") == "VA FileMan"
        
        # Case insensitive
        assert parser.find_package_by_prefix("prc") == "Accounts Receivable"
        assert parser.find_package_by_prefix("gmra") == "Adverse Reaction Tracking"
        
        # Non-existent prefix
        assert parser.find_package_by_prefix("XYZ") is None

    def test_find_package_by_file_number(self, sample_csv_file):
        """Test finding packages by file number."""
        parser = PackageCSVParser()
        parser.parse_file(sample_csv_file)
        
        # File in range
        assert parser.find_package_by_file_number("430.5") == "Accounts Receivable"
        assert parser.find_package_by_file_number("120.5") == "Adverse Reaction Tracking"
        assert parser.find_package_by_file_number("1.5") == "VA FileMan"
        
        # Edge cases
        assert parser.find_package_by_file_number("430") == "Accounts Receivable"
        assert parser.find_package_by_file_number("430.9") == "Accounts Receivable"
        
        # Out of range
        assert parser.find_package_by_file_number("1000") is None
        assert parser.find_package_by_file_number("-1") is None
        
        # Invalid file number
        assert parser.find_package_by_file_number("ABC") is None

    def test_get_all_prefixes(self, sample_csv_file):
        """Test getting all unique prefixes."""
        parser = PackageCSVParser()
        parser.parse_file(sample_csv_file)
        
        prefixes = parser.get_all_prefixes()
        
        assert "PRC" in prefixes
        assert "PRCA" in prefixes
        assert "GMRA" in prefixes
        assert "DI" in prefixes
        assert "DD" in prefixes
        
        # Should be sorted
        assert prefixes == sorted(prefixes)

    def test_get_statistics(self, sample_csv_file):
        """Test getting parsing statistics."""
        parser = PackageCSVParser()
        parser.parse_file(sample_csv_file)
        
        stats = parser.get_statistics()
        
        assert stats["total_packages"] == 3
        assert stats["total_prefixes"] == 7  # Total across all packages
        assert stats["unique_prefixes"] == 7  # All unique in this sample
        assert stats["packages_with_file_ranges"] == 3
        assert stats["packages_with_vdl_id"] == 3

    def test_multi_row_packages(self):
        """Test handling packages that span multiple rows."""
        # Create a CSV with continuation rows
        csv_content = """Directory Name,Package Name,Prefixes,VDL ID,File Numbers Low,File Numbers High
Multi Row Package,Multi Row,MR1 MR2,100,500,599
,,MR3 MR4,,, 
Another Package,Another,AP,101,600,699"""
        
        from tempfile import NamedTemporaryFile
        import tempfile
        
        with NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = Path(f.name)
        
        try:
            parser = PackageCSVParser()
            packages = parser.parse_file(temp_path)
            
            assert len(packages) == 2
            
            # Check that first package has all prefixes
            mr_package = next(p for p in packages if p.name == "Multi Row")
            assert len(mr_package.prefixes) == 4
            assert "MR1" in mr_package.prefixes
            assert "MR2" in mr_package.prefixes
            assert "MR3" in mr_package.prefixes
            assert "MR4" in mr_package.prefixes
            
        finally:
            temp_path.unlink()  # Clean up temp file