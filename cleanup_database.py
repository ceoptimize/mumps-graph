#!/usr/bin/env python
"""Clean out the entire Neo4j database - removes ALL nodes and relationships."""

import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase
from rich.console import Console

console = Console()
load_dotenv()

def cleanup_database():
    """Remove all nodes and relationships from the database."""
    
    # Connect to Neo4j
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
    username = os.getenv("NEO4J_USERNAME", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "vista123")
    
    driver = GraphDatabase.driver(uri, auth=(username, password))
    
    console.print("[bold red]⚠️  DATABASE CLEANUP WARNING ⚠️[/bold red]\n")
    console.print("This will DELETE ALL nodes and relationships from the database!")
    
    # Get current counts
    try:
        with driver.session() as session:
            result = session.run("MATCH (n) RETURN count(n) as nodes")
            node_count = result.single()["nodes"]
            result = session.run("MATCH ()-[r]->() RETURN count(r) as rels")
            rel_count = result.single()["rels"]
            
            if node_count == 0 and rel_count == 0:
                console.print("[green]Database is already empty.[/green]")
                driver.close()
                return
            
            console.print(f"Current database contains:")
            console.print(f"  • {node_count:,} nodes")
            console.print(f"  • {rel_count:,} relationships\n")
            
            # Confirm deletion
            response = input("Are you sure you want to delete everything? (yes/no): ")
            if response.lower() != "yes":
                console.print("[yellow]Cleanup cancelled.[/yellow]")
                driver.close()
                return
            
            console.print("\n[cyan]Cleaning database in batches...[/cyan]")
            
            # Delete relationships in batches
            console.print("Deleting relationships...")
            rel_deleted = 0
            while True:
                result = session.run(
                    "MATCH ()-[r]->() WITH r LIMIT 10000 DELETE r RETURN count(r) as deleted"
                )
                batch_deleted = result.single()["deleted"]
                if batch_deleted == 0:
                    break
                rel_deleted += batch_deleted
                console.print(f"  Deleted {rel_deleted:,} relationships...", end="\r")
            
            if rel_deleted > 0:
                console.print(f"  ✅ Deleted {rel_deleted:,} relationships total")
            
            # Delete nodes in batches
            console.print("\nDeleting nodes...")
            nodes_deleted = 0
            while True:
                result = session.run(
                    "MATCH (n) WITH n LIMIT 10000 DELETE n RETURN count(n) as deleted"
                )
                batch_deleted = result.single()["deleted"]
                if batch_deleted == 0:
                    break
                nodes_deleted += batch_deleted
                console.print(f"  Deleted {nodes_deleted:,} nodes...", end="\r")
            
            if nodes_deleted > 0:
                console.print(f"  ✅ Deleted {nodes_deleted:,} nodes total")
            
            # Final verification
            result = session.run("MATCH (n) RETURN count(n) as remaining")
            remaining = result.single()["remaining"]
            
            if remaining == 0:
                console.print("\n[bold green]✅ Database successfully cleaned![/bold green]")
            else:
                console.print(f"\n[yellow]⚠️  Warning: {remaining} nodes still remain[/yellow]")
                
    except Exception as e:
        console.print(f"[red]Error during cleanup: {e}[/red]")
        sys.exit(1)
    finally:
        driver.close()

if __name__ == "__main__":
    cleanup_database()