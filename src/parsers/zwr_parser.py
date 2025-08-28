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
        self.file_names: Dict[str, str] = {}  # Maps file number to actual name
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

        # First pass: collect file names from NM entries
        for line_num, line in enumerate(lines, 1):
            self.current_line_number = line_num
            parsed = self.parse_line(line)

            if not parsed or not parsed.is_dd_entry():
                continue

            # Look for file name entries: ^DD(file_num,0,"NM","NAME")=""
            if (len(parsed.subscripts) >= 4 and 
                parsed.subscripts[1] == "0" and 
                parsed.subscripts[2] == "NM"):
                file_number = parsed.subscripts[0]
                file_name = parsed.subscripts[3]
                self.file_names[file_number] = file_name

        # Second pass: process files and fields
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

        # Update internal state for statistics
        self.files = files
        self.fields = fields
        
        return files, fields

    def _process_file_header(self, parsed: ParsedGlobal) -> Optional[FileNode]:
        """Process a file header entry from DD."""
        file_number = parsed.subscripts[0]
        parts = parsed.value.split("^")

        if not parts:
            return None

        # Use the actual name from NM entries if available, otherwise use header name
        if file_number in self.file_names:
            file_name = self.file_names[file_number]
        elif parts[0] and parts[0] not in ["FIELD", "SUB-FIELD"]:
            # Use the name from header if it's not a generic term
            file_name = parts[0]
        else:
            file_name = f"FILE_{file_number}"

        # Global root will be extracted from DIC entries later
        global_root = None

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
                # Handle complex pointer types (*P format)
                if type_info.startswith("*P") or "P" in type_info[:3]:
                    is_pointer = True
                    data_type = "P"
                    # Extract target file from pointer definition
                    target_match = re.search(r"P(\d+)", type_info)
                    if target_match:
                        target_file = target_match.group(1)
                # Handle required fields with type info (RF, RN, RD, etc.)
                elif type_info.startswith("R") and len(type_info) > 1:
                    # R followed by actual type (F, N, D, etc.)
                    if len(type_info) > 1 and type_info[1] in "FNDSPWVCMK":
                        data_type = type_info[1].upper()
                    else:
                        data_type = "R"  # Just required, no specific type
                # Handle computed fields
                elif type_info.startswith("C"):
                    is_computed = True
                    data_type = "C"
                # Handle multiple fields
                elif type_info.startswith("M"):
                    is_multiple = True
                    data_type = "M"
                # Standard types
                else:
                    # First character is usually the type
                    first_char = type_info[0].upper()
                    if first_char in "FNDSPWVCMK":
                        data_type = first_char

        # Check if field is required (R prefix in type info or R in parts[2])
        required = False
        if len(parts) > 1 and parts[1]:
            # Required if type starts with R (RF, RN, RD, etc.)
            required = parts[1].startswith("R")
        # Also check parts[2] for additional required flag
        if not required and len(parts) > 2 and parts[2]:
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
    
    def parse_dic_file(self, file_path: Path, files: Dict[str, FileNode]):
        """
        Parse DIC file to extract global roots.
        
        Args:
            file_path: Path to FILE.zwr (DIC entries)
            files: Dictionary of FileNode objects to update
        """
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                parsed = self.parse_line(line)
                if not parsed:
                    continue
                    
                # Look for DIC global root entries: ^DIC(file_num,0,"GL")="^GLOBAL("
                if (parsed.global_name == "DIC" and 
                    len(parsed.subscripts) == 3 and 
                    parsed.subscripts[1] == "0" and 
                    parsed.subscripts[2] == "GL"):
                    
                    file_number = parsed.subscripts[0]
                    if file_number in files:
                        # Clean up the global root value
                        global_root = parsed.value
                        if not global_root.startswith("^"):
                            global_root = "^" + global_root
                        files[file_number].global_root = global_root

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
