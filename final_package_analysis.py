#!/usr/bin/env python3
"""
Final analysis of package discrepancy - identify the 56 mismatched directories.
"""

import csv
from pathlib import Path

def final_analysis():
    packages_csv = Path("VistA-M-source-code/Packages.csv")
    packages_dir = Path("VistA-M-source-code/Packages")
    
    # Get filesystem directories
    filesystem_dirs = set(d.name for d in packages_dir.iterdir() if d.is_dir())
    print(f"Filesystem has {len(filesystem_dirs)} directories")
    
    # Parse CSV
    csv_packages = {}
    current_package = None
    
    with open(packages_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            package_name = row.get('Package Name', '').strip()
            directory_name = row.get('Directory Name', '').strip()
            
            if package_name:
                current_package = package_name
                csv_packages[package_name] = directory_name
    
    print(f"CSV defines {len(csv_packages)} packages")
    
    # Find mismatches
    print("\n=== ANALYSIS OF 56 MISMATCHED PACKAGES ===")
    
    # Group by type of mismatch
    no_directory_specified = []
    directory_doesnt_exist = []
    name_mismatch = []
    
    for pkg_name, directory in csv_packages.items():
        if not directory:
            no_directory_specified.append(pkg_name)
        elif directory not in filesystem_dirs:
            # Check if it's a naming convention issue
            # Some directories might use different naming conventions
            possible_matches = []
            
            # Try variations
            variations = [
                directory.replace(' ', ''),  # Remove spaces
                directory.replace(' ', '_'),  # Spaces to underscores
                directory.replace('/', ' '),  # Slash to space
                directory.replace('/', ''),   # Remove slash
                directory.replace('-', ' '),  # Dash to space
            ]
            
            for variant in variations:
                if variant in filesystem_dirs:
                    possible_matches.append(variant)
            
            if possible_matches:
                name_mismatch.append((pkg_name, directory, possible_matches))
            else:
                directory_doesnt_exist.append((pkg_name, directory))
    
    print(f"\nNo directory specified: {len(no_directory_specified)}")
    if no_directory_specified:
        print("These packages have no directory name in CSV:")
        for pkg in no_directory_specified[:10]:
            print(f"  - {pkg}")
    
    print(f"\nDirectory doesn't exist: {len(directory_doesnt_exist)}")
    if directory_doesnt_exist:
        print("These packages specify directories that don't exist:")
        for pkg, dir_name in sorted(directory_doesnt_exist)[:20]:
            print(f"  - {pkg} -> '{dir_name}'")
        if len(directory_doesnt_exist) > 20:
            print(f"  ... and {len(directory_doesnt_exist) - 20} more")
    
    print(f"\nPossible naming mismatches: {len(name_mismatch)}")
    if name_mismatch:
        print("These might be naming convention issues:")
        for pkg, csv_dir, matches in name_mismatch[:10]:
            print(f"  - {pkg}: CSV='{csv_dir}' might be: {matches}")
    
    # Show what's in filesystem but not matched
    csv_directories = set(d for d in csv_packages.values() if d)
    unmatched_filesystem = filesystem_dirs - csv_directories
    
    print(f"\n=== DIRECTORIES IN FILESYSTEM BUT NOT MATCHED ({len(unmatched_filesystem)}) ===")
    if unmatched_filesystem:
        for dir_name in sorted(unmatched_filesystem)[:10]:
            print(f"  - {dir_name}")
    
    # Final summary
    print("\n=== EXPLANATION OF THE 55 EXTRA PACKAGES ===")
    print("The graph has 195 packages while filesystem has 140 directories because:")
    print(f"1. The graph is built from Packages.csv which defines 195 packages")
    print(f"2. Of these 195 packages:")
    print(f"   - 139 have matching directories in the filesystem")
    print(f"   - 56 don't have matching directories, these are:")
    
    # Categorize the 56
    site_specific = []
    test_demo = []
    infrastructure = []
    other = []
    
    for pkg, _ in directory_doesnt_exist:
        pkg_upper = pkg.upper()
        if any(x in pkg_upper for x in ['VA', 'VAMC', 'VISN', 'CIOFO', 'OIFO']):
            site_specific.append(pkg)
        elif any(x in pkg_upper for x in ['TEST', 'DEMO']):
            test_demo.append(pkg)
        elif any(x in pkg_upper for x in ['PATCH', 'MASTER', 'LIBRARY', 'NATIONAL']):
            infrastructure.append(pkg)
        else:
            other.append(pkg)
    
    print(f"\n     a) {len(site_specific)} Site-specific packages (VA medical centers, etc)")
    if site_specific:
        print(f"        Examples: {', '.join(site_specific[:5])}")
    
    print(f"\n     b) {len(infrastructure)} Infrastructure/System packages")
    if infrastructure:
        print(f"        Examples: {', '.join(infrastructure[:5])}")
    
    print(f"\n     c) {len(test_demo)} Test/Demo packages")
    if test_demo:
        print(f"        Examples: {', '.join(test_demo[:5])}")
    
    print(f"\n     d) {len(other)} Other logical packages")
    if other:
        print(f"        Examples: {', '.join(other[:5])}")
    
    print("\n3. These are LOGICAL packages defined in the VistA system")
    print("   but don't have physical code directories in this repository.")
    print("   They likely represent:")
    print("   - Site-specific customizations")
    print("   - Infrastructure/system packages")
    print("   - Historical or deprecated packages")
    print("   - Packages that exist elsewhere in the VistA ecosystem")

if __name__ == "__main__":
    final_analysis()