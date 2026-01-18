"""Integration tests for hook discovery with actual MyBB installation."""

import pytest
from pathlib import Path
from mybb_mcp.tools.hooks_expanded import discover_hooks, find_hook_usage


# Skip if TestForum not available
TESTFORUM_PATH = Path("/home/austin/projects/MyBB_Playground/TestForum")
skip_if_no_testforum = pytest.mark.skipif(
    not TESTFORUM_PATH.exists(),
    reason="TestForum installation not found"
)


@skip_if_no_testforum
def test_discover_hooks_in_testforum():
    """Test hook discovery in actual TestForum installation."""
    result = discover_hooks(TESTFORUM_PATH)

    # Should find many hooks
    assert "Discovered" in result
    assert "Hook Name" in result  # Table header
    assert "global_start" in result or "index_start" in result


@skip_if_no_testforum
def test_discover_hooks_global_php():
    """Test discovering hooks in global.php specifically."""
    result = discover_hooks(TESTFORUM_PATH, path="global.php")

    assert "Discovered" in result
    # global.php should have global_start, global_intermediate, global_end
    assert "global_start" in result or "global_intermediate" in result or "global_end" in result


@skip_if_no_testforum
def test_discover_hooks_with_category_filter():
    """Test discovering hooks filtered by category."""
    result = discover_hooks(TESTFORUM_PATH, category="member")

    assert "Discovered" in result
    # Should only find member_* hooks
    if "member_" in result:
        # Verify no non-member hooks are present
        assert "index_start" not in result
        assert "global_start" not in result


@skip_if_no_testforum
def test_discover_hooks_with_search():
    """Test discovering hooks with search term."""
    result = discover_hooks(TESTFORUM_PATH, search="login")

    assert "Discovered" in result
    # Should find login-related hooks
    if "login" in result.lower():
        lines = result.split('\n')
        # Verify table format
        assert any("|" in line for line in lines)


@skip_if_no_testforum
def test_find_hook_usage_global_start():
    """Test finding usage of global_start hook in plugins."""
    result = find_hook_usage(TESTFORUM_PATH, "global_start")

    # Even if no plugins use it, should return proper message
    assert "global_start" in result
    assert "Hook Usage" in result or "not used" in result


@skip_if_no_testforum
def test_discover_hooks_parser():
    """Test discovering parser hooks in class_parser.php."""
    result = discover_hooks(TESTFORUM_PATH, path="inc/class_parser.php")

    assert "Discovered" in result
    # Should find parse_message hooks
    if "parse_message" in result:
        assert "class_parser.php" in result
