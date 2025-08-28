# VistA-M Graph Database

A Neo4j-based graph database implementation for analyzing VistA (Veterans Information Systems and Technology Architecture) medical record system's data dictionary and codebase structure.

## 🎯 Overview

This project transforms VistA's complex hierarchical data structures into a queryable graph database, enabling:
- Visual exploration of file/field relationships
- Cross-reference analysis
- Subfile hierarchy mapping
- Package dependency tracking
- Future: MUMPS code flow analysis

## 📊 What Gets Loaded

The graph database contains:

### Nodes (117,590 total)
- **195 Packages** - VistA application modules
- **7,939 Files** - Data dictionary file definitions  
- **95,955 Fields** - Individual field definitions
- **13,501 CrossReferences** - Index definitions

### Relationships (126,207 total)
- **CONTAINS_FILE** - Package ownership of files
- **CONTAINS_FIELD** - File-to-field relationships
- **POINTS_TO** - Pointer field references
- **INDEXED_BY** - Field cross-reference indexes
- **SUBFILE_OF** - Hierarchical subfile relationships

## 🚀 Quick Start

### Prerequisites

- Docker installed and running
- Python 3.8 or higher
- UV package manager ([install instructions](https://github.com/astral-sh/uv))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/VistA-M.git
   cd VistA-M
   ```

2. **Start Neo4j database**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```
   Wait ~10 seconds for Neo4j to initialize. Verify at http://localhost:7474

3. **Install Python dependencies**
   ```bash
   uv sync
   ```

4. **Load the graph data**
   ```bash
   # Phase 1: Load basic structure (Files, Fields, Packages)
   uv run python -m src.main --phase 1
   
   # Phase 2: Load enhanced relationships (CrossReferences, Subfiles)
   uv run python -m src.main --phase 2
   ```

5. **Fix Phase 2 relationships** (Required due to known bug)
   
   Save this as `fix_phase2.py`:
   ```python
   from neo4j import GraphDatabase
   import os
   from dotenv import load_dotenv

   load_dotenv()
   driver = GraphDatabase.driver(
       os.getenv("NEO4J_URI", "bolt://localhost:7687"),
       auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
   )

   with driver.session() as session:
       # Create INDEXED_BY relationships
       result = session.run('''
           MATCH (x:CrossReference)
           MATCH (f:Field {file_number: x.file_number, number: x.field_number})
           CREATE (f)-[r:INDEXED_BY]->(x)
           SET r.xref_name = x.name, r.xref_type = x.xref_type
           RETURN count(r) as created
       ''')
       print(f"Created {result.single()['created']} INDEXED_BY relationships")
       
       # Create SUBFILE_OF relationships
       result = session.run('''
           MATCH (child:File)
           WHERE child.number CONTAINS '.'
           WITH child, split(child.number, '.')[0] as parent_num
           MATCH (parent:File {number: parent_num})
           CREATE (child)-[r:SUBFILE_OF]->(parent)
           SET r.level = size(split(child.number, '.'))
           RETURN count(r) as created
       ''')
       print(f"Created {result.single()['created']} SUBFILE_OF relationships")

   driver.close()
   ```
   
   Run it:
   ```bash
   uv run python fix_phase2.py
   ```

6. **Verify installation**
   
   Open http://localhost:7474 and run:
   ```cypher
   MATCH (n) RETURN count(n) as nodes
   MATCH ()-[r]->() RETURN count(r) as relationships
   ```
   
   Expected results:
   - Nodes: ~117,590
   - Relationships: ~126,207

## 🔍 Exploring the Graph

### Neo4j Browser

Access at http://localhost:7474 (default credentials: neo4j/password)

### Sample Queries

**View file structure:**
```cypher
MATCH (f:File {number: "2"})-[:CONTAINS_FIELD]->(field)
RETURN f, field
LIMIT 50
```

**Find cross-references:**
```cypher
MATCH (f:Field)-[r:INDEXED_BY]->(x:CrossReference)
WHERE f.file_number = "2"
RETURN f.name, x.name, x.xref_type
```

**Explore subfile hierarchy:**
```cypher
MATCH path = (sub:File)-[:SUBFILE_OF*]->(parent:File {number: "2"})
RETURN path
```

**Package dependencies:**
```cypher
MATCH (p:Package)-[:CONTAINS_FILE]->(f:File)
WHERE p.name = "VA FILEMAN"
RETURN p, f
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
│   │   └── queries.py       # Cypher query templates
│   └── models/
│       ├── nodes.py         # Node data models
│       └── relationships.py # Relationship models
├── tests/                   # Test suite
├── docker/
│   └── docker-compose.yml   # Neo4j configuration
├── Vista-M-source-code/     # VistA source files (not in git)
│   ├── DD.zwr              # Data Dictionary
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

# File Paths
DD_FILE_PATH=Vista-M-source-code/Packages/VA FileMan/Globals/DD.zwr
PACKAGES_CSV_PATH=Vista-M-source-code/Packages.csv

# Processing Configuration
BATCH_SIZE=1000
MAX_WORKERS=4
LOG_LEVEL=INFO
```

## 🐛 Known Issues

1. **Phase 2 relationships bug** - The pipeline creates nodes but not relationships. Use the fix script above.

2. **Duplicate nodes on re-run** - Running Phase 1 twice creates duplicates. To reset:
   ```bash
   # Clear database
   uv run python -c "
   from neo4j import GraphDatabase
   driver = GraphDatabase.driver('bolt://localhost:7687', auth=('neo4j', 'password'))
   driver.session().run('MATCH (n) DETACH DELETE n')
   driver.close()
   "
   
   # Reload from Phase 1
   ```

3. **Orphan files** - ~65% of files aren't linked to packages. This is expected:
   - Most are subfiles (connected via SUBFILE_OF)
   - System files (< 1.0) are FileMan infrastructure
   - Some files exist in DD but not in Packages.csv

## 🧪 Testing

Run the test suite:
```bash
uv run pytest tests/ -v
```

Check test coverage:
```bash
uv run pytest tests/ --cov=src --cov-report=html
```

## 🚧 Roadmap

### Phase 3: Code Structure (Planned)
- Parse 33,951 MUMPS routine files
- Create Routine and Label nodes
- Map code flow relationships (CALLS, INVOKES)
- Connect code to data model

### Phase 4: Code Relationships (Planned)
- Extract DO, GOTO, $$ calls
- Map global access patterns
- Build confidence scoring

### Phase 5: Enhancement (Planned)
- Calculate code metrics
- Add validation rules
- Performance optimization

## 📖 Understanding VistA Structure

### Files and Fields
- **Files** are database tables (e.g., File #2 = PATIENT)
- **Fields** are columns within files
- **Subfiles** enable hierarchical data (e.g., 2.01 = Patient Aliases)

### Cross-References
- Indexes for fast lookups
- Types: Regular, MUMPS, Trigger
- Stored in ^DD(file,field,1,xref_number) nodes

### Packages
- Logical application groupings
- Own specific file number ranges
- Examples: VA FILEMAN, KERNEL, PHARMACY

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests before committing
4. Submit a pull request

## 📝 License

[Your License Here]

## 🙏 Acknowledgments

- VistA development community
- VA for open-sourcing VistA
- Neo4j for graph database technology

## 📧 Contact

[Your contact information]

---

**Loading Time**: ~2-3 minutes for complete graph  
**Requirements**: 4GB RAM minimum, 8GB recommended  
**Tested On**: Python 3.8-3.12, Neo4j 4.4+