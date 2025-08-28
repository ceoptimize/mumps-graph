"""Relationship definitions for graph database."""

from enum import Enum
from typing import Any, Dict

from pydantic import BaseModel, Field


class RelationshipType(Enum):
    """Types of relationships in the graph."""

    CONTAINS_FILE = "CONTAINS_FILE"
    CONTAINS_FIELD = "CONTAINS_FIELD"
    POINTS_TO = "POINTS_TO"
    COMPUTED_FROM = "COMPUTED_FROM"
    SUBFILE_OF = "SUBFILE_OF"
    BELONGS_TO_PACKAGE = "BELONGS_TO_PACKAGE"
    INDEXED_BY = "INDEXED_BY"
    VARIABLE_POINTER = "VARIABLE_POINTER"


class Relationship(BaseModel):
    """Base relationship model."""

    relationship_type: RelationshipType
    from_id: str
    to_id: str
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_cypher_props(self) -> Dict[str, Any]:
        """Convert to properties for Cypher query."""
        return {
            "confidence": self.confidence,
            **self.metadata,
        }


class ContainsFileRel(Relationship):
    """Package contains File relationship."""

    relationship_type: RelationshipType = RelationshipType.CONTAINS_FILE

    def __init__(self, package_id: str, file_id: str, confidence: float = 1.0):
        super().__init__(
            from_id=package_id,
            to_id=file_id,
            confidence=confidence,
        )


class ContainsFieldRel(Relationship):
    """File contains Field relationship."""

    relationship_type: RelationshipType = RelationshipType.CONTAINS_FIELD

    def __init__(self, file_id: str, field_id: str, field_number: str):
        super().__init__(
            from_id=file_id,
            to_id=field_id,
            metadata={"field_number": field_number},
        )


class PointsToRel(Relationship):
    """Field points to File relationship (for pointer fields)."""

    relationship_type: RelationshipType = RelationshipType.POINTS_TO

    def __init__(
        self, field_id: str, target_file_id: str, confidence: float = 1.0
    ):
        super().__init__(
            from_id=field_id,
            to_id=target_file_id,
            confidence=confidence,
        )


class ComputedFromRel(Relationship):
    """Computed field references other fields."""

    relationship_type: RelationshipType = RelationshipType.COMPUTED_FROM

    def __init__(
        self,
        computed_field_id: str,
        source_field_id: str,
        confidence: float = 0.8,
    ):
        super().__init__(
            from_id=computed_field_id,
            to_id=source_field_id,
            confidence=confidence,
        )


class SubfileOfRel(Relationship):
    """Subfile relationship to parent file with enhanced metadata."""

    relationship_type: RelationshipType = RelationshipType.SUBFILE_OF

    def __init__(
        self,
        subfile_id: str,
        parent_file_id: str,
        parent_field: str,
        level: int = 1,
    ):
        super().__init__(
            from_id=subfile_id,
            to_id=parent_file_id,
            confidence=1.0,
            metadata={
                "parent_field": parent_field,
                "level": level,
            },
        )


class IndexedByRel(Relationship):
    """Field INDEXED_BY CrossReference relationship."""

    relationship_type: RelationshipType = RelationshipType.INDEXED_BY

    def __init__(
        self,
        field_id: str,
        xref_id: str,
        xref_name: str,
        xref_type: str,
        set_condition: str = None,
        kill_condition: str = None,
    ):
        metadata = {
            "xref_name": xref_name,
            "xref_type": xref_type,
        }
        if set_condition:
            metadata["set_condition"] = set_condition
        if kill_condition:
            metadata["kill_condition"] = kill_condition

        super().__init__(
            from_id=field_id,
            to_id=xref_id,
            confidence=1.0,
            metadata=metadata,
        )


class VariablePointerRel(Relationship):
    """Variable pointer can point to multiple files."""

    relationship_type: RelationshipType = RelationshipType.VARIABLE_POINTER

    def __init__(
        self,
        field_id: str,
        target_file_id: str,
        target_file: str,
        target_global: str,
        target_description: str = None,
        v_number: str = None,
    ):
        metadata = {
            "target_file": target_file,
            "target_global": target_global,
        }
        if target_description:
            metadata["target_description"] = target_description
        if v_number:
            metadata["v_number"] = v_number

        super().__init__(
            from_id=field_id,
            to_id=target_file_id,
            confidence=1.0,
            metadata=metadata,
        )
