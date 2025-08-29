"""Pydantic models for graph nodes."""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class PackageNode(BaseModel):
    """Package organizational unit from Packages.csv."""

    package_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    directory: str
    prefixes: List[str] = Field(default_factory=list)
    vdl_id: Optional[str] = None
    files_low: Optional[str] = None
    files_high: Optional[str] = None
    file_numbers: List[str] = Field(default_factory=list)  # Individual file numbers

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "package_id": self.package_id,
            "name": self.name,
            "directory": self.directory,
            "prefixes": self.prefixes,
            "vdl_id": self.vdl_id,
            "files_low": self.files_low,
            "files_high": self.files_high,
            "file_numbers": self.file_numbers,
        }


class FileNode(BaseModel):
    """File/Table definition from DD."""

    file_id: str = Field(default_factory=lambda: str(uuid4()))
    number: str  # e.g., "2" for PATIENT file
    name: str  # e.g., "PATIENT"
    global_root: Optional[str] = None  # e.g., "^DPT"
    parent_file: Optional[str] = None  # For subfiles
    is_subfile: bool = False
    description: Optional[str] = None
    last_modified: Optional[str] = None
    version: Optional[str] = None

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "file_id": self.file_id,
            "number": self.number,
            "name": self.name,
            "global_root": self.global_root,
            "parent_file": self.parent_file,
            "is_subfile": self.is_subfile,
            "description": self.description,
            "last_modified": self.last_modified,
            "version": self.version,
        }


class FieldNode(BaseModel):
    """Field definition within a file."""

    field_id: str = Field(default_factory=lambda: str(uuid4()))
    number: str  # e.g., ".01"
    name: str  # e.g., "NAME"
    file_number: str  # Parent file number
    data_type: str  # F, N, D, P, S, C, W, V
    required: bool = False
    is_pointer: bool = False
    is_computed: bool = False
    is_multiple: bool = False
    target_file: Optional[str] = None  # For pointer fields
    mumps_code: Optional[str] = None  # For computed fields
    description: Optional[str] = None
    help_text: Optional[str] = None

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "field_id": self.field_id,
            "number": self.number,
            "name": self.name,
            "file_number": self.file_number,
            "data_type": self.data_type,
            "required": self.required,
            "is_pointer": self.is_pointer,
            "is_computed": self.is_computed,
            "is_multiple": self.is_multiple,
            "target_file": self.target_file,
            "mumps_code": self.mumps_code,
            "description": self.description,
            "help_text": self.help_text,
        }


class ParsedGlobal(BaseModel):
    """Parsed global line from ZWR file."""

    global_name: str
    subscripts: List[str]
    value: str
    raw_line: str

    def is_dd_entry(self) -> bool:
        """Check if this is a DD (Data Dictionary) entry."""
        return self.global_name == "DD"

    def is_file_header(self) -> bool:
        """Check if this is a file header entry (^DD(file_num,0))."""
        return self.is_dd_entry() and len(self.subscripts) == 2 and self.subscripts[1] == "0"

    def is_field_definition(self) -> bool:
        """Check if this is a field definition entry."""
        return self.is_dd_entry() and len(self.subscripts) >= 3 and self.subscripts[2] == "0"


DATA_TYPE_MAP = {
    "F": "Free Text",
    "N": "Numeric",
    "D": "Date/Time",
    "P": "Pointer",
    "S": "Set of Codes",
    "C": "Computed",
    "W": "Word Processing",
    "V": "Variable Pointer",
    "K": "MUMPS",
    "M": "Multiple",
}


class CrossReferenceNode(BaseModel):
    """Cross-reference/index definition from DD."""

    xref_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # XRef name (e.g., "B", "AVAFC391")
    file_number: str  # File containing the xref
    field_number: str  # Field being indexed
    xref_type: str  # "regular", "trigger", "new-style", "MUMPS"
    xref_number: str  # XRef number in DD
    set_logic: Optional[str] = None
    kill_logic: Optional[str] = None
    execution: str = "field"  # "field", "record", "global"
    description: Optional[str] = None

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "xref_id": self.xref_id,
            "name": self.name,
            "file_number": self.file_number,
            "field_number": self.field_number,
            "xref_type": self.xref_type,
            "xref_number": self.xref_number,
            "set_logic": self.set_logic,
            "kill_logic": self.kill_logic,
            "execution": self.execution,
            "description": self.description,
        }


class SubfileNode(FileNode):
    """Subfile is a special type of File with parent relationship."""

    parent_file_number: str  # Parent file number
    parent_field_number: str  # Multiple field that contains this subfile
    nesting_level: int = 1  # How deep in the hierarchy

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        base_dict = super().dict_for_neo4j()
        base_dict.update(
            {
                "parent_file_number": self.parent_file_number,
                "parent_field_number": self.parent_field_number,
                "nesting_level": self.nesting_level,
                "is_subfile": True,  # Ensure this is set
            }
        )
        return base_dict


class RoutineNode(BaseModel):
    """MUMPS routine file representation."""

    routine_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g., "DG10"
    package_name: Optional[str] = None  # e.g., "Registration"
    prefix: Optional[str] = None  # e.g., "DG"
    path: str  # Full file path
    lines_of_code: int = 0
    last_modified: Optional[str] = None
    version: Optional[str] = None
    patches: List[str] = Field(default_factory=list)  # Extracted from header
    description: Optional[str] = None  # From header comments

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "routine_id": self.routine_id,
            "name": self.name,
            "package_name": self.package_name,
            "prefix": self.prefix,
            "path": self.path,
            "lines_of_code": self.lines_of_code,
            "last_modified": self.last_modified,
            "version": self.version,
            "patches": self.patches,
            "description": self.description,
        }


class LabelNode(BaseModel):
    """Label/entry point within a MUMPS routine."""

    label_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g., "PROCESS"
    routine_name: str  # Parent routine
    line_number: int
    is_entry_point: bool = False  # Called from other routines
    is_function: bool = False  # Returns value (QUIT with value)
    parameters: List[str] = Field(default_factory=list)  # If determinable
    comment: Optional[str] = None  # Adjacent comment

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "label_id": self.label_id,
            "name": self.name,
            "routine_name": self.routine_name,
            "line_number": self.line_number,
            "is_entry_point": self.is_entry_point,
            "is_function": self.is_function,
            "parameters": self.parameters,
            "comment": self.comment,
        }


class GlobalNode(BaseModel):
    """Global storage location in VistA."""

    global_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g., "DPT" (without ^)
    type: str = "data"  # "data", "index", "temp"
    file_number: Optional[str] = None  # Associated file if known
    description: Optional[str] = None

    def dict_for_neo4j(self) -> Dict[str, Any]:
        """Convert to dict for Neo4j node creation."""
        return {
            "global_id": self.global_id,
            "name": self.name,
            "type": self.type,
            "file_number": self.file_number,
            "description": self.description,
        }
