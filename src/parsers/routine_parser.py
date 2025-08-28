"""Custom Python parser for MUMPS routine files."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rich.console import Console

from src.models.nodes import LabelNode, RoutineNode

console = Console()


class RoutineParser:
    """Parser for MUMPS routine files to extract labels and structure."""

    # Pattern to match labels (start at column 1, alphanumeric)
    # Examples: START, A1, EN(DFN,TYPE), FUNC()
    LABEL_PATTERN = re.compile(
        r'^([A-Z][A-Z0-9]*)'  # Label name
        r'(?:\(([^)]*)\))?'  # Optional parameters
        r'(?:\s+[^;].*)?'  # Optional code on same line
        r'(?:\s*;(.*))?'  # Optional comment
    )

    # Pattern to extract routine metadata from header
    HEADER_PATTERN = re.compile(
        r';;([\d.]+);.*?\*\*([^*]+)\*\*'  # Version and patches
    )

    # Entry point indicators (heuristics)
    ENTRY_POINT_INDICATORS = ['EN', 'EP', 'START', 'INIT', 'BEGIN']

    # Pattern to detect functions (QUIT with value)
    FUNCTION_PATTERN = re.compile(
        r'\sQ(?:UIT)?\s+\$\$',  # QUIT $$VALUE
        re.IGNORECASE
    )

    def parse_directory(
        self, dir_path: Path, package_name: Optional[str] = None
    ) -> Tuple[List[RoutineNode], List[LabelNode]]:
        """Parse all routine files in a directory.

        Args:
            dir_path: Path to directory containing .m files
            package_name: Optional package name

        Returns:
            Tuple of (routines, labels)
        """
        routines = []
        all_labels = []

        # Find all .m files
        m_files = list(dir_path.glob("*.m"))

        for file_path in m_files:
            try:
                routine, labels = self.process_routine_file(file_path, package_name)
                if routine:
                    routines.append(routine)
                    all_labels.extend(labels)
            except Exception as e:
                console.print(f"[red]Error parsing {file_path}: {e}[/red]")

        return routines, all_labels

    def process_routine_file(
        self, file_path: Path, package_name: Optional[str] = None
    ) -> Tuple[Optional[RoutineNode], List[LabelNode]]:
        """Process a single routine file.

        Args:
            file_path: Path to .m file
            package_name: Optional package name

        Returns:
            Tuple of (routine_node, label_nodes)
        """
        labels = []

        # Extract routine name from filename
        routine_name = file_path.stem

        # Try to extract prefix (first 2-4 alpha chars)
        prefix = None
        if routine_name:
            match = re.match(r'^([A-Z]+)', routine_name)
            if match:
                prefix = match.group(1)[:4]  # Max 4 chars for prefix

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception as e:
            console.print(f"[yellow]Could not read {file_path}: {e}[/yellow]")
            return None, []

        # Create routine node
        routine = RoutineNode(
            name=routine_name,
            package_name=package_name,
            prefix=prefix,
            path=str(file_path),
            lines_of_code=len(lines)
        )

        # Extract metadata from header if present
        if lines:
            header_info = self._extract_header_info(lines[:5])
            if header_info:
                routine.version = header_info.get('version')
                routine.patches = header_info.get('patches', [])
                routine.description = header_info.get('description')

        # Parse labels
        for line_num, line in enumerate(lines, 1):
            label_data = self._extract_label(line, line_num)
            if label_data:
                label = LabelNode(
                    name=label_data['name'],
                    routine_name=routine_name,
                    line_number=line_num,
                    parameters=label_data.get('parameters', []),
                    comment=label_data.get('comment'),
                    is_entry_point=self._is_entry_point(label_data['name']),
                    is_function=False  # Will be determined by analyzing code after label
                )

                # Check if this is a function by looking ahead
                if self._is_function(lines, line_num):
                    label.is_function = True

                labels.append(label)

        return routine, labels

    def _extract_header_info(self, header_lines: List[str]) -> Optional[Dict]:
        """Extract metadata from routine header comments.

        Args:
            header_lines: First few lines of the file

        Returns:
            Dict with version, patches, description
        """
        info = {}

        for line in header_lines:
            # Look for version/patch info
            match = self.HEADER_PATTERN.search(line)
            if match:
                version_str = match.group(1)
                patch_str = match.group(2)

                info['version'] = version_str
                patches = [p.strip() for p in patch_str.split(',')]
                info['patches'] = patches

            # Extract description from first comment line
            if line.startswith(';') and 'description' not in info:
                desc = line[1:].strip()
                if desc and not desc.startswith(';') and not desc.startswith('**'):
                    info['description'] = desc

        return info if info else None

    def _extract_label(self, line: str, line_num: int) -> Optional[Dict]:
        """Extract label information from a line.

        Args:
            line: Line of code
            line_num: Line number

        Returns:
            Dict with label info or None
        """
        # Labels must start at column 1 (no leading spaces)
        if not line or line[0] == ' ' or line[0] == '\t' or line[0] == ';':
            return None

        # Try to match label pattern
        match = self.LABEL_PATTERN.match(line)
        if match:
            label_name = match.group(1)
            params_str = match.group(2)
            comment = match.group(3)

            # Parse parameters if present
            parameters = []
            if params_str:
                parameters = [p.strip() for p in params_str.split(',')]

            return {
                'name': label_name,
                'parameters': parameters,
                'comment': comment.strip() if comment else None
            }

        return None

    def _is_entry_point(self, label_name: str) -> bool:
        """Determine if a label is likely an entry point.

        Args:
            label_name: Name of the label

        Returns:
            True if likely an entry point
        """
        # Check if label starts with known entry point indicators
        for indicator in self.ENTRY_POINT_INDICATORS:
            if label_name.startswith(indicator):
                return True

        # Main entry points often have short names like A, A1, etc.
        if len(label_name) <= 2:
            return True

        return False

    def _is_function(self, lines: List[str], label_line_num: int) -> bool:
        """Determine if a label is a function by checking for QUIT with value.

        Args:
            lines: All lines in the file
            label_line_num: Line number of the label

        Returns:
            True if the label appears to be a function
        """
        # Look ahead up to 20 lines for a QUIT with value
        max_look_ahead = min(label_line_num + 20, len(lines))

        for i in range(label_line_num, max_look_ahead):
            line = lines[i]

            # Stop at next label
            if i > label_line_num and line and line[0] not in ' \t;':
                break

            # Check for QUIT with value pattern
            if self.FUNCTION_PATTERN.search(line):
                return True

            # Also check for explicit QUIT value patterns
            if re.search(r'\sQ(?:UIT)?\s+\w+', line, re.IGNORECASE):
                # But not just QUIT (with no value)
                if not re.search(r'\sQ(?:UIT)?\s*$', line, re.IGNORECASE):
                    return True

        return False

    def extract_labels_from_content(
        self, content: str, routine_name: str
    ) -> List[LabelNode]:
        """Extract labels from routine content string.

        Args:
            content: MUMPS routine content
            routine_name: Name of the routine

        Returns:
            List of LabelNode objects
        """
        labels = []
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            label_data = self._extract_label(line, line_num)
            if label_data:
                label = LabelNode(
                    name=label_data['name'],
                    routine_name=routine_name,
                    line_number=line_num,
                    parameters=label_data.get('parameters', []),
                    comment=label_data.get('comment'),
                    is_entry_point=self._is_entry_point(label_data['name']),
                    is_function=self._is_function(lines, line_num - 1)  # 0-indexed for list
                )
                labels.append(label)

        return labels
