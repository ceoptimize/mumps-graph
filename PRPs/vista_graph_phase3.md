# VistA Graph Database Phase 3: Code Structure Implementation PRP

## Executive Summary
Implement Phase 3 of the VistA Graph Database roadmap, focusing on parsing and representing MUMPS routines and their internal structure (labels, entry points, functions) in the Neo4j graph database.

## Context & Current State

### What's Already Completed
**Phase 1 (Foundation):**
- ✅ Neo4j database setup with indexes
- ✅ Package nodes from Packages.csv (all packages with prefixes)
- ✅ File nodes from DD.zwr (all files with global roots)
- ✅ Field nodes with types (Free Text, Pointer, Computed, etc.)
- ✅ CONTAINS_FIELD relationships
- ✅ POINTS_TO relationships for pointer fields

**Phase 2 (Static Relationships):**
- ✅ CrossReference nodes for indexes
- ✅ INDEXED_BY relationships
- ✅ SUBFILE_OF relationships for hierarchical data
- ✅ VARIABLE_POINTER relationships

### Phase 3 Goals
According to `vista_graph_implementation_roadmap.md` (Week 5-6):
1. Process routine files (`.m` files in Vista-M-source-code/Packages/*/Routines/)
2. Integrate MUMPS parser (compare emcellent vs custom implementation)
3. Extract labels from routines
4. Identify entry points and functions
5. Create Routine and Label nodes with relationships

## Implementation Approach

### Emcellent Parser Strategy
Use the emcellent MUMPS parser to parse routine files and extract structure. Emcellent provides robust MUMPS parsing with proper AST generation, eliminating the need for custom regex-based parsing.

### Node Schema Extensions

#### Routine Node
```python
class RoutineNode(BaseModel):
    routine_id: str  # UUID
    name: str  # e.g., "DG10"
    package_name: str  # e.g., "Registration"
    prefix: str  # e.g., "DG"
    path: str  # Full file path
    lines_of_code: int
    last_modified: Optional[str]
    version: Optional[str]
    patches: List[str]  # Extracted from header
    description: Optional[str]  # From header comments
```

#### Label Node
```python
class LabelNode(BaseModel):
    label_id: str  # UUID
    name: str  # e.g., "PROCESS"
    routine_name: str  # Parent routine
    line_number: int
    is_entry_point: bool  # Called from other routines
    is_function: bool  # Returns value (QUIT with value)
    parameters: List[str]  # If determinable
    comment: Optional[str]  # Adjacent comment
```

### MUMPS Code Patterns to Recognize

#### Labels
```mumps
LABEL ; Comment
START ;
A W !! K VET,DIE
EN(DFN,TYPE) ; Entry point with parameters
```

#### Function Detection
```mumps
FUNC() Q $$VALUE  ; Function returning value
CHECK() Q 1  ; Returns literal
```

#### Entry Points (heuristics)
- Labels called with DO from other routines
- Labels with EN prefix
- Labels with parameters
- Labels at beginning of routine

## Technical Implementation Details

### Emcellent MUMPS Parser Integration

**Using Emcellent for MUMPS Parsing:**
```python
from pathlib import Path
from typing import List, Dict, Optional
from emcellent import parse_mumps_file, MumpsAST

class MUMPSParser:
    ENTRY_POINT_INDICATORS = ['EN', 'EP', 'START', 'INIT']
    
    def parse_routine(self, file_path: str) -> Dict:
        """Parse a MUMPS routine file using emcellent."""
        labels = []
        
        # Parse file with emcellent
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Get AST from emcellent
        ast = parse_mumps_file(content)
        
        # Extract labels from AST
        for node in ast.walk():
            if node.type == 'label':
                label_data = {
                    'name': node.name,
                    'line_number': node.line,
                    'parameters': self.extract_params(node),
                    'is_function': self.is_function(node),
                    'is_entry_point': self.is_entry_point(node.name),
                    'comment': node.comment if hasattr(node, 'comment') else ''
                }
                labels.append(label_data)
        
        return {'labels': labels, 'ast': ast}
    
    def extract_params(self, node) -> List[str]:
        """Extract parameters from a label node."""
        if hasattr(node, 'parameters'):
            return node.parameters
        return []
    
    def is_function(self, node) -> bool:
        """Determine if a label is a function (returns a value)."""
        # Check if the label has a QUIT with value in its body
        for child in node.children:
            if child.type == 'quit' and child.has_value:
                return True
        return False
    
    def is_entry_point(self, label_name: str) -> bool:
        """Determine if a label is likely an entry point."""
        return any(label_name.startswith(prefix) for prefix in self.ENTRY_POINT_INDICATORS)
```

## Project Management

**Use Archon MCP Server**: This implementation should be managed using Archon for project and task tracking. Create a project in Archon called Vista Graph 3 EM and break down the implementation into atomic tasks that can be tracked and managed systematically.

## Implementation Tasks

### Phase 3A: Parser Integration

1. **Integrate Emcellent Parser**
   - Install and configure emcellent parser
   - Create wrapper for emcellent AST traversal
   - Extract labels, functions, and entry points from AST
   - Handle parameters and comments
   - Handle edge cases and malformed routines

2. **Validate Parser**
   - Parse sample routines from Registration package
   - Validate AST accuracy on 10 representative routines
   - Measure performance metrics
   - Document AST node patterns found

### Phase 3B: Graph Integration

3. **Extend Node Models**
   ```python
   # src/models/nodes.py
   class RoutineNode(BaseModel):
       # Implementation
   
   class LabelNode(BaseModel):
       # Implementation
   ```

4. **Create Routine Parser Module**
   ```python
   # src/parsers/routine_parser.py
   from emcellent import parse_mumps_file
   
   class RoutineParser:
       def parse_directory(self, dir_path: Path) -> List[RoutineNode]
       def extract_labels_from_ast(self, ast, routine: RoutineNode) -> List[LabelNode]
       def process_routine_file(self, file_path: Path) -> Tuple[RoutineNode, List[LabelNode]]
   ```

5. **Extend Graph Builder**
   ```python
   # src/graph/builder.py
   def create_routine_nodes(self, routines: List[RoutineNode])
   def create_label_nodes(self, labels: List[LabelNode])
   def create_routine_label_relationships()
   def create_package_routine_relationships()
   ```

6. **Update Main Pipeline**
   ```python
   # src/main.py
   def phase3_pipeline(args):
       # Process routines
       # Extract labels
       # Build graph extensions
   ```

### Relationships to Create

#### CONTAINS_LABEL Relationship
**Purpose**: Links routines to their labels (fundamental MUMPS organizational unit)
```cypher
(:Routine)-[:CONTAINS_LABEL {
    line_number: 45
}]->(:Label)
```

**Implementation in builder.py:**
```python
def create_contains_label_relationships(
    self, routines: List[RoutineNode], labels: List[LabelNode]
) -> int:
    """Create CONTAINS_LABEL relationships between routines and their labels."""
    relationships = []
    
    # Group labels by routine
    labels_by_routine = {}
    for label in labels:
        if label.routine_name not in labels_by_routine:
            labels_by_routine[label.routine_name] = []
        labels_by_routine[label.routine_name].append(label)
    
    # Build relationships
    for routine in routines:
        if routine.name in labels_by_routine:
            for label in labels_by_routine[routine.name]:
                relationships.append({
                    'routine_id': routine.routine_id,
                    'label_id': label.label_id,
                    'line_number': label.line_number
                })
    
    # Batch create using existing pattern
    return self.batch_create_relationships("CONTAINS_LABEL", relationships)
```

#### OWNS_ROUTINE Relationship  
**Purpose**: Links packages to their routines based on prefix matching
```cypher
(:Package)-[:OWNS_ROUTINE]->(:Routine)
```

## Critical: Node Matching Strategy

### DO NOT Use Random IDs for Matching
**Problem**: The current models use `uuid4()` for IDs, which are random and won't match between phases or runs.

### Use Business Keys for Matching

#### Matching Existing Nodes from Phase 1-2
```python
# CORRECT: Match on business keys, not IDs
def find_package_for_routine(self, routine_name: str, prefix: str) -> Optional[str]:
    """Find package by prefix, not by package_id."""
    query = """
    MATCH (p:Package)
    WHERE $prefix IN p.prefixes
    RETURN p.name as package_name, p.package_id as package_id
    """
    result = self.connection.execute_query(query, {"prefix": prefix})
    if result:
        return result[0]["package_name"]
    return None

# WRONG: Don't try to match on package_id
# The package_id from Phase 1 is a UUID that we can't recreate
```

#### Creating Relationships Using Business Keys
```python
def create_package_routine_relationships(self, routines: List[RoutineNode]) -> int:
    """Link routines to packages using prefix matching, not IDs."""
    query = """
    UNWIND $routines as routine
    MATCH (p:Package)
    WHERE routine.prefix IN p.prefixes
    MATCH (r:Routine {name: routine.name})
    MERGE (p)-[:OWNS_ROUTINE]->(r)
    RETURN count(*) as count
    """
    
    routine_data = [
        {
            "name": r.name,
            "prefix": r.prefix  # e.g., "DG" from "DG10"
        }
        for r in routines
    ]
    
    result = self.connection.execute_query(
        query, {"routines": routine_data}
    )
    return result[0]["count"] if result else 0
```

#### Node Creation with Merge
```python
def create_routine_nodes(self, routines: List[RoutineNode]) -> int:
    """Create routine nodes using MERGE to prevent duplicates."""
    query = """
    UNWIND $batch as routine
    MERGE (r:Routine {name: routine.name})
    ON CREATE SET 
        r.routine_id = routine.routine_id,
        r.package_name = routine.package_name,
        r.prefix = routine.prefix,
        r.path = routine.path,
        r.lines_of_code = routine.lines_of_code,
        r.last_modified = routine.last_modified
    ON MATCH SET
        r.lines_of_code = routine.lines_of_code,
        r.last_modified = routine.last_modified
    RETURN count(r) as count
    """
    # Use business key (name) for MERGE, not routine_id
```

### Business Keys by Node Type

| Node Type | Business Key | Example |
|-----------|--------------|---------|
| Package | name | "Registration" |
| File | number | "2" |
| Field | file_number + number | "2" + ".01" |
| Routine | name | "DG10" |
| Label | routine_name + name | "DG10" + "START" |
| CrossReference | file_number + field_number + name | "2" + ".01" + "B" |

### Relationship Creation Pattern
```python
# Always match nodes by business keys
MATCH (source:NodeType {business_key: $source_key})
MATCH (target:NodeType {business_key: $target_key})
MERGE (source)-[:RELATIONSHIP_TYPE]->(target)
```

### Validation Query
```cypher
// Check for orphaned routines (no package relationship)
MATCH (r:Routine)
WHERE NOT ((:Package)-[:OWNS_ROUTINE]->(r))
RETURN count(r) as orphaned_routines

// Check for duplicate routines
MATCH (r:Routine)
WITH r.name as name, count(r) as count
WHERE count > 1
RETURN name, count
```

## File References for Context

### Existing Code to Reference
- **Node Models**: `src/models/nodes.py:35-96` (FileNode, FieldNode patterns)
- **Parser Pattern**: `src/parsers/zwr_parser.py` (ZWRParser structure)
- **Builder Pattern**: `src/graph/builder.py:96-214` (batch creation methods)
- **Pipeline Pattern**: `src/main.py:252-356` (phase2_pipeline implementation)

### MUMPS Files to Parse
- **Location**: `Vista-M-source-code/Packages/*/Routines/*.m`
- **Example**: `Vista-M-source-code/Packages/Registration/Routines/DG10.m`
- **Count**: Approximately 20,000+ routine files

## Validation Gates

### Unit Tests
```bash
# Test parser accuracy
uv run pytest tests/test_routine_parser.py -v

# Test graph builder extensions
uv run pytest tests/test_phase3_builder.py -v
```

### Integration Tests
```bash
# Parse all routines and validate
uv run python -m src.main --phase 3 --validate-only

# Check graph integrity
uv run python scripts/validate_phase3.py
```

### Quality Checks
```bash
# Code style and typing
uv run ruff check --fix src/
uv run mypy src/

# Coverage
uv run pytest --cov=src --cov-report=html
```

## Success Metrics

### Parser Performance Metrics
- **Accuracy**: 95%+ labels correctly identified
- **Performance**: < 30 seconds for 1000 routines
- **Robustness**: Handle malformed MUMPS gracefully

### Graph Completeness
- 100% of routine files processed
- 95%+ of labels extracted
- 90%+ of entry points identified
- All routine-package relationships mapped

### Performance Targets
- Parse time: < 5 minutes for all routines
- Graph import: < 10 minutes
- Query response: < 1 second for routine dependencies

## Error Handling Strategy

### Parser Failures
```python
try:
    parsed = parser.parse_routine(file_path)
except ParseError as e:
    logger.warning(f"Failed to parse {file_path}: {e}")
    # Create routine node with basic info
    # Mark as needs_review
    # Continue processing
```

### Graceful Degradation
- If parser fails, extract basic info (name, line count)
- Mark unparseable routines for manual review
- Log all errors with context

## Decision Documentation

### Parser Implementation Rationale
The Emcellent parser approach provides:
- Robust, tested MUMPS parsing capabilities
- Proper AST generation for structured code analysis
- Handles MUMPS syntax edge cases correctly
- Eliminates need for maintaining custom regex patterns
- More accurate parsing of complex MUMPS constructs
- Better handling of malformed or non-standard code

### Implementation Notes
- Start with Registration package (smaller subset)
- Validate against known routine structures
- Iterate based on patterns discovered

## Resources

### Documentation
- **MUMPS Syntax**: https://mumps.dev/
- **VistaM Repository**: Vista-M-source-code

### Code Examples
Reference implementations in:
- `tests/fixtures/sample_routines/` (create test cases)
- Existing Phase 1-2 patterns in `src/`

## Risk Mitigation

### Technical Risks
1. **MUMPS Syntax Complexity**: Rely on emcellent's proven parsing, mark uncertain extractions
2. **Scale Issues**: Process in batches, use multiprocessing
3. **Parser Dependencies**: Ensure emcellent is properly installed and configured

### Data Quality
1. **Malformed Routines**: Log and continue, don't fail pipeline
2. **Missing Metadata**: Use defaults, mark for review
3. **Inconsistent Patterns**: Document variations found

## Confidence Score: 9/10

### Strengths
- Clear requirements from roadmap
- Existing pattern to follow (Phase 1-2)
- Well-defined node/relationship schema
- Leveraging proven emcellent parser
- More reliable AST-based parsing

### Areas of Uncertainty
- MUMPS parsing edge cases
- Performance at scale (20,000+ files)
- Entry point detection heuristics

### Mitigation
- Start with subset (Registration package)
- Extensive logging and validation
- Iterative refinement based on patterns found
- Performance profiling and optimization


