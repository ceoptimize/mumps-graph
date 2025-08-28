#!/usr/bin/env python
"""Validate Phase 3 graph implementation by checking samples and duplicates."""

import os
from dotenv import load_dotenv
from neo4j import GraphDatabase
from rich.console import Console
from rich.table import Table
from rich import print as rprint

console = Console()
load_dotenv()

def get_driver():
    """Create Neo4j driver connection."""
    return GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7688"),
        auth=(os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", "vista123"))
    )

def validate_routine_nodes(session):
    """Validate 10 sample Routine nodes."""
    console.print("\n[bold cyan]═══ Validating Routine Nodes ═══[/bold cyan]")
    
    # Get sample routine nodes
    query = """
    MATCH (r:Routine)
    RETURN r.routine_id, r.name, r.package_name, r.prefix, r.path, r.lines_of_code
    ORDER BY r.name
    LIMIT 10
    """
    
    result = session.run(query)
    routines = list(result)
    
    table = Table(title="Sample Routine Nodes", show_header=True)
    table.add_column("Name", style="cyan")
    table.add_column("Package", style="yellow")
    table.add_column("Prefix", style="green")
    table.add_column("LOC", justify="right")
    table.add_column("Path", style="dim", max_width=50)
    
    for r in routines:
        table.add_row(
            r["r.name"],
            r["r.package_name"] or "N/A",
            r["r.prefix"] or "N/A",
            str(r["r.lines_of_code"]),
            r["r.path"][-50:] if len(r["r.path"]) > 50 else r["r.path"]
        )
    
    console.print(table)
    
    # Validate structure
    validations = []
    for r in routines:
        # Check that routine_id exists and is unique
        if r["r.routine_id"]:
            validations.append(f"✅ {r['r.name']}: Has unique routine_id")
        else:
            validations.append(f"❌ {r['r.name']}: Missing routine_id")
        
        # Check that path points to actual .m file
        if r["r.path"] and r["r.path"].endswith(".m"):
            validations.append(f"✅ {r['r.name']}: Valid .m file path")
        else:
            validations.append(f"❌ {r['r.name']}: Invalid path")
    
    return validations

def validate_label_nodes(session):
    """Validate 10 sample Label nodes."""
    console.print("\n[bold cyan]═══ Validating Label Nodes ═══[/bold cyan]")
    
    # Get sample label nodes with variety
    query = """
    MATCH (l:Label)
    WHERE l.is_entry_point = true OR l.is_function = true
    RETURN l.label_id, l.name, l.routine_name, l.line_number, 
           l.is_entry_point, l.is_function, l.parameters
    ORDER BY l.routine_name, l.line_number
    LIMIT 10
    """
    
    result = session.run(query)
    labels = list(result)
    
    table = Table(title="Sample Label Nodes", show_header=True)
    table.add_column("Label", style="cyan")
    table.add_column("Routine", style="yellow")
    table.add_column("Line#", justify="right")
    table.add_column("Entry?", justify="center")
    table.add_column("Func?", justify="center")
    table.add_column("Parameters", style="green")
    
    for l in labels:
        params = ", ".join(l["l.parameters"]) if l["l.parameters"] else "None"
        table.add_row(
            l["l.name"],
            l["l.routine_name"],
            str(l["l.line_number"]),
            "✓" if l["l.is_entry_point"] else "",
            "✓" if l["l.is_function"] else "",
            params
        )
    
    console.print(table)
    
    validations = []
    for l in labels:
        # Check label has required fields
        if l["l.label_id"] and l["l.name"] and l["l.routine_name"]:
            validations.append(f"✅ {l['l.name']} in {l['l.routine_name']}: Complete structure")
        else:
            validations.append(f"❌ {l['l.name']}: Missing required fields")
    
    return validations

def validate_contains_label_relationships(session):
    """Validate 10 sample CONTAINS_LABEL relationships."""
    console.print("\n[bold cyan]═══ Validating CONTAINS_LABEL Relationships ═══[/bold cyan]")
    
    query = """
    MATCH (r:Routine)-[rel:CONTAINS_LABEL]->(l:Label)
    RETURN r.name as routine, l.name as label, 
           l.line_number as line_num, rel.line_number as rel_line
    ORDER BY r.name, l.line_number
    LIMIT 10
    """
    
    result = session.run(query)
    relationships = list(result)
    
    table = Table(title="Sample CONTAINS_LABEL Relationships", show_header=True)
    table.add_column("Routine", style="cyan")
    table.add_column("→", justify="center")
    table.add_column("Label", style="yellow")
    table.add_column("Line#", justify="right")
    table.add_column("Rel Line#", justify="right")
    
    validations = []
    for rel in relationships:
        table.add_row(
            rel["routine"],
            "→",
            rel["label"],
            str(rel["line_num"]),
            str(rel["rel_line"]) if rel["rel_line"] else "N/A"
        )
        
        # Validate relationship consistency
        if rel["line_num"] == rel["rel_line"] or rel["rel_line"] is None:
            validations.append(f"✅ {rel['routine']} → {rel['label']}: Line numbers consistent")
        else:
            validations.append(f"⚠️  {rel['routine']} → {rel['label']}: Line number mismatch")
    
    console.print(table)
    return validations

def validate_owns_routine_relationships(session):
    """Validate 10 sample OWNS_ROUTINE relationships."""
    console.print("\n[bold cyan]═══ Validating OWNS_ROUTINE Relationships ═══[/bold cyan]")
    
    query = """
    MATCH (p:Package)-[rel:OWNS_ROUTINE]->(r:Routine)
    WHERE r.prefix IS NOT NULL
    RETURN p.name as package, p.prefixes as prefixes, 
           r.name as routine, r.prefix as routine_prefix
    LIMIT 10
    """
    
    result = session.run(query)
    relationships = list(result)
    
    table = Table(title="Sample OWNS_ROUTINE Relationships", show_header=True)
    table.add_column("Package", style="cyan")
    table.add_column("Prefixes", style="dim")
    table.add_column("→", justify="center")
    table.add_column("Routine", style="yellow")
    table.add_column("R.Prefix", style="green")
    
    validations = []
    for rel in relationships:
        prefixes_str = ", ".join(rel["prefixes"]) if rel["prefixes"] else "None"
        table.add_row(
            rel["package"],
            prefixes_str,
            "→",
            rel["routine"],
            rel["routine_prefix"]
        )
        
        # Validate prefix matching
        if rel["prefixes"] and rel["routine_prefix"] in rel["prefixes"]:
            validations.append(f"✅ {rel['package']} owns {rel['routine']}: Prefix matches")
        else:
            validations.append(f"❌ {rel['package']} owns {rel['routine']}: Prefix mismatch!")
    
    console.print(table)
    return validations

def check_duplicates(session):
    """Check for duplicate nodes and relationships."""
    console.print("\n[bold red]═══ Checking for Duplicates ═══[/bold red]")
    
    checks = []
    
    # Check for duplicate Routine nodes
    query = """
    MATCH (r:Routine)
    WITH r.name as name, count(*) as cnt
    WHERE cnt > 1
    RETURN name, cnt
    ORDER BY cnt DESC
    LIMIT 10
    """
    result = session.run(query)
    dup_routines = list(result)
    
    if dup_routines:
        console.print("\n[red]⚠️  Found duplicate Routine nodes:[/red]")
        for dup in dup_routines:
            console.print(f"  • {dup['name']}: {dup['cnt']} copies")
        checks.append(f"❌ Found {len(dup_routines)} duplicate routine names")
    else:
        console.print("[green]✅ No duplicate Routine nodes found[/green]")
        checks.append("✅ No duplicate Routine nodes")
    
    # Check for duplicate Label nodes (same name + routine)
    query = """
    MATCH (l:Label)
    WITH l.routine_name + '::' + l.name as composite_key, count(*) as cnt
    WHERE cnt > 1
    RETURN composite_key, cnt
    ORDER BY cnt DESC
    LIMIT 10
    """
    result = session.run(query)
    dup_labels = list(result)
    
    if dup_labels:
        console.print("\n[red]⚠️  Found duplicate Label nodes:[/red]")
        for dup in dup_labels:
            console.print(f"  • {dup['composite_key']}: {dup['cnt']} copies")
        checks.append(f"❌ Found {len(dup_labels)} duplicate label combinations")
    else:
        console.print("[green]✅ No duplicate Label nodes found[/green]")
        checks.append("✅ No duplicate Label nodes")
    
    # Check for duplicate CONTAINS_LABEL relationships
    query = """
    MATCH (r:Routine)-[rel:CONTAINS_LABEL]->(l:Label)
    WITH r.name + '::' + l.name as rel_key, count(*) as cnt
    WHERE cnt > 1
    RETURN rel_key, cnt
    ORDER BY cnt DESC
    LIMIT 10
    """
    result = session.run(query)
    dup_rels = list(result)
    
    if dup_rels:
        console.print("\n[red]⚠️  Found duplicate CONTAINS_LABEL relationships:[/red]")
        for dup in dup_rels:
            console.print(f"  • {dup['rel_key']}: {dup['cnt']} copies")
        checks.append(f"❌ Found {len(dup_rels)} duplicate CONTAINS_LABEL relationships")
    else:
        console.print("[green]✅ No duplicate CONTAINS_LABEL relationships found[/green]")
        checks.append("✅ No duplicate CONTAINS_LABEL relationships")
    
    # Check routine-label consistency
    query = """
    MATCH (l:Label)
    WHERE NOT EXISTS {
        MATCH (r:Routine {name: l.routine_name})-[:CONTAINS_LABEL]->(l)
    }
    RETURN count(l) as orphaned_labels
    """
    result = session.run(query)
    orphaned = result.single()["orphaned_labels"]
    
    if orphaned > 0:
        console.print(f"\n[yellow]⚠️  Found {orphaned} orphaned labels (no routine relationship)[/yellow]")
        checks.append(f"⚠️  {orphaned} orphaned labels")
    else:
        console.print("[green]✅ All labels connected to routines[/green]")
        checks.append("✅ All labels properly connected")
    
    return checks

def validate_data_integrity(session):
    """Additional data integrity checks."""
    console.print("\n[bold magenta]═══ Data Integrity Checks ═══[/bold magenta]")
    
    checks = []
    
    # Check that routine names match label routine_names
    query = """
    MATCH (r:Routine)-[:CONTAINS_LABEL]->(l:Label)
    WHERE r.name <> l.routine_name
    RETURN r.name as routine, l.routine_name as label_routine, l.name as label
    LIMIT 5
    """
    result = session.run(query)
    mismatches = list(result)
    
    if mismatches:
        console.print("\n[red]❌ Found routine name mismatches:[/red]")
        for m in mismatches:
            console.print(f"  • Routine '{m['routine']}' contains label '{m['label']}' " +
                        f"but label thinks it belongs to '{m['label_routine']}'")
        checks.append(f"❌ {len(mismatches)} routine name mismatches")
    else:
        console.print("[green]✅ All routine-label names consistent[/green]")
        checks.append("✅ Routine-label names consistent")
    
    # Check line numbers are positive
    query = """
    MATCH (l:Label)
    WHERE l.line_number <= 0 OR l.line_number IS NULL
    RETURN count(l) as invalid_lines
    """
    result = session.run(query)
    invalid = result.single()["invalid_lines"]
    
    if invalid > 0:
        console.print(f"[red]❌ Found {invalid} labels with invalid line numbers[/red]")
        checks.append(f"❌ {invalid} invalid line numbers")
    else:
        console.print("[green]✅ All line numbers valid[/green]")
        checks.append("✅ All line numbers valid")
    
    # Check routine prefixes are uppercase
    query = """
    MATCH (r:Routine)
    WHERE r.prefix IS NOT NULL AND r.prefix <> toUpper(r.prefix)
    RETURN count(r) as lowercase_prefixes
    """
    result = session.run(query)
    lowercase = result.single()["lowercase_prefixes"]
    
    if lowercase > 0:
        console.print(f"[yellow]⚠️  Found {lowercase} routines with lowercase prefixes[/yellow]")
        checks.append(f"⚠️  {lowercase} lowercase prefixes")
    else:
        console.print("[green]✅ All prefixes properly uppercase[/green]")
        checks.append("✅ All prefixes uppercase")
    
    return checks

def main():
    """Run all validations."""
    driver = get_driver()
    
    console.print("[bold blue]╔═══════════════════════════════════════╗[/bold blue]")
    console.print("[bold blue]║   Phase 3 Graph Validation Report     ║[/bold blue]")
    console.print("[bold blue]╚═══════════════════════════════════════╝[/bold blue]")
    
    all_validations = []
    
    with driver.session() as session:
        # Validate nodes
        all_validations.extend(validate_routine_nodes(session))
        all_validations.extend(validate_label_nodes(session))
        
        # Validate relationships
        all_validations.extend(validate_contains_label_relationships(session))
        all_validations.extend(validate_owns_routine_relationships(session))
        
        # Check for duplicates
        all_validations.extend(check_duplicates(session))
        
        # Data integrity
        all_validations.extend(validate_data_integrity(session))
    
    # Summary
    console.print("\n[bold yellow]═══ Validation Summary ═══[/bold yellow]")
    
    passed = sum(1 for v in all_validations if v.startswith("✅"))
    warnings = sum(1 for v in all_validations if v.startswith("⚠️"))
    failed = sum(1 for v in all_validations if v.startswith("❌"))
    
    console.print(f"[green]✅ Passed: {passed}[/green]")
    console.print(f"[yellow]⚠️  Warnings: {warnings}[/yellow]")
    console.print(f"[red]❌ Failed: {failed}[/red]")
    
    if failed == 0:
        console.print("\n[bold green]🎉 Phase 3 graph validation PASSED![/bold green]")
    else:
        console.print("\n[bold red]⚠️  Phase 3 graph has issues that need attention[/bold red]")
    
    driver.close()

if __name__ == "__main__":
    main()