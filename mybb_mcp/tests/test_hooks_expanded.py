"""Tests for expanded hook system."""

import pytest
from pathlib import Path
from mybb_mcp.tools.hooks_expanded import (
    HOOKS_REFERENCE_EXPANDED,
    discover_hooks,
    find_hook_usage,
)


def test_hooks_reference_expanded():
    """Test that expanded hooks reference contains 150+ hooks."""
    total_hooks = sum(len(hooks) for hooks in HOOKS_REFERENCE_EXPANDED.values())
    assert total_hooks >= 150, f"Expected 150+ hooks, got {total_hooks}"

    # Verify new categories exist
    assert "parser" in HOOKS_REFERENCE_EXPANDED
    assert "moderation" in HOOKS_REFERENCE_EXPANDED
    assert "email" in HOOKS_REFERENCE_EXPANDED
    assert "editpost" in HOOKS_REFERENCE_EXPANDED


def test_hooks_categories():
    """Test that all expected categories are present."""
    expected_categories = [
        "global", "index", "showthread", "member", "usercp",
        "forumdisplay", "newthread", "newreply", "editpost",
        "modcp", "admin", "parser", "moderation", "datahandler",
        "email", "misc"
    ]

    for category in expected_categories:
        assert category in HOOKS_REFERENCE_EXPANDED, f"Missing category: {category}"


def test_parser_hooks():
    """Test that parser hooks are correctly defined."""
    parser_hooks = HOOKS_REFERENCE_EXPANDED["parser"]

    expected_parser_hooks = [
        "parse_message_start",
        "parse_message_htmlsanitized",
        "parse_message_me_mycode",
        "parse_message",
        "parse_message_end",
        "text_parse_message"
    ]

    for hook in expected_parser_hooks:
        assert hook in parser_hooks, f"Missing parser hook: {hook}"


def test_authentication_hooks():
    """Test that authentication hooks are present in member category."""
    member_hooks = HOOKS_REFERENCE_EXPANDED["member"]

    expected_auth_hooks = [
        "member_login",
        "member_do_login_start",
        "member_do_login_end",
        "member_logout_start",
        "member_logout_end"
    ]

    for hook in expected_auth_hooks:
        assert hook in member_hooks, f"Missing auth hook: {hook}"


def test_datahandler_hooks():
    """Test that datahandler hooks are expanded."""
    datahandler_hooks = HOOKS_REFERENCE_EXPANDED["datahandler"]

    # Should have both post and user datahandler hooks
    assert "datahandler_post_validate_post" in datahandler_hooks
    assert "datahandler_post_validate_thread" in datahandler_hooks
    assert "datahandler_user_validate" in datahandler_hooks
    assert "datahandler_user_insert" in datahandler_hooks
    assert "datahandler_user_delete_start" in datahandler_hooks

    assert len(datahandler_hooks) >= 15, f"Expected 15+ datahandler hooks, got {len(datahandler_hooks)}"


def test_modcp_hooks_expanded():
    """Test that modcp hooks are significantly expanded."""
    modcp_hooks = HOOKS_REFERENCE_EXPANDED["modcp"]

    # Original had only 2 hooks, expanded should have 40+
    assert len(modcp_hooks) >= 40, f"Expected 40+ modcp hooks, got {len(modcp_hooks)}"

    # Check for specific modcp hooks from research
    expected_modcp_hooks = [
        "modcp_reports_start",
        "modcp_modqueue_threads_end",
        "modcp_banning",
        "modcp_ipsearch_posts_start",
        "modcp_modlogs_start"
    ]

    for hook in expected_modcp_hooks:
        assert hook in modcp_hooks, f"Missing modcp hook: {hook}"


def test_discover_hooks_function_exists():
    """Test that discover_hooks function is callable."""
    # Just verify the function exists and has correct signature
    import inspect
    sig = inspect.signature(discover_hooks)

    assert "mybb_root" in sig.parameters
    assert "path" in sig.parameters
    assert "category" in sig.parameters
    assert "search" in sig.parameters


def test_find_hook_usage_function_exists():
    """Test that find_hook_usage function is callable."""
    import inspect
    sig = inspect.signature(find_hook_usage)

    assert "mybb_root" in sig.parameters
    assert "hook_name" in sig.parameters


def test_discover_hooks_no_mybb_dir():
    """Test discover_hooks with non-existent MyBB directory."""
    fake_path = Path("/nonexistent/mybb")
    result = discover_hooks(fake_path)

    assert "No hooks found" in result


def test_find_hook_usage_no_plugins_dir():
    """Test find_hook_usage with non-existent plugins directory."""
    fake_path = Path("/nonexistent/mybb")
    result = find_hook_usage(fake_path, "global_start")

    assert "Plugins directory not found" in result
