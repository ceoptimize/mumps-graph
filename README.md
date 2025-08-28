# VistA-M Graph Database

A Neo4j-based graph database implementation for analyzing VistA (Veterans Information Systems and Technology Architecture) medical record system's data dictionary and codebase structure.

## 🎯 Overview

This project transforms VistA's complex hierarchical data structures into a queryable graph database, enabling:
- Visual exploration of file/field relationships
- Cross-reference analysis
- Subfile hierarchy mapping
- Package dependency tracking
- MUMPS routine and label code structure analysis
- Code flow and call graph analysis

## 📊 What Gets Loaded

The graph database contains (after all phases):

### Phase 1 & 2 - Data Dictionary Structure
**Nodes (117,590 total)**
- **195 Packages** - VistA application modules
- **7,939 Files** - Data dictionary file definitions  
- **95,955 Fields** - Individual field definitions
- **13,501 CrossReferences** - Index definitions

**Relationships (126,207 total)**
- **CONTAINS_FILE** (2,790) - Package ownership of files
- **CONTAINS_FIELD** (95,955) - File-to-field relationships
- **POINTS_TO** (8,376) - Pointer field references
- **INDEXED_BY** (13,501) - Field cross-reference indexes
- **SUBFILE_OF** (5,585) - Hierarchical subfile relationships

### Phase 3 - Code Structure
**Additional Nodes (336,649 total)**
- **33,951 Routines** - MUMPS routine files
- **302,698 Labels** - Entry points, functions, and subroutines

**Additional Relationships (308,974 total)**
- **CONTAINS_LABEL** (302,698) - Routine-to-label relationships
- **OWNS_ROUTINE** (6,276) - Package-to-routine relationships

## 🚀 Complete Loading Process

### Prerequisites

- Docker installed and running
- Python 3.8 or higher
- UV package manager ([install instructions](https://github.com/astral-sh/uv))
- ~2GB free disk space
- 4GB RAM (8GB recommended)

### Step-by-Step Installation

#### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/VistA-M.git
cd VistA-M

# Install Python dependencies
uv sync
```

#### 2. Start Neo4j Database
```bash
# Start Neo4j container
docker-compose -f docker/docker-compose.yml up -d

# Wait for Neo4j to be ready (takes ~10 seconds)
sleep 10

# Verify Neo4j is running
curl -f http://localhost:7474 || echo "Neo4j not ready yet"
```

Neo4j will be accessible at http://localhost:7474 with credentials neo4j/password

#### 3. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env if needed (default settings should work)
# Default Neo4j port is 7688 to avoid conflicts
```

#### 4. Database Management

**Clean/Reset Database:**
```bash
# Use the cleanup script for safe database clearing
uv run python cleanup_database.py
# This will prompt for confirmation before deleting all data
```

#### 5. Load the Complete Graph

```bash
# Phase 1: Load basic structure (2-3 minutes)
# Creates: Package, File, Field nodes
# Creates: CONTAINS_FILE, CONTAINS_FIELD, POINTS_TO relationships
uv run python -m src.main --phase 1

# Phase 2: Load enhanced relationships (1-2 minutes)
# Creates: CrossReference nodes
# Creates: INDEXED_BY, SUBFILE_OF relationships
uv run python -m src.main --phase 2

# OPTIONAL - Phase 3: Load code structure (requires VistA-M source code)
# First, create indexes for optimal performance
uv run python create_phase3_indexes.py

# Then load all MUMPS routines and labels (~30 seconds with indexes)
# Creates: Routine and Label nodes
# Creates: CONTAINS_LABEL and OWNS_ROUTINE relationships
uv run python -m src.main --phase 3 --all-packages

# Or load just Registration package for testing (~2 seconds)
uv run python -m src.main --phase 3
```

#### 6. Verify the Load

Open Neo4j Browser at http://localhost:7474 and run:

```cypher
// Check total counts
MATCH (n) RETURN labels(n)[0] as Type, count(n) as Count
ORDER BY Count DESC

// Should return (Phases 1-2):
// Field           95,955
// CrossReference  13,501
// File             7,939
// Package            195

// With Phase 3 adds:
// Label          302,698
// Routine         33,951
```

```cypher
// Check relationships
MATCH ()-[r]->() 
RETURN type(r) as Relationship, count(r) as Count
ORDER BY Count DESC

// Should return (Phases 1-2):
// CONTAINS_FIELD   95,955
// INDEXED_BY       13,501
// POINTS_TO         8,376
// SUBFILE_OF        5,585
// CONTAINS_FILE     2,790

// With Phase 3 adds:
// CONTAINS_LABEL  302,698
// OWNS_ROUTINE      6,276
```

### Complete Reload Process

If you need to reload the data (e.g., after updates to source files):

```bash
# Quick reload for Phases 1-2 only
uv run python cleanup_database.py && \
uv run python -m src.main --phase 1 && \
uv run python -m src.main --phase 2
# Total time: ~5 minutes

# Full reload including all code structure (Phases 1-3)
uv run python cleanup_database.py && \
uv run python -m src.main --phase 1 && \
uv run python -m src.main --phase 2 && \
uv run python create_phase3_indexes.py && \
uv run python -m src.main --phase 3 --all-packages
# Total time: ~6 minutes with indexes

# Validate the complete load
uv run python validate_phase3_graph.py
```

## 🔍 Exploring the Graph

### Neo4j Browser Quick Start

1. Navigate to http://localhost:7474
2. Login with neo4j/password
3. Try these starter queries:

**See the entire schema:**
```cypher
CALL db.schema.visualization()
```

**Find the PATIENT file and its fields:**
```cypher
MATCH (f:File {number: "2", name: "PATIENT"})-[:CONTAINS_FIELD]->(field)
RETURN f, field
LIMIT 25
```

**Explore cross-references on a field:**
```cypher
MATCH (f:Field {name: "NAME", file_number: "2"})-[r:INDEXED_BY]->(x:CrossReference)
RETURN f, r, x
```

**Trace subfile hierarchy:**
```cypher
MATCH path = (child:File)-[:SUBFILE_OF*]->(parent:File {number: "2"})
RETURN path
```

**View a package's files:**
```cypher
MATCH (p:Package {name: "VA FILEMAN"})-[:CONTAINS_FILE]->(f:File)
RETURN p, f
LIMIT 50
```

### Advanced Analysis Queries

**Files with most fields:**
```cypher
MATCH (f:File)-[:CONTAINS_FIELD]->(field)
RETURN f.name, f.number, count(field) as field_count
ORDER BY field_count DESC
LIMIT 10
```

**Most referenced files (pointer targets):**
```cypher
MATCH (field:Field)-[:POINTS_TO]->(f:File)
RETURN f.name, f.number, count(field) as references
ORDER BY references DESC
LIMIT 10
```

**Complex subfile structures:**
```cypher
MATCH (f:File)
WHERE f.number CONTAINS "."
WITH f, size(split(f.number, ".")) as depth
RETURN f.name, f.number, depth
ORDER BY depth DESC
LIMIT 10
```

## 🗂️ Project Structure

```
VistA-M/
├── src/
│   ├── main.py              # Entry point with phase selection
│   ├── parsers/
│   │   ├── zwr_parser.py    # Parses DD.zwr data dictionary
│   │   └── csv_parser.py    # Parses Packages.csv
│   ├── graph/
│   │   ├── builder.py       # Creates nodes and relationships
│   │   ├── connection.py    # Neo4j connection handler
│   │   └── queries.py       # Cypher query templates (with MERGE for idempotency)
│   └── models/
│       ├── nodes.py         # Node data models
│       └── relationships.py # Relationship models
├── tests/                   # Comprehensive test suite
├── docker/
│   └── docker-compose.yml   # Neo4j configuration
├── Vista-M-source-code/     # VistA source files (not in git)
│   ├── DD.zwr              # Data Dictionary (~765K lines)
│   ├── FILE.zwr            # File metadata
│   └── Packages.csv        # Package definitions
└── .env                    # Configuration settings
```

## ⚙️ Configuration

Settings are defined in `.env`:

```env
# Neo4j Configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
NEO4J_DATABASE=neo4j

# File Paths (relative to project root)
DD_FILE_PATH=Vista-M-source-code/Packages/VA FileMan/Globals/DD.zwr
FILE_PATH=Vista-M-source-code/Packages/VA FileMan/Globals/FILE.zwr
PACKAGES_CSV_PATH=Vista-M-source-code/Packages.csv

# Processing Configuration
BATCH_SIZE=1000  # Nodes per batch
MAX_WORKERS=4     # Parallel workers
LOG_LEVEL=INFO    # DEBUG for troubleshooting
```

## 🛠️ Troubleshooting

### Issue: "Phase 2 shows 0 relationships created"
**Solution:** This is normal if relationships already exist. Check the validation output instead. The code uses MERGE operations to prevent duplicates.

### Issue: "Duplicate nodes after re-running Phase 1"
**Solution:** Phase 1 uses CREATE operations for performance. Always clear the database before re-running:
```bash
uv run python -c "
from neo4j import GraphDatabase
driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
driver.session().run('MATCH (n) DETACH DELETE n')
driver.close()
"
```

### Issue: "Neo4j won't start"
**Solution:** Check Docker is running and ports are free:
```bash
# Check if port 7687 is in use
lsof -i :7687

# Restart Docker containers
docker-compose -f docker/docker-compose.yml down
docker-compose -f docker/docker-compose.yml up -d
```

### Issue: "Import is very slow"
**Solution:** 
1. Ensure Docker has enough memory (Settings > Resources > Memory: 4GB+)
2. Check disk space (need ~2GB free)
3. Reduce BATCH_SIZE in .env if memory constrained

### Cleaning Up Duplicate Nodes

If you accidentally created duplicates by running phases multiple times:

```python
# Save as cleanup_duplicates.py
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()
driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
)

with driver.session() as session:
    # Remove duplicate CrossReferences
    session.run("""
        MATCH (x:CrossReference)
        WITH x.xref_id as xref_id, COLLECT(x) as nodes
        WHERE SIZE(nodes) > 1
        FOREACH (n IN TAIL(nodes) | DETACH DELETE n)
    """)
    
    # Remove duplicate relationships
    session.run("""
        MATCH (f:Field)-[r:INDEXED_BY]->(x:CrossReference)
        WITH f, x, COLLECT(r) as rels
        WHERE SIZE(rels) > 1
        FOREACH (rel IN TAIL(rels) | DELETE rel)
    """)
    
    print("Duplicates cleaned")

driver.close()
```

## 🐛 Known Issues & Limitations

1. **Orphan Files (~65% of files)** - This is expected behavior:
   - Subfiles (e.g., "2.01") are connected via SUBFILE_OF, not CONTAINS_FILE
   - System files (number < 1.0) are FileMan infrastructure
   - Some files exist in DD but aren't assigned to packages

2. **Variable Pointer Relationships** - Currently 0 in most datasets:
   - Variable pointers are stored differently in DD.zwr
   - Full implementation pending in Phase 3

3. **Memory Usage** - Large batches may cause memory issues:
   - Reduce BATCH_SIZE in .env if needed
   - Default 1000 works well for 8GB systems

## 🧪 Testing

Run the comprehensive test suite:
```bash
# All tests
uv run pytest tests/ -v

# Specific phase tests
uv run pytest tests/test_phase1_builder.py -v
uv run pytest tests/test_phase2_builder.py -v

# With coverage report
uv run pytest tests/ --cov=src --cov-report=html
# View coverage at htmlcov/index.html
```

## 🚧 Roadmap

### ✅ Completed
- Phase 1: Basic structure (Packages, Files, Fields)
- Phase 2: Static relationships (CrossReferences, Subfiles)
- Duplicate prevention (MERGE operations)
- Comprehensive test coverage

### Phase 3: Code Structure (In Development)
- Parse 33,951 MUMPS routine files
- Create Routine and Label nodes
- Map code flow relationships (CALLS, INVOKES)
- Connect code to data model

### Phase 4: Code Relationships (Planned)
- Extract DO, GOTO, $$ calls
- Map global access patterns
- Build confidence scoring
- Dead code detection

### Phase 5: Enhancement (Planned)
- Calculate code metrics (cyclomatic complexity)
- Add validation rules from DD
- Performance optimization
- GraphQL API layer

## 📖 Understanding VistA Structure

### Files and Fields
- **Files** are database tables (e.g., File #2 = PATIENT)
- **Fields** are columns within files (e.g., Field .01 = NAME)
- **Subfiles** enable hierarchical data (e.g., 2.01 = Patient Aliases)
- Numbers < 1.0 are system files, > 1.0 are application files

### Cross-References (Indexes)
- Provide fast lookups on fields
- Types: Regular, MUMPS code, Trigger, New-style
- Stored in ^DD(file,field,1,xref_number) nodes
- Essential for FileMan's operation

### Packages
- Logical application groupings
- Own specific file number ranges
- Examples: 
  - VA FILEMAN (1-1.9999)
  - KERNEL (3.2-19.9)
  - PHARMACY (50-59)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests before committing
4. Ensure code follows project style (uv run ruff check)
5. Submit a pull request

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- VistA development community
- VA for open-sourcing VistA
- Neo4j for graph database technology
- UV for modern Python packaging

## 📧 Contact

[Your contact information]

---

**Performance Metrics:**
- **Loading Time**: ~5 minutes for complete graph
- **Database Size**: ~500MB when loaded  
- **Query Performance**: Most queries < 100ms
- **Requirements**: 4GB RAM minimum, 8GB recommended  
- **Tested On**: Python 3.8-3.12, Neo4j 4.4-5.x, Docker 20+