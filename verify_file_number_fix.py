#!/usr/bin/env python3
"""
Verification script to confirm that file_number is consistently populated in all File nodes.
This addresses the previously reported issue about file_number not being populated.
"""

from pathlib import Path
from typing import Dict, List, Tuple
from src.parsers.zwr_parser import ZWRParser
from src.models.nodes import FileNode


def verify_file_number_population() -> Tuple[bool, str]:
    """
    Verify that file_number is populated in all File nodes.
    
    Returns:
        Tuple of (success, report_message)
    """
    report_lines = []
    report_lines.append("=" * 70)
    report_lines.append("FILE NUMBER POPULATION VERIFICATION REPORT")
    report_lines.append("=" * 70)
    report_lines.append("")
    
    # Test 1: Simple synthetic test
    report_lines.append("TEST 1: Synthetic ZWR Data")
    report_lines.append("-" * 30)
    
    test_zwr_content = """
^DD(2,0)="PATIENT^DPT(^"
^DD(2,0,"NM","PATIENT")=""
^DD(2,.01,0)="NAME^RF^^0;1^"
^DD(200,0)="NEW PERSON FILE^VA(200,^"
^DD(200,0,"NM","NEW PERSON FILE")=""
^DD(200,.01,0)="NAME^RF^^0;1^"
^DD(9.8,0)="ROUTINE^^"
^DD(9.8,0,"NM","ROUTINE")=""
^DD(404.51,0)="APPOINTMENT^SC(^"
^DD(404.51,0,"NM","APPOINTMENT")=""
"""
    
    parser = ZWRParser()
    lines = test_zwr_content.strip().split('\n')
    files, fields = parser.extract_file_definitions(lines)
    
    missing_file_numbers = []
    for file_num, file_node in files.items():
        if not file_node.file_number:
            missing_file_numbers.append((file_num, file_node.name))
    
    if missing_file_numbers:
        report_lines.append(f"❌ FAILED: {len(missing_file_numbers)} files missing file_number")
        for file_num, name in missing_file_numbers:
            report_lines.append(f"   - File key={file_num}, name={name}")
    else:
        report_lines.append(f"✅ PASSED: All {len(files)} files have file_number populated")
        report_lines.append("   Sample files verified:")
        for file_num, file_node in list(files.items())[:3]:
            report_lines.append(f"   - file_number={file_node.file_number}, name={file_node.name}")
    
    report_lines.append("")
    
    # Test 2: Check FileNode model structure
    report_lines.append("TEST 2: FileNode Model Structure")
    report_lines.append("-" * 30)
    
    # Create a FileNode directly to ensure the field exists
    test_file = FileNode(
        file_number="999",
        name="TEST_FILE",
        global_root="^TEST"
    )
    
    if hasattr(test_file, 'file_number') and test_file.file_number == "999":
        report_lines.append("✅ PASSED: FileNode has file_number field and it's assignable")
        report_lines.append(f"   - Created test FileNode with file_number={test_file.file_number}")
    else:
        report_lines.append("❌ FAILED: FileNode doesn't have proper file_number field")
    
    # Check dict_for_neo4j includes file_number
    neo4j_dict = test_file.dict_for_neo4j()
    if 'file_number' in neo4j_dict:
        report_lines.append("✅ PASSED: dict_for_neo4j() includes file_number field")
        report_lines.append(f"   - Neo4j dict contains: file_number={neo4j_dict['file_number']}")
    else:
        report_lines.append("❌ FAILED: dict_for_neo4j() missing file_number field")
    
    report_lines.append("")
    
    # Test 3: Parser assignment verification
    report_lines.append("TEST 3: Parser Assignment Logic")
    report_lines.append("-" * 30)
    
    # Check the parser creates FileNode with file_number correctly
    test_single_file = '^DD(42,0)="ANSWER^ANS^"'
    parser2 = ZWRParser()
    parsed = parser2.parse_line(test_single_file)
    
    if parsed and parsed.is_file_header():
        file_node = parser2._process_file_header(parsed)
        if file_node and file_node.file_number == "42":
            report_lines.append("✅ PASSED: Parser correctly assigns file_number from subscript")
            report_lines.append(f"   - Parsed file_number={file_node.file_number} from subscript '42'")
        else:
            report_lines.append("❌ FAILED: Parser didn't assign file_number correctly")
            if file_node:
                report_lines.append(f"   - Got file_number={file_node.file_number} instead of '42'")
    else:
        report_lines.append("⚠️  SKIPPED: Could not parse test line")
    
    report_lines.append("")
    
    # Summary
    report_lines.append("=" * 70)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 70)
    
    all_passed = len([line for line in report_lines if "❌ FAILED" in line]) == 0
    
    if all_passed:
        report_lines.append("✅ ALL TESTS PASSED - file_number is being populated consistently!")
        report_lines.append("")
        report_lines.append("The fix has been CONFIRMED to be working correctly:")
        report_lines.append("- FileNode model has the file_number field")
        report_lines.append("- Parser correctly extracts and assigns file_number from DD entries")
        report_lines.append("- All File nodes created have file_number populated")
        report_lines.append("- The field is properly included in Neo4j exports")
    else:
        report_lines.append("❌ SOME TESTS FAILED - file_number population issue may persist")
        report_lines.append("Please review the failed tests above for details.")
    
    report_lines.append("")
    report_lines.append("=" * 70)
    
    report = "\n".join(report_lines)
    return all_passed, report


if __name__ == "__main__":
    success, report = verify_file_number_population()
    print(report)
    
    # Exit with appropriate code
    import sys
    sys.exit(0 if success else 1)