#!/usr/bin/env python3
"""
Investigate package discrepancy between graph (195) and filesystem (140).
"""

import os
from pathlib import Path
from src.graph.connection import Neo4jConnection

def investigate_packages():
    # Get filesystem packages
    packages_dir = Path("VistA-M-source-code/Packages")
    filesystem_packages = set()
    for item in packages_dir.iterdir():
        if item.is_dir():
            filesystem_packages.add(item.name)
    
    print(f"Filesystem packages: {len(filesystem_packages)}")
    
    # Get graph packages
    conn = Neo4jConnection()
    conn.connect()
    
    graph_packages = {}
    graph_packages_by_dir = {}
    
    with conn.driver.session() as session:
        # Get all packages with their properties
        result = session.run('''
            MATCH (p:Package)
            OPTIONAL MATCH (p)-[:OWNS_ROUTINE]->(r:Routine)
            RETURN p.name as name, 
                   p.directory as directory,
                   p.package_id as package_id,
                   p.prefixes as prefixes,
                   p.file_numbers as file_numbers,
                   count(r) as routine_count
            ORDER BY p.name
        ''')
        
        for record in result:
            name = record['name']
            directory = record['directory']
            graph_packages[name] = {
                'directory': directory,
                'package_id': record['package_id'],
                'prefixes': record['prefixes'],
                'file_numbers': record['file_numbers'],
                'routine_count': record['routine_count']
            }
            
            # Also track by directory for matching
            if directory:
                if directory not in graph_packages_by_dir:
                    graph_packages_by_dir[directory] = []
                graph_packages_by_dir[directory].append(name)
    
    print(f"Graph packages: {len(graph_packages)}")
    
    # Find packages in graph but not in filesystem
    extra_in_graph = []
    matched_packages = []
    mismatched_directory = []
    
    for pkg_name, pkg_info in graph_packages.items():
        directory = pkg_info['directory']
        
        # Check if directory exists in filesystem
        if directory in filesystem_packages:
            matched_packages.append((pkg_name, directory))
        elif directory and directory != pkg_name:
            # Directory specified but doesn't match filesystem
            mismatched_directory.append((pkg_name, directory))
        else:
            # No matching directory found
            extra_in_graph.append(pkg_name)
    
    # Find packages in filesystem but not matched
    unmatched_filesystem = filesystem_packages - set([d for _, d in matched_packages])
    
    print(f"\n=== ANALYSIS ===")
    print(f"Matched packages: {len(matched_packages)}")
    print(f"Extra in graph: {len(extra_in_graph)}")
    print(f"Mismatched directory: {len(mismatched_directory)}")
    print(f"Unmatched filesystem: {len(unmatched_filesystem)}")
    
    # Check for duplicates in graph
    print("\n=== CHECKING FOR DUPLICATES IN GRAPH ===")
    directories_with_multiple = {}
    for directory, names in graph_packages_by_dir.items():
        if len(names) > 1:
            directories_with_multiple[directory] = names
    
    if directories_with_multiple:
        print(f"Found {len(directories_with_multiple)} directories with multiple package names:")
        for directory, names in sorted(directories_with_multiple.items())[:10]:
            print(f"  Directory '{directory}' has packages: {', '.join(names)}")
    
    # Show packages with no routines
    print("\n=== PACKAGES WITH NO ROUTINES ===")
    no_routine_packages = [name for name, info in graph_packages.items() 
                          if info['routine_count'] == 0]
    print(f"Found {len(no_routine_packages)} packages with no routines")
    if no_routine_packages:
        print("First 10:", no_routine_packages[:10])
    
    # Show extra packages in detail
    print("\n=== EXTRA PACKAGES IN GRAPH (not in filesystem) ===")
    print(f"Total: {len(extra_in_graph)}")
    
    # Categorize extra packages
    logical_packages = []
    test_packages = []
    site_specific = []
    other = []
    
    for pkg in extra_in_graph:
        pkg_upper = pkg.upper()
        if 'TEST' in pkg_upper or 'DEMO' in pkg_upper:
            test_packages.append(pkg)
        elif 'VA' in pkg_upper or 'VAMC' in pkg_upper or 'VISN' in pkg_upper:
            site_specific.append(pkg)
        elif pkg in ['CONTROLLED SUBSTANCES', 'HEALTH DATA REPOSITORY', 
                     'MASTER PATIENT INDEX', 'PATCH MODULE', 'VBECS']:
            logical_packages.append(pkg)
        else:
            other.append(pkg)
    
    print(f"\nLogical/System packages ({len(logical_packages)}):")
    for pkg in sorted(logical_packages):
        info = graph_packages[pkg]
        print(f"  - {pkg}: prefixes={info['prefixes']}, routines={info['routine_count']}")
    
    print(f"\nTest/Demo packages ({len(test_packages)}):")
    for pkg in sorted(test_packages)[:5]:
        info = graph_packages[pkg]
        print(f"  - {pkg}: prefixes={info['prefixes']}, routines={info['routine_count']}")
    
    print(f"\nSite-specific packages ({len(site_specific)}):")
    for pkg in sorted(site_specific)[:5]:
        info = graph_packages[pkg]
        print(f"  - {pkg}: prefixes={info['prefixes']}, routines={info['routine_count']}")
    
    print(f"\nOther packages ({len(other)}):")
    for pkg in sorted(other)[:10]:
        info = graph_packages[pkg]
        print(f"  - {pkg}: prefixes={info['prefixes']}, routines={info['routine_count']}")
    
    # Check Packages.csv for the source of truth
    print("\n=== CHECKING Packages.csv ===")
    packages_csv = Path("VistA-M-source-code/Packages.csv")
    if packages_csv.exists():
        import csv
        csv_packages = set()
        with open(packages_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'Package Name' in row:
                    csv_packages.add(row['Package Name'])
        
        print(f"Packages in Packages.csv: {len(csv_packages)}")
        
        # Compare with graph
        in_csv_not_filesystem = csv_packages - filesystem_packages
        print(f"In CSV but not filesystem: {len(in_csv_not_filesystem)}")
        if in_csv_not_filesystem:
            print("First 10:", list(sorted(in_csv_not_filesystem))[:10])

if __name__ == "__main__":
    investigate_packages()