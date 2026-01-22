"""
Test for bug: Duplicate tree depth settings causing UI inconsistency

Bug ID: 2026-01-21_duplicate_tree_depth_settings
Category: logic
Severity: medium

Description:
The invite_system plugin defines TWO settings for tree depth:
1. 'invite_system_tree_max_depth' (line 625) - numeric optionscode
2. 'invite_tree_max_depth' (line 1099) - select dropdown

Different parts of the code reference different setting names:
- admin/settings.php uses 'invite_system_tree_max_depth'
- InviteTree.php and usercp.php use 'invite_tree_max_depth'

This creates inconsistency and confusion in the ACP.

Expected behavior:
- Only ONE setting should exist for tree depth
- All code should reference the same setting name
- The setting should have a proper select dropdown (1-10)

Test strategy:
1. Parse the plugin file to find all setting definitions
2. Check for duplicate tree depth settings
3. Verify that only one tree depth setting exists after fix
4. Verify that all code references use the same setting name
"""

import re
from pathlib import Path

def test_no_duplicate_tree_depth_settings():
    """Test that only one tree depth setting is defined in _install()"""
    plugin_file = Path("/home/austin/projects/MyBB_Playground/plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php")

    assert plugin_file.exists(), "Plugin file not found"

    content = plugin_file.read_text()

    # Find all settings definitions with 'tree' and 'depth' in the name
    tree_depth_pattern = r"'name'\s*=>\s*'[^']*tree[^']*depth[^']*'"
    matches = re.findall(tree_depth_pattern, content, re.IGNORECASE)

    # Extract setting names
    setting_names = [re.search(r"'([^']+)'$", match).group(1) for match in matches]

    print(f"Found tree depth settings: {setting_names}")

    # There should be exactly ONE tree depth setting
    assert len(setting_names) == 1, f"Expected 1 tree depth setting, found {len(setting_names)}: {setting_names}"

    # The single setting should be 'invite_tree_max_depth' (the one with select dropdown)
    assert setting_names[0] == 'invite_tree_max_depth', f"Expected 'invite_tree_max_depth', got '{setting_names[0]}'"


def test_tree_depth_setting_has_select_optionscode():
    """Test that the tree depth setting uses a select dropdown (not numeric)"""
    plugin_file = Path("/home/austin/projects/MyBB_Playground/plugin_manager/plugins/private/invite_system/inc/plugins/invite_system.php")

    content = plugin_file.read_text()

    # Find the invite_tree_max_depth setting definition
    pattern = r"'name'\s*=>\s*'invite_tree_max_depth'.*?'optionscode'\s*=>\s*'([^']+)'"
    match = re.search(pattern, content, re.DOTALL)

    assert match, "Could not find invite_tree_max_depth setting"

    optionscode = match.group(1)

    print(f"Found optionscode: {optionscode[:50]}...")

    # Should be a select dropdown with options 1-10
    assert optionscode.startswith('select\\n'), f"Expected select optionscode, got: {optionscode[:20]}"
    assert '1=1' in optionscode, "Select should include option 1=1"
    assert '10=10' in optionscode, "Select should include option 10=10"


def test_consistent_setting_name_usage():
    """Test that all code uses 'invite_tree_max_depth' (not invite_system_tree_max_depth)"""
    base_path = Path("/home/austin/projects/MyBB_Playground/plugin_manager/plugins/private/invite_system")

    # Files that should use the setting
    files_to_check = [
        base_path / "inc/plugins/invite_system/admin/settings.php",
        base_path / "inc/plugins/invite_system/core/InviteTree.php",
        base_path / "inc/plugins/invite_system/handlers/usercp.php"
    ]

    wrong_setting_name = 'invite_system_tree_max_depth'
    correct_setting_name = 'invite_tree_max_depth'

    for file_path in files_to_check:
        if not file_path.exists():
            continue

        content = file_path.read_text()

        # Check for wrong setting name
        if wrong_setting_name in content:
            # Find the line number for better error message
            lines = content.split('\n')
            wrong_lines = [i+1 for i, line in enumerate(lines) if wrong_setting_name in line]

            assert False, f"{file_path.name} uses deprecated setting name '{wrong_setting_name}' on lines: {wrong_lines}. Should use '{correct_setting_name}'"


if __name__ == "__main__":
    print("Running bug reproduction tests...")
    print("\n=== Test 1: No duplicate settings ===")
    try:
        test_no_duplicate_tree_depth_settings()
        print("✅ PASS")
    except AssertionError as e:
        print(f"❌ FAIL: {e}")

    print("\n=== Test 2: Correct optionscode ===")
    try:
        test_tree_depth_setting_has_select_optionscode()
        print("✅ PASS")
    except AssertionError as e:
        print(f"❌ FAIL: {e}")

    print("\n=== Test 3: Consistent usage ===")
    try:
        test_consistent_setting_name_usage()
        print("✅ PASS")
    except AssertionError as e:
        print(f"❌ FAIL: {e}")
