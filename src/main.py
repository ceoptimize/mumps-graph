"""Main entry point for VistA Graph Database Phase 1 execution."""

import argparse
import logging
import sys
import time

from dotenv import load_dotenv
from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.table import Table

from src.config.settings import get_settings
from src.graph.builder import GraphBuilder
from src.graph.connection import Neo4jConnection
from src.parsers.csv_parser import PackageCSVParser
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
        help="Phase to execute (default: 1)",
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

    return parser.parse_args()


def display_welcome():
    """Display welcome banner."""
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
        orphan_query = "MATCH (f:File) WHERE NOT (()-[:CONTAINS_FILE]->(f)) RETURN count(f) AS count"
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
    display_welcome()

    try:
        # Execute phase
        if args.phase == 1:
            phase1_pipeline(args)
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
