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

### Git Worktree Strategy
As specified in feature_3.md, create two parallel implementations:
1. **Branch 1**: emcellent-based parser (Node.js subprocess)
2. **Branch 2**: Custom Python parser (regex/pattern-based)

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

### Option 1: emcellent Parser Integration

**Setup:**
```bash
# In worktree branch
cd parser_implementations/emcellent_parser
npm install emcellent
```

**Python Integration:**
```python
import subprocess
import json

class EmcellentParser:
    def parse_routine(self, file_path: str) -> Dict:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Call emcellent via Node.js
        result = subprocess.run(
            ['node', 'parse_mumps.js', content],
            capture_output=True,
            text=True
        )
        
        return json.loads(result.stdout)
```

**Node.js Bridge (parse_mumps.js):**
```javascript
const emcellent = require('emcellent');
const input = process.argv[2];
const parsed = emcellent.parse(input);
console.log(JSON.stringify(parsed));
```

### Option 2: Custom Python Parser

**Pattern-Based Parser:**
```python
import re
from typing import List, Dict, Optional

class MUMPSParser:
    # Regex patterns
    LABEL_PATTERN = r'^([A-Z][A-Z0-9]*)\s*(\([^)]*\))?\s*(;.*)?$'
    FUNCTION_PATTERN = r'Q\s+\$\$|QUIT\s+\$\$'
    ENTRY_POINT_INDICATORS = ['EN', 'EP', 'START', 'INIT']
    
    def parse_routine(self, file_path: str) -> Dict:
        labels = []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # Skip header lines
            if line_num == 1 and ';;' in line:
                continue
                
            # Check for label at start of line
            if line and not line[0].isspace():
                match = re.match(self.LABEL_PATTERN, line)
                if match:
                    label_name = match.group(1)
                    params = match.group(2) or ''
                    comment = match.group(3) or ''
                    
                    labels.append({
                        'name': label_name,
                        'line_number': line_num,
                        'parameters': self.extract_params(params),
                        'is_function': self.is_function(lines, line_num),
                        'is_entry_point': self.is_entry_point(label_name),
                        'comment': comment.strip(';').strip()
                    })
        
        return {'labels': labels}
```

## Project Management

**Use Archon MCP Server**: This implementation should be managed using Archon for project and task tracking. Create a project in Archon and break down the implementation into atomic tasks that can be tracked and managed systematically.

## Implementation Tasks
   ```bash
   git worktree add ../VistA-M-emcellent feature/phase3-emcellent
   git worktree add ../VistA-M-custom feature/phase3-custom
   ```

2. **Implement emcellent Parser**
   - Install Node.js dependencies
   - Create Python-Node.js bridge
   - Parse sample routines
   - Extract labels and metadata

3. **Implement Custom Parser**
   - Create regex patterns for MUMPS syntax
   - Handle label detection
   - Identify functions vs subroutines
   - Extract parameters

4. **Compare Parsers**
   - Parse 100 sample routines with both
   - Compare accuracy (manually validate 10 routines)
   - Measure performance
   - Assess maintainability

### Phase 3B: Graph Integration

5. **Extend Node Models**
   ```python
   # src/models/nodes.py
   class RoutineNode(BaseModel):
       # Implementation
   
   class LabelNode(BaseModel):
       # Implementation
   ```

6. **Create Routine Parser Module**
   ```python
   # src/parsers/routine_parser.py
   class RoutineParser:
       def parse_directory(self, dir_path: Path) -> List[RoutineNode]
       def extract_labels(self, routine: RoutineNode) -> List[LabelNode]
   ```

7. **Extend Graph Builder**
   ```python
   # src/graph/builder.py
   def create_routine_nodes(self, routines: List[RoutineNode])
   def create_label_nodes(self, labels: List[LabelNode])
   def create_routine_label_relationships()
   def create_package_routine_relationships()
   ```

8. **Update Main Pipeline**
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

### Parser Comparison Metrics
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

### Parser Choice Rationale
After implementing both approaches, choose based on:

| Criteria | emcellent | Custom | Winner |
|----------|-----------|---------|---------|
| Accuracy | Full AST | Pattern matching | TBD |
| Speed | Node.js overhead | Pure Python | TBD |
| Maintainability | External dep | Internal control | TBD |
| Extensibility | Limited to emcellent | Full control | TBD |

### Implementation Notes
- Start with Registration package (smaller subset)
- Validate against known routine structures
- Consider hybrid approach if beneficial

## Resources

### Documentation
- **emcellent**: https://github.com/mmccall/eMcellent
- **MUMPS Syntax**: https://mumps.dev/
- **VistaM Repository**: Vista-M-source-code

### Code Examples
Reference implementations in:
- `tests/fixtures/sample_routines/` (create test cases)
- Existing Phase 1-2 patterns in `src/`

## Risk Mitigation

### Technical Risks
1. **MUMPS Syntax Complexity**: Use conservative patterns, mark uncertain extractions
2. **Scale Issues**: Process in batches, use multiprocessing
3. **Parser Dependencies**: Vendor both parsers, document setup

### Data Quality
1. **Malformed Routines**: Log and continue, don't fail pipeline
2. **Missing Metadata**: Use defaults, mark for review
3. **Inconsistent Patterns**: Document variations found

## Confidence Score: 8.5/10

### Strengths
- Clear requirements from roadmap
- Existing pattern to follow (Phase 1-2)
- Well-defined node/relationship schema
- Two implementation approaches for comparison

### Areas of Uncertainty
- MUMPS parsing complexity (many edge cases)
- Performance at scale (20,000+ files)
- Entry point detection heuristics

### Mitigation
- Start with subset (Registration package)
- Implement both parsers for comparison
- Extensive logging and validation
- Iterative refinement based on results


