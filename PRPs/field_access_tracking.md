name: "Field-Level Reference Tracking for VistA MUMPS - Enhanced Impact Analysis"
description: |
  Implement field-level reference tracking to enable precise impact analysis when FileMan fields are modified, 
  allowing developers to identify exactly which routines access specific fields rather than just globals.

---

## Goal
Implement field-level reference tracking that creates direct relationships between MUMPS code elements (Labels/Routines) and FileMan fields, enabling precise impact analysis when fields are modified. The system will parse global references to identify specific field access patterns and create ACCESSES_FIELD relationships in the Neo4j graph database.

## Why
- **Impact Analysis**: Immediately identify affected code when planning field changes (target: 80% reduction in analysis time)
- **Code Understanding**: Visualize field usage patterns across the entire VistA codebase
- **Risk Assessment**: Distinguish between read and write operations on critical fields
- **Maintenance Planning**: Better scope estimation for field modifications and data dictionary changes
- **Compliance**: Track access to sensitive fields (SSN, DOB, etc.) for security auditing

## What
Enhance the existing global access parsing to extract field-level information from MUMPS patterns and create precise field-level relationships in the graph database.

### Success Criteria
- [ ] Parse $PIECE operations to identify specific field access (e.g., `$P(^DPT(DFN,0),"^",1)` → field .01)
- [ ] Create ACCESSES_FIELD relationships with metadata (piece number, node, access type)
- [ ] Support both direct node access and cross-reference patterns
- [ ] Achieve 95%+ accuracy in field identification
- [ ] Handle READ, WRITE, KILL, and EXISTS operations correctly
- [ ] Process all Registration package routines as proof of concept
- [ ] Generate report showing field usage frequency and access patterns

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://www.va.gov/vdl/documents/Infrastructure/Fileman/fm22_2tm.pdf
  why: VA FileMan Technical Manual - understand DD structure and field storage patterns
  
- file: src/parsers/code_extractor.py
  why: Current implementation of global access parsing - extend extract_accesses_from_routine method
  
- file: src/models/relationships.py
  why: Add new ACCESSES_FIELD relationship type here
  
- file: src/models/nodes.py
  why: Understand FieldNode structure for creating relationships

- file: src/graph/builder.py
  why: Pattern for creating batch relationships in Neo4j

- file: src/graph/node_cache.py
  why: Use for resolving field references by file and field number

- url: https://vistapedia.com/index.php/MUMPS_Functions_$PIECE
  why: $PIECE function documentation for parsing field extraction patterns

- doc: VistA FileMan Data Dictionary Structure
  section: Global Storage Patterns
  critical: Fields are stored in pieces delimited by "^" on specific nodes
```

### Current Codebase Structure
```bash
src/
├── models/
│   ├── nodes.py          # Contains FieldNode, FileNode, LabelNode classes
│   └── relationships.py  # Relationship definitions (need to add ACCESSES_FIELD)
├── parsers/
│   ├── code_extractor.py # Main parser - has extract_accesses_from_routine method
│   └── routine_parser.py # Parses routine structure
├── graph/
│   ├── builder.py        # Creates relationships in Neo4j
│   └── node_cache.py     # Caches nodes for efficient lookup
└── main.py              # Orchestrates the parsing pipeline
```

### Desired Additions
```bash
src/
├── models/
│   └── relationships.py  # ADD: AccessesFieldRel class
├── parsers/
│   ├── code_extractor.py # ENHANCE: extract_field_accesses_from_routine method
│   └── field_mapper.py   # NEW: Maps global patterns to field definitions
├── graph/
│   └── builder.py        # ADD: create_field_access_relationships method
└── reports/
    └── field_usage_report.py # NEW: Generate field usage analytics
```

### Known Gotchas & FileMan Quirks
```python
# CRITICAL: FileMan field storage patterns
# Fields on node 0: pieces 1-N map to fields .01-.0N typically
# Example: ^DPT(DFN,0) piece 1 = field .01 (NAME), piece 2 = field .02 (SEX)
# BUT: Not all fields follow this pattern - some are computed or stored elsewhere

# GOTCHA: Variable subscripts need pattern matching
# ^DPT(DFN,0) where DFN is a variable - need to recognize as patient file access

# GOTCHA: Cross-references don't follow piece patterns
# ^DPT("B",NAME,DFN) is the B cross-reference for field .01

# CRITICAL: Access type detection
# SET ^GLOBAL()= is WRITE
# S X=$P(^GLOBAL(),"^",1) is READ  
# K ^GLOBAL() is KILL
# $D(^GLOBAL()) is EXISTS

# GOTCHA: Indirect references are common
# S X="^DPT("_DFN_",0)" ... @X - need to handle indirection

# PATTERN: MUMPS allows abbreviated commands
# S = SET, K = KILL, D = DO, G = GOTO
```

## Implementation Blueprint

### Data Models and Structure

```python
# In src/models/relationships.py - ADD this new relationship class
class AccessesFieldRel(Relationship):
    """Label/Routine accesses a specific FileMan field."""
    
    relationship_type: RelationshipType = RelationshipType.ACCESSES_FIELD
    
    def __init__(
        self,
        label_id: str,
        field_id: str,
        line_number: int,
        access_type: str,  # "READ", "WRITE", "KILL", "EXISTS"
        piece_number: int = None,  # For $PIECE operations
        node_location: str = None,  # e.g., "0", ".3", "NAME"
        extraction_pattern: str = None,  # Original code pattern
        confidence: float = 0.8,
    ):
        metadata = {
            "line_number": line_number,
            "access_type": access_type,
        }
        if piece_number is not None:
            metadata["piece_number"] = piece_number
        if node_location:
            metadata["node_location"] = node_location
        if extraction_pattern:
            metadata["extraction_pattern"] = extraction_pattern
            
        super().__init__(
            from_id=label_id,
            to_id=field_id,
            confidence=confidence,
            metadata=metadata,
        )
```

### List of Tasks to Complete
Create a new archon project called Vista Graph Database Field Access and track all tasks there. 

```yaml
Task 1: Add ACCESSES_FIELD relationship type
MODIFY src/models/relationships.py:
  - FIND pattern: "class RelationshipType(Enum)"
  - ADD after last relationship type: ACCESSES_FIELD = "ACCESSES_FIELD"
  - ADD AccessesFieldRel class as shown above

Task 2: Create field mapping module
CREATE src/parsers/field_mapper.py:
  - MIRROR pattern from: src/parsers/code_extractor.py structure
  - CREATE FieldMapper class with methods to map global patterns to fields
  - IMPLEMENT piece-to-field mapping logic

Task 3: Enhance code extractor with field-level parsing
MODIFY src/parsers/code_extractor.py:
  - ADD new method: extract_field_accesses_from_routine
  - ENHANCE existing GLOBAL_ACCESS_PATTERN regex to capture full context
  - ADD $PIECE parsing logic to identify specific fields

Task 4: Update node cache for field resolution
MODIFY src/graph/node_cache.py:
  - ADD method: resolve_field_by_file_and_number
  - ADD method: get_field_metadata to retrieve field storage info
  - ENHANCE _load_files to include field mappings

Task 5: Create field access relationship builder
MODIFY src/graph/builder.py:
  - ADD method: create_field_access_relationships
  - FOLLOW pattern from create_accesses_relationships
  - BATCH process for efficiency

Task 6: Integrate into main pipeline
MODIFY src/main.py:
  - ADD call to extract_field_accesses_from_routine in Phase 4
  - ADD call to create_field_access_relationships
  - ADD statistics reporting for field accesses

Task 7: Create field usage report generator
CREATE src/reports/field_usage_report.py:
  - QUERY Neo4j for ACCESSES_FIELD relationships
  - GENERATE statistics: most accessed fields, read vs write ratios
  - OUTPUT CSV and console report

Task 8: Add comprehensive tests
CREATE tests/test_field_access_extraction.py:
  - TEST $PIECE parsing with various patterns
  - TEST access type detection (READ/WRITE/KILL/EXISTS)
  - TEST field resolution accuracy
  - TEST cross-reference pattern recognition
```

### Per Task Implementation Details

```python
# Task 2: Field Mapper Implementation
class FieldMapper:
    def __init__(self, node_cache: NodeLookupCache):
        self.node_cache = node_cache
        # Standard FileMan node 0 field mappings (common pattern)
        self.standard_mappings = {
            "2": {  # PATIENT file
                "0": {  # Node 0
                    1: ".01",   # NAME
                    2: ".02",   # SEX
                    3: ".03",   # DATE OF BIRTH
                    9: ".09",   # SOCIAL SECURITY NUMBER
                },
                ".3": {  # Node .3
                    1: ".301",  # SERVICE CONNECTED?
                    2: ".302",  # SERVICE CONNECTED PERCENTAGE
                }
            }
        }
    
    def map_piece_to_field(self, file_number: str, node: str, piece: int) -> Optional[str]:
        """Map a piece number on a node to a field number."""
        # Check standard mappings first
        if file_number in self.standard_mappings:
            if node in self.standard_mappings[file_number]:
                return self.standard_mappings[file_number][node].get(piece)
        
        # Query the data dictionary for actual mapping
        # This would need to parse ^DD(file_number,field_number,0) entries
        return self.node_cache.resolve_field_by_position(file_number, node, piece)

# Task 3: Enhanced Global Access Parsing
def extract_field_accesses_from_routine(self, routine_path: Path) -> Tuple[List[Dict], List[Dict]]:
    """Extract field-level access patterns from MUMPS code."""
    field_accesses = []
    orphan_accesses = []
    
    # Enhanced pattern to capture $PIECE operations
    PIECE_PATTERN = re.compile(
        r'\$P(?:IECE)?\s*\(\s*'  # $P or $PIECE
        r'\^([A-Z][A-Z0-9]*)'     # Global name
        r'\(([^)]+)\)'            # Subscripts
        r',\s*"\^"\s*,\s*(\d+)'   # Piece number
    )
    
    # Pattern for SET operations
    SET_GLOBAL_PATTERN = re.compile(
        r'^\s+S(?:ET)?\s+'        # SET command
        r'\^([A-Z][A-Z0-9]*)'     # Global name
        r'\(([^)]+)\)\s*='        # Subscripts and assignment
    )
    
    # Process each line
    for line_num, line in enumerate(lines, 1):
        # Check for $PIECE operations (READ)
        for match in PIECE_PATTERN.finditer(line):
            global_name = match.group(1)
            subscripts = match.group(2)
            piece_num = int(match.group(3))
            
            # Resolve to file and field
            file_info = self.node_cache.resolve_file_by_global(global_name)
            if file_info:
                field_number = self.field_mapper.map_piece_to_field(
                    file_info[0], "0", piece_num  # Assuming node 0 for now
                )
                if field_number:
                    field_id = self.node_cache.resolve_field(file_info[0], field_number)
                    if field_id and current_label_id:
                        field_accesses.append({
                            "label_id": current_label_id,
                            "field_id": field_id,
                            "line_number": line_num,
                            "access_type": "READ",
                            "piece_number": piece_num,
                            "node_location": "0",
                            "pattern": match.group(0)
                        })
```

### Integration Points
```yaml
DATABASE:
  - No schema changes needed - using existing Label and Field nodes
  - New relationship type: ACCESSES_FIELD
  
CONFIGURATION:
  - Add to: src/config/settings.py (if needed)
  - pattern: "FIELD_ACCESS_CONFIDENCE_THRESHOLD = 0.7"
  
NEO4J INDEXES:
  - Ensure index on: Field(file_number, number)
  - Ensure index on: Label(routine_name, name)
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
uv run ruff check src/parsers/field_mapper.py --fix
uv run ruff check src/parsers/code_extractor.py --fix
uv run mypy src/parsers/field_mapper.py
uv run mypy src/parsers/code_extractor.py

# Expected: No errors. If errors, READ and fix.
```

### Level 2: Unit Tests
```python
# CREATE tests/test_field_access_extraction.py
import pytest
from src.parsers.field_mapper import FieldMapper
from src.parsers.code_extractor import CodeRelationshipExtractor

def test_piece_extraction():
    """Test $PIECE pattern recognition"""
    code = 'S NAME=$P(^DPT(DFN,0),"^",1)'
    extractor = CodeRelationshipExtractor(mock_cache)
    result = extractor.extract_piece_operations(code)
    assert result[0]["piece_number"] == 1
    assert result[0]["global_name"] == "DPT"

def test_access_type_detection():
    """Test READ vs WRITE detection"""
    read_code = 'S X=$P(^DPT(DFN,0),"^",1)'
    write_code = 'S ^DPT(DFN,0)=NAME_"^"_SEX'
    
    assert extractor.detect_access_type(read_code, 5) == "READ"
    assert extractor.detect_access_type(write_code, 2) == "WRITE"

def test_field_mapping():
    """Test piece to field number mapping"""
    mapper = FieldMapper(mock_cache)
    # Patient file, node 0, piece 1 should map to field .01
    assert mapper.map_piece_to_field("2", "0", 1) == ".01"
    assert mapper.map_piece_to_field("2", "0", 9) == ".09"  # SSN

def test_cross_reference_pattern():
    """Test cross-reference recognition"""
    code = 'S DFN=$O(^DPT("B",NAME,""))'
    result = extractor.extract_xref_access(code)
    assert result["xref_name"] == "B"
    assert result["field_reference"] == ".01"  # B xref is on NAME field
```

```bash
# Run unit tests
uv run pytest tests/test_field_access_extraction.py -v
```

### Level 3: Integration Test
```bash
# Process a sample routine with known field accesses
uv run python -m src.main --phase 4 --test-routine DG10

# Verify in Neo4j
echo 'MATCH (l:Label)-[r:ACCESSES_FIELD]->(f:Field) 
WHERE l.routine_name = "DG10" 
RETURN l.name, f.number, f.name, r.access_type, r.piece_number 
LIMIT 10' | cypher-shell

# Expected: See field relationships with correct piece numbers
```

### Level 4: Full Pipeline Test
```bash
# Run complete extraction on Registration package
uv run python -m src.main --phase 4 --package Registration

# Generate field usage report
uv run python -m src.reports.field_usage_report --package Registration

# Expected output:
# Field Usage Report - Registration Package
# ==========================================
# Most Accessed Fields:
# 1. PATIENT.NAME (.01): 342 accesses (280 READ, 62 WRITE)
# 2. PATIENT.SSN (.09): 156 accesses (156 READ, 0 WRITE)
# ...
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] Sample routine processing successful
- [ ] Field relationships visible in Neo4j browser
- [ ] Access types (READ/WRITE) correctly identified
- [ ] Piece numbers correctly mapped to field numbers
- [ ] Performance acceptable (<5 min for 1000 routines)
- [ ] Field usage report generates correctly

## Anti-Patterns to Avoid
- ❌ Don't hardcode field mappings - use data dictionary
- ❌ Don't assume all files follow the same piece pattern
- ❌ Don't ignore indirect references (@variable syntax)
- ❌ Don't miss abbreviated MUMPS commands (S vs SET)
- ❌ Don't create duplicate relationships for the same access
- ❌ Don't assume node 0 for all field storage

## Expected Challenges & Solutions

### Challenge 1: Variable Field Mappings
**Problem**: Not all files store fields in the same piece positions
**Solution**: Query ^DD global for actual field storage locations

### Challenge 2: Computed Fields
**Problem**: Some fields are computed, not stored
**Solution**: Parse MUMPS code in computed field definitions

### Challenge 3: Cross-Reference Patterns
**Problem**: XRefs don't use piece extraction
**Solution**: Map XRef names to their indexed fields via DD

### Challenge 4: Performance with Large Codebases
**Problem**: Parsing thousands of routines is slow
**Solution**: Batch processing, caching, parallel execution

## Additional Resources
- VistA Data Dictionary Browser: Use to verify field mappings
- MUMPS by Example: Reference for command patterns
- FileMan Programmer Manual: Deep dive on DD structure

---

**Confidence Score: 8.5/10**

This PRP provides comprehensive context for implementing field-level reference tracking. The score reflects:
- ✅ Strong understanding of existing codebase structure
- ✅ Clear implementation path with specific code examples  
- ✅ Detailed validation steps and test cases
- ✅ Addresses known MUMPS/FileMan quirks
- ⚠️ May need additional DD parsing logic for complex field mappings
- ⚠️ Cross-reference handling might need refinement based on actual data

The implementation should succeed in one pass with potential minor adjustments for edge cases in field mapping logic.