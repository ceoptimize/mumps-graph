"""CSV parser for Packages.csv file."""

import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.models.nodes import PackageNode


class PackageCSVParser:
    """Parser for VistA Packages.csv file."""

    def __init__(self):
        """Initialize the CSV parser."""
        self.packages: List[PackageNode] = []
        self.prefix_to_package: Dict[str, str] = {}
        self.file_range_to_package: Dict[tuple, str] = {}
        self.file_to_package: Dict[str, str] = {}  # Direct file number to package mapping

    def parse_file(self, file_path: Path) -> List[PackageNode]:
        """
        Parse the Packages.csv file.

        Args:
            file_path: Path to Packages.csv

        Returns:
            List of PackageNode objects
        """
        packages = []
        current_package = None

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Handle multi-row packages (continuation rows)
                if self._is_continuation_row(row):
                    if current_package:
                        # Add additional prefixes from continuation row
                        additional_prefixes = self._extract_prefixes(row)
                        current_package.prefixes.extend(additional_prefixes)
                        # Add file numbers from continuation row
                        file_num = row.get("File Numbers", "").strip()
                        if file_num:
                            current_package.file_numbers.append(file_num)
                            self.file_to_package[file_num] = current_package.name
                    continue

                # Process new package
                package = self._process_package_row(row)
                if package:
                    packages.append(package)
                    current_package = package

                    # Map prefixes to package
                    for prefix in package.prefixes:
                        self.prefix_to_package[prefix] = package.name

                    # Map file numbers to package
                    for file_num in package.file_numbers:
                        self.file_to_package[file_num] = package.name

                    # Map file range to package (if applicable)
                    if package.files_low and package.files_high:
                        try:
                            low = float(package.files_low)
                            high = float(package.files_high)
                            self.file_range_to_package[(low, high)] = package.name
                        except (ValueError, TypeError):
                            pass

        self.packages = packages
        return packages

    def _is_continuation_row(self, row: Dict[str, str]) -> bool:
        """
        Check if a row is a continuation of the previous package.

        Args:
            row: CSV row as dictionary

        Returns:
            True if continuation row
        """
        # Continuation rows have empty Package Name and Directory Name
        # but may have prefixes or file numbers
        return not row.get("Package Name", "").strip() and not row.get("Directory Name", "").strip()

    def _process_package_row(self, row: Dict[str, str]) -> Optional[PackageNode]:
        """
        Process a package row from CSV.

        Args:
            row: CSV row as dictionary

        Returns:
            PackageNode or None
        """
        directory = row.get("Directory Name", "").strip()
        if not directory:
            return None

        name = row.get("Package Name", "").strip()
        if not name:
            name = directory  # Fallback to directory name

        prefixes = self._extract_prefixes(row)
        vdl_id = row.get("VDL ID", "").strip() or None

        # Extract file numbers
        file_numbers = []
        file_num = row.get("File Numbers", "").strip()
        if file_num:
            file_numbers.append(file_num)

        # Extract file range (legacy support)
        files_low = row.get("File Numbers Low", "").strip() or None
        files_high = row.get("File Numbers High", "").strip() or None

        return PackageNode(
            name=name,
            directory=directory,
            prefixes=prefixes,
            vdl_id=vdl_id,
            files_low=files_low,
            files_high=files_high,
            file_numbers=file_numbers,
        )

    def _extract_prefixes(self, row: Dict[str, str]) -> List[str]:
        """
        Extract prefixes from a CSV row.

        Args:
            row: CSV row as dictionary

        Returns:
            List of prefix strings
        """
        prefixes_str = row.get("Prefixes", "").strip()
        if not prefixes_str:
            return []

        # Handle multiple prefixes separated by commas or spaces
        prefixes = []
        # Split by comma first
        parts = prefixes_str.split(",")
        for part in parts:
            part = part.strip()
            if part:
                # Sometimes prefixes are space-separated within a part
                sub_parts = part.split()
                prefixes.extend(sub_parts)

        # Clean up prefixes
        cleaned_prefixes = []
        for prefix in prefixes:
            prefix = prefix.strip().upper()
            # Remove any quotes or special characters
            prefix = prefix.replace('"', "").replace("'", "")
            if prefix and prefix != "N/A":
                cleaned_prefixes.append(prefix)

        return cleaned_prefixes

    def find_package_by_prefix(self, prefix: str) -> Optional[str]:
        """
        Find package name by prefix.

        Args:
            prefix: Prefix to search

        Returns:
            Package name or None
        """
        return self.prefix_to_package.get(prefix.upper())

    def find_package_by_file_number(self, file_number: str) -> Optional[str]:
        """
        Find package name by file number.

        Args:
            file_number: File number to search

        Returns:
            Package name or None
        """
        # First check direct mapping
        if file_number in self.file_to_package:
            return self.file_to_package[file_number]

        # Then check ranges (if any)
        try:
            file_num = float(file_number)
        except (ValueError, TypeError):
            return None

        # Check file ranges
        for (low, high), package_name in self.file_range_to_package.items():
            if low <= file_num <= high:
                return package_name

        return None

    def get_all_prefixes(self) -> List[str]:
        """Get all unique prefixes."""
        return sorted(self.prefix_to_package.keys())

    def get_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        total_prefixes = sum(len(p.prefixes) for p in self.packages)
        packages_with_ranges = sum(1 for p in self.packages if p.files_low and p.files_high)

        return {
            "total_packages": len(self.packages),
            "total_prefixes": total_prefixes,
            "unique_prefixes": len(self.prefix_to_package),
            "packages_with_file_ranges": packages_with_ranges,
            "packages_with_vdl_id": sum(1 for p in self.packages if p.vdl_id),
        }
