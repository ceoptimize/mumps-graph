name: "VistA-M Discovery Phase 1: Comprehensive Extraction Engine"
description: |

## Purpose
Build a comprehensive extraction engine that extracts EVERYTHING from the VistA-M repository without assumptions, creating the foundation for pattern discovery and analysis.

## Core Principles
1. **Zero Assumptions**: Extract every pattern without preconceptions
2. **Pattern-Driven**: Let the data reveal its structure naturally  
3. **Evidence-Based**: All findings must be backed by empirical discovery
4. **Comprehensive**: Better to over-extract than miss critical patterns
5. **MUMPS-Aware**: Handle special characters and syntax unique to M language

---

## Goal
Implement Phase 1 of the Pure Discovery approach: Create a Python-based extraction engine that processes EVERY file in the VistA-M repository, extracting all identifiable patterns, structures, and relationships without filtering or prioritization. The output should be comprehensive JSON datasets containing all discovered elements for later analysis.

## Why
- **Legacy Understanding**: VistA is a 40+ year old system with unknown patterns and conventions
- **Comprehensive Coverage**: Missing patterns could lead to critical gaps in understanding
- **Foundation for Analysis**: This extraction forms the basis for all subsequent pattern discovery
- **Evidence-Based Schema**: Future graph schemas will be derived from actual data, not assumptions

## What
A Python extraction engine that:
- Processes all .m (MUMPS routines), .zwr (globals), and .csv files
- Extracts every identifiable element from each line of code
- Preserves full context for every extraction
- Outputs structured JSON with complete extraction data
- Handles MUMPS-specific syntax and special characters

### Success Criteria
- [ ] Processes 100% of files in Vista-M-source-code directory
- [ ] Extracts all MUMPS-specific patterns (caret patterns, dollar functions, etc.)
- [ ] Generates gigabytes of structured extraction data
- [ ] Preserves complete context for every extraction
- [ ] Successfully handles all MUMPS special characters
- [ ] Outputs valid JSON that can be analyzed in Phase 2

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://en.wikipedia.org/wiki/MUMPS_syntax
  why: Core MUMPS syntax patterns, operators, and special characters
  
- url: https://learnxinyminutes.com/m/
  why: Quick reference for M language patterns and examples
  
- file: /Users/christieentwistle/VSCodeProjects/VistA-M/Claude-Desktop/pure_discovery_approach.md
  why: Contains Phase 1 implementation blueprint and expected outputs

- file: /Users/christieentwistle/VSCodeProjects/VistA-M/Vista-M-source-code/Packages/Accounts Receivable/Routines/PRCAACC.m
  why: Example MUMPS routine showing typical patterns
  
- file: /Users/christieentwistle/VSCodeProjects/VistA-M/Vista-M-source-code/Packages.csv
  why: Understanding package structure and organization

- url: https://vivian.worldvista.org/dox/
  why: VistA cross-reference documentation for validation
  note: Use playwright MCP to browse if needed for specific patterns
```

### Current Codebase Structure
```bash
VistA-M/
├── CLAUDE.md                    # Project guidelines
├── Claude-Desktop/
│   ├── pure_discovery_approach.md  # Phase 1-5 blueprint
│   └── hybrid_iterative_approach.md
├── Vista-M-source-code/
│   ├── Packages.csv             # Package metadata
│   └── Packages/                # Contains all VistA packages
│       ├── [Package Name]/
│       │   ├── Routines/        # .m files (MUMPS code)
│       │   └── Globals/         # .zwr files (data)
│       └── ... (60+ packages)
└── PRPs/
    └── vista_discovery_phase1.md  # This file
```

### Desired Codebase Structure After Implementation
```bash
VistA-M/
├── discovery/                   # New directory for discovery engine
│   ├── __init__.py
│   ├── config.py                # Configuration settings
│   ├── extractor.py             # Main extraction engine
│   ├── patterns.py              # Pattern definitions
│   ├── mumps_parser.py          # MUMPS-specific parsing
│   ├── file_processor.py        # File handling logic
│   ├── output_manager.py        # JSON output management
│   └── tests/
│       ├── test_extractor.py
│       ├── test_mumps_parser.py
│       └── test_patterns.py
├── output/                      # Extraction results
│   ├── raw_extractions.json    # Main extraction data
│   ├── file_metadata.json      # File-level statistics
│   └── extraction_log.json     # Processing log
└── pyproject.toml              # Python dependencies
```

### MUMPS Language Patterns & Gotchas
```python
# CRITICAL: MUMPS Special Characters that MUST be handled
# ^ (caret) - Global variable prefix, also used in routine calls (DO ^ROUTINE)
# $ (dollar) - System functions ($DATA, $ORDER) and intrinsic variables
# ; (semicolon) - Comments (everything after ; is ignored)
# . (period) - Line continuation and decimal points
# ! - New line in WRITE commands
# # - New page in WRITE commands, also modulo operator
# _ - String concatenation operator
# ? - Pattern matching operator
# @ - Indirection operator

# MUMPS Line Structure:
# - Lines starting with no space are labels
# - Lines starting with space/tab contain code
# - Commands are abbreviated (S for SET, D for DO, Q for QUIT)
# - Arguments separated by single space from command
# - Multiple commands on same line separated by space

# Global Variable Patterns:
# ^GLOBAL - Simple global
# ^GLOBAL(subscript) - Subscripted global
# ^GLOBAL(sub1,sub2,sub3) - Multi-dimensional global

# Common MUMPS Patterns to Extract:
# SET variable=value
# DO ^ROUTINE or DO LABEL^ROUTINE
# FOR loops with specific syntax
# IF/ELSE with postconditionals
# $PIECE for string parsing
# $ORDER for traversing globals
```

## Implementation Blueprint

### Data Models and Structure

```python
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import re

class LineExtraction(BaseModel):
    """Extraction data for a single line of code"""
    line_number: int
    raw_line: str
    line_length: int
    whitespace_prefix: int
    is_label: bool  # Lines starting without whitespace
    is_code: bool   # Lines starting with whitespace
    is_comment: bool  # Lines starting with ;
    
    # Token extractions
    all_words: List[str] = Field(default_factory=list)
    all_numbers: List[str] = Field(default_factory=list)
    all_symbols: List[str] = Field(default_factory=list)
    quoted_strings: List[str] = Field(default_factory=list)
    
    # MUMPS-specific patterns
    caret_patterns: List[str] = Field(default_factory=list)  # ^GLOBAL, ^ROUTINE
    dollar_patterns: List[str] = Field(default_factory=list)  # $DATA, $ORDER, etc
    commands: List[str] = Field(default_factory=list)  # S, D, Q, FOR, IF
    assignments: List[str] = Field(default_factory=list)  # VAR=VALUE patterns
    label_references: List[str] = Field(default_factory=list)  # LABEL^ROUTINE
    global_references: List[str] = Field(default_factory=list)  # ^GLOBAL(subscripts)
    comments: List[str] = Field(default_factory=list)  # Text after ;
    
    # Character frequency analysis
    character_counts: Dict[str, int] = Field(default_factory=dict)
    
class FileExtraction(BaseModel):
    """Complete extraction data for a file"""
    file_path: str
    file_type: str  # .m, .zwr, .csv
    file_size: int
    total_lines: int
    extraction_timestamp: datetime
    package_name: Optional[str] = None
    routine_name: Optional[str] = None  # For .m files
    
    # Line-by-line extractions
    line_extractions: List[LineExtraction]
    
    # File-level aggregations
    total_labels: int = 0
    total_globals: int = 0
    total_routines_called: int = 0
    unique_commands: List[str] = Field(default_factory=list)
    unique_globals: List[str] = Field(default_factory=list)
    
class ExtractionConfig(BaseModel):
    """Configuration for extraction process"""
    source_directory: Path = Path("Vista-M-source-code")
    output_directory: Path = Path("output")
    process_limit: Optional[int] = None  # Limit files for testing
    verbose: bool = True
    chunk_size: int = 1000  # Files per output chunk
```

### List of Tasks to Complete

```yaml
Task 1: Project Setup and Configuration
CREATE pyproject.toml:
  - Add dependencies: pydantic, typing-extensions, pathlib
  - Add dev dependencies: pytest, ruff, mypy
  - Configure Python 3.10+ requirement

CREATE discovery/__init__.py:
  - Empty file to make package

CREATE discovery/config.py:
  - Define ExtractionConfig model
  - Set default paths and parameters
  - Add logging configuration

Task 2: MUMPS Pattern Definitions
CREATE discovery/patterns.py:
  - Define regex patterns for MUMPS syntax
  - Pattern for caret globals: r'\^[A-Z0-9$%]+(\([^)]*\))?'
  - Pattern for dollar functions: r'\$\$?[A-Z0-9]+'
  - Pattern for commands: r'^\s*([A-Z]+)\s'
  - Pattern for labels: r'^[A-Z0-9%]+' 
  - Pattern for assignments: r'[A-Z0-9$%]+=\S+'
  - Pattern for comments: r';.*$'

Task 3: MUMPS Parser Implementation  
CREATE discovery/mumps_parser.py:
  - Implement line parser for MUMPS code
  - Extract all tokens and patterns from single line
  - Handle special characters properly
  - Return LineExtraction object

Task 4: File Processor
CREATE discovery/file_processor.py:
  - Process different file types (.m, .zwr, .csv)
  - Extract package/routine names from paths
  - Call mumps_parser for each line
  - Aggregate file-level statistics
  - Return FileExtraction object

Task 5: Main Extraction Engine
CREATE discovery/extractor.py:
  - Scan source directory recursively
  - Process files in batches
  - Handle errors gracefully (log and continue)
  - Track progress with logging
  - Manage memory by chunking output

Task 6: Output Manager
CREATE discovery/output_manager.py:
  - Write extractions to JSON files
  - Handle large outputs by chunking
  - Create summary statistics
  - Generate extraction log

Task 7: Test Suite
CREATE discovery/tests/test_mumps_parser.py:
  - Test pattern extraction for known MUMPS code
  - Test special character handling
  - Test edge cases

CREATE discovery/tests/test_extractor.py:
  - Test end-to-end extraction
  - Test error handling
  - Test output generation

Task 8: Run Extraction
CREATE discovery/run_extraction.py:
  - Main entry point script
  - Configure logging
  - Run full extraction
  - Generate final report
```

### Task Implementation Details

```python
# Task 2: patterns.py - Critical MUMPS Patterns
import re

class MUMPSPatterns:
    """Regex patterns for MUMPS/M language extraction"""
    
    # Global variables (start with ^)
    GLOBAL_SIMPLE = re.compile(r'\^[A-Z0-9$%]+')
    GLOBAL_SUBSCRIPT = re.compile(r'\^[A-Z0-9$%]+\([^)]*\)')
    
    # Dollar functions and variables
    DOLLAR_FUNCTION = re.compile(r'\$\$[A-Z0-9]+')
    DOLLAR_INTRINSIC = re.compile(r'\$[A-Z0-9]+')
    
    # Commands (abbreviated and full)
    COMMAND = re.compile(r'^\s*([A-Z]+)\s')
    ABBREVIATED_COMMAND = re.compile(r'^\s*([SDQIFKGHNMRWX])\s')
    
    # Labels and routines
    LABEL = re.compile(r'^([A-Z0-9%]+)')
    ROUTINE_CALL = re.compile(r'\^[A-Z0-9]+')
    LABEL_ROUTINE = re.compile(r'[A-Z0-9]+\^[A-Z0-9]+')
    
    # Assignments and operators
    ASSIGNMENT = re.compile(r'[A-Z0-9$%]+=')
    STRING_CONCAT = re.compile(r'_')
    PATTERN_MATCH = re.compile(r'\?')
    
    # Comments
    COMMENT = re.compile(r';.*$')
    
    # Quoted strings
    QUOTED_STRING = re.compile(r'"[^"]*"')
    
    # Numbers
    NUMBER = re.compile(r'\b\d+\.?\d*\b')

# Task 3: mumps_parser.py - Line Parser
def extract_everything_from_line(line: str, line_number: int) -> LineExtraction:
    """Extract all identifiable elements from a MUMPS line"""
    extraction = LineExtraction(
        line_number=line_number,
        raw_line=line,
        line_length=len(line),
        whitespace_prefix=len(line) - len(line.lstrip()),
        is_label=not line.startswith((' ', '\t')) and line.strip() != '',
        is_code=line.startswith((' ', '\t')),
        is_comment=line.strip().startswith(';')
    )
    
    # Extract all patterns
    extraction.caret_patterns = MUMPSPatterns.GLOBAL_SUBSCRIPT.findall(line)
    extraction.caret_patterns.extend(MUMPSPatterns.GLOBAL_SIMPLE.findall(line))
    extraction.dollar_patterns = MUMPSPatterns.DOLLAR_FUNCTION.findall(line)
    extraction.dollar_patterns.extend(MUMPSPatterns.DOLLAR_INTRINSIC.findall(line))
    
    # Extract commands
    command_match = MUMPSPatterns.COMMAND.search(line)
    if command_match:
        extraction.commands.append(command_match.group(1))
    
    # Extract other elements
    extraction.quoted_strings = MUMPSPatterns.QUOTED_STRING.findall(line)
    extraction.assignments = MUMPSPatterns.ASSIGNMENT.findall(line)
    extraction.comments = MUMPSPatterns.COMMENT.findall(line)
    extraction.all_numbers = MUMPSPatterns.NUMBER.findall(line)
    
    # Character frequency
    from collections import Counter
    extraction.character_counts = dict(Counter(line))
    
    # Extract all words (alphanumeric sequences)
    extraction.all_words = re.findall(r'\b[A-Z0-9]+\b', line, re.IGNORECASE)
    
    # Extract all symbols
    extraction.all_symbols = re.findall(r'[^\w\s]', line)
    
    return extraction

# Task 5: Main extraction loop pseudocode
async def extract_repository(config: ExtractionConfig):
    """Main extraction orchestration"""
    all_extractions = []
    file_count = 0
    
    # Scan for all files
    for file_path in config.source_directory.rglob("*"):
        if file_path.suffix not in ['.m', '.zwr', '.csv']:
            continue
            
        try:
            # Process file
            file_extraction = await process_file(file_path)
            all_extractions.append(file_extraction)
            file_count += 1
            
            # Chunk output to manage memory
            if len(all_extractions) >= config.chunk_size:
                await write_chunk(all_extractions, chunk_number)
                all_extractions = []
                
        except Exception as e:
            logger.error(f"Failed to process {file_path}: {e}")
            continue
    
    # Write final chunk
    if all_extractions:
        await write_chunk(all_extractions, final_chunk)
    
    return file_count
```

### Integration Points
```yaml
LOGGING:
  - Use standard Python logging
  - Log to: output/extraction.log
  - Include progress indicators
  
OUTPUT:
  - JSON files in output/ directory
  - Chunk large outputs to prevent memory issues
  - Include metadata about extraction run
  
ERROR_HANDLING:
  - Continue on file errors (log and skip)
  - Track failed files for review
  - Generate error summary report
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# After creating files, run these checks
cd /Users/christieentwistle/VSCodeProjects/VistA-M

# Install dependencies
uv add pydantic typing-extensions
uv add --dev pytest ruff mypy

# Check syntax and style
uv run ruff check discovery/ --fix
uv run mypy discovery/

# Expected: No errors
```

### Level 2: Unit Tests
```python
# CREATE discovery/tests/test_mumps_parser.py
import pytest
from discovery.mumps_parser import extract_everything_from_line

def test_extract_global_pattern():
    """Test extraction of global variable patterns"""
    line = ' S ^PRCA(430,BN,0)="TEST"'
    result = extract_everything_from_line(line, 1)
    assert '^PRCA(430,BN,0)' in result.caret_patterns
    assert result.is_code == True
    assert 'S' in result.commands

def test_extract_dollar_function():
    """Test extraction of dollar functions"""
    line = ' S X=$$HTFM^XLFDT(%H)'
    result = extract_everything_from_line(line, 1)
    assert '$$HTFM' in result.dollar_patterns
    assert '^XLFDT' in result.caret_patterns

def test_extract_label():
    """Test label detection"""
    line = 'HTFM(%H,%F) ;$H to FM, %F=1 for date only'
    result = extract_everything_from_line(line, 1)
    assert result.is_label == True
    assert ';$H to FM, %F=1 for date only' in result.comments

def test_extract_assignment():
    """Test assignment pattern extraction"""  
    line = ' S %Y=$E(X,1,3),%M=$E(X,4,5)'
    result = extract_everything_from_line(line, 1)
    assert '%Y=' in result.assignments
    assert '%M=' in result.assignments
```

```bash
# Run tests
uv run pytest discovery/tests/ -v

# Expected: All tests pass
```

### Level 3: Integration Test
```bash
# Create a small test dataset
mkdir -p test_data/Packages/Test/Routines
echo 'TEST ;Test routine
 S ^GLOBAL(1)="value"
 Q' > test_data/Packages/Test/Routines/TEST.m

# Run extraction on test data
uv run python discovery/run_extraction.py --source test_data --output test_output

# Verify output
python -c "import json; data=json.load(open('test_output/raw_extractions.json')); print(f'Extracted {len(data)} files')"

# Expected: Valid JSON with extraction data
```

### Level 4: Full Repository Test
```bash
# Run on actual VistA repository
uv run python discovery/run_extraction.py \
  --source Vista-M-source-code \
  --output output \
  --verbose

# Monitor progress
tail -f output/extraction.log

# Verify results
ls -lh output/*.json
# Expected: Multiple GB of extraction data
```

## Final Validation Checklist
- [ ] All .m, .zwr, and .csv files processed
- [ ] MUMPS special characters correctly extracted
- [ ] Global variable patterns identified
- [ ] Dollar functions captured
- [ ] Commands and labels detected
- [ ] Output is valid JSON
- [ ] No data loss during extraction
- [ ] Memory usage stays reasonable
- [ ] Error handling works (skips bad files)
- [ ] Extraction log is informative

---

## Anti-Patterns to Avoid
- ❌ Don't filter or prioritize patterns - extract everything
- ❌ Don't make assumptions about what's important
- ❌ Don't skip files that seem unimportant
- ❌ Don't lose context when extracting patterns
- ❌ Don't fail on single file errors - log and continue
- ❌ Don't load entire dataset into memory at once

## Expected Output Scale
- **Files Processed**: ~25,000+ files
- **Lines Analyzed**: ~5+ million lines
- **Extraction Size**: 5-10 GB of JSON data
- **Processing Time**: 2-6 hours depending on hardware
- **Pattern Types**: 50+ different pattern categories

## Next Phase Connection
The output from this extraction engine feeds directly into Phase 2: Pattern Discovery & Analysis, where the raw extractions will be analyzed to discover all patterns without filtering or prioritization.

---

# Confidence Score: 8/10

**Strengths:**
- Comprehensive pattern coverage for MUMPS
- Clear implementation path with pseudocode
- Handles all special characters and syntax
- Includes thorough testing strategy
- Memory-conscious chunking approach

**Improvements Needed:**
- Could include more MUMPS-specific edge cases
- Performance optimization strategies for large repository
- More detailed error recovery mechanisms

This PRP provides sufficient context and detail for an AI agent to implement Phase 1 successfully in one pass.