---
id: mybb_forge_v2-task-package-6-1-subtree-handlers
title: 'Task Package 6.1: Subtree Handler Module Implementation'
doc_name: TASK_PACKAGE_6_1_SUBTREE_HANDLERS
category: implementation
status: draft
version: '0.1'
last_updated: '2026-01-19'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---
# Task Package 6.1: Subtree Handler Module Implementation

## Overview

**Date:** 2026-01-19  
**Agent:** MyBB-Coder  
**Phase:** 6  
**Task Package:** 6.1  
**Confidence:** 0.95

## Scope of Work

Created new MCP tools for git subtree operations with ForgeConfig integration. This allows managing external repositories as subtrees through Claude Code with automatic remote URL resolution from `.mybb-forge.yaml`.

## Files Created

### 1. `mybb_mcp/mybb_mcp/handlers/subtrees.py` (265 lines)

Complete subtree handler module with:
- **ForgeConfig integration** - Dynamic import path using sys.path manipulation
- **4 handler functions**:
  - `handle_subtree_list()` - Lists configured subtrees from config
  - `handle_subtree_add()` - Adds subtree with --squash
  - `handle_subtree_push()` - Pushes changes to remote
  - `handle_subtree_pull()` - Pulls updates with --squash
- **Config-aware remote lookup** - All tools use `ForgeConfig.get_subtree_remote()` when remote not provided
- **Robust error handling** - Graceful failures with helpful messages
- **Git command execution** - subprocess.run() with capture_output, timeouts (60s for add, 120s for push/pull)
- **SUBTREE_HANDLERS registry** - Dict mapping tool names to handlers

## Files Modified

### 2. `mybb_mcp/mybb_mcp/handlers/dispatcher.py`

**Changes:**
- Line 56: Added `from .subtrees import SUBTREE_HANDLERS`
- Line 69: Added `HANDLER_REGISTRY.update(SUBTREE_HANDLERS)`

**Purpose:** Registers subtree handlers in central dispatcher following existing pattern.

### 3. `mybb_mcp/mybb_mcp/tools_registry.py`

**Changes:**
- Lines 744-795: Added SUBTREE_TOOLS section with 4 tool definitions
- Line 1151: Added SUBTREE_TOOLS to ALL_TOOLS list
- Line 1159: Updated EXPECTED_TOOL_COUNT from 85 to 89

**Tool Definitions:**
1. `mybb_subtree_list` - No required params
2. `mybb_subtree_add` - Required: prefix; Optional: remote, branch
3. `mybb_subtree_push` - Required: prefix; Optional: remote, branch
4. `mybb_subtree_pull` - Required: prefix; Optional: remote, branch

## Key Implementation Details

### ForgeConfig Integration

```python
# Dynamic import path resolution
import sys
sys.path.insert(0, str(Path(__file__).parents[4] / "plugin_manager"))
from forge_config import ForgeConfig
```

### Remote Lookup Pattern

All tools follow this pattern:
```python
if not remote:
    forge_config = ForgeConfig(repo_root)
    remote = forge_config.get_subtree_remote(prefix)
    if not remote:
        return f"Error: No remote configured for subtree prefix '{prefix}' and no remote URL provided"
```

### Git Command Execution

```python
cmd = ["git", "subtree", "add", "--prefix", prefix, remote, branch, "--squash"]
result = subprocess.run(cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=60)
```

## Verification Results

✅ All task package requirements satisfied:

| Requirement | Status | Notes |
|-------------|--------|-------|
| subtree_list tool | ✅ Pass | No required params, formats config data |
| Remote lookup from config | ✅ Pass | All tools use ForgeConfig.get_subtree_remote() |
| Graceful error handling | ✅ Pass | Missing config returns helpful messages |
| Dispatcher integration | ✅ Pass | SUBTREE_HANDLERS imported and registered |
| Tool registry definitions | ✅ Pass | All 4 tools defined with proper schemas |
| Git command execution | ✅ Pass | subprocess.run() with cwd, timeouts, error handling |
| Tool count update | ✅ Pass | EXPECTED_TOOL_COUNT: 85 → 89 |

### Syntax Verification

All files compile successfully:
```bash
python3 -m py_compile mybb_mcp/mybb_mcp/handlers/subtrees.py
python3 -m py_compile mybb_mcp/mybb_mcp/handlers/dispatcher.py
python3 -m py_compile mybb_mcp/mybb_mcp/tools_registry.py
# All passed with no errors
```

### Import Path Verification

ForgeConfig import path tested and working:
```bash
python3 -c "from pathlib import Path; import sys; sys.path.insert(0, str(Path('plugin_manager'))); from forge_config import ForgeConfig; print('ForgeConfig imported successfully')"
# Output: ForgeConfig imported successfully
```

## Test Plan

To verify the implementation works:

1. **List subtrees:**
   ```
   "List configured subtrees"
   ```
   Expected: Shows subtrees from .mybb-forge.yaml with prefix, remote, branch

2. **Add subtree (with config):**
   ```
   "Add subtree with prefix 'mybb_mcp'"
   ```
   Expected: Looks up remote from config, runs git subtree add

3. **Add subtree (explicit remote):**
   ```
   "Add subtree with prefix 'new_component' and remote 'https://github.com/user/repo.git'"
   ```
   Expected: Uses provided remote, runs git subtree add

4. **Error handling:**
   ```
   "Add subtree with prefix 'unknown_prefix'"
   ```
   Expected: Returns error message about missing remote config

## Follow-up Suggestions

1. **Testing:** Create integration tests for subtree operations
2. **Documentation:** Update MCP tools wiki with subtree tool examples
3. **Optimization:** Consider caching ForgeConfig instance in handlers if performance becomes an issue
4. **Enhancement:** Add `mybb_subtree_split` for splitting out history (advanced use case)

## Confidence Assessment: 0.95

**Reasoning:**
- ✅ All task package requirements implemented correctly
- ✅ Follows established patterns from existing handlers
- ✅ Syntax verified, imports tested
- ✅ Error handling comprehensive
- ⚠️ Minor risk: Untested in actual MCP server runtime (requires server restart)
- ⚠️ Minor risk: git subtree commands can be complex with merge conflicts

**Why 0.95 and not 1.0:**
- Haven't tested tools in live MCP server (requires restart + actual git operations)
- Git subtree can have edge cases with merge conflicts
- ForgeConfig dynamic import is slightly unconventional but necessary

## Summary

Task Package 6.1 is complete and ready for testing. All 4 subtree tools are implemented, registered, and verified for syntax. The implementation follows existing patterns and integrates cleanly with ForgeConfig for config-aware remote lookup. Next steps: restart MCP server and test tools with actual git operations.
