"""Main entry point for VistA Graph Database Phase 1 execution."""

import argparse
import logging
import sys
import time

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.config.settings import get_settings
from src.graph.builder import GraphBuilder
from src.graph.connection import Neo4jConnection
from src.parsers.csv_parser import PackageCSVParser
from src.parsers.routine_parser import RoutineParser
from src.parsers.zwr_parser import ZWRParser

# Setup rich console
console = Console()

# Load environment variables
load_dotenv()


def setup_logging(log_level: str = "INFO"):
    """
    Configure logging with rich handler.

    Args:
        log_level: Logging level
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(message)s",
        handlers=[
            RichHandler(
                rich_tracebacks=True,
                console=console,
                show_time=True,
                show_path=False,
            )
        ],
    )


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="VistA Graph Database Phase 1 - Foundation Implementation"
    )

    parser.add_argument(
        "--phase",
        type=int,
        default=1,
        choices=[1, 2, 3, 4],
        help="Phase to execute (1: Foundation, 2: Static Relationships, 3: Code Structure, 4: Code Relationships)",
    )

    parser.add_argument(
        "--source",
        type=str,
        default="Vista-M-source-code",
        help="Path to VistA-M source directory",
    )

    parser.add_argument(
        "--clear-db",
        action="store_true",
        help="Clear existing database before import",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for database operations (default: 1000)",
    )

    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level (default: INFO)",
    )

    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate existing graph, don't build",
    )

    parser.add_argument(
        "--all-packages",
        action="store_true",
        help="Process all packages (Phase 3 only, default: Registration only)",
    )

    return parser.parse_args()


def display_welcome(phase: int = 1):
    """Display welcome banner."""
    if phase == 1:
        welcome_text = """
[bold cyan]VistA Graph Database[/bold cyan]
[yellow]Phase 1: Foundation Implementation[/yellow]

Building graph database from:
• Data Dictionary (DD.zwr)
• Package definitions (Packages.csv)

This will create:
• Package nodes
• File nodes
• Field nodes
• Relationships between entities
        """
    elif phase == 2:
        welcome_text = """
[bold cyan]VistA Graph Database[/bold cyan]
[yellow]Phase 2: Static Relationships[/yellow]

Extracting deterministic relationships:
• Cross-reference definitions
• Subfile hierarchies
• Variable pointer targets

This will create:
• CrossReference nodes
• INDEXED_BY relationships
• SUBFILE_OF relationships
• VARIABLE_POINTER relationships
        """
    elif phase == 3:
        welcome_text = """
[bold cyan]VistA Graph Database[/bold cyan]
[yellow]Phase 3: Code Structure Implementation[/yellow]

Parsing MUMPS routine files to extract:
• Routine structure and metadata
• Labels (entry points/functions)
• Code organization

This will create:
• Routine nodes
• Label nodes
• CONTAINS_LABEL relationships
• OWNS_ROUTINE relationships
        """
    elif phase == 4:
        welcome_text = """
[bold cyan]VistA Graph Database[/bold cyan]
[yellow]Phase 4: Code Relationships[/yellow]

Extracting code interdependencies and global access patterns:
• Call patterns (DO, GOTO, JOB)
• Function invocations ($$)
• Global access patterns (READ, WRITE, KILL)
• Control flow relationships

This will create:
• Global nodes
• CALLS relationships
• INVOKES relationships
• ACCESSES relationships
• FALLS_THROUGH relationships
• STORED_IN relationships
        """
    else:
        welcome_text = (
            f"[bold cyan]VistA Graph Database[/bold cyan]\n[yellow]Phase {phase}[/yellow]"
        )

    console.print(Panel.fit(welcome_text, title="Welcome", border_style="cyan"))


def phase1_pipeline(args):
    """
    Execute Phase 1 pipeline.

    Args:
        args: Command line arguments
    """
    settings = get_settings()

    # Validate paths
    console.print("\n[cyan]Validating file paths...[/cyan]")
    if not settings.validate_paths():
        console.print("[red]❌ Path validation failed![/red]")
        sys.exit(1)
    console.print("[green]✅ All paths validated[/green]")

    # Initialize Neo4j connection
    console.print("\n[cyan]Connecting to Neo4j...[/cyan]")
    connection = Neo4jConnection()

    if not connection.connect():
        console.print("[red]❌ Failed to connect to Neo4j![/red]")
        console.print(
            "[yellow]Make sure Neo4j is running:[/yellow]\n"
            "  docker-compose -f docker/docker-compose.yml up -d"
        )
        sys.exit(1)
    console.print("[green]✅ Connected to Neo4j[/green]")

    # Clear database if requested
    if args.clear_db:
        console.print("\n[yellow]Clearing existing database...[/yellow]")
        if connection.clear_database():
            console.print("[green]✅ Database cleared[/green]")
        else:
            console.print("[red]❌ Failed to clear database![/red]")
            sys.exit(1)

    # If validate only, skip building
    if args.validate_only:
        validate_graph(connection)
        connection.disconnect()
        return

    # Parse Packages.csv
    console.print("\n[cyan]Parsing Packages.csv...[/cyan]")
    csv_parser = PackageCSVParser()
    packages_path = settings.get_absolute_path(settings.packages_csv_path)
    packages = csv_parser.parse_file(packages_path)

    csv_stats = csv_parser.get_statistics()
    console.print(
        f"[green]✅ Parsed {csv_stats['total_packages']} packages "
        f"with {csv_stats['total_prefixes']} prefixes[/green]"
    )

    # Parse DD.zwr
    console.print("\n[cyan]Parsing DD.zwr...[/cyan]")
    zwr_parser = ZWRParser()
    dd_path = settings.get_absolute_path(settings.dd_file_path)

    start_time = time.time()
    files, fields = zwr_parser.parse_file(dd_path)
    parse_time = time.time() - start_time

    zwr_stats = zwr_parser.get_statistics()
    console.print(
        f"[green]✅ Parsed {zwr_stats['total_files']} files and "
        f"{zwr_stats['total_fields']} fields in {parse_time:.2f}s[/green]"
    )

    # Parse FILE.zwr for global roots
    console.print("[cyan]Parsing FILE.zwr for global roots...[/cyan]")
    file_zwr_path = settings.vista_source_dir / "Packages/VA FileMan/Globals/1+FILE.zwr"
    if file_zwr_path.exists():
        zwr_parser.parse_dic_file(file_zwr_path, files)
        console.print("[green]✅ Updated global roots from FILE.zwr[/green]")
    else:
        console.print("[yellow]⚠️  FILE.zwr not found, global roots may be incomplete[/yellow]")

    # Build graph
    console.print("\n[cyan]Building graph database...[/cyan]")
    builder = GraphBuilder(connection, batch_size=args.batch_size)

    # Create indexes
    console.print("[cyan]Creating indexes...[/cyan]")
    if not builder.create_indexes():
        console.print("[red]❌ Failed to create indexes![/red]")
        sys.exit(1)

    # Create nodes
    builder.batch_create_packages(packages)
    builder.batch_create_files(list(files.values()))
    builder.batch_create_fields(fields)

    # Create relationships
    console.print("\n[cyan]Creating relationships...[/cyan]")
    builder.create_file_field_relationships(files, fields)
    builder.create_pointer_relationships(fields, files)
    builder.create_package_file_relationships(packages, files, csv_parser)

    # Get final statistics
    build_stats = builder.get_statistics()

    # Display results
    display_results(build_stats, parse_time)

    # Validate graph
    validate_graph(connection)

    # Disconnect
    connection.disconnect()
    console.print("\n[green]✅ Phase 1 completed successfully![/green]")


def phase2_pipeline(args):
    """
    Execute Phase 2 pipeline: Extract static relationships.

    Args:
        args: Command line arguments
    """
    settings = get_settings()

    # Initialize Neo4j connection
    console.print("\n[cyan]Connecting to Neo4j...[/cyan]")
    connection = Neo4jConnection()

    if not connection.connect():
        console.print("[red]❌ Failed to connect to Neo4j![/red]")
        console.print(
            "[yellow]Make sure Neo4j is running:[/yellow]\n"
            "  docker-compose -f docker/docker-compose.yml up -d"
        )
        sys.exit(1)
    console.print("[green]✅ Connected to Neo4j[/green]")

    # Check if Phase 1 has been completed
    console.print("\n[cyan]Checking Phase 1 completion...[/cyan]")
    db_info = connection.get_database_info()

    if not db_info or db_info.get("total_nodes", 0) == 0:
        console.print("[red]❌ Phase 1 must be completed first![/red]")
        console.print("Run: python -m src.main --phase 1")
        sys.exit(1)

    console.print(f"[green]✅ Found {db_info['total_nodes']} nodes from Phase 1[/green]")

    # Parse DD.zwr for extended information
    console.print("\n[cyan]Parsing DD.zwr for Phase 2 relationships...[/cyan]")
    zwr_parser = ZWRParser()
    dd_path = settings.get_absolute_path(settings.dd_file_path)

    # Read DD file
    with open(dd_path, "r", encoding="utf-8", errors="ignore") as f:
        dd_lines = f.readlines()

    console.print(f"[dim]Read {len(dd_lines)} lines from DD.zwr[/dim]")

    # Parse Phase 1 data first (needed for Phase 2 relationships)
    console.print("[cyan]Extracting file and field definitions...[/cyan]")
    files, fields = zwr_parser.extract_file_definitions(dd_lines)

    # Extract Phase 2 specific data
    console.print("[cyan]Extracting cross-references...[/cyan]")
    xrefs = zwr_parser.extract_cross_references(dd_lines)
    console.print(f"[green]✅ Found {len(xrefs)} cross-reference definitions[/green]")

    console.print("[cyan]Identifying subfiles...[/cyan]")
    subfiles = zwr_parser.extract_subfiles(files)
    console.print(f"[green]✅ Found {len(subfiles)} subfiles[/green]")

    console.print("[cyan]Extracting variable pointer targets...[/cyan]")
    v_pointers = zwr_parser.extract_variable_pointers(dd_lines)
    console.print(f"[green]✅ Found {len(v_pointers)} variable pointer fields[/green]")

    # Build Phase 2 graph extensions
    console.print("\n[cyan]Building Phase 2 graph extensions...[/cyan]")
    builder = GraphBuilder(connection, batch_size=args.batch_size)

    # Create new node types
    if xrefs:
        console.print("[cyan]Creating CrossReference nodes...[/cyan]")
        xref_count = builder.create_cross_reference_nodes(xrefs)
        console.print(f"[green]✅ Created {xref_count} CrossReference nodes[/green]")

    # Create Phase 2 relationships
    if xrefs and fields:
        console.print("[cyan]Creating INDEXED_BY relationships...[/cyan]")
        indexed_count = builder.create_indexed_by_relationships(xrefs, fields)
        console.print(f"[green]✅ Created {indexed_count} INDEXED_BY relationships[/green]")

    if subfiles:
        console.print("[cyan]Creating SUBFILE_OF relationships...[/cyan]")
        subfile_count = builder.create_subfile_relationships(subfiles, files)
        console.print(f"[green]✅ Created {subfile_count} SUBFILE_OF relationships[/green]")

    if v_pointers:
        console.print("[cyan]Creating VARIABLE_POINTER relationships...[/cyan]")
        vpointer_count = builder.create_variable_pointer_relationships(v_pointers, fields, files)
        console.print(f"[green]✅ Created {vpointer_count} VARIABLE_POINTER relationships[/green]")

    # Validate Phase 2
    console.print("\n[cyan]Validating Phase 2 results...[/cyan]")
    validate_phase2(connection)

    # Display summary
    display_phase2_results(
        xref_count if xrefs else 0,
        indexed_count if xrefs and fields else 0,
        subfile_count if subfiles else 0,
        vpointer_count if v_pointers else 0,
    )

    # Disconnect
    connection.disconnect()
    console.print("\n[green]✅ Phase 2 completed successfully![/green]")


def validate_phase2(connection: Neo4jConnection):
    """
    Validate Phase 2 specific relationships.

    Args:
        connection: Neo4j connection
    """
    from src.graph.queries import GraphQueries

    queries = GraphQueries()

    # Run Phase 2 validation query
    validation_query = queries.validate_phase2_relationships()
    results = connection.execute_query(validation_query)

    if results:
        # Create validation table
        table = Table(title="Phase 2 Validation", show_header=True)
        table.add_column("Relationship Type", style="cyan")
        table.add_column("Expected Min", justify="right")
        table.add_column("Actual Count", justify="right")
        table.add_column("Status", justify="center")

        has_failures = False
        for result in results:
            status_color = "green" if result["status"] == "PASS" else "red"
            table.add_row(
                result["relationship_type"],
                str(result["expected_minimum"]),
                str(result["actual_count"]),
                f"[{status_color}]{result['status']}[/{status_color}]",
            )
            if result["status"] == "FAIL":
                has_failures = True

        console.print(table)

        if has_failures:
            console.print("\n[yellow]⚠️  Some validation checks failed[/yellow]")
            console.print("[dim]This may be normal depending on your DD.zwr content[/dim]")
    else:
        console.print("[yellow]⚠️  Could not run validation query[/yellow]")


def display_phase2_results(xrefs: int, indexed: int, subfiles: int, vpointers: int):
    """
    Display Phase 2 execution results.

    Args:
        xrefs: Number of cross-reference nodes created
        indexed: Number of INDEXED_BY relationships created
        subfiles: Number of SUBFILE_OF relationships created
        vpointers: Number of VARIABLE_POINTER relationships created
    """
    table = Table(title="Phase 2 Results", show_header=True)
    table.add_column("Entity Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("CrossReference nodes", str(xrefs))
    table.add_row("INDEXED_BY relationships", str(indexed))
    table.add_row("SUBFILE_OF relationships", str(subfiles))
    table.add_row("VARIABLE_POINTER relationships", str(vpointers))
    table.add_row("", "")
    table.add_row(
        "[bold]Total new entities[/bold]",
        f"[bold]{xrefs + indexed + subfiles + vpointers}[/bold]",
    )

    console.print("\n")
    console.print(table)


def phase3_pipeline(args):
    """
    Execute Phase 3 pipeline: Parse MUMPS routines and create code structure graph.

    Args:
        args: Command line arguments
    """
    settings = get_settings()

    # Initialize Neo4j connection
    console.print("\n[cyan]Connecting to Neo4j...[/cyan]")
    connection = Neo4jConnection()

    if not connection.connect():
        console.print("[red]❌ Failed to connect to Neo4j![/red]")
        console.print(
            "[yellow]Make sure Neo4j is running:[/yellow]\n"
            "  docker-compose -f docker/docker-compose.yml up -d"
        )
        sys.exit(1)
    console.print("[green]✅ Connected to Neo4j[/green]")

    # Check if Phase 1 has been completed
    console.print("\n[cyan]Checking Phase 1 & 2 completion...[/cyan]")
    db_info = connection.get_database_info()

    if not db_info or db_info.get("total_nodes", 0) == 0:
        console.print("[red]❌ Phase 1 must be completed first![/red]")
        console.print("Run: python -m src.main --phase 1")
        sys.exit(1)

    console.print(f"[green]✅ Found {db_info['total_nodes']} nodes from previous phases[/green]")

    # Initialize parser
    console.print("\n[cyan]Initializing MUMPS routine parser...[/cyan]")
    routine_parser = RoutineParser()

    # Find and parse routine files
    from pathlib import Path

    vista_source_dir = settings.get_absolute_path(Path("Vista-M-source-code"))
    packages_dir = vista_source_dir / "Packages"

    if not packages_dir.exists():
        console.print(f"[red]❌ Packages directory not found: {packages_dir}[/red]")
        sys.exit(1)

    # Collect all routines and labels
    all_routines = []
    all_labels = []

    # Process each package directory
    console.print("[cyan]Processing routine files by package...[/cyan]")
    package_dirs = [d for d in packages_dir.iterdir() if d.is_dir()]

    # Process Registration package first as a test
    registration_dir = packages_dir / "Registration" / "Routines"
    if registration_dir.exists():
        console.print("[cyan]Processing Registration package routines...[/cyan]")
        routines, labels = routine_parser.parse_directory(registration_dir, "Registration")
        console.print(f"[green]✅ Found {len(routines)} routines with {len(labels)} labels[/green]")
        all_routines.extend(routines)
        all_labels.extend(labels)

    # Process all other packages (optional - can be limited for testing)
    if args.all_packages:
        for package_dir in package_dirs:
            if package_dir.name == "Registration":
                continue  # Already processed

            routines_dir = package_dir / "Routines"
            if routines_dir.exists():
                console.print(f"[cyan]Processing {package_dir.name} package...[/cyan]")
                routines, labels = routine_parser.parse_directory(routines_dir, package_dir.name)
                if routines:
                    console.print(
                        f"[dim]  Found {len(routines)} routines with {len(labels)} labels[/dim]"
                    )
                    all_routines.extend(routines)
                    all_labels.extend(labels)

    console.print(
        f"\n[green]✅ Total: {len(all_routines)} routines with {len(all_labels)} labels[/green]"
    )

    # Build Phase 3 graph extensions
    console.print("\n[cyan]Building Phase 3 graph extensions...[/cyan]")
    builder = GraphBuilder(connection, batch_size=args.batch_size)

    # Create routine nodes
    if all_routines:
        console.print("[cyan]Creating Routine nodes...[/cyan]")
        routine_count = builder.create_routine_nodes(all_routines)
        console.print(f"[green]✅ Created {routine_count} Routine nodes[/green]")

    # Create label nodes
    if all_labels:
        console.print("[cyan]Creating Label nodes...[/cyan]")
        label_count = builder.create_label_nodes(all_labels)
        console.print(f"[green]✅ Created {label_count} Label nodes[/green]")

    # Create relationships
    if all_routines and all_labels:
        console.print("[cyan]Creating CONTAINS_LABEL relationships...[/cyan]")
        contains_count = builder.create_contains_label_relationships(all_routines, all_labels)
        console.print(f"[green]✅ Created {contains_count} CONTAINS_LABEL relationships[/green]")

    if all_routines:
        console.print("[cyan]Creating OWNS_ROUTINE relationships...[/cyan]")
        owns_count = builder.create_package_routine_relationships(all_routines)
        console.print(f"[green]✅ Created {owns_count} OWNS_ROUTINE relationships[/green]")

    # Validate Phase 3
    console.print("\n[cyan]Validating Phase 3 results...[/cyan]")
    validate_phase3(connection)

    # Display summary
    display_phase3_results(
        len(all_routines),
        len(all_labels),
        contains_count if all_routines and all_labels else 0,
        owns_count if all_routines else 0,
    )


def validate_phase3(connection: Neo4jConnection):
    """
    Validate Phase 3 specific relationships and nodes.

    Args:
        connection: Neo4j connection
    """
    validation_queries = [
        # Check for routines
        {
            "description": "Routine nodes",
            "query": "MATCH (r:Routine) RETURN count(r) as count",
            "expected_minimum": 1,
        },
        # Check for labels
        {
            "description": "Label nodes",
            "query": "MATCH (l:Label) RETURN count(l) as count",
            "expected_minimum": 1,
        },
        # Check CONTAINS_LABEL relationships
        {
            "description": "CONTAINS_LABEL",
            "query": "MATCH ()-[:CONTAINS_LABEL]->() RETURN count(*) as count",
            "expected_minimum": 1,
        },
        # Check OWNS_ROUTINE relationships
        {
            "description": "OWNS_ROUTINE",
            "query": "MATCH ()-[:OWNS_ROUTINE]->() RETURN count(*) as count",
            "expected_minimum": 0,  # May not have package matches
        },
        # Check for orphaned routines
        {
            "description": "Orphaned routines (no package)",
            "query": "MATCH (r:Routine) WHERE NOT ((:Package)-[:OWNS_ROUTINE]->(r)) RETURN count(r) as count",
            "expected_minimum": -1,  # Just informational
        },
        # Check for entry points
        {
            "description": "Entry point labels",
            "query": "MATCH (l:Label {is_entry_point: true}) RETURN count(l) as count",
            "expected_minimum": 0,
        },
        # Check for functions
        {
            "description": "Function labels",
            "query": "MATCH (l:Label {is_function: true}) RETURN count(l) as count",
            "expected_minimum": 0,
        },
    ]

    results = []
    for check in validation_queries:
        try:
            result = connection.execute_query(check["query"])
            if result:
                count = result[0]["count"]
                status = (
                    "INFO"
                    if check["expected_minimum"] < 0
                    else ("PASS" if count >= check["expected_minimum"] else "WARN")
                )
                results.append(
                    {
                        "entity_type": check["description"],
                        "expected_minimum": check["expected_minimum"]
                        if check["expected_minimum"] >= 0
                        else "N/A",
                        "actual_count": count,
                        "status": status,
                    }
                )
        except Exception as e:
            logging.error(f"Validation query failed: {e}")

    if results:
        # Create validation table
        table = Table(title="Phase 3 Validation", show_header=True)
        table.add_column("Entity Type", style="cyan")
        table.add_column("Expected Min", justify="right")
        table.add_column("Actual Count", justify="right")
        table.add_column("Status", justify="center")

        for result in results:
            status_color = (
                "green"
                if result["status"] == "PASS"
                else ("yellow" if result["status"] == "WARN" else "dim")
            )
            table.add_row(
                result["entity_type"],
                str(result["expected_minimum"]),
                str(result["actual_count"]),
                f"[{status_color}]{result['status']}[/{status_color}]",
            )

        console.print(table)


def display_phase3_results(routines: int, labels: int, contains: int, owns: int):
    """
    Display Phase 3 execution results.

    Args:
        routines: Number of routine nodes created
        labels: Number of label nodes created
        contains: Number of CONTAINS_LABEL relationships created
        owns: Number of OWNS_ROUTINE relationships created
    """
    table = Table(title="Phase 3 Results", show_header=True)
    table.add_column("Entity Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Routine nodes", str(routines))
    table.add_row("Label nodes", str(labels))
    table.add_row("CONTAINS_LABEL relationships", str(contains))
    table.add_row("OWNS_ROUTINE relationships", str(owns))
    table.add_row("", "")
    table.add_row(
        "[bold]Total new entities[/bold]", f"[bold]{routines + labels + contains + owns}[/bold]"
    )

    console.print("\n")
    console.print(table)


def phase4_pipeline(args):
    """
    Execute Phase 4 pipeline: Extract code relationships with proper node resolution.

    Args:
        args: Command line arguments
    """
    settings = get_settings()
    from pathlib import Path

    from src.graph.node_cache import NodeLookupCache
    from src.parsers.code_extractor import CodeRelationshipExtractor

    # Initialize Neo4j connection
    console.print("\n[cyan]Connecting to Neo4j...[/cyan]")
    connection = Neo4jConnection()

    if not connection.connect():
        console.print("[red]❌ Failed to connect to Neo4j![/red]")
        console.print(
            "[yellow]Make sure Neo4j is running:[/yellow]\n"
            "  docker-compose -f docker/docker-compose.yml up -d"
        )
        sys.exit(1)
    console.print("[green]✅ Connected to Neo4j[/green]")

    # Check if Phase 3 has been completed
    console.print("\n[cyan]Checking Phase 3 completion...[/cyan]")
    db_info = connection.get_database_info()

    if not db_info or db_info.get("total_nodes", 0) == 0:
        console.print("[red]❌ Phase 1-3 must be completed first![/red]")
        console.print("Run: python -m src.main --phase 1")
        console.print("     python -m src.main --phase 2")
        console.print("     python -m src.main --phase 3")
        sys.exit(1)

    # Check for Label nodes specifically
    label_check = connection.execute_query("MATCH (l:Label) RETURN count(l) as count")
    if not label_check or label_check[0]["count"] == 0:
        console.print("[red]❌ No Label nodes found. Phase 3 must be completed first![/red]")
        sys.exit(1)

    console.print(f"[green]✅ Found {db_info['total_nodes']} nodes from previous phases[/green]")

    # Initialize node lookup cache
    console.print("\n[cyan]Loading existing nodes from Phases 1-3...[/cyan]")
    node_cache = NodeLookupCache(connection)
    if not node_cache.load_from_neo4j():
        console.print("[red]❌ Failed to load node cache![/red]")
        sys.exit(1)

    cache_stats = node_cache.get_statistics()
    console.print(
        f"[green]✅ Loaded: {cache_stats['labels']} labels, "
        f"{cache_stats['routines']} routines, "
        f"{cache_stats['files']} files[/green]"
    )

    # Create Global nodes
    console.print("\n[cyan]Creating Global nodes...[/cyan]")
    globals_to_create = {}  # {global_name: file_number or None}

    # From File.global_root
    for file_num, (_file_id, global_root) in node_cache.files.items():
        if global_root:
            global_name = global_root.replace("^", "").split("(")[0]
            globals_to_create[global_name] = file_num

    # Build graph and create Global nodes
    builder = GraphBuilder(connection, batch_size=args.batch_size)
    global_count = builder.create_global_nodes(globals_to_create)
    console.print(f"[green]✅ Created {global_count} Global nodes[/green]")

    # Reload cache with new Global nodes
    node_cache.load_globals()

    # Create STORED_IN relationships
    stored_count = builder.create_stored_in_relationships(node_cache)
    console.print(f"[green]✅ Created {stored_count} STORED_IN relationships[/green]")

    # Initialize code extractor
    extractor = CodeRelationshipExtractor(node_cache)

    # Find and process routine files
    vista_source_dir = settings.get_absolute_path(Path("Vista-M-source-code"))
    packages_dir = vista_source_dir / "Packages"

    if not packages_dir.exists():
        console.print(f"[red]❌ Packages directory not found: {packages_dir}[/red]")
        sys.exit(1)

    # Extract relationships from routines
    all_calls = []
    all_unresolved_calls = []
    all_invokes = []
    all_unresolved_invokes = []
    all_accesses = []
    all_orphan_accesses = []
    all_falls_through = []

    console.print("\n[cyan]Extracting code relationships...[/cyan]")

    # Process Registration package as primary target
    registration_dir = packages_dir / "Registration" / "Routines"
    if registration_dir.exists():
        console.print("[cyan]Processing Registration package routines...[/cyan]")
        routine_files = list(registration_dir.glob("*.m"))

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task(
                f"[cyan]Processing {len(routine_files)} routines...", total=len(routine_files)
            )

            for routine_file in routine_files:
                # Extract CALLS
                calls, unresolved, orphans = extractor.extract_calls_from_routine(routine_file)
                all_calls.extend(calls)
                all_unresolved_calls.extend(unresolved)

                # Extract INVOKES
                invokes, unresolved_inv, orphan_inv = extractor.extract_invokes_from_routine(
                    routine_file
                )
                all_invokes.extend(invokes)
                all_unresolved_invokes.extend(unresolved_inv)

                # Extract ACCESSES
                accesses, orphan_acc = extractor.extract_accesses_from_routine(routine_file)
                all_accesses.extend(accesses)
                all_orphan_accesses.extend(orphan_acc)

                # Extract FALLS_THROUGH
                falls = extractor.extract_falls_through_relationships(routine_file)
                all_falls_through.extend(falls)

                progress.advance(task)

    # Process additional packages if requested
    if args.all_packages:
        console.print("[cyan]Processing all other packages...[/cyan]")
        for package_dir in packages_dir.iterdir():
            if package_dir.name == "Registration" or not package_dir.is_dir():
                continue

            routines_dir = package_dir / "Routines"
            if routines_dir.exists():
                routine_files = list(routines_dir.glob("*.m"))
                if routine_files:
                    console.print(
                        f"[dim]  Processing {package_dir.name}: {len(routine_files)} routines[/dim]"
                    )

                    for routine_file in routine_files:
                        calls, unresolved, orphans = extractor.extract_calls_from_routine(
                            routine_file
                        )
                        all_calls.extend(calls)
                        all_unresolved_calls.extend(unresolved)

                        invokes, unresolved_inv, orphan_inv = (
                            extractor.extract_invokes_from_routine(routine_file)
                        )
                        all_invokes.extend(invokes)
                        all_unresolved_invokes.extend(unresolved_inv)

                        accesses, orphan_acc = extractor.extract_accesses_from_routine(routine_file)
                        all_accesses.extend(accesses)
                        all_orphan_accesses.extend(orphan_acc)

                        falls = extractor.extract_falls_through_relationships(routine_file)
                        all_falls_through.extend(falls)

    # Create relationships in Neo4j
    console.print("\n[cyan]Creating relationships in graph database...[/cyan]")

    # Create CALLS relationships
    if all_calls:
        console.print(f"[cyan]Creating {len(all_calls)} CALLS relationships...[/cyan]")
        calls_count = builder.create_calls_relationships(all_calls)
        console.print(f"[green]✅ Created {calls_count} CALLS relationships[/green]")

    # Create INVOKES relationships
    if all_invokes:
        console.print(f"[cyan]Creating {len(all_invokes)} INVOKES relationships...[/cyan]")
        invokes_count = builder.create_invokes_relationships(all_invokes)
        console.print(f"[green]✅ Created {invokes_count} INVOKES relationships[/green]")

    # Create ACCESSES relationships
    if all_accesses:
        console.print(f"[cyan]Creating {len(all_accesses)} ACCESSES relationships...[/cyan]")
        accesses_count = builder.create_accesses_relationships(all_accesses)
        console.print(f"[green]✅ Created {accesses_count} ACCESSES relationships[/green]")

    # Create FALLS_THROUGH relationships
    if all_falls_through:
        console.print(
            f"[cyan]Creating {len(all_falls_through)} FALLS_THROUGH relationships...[/cyan]"
        )
        falls_count = builder.create_falls_through_relationships(all_falls_through)
        console.print(f"[green]✅ Created {falls_count} FALLS_THROUGH relationships[/green]")

    # Handle orphan accesses by creating new globals
    if all_orphan_accesses:
        console.print(
            f"\n[cyan]Creating globals for {len(all_orphan_accesses)} orphan accesses...[/cyan]"
        )
        orphan_globals = {}
        for acc in all_orphan_accesses:
            if (
                acc["global_name"] not in orphan_globals
                and acc["global_name"] not in node_cache.globals
            ):
                orphan_globals[acc["global_name"]] = None

        if orphan_globals:
            orphan_global_count = builder.create_global_nodes(orphan_globals)
            console.print(
                f"[green]✅ Created {orphan_global_count} additional Global nodes[/green]"
            )

            # Reload globals and create orphan accesses
            node_cache.load_globals()

            resolved_orphans = []
            for acc in all_orphan_accesses:
                global_id = node_cache.resolve_global(acc["global_name"])
                if global_id:
                    acc["global_id"] = global_id
                    resolved_orphans.append(acc)

            if resolved_orphans:
                orphan_access_count = builder.create_accesses_relationships(resolved_orphans)
                console.print(
                    f"[green]✅ Created {orphan_access_count} additional ACCESSES relationships[/green]"
                )

    # Report unresolved references
    if all_unresolved_calls:
        console.print(f"\n[yellow]⚠️  {len(all_unresolved_calls)} unresolved CALLS[/yellow]")
        for call in all_unresolved_calls[:5]:  # Show first 5
            console.print(
                f"    {call['source_routine']}:{call['source_label']} -> "
                f"{call['target_routine']}:{call['target_label']}"
            )
        if len(all_unresolved_calls) > 5:
            console.print(f"    ... and {len(all_unresolved_calls) - 5} more")

    if all_unresolved_invokes:
        console.print(f"\n[yellow]⚠️  {len(all_unresolved_invokes)} unresolved INVOKES[/yellow]")
        for inv in all_unresolved_invokes[:5]:  # Show first 5
            console.print(
                f"    {inv['source_routine']}:{inv['source_label']} -> "
                f"$${inv['target_label']}^{inv['target_routine']}"
            )
        if len(all_unresolved_invokes) > 5:
            console.print(f"    ... and {len(all_unresolved_invokes) - 5} more")

    # Validate Phase 4
    console.print("\n[cyan]Validating Phase 4 results...[/cyan]")
    validate_phase4(connection)

    # Display summary
    display_phase4_results(
        global_count + (orphan_global_count if all_orphan_accesses else 0),
        calls_count if all_calls else 0,
        invokes_count if all_invokes else 0,
        accesses_count + (orphan_access_count if all_orphan_accesses else 0) if all_accesses else 0,
        falls_count if all_falls_through else 0,
        stored_count,
        len(all_unresolved_calls),
        len(all_unresolved_invokes),
    )

    # Disconnect
    connection.disconnect()
    console.print("\n[green]✅ Phase 4 completed successfully![/green]")


def validate_phase4(connection: Neo4jConnection):
    """
    Validate Phase 4 specific relationships and nodes.

    Args:
        connection: Neo4j connection
    """
    validation_queries = [
        {
            "description": "Global nodes",
            "query": "MATCH (g:Global) RETURN count(g) as count",
            "expected_minimum": 1,
        },
        {
            "description": "CALLS relationships",
            "query": "MATCH ()-[:CALLS]->() RETURN count(*) as count",
            "expected_minimum": 0,
        },
        {
            "description": "INVOKES relationships",
            "query": "MATCH ()-[:INVOKES]->() RETURN count(*) as count",
            "expected_minimum": 0,
        },
        {
            "description": "ACCESSES relationships",
            "query": "MATCH ()-[:ACCESSES]->() RETURN count(*) as count",
            "expected_minimum": 0,
        },
        {
            "description": "FALLS_THROUGH relationships",
            "query": "MATCH ()-[:FALLS_THROUGH]->() RETURN count(*) as count",
            "expected_minimum": 0,
        },
        {
            "description": "STORED_IN relationships",
            "query": "MATCH ()-[:STORED_IN]->() RETURN count(*) as count",
            "expected_minimum": 0,
        },
        {
            "description": "Orphan globals (no file)",
            "query": "MATCH (g:Global) WHERE g.file_number IS NULL RETURN count(g) as count",
            "expected_minimum": -1,  # Just informational
        },
    ]

    results = []
    for check in validation_queries:
        try:
            result = connection.execute_query(check["query"])
            if result:
                count = result[0]["count"]
                status = (
                    "INFO"
                    if check["expected_minimum"] < 0
                    else ("PASS" if count >= check["expected_minimum"] else "WARN")
                )
                results.append(
                    {
                        "entity_type": check["description"],
                        "expected_minimum": check["expected_minimum"]
                        if check["expected_minimum"] >= 0
                        else "N/A",
                        "actual_count": count,
                        "status": status,
                    }
                )
        except Exception as e:
            logging.error(f"Validation query failed: {e}")

    if results:
        # Create validation table
        table = Table(title="Phase 4 Validation", show_header=True)
        table.add_column("Entity Type", style="cyan")
        table.add_column("Expected Min", justify="right")
        table.add_column("Actual Count", justify="right")
        table.add_column("Status", justify="center")

        for result in results:
            status_color = (
                "green"
                if result["status"] == "PASS"
                else ("yellow" if result["status"] == "WARN" else "dim")
            )
            table.add_row(
                result["entity_type"],
                str(result["expected_minimum"]),
                str(result["actual_count"]),
                f"[{status_color}]{result['status']}[/{status_color}]",
            )

        console.print(table)


def display_phase4_results(
    globals: int,
    calls: int,
    invokes: int,
    accesses: int,
    falls: int,
    stored: int,
    unresolved_calls: int,
    unresolved_invokes: int,
):
    """
    Display Phase 4 execution results.

    Args:
        globals: Number of Global nodes created
        calls: Number of CALLS relationships created
        invokes: Number of INVOKES relationships created
        accesses: Number of ACCESSES relationships created
        falls: Number of FALLS_THROUGH relationships created
        stored: Number of STORED_IN relationships created
        unresolved_calls: Number of unresolved call references
        unresolved_invokes: Number of unresolved function references
    """
    table = Table(title="Phase 4 Results", show_header=True)
    table.add_column("Entity Type", style="cyan")
    table.add_column("Count", justify="right", style="green")

    table.add_row("Global nodes", str(globals))
    table.add_row("CALLS relationships", str(calls))
    table.add_row("INVOKES relationships", str(invokes))
    table.add_row("ACCESSES relationships", str(accesses))
    table.add_row("FALLS_THROUGH relationships", str(falls))
    table.add_row("STORED_IN relationships", str(stored))

    if unresolved_calls > 0 or unresolved_invokes > 0:
        table.add_row("", "")
        if unresolved_calls > 0:
            table.add_row(
                "[yellow]Unresolved calls[/yellow]", f"[yellow]{unresolved_calls}[/yellow]"
            )
        if unresolved_invokes > 0:
            table.add_row(
                "[yellow]Unresolved invokes[/yellow]", f"[yellow]{unresolved_invokes}[/yellow]"
            )

    table.add_row("", "")
    table.add_row(
        "[bold]Total new entities[/bold]",
        f"[bold]{globals + calls + invokes + accesses + falls + stored}[/bold]",
    )

    console.print("\n")
    console.print(table)


def validate_graph(connection: Neo4jConnection):
    """
    Validate the created graph.

    Args:
        connection: Neo4j connection
    """
    console.print("\n[cyan]Validating graph...[/cyan]")

    # Get database info
    db_info = connection.get_database_info()

    if db_info:
        # Create validation table
        table = Table(title="Graph Validation Results", show_header=True)
        table.add_column("Entity", style="cyan")
        table.add_column("Count", justify="right", style="green")

        # Add node counts
        for label, count in db_info.get("nodes", {}).items():
            table.add_row(f"{label} nodes", str(count))

        # Add relationship counts
        for rel_type, count in db_info.get("relationships", {}).items():
            table.add_row(f"{rel_type} relationships", str(count))

        # Add totals
        table.add_row("", "")
        table.add_row(
            "[bold]Total nodes[/bold]",
            f"[bold]{db_info.get('total_nodes', 0)}[/bold]",
        )
        table.add_row(
            "[bold]Total relationships[/bold]",
            f"[bold]{db_info.get('total_relationships', 0)}[/bold]",
        )

        console.print(table)

        # Check for issues
        issues = []

        # Check for orphan files
        orphan_query = (
            "MATCH (f:File) WHERE NOT (()-[:CONTAINS_FILE]->(f)) RETURN count(f) AS count"
        )
        orphan_result = connection.execute_query(orphan_query)
        if orphan_result and orphan_result[0]["count"] > 0:
            issues.append(f"Found {orphan_result[0]['count']} orphan files")

        # Check for dangling pointers
        dangling_query = (
            "MATCH (f:Field) WHERE f.is_pointer = true AND "
            "NOT (f)-[:POINTS_TO]->() RETURN count(f) AS count"
        )
        dangling_result = connection.execute_query(dangling_query)
        if dangling_result and dangling_result[0]["count"] > 0:
            issues.append(f"Found {dangling_result[0]['count']} dangling pointers")

        if issues:
            console.print("\n[yellow]⚠️  Validation issues found:[/yellow]")
            for issue in issues:
                console.print(f"  • {issue}")
        else:
            console.print("\n[green]✅ No validation issues found[/green]")
    else:
        console.print("[red]❌ Failed to get database info![/red]")


def display_results(stats: dict, parse_time: float):
    """
    Display execution results.

    Args:
        stats: Build statistics
        parse_time: Time taken to parse DD.zwr
    """
    # Create results table
    table = Table(title="Phase 1 Results", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Packages created", str(stats["packages_created"]))
    table.add_row("Files created", str(stats["files_created"]))
    table.add_row("Fields created", str(stats["fields_created"]))
    table.add_row("Relationships created", str(stats["relationships_created"]))
    table.add_row("Parse time", f"{parse_time:.2f}s")

    console.print("\n")
    console.print(table)


def main():
    """Main entry point."""
    args = parse_arguments()

    # Setup logging
    setup_logging(args.log_level)

    # Display welcome
    display_welcome(args.phase)

    try:
        # Execute phase
        if args.phase == 1:
            phase1_pipeline(args)
        elif args.phase == 2:
            phase2_pipeline(args)
        elif args.phase == 3:
            phase3_pipeline(args)
        elif args.phase == 4:
            phase4_pipeline(args)
        else:
            console.print(f"[red]Phase {args.phase} not implemented yet![/red]")
            sys.exit(1)

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        logging.exception("Unhandled exception")
        sys.exit(1)


if __name__ == "__main__":
    main()
