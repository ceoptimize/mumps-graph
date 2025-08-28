#!/usr/bin/env python
"""Create Neo4j indexes for Phase 3 performance optimization."""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase
from rich.console import Console

console = Console()

# Load environment variables
load_dotenv()

def create_indexes():
    """Create indexes for Phase 3 MERGE operations."""
    
    # Connect to Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "vista123")
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    console.print("[bold cyan]Creating Neo4j Indexes for Phase 3 Performance[/bold cyan]\n")
    
    indexes = [
        # Routine indexes
        ("Routine", "name", "CREATE INDEX routine_name IF NOT EXISTS FOR (r:Routine) ON (r.name)"),
        ("Routine", "routine_id", "CREATE INDEX routine_id IF NOT EXISTS FOR (r:Routine) ON (r.routine_id)"),
        
        # Label indexes - composite index for the MERGE operation
        ("Label", "routine_name+name", "CREATE INDEX label_composite IF NOT EXISTS FOR (l:Label) ON (l.routine_name, l.name)"),
        ("Label", "routine_name", "CREATE INDEX label_routine IF NOT EXISTS FOR (l:Label) ON (l.routine_name)"),
        ("Label", "label_id", "CREATE INDEX label_id IF NOT EXISTS FOR (l:Label) ON (l.label_id)"),
        
        # Additional performance indexes
        ("Package", "prefixes", "CREATE INDEX package_prefixes IF NOT EXISTS FOR (p:Package) ON (p.prefixes)"),
    ]
    
    with driver.session() as session:
        for label, fields, query in indexes:
            try:
                console.print(f"Creating index on {label}({fields})...")
                session.run(query)
                console.print(f"[green]✅ Index on {label}({fields}) created[/green]")
            except Exception as e:
                if "already exists" in str(e).lower():
                    console.print(f"[yellow]⚠️  Index on {label}({fields}) already exists[/yellow]")
                else:
                    console.print(f"[red]❌ Failed to create index on {label}({fields}): {e}[/red]")
        
        # Create constraints for uniqueness (these also create indexes)
        constraints = [
            ("Routine", "routine_id", "CREATE CONSTRAINT routine_unique IF NOT EXISTS FOR (r:Routine) REQUIRE r.routine_id IS UNIQUE"),
            ("Label", "label_id", "CREATE CONSTRAINT label_unique IF NOT EXISTS FOR (l:Label) REQUIRE l.label_id IS UNIQUE"),
        ]
        
        console.print("\n[bold]Creating Constraints:[/bold]")
        for label, field, query in constraints:
            try:
                console.print(f"Creating constraint on {label}.{field}...")
                session.run(query)
                console.print(f"[green]✅ Constraint on {label}.{field} created[/green]")
            except Exception as e:
                if "already exists" in str(e).lower():
                    console.print(f"[yellow]⚠️  Constraint on {label}.{field} already exists[/yellow]")
                else:
                    console.print(f"[red]❌ Failed to create constraint: {e}[/red]")
        
        # Check index status
        console.print("\n[bold]Checking Index Status:[/bold]")
        result = session.run("SHOW INDEXES")
        index_count = 0
        for record in result:
            if record.get("entityType") in ["NODE", "Node"]:
                index_count += 1
                state = record.get("state", "UNKNOWN")
                name = record.get("name", "unnamed")
                console.print(f"  • {name}: [green]{state}[/green]")
        
        console.print(f"\n[bold green]✅ Total indexes available: {index_count}[/bold green]")
    
    driver.close()
    console.print("\n[bold green]Index creation complete! Phase 3 will now run much faster.[/bold green]")

if __name__ == "__main__":
    try:
        create_indexes()
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)