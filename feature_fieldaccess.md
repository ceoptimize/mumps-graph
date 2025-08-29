# Feature Request: Field-Level Reference Tracking for Enhanced Impact Analysis

## Summary
Add field-level reference tracking to enable precise impact analysis when FileMan fields are modified, allowing developers to identify exactly which routines access specific fields rather than just globals.

## Current State
The system currently tracks relationships at the global level:
- Labels/routines → Global access patterns (e.g., `^DPT(DFN,0)`)
- Globals → FileMan files
- Files → Field definitions

However, there's no direct tracking of which specific FileMan fields are accessed by code.

## Proposed Enhancement
Implement field-level reference tracking that creates direct relationships between code elements and FileMan fields.

### Key Features:

1. **Parse Global References to Field Level**
   - Analyze subscript patterns to determine specific field access
   - Example: `^DPT(DFN,0)` → Maps to fields .01-.09 on zero node
   - Example: `$P(^DPT(DFN,0),"^",1)` → Maps to field .01 specifically

2. **New Relationship Types**
   - Create `ACCESSES_FIELD` relationships between Labels/Routines and Fields
   - Include metadata: piece number, node location, access type (READ/WRITE)

3. **Enhanced Query Capabilities**
   - "Show all routines that access patient NAME field (.01)"
   - "Find all code that writes to field X"
   - "List routines affected by changes to file Y, field Z"

## Business Value
- **Impact Analysis**: Immediately identify affected code when planning field changes
- **Code Understanding**: Visualize field usage patterns across the codebase
- **Risk Assessment**: Distinguish between read and write operations on critical fields
- **Maintenance Planning**: Better scope estimation for field modifications

## Technical Approach
Enhance the existing global access parsing to extract field-level information from patterns like:
- Direct node access: `^GLOBAL(SUB,NODE)`
- Piece extraction: `$P(...,"^",N)`
- Cross-reference access: `^GLOBAL(SUB,"XREF")`

## Implementation Details

### Data Model Changes
```
New Relationship: ACCESSES_FIELD
Properties:
- accessType: READ | WRITE | KILL | EXISTS
- pieceNumber: Integer (for $PIECE operations)
- nodeLocation: String (e.g., "0", "1", "NAME")
- extractionPattern: String (original code pattern)
- confidence: Float (parsing confidence score)
```

### Example Scenarios

#### Scenario 1: Direct Field Access
```mumps
S NAME=$P(^DPT(DFN,0),"^",1)  ; Accessing .01 field
```
Creates: `Label -[ACCESSES_FIELD {pieceNumber: 1, nodeLocation: "0", accessType: "READ"}]-> Field(.01)`

#### Scenario 2: Multiple Field Updates
```mumps
S ^DPT(DFN,0)=NAME_"^"_SEX_"^"_DOB  ; Writing fields .01, .02, .03
```
Creates multiple ACCESSES_FIELD relationships for each field being written.

#### Scenario 3: Cross-Reference Access
```mumps
S DFN=$O(^DPT("B",NAME,""))  ; Using B cross-reference
```
Creates: `Label -[ACCESSES_FIELD {crossReference: "B", accessType: "READ"}]-> Field(.01)`

## Success Metrics
- Reduction in time to perform field change impact analysis (target: 80% reduction)
- Increase in accuracy of identifying affected routines (target: 95%+ accuracy)
- Number of previously hidden field dependencies discovered

