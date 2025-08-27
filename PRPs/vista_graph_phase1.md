name: "VistA Graph Database Phase 1 - Foundation Implementation"
description: |

## Purpose
Implement Phase 1 of the VistA Graph Database roadmap, creating the core schema infrastructure with Neo4j, ZWR parser, and package mapping to establish the foundation for graph-based VistA-M analysis.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Build the foundational graph database infrastructure for VistA-M codebase analysis by:
- Setting up Neo4j Community Edition with Docker
- Creating a robust ZWR parser for DD.zwr format
- Parsing Packages.csv for package-to-prefix mapping
- Creating foundational nodes (Package, File, Field) and relationships

## Why
- **Business value**: Enable impact analysis and dependency tracking in VistA-M
- **Integration**: Foundation for all future graph analysis phases
- **Problems solved**: Currently no structured way to understand VistA's complex interdependencies
- **For whom**: VistA developers, modernization teams, and maintainers

## What
A working Neo4j database populated with:
- All Package nodes from Packages.csv
- File and Field nodes from DD.zwr
- Basic CONTAINS_FIELD relationships
- Confidence scoring on all relationships

### Success Criteria
- [ ] Neo4j database running with Docker
- [ ] ZWR parser successfully parses 100% of DD.zwr
- [ ] All packages mapped from Packages.csv
- [ ] Cypher queries return correct file/field structures
- [ ] Unit tests pass with 80%+ coverage
- [ ] Performance: Parse and load complete DD in <30 seconds

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://neo4j.com/docs/api/python-driver/current/
  why: Official Neo4j Python driver documentation for connection and queries
  
- url: https://neo4j.com/docs/cypher-manual/current/
  why: Cypher query language reference for creating nodes and relationships
  
- file: /Users/christieentwistle/VSCodeProjects/VistA-M/Vista-M-source-code/Packages/VA FileMan/Globals/DD.zwr
  why: Main data dictionary file to parse - contains all file/field definitions
  
- file: /Users/christieentwistle/VSCodeProjects/VistA-M/Vista-M-source-code/Packages.csv
  why: Package definitions with prefixes and file ranges
  
- doc: https://hub.docker.com/_/neo4j
  section: Running Neo4j Community Edition
  critical: Use :latest tag and proper volume mapping for data persistence
  
- file: /Users/christieentwistle/VSCodeProjects/VistA-M/vista_graph_implementation_roadmap.md
  why: Complete implementation specification and phase details
```

### Current Codebase tree
```bash
/Users/christieentwistle/VSCodeProjects/VistA-M/
├── CLAUDE.md
├── PRPs/
│   ├── EXAMPLE_multi_agent_prp.md
│   ├── templates/
│   │   └── prp_base.md
│   └── vista_discovery_phase1.md
├── Vista-M-source-code/
│   ├── Packages.csv
│   └── Packages/
│       └── [Multiple package directories with .zwr and .m files]
├── feature_1.md
└── vista_graph_implementation_roadmap.md
```

### Desired Codebase tree with files to be added
```bash
/Users/christieentwistle/VSCodeProjects/VistA-M/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   └── settings.py  # Neo4j connection settings
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── zwr_parser.py  # ZWR format parser
│   │   └── csv_parser.py  # Packages.csv parser
│   ├── models/
│   │   ├── __init__.py
│   │   ├── nodes.py  # Pydantic models for graph nodes
│   │   └── relationships.py  # Relationship definitions
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── connection.py  # Neo4j connection management
│   │   ├── builder.py  # Main graph builder class
│   │   └── queries.py  # Cypher query templates
│   └── main.py  # Entry point for Phase 1 execution
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_zwr_parser.py
│   ├── test_csv_parser.py
│   ├── test_graph_builder.py
│   └── fixtures/
│       ├── sample_dd.zwr
│       └── sample_packages.csv
├── docker/
│   └── docker-compose.yml  # Neo4j setup
├── pyproject.toml  # UV package management
├── README.md  # Project documentation
└── .env.example  # Environment variables template
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: py2neo is EOL/deprecated - use official neo4j driver
# Example: from neo4j import GraphDatabase (NOT from py2neo import Graph)

# CRITICAL: Neo4j Community Edition limitations
# - No role-based access control
# - Single database only
# - No clustering

# CRITICAL: ZWR format uses MUMPS global syntax
# Example: ^DD(0,0)="ATTRIBUTE^N^999^41" 
# Parse pattern: ^GLOBAL(subscripts)=value

# CRITICAL: Use batch imports for performance
# Neo4j can timeout with individual CREATE statements for large datasets
# Use UNWIND for batch operations

# CRITICAL: Docker volume mapping required for persistence
# Without volumes, data is lost on container restart
```

## Implementation Blueprint

### Data models and structure

```python
# src/models/nodes.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from uuid import uuid4

class PackageNode(BaseModel):
    """Package organizational unit"""
    package_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    directory: str
    prefixes: List[str] = []
    vdl_id: Optional[str] = None
    
class FileNode(BaseModel):
    """File/Table definition from DD"""
    file_id: str = Field(default_factory=lambda: str(uuid4()))
    number: str  # e.g., "2" for PATIENT file
    name: str  # e.g., "PATIENT"
    global_root: Optional[str] = None  # e.g., "^DPT"
    parent_file: Optional[str] = None  # For subfiles
    is_subfile: bool = False
    
class FieldNode(BaseModel):
    """Field definition within a file"""
    field_id: str = Field(default_factory=lambda: str(uuid4()))
    number: str  # e.g., ".01"
    name: str  # e.g., "NAME"
    file_number: str  # Parent file number
    data_type: str  # F, N, D, P, S, C, W, V
    required: bool = False
    is_pointer: bool = False
    is_computed: bool = False
    target_file: Optional[str] = None  # For pointer fields
    mumps_code: Optional[str] = None  # For computed fields
```

### List of tasks to be completed
Please create a new project in Archon and create and manage and move tasks there according to the below. 

```yaml
Task 1: Project Setup and Dependencies
CREATE pyproject.toml:
  - Setup UV configuration
  - Add dependencies: neo4j, pydantic, python-dotenv, rich
  - Add dev dependencies: pytest, ruff, mypy, pytest-cov
  
CREATE .env.example:
  - NEO4J_URI=bolt://localhost:7687
  - NEO4J_USER=neo4j
  - NEO4J_PASSWORD=password
  - NEO4J_DATABASE=neo4j

Task 2: Docker Setup for Neo4j
CREATE docker/docker-compose.yml:
  - Use neo4j:latest image
  - Map ports 7687 (bolt) and 7474 (browser)
  - Set volumes for data persistence
  - Configure environment variables

Task 3: Configuration Module
CREATE src/config/settings.py:
  - Load environment variables
  - Define Neo4j connection parameters
  - Add file path configurations
  - Use pydantic_settings for validation

Task 4: ZWR Parser Implementation
CREATE src/parsers/zwr_parser.py:
  - Parse global syntax: ^GLOBAL(subscripts)=value
  - Handle escaped characters
  - Extract file definitions from ^DD
  - Extract field definitions
  - Handle multi-line values

Task 5: Package CSV Parser
CREATE src/parsers/csv_parser.py:
  - Parse Packages.csv format
  - Handle multi-row packages
  - Extract prefixes array
  - Map file numbers to packages

Task 6: Graph Connection Management
CREATE src/graph/connection.py:
  - Neo4j driver initialization
  - Connection pooling
  - Session management
  - Error handling and retries

Task 7: Graph Builder Core
CREATE src/graph/builder.py:
  - Create indexes on key properties
  - Batch import functionality
  - Create Package nodes
  - Create File/Field nodes
  - Create relationships

Task 8: Query Templates
CREATE src/graph/queries.py:
  - Cypher templates for CRUD operations
  - Batch import queries with UNWIND
  - Index creation queries
  - Validation queries

Task 9: Main Execution Script
CREATE src/main.py:
  - Parse command line arguments
  - Initialize Neo4j connection
  - Execute Phase 1 pipeline
  - Progress reporting with rich

Task 10: Comprehensive Testing
CREATE tests/:
  - Unit tests for each parser
  - Integration tests for graph builder
  - Sample fixtures for testing
  - Mock Neo4j for unit tests
```

### Per task pseudocode

```python
# Task 4: ZWR Parser Pseudocode
class ZWRParser:
    def parse_line(self, line: str) -> Dict[str, Any]:
        # Pattern: ^GLOBAL(subscripts)=value
        match = re.match(r'^\^(\w+)\((.*?)\)="(.*)"$', line)
        if match:
            global_name = match.group(1)  # "DD"
            subscripts = self.parse_subscripts(match.group(2))  # ["0", "0"]
            value = self.unescape_value(match.group(3))
            return {
                "global": global_name,
                "subscripts": subscripts, 
                "value": value
            }
    
    def extract_file_definitions(self, lines: List[str]) -> List[FileNode]:
        # Look for ^DD(file_number,0) entries
        files = {}
        for line in lines:
            parsed = self.parse_line(line)
            if parsed["global"] == "DD" and len(parsed["subscripts"]) == 2:
                if parsed["subscripts"][1] == "0":
                    file_num = parsed["subscripts"][0]
                    # Parse: "FILE_NAME^GLOBAL^..."
                    parts = parsed["value"].split("^")
                    files[file_num] = FileNode(
                        number=file_num,
                        name=parts[0],
                        global_root=parts[1] if len(parts) > 1 else None
                    )
        return list(files.values())

# Task 7: Graph Builder Pseudocode  
class GraphBuilder:
    def __init__(self, driver):
        self.driver = driver
        
    def create_indexes(self):
        queries = [
            "CREATE INDEX file_number IF NOT EXISTS FOR (f:File) ON (f.number)",
            "CREATE INDEX package_name IF NOT EXISTS FOR (p:Package) ON (p.name)",
            "CREATE INDEX field_composite IF NOT EXISTS FOR (f:Field) ON (f.file_number, f.number)"
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query)
    
    def batch_create_nodes(self, nodes: List[BaseModel], label: str):
        # Use UNWIND for batch import
        query = f"""
        UNWIND $batch AS item
        CREATE (n:{label})
        SET n = item
        """
        # Process in chunks of 1000 for performance
        for chunk in chunks(nodes, 1000):
            batch_data = [node.dict() for node in chunk]
            with self.driver.session() as session:
                session.run(query, batch=batch_data)
```

### Integration Points
```yaml
DOCKER:
  - file: docker/docker-compose.yml
  - command: "docker-compose -f docker/docker-compose.yml up -d"
  - verify: "curl http://localhost:7474"
  
NEO4J:
  - connection: bolt://localhost:7687
  - browser: http://localhost:7474
  - credentials: neo4j/password (change in production)
  
DATA_SOURCES:
  - dd_file: Vista-M-source-code/Packages/VA FileMan/Globals/DD.zwr
  - packages_csv: Vista-M-source-code/Packages.csv
  - globals_dir: Vista-M-source-code/Packages/*/Globals/*.zwr
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Setup project first
uv venv
uv sync

# Run these FIRST - fix any errors before proceeding
uv run ruff check src/ --fix  # Auto-fix what's possible
uv run mypy src/              # Type checking

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests
```python
# tests/test_zwr_parser.py
import pytest
from src.parsers.zwr_parser import ZWRParser

def test_parse_simple_global():
    """Test parsing basic global line"""
    parser = ZWRParser()
    result = parser.parse_line('^DD(0,0)="ATTRIBUTE^N^999^41"')
    assert result["global"] == "DD"
    assert result["subscripts"] == ["0", "0"]
    assert result["value"] == "ATTRIBUTE^N^999^41"

def test_extract_file_definitions():
    """Test extracting file nodes from DD"""
    parser = ZWRParser()
    lines = [
        '^DD(2,0)="PATIENT^DPT^^ ^K:X X"',
        '^DD(2,.01,0)="NAME^RF^^0;1^K:$L(X)>30 X"'
    ]
    files = parser.extract_file_definitions(lines)
    assert len(files) == 1
    assert files[0].number == "2"
    assert files[0].name == "PATIENT"
    assert files[0].global_root == "^DPT"

def test_handle_escaped_quotes():
    """Test handling escaped characters in ZWR"""
    parser = ZWRParser()
    result = parser.parse_line('^DD(0,0)="TEST""VALUE"')
    assert result["value"] == 'TEST"VALUE'
```

```bash
# Run and iterate until passing:
uv run pytest tests/ -v --cov=src --cov-report=html
# If failing: Read error, understand root cause, fix code, re-run
```

### Level 3: Integration Test
```bash
# Start Neo4j
docker-compose -f docker/docker-compose.yml up -d

# Wait for Neo4j to be ready
sleep 10

# Run the main script
uv run python -m src.main --phase 1 --source Vista-M-source-code/

# Verify in Neo4j Browser (http://localhost:7474)
# Run Cypher query:
# MATCH (p:Package) RETURN count(p)
# Expected: Should return count of packages from Packages.csv

# Check file nodes:
# MATCH (f:File) RETURN f.number, f.name LIMIT 10
# Expected: Should show file definitions from DD.zwr
```

### Level 4: Performance Test
```bash
# Time the full import
time uv run python -m src.main --phase 1 --source Vista-M-source-code/

# Expected: < 30 seconds for complete DD.zwr parsing and loading
# If slow: Check batch size, add progress bars, optimize queries
```

## Final Validation Checklist
- [ ] All tests pass: `uv run pytest tests/ -v`
- [ ] No linting errors: `uv run ruff check src/`
- [ ] No type errors: `uv run mypy src/`
- [ ] Docker containers running: `docker ps`
- [ ] Neo4j accessible at http://localhost:7474
- [ ] Sample queries return expected results
- [ ] DD.zwr fully parsed without errors
- [ ] Packages.csv mapped correctly
- [ ] Relationships created between files and fields
- [ ] Performance target met (<30 seconds)

---

## Anti-Patterns to Avoid
- ❌ Don't use py2neo (it's EOL) - use official neo4j driver
- ❌ Don't create nodes one by one - use batch UNWIND
- ❌ Don't skip index creation - queries will be slow
- ❌ Don't hardcode file paths - use config
- ❌ Don't ignore parsing errors - log and handle gracefully
- ❌ Don't load entire DD.zwr into memory at once - stream it

## Confidence Score: 8/10

High confidence due to:
- Clear data formats (ZWR, CSV)
- Well-defined schema from roadmap
- Official Neo4j driver documentation
- Straightforward parsing requirements

Points deducted for:
- MUMPS parser complexity (deferred to later phase)
- Potential ZWR edge cases not yet discovered