# PRP: VistA Graph Database Phase 2 - Static Relationships

## 🎯 Objective
Implement Phase 2 of the VistA Graph Database roadmap, extracting deterministic relationships from the Data Dictionary (DD) including pointer relationships, cross-references, and subfile structures.

## 📝 Requirements
Based on vista_graph_implementation_roadmap.md Phase 2 (Weeks 3-4):
1. **Extract pointer relationships** - Parse P-type and V-type (variable pointer) fields
2. **Map cross-references** - Extract from DD(file,field,1) nodes for index relationships
3. **Process subfiles** - Identify multiple fields and create subfile hierarchy
4. **Create INDEXED_BY relationships** - Store set/kill logic as properties

## 🏗️ Current State (Phase 1 Complete)
- ✅ Neo4j database running and accessible
- ✅ ZWR parser extracting files and fields from DD.zwr
- ✅ Package, File, Field nodes created successfully
- ✅ Basic relationships: CONTAINS_FILE, CONTAINS_FIELD, POINTS_TO (basic)
- ✅ Main pipeline in src/main.py with phase argument support

## 📚 Research & Context

### Cross-Reference Structure in DD
Cross-references are stored in DD nodes with subscript pattern: `^DD(file,field,1,xref_num,...)`
```mumps
^DD(2,391,1,0)="^.1"                    // Cross-ref header
^DD(2,391,1,991,0)="2^AVAFC391^MUMPS"   // XRef definition: file^name^type
^DD(2,391,1,991,1)="SET logic..."       // Set logic
^DD(2,391,1,991,2)="KILL logic..."      // Kill logic
```

### Subfile Identification
Subfiles are identified by:
- Field type "M" (Multiple)
- File numbers with decimals (e.g., "2.01" is subfile of "2")
- Parent-child relationships in DD structure

### Variable Pointer Fields
V-type fields can point to multiple files:
```mumps
^DD(file,field,0)="POINTER^V..."        // Variable pointer indicator
^DD(file,field,"V",target_num,0)="target_file^target_global^description"
```

### Existing Code Base Structure
```
src/
├── models/
│   ├── nodes.py          # PackageNode, FileNode, FieldNode
│   └── relationships.py  # ContainsFieldRel, PointsToRel, etc.
├── parsers/
│   ├── zwr_parser.py    # Parses DD.zwr, needs extension for xrefs
│   └── csv_parser.py    # Parses Packages.csv
├── graph/
│   ├── builder.py       # Graph construction, needs Phase 2 methods
│   ├── connection.py    # Neo4j connection handling
│   └── queries.py       # Cypher queries, needs xref queries
└── main.py              # CLI entry, needs phase 2 pipeline
```

## 🔧 Implementation Blueprint

### 1. Extend Models (src/models/)

#### nodes.py additions:
```python
class CrossReferenceNode(BaseModel):
    """Cross-reference/index definition."""
    xref_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str               # XRef name (e.g., "B", "AVAFC391")
    file_number: str        # File containing the xref
    field_number: str       # Field being indexed
    xref_type: str          # "regular", "trigger", "new-style", "MUMPS"
    xref_number: str        # XRef number in DD
    set_logic: Optional[str] = None
    kill_logic: Optional[str] = None
    execution: str = "field"  # "field", "record", "global"
    
class SubfileNode(FileNode):
    """Subfile is a special type of File."""
    parent_file_number: str
    parent_field_number: str  # Multiple field that contains this subfile
```

#### relationships.py additions:
```python
class IndexedByRel(BaseModel):
    """Field INDEXED_BY CrossReference relationship."""
    xref_name: str
    xref_type: str
    set_condition: Optional[str] = None
    kill_condition: Optional[str] = None
    
class SubfileOfRel(BaseModel):
    """Subfile SUBFILE_OF parent File relationship."""
    parent_field: str  # The multiple field containing subfile
    level: int  # Nesting level (1 for direct, 2 for sub-subfile)

class VariablePointerRel(BaseModel):
    """Variable pointer can point to multiple files."""
    target_file: str
    target_global: str
    target_description: Optional[str] = None
    v_number: str  # The V-pointer target number
```

### 2. Enhance ZWR Parser (src/parsers/zwr_parser.py)

Add methods to extract:
```python
def extract_cross_references(self, lines: List[str]) -> Dict[str, CrossReferenceNode]:
    """Extract cross-reference definitions from DD."""
    xrefs = {}
    for parsed in self.parse_lines(lines):
        if self.is_xref_header(parsed):  # DD(file,field,1,0)="^.1"
            xref = self.parse_xref_definition(parsed, lines)
            xrefs[xref.xref_id] = xref
    return xrefs
    
def extract_subfiles(self, files: Dict[str, FileNode]) -> List[SubfileNode]:
    """Identify and create subfile nodes."""
    subfiles = []
    for file_num, file_node in files.items():
        if "." in file_num:  # Decimal indicates subfile
            parent_num = file_num.split(".")[0]
            subfile = SubfileNode(
                **file_node.dict(),
                parent_file_number=parent_num
            )
            subfiles.append(subfile)
    return subfiles

def extract_variable_pointers(self, lines: List[str]) -> Dict[str, List[Dict]]:
    """Extract V-type pointer targets."""
    v_pointers = {}  # field_id -> list of targets
    for parsed in self.parse_lines(lines):
        if self.is_v_pointer_target(parsed):  # DD(file,field,"V",n,0)
            field_key = f"{parsed.subscripts[0]}_{parsed.subscripts[1]}"
            target_info = self.parse_v_target(parsed.value)
            v_pointers.setdefault(field_key, []).append(target_info)
    return v_pointers
```

### 3. Extend Graph Builder (src/graph/builder.py)

Add Phase 2 specific methods:
```python
def create_cross_reference_nodes(self, xrefs: List[CrossReferenceNode]) -> int:
    """Create cross-reference nodes in Neo4j."""
    # Batch create XRef nodes
    
def create_indexed_by_relationships(self, xrefs: Dict, fields: List[FieldNode]):
    """Create INDEXED_BY relationships between fields and xrefs."""
    # Match fields to their xrefs and create relationships
    
def create_subfile_relationships(self, subfiles: List[SubfileNode]):
    """Create SUBFILE_OF relationships."""
    # Link subfiles to parent files
    
def create_variable_pointer_relationships(self, v_pointers: Dict, fields: List):
    """Create multiple POINTS_TO relationships for V-type fields."""
    # Each V-pointer field gets multiple POINTS_TO relationships
    
def enhance_pointer_relationships(self):
    """Enhance existing pointer relationships with more metadata."""
    # Add laygo, required, and other pointer attributes
```

### 4. Update Graph Queries (src/graph/queries.py)

Add queries for Phase 2:
```python
@staticmethod
def create_xref_node() -> str:
    """Create cross-reference node."""
    return """
    UNWIND $batch AS xref
    CREATE (x:CrossReference)
    SET x = xref
    RETURN count(x) AS created
    """

@staticmethod
def create_indexed_by_rel() -> str:
    """Create INDEXED_BY relationship."""
    return """
    UNWIND $batch AS item
    MATCH (f:Field {field_id: item.field_id})
    MATCH (x:CrossReference {xref_id: item.xref_id})
    CREATE (f)-[r:INDEXED_BY]->(x)
    SET r = item.props
    RETURN count(r) AS created
    """

@staticmethod
def find_subfiles() -> str:
    """Find all subfiles and their parents."""
    return """
    MATCH (child:File)
    WHERE child.number CONTAINS '.'
    WITH child, split(child.number, '.')[0] AS parent_num
    MATCH (parent:File {number: parent_num})
    RETURN parent, collect(child) AS subfiles
    """
```

### 5. Create Phase 2 Pipeline (src/main.py)

Add phase2_pipeline function:
```python
def phase2_pipeline(args):
    """Execute Phase 2: Static Relationships."""
    settings = get_settings()
    connection = Neo4jConnection()
    
    # 1. Parse DD for extended information
    console.print("[cyan]Parsing DD.zwr for relationships...[/cyan]")
    zwr_parser = ZWRParser()
    dd_path = settings.get_absolute_path(settings.dd_file_path)
    
    # Parse with Phase 2 extractors
    files, fields = zwr_parser.parse_file(dd_path)
    xrefs = zwr_parser.extract_cross_references(dd_lines)
    subfiles = zwr_parser.extract_subfiles(files)
    v_pointers = zwr_parser.extract_variable_pointers(dd_lines)
    
    # 2. Build graph extensions
    builder = GraphBuilder(connection)
    
    # Create new node types
    builder.create_cross_reference_nodes(xrefs)
    
    # Create Phase 2 relationships
    builder.create_indexed_by_relationships(xrefs, fields)
    builder.create_subfile_relationships(subfiles)
    builder.create_variable_pointer_relationships(v_pointers, fields)
    
    # 3. Validate and report
    validate_phase2(connection)
    
# Update main() to handle phase 2
if args.phase == 2:
    phase2_pipeline(args)
```

## 🧪 Validation Gates

```bash
# 1. Syntax and style checks
uv run ruff check --fix src/
uv run mypy src/ --ignore-missing-imports

# 2. Unit tests for Phase 2 components
uv run pytest tests/test_phase2_parser.py -v
uv run pytest tests/test_phase2_builder.py -v

# 3. Integration test - run Phase 2 pipeline
uv run python -m src.main --phase 2 --source Vista-M-source-code

# 4. Neo4j validation queries
# Count new relationships
MATCH ()-[r:INDEXED_BY]->() RETURN count(r)
MATCH ()-[r:SUBFILE_OF]->() RETURN count(r)

# Verify cross-references
MATCH (f:Field)-[:INDEXED_BY]->(x:CrossReference)
RETURN f.name, x.name LIMIT 20

# Check subfile hierarchy
MATCH (parent:File)<-[:SUBFILE_OF]-(child:File)
RETURN parent.name, collect(child.name)
```

## 📁 File Structure After Phase 2

```
src/
├── models/
│   ├── nodes.py          # + CrossReferenceNode, SubfileNode
│   └── relationships.py  # + IndexedByRel, SubfileOfRel, VariablePointerRel
├── parsers/
│   └── zwr_parser.py    # + extract_cross_references(), extract_subfiles()
├── graph/
│   ├── builder.py       # + Phase 2 relationship builders
│   └── queries.py       # + Cross-reference and subfile queries
├── main.py              # + phase2_pipeline()
└── validators/
    └── phase2.py        # New: Phase 2 specific validation
tests/
├── test_phase2_parser.py    # New: Test xref and subfile extraction
└── test_phase2_builder.py   # New: Test Phase 2 relationships
```

## 🎯 Success Criteria

1. **Cross-References Extracted**: All DD(file,field,1,...) entries processed
2. **INDEXED_BY Relationships**: Fields linked to their indexes
3. **Subfile Hierarchy**: All decimal-numbered files linked to parents
4. **Variable Pointers**: V-type fields have multiple POINTS_TO relationships
5. **Enhanced Metadata**: Set/kill logic stored on relationships
6. **Performance**: Phase 2 completes in <60 seconds
7. **Validation**: No orphaned cross-references, all subfiles have parents

## 📊 Expected Outcomes

Based on typical VistA DD structure:
- ~5,000-10,000 cross-reference nodes
- ~20,000+ INDEXED_BY relationships
- ~500-1,000 subfile relationships
- ~100-500 variable pointer fields with multiple targets

## 🚨 Error Handling

1. **Missing Parent Files**: Log warning, create placeholder node
2. **Invalid XRef Logic**: Store as-is, flag for manual review
3. **Circular Subfiles**: Detect and prevent infinite loops
4. **Unparseable V-Pointers**: Store raw, mark confidence=0.5

## 📝 Implementation Tasks
Please create a new project in Archon and create and manage and move tasks there according to the below. 

1. Create model extensions for CrossReference and Subfile nodes
2. Extend ZWR parser to extract cross-references from DD
3. Parse subfile relationships from file numbers
4. Extract variable pointer targets
5. Build INDEXED_BY relationships
6. Build SUBFILE_OF relationships  
7. Create multiple POINTS_TO for V-type fields
8. Add Phase 2 pipeline to main.py
9. Create validation queries
10. Write comprehensive tests
11. Update documentation

## 🔗 References

- **VistA FileMan Programmer Manual**: https://www.va.gov/vdl/documents/Infrastructure/Kernel/fm22_0pm.pdf (Section on Cross-References)
- **MUMPS Cross-Reference Structure**: https://en.wikipedia.org/wiki/MUMPS#Cross-references
- **FileMan Data Dictionary**: https://www.hardhats.org/fileman/u2/dd_struc.htm
- **Graph Database Best Practices**: https://neo4j.com/developer/guide-data-modeling/

## 📈 Confidence Score: 8.5/10

High confidence due to:
- ✅ Clear Phase 1 foundation already working
- ✅ Well-defined DD structure for parsing
- ✅ Existing parser and builder patterns to extend
- ✅ Clear success criteria from roadmap

Minor uncertainties:
- Exact count of cross-references (varies by VistA version)
- Complex V-pointer resolution may need refinement
- Some XRef logic may be too complex for initial parsing

---

**Ready for implementation.** This PRP provides comprehensive context for one-pass Phase 2 development.