#!/usr/bin/env python3
"""
Manual verification script for AC Rule DocType permission hooks.

This script verifies that the permission hook functions are correctly implemented
and can be imported without errors.
"""

import sys
import os

# Add the tweaks directory to the path
tweaks_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if tweaks_dir not in sys.path:
    sys.path.insert(0, tweaks_dir)

def verify_imports():
    """Verify that all required modules can be imported"""
    print("=" * 60)
    print("Verifying imports...")
    print("=" * 60)
    
    try:
        # Import the module directly
        sys.path.insert(0, os.path.join(tweaks_dir, 'tweaks', 'doctype', 'ac_rule'))
        import ac_rule_utils
        print("✓ Successfully imported ac_rule_utils")
        
        # Check that the new functions exist
        assert hasattr(ac_rule_utils, 'ptype_to_action'), "Missing ptype_to_action function"
        print("✓ ptype_to_action function exists")
        
        assert hasattr(ac_rule_utils, 'get_permission_query_conditions'), "Missing get_permission_query_conditions function"
        print("✓ get_permission_query_conditions function exists")
        
        assert hasattr(ac_rule_utils, 'has_permission'), "Missing has_permission function"
        print("✓ has_permission function exists")
        
        return True
    except Exception as e:
        print(f"✗ Import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_ptype_mapping():
    """Verify ptype to action mapping logic"""
    print("\n" + "=" * 60)
    print("Verifying ptype to action mapping...")
    print("=" * 60)
    
    try:
        sys.path.insert(0, os.path.join(tweaks_dir, 'tweaks', 'doctype', 'ac_rule'))
        import ac_rule_utils
        ptype_to_action = ac_rule_utils.ptype_to_action
        
        # Test various ptype values
        test_cases = [
            ("read", "Read"),
            ("write", "Write"),
            ("create", "Create"),
            ("delete", "Delete"),
            ("submit", "Submit"),
            ("cancel", "Cancel"),
            ("amend", "Amend"),
            ("print", "Print"),
            ("email", "Email"),
            ("import", "Import"),
            ("export", "Export"),
            ("share", "Share"),
            ("select", "Select"),
            ("report", "Report"),
            (None, "Read"),  # Default case
        ]
        
        all_passed = True
        for ptype, expected in test_cases:
            result = ptype_to_action(ptype)
            if result == expected:
                print(f"✓ ptype_to_action('{ptype}') = '{result}'")
            else:
                print(f"✗ ptype_to_action('{ptype}') = '{result}' (expected '{expected}')")
                all_passed = False
        
        return all_passed
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_function_signatures():
    """Verify that functions have correct signatures"""
    print("\n" + "=" * 60)
    print("Verifying function signatures...")
    print("=" * 60)
    
    try:
        import inspect
        sys.path.insert(0, os.path.join(tweaks_dir, 'tweaks', 'doctype', 'ac_rule'))
        import ac_rule_utils
        
        get_permission_query_conditions = ac_rule_utils.get_permission_query_conditions
        has_permission = ac_rule_utils.has_permission
        
        # Check get_permission_query_conditions signature
        sig = inspect.signature(get_permission_query_conditions)
        params = list(sig.parameters.keys())
        assert 'doctype' in params, "get_permission_query_conditions missing 'doctype' parameter"
        assert 'user' in params, "get_permission_query_conditions missing 'user' parameter"
        print(f"✓ get_permission_query_conditions signature: {sig}")
        
        # Check has_permission signature
        sig = inspect.signature(has_permission)
        params = list(sig.parameters.keys())
        assert 'doc' in params, "has_permission missing 'doc' parameter"
        assert 'ptype' in params, "has_permission missing 'ptype' parameter"
        assert 'user' in params, "has_permission missing 'user' parameter"
        assert 'debug' in params, "has_permission missing 'debug' parameter"
        print(f"✓ has_permission signature: {sig}")
        
        return True
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def verify_hooks_registration():
    """Verify that hooks are properly registered"""
    print("\n" + "=" * 60)
    print("Verifying hooks registration...")
    print("=" * 60)
    
    try:
        # Import hooks.py directly
        import importlib.util
        hooks_path = os.path.join(tweaks_dir, 'hooks.py')
        spec = importlib.util.spec_from_file_location("hooks", hooks_path)
        hooks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(hooks)
        
        # Check has_permission hooks
        if hasattr(hooks, 'has_permission'):
            has_perm_hooks = hooks.has_permission.get('*', [])
            expected_hook = 'tweaks.tweaks.doctype.ac_rule.ac_rule_utils.has_permission'
            if expected_hook in has_perm_hooks:
                print(f"✓ has_permission hook registered: {expected_hook}")
            else:
                print(f"✗ has_permission hook NOT found in hooks")
                print(f"  Found hooks: {has_perm_hooks}")
                return False
        else:
            print("✗ has_permission not found in hooks")
            return False
        
        # Check permission_query_conditions hooks
        if hasattr(hooks, 'permission_query_conditions'):
            perm_query_hooks = hooks.permission_query_conditions.get('*', [])
            expected_hook = 'tweaks.tweaks.doctype.ac_rule.ac_rule_utils.get_permission_query_conditions'
            if expected_hook in perm_query_hooks:
                print(f"✓ permission_query_conditions hook registered: {expected_hook}")
            else:
                print(f"✗ permission_query_conditions hook NOT found in hooks")
                print(f"  Found hooks: {perm_query_hooks}")
                return False
        else:
            print("✗ permission_query_conditions not found in hooks")
            return False
        
        return True
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all verification tests"""
    print("\n" + "=" * 60)
    print("AC Rule DocType Permission Hooks - Verification Script")
    print("=" * 60)
    
    results = []
    
    # Run all verification tests
    results.append(("Import Verification", verify_imports()))
    results.append(("Ptype Mapping Verification", verify_ptype_mapping()))
    results.append(("Function Signature Verification", verify_function_signatures()))
    results.append(("Hooks Registration Verification", verify_hooks_registration()))
    
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
        return 0
    else:
        print("✗ Some verifications FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(main())
