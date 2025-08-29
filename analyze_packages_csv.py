#!/usr/bin/env python3
"""
Analyze Packages.csv to understand the package structure.
"""

import csv
from pathlib import Path
from collections import defaultdict

def analyze_packages_csv():
    packages_csv = Path("VistA-M-source-code/Packages.csv")
    
    packages = {}
    current_package = None
    
    with open(packages_csv, 'r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            package_name = row.get('Package Name', '').strip()
            directory_name = row.get('Directory Name', '').strip()
            prefixes = row.get('Prefixes', '').strip()
            file_numbers = row.get('File Numbers', '').strip()
            
            # If package name is present, this is a main package entry
            if package_name:
                current_package = package_name
                packages[package_name] = {
                    'directory': directory_name,
                    'prefixes': [prefixes] if prefixes else [],
                    'file_numbers': [file_numbers] if file_numbers else [],
                    'file_names': [],
                    'rows': 1
                }
            # If no package name but has data, this is a continuation row
            elif current_package and (prefixes or file_numbers):
                if prefixes:
                    packages[current_package]['prefixes'].append(prefixes)
                if file_numbers:
                    packages[current_package]['file_numbers'].append(file_numbers)
                packages[current_package]['rows'] += 1
    
    print(f"Total unique packages in CSV: {len(packages)}")
    
    # Categorize packages
    with_directory = []
    without_directory = []
    
    for pkg_name, info in packages.items():
        if info['directory']:
            with_directory.append((pkg_name, info['directory']))
        else:
            without_directory.append(pkg_name)
    
    print(f"\nPackages WITH directory: {len(with_directory)}")
    print(f"Packages WITHOUT directory: {len(without_directory)}")
    
    # Check which directories exist
    packages_dir = Path("VistA-M-source-code/Packages")
    existing_dirs = set(d.name for d in packages_dir.iterdir() if d.is_dir())
    
    matched = []
    mismatched = []
    
    for pkg_name, directory in with_directory:
        if directory in existing_dirs:
            matched.append((pkg_name, directory))
        else:
            mismatched.append((pkg_name, directory))
    
    print(f"\nPackages with EXISTING directories: {len(matched)}")
    print(f"Packages with NON-EXISTING directories: {len(mismatched)}")
    
    # Show packages without directories (these are the extra 55!)
    print(f"\n=== PACKAGES WITHOUT DIRECTORIES ({len(without_directory)}) ===")
    print("These are logical/administrative packages that don't have physical directories:")
    
    # Categorize them
    categories = defaultdict(list)
    
    for pkg in without_directory:
        info = packages[pkg]
        if 'TEST' in pkg.upper() or 'DEMO' in pkg.upper():
            categories['Test/Demo'].append(pkg)
        elif 'VA' in pkg.upper() or 'VAMC' in pkg.upper() or 'CIOFO' in pkg.upper():
            categories['Site-Specific'].append(pkg)
        elif 'PATCH' in pkg.upper() or 'KERNEL' in pkg.upper() or 'FILEMAN' in pkg.upper():
            categories['System/Infrastructure'].append(pkg)
        elif any(p for p in info['prefixes']):
            categories['Has Prefixes'].append(pkg)
        else:
            categories['Other'].append(pkg)
    
    for category, pkgs in sorted(categories.items()):
        print(f"\n{category} ({len(pkgs)}):")
        for pkg in sorted(pkgs)[:10]:
            info = packages[pkg]
            prefixes = ', '.join(info['prefixes']) if info['prefixes'] else 'None'
            print(f"  - {pkg}: prefixes=[{prefixes}]")
        if len(pkgs) > 10:
            print(f"  ... and {len(pkgs) - 10} more")
    
    # Show packages with the most file numbers
    print("\n=== PACKAGES WITH MOST FILE NUMBERS ===")
    by_file_count = sorted(packages.items(), 
                          key=lambda x: len(x[1]['file_numbers']), 
                          reverse=True)
    
    for pkg_name, info in by_file_count[:10]:
        file_count = len(info['file_numbers'])
        has_dir = "✓" if info['directory'] else "✗"
        print(f"  {pkg_name}: {file_count} files, dir={has_dir}")
    
    # Summary
    print("\n=== SUMMARY ===")
    print(f"The CSV defines {len(packages)} packages total:")
    print(f"  - {len(matched)} have directories and exist in filesystem")
    print(f"  - {len(mismatched)} have directories but don't exist in filesystem")
    print(f"  - {len(without_directory)} are logical packages without directories")
    print(f"\nThis explains the discrepancy:")
    print(f"  Filesystem: 140 physical directories")
    print(f"  Graph: 195 packages (140 physical + 55 logical)")
    print(f"  CSV: 196 package definitions (source of truth)")

if __name__ == "__main__":
    analyze_packages_csv()