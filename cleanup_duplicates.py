"""
Clean up duplicate CrossReference nodes in the database.
Keeps one copy of each unique xref_id and removes the duplicates.
"""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI", "bolt://localhost:7687"),
    auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
)

with driver.session() as session:
    print("=== Cleaning Up Duplicate CrossReference Nodes ===\n")
    
    # First, check current state
    result = session.run("MATCH (x:CrossReference) RETURN count(x) as count")
    total_before = result.single()["count"]
    print(f"Total CrossReference nodes before cleanup: {total_before}")
    
    # Delete duplicates, keeping one of each xref_id
    print("\nRemoving duplicates...")
    result = session.run("""
        MATCH (x:CrossReference)
        WITH x.xref_id as xref_id, COLLECT(x) as nodes
        WHERE SIZE(nodes) > 1
        // Keep the first node, delete the rest
        FOREACH (n IN TAIL(nodes) | DETACH DELETE n)
        RETURN COUNT(DISTINCT xref_id) as cleaned_groups
    """)
    
    cleaned = result.single()["cleaned_groups"]
    print(f"Cleaned {cleaned} groups of duplicates")
    
    # Check result
    result = session.run("MATCH (x:CrossReference) RETURN count(x) as count")
    total_after = result.single()["count"]
    print(f"\nTotal CrossReference nodes after cleanup: {total_after}")
    print(f"Removed {total_before - total_after} duplicate nodes")
    
    # Verify uniqueness
    result = session.run("""
        MATCH (x:CrossReference)
        WITH x.xref_id as xref_id, count(x) as count
        WHERE count > 1
        RETURN count(*) as remaining_duplicates
    """)
    remaining = result.single()["remaining_duplicates"]
    
    if remaining == 0:
        print("\n✅ All duplicates successfully removed!")
    else:
        print(f"\n⚠️ Warning: {remaining} duplicate groups remain")
    
    # Check relationships
    print("\n=== Checking Relationships ===")
    for rel_type in ["INDEXED_BY", "SUBFILE_OF"]:
        result = session.run(f"""
            MATCH ()-[r:{rel_type}]->()
            RETURN count(r) as count
        """)
        count = result.single()["count"]
        print(f"  {rel_type}: {count} relationships")

driver.close()

print("\n✅ Cleanup complete!")