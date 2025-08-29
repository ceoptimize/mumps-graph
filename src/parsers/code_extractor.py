"""Extract code relationships from MUMPS routines."""

import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.graph.node_cache import NodeLookupCache

logger = logging.getLogger(__name__)


class CodeRelationshipExtractor:
    """Extract relationships from MUMPS code with node resolution."""

    def __init__(self, node_cache: NodeLookupCache):
        """
        Initialize the code relationship extractor.

        Args:
            node_cache: Node lookup cache for resolving references
        """
        self.node_cache = node_cache

        # Patterns for MUMPS commands
        self.DO_PATTERN = re.compile(
            r"^\s+D(?:O)?\s+"  # DO or D command
            r"([A-Z][A-Z0-9]*)"  # Label name
            r"(?:\^([A-Z][A-Z0-9]*))?"  # Optional routine
            r"(?:\((.*?)\))?",  # Optional parameters
            re.IGNORECASE,
        )

        self.GOTO_PATTERN = re.compile(
            r"^\s+G(?:OTO)?\s+"  # GOTO or G command
            r"([A-Z][A-Z0-9]*)"  # Label name
            r"(?:\^([A-Z][A-Z0-9]*))?",  # Optional routine
            re.IGNORECASE,
        )

        self.JOB_PATTERN = re.compile(
            r"^\s+J(?:OB)?\s+"  # JOB or J command
            r"([A-Z][A-Z0-9]*)"  # Label name
            r"(?:\^([A-Z][A-Z0-9]*))?",  # Optional routine
            re.IGNORECASE,
        )

        self.FUNCTION_PATTERN = re.compile(
            r"\$\$"  # Function indicator
            r"([A-Z][A-Z0-9]*)"  # Function name
            r"(?:\^([A-Z][A-Z0-9]*))?"  # Optional routine
            r"(?:\((.*?)\))?",  # Optional parameters
            re.IGNORECASE,
        )

        # Pattern for global access - more permissive
        self.GLOBAL_ACCESS_PATTERN = re.compile(
            r"\^([A-Z][A-Z0-9]*)"  # Global name
            r"(?:\((.*?)\))?",  # Optional subscripts
            re.IGNORECASE,
        )

        # Pattern for SET command assignment
        self.SET_PATTERN = re.compile(
            r"^\s+S(?:ET)?\s+",  # SET or S command
            re.IGNORECASE,
        )

        # Pattern for KILL command
        self.KILL_PATTERN = re.compile(
            r"^\s+K(?:ILL)?\s+",  # KILL or K command
            re.IGNORECASE,
        )

    def extract_calls_from_routine(
        self, routine_path: Path
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Extract all call relationships from a routine with source label resolution.

        Args:
            routine_path: Path to the MUMPS routine file

        Returns:
            Tuple of (calls, unresolved_calls, orphan_calls)
        """
        calls = []
        unresolved_calls = []
        orphan_calls = []  # Calls where source label isn't found
        routine_name = routine_path.stem.upper()

        try:
            with open(routine_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read routine {routine_path}: {e}")
            return calls, unresolved_calls, orphan_calls

        current_label = None
        current_label_id = None

        for line_num, line in enumerate(lines, 1):
            # Track current label context
            if line and line[0] not in " \t;":  # New label
                label_match = re.match(r"^([A-Z][A-Z0-9]*)", line, re.IGNORECASE)
                if label_match:
                    current_label = label_match.group(1).upper()
                    current_label_id = self.node_cache.resolve_label(routine_name, current_label)

            # Skip if we don't have a current label context
            if not current_label:
                continue

            # Extract DO calls
            do_match = self.DO_PATTERN.match(line)
            if do_match:
                target_label = do_match.group(1).upper()
                target_routine = do_match.group(2).upper() if do_match.group(2) else routine_name

                call_info = {
                    "source_label_id": current_label_id,
                    "source_label": current_label,
                    "source_routine": routine_name,
                    "target_label": target_label,
                    "target_routine": target_routine,
                    "line_number": line_num,
                    "call_type": "DO",
                }

                # Resolve target
                target_id = self.node_cache.resolve_label(target_routine, target_label)

                if current_label_id and target_id:
                    call_info["target_label_id"] = target_id
                    calls.append(call_info)
                elif current_label_id:
                    unresolved_calls.append(call_info)
                else:
                    orphan_calls.append(call_info)

            # Extract GOTO calls
            goto_match = self.GOTO_PATTERN.match(line)
            if goto_match:
                target_label = goto_match.group(1).upper()
                target_routine = (
                    goto_match.group(2).upper() if goto_match.group(2) else routine_name
                )

                call_info = {
                    "source_label_id": current_label_id,
                    "source_label": current_label,
                    "source_routine": routine_name,
                    "target_label": target_label,
                    "target_routine": target_routine,
                    "line_number": line_num,
                    "call_type": "GOTO",
                }

                # Resolve target
                target_id = self.node_cache.resolve_label(target_routine, target_label)

                if current_label_id and target_id:
                    call_info["target_label_id"] = target_id
                    calls.append(call_info)
                elif current_label_id:
                    unresolved_calls.append(call_info)
                else:
                    orphan_calls.append(call_info)

            # Extract JOB calls
            job_match = self.JOB_PATTERN.match(line)
            if job_match:
                target_label = job_match.group(1).upper()
                target_routine = job_match.group(2).upper() if job_match.group(2) else routine_name

                call_info = {
                    "source_label_id": current_label_id,
                    "source_label": current_label,
                    "source_routine": routine_name,
                    "target_label": target_label,
                    "target_routine": target_routine,
                    "line_number": line_num,
                    "call_type": "JOB",
                }

                # Resolve target
                target_id = self.node_cache.resolve_label(target_routine, target_label)

                if current_label_id and target_id:
                    call_info["target_label_id"] = target_id
                    calls.append(call_info)
                elif current_label_id:
                    unresolved_calls.append(call_info)
                else:
                    orphan_calls.append(call_info)

        return calls, unresolved_calls, orphan_calls

    def extract_invokes_from_routine(
        self, routine_path: Path
    ) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Extract function invocations from a routine.

        Args:
            routine_path: Path to the MUMPS routine file

        Returns:
            Tuple of (invokes, unresolved_invokes, orphan_invokes)
        """
        invokes = []
        unresolved_invokes = []
        orphan_invokes = []
        routine_name = routine_path.stem.upper()

        try:
            with open(routine_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read routine {routine_path}: {e}")
            return invokes, unresolved_invokes, orphan_invokes

        current_label = None
        current_label_id = None

        for line_num, line in enumerate(lines, 1):
            # Track current label context
            if line and line[0] not in " \t;":  # New label
                label_match = re.match(r"^([A-Z][A-Z0-9]*)", line, re.IGNORECASE)
                if label_match:
                    current_label = label_match.group(1).upper()
                    current_label_id = self.node_cache.resolve_label(routine_name, current_label)

            # Skip if we don't have a current label context
            if not current_label:
                continue

            # Find all function calls in the line
            for func_match in self.FUNCTION_PATTERN.finditer(line):
                target_label = func_match.group(1).upper()
                target_routine = (
                    func_match.group(2).upper() if func_match.group(2) else routine_name
                )

                # Try to extract assignment variable
                assigns_to = None
                before_func = line[: func_match.start()]
                set_match = re.search(
                    r"S(?:ET)?\s+([A-Z][A-Z0-9]*)\s*=\s*$", before_func, re.IGNORECASE
                )
                if set_match:
                    assigns_to = set_match.group(1).upper()

                invoke_info = {
                    "source_label_id": current_label_id,
                    "source_label": current_label,
                    "source_routine": routine_name,
                    "target_label": target_label,
                    "target_routine": target_routine,
                    "line_number": line_num,
                    "assigns_to": assigns_to,
                }

                # Resolve target
                target_id = self.node_cache.resolve_label(target_routine, target_label)

                if current_label_id and target_id:
                    invoke_info["target_label_id"] = target_id
                    invokes.append(invoke_info)
                elif current_label_id:
                    unresolved_invokes.append(invoke_info)
                else:
                    orphan_invokes.append(invoke_info)

        return invokes, unresolved_invokes, orphan_invokes

    def extract_accesses_from_routine(self, routine_path: Path) -> Tuple[List[Dict], List[Dict]]:
        """
        Extract global access patterns from a routine.

        Args:
            routine_path: Path to the MUMPS routine file

        Returns:
            Tuple of (accesses, orphan_accesses)
        """
        accesses = []
        orphan_accesses = []  # Accesses where source label isn't found
        routine_name = routine_path.stem.upper()

        try:
            with open(routine_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read routine {routine_path}: {e}")
            return accesses, orphan_accesses

        current_label = None
        current_label_id = None

        for line_num, line in enumerate(lines, 1):
            # Track current label context
            if line and line[0] not in " \t;":  # New label
                label_match = re.match(r"^([A-Z][A-Z0-9]*)", line, re.IGNORECASE)
                if label_match:
                    current_label = label_match.group(1).upper()
                    current_label_id = self.node_cache.resolve_label(routine_name, current_label)

            # Skip if we don't have a current label context
            if not current_label:
                continue

            # Find all global references in the line
            for global_match in self.GLOBAL_ACCESS_PATTERN.finditer(line):
                global_name = global_match.group(1).upper()
                subscripts = global_match.group(2) if global_match.group(2) else ""
                pattern = f"^{global_name}({subscripts})" if subscripts else f"^{global_name}"

                # Determine access type
                access_type = self.determine_access_type(line, global_match.start())

                # Resolve global
                global_id = self.node_cache.resolve_global(global_name)

                if current_label_id and global_id:
                    access_info = {
                        "label_id": current_label_id,
                        "global_id": global_id,
                        "label_name": current_label,
                        "routine_name": routine_name,
                        "global_name": global_name,
                        "line_number": line_num,
                        "access_type": access_type,
                        "pattern": pattern,
                    }
                    accesses.append(access_info)
                elif current_label_id:
                    # Global not found - we'll create it later
                    orphan_access = {
                        "label_id": current_label_id,
                        "label_name": current_label,
                        "routine_name": routine_name,
                        "global_name": global_name,
                        "line_number": line_num,
                        "access_type": access_type,
                        "pattern": pattern,
                    }
                    orphan_accesses.append(orphan_access)

        return accesses, orphan_accesses

    def determine_access_type(self, line: str, global_pos: int) -> str:
        """
        Determine if global access is READ, WRITE, KILL, or EXISTS.

        Args:
            line: The complete line containing the global reference
            global_pos: Position of the global reference in the line

        Returns:
            Access type string
        """
        # Get the part of the line before the global reference
        before_global = line[:global_pos] if global_pos > 0 else ""

        # Check for KILL command
        if self.KILL_PATTERN.match(line):
            return "KILL"

        # Check for SET (write) - look for = after the global
        after_global = line[global_pos:]
        if self.SET_PATTERN.match(line) and "=" in after_global:
            # Make sure the = is for this global, not something else
            equal_pos = after_global.find("=")
            # Check if there's another global or command before the =
            if not re.search(r"[,\s]\s*\^", after_global[:equal_pos]):
                return "WRITE"

        # Check for $DATA existence check
        if re.search(r"\$D(?:ATA)?\s*\(", before_global, re.IGNORECASE):
            return "EXISTS"

        # Check for $ORDER, $NEXT
        if re.search(r"\$O(?:RDER)?\s*\(", before_global, re.IGNORECASE):
            return "READ"
        if re.search(r"\$N(?:EXT)?\s*\(", before_global, re.IGNORECASE):
            return "READ"

        # Default to READ
        return "READ"

    def extract_falls_through_relationships(self, routine_path: Path) -> List[Dict]:
        """
        Extract FALLS_THROUGH relationships between consecutive labels.

        Args:
            routine_path: Path to the MUMPS routine file

        Returns:
            List of falls_through relationships
        """
        falls_through = []
        routine_name = routine_path.stem.upper()

        # Get all labels in this routine ordered by line number
        labels_in_routine = []

        try:
            with open(routine_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception as e:
            logger.error(f"Failed to read routine {routine_path}: {e}")
            return falls_through

        # Find all labels and their positions
        for line_num, line in enumerate(lines, 1):
            if line and line[0] not in " \t;":  # New label
                label_match = re.match(r"^([A-Z][A-Z0-9]*)", line, re.IGNORECASE)
                if label_match:
                    label_name = label_match.group(1).upper()
                    label_id = self.node_cache.resolve_label(routine_name, label_name)
                    if label_id:
                        labels_in_routine.append(
                            {
                                "label_name": label_name,
                                "label_id": label_id,
                                "line_number": line_num,
                            }
                        )

        # Create FALLS_THROUGH relationships between consecutive labels
        for i in range(len(labels_in_routine) - 1):
            current = labels_in_routine[i]
            next_label = labels_in_routine[i + 1]

            # Check if there's an explicit QUIT or GOTO before the next label
            has_explicit_exit = False
            for line_num in range(current["line_number"], next_label["line_number"]):
                if line_num <= len(lines):
                    line = lines[line_num - 1]
                    # Check for QUIT or GOTO at the end of current label
                    if re.match(r"^\s+Q(?:UIT)?(?:\s|$)", line, re.IGNORECASE):
                        has_explicit_exit = True
                        break
                    if self.GOTO_PATTERN.match(line):
                        has_explicit_exit = True
                        break

            # Create FALLS_THROUGH if no explicit exit
            if not has_explicit_exit:
                falls_through.append(
                    {
                        "from_label_id": current["label_id"],
                        "to_label_id": next_label["label_id"],
                        "from_label": current["label_name"],
                        "to_label": next_label["label_name"],
                        "routine_name": routine_name,
                        "confidence": 0.9 if not has_explicit_exit else 0.5,
                    }
                )

        return falls_through

    def extract_all_globals_from_code(self, packages_dir: Path) -> Dict[str, Optional[str]]:
        """
        Extract all unique globals from MUMPS code.

        Args:
            packages_dir: Path to the Packages directory

        Returns:
            Dictionary of {global_name: file_number or None}
        """
        globals_found = {}

        # Process all routine files
        for routine_file in packages_dir.glob("*/Routines/*.m"):
            try:
                with open(routine_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                # Find all global references
                for match in self.GLOBAL_ACCESS_PATTERN.finditer(content):
                    global_name = match.group(1).upper()
                    if global_name not in globals_found:
                        # Try to associate with a file if possible
                        file_info = self.node_cache.resolve_file_by_global(global_name)
                        globals_found[global_name] = file_info[0] if file_info else None

            except Exception as e:
                logger.error(f"Failed to process {routine_file}: {e}")

        return globals_found
