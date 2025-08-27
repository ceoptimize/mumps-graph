"""ZWR (Zoned Write) format parser for VistA global exports."""

import re
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

from src.models.nodes import FieldNode, FileNode, ParsedGlobal


class ZWRParser:
    """Parser for ZWR format global exports."""

    # Pattern for parsing global lines: ^GLOBAL(subscripts)=value
    GLOBAL_PATTERN = re.compile(r'^\^(\w+)\((.*?)\)="(.*)"$')

    def __init__(self):
        """Initialize the ZWR parser."""
        self.files: Dict[str, FileNode] = {}
        self.fields: List[FieldNode] = []
        self.current_line_number = 0

    def parse_line(self, line: str) -> Optional[ParsedGlobal]:
        """
        Parse a single ZWR line.

        Args:
            line: Raw line from ZWR file

        Returns:
            ParsedGlobal object or None if line doesn't match pattern
        """
        line = line.strip()
        if not line or line.startswith("GT.M") or line.startswith("ZWR"):
            return None

        match = self.GLOBAL_PATTERN.match(line)
        if not match:
            return None

        global_name = match.group(1)
        subscripts_str = match.group(2)
        value = match.group(3)

        # Parse subscripts
        subscripts = self.parse_subscripts(subscripts_str)

        # Unescape value
        value = self.unescape_value(value)

        return ParsedGlobal(
            global_name=global_name,
            subscripts=subscripts,
            value=value,
            raw_line=line,
        )

    def parse_subscripts(self, subscripts_str: str) -> List[str]:
        """
        Parse subscripts from a comma-separated string.

        Args:
            subscripts_str: Comma-separated subscripts

        Returns:
            List of subscript values
        """
        if not subscripts_str:
            return []

        subscripts = []
        current = ""
        in_quotes = False
        escape_next = False

        for char in subscripts_str:
            if escape_next:
                current += char
                escape_next = False
            elif char == "\\":
                escape_next = True
            elif char == '"':
                in_quotes = not in_quotes
                current += char
            elif char == "," and not in_quotes:
                subscripts.append(self.clean_subscript(current))
                current = ""
            else:
                current += char

        if current:
            subscripts.append(self.clean_subscript(current))

        return subscripts

    def clean_subscript(self, subscript: str) -> str:
        """Clean and normalize a subscript value."""
        subscript = subscript.strip()
        # Remove surrounding quotes if present
        if subscript.startswith('"') and subscript.endswith('"'):
            subscript = subscript[1:-1]
        return subscript

    def unescape_value(self, value: str) -> str:
        """
        Unescape special characters in ZWR values.

        Args:
            value: Escaped value from ZWR

        Returns:
            Unescaped value
        """
        # Handle doubled quotes (escaped quotes in ZWR)
        value = value.replace('""', '"')
        return value

    def extract_file_definitions(
        self, lines: List[str]
    ) -> Tuple[Dict[str, FileNode], List[FieldNode]]:
        """
        Extract file and field definitions from DD globals.

        Args:
            lines: List of ZWR lines

        Returns:
            Tuple of (files dict, fields list)
        """
        files = {}
        fields = []

        for line_num, line in enumerate(lines, 1):
            self.current_line_number = line_num
            parsed = self.parse_line(line)

            if not parsed or not parsed.is_dd_entry():
                continue

            if parsed.is_file_header():
                # Process file header: ^DD(file_num,0)="NAME^GLOBAL^..."
                file_node = self._process_file_header(parsed)
                if file_node:
                    files[file_node.number] = file_node

            elif parsed.is_field_definition():
                # Process field definition: ^DD(file_num,field_num,0)="NAME^TYPE^..."
                field_node = self._process_field_definition(parsed)
                if field_node:
                    fields.append(field_node)

        return files, fields

    def _process_file_header(self, parsed: ParsedGlobal) -> Optional[FileNode]:
        """Process a file header entry from DD."""
        file_number = parsed.subscripts[0]
        parts = parsed.value.split("^")

        if not parts:
            return None

        file_name = parts[0] if parts[0] else f"FILE_{file_number}"

        # Extract global root if present
        global_root = None
        if len(parts) > 1 and parts[1]:
            global_root = f"^{parts[1]}" if not parts[1].startswith("^") else parts[1]

        # Check if this is a subfile
        is_subfile = "SUB-FILE" in parsed.value.upper() or float(file_number) % 1 != 0

        return FileNode(
            number=file_number,
            name=file_name,
            global_root=global_root,
            is_subfile=is_subfile,
        )

    def _process_field_definition(self, parsed: ParsedGlobal) -> Optional[FieldNode]:
        """Process a field definition entry from DD."""
        if len(parsed.subscripts) < 3:
            return None

        file_number = parsed.subscripts[0]
        field_number = parsed.subscripts[1]

        # Skip non-field entries
        if field_number == "0" or field_number.startswith("B"):
            return None

        parts = parsed.value.split("^")
        if not parts:
            return None

        field_name = parts[0] if parts[0] else f"FIELD_{field_number}"

        # Determine data type
        data_type = "F"  # Default to Free Text
        is_pointer = False
        is_computed = False
        is_multiple = False
        target_file = None

        if len(parts) > 1:
            type_info = parts[1]
            if type_info:
                # First character is usually the type
                data_type = type_info[0].upper()

                # Check for special types
                if data_type == "P":
                    is_pointer = True
                    # Extract target file from pointer definition
                    if len(type_info) > 1:
                        target_match = re.search(r"P(\d+)", type_info)
                        if target_match:
                            target_file = target_match.group(1)
                elif data_type == "C":
                    is_computed = True
                elif type_info.startswith("M"):
                    is_multiple = True
                    data_type = "M"

        # Check if field is required (usually in parts[2])
        required = False
        if len(parts) > 2 and parts[2]:
            required = "R" in parts[2].upper()

        return FieldNode(
            number=field_number,
            name=field_name,
            file_number=file_number,
            data_type=data_type,
            required=required,
            is_pointer=is_pointer,
            is_computed=is_computed,
            is_multiple=is_multiple,
            target_file=target_file,
        )

    def parse_file(self, file_path: Path) -> Tuple[Dict[str, FileNode], List[FieldNode]]:
        """
        Parse a complete ZWR file.

        Args:
            file_path: Path to ZWR file

        Returns:
            Tuple of (files dict, fields list)
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        return self.extract_file_definitions(lines)

    def stream_parse_file(
        self, file_path: Path
    ) -> Generator[ParsedGlobal, None, None]:
        """
        Stream parse a ZWR file line by line.

        Args:
            file_path: Path to ZWR file

        Yields:
            ParsedGlobal objects
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line_num, line in enumerate(f, 1):
                self.current_line_number = line_num
                parsed = self.parse_line(line)
                if parsed:
                    yield parsed

    def get_statistics(self) -> Dict[str, Any]:
        """Get parsing statistics."""
        return {
            "total_files": len(self.files),
            "total_fields": len(self.fields),
            "lines_processed": self.current_line_number,
            "subfiles_count": sum(1 for f in self.files.values() if f.is_subfile),
            "pointer_fields_count": sum(1 for f in self.fields if f.is_pointer),
            "computed_fields_count": sum(1 for f in self.fields if f.is_computed),
            "required_fields_count": sum(1 for f in self.fields if f.required),
        }
