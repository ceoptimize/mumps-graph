# PRP: VistA Graph Database Phase 4 - Code Relationships

## Overview

This PRP guides the implementation of Phase 4 of the VistA Graph Database project, focusing on extracting and mapping code interdependencies and global access patterns from MUMPS routines. Phase 4 builds upon the foundation established in Phases 1-3, which created Package, File, Field, Routine, and Label nodes along with their structural relationships.

## Context

### Current State (After Phase 3)
- **Nodes Created**: Package, File, Field, CrossReference, Routine, Label
- **Relationships Created**: CONTAINS_FILE, CONTAINS_FIELD, POINTS_TO, INDEXED_BY, CONTAINS_LABEL, OWNS_ROUTINE
- **Parser Available**: Custom Python MUMPS parser that extracts labels from routines
- **Infrastructure**: Neo4j database with batch processing capability

### Phase 4 Goals
According to `vista_graph_implementation_roadmap.md`:
1. Create Global nodes as prerequisites for access relationships
2. Extract call patterns (DO, GOTO, $$) between labels
3. Map global access patterns (READ, WRITE, KILL)
4. Build confidence scoring system for relationships
5. Add FALLS_THROUGH relationships for control flow

## Implementation Architecture

### 1. New Node Types

#### GlobalNode
```python
class GlobalNode(BaseModel):
    """Global storage location in VistA."""
    global_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str  # e.g., "DPT" (without ^)
    type: str = "data"  # "data", "index", "temp"
    file_number: Optional[str] = None  # Associated file if known
    description: Optional[str] = None
```

### 2. New Relationship Types

```python
class CallsRel(Relationship):
    """Label calls another label via DO or GOTO."""
    line_number: int
    call_type: str  # "DO", "GOTO", "JOB"
    target_routine: Optional[str] = None  # For cross-routine calls
    confidence: float = 1.0  # Parser-confirmed

class InvokesRel(Relationship):
    """Label invokes function via $$."""
    line_number: int
    assigns_to: Optional[str] = None  # Variable if captured
    target_routine: Optional[str] = None
    confidence: float = 1.0

class AccessesRel(Relationship):
    """Label accesses a global."""
    line_number: int
    access_type: str  # "READ", "WRITE", "KILL", "EXISTS"
    pattern: Optional[str] = None  # e.g., "^DPT(DFN,0)"
    confidence: float = 0.8  # Pattern-matched

class FallsThroughRel(Relationship):
    """Sequential execution between labels."""
    confidence: float = 0.9  # High unless explicit QUIT

class StoredInRel(Relationship):
    """File is stored in a global."""
    confidence: float = 1.0  # From DD definition
```

### 3. Node Resolution Strategy

#### Critical: Efficient Node Lookup Cache
```python
class NodeLookupCache:
    """Cache existing nodes from Phases 1-3 for efficient relationship creation."""
    
    def __init__(self, connection: Neo4jConnection):
        self.connection = connection
        # Key lookups for finding nodes by their natural identifiers
        self.labels = {}  # {(routine_name, label_name): label_id}
        self.labels_by_line = {}  # {(routine_name, line_number): label_id}
        self.routines = {}  # {routine_name: routine_id}
        self.globals = {}  # {global_name: global_id}
        self.files = {}  # {file_number: (file_id, global_root)}
        
    def load_from_neo4j(self):
        """Pre-load all nodes for efficient lookup during relationship creation."""
        
        # Load all Label nodes
        query = """
        MATCH (l:Label)
        RETURN l.label_id as id, l.name as name, 
               l.routine_name as routine, l.line_number as line
        """
        labels = self.connection.execute_query(query)
        for label in labels:
            key = (label['routine'], label['name'])
            self.labels[key] = label['id']
            line_key = (label['routine'], label['line'])
            self.labels_by_line[line_key] = label['id']
        
        # Load all Routine nodes
        query = "MATCH (r:Routine) RETURN r.routine_id as id, r.name as name"
        routines = self.connection.execute_query(query)
        for routine in routines:
            self.routines[routine['name']] = routine['id']
        
        # Load all File nodes with global roots
        query = """
        MATCH (f:File) 
        RETURN f.file_id as id, f.number as num, f.global_root as root
        """
        files = self.connection.execute_query(query)
        for file in files:
            self.files[file['num']] = (file['id'], file['root'])
        
        # Globals will be loaded after creation in Phase 4
        
    def resolve_label(self, routine_name: str, label_name: str) -> Optional[str]:
        """Resolve a label reference to its node ID."""
        return self.labels.get((routine_name, label_name))
    
    def resolve_label_by_line(self, routine_name: str, line_num: int) -> Optional[str]:
        """Resolve a label by its line number in a routine."""
        return self.labels_by_line.get((routine_name, line_num))
```

### 4. Enhanced Parser Module

#### Code Relationship Extractor
```python
class CodeRelationshipExtractor:
    """Extract relationships from MUMPS code with node resolution."""
    
    def __init__(self, node_cache: NodeLookupCache):
        self.node_cache = node_cache
        
        # Patterns for MUMPS commands
        self.DO_PATTERN = re.compile(
            r'^\s+D(?:O)?\s+'  # DO or D command
            r'([A-Z][A-Z0-9]*)'  # Label name
            r'(?:\^([A-Z][A-Z0-9]*))?'  # Optional routine
            r'(?:\((.*?)\))?'  # Optional parameters
        )
        
        self.GOTO_PATTERN = re.compile(
            r'^\s+G(?:OTO)?\s+'  # GOTO or G command
            r'([A-Z][A-Z0-9]*)'  # Label name
            r'(?:\^([A-Z][A-Z0-9]*))?'  # Optional routine
        )
        
        self.FUNCTION_PATTERN = re.compile(
            r'\$\$'  # Function indicator
            r'([A-Z][A-Z0-9]*)'  # Function name
            r'(?:\^([A-Z][A-Z0-9]*))?'  # Optional routine
            r'(?:\((.*?)\))?'  # Optional parameters
        )
        
        self.GLOBAL_ACCESS_PATTERN = re.compile(
            r'\^([A-Z][A-Z0-9]*)'  # Global name
            r'(?:\((.*?)\))?'  # Optional subscripts
        )
    
    def extract_calls_from_routine(self, routine_path: Path) -> List[Dict]:
        """Extract all call relationships from a routine with source label resolution."""
        calls = []
        routine_name = routine_path.stem
        
        with open(routine_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        current_label = None
        current_label_id = None
        
        for line_num, line in enumerate(lines, 1):
            # Track current label context
            if line and line[0] not in ' \t;':  # New label
                label_match = re.match(r'^([A-Z][A-Z0-9]*)', line)
                if label_match:
                    current_label = label_match.group(1)
                    current_label_id = self.node_cache.resolve_label(
                        routine_name, current_label
                    )
            
            # Extract DO/GOTO calls
            if current_label_id:
                # Check for DO pattern
                do_match = self.DO_PATTERN.match(line)
                if do_match:
                    calls.append({
                        'source_label_id': current_label_id,
                        'source_label': current_label,
                        'source_routine': routine_name,
                        'target_label': do_match.group(1),
                        'target_routine': do_match.group(2) or routine_name,
                        'line_number': line_num,
                        'call_type': 'DO'
                    })
                
                # Similar for GOTO...
        
        return calls
        
    def determine_access_type(self, line: str, global_ref: str) -> str:
        """Determine if global access is READ, WRITE, KILL, or EXISTS."""
        # Check for KILL command
        if re.search(rf'K(?:ILL)?\s+.*\^{global_ref}', line):
            return 'KILL'
        # Check for SET (write)
        if re.search(rf'S(?:ET)?\s+\^{global_ref}.*=', line):
            return 'WRITE'
        # Check for $DATA existence check
        if re.search(rf'\$D(?:ATA)?\(\^{global_ref}', line):
            return 'EXISTS'
        # Default to READ
        return 'READ'
```

## Implementation Tasks
Please use Archon mcp to track all tasks in a new project called Vista Graph Phase 4.

### Task 1: Create Node Lookup Cache Infrastructure
1. Create `src/graph/node_cache.py` with NodeLookupCache class
2. Load all existing nodes from Phases 1-3 into memory
3. Create efficient lookup dictionaries by natural keys
4. Add methods for resolving references to node IDs

### Task 2: Create Global Nodes Infrastructure
1. Add GlobalNode class to `src/models/nodes.py`
2. Create method to extract unique globals from File.global_root
3. Scan code for globals without file associations
4. Batch create Global nodes in Neo4j
5. Update node cache with new Global nodes

### Task 3: Add Relationship Classes
1. Add new relationship types to `src/models/relationships.py`
2. Update RelationshipType enum
3. Create relationship classes with proper metadata
4. Ensure from_id and to_id use resolved node IDs

### Task 4: Implement Code Relationship Extractor
1. Create `src/parsers/code_extractor.py` with patterns
2. Pass NodeLookupCache to extractor for immediate resolution
3. Implement method to parse DO/GOTO calls with source resolution
4. Implement method to parse function invocations
5. Implement method to parse global accesses
6. Add confidence scoring based on resolution success

### Task 5: Enhance Graph Builder with Node Resolution
1. Add `create_global_nodes()` method
2. Add `create_calls_relationships()` with node ID resolution
3. Add `create_invokes_relationships()` with node ID resolution
4. Add `create_accesses_relationships()` with node ID resolution
5. Add `create_falls_through_relationships()` using label line numbers
6. Add `create_stored_in_relationships()` matching globals to files

### Task 6: Implement Phase 4 Pipeline
1. Add phase 4 to command-line arguments
2. Create `phase4_pipeline()` function in main.py
3. Initialize NodeLookupCache and load all existing nodes
4. Process routines to extract relationships with resolution
5. Create relationships using resolved node IDs
6. Track and report unresolved references

### Task 7: Add Validation and Testing
1. Create test cases for node resolution
2. Validate all relationships use existing node IDs
3. Report unresolved calls with details
4. Create validation queries for relationship integrity

## Pseudocode Implementation

```python
def phase4_pipeline(args):
    """Execute Phase 4: Code Relationships with proper node resolution."""
    
    # 1. Validate Phase 3 completion
    if not validate_phase3_complete():
        exit("Phase 3 must be completed first")
    
    # 2. Initialize node lookup cache
    console.print("[cyan]Loading existing nodes from Phases 1-3...[/cyan]")
    node_cache = NodeLookupCache(connection)
    node_cache.load_from_neo4j()
    console.print(f"[green]Loaded: {len(node_cache.labels)} labels, "
                  f"{len(node_cache.routines)} routines, "
                  f"{len(node_cache.files)} files[/green]")
    
    # 3. Create Global nodes
    globals_to_create = {}  # {global_name: file_number or None}
    
    # From File.global_root
    for file_num, (file_id, global_root) in node_cache.files.items():
        if global_root:
            global_name = global_root.replace('^', '').split('(')[0]
            globals_to_create[global_name] = file_num
    
    # From code scanning (utility globals)
    for routine_file in find_all_routines():
        globals_in_code = extract_globals_from_code(routine_file)
        for global_name in globals_in_code:
            if global_name not in globals_to_create:
                globals_to_create[global_name] = None  # No file association
    
    # Create Global nodes and update cache
    global_nodes = create_global_nodes(globals_to_create)
    for node in global_nodes:
        node_cache.globals[node.name] = node.global_id
    
    # Create STORED_IN relationships
    create_stored_in_relationships(node_cache)
    
    # 4. Extract and create call relationships with resolution
    extractor = CodeRelationshipExtractor(node_cache)
    
    resolved_calls = []
    unresolved_calls = []
    resolved_invokes = []
    unresolved_invokes = []
    resolved_accesses = []
    
    for routine_file in find_all_routines():
        # Extract calls with immediate source resolution
        calls = extractor.extract_calls_from_routine(routine_file)
        
        for call in calls:
            # Resolve target label
            target_id = node_cache.resolve_label(
                call['target_routine'], 
                call['target_label']
            )
            
            if call['source_label_id'] and target_id:
                resolved_calls.append({
                    'from_id': call['source_label_id'],
                    'to_id': target_id,
                    'props': {
                        'line_number': call['line_number'],
                        'call_type': call['call_type'],
                        'confidence': 1.0  # Both nodes resolved
                    }
                })
            else:
                unresolved_calls.append(call)
        
        # Similar for invokes and accesses...
    
    # 5. Create relationships using resolved node IDs
    console.print(f"[cyan]Creating {len(resolved_calls)} CALLS relationships...[/cyan]")
    create_calls_relationships_batch(resolved_calls)
    
    # 6. Create FALLS_THROUGH relationships using line numbers
    create_falls_through_relationships(node_cache)
    
    # 7. Report results
    console.print(f"[green]✅ Created {len(resolved_calls)} CALLS relationships[/green]")
    if unresolved_calls:
        console.print(f"[yellow]⚠️  {len(unresolved_calls)} unresolved calls[/yellow]")
        for call in unresolved_calls[:5]:  # Show first 5
            console.print(f"    {call['source_routine']}:{call['source_label']} -> "
                         f"{call['target_routine']}:{call['target_label']}")
    
    validate_relationships()
    report_confidence_distribution()
```

### Relationship Creation with Proper Node Resolution

```python
def create_calls_relationships_batch(resolved_relationships: List[Dict]):
    """Create CALLS relationships using pre-resolved node IDs."""
    
    query = """
    UNWIND $batch AS rel
    MATCH (source) WHERE id(source) = rel.from_id
    MATCH (target) WHERE id(target) = rel.to_id
    CREATE (source)-[r:CALLS {
        line_number: rel.props.line_number,
        call_type: rel.props.call_type,
        confidence: rel.props.confidence
    }]->(target)
    RETURN count(r) as created
    """
    
    # Or using node properties if IDs are stored as properties
    query_alt = """
    UNWIND $batch AS rel
    MATCH (source:Label {label_id: rel.from_id})
    MATCH (target:Label {label_id: rel.to_id})
    CREATE (source)-[r:CALLS {
        line_number: rel.props.line_number,
        call_type: rel.props.call_type,
        confidence: rel.props.confidence
    }]->(target)
    RETURN count(r) as created
    """
    
    for batch in chunks(resolved_relationships, 1000):
        result = connection.execute_query(query_alt, {'batch': batch})
        
def create_stored_in_relationships(node_cache: NodeLookupCache):
    """Create STORED_IN relationships between Files and Globals."""
    
    relationships = []
    
    for file_num, (file_id, global_root) in node_cache.files.items():
        if global_root:
            global_name = global_root.replace('^', '').split('(')[0]
            global_id = node_cache.globals.get(global_name)
            
            if global_id:
                relationships.append({
                    'file_id': file_id,
                    'global_id': global_id
                })
    
    query = """
    UNWIND $batch AS rel
    MATCH (f:File {file_id: rel.file_id})
    MATCH (g:Global {global_id: rel.global_id})
    CREATE (f)-[:STORED_IN {confidence: 1.0}]->(g)
    RETURN count(*) as created
    """
    
    result = connection.execute_query(query, {'batch': relationships})
```

## Pattern Matching Examples

### DO Call Patterns
```mumps
D NOW^%DTC          ; DO NOW label in %DTC routine
D PROCESS           ; DO PROCESS in same routine
D EN^DG10(DFN)      ; DO EN in DG10 with parameter
DO VALIDATE^DGRPV   ; Full DO command
```

### Function Call Patterns
```mumps
S X=$$GET1^DIQ(...)     ; Function call with assignment
I $$VALID^DGRPV(DFN)    ; Function in condition
W $$FMTE^XLFDT(DATE)    ; Function in write
```

### Global Access Patterns
```mumps
S ^DPT(DFN,0)=DATA      ; WRITE access
S X=$G(^DPT(DFN,.35))   ; READ access with $GET
K ^TMP($J)              ; KILL access
I $D(^DGMT(408.31,DA))  ; EXISTS check with $DATA
S DA=$O(^DGPT("AFEE"))  ; READ with $ORDER
```

## Validation Gates

```bash
# 1. Syntax and Style Check
uv run ruff check --fix src/
uv run ruff format src/

# 2. Type Checking
uv run mypy src/

# 3. Unit Tests for Pattern Matching
uv run pytest tests/test_code_extractor.py -v

# 4. Integration Tests
uv run pytest tests/test_phase4_builder.py -v

# 5. Graph Validation Queries
# Check Global node creation
MATCH (g:Global) RETURN count(g) as global_count

# Check CALLS relationships
MATCH ()-[r:CALLS]->() RETURN count(r) as calls_count

# Check confidence distribution
MATCH ()-[r]->() WHERE r.confidence IS NOT NULL
RETURN type(r) as rel_type, 
       avg(r.confidence) as avg_confidence,
       min(r.confidence) as min_confidence,
       max(r.confidence) as max_confidence

# Check unresolved calls
MATCH (l:Label)-[r:CALLS]->(target)
WHERE NOT (target:Label)
RETURN count(r) as unresolved_calls

# Check orphan globals (no file association)
MATCH (g:Global)
WHERE NOT (g)<-[:STORED_IN]-(:File)
RETURN count(g) as orphan_globals
```

## Error Handling Strategy

1. **Node Resolution Failures**: Track unresolved references, report at end
2. **Missing Source Labels**: Skip relationship creation, log for debugging
3. **Parser Failures**: Log unparseable lines, continue with pattern matching
4. **Unresolved Targets**: Don't create relationship, add to unresolved list
5. **Ambiguous Patterns**: Use lowest confidence score, log for manual verification
6. **Circular Dependencies**: Detect and flag, don't prevent creation
7. **Cache Memory**: Monitor cache size, warn if > 1GB

## Performance Optimizations

1. **Node Cache**: Pre-load all nodes once to avoid repeated database queries
2. **Batch Processing**: Process relationships in batches of 1000
3. **Index Usage**: Ensure indexes on label_id, routine_id, global_id for fast lookups
4. **Memory Management**: Process one routine at a time, clear intermediate data
5. **Efficient Lookups**: Use dictionaries with tuple keys for O(1) lookups
6. **Parallel Processing**: Consider concurrent routine processing (optional enhancement)

## Success Metrics

- ✅ 100% of Global nodes created from File.global_root
- ✅ 90%+ of DO/GOTO calls resolved to target labels
- ✅ 85%+ of function calls resolved
- ✅ 80%+ of global accesses mapped
- ✅ Confidence scores: 70%+ parser-confirmed, <10% inferred
- ✅ Performance: < 5 minutes for complete Phase 4 execution

## Testing Data

Use Registration package routines for initial testing:
- Expected ~50-100 routines
- Expected ~500-1000 labels  
- Expected ~2000+ call relationships
- Expected ~1000+ global accesses

## Key Files to Reference

- `src/parsers/routine_parser.py` - Existing label extraction
- `src/models/nodes.py` - Node definitions
- `src/models/relationships.py` - Relationship definitions
- `src/graph/builder.py` - Graph building methods
- `src/main.py` - Pipeline structure
- `Vista-M-source-code/Packages/Registration/Routines/*.m` - Sample MUMPS code

## Implementation Order

1. **GlobalNode and StoredIn** - Foundation for access relationships
2. **Code Extractor with Tests** - Ensure pattern matching works
3. **CALLS Relationships** - Most common and deterministic
4. **INVOKES Relationships** - Function calls
5. **ACCESSES Relationships** - Global access patterns
6. **FALLS_THROUGH** - Control flow
7. **Validation and Reporting** - Quality assurance

## Confidence Score Guidelines

- **1.0**: Parser-confirmed, unambiguous match
- **0.9**: Pattern-matched with high certainty
- **0.8**: Pattern-matched with context validation
- **0.7**: Pattern-matched basic
- **0.5**: Inferred or ambiguous
- **0.3**: Best guess, needs review

This PRP provides a complete implementation guide for Phase 4, building upon the existing codebase while adding the critical code relationship extraction capabilities needed for comprehensive VistA system analysis.

## Critical Success Factors for Node Resolution

1. **Node Cache Completeness**: Must load ALL nodes from Phases 1-3 before starting
2. **Unique Key Strategy**: Use composite keys (routine_name, label_name) for lookups
3. **ID Consistency**: Always use the UUID fields (label_id, routine_id, etc.) for relationships
4. **Resolution Validation**: Never create a relationship without both source and target IDs
5. **Fallback Strategy**: Track unresolved references for manual review, don't guess

## PRP Confidence Score: 9.5/10

Very high confidence due to:
- Comprehensive node resolution strategy added
- Clear mapping from natural keys to node IDs
- Efficient caching mechanism for performance
- Proper handling of unresolved references
- Established Neo4j infrastructure
- Detailed implementation pseudocode with resolution

The addition of the NodeLookupCache and resolution strategy addresses the critical gap in merging with existing nodes, ensuring Phase 4 relationships will correctly link to Phase 1-3 nodes rather than creating duplicates or failing to connect.