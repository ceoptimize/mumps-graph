# VistA Graph Database Implementation Roadmap

## Executive Summary

This document provides a practical implementation roadmap for building a graph database representation of the VistA-M codebase. The design balances completeness with feasibility, focusing on extractable patterns that provide maximum value for system understanding, impact analysis, and modernization efforts.

## Core Design Principles

1. **Extract only what we can determine with confidence** - Avoid inferring relationships that require runtime context
2. **Prioritize high-value relationships** - Focus on what developers actually need to understand the system
3. **Use parser where it adds precision** - Don't parse for parsing's sake
4. **Keep the schema extensible** - Allow for future enhancement without breaking changes

## Graph Schema

### Primary Node Types

#### 1. Package
**Purpose**: Top-level organization unit  
**Source**: `Packages.csv`  
**Extraction**: Deterministic CSV parsing
```cypher
(:Package {
  name: "Registration",
  prefixes: ["DG", "VAF"],
  directory: "Registration"
})
```

#### 2. File
**Purpose**: Data structure definitions  
**Source**: `DD.zwr`, individual `.zwr` files  
**Extraction**: Deterministic parsing of ZWR format
```cypher
(:File {
  number: "2",
  name: "PATIENT",
  global_root: "^DPT"
})

// Subfiles get multiple labels
(:File:Subfile {
  number: "2.01",
  name: "ALIAS",
  parent_file: "2"
})
```

#### 3. Field
**Purpose**: Data element definitions  
**Source**: `DD.zwr`  
**Extraction**: Deterministic from DD global
```cypher
(:Field {
  number: ".01",
  name: "NAME",
  file: "2",
  data_type: "F",  // F, N, D, P, S, C, W, V
  required: true
})

// Pointer fields get additional label
(:Field:Pointer {
  number: ".302",
  name: "PROVIDER",
  file: "2",
  target_file: "200"
})

// Computed fields
(:Field:Computed {
  number: ".033",
  name: "AGE",
  file: "2",
  mumps_code: "S X=$$AGE^DPTAGE(DFN)"  // Store but don't parse initially
})
```

#### 4. Global
**Purpose**: Physical storage locations  
**Source**: File definitions + routine analysis  
**Extraction**: Pattern matching from code
```cypher
(:Global {
  name: "^DPT",
  type: "data",  // "data", "index", "temp"
  file: "2"  // If determinable
})
```

#### 5. Routine
**Purpose**: Code files  
**Source**: `.m` files  
**Extraction**: File system + header parsing
```cypher
(:Routine {
  name: "DG10",
  package: "Registration",  // Determined by prefix
  path: "Registration/Routines/DG10.m",
  lines_of_code: 523
})
```

#### 6. Label
**Purpose**: Code organization units (the fundamental MUMPS unit)  
**Source**: MUMPS parser analysis of `.m` files  
**Extraction**: Parser required for accuracy
```cypher
// Basic label
(:Label {
  name: "PROCESS",
  routine: "DG10",
  line_number: 45
})

// Labels with multiple types using Neo4j multi-label feature
(:Label:EntryPoint {
  name: "EN",
  routine: "DG10",
  line_number: 8,
  parameters: ["DFN", "TYPE"]  // If determinable
})

(:Label:Function {
  name: "VALID",
  routine: "DGRPV",
  line_number: 234,
  returns_value: true
})

// Combined types
(:Label:EntryPoint:Function {
  name: "CHECK",
  routine: "DGRPV",
  line_number: 100
})
```

### Primary Relationship Types

#### 1. Structural Relationships (High Confidence)

**Source**: Static analysis of DD and file system
```cypher
// Package ownership - from Packages.csv
(:Package)-[:OWNS_FILE]->(:File)
(:Package)-[:OWNS_ROUTINE]->(:Routine)  // Based on prefix matching

// File structure - from DD.zwr
(:File)-[:CONTAINS_FIELD]->(:Field)
(:File:Subfile)-[:CHILD_OF]->(:File)  // Parent-subfile relationship

// Code structure - from parser
(:Routine)-[:CONTAINS_LABEL]->(:Label)
```

#### 2. Data Relationships (High Confidence)

**Source**: DD.zwr field definitions
```cypher
// Pointer relationships - deterministic from DD
(:Field:Pointer)-[:POINTS_TO {
  required: false,
  laygo: true  // Can create new entries
}]->(:File)

// Storage relationships - moved to Phase 4 with Global node creation
// (:File)-[:STORED_IN]->(:Global)

// Index relationships - from DD cross-reference definitions
(:Field)-[:INDEXED_BY]->(:CrossReference)
```

#### 3. Code Flow Relationships (Parser Required)

**Source**: MUMPS parser analysis
```cypher
// Direct calls - high confidence with parser
(:Label)-[:CALLS {
  line: 45,
  call_type: "DO"  // vs "GOTO", "JOB"
}]->(:Label)

// Function invocations
(:Label)-[:INVOKES {
  line: 46,
  assigns_to: "RESULT"  // Variable if captured
}]->(:Label:Function)

// Fall-through (sequential execution)
(:Label)-[:FALLS_THROUGH]->(:Label)
```

#### 4. Global Access Relationships (Phase 4)

**Source**: Parser + pattern matching
```cypher
// Global nodes and storage (created in Phase 4)
(:Global {name: "DPT"})
(:File)-[:STORED_IN]->(:Global)

// Global access patterns from code
(:Label)-[:ACCESSES {
  line: 48,
  access_type: "READ",  // vs "WRITE", "KILL"
  pattern: "^DPT(DFN,0)"  // If determinable
}]->(:Global)
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Goal**: Build core schema infrastructure

#### Tasks:
1. **Set up graph database** (Neo4j, community edition, apoc enabled)
   - Install and configure
   - Create indexes on key properties (file.number, routine.name, label.name)
   - Set up multi-label support

2. **Build ZWR parser**
   - Parse DD.zwr format
   - Extract file/field definitions
   - Handle special characters and escaping

3. **Parse Packages.csv**
   - Map packages to prefixes
   - Extract file ranges

#### Deliverables:
- Populated Package nodes
- File and Field nodes from DD
- Basic CONTAINS_FIELD relationships

### Phase 2: Static Relationships (Week 3-4)
**Goal**: Extract deterministic relationships from DD

#### Tasks:
1. **Extract pointer relationships**
   - Parse P-type fields
   - Create POINTS_TO relationships
   - Handle variable pointers (store but mark as complex)

2. **Map cross-references**
   - Extract from DD(file,field,1) nodes
   - Create INDEXED_BY relationships
   - Store set/kill logic as properties

3. **Process subfiles**
   - Identify multiple fields
   - Create subfile hierarchy

#### Deliverables:
- Complete data dictionary graph
- All pointer relationships
- Cross-reference mappings

### Phase 3: Code Structure (Week 5-6)
**Goal**: Add routine and basic code structure

#### Tasks:
1. **Process routine files**
   - Create Routine nodes
   - Extract header metadata (version, patches)
   - Map to packages by prefix

2. **Integrate MUMPS parser**
   - Set up parser (emcellent or similar)
   - Handle parsing errors gracefully
   - Fall back to pattern matching where needed

3. **Extract labels**
   - Parse all labels from routines
   - Identify entry points (called from other routines)
   - Detect functions (QUIT with value)

#### Deliverables:
- All Routine nodes
- Label nodes with multi-label types
- CONTAINS_LABEL relationships

### Phase 4: Code Relationships (Week 7-8)
**Goal**: Map code interdependencies and global access patterns

#### Tasks:
1. **Create Global nodes (prerequisite)**
   - Extract global names from File.global_root property
   - Create Global nodes for each unique global
   - Create STORED_IN relationships from Files to Globals
   - Handle globals without File associations (utility globals)

2. **Extract call patterns**
   - Parse DO, GOTO, and $$ calls
   - Match to target labels
   - Handle external routine calls
   - Create FALLS_THROUGH relationships for sequential flow

3. **Map global access**
   - Identify global references in code (^GLOBAL patterns)
   - Distinguish READ vs WRITE vs KILL operations
   - Create ACCESSES relationships to Global nodes
   - Match to File definitions where possible via global_root

4. **Build confidence scoring**
   - Mark parser-confirmed (1.0)
   - Mark pattern-matched (0.7)
   - Mark inferred (0.5)

#### Deliverables:
- Global nodes and STORED_IN relationships
- CALLS relationships between labels
- INVOKES relationships for function calls
- ACCESSES relationships to globals
- FALLS_THROUGH relationships for control flow
- Confidence scores on relationships

### Phase 5: Enhancement & Validation (Week 9-10)
**Goal**: Add valuable metadata and validate graph

#### Tasks:
1. **Calculate metrics**
   - Lines of code per routine
   - Number of entry points
   - Fan-in/fan-out for labels

2. **Validate relationships**
   - Check for orphaned nodes
   - Verify pointer targets exist
   - Flag unresolved calls
   
3. **Create utility queries**
   - Impact analysis templates
   - Dependency reports
   - Common traversal patterns

#### Deliverables:
- Enriched metadata
- Validation report
- Query library

## Data Extraction Pipeline

```python
# Pseudo-code for extraction pipeline

class VistAGraphBuilder:
    def __init__(self, graph_db):
        self.graph = graph_db
        self.parser = MUMPSParser()
        
    def phase1_extract_schema(self):
        # Parse DD.zwr
        dd_data = parse_dd_global("DD.zwr")
        for file_num, file_data in dd_data.items():
            file_node = self.graph.create_node(
                labels=["File"],
                properties={
                    "number": file_num,
                    "name": file_data["name"],
                    "global_root": file_data["global"]
                }
            )
            
            # Add fields
            for field_num, field_data in file_data["fields"].items():
                field_labels = ["Field"]
                if field_data["type"] == "P":
                    field_labels.append("Pointer")
                elif field_data["type"] == "C":
                    field_labels.append("Computed")
                    
                field_node = self.graph.create_node(
                    labels=field_labels,
                    properties={
                        "number": field_num,
                        "name": field_data["name"],
                        "file": file_num,
                        "data_type": field_data["type"]
                    }
                )
                
                self.graph.create_relationship(
                    file_node, field_node, "CONTAINS_FIELD"
                )
    
    def phase2_extract_pointers(self):
        # Query all pointer fields
        pointer_fields = self.graph.query(
            "MATCH (f:Field:Pointer) RETURN f"
        )
        
        for field in pointer_fields:
            target_file = extract_target_file(field["specifier"])
            if target_file:
                target = self.graph.find_node(
                    "File", {"number": target_file}
                )
                if target:
                    self.graph.create_relationship(
                        field, target, "POINTS_TO",
                        {"confidence": 1.0}
                    )
    
    def phase3_parse_routines(self):
        for routine_file in glob("**/*.m"):
            routine_name = parse_routine_name(routine_file)
            routine_node = self.graph.create_node(
                labels=["Routine"],
                properties={
                    "name": routine_name,
                    "path": routine_file
                }
            )
            
            try:
                ast = self.parser.parse(routine_file)
                labels = extract_labels(ast)
                
                for label in labels:
                    label_types = ["Label"]
                    if is_entry_point(label):
                        label_types.append("EntryPoint")
                    if is_function(label):
                        label_types.append("Function")
                    
                    label_node = self.graph.create_node(
                        labels=label_types,
                        properties={
                            "name": label["name"],
                            "routine": routine_name,
                            "line_number": label["line"]
                        }
                    )
                    
                    self.graph.create_relationship(
                        routine_node, label_node, "CONTAINS_LABEL"
                    )
            except ParseError:
                # Fall back to pattern matching
                labels = extract_labels_pattern(routine_file)
                # ... handle with lower confidence
```

## Query Templates for Use Cases

### 1. Learning File/Field Structures
```cypher
// Get complete structure of a file
MATCH (f:File {number: $file_num})-[:CONTAINS_FIELD]->(field:Field)
OPTIONAL MATCH (field:Pointer)-[:POINTS_TO]->(target:File)
RETURN f.name, field.number, field.name, field.data_type, target.name
ORDER BY field.number
```

### 2. Code Generation Support
```cypher
// Find all fields that need handling for a record type
MATCH (f:File {number: $file_num})-[:CONTAINS_FIELD]->(field:Field)
WHERE field.required = true OR field.data_type IN ["P", "V"]
RETURN field.number, field.name, field.data_type, field.input_transform
```

### 3. Impact Analysis
```cypher
// Find all code that accesses a specific field
MATCH (field:Field {file: $file_num, number: $field_num})
OPTIONAL MATCH (field)<-[:INDEXED_BY]-(xref)
OPTIONAL MATCH (field)<-[:POINTS_TO]-(pointer:Field)
OPTIONAL MATCH (:Label)-[acc:ACCESSES]->(:Global {file: $file_num})
RETURN field, collect(DISTINCT xref), collect(DISTINCT pointer), count(acc)
```

### 4. Dependency Tracking
```cypher
// Find dependencies of a routine
MATCH (r:Routine {name: $routine_name})-[:CONTAINS_LABEL]->(l:Label)
-[:CALLS]->(target:Label)<-[:CONTAINS_LABEL]-(dep:Routine)
WHERE dep.name <> r.name
RETURN DISTINCT dep.name, count(target) as call_count
ORDER BY call_count DESC
```

### 5. Data Flow Visualization
```cypher
// Trace data flow through pointer chains
MATCH path = (f1:File)-[:CONTAINS_FIELD]->(:Field:Pointer)-[:POINTS_TO]->(f2:File)
-[:CONTAINS_FIELD]->(:Field:Pointer)-[:POINTS_TO]->(f3:File)
RETURN path, f1.name, f2.name, f3.name
```

### 6. Migration Planning
```cypher
// Assess migration complexity for a package
MATCH (p:Package {name: $package_name})
OPTIONAL MATCH (p)-[:OWNS_FILE]->(f:File)
OPTIONAL MATCH (p)-[:OWNS_ROUTINE]->(r:Routine)
OPTIONAL MATCH (f)<-[:POINTS_TO]-(:Field)<-[:CONTAINS_FIELD]-(ext:File)
WHERE NOT (ext)<-[:OWNS_FILE]-(p)
RETURN 
  count(DISTINCT f) as file_count,
  count(DISTINCT r) as routine_count,
  count(DISTINCT ext) as external_dependencies
```

## Key Decisions and Tradeoffs

### What We Include
1. **All file/field definitions** - Complete data dictionary
2. **All pointer relationships** - Critical for data integrity
3. **All routines and labels** - Code organization structure
4. **Direct call relationships** - Where parseable with confidence
5. **Global access patterns** - Where identifiable
6. **Cross-reference definitions** - For understanding indexes

### What We Defer
1. **Variable-level data flow** - Too complex, limited value
2. **Complete control flow graphs** - Overengineering for most use cases
3. **Indirect execution paths** - Cannot determine statically
4. **Screen/action code execution** - Store as text, don't parse initially
5. **Computed field dependencies** - Store code, analyze on demand

### What We Mark as "Needs Review"
1. **Unresolved routine calls** - Label not found
2. **Variable pointers** - Multiple possible targets
3. **Indirect global references** - Using @ operator
4. **Dynamic code execution** - XECUTE commands

## Success Metrics

### Completeness
- 100% of files and fields captured
- 100% of pointer relationships mapped
- 95%+ of routines parsed successfully
- 90%+ of direct calls resolved

### Accuracy
- Parser-confirmed relationships: 70%+
- Pattern-matched relationships: 20%
- Inferred relationships: <10%

### Utility
- Impact analysis queries < 1 second
- Dependency reports < 5 seconds
- Full package analysis < 30 seconds

## Tools Required

### Essential
- **Neo4j** (or similar graph database)
- **MUMPS Parser** (emcellent or equivalent)
- **Python/Node.js** for orchestration
- **ZWR format parser** (custom build)

### Recommended
- **Apache Airflow** for pipeline management
- **GraphQL API** for query interface
- **Visualization library** (D3.js, Cytoscape)

## Risk Mitigation

### Parser Failures
- Implement graceful degradation to pattern matching
- Mark confidence levels appropriately
- Log unparseable sections for manual review

### Scale Issues
- Build incrementally, validate at each phase
- Use batch imports for Neo4j
- Create indexes before bulk operations

### Data Quality
- Validate pointer targets exist
- Check for orphaned nodes
- Flag suspicious patterns (circular dependencies)

## Maintenance Strategy

### Incremental Updates
- Track file modification times
- Re-parse only changed files
- Update relationships incrementally

### Version Control Integration
- Link commits to graph changes
- Track which patches affect which routines
- Build change impact reports

### Quality Monitoring
- Track parser success rates
- Monitor relationship confidence distribution
- Alert on degradation patterns

## Conclusion

This implementation roadmap provides a practical path to building a VistA graph database that is:

1. **Achievable** - Based on extractable patterns
2. **Valuable** - Supports real use cases
3. **Maintainable** - Clear schema and update strategy
4. **Extensible** - Can add complexity later if needed

The key is starting with high-confidence, high-value relationships and building incrementally. The schema uses Neo4j's strengths (multi-label nodes, rich relationships) while avoiding overengineering (trying to capture every possible runtime behavior).

Total estimated effort: 10 weeks for initial implementation, resulting in a graph that can answer the critical questions about VistA's structure and dependencies.