#!/usr/bin/env python
"""Debug script to check why Phase 2 relationships aren't being created."""

from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

def debug_phase2():
    """Debug Phase 2 relationship creation."""
    load_dotenv()
    driver = GraphDatabase.driver(
        os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        auth=(os.getenv("NEO4J_USER", "neo4j"), os.getenv("NEO4J_PASSWORD", "password"))
    )
    
    with driver.session() as session:
        print("=== CHECKING PHASE 2 ENTITIES ===\n")
        
        # 1. Check if CrossReference nodes and Fields exist with matching IDs
        print("1. Checking for matching Field-CrossReference pairs...")
        result = session.run("""
            MATCH (x:CrossReference)
            RETURN x.file_number as file_num, x.field_number as field_num, x.name as xref_name
            LIMIT 5
        """)
        
        xrefs = list(result)
        print(f"Sample CrossReferences:")
        for xref in xrefs:
            print(f"  File: {xref['file_num']}, Field: {xref['field_num']}, Name: {xref['xref_name']}")
            
            # Check if corresponding field exists
            field_check = session.run("""
                MATCH (f:Field {file_number: $file_num, number: $field_num})
                RETURN f.field_id as field_id, f.name as name
            """, file_num=xref['file_num'], field_num=xref['field_num'])
            
            field = field_check.single()
            if field:
                print(f"    ✓ Found matching field: {field['name']} (ID: {field['field_id']})")
            else:
                print(f"    ✗ No matching field found!")
        
        print("\n2. Trying to manually create an INDEXED_BY relationship...")
        
        # Get one xref and its matching field
        test_result = session.run("""
            MATCH (x:CrossReference)
            WITH x LIMIT 1
            MATCH (f:Field {file_number: x.file_number, number: x.field_number})
            RETURN f.field_id as field_id, x.xref_id as xref_id, 
                   f.name as field_name, x.name as xref_name
        """)
        
        test = test_result.single()
        if test:
            print(f"Found pair: Field '{test['field_name']}' -> XRef '{test['xref_name']}'")
            
            # Try to create relationship
            create_result = session.run("""
                MATCH (f:Field {field_id: $field_id})
                MATCH (x:CrossReference {xref_id: $xref_id})
                CREATE (f)-[r:INDEXED_BY]->(x)
                SET r.xref_name = x.name, r.xref_type = x.xref_type
                RETURN count(r) as created
            """, field_id=test['field_id'], xref_id=test['xref_id'])
            
            created = create_result.single()['created']
            if created:
                print(f"  ✓ Successfully created INDEXED_BY relationship!")
                
                # Verify it exists
                verify = session.run("""
                    MATCH (f:Field)-[r:INDEXED_BY]->(x:CrossReference)
                    RETURN count(r) as count
                """).single()
                print(f"  Total INDEXED_BY relationships now: {verify['count']}")
            else:
                print("  ✗ Failed to create relationship")
        else:
            print("  ✗ Could not find matching Field-CrossReference pair")
            
        print("\n3. Checking subfile candidates...")
        subfile_check = session.run("""
            MATCH (f:File)
            WHERE f.number CONTAINS '.'
            RETURN f.number as num, f.name as name
            ORDER BY f.number
            LIMIT 5
        """)
        
        print("Sample subfiles (files with decimal numbers):")
        for sf in subfile_check:
            print(f"  {sf['num']}: {sf['name']}")
            
            # Check parent
            parent_num = sf['num'].split('.')[0]
            parent_check = session.run("""
                MATCH (p:File {number: $num})
                RETURN p.name as name
            """, num=parent_num)
            
            parent = parent_check.single()
            if parent:
                print(f"    Parent {parent_num}: {parent['name']}")
                
        print("\n4. Checking V-type fields...")
        v_check = session.run("""
            MATCH (f:Field {data_type: 'V'})
            RETURN f.file_number as file_num, f.number as field_num, f.name as name
            LIMIT 5
        """)
        
        print("Sample V-type (Variable Pointer) fields:")
        for vf in v_check:
            print(f"  File {vf['file_num']}, Field {vf['field_num']}: {vf['name']}")
    
    driver.close()

if __name__ == "__main__":
    debug_phase2()