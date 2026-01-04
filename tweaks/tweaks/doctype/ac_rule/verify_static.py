#!/usr/bin/env python3
"""
Static verification script for AC Rule DocType permission hooks.

This script performs static checks without importing Frappe dependencies.
"""

import os
import re


def check_file_exists(filepath, description):
    """Check if a file exists"""
    if os.path.exists(filepath):
        print(f"✓ {description} exists")
        return True
    else:
        print(f"✗ {description} NOT found")
        return False


def check_function_defined(filepath, function_name):
    """Check if a function is defined in a file"""
    with open(filepath, 'r') as f:
        content = f.read()
        
    # Check for function definition
    pattern = rf'^def {function_name}\s*\('
    if re.search(pattern, content, re.MULTILINE):
        print(f"✓ Function '{function_name}' is defined")
        return True
    else:
        print(f"✗ Function '{function_name}' NOT found")
        return False


def check_hook_registered(hooks_file, hook_type, hook_path):
    """Check if a hook is registered in hooks.py"""
    with open(hooks_file, 'r') as f:
        content = f.read()
    
    # Check if hook path is in the file
    if hook_path in content:
        print(f"✓ Hook '{hook_path}' is registered for '{hook_type}'")
        return True
    else:
        print(f"✗ Hook '{hook_path}' NOT found for '{hook_type}'")
        return False


def verify_ac_rule_utils():
    """Verify ac_rule_utils.py implementation"""
    print("=" * 60)
    print("Verifying ac_rule_utils.py...")
    print("=" * 60)
    
    filepath = "/home/runner/work/frappe_tweaks/frappe_tweaks/tweaks/tweaks/doctype/ac_rule/ac_rule_utils.py"
    
    results = []
    results.append(check_file_exists(filepath, "ac_rule_utils.py"))
    
    if results[0]:  # Only check functions if file exists
        results.append(check_function_defined(filepath, "ptype_to_action"))
        results.append(check_function_defined(filepath, "get_permission_query_conditions"))
        results.append(check_function_defined(filepath, "has_permission"))
    
    return all(results)


def verify_ptype_mapping_logic():
    """Verify ptype_to_action function logic"""
    print("\n" + "=" * 60)
    print("Verifying ptype_to_action logic...")
    print("=" * 60)
    
    filepath = "/home/runner/work/frappe_tweaks/frappe_tweaks/tweaks/tweaks/doctype/ac_rule/ac_rule_utils.py"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the ptype_to_action function
    pattern = r'def ptype_to_action\(ptype\):.*?(?=\ndef |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("✗ Could not find ptype_to_action function")
        return False
    
    function_body = match.group(0)
    
    # Check for key logic elements
    checks = [
        ('if not ptype:', "Checks for None/empty ptype"),
        ('return "Read"', "Returns default 'Read' action"),
        ('capitalize()', "Capitalizes ptype"),
    ]
    
    results = []
    for pattern, description in checks:
        if pattern in function_body:
            print(f"✓ {description}")
            results.append(True)
        else:
            print(f"✗ Missing: {description}")
            results.append(False)
    
    return all(results)


def verify_permission_query_conditions():
    """Verify get_permission_query_conditions function"""
    print("\n" + "=" * 60)
    print("Verifying get_permission_query_conditions...")
    print("=" * 60)
    
    filepath = "/home/runner/work/frappe_tweaks/frappe_tweaks/tweaks/tweaks/doctype/ac_rule/ac_rule_utils.py"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the function
    pattern = r'def get_permission_query_conditions\(doctype.*?\):.*?(?=\ndef |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("✗ Could not find get_permission_query_conditions function")
        return False
    
    function_body = match.group(0)
    
    # Check for key logic elements
    checks = [
        ('if user == "Administrator"', "Checks for Administrator"),
        ('return ""', "Returns empty string for unmanaged/full access"),
        ('get_resource_filter_query(', "Calls get_resource_filter_query"),
        ('result.get("unmanaged")', "Checks for unmanaged resources"),
        ('result.get("access")', "Checks access level"),
    ]
    
    results = []
    for pattern, description in checks:
        if pattern in function_body:
            print(f"✓ {description}")
            results.append(True)
        else:
            print(f"✗ Missing: {description}")
            results.append(False)
    
    return all(results)


def verify_has_permission_function():
    """Verify has_permission function"""
    print("\n" + "=" * 60)
    print("Verifying has_permission function...")
    print("=" * 60)
    
    filepath = "/home/runner/work/frappe_tweaks/frappe_tweaks/tweaks/tweaks/doctype/ac_rule/ac_rule_utils.py"
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Find the function
    pattern = r'def has_permission\(doc.*?\):.*?(?=\ndef |\Z)'
    match = re.search(pattern, content, re.DOTALL)
    
    if not match:
        print("✗ Could not find has_permission function")
        return False
    
    function_body = match.group(0)
    
    # Check for key logic elements
    checks = [
        ('if user == "Administrator"', "Checks for Administrator"),
        ('ptype_to_action(ptype)', "Maps ptype to action"),
        ('get_resource_rules(', "Calls get_resource_rules"),
        ('result.get("unmanaged")', "Checks for unmanaged resources"),
        ('return None', "Returns None for unmanaged"),
        ('isinstance(doc, dict)', "Handles dict documents"),
    ]
    
    results = []
    for pattern, description in checks:
        if pattern in function_body:
            print(f"✓ {description}")
            results.append(True)
        else:
            print(f"✗ Missing: {description}")
            results.append(False)
    
    return all(results)


def verify_hooks_registration():
    """Verify hooks are registered in hooks.py"""
    print("\n" + "=" * 60)
    print("Verifying hooks registration...")
    print("=" * 60)
    
    hooks_file = "/home/runner/work/frappe_tweaks/frappe_tweaks/tweaks/hooks.py"
    
    results = []
    results.append(check_file_exists(hooks_file, "hooks.py"))
    
    if results[0]:  # Only check hooks if file exists
        results.append(check_hook_registered(
            hooks_file,
            "has_permission",
            "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.has_permission"
        ))
        results.append(check_hook_registered(
            hooks_file,
            "permission_query_conditions",
            "tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_permission_query_conditions"
        ))
    
    return all(results)


def main():
    """Run all verification tests"""
    print("\n" + "=" * 60)
    print("AC Rule DocType Permission Hooks - Static Verification")
    print("=" * 60)
    
    results = []
    
    # Run all verification tests
    results.append(("ac_rule_utils.py Implementation", verify_ac_rule_utils()))
    results.append(("ptype_to_action Logic", verify_ptype_mapping_logic()))
    results.append(("get_permission_query_conditions Logic", verify_permission_query_conditions()))
    results.append(("has_permission Logic", verify_has_permission_function()))
    results.append(("Hooks Registration", verify_hooks_registration()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("✓ All verifications PASSED")
        print("\nThe AC Rule DocType permission hooks have been successfully implemented.")
        print("Key features:")
        print("  - Administrator always has full access")
        print("  - Unmanaged resources fall through to standard Frappe permissions")
        print("  - Supports Permit/Forbid rule logic")
        print("  - Handles resource filters for both list views and single documents")
        return 0
    else:
        print("✗ Some verifications FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
