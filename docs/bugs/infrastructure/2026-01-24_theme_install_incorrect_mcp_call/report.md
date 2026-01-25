
# 🐞 Theme installer calls MCP tools as module functions instead of using DB methods — theme-management-system
**Author:** Scribe
**Version:** v0.1
**Status:** Fixed
**Last Updated:** 2026-01-24 08:23:27 UTC

> Summarise why this document exists and what decisions it captures.

---
## Bug Overview
<!-- ID: bug_overview -->
**Bug ID:** theme_install_incorrect_mcp_call

**Reported By:** Scribe

**Date Reported:** 2026-01-24 08:23:27 UTC

**Severity:** HIGH

**Status:** FIXED

**Component:** plugin_manager/installer.py ThemeInstaller

**Environment:** [local/staging/production]

**Customer Impact:** [Describe impact or 'None']


---
## Description
<!-- ID: description -->
### Summary
Theme installation via `mybb_theme_install(codename="flavor")` fails with `AttributeError: module 'mybb_mcp' has no attribute 'mybb_list_stylesheets'`. The installer attempts to import MCP tools as module functions, which is architecturally incorrect.

### Expected Behaviour
`mybb_theme_install()` should deploy all stylesheets from workspace to MyBB database by calling DB methods through proper dependency injection.

### Actual Behaviour
Installation fails with AttributeError during stylesheet deployment. Theme record is created but 0 stylesheets are deployed.

### Steps to Reproduce
1. Run `mybb_theme_install(codename="flavor")`
2. Observe error: `Stylesheet deployment failed: module 'mybb_mcp' has no attribute 'mybb_list_stylesheets'`
3. Check result shows `stylesheets_deployed: 0`


---
## Investigation
<!-- ID: investigation -->
**Root Cause Analysis:**
The `ThemeInstaller.install_theme()` method in `plugin_manager/installer.py` (lines 725-742) was attempting to import and call MCP tools as module functions:

```python
import mybb_mcp
existing_stylesheets = mybb_mcp.mybb_list_stylesheets(tid=tid)
mybb_mcp.mybb_write_stylesheet(sid=sid, stylesheet=css_content)
```

This is architecturally incorrect because MCP tools are handlers dispatched through the MCP server, not importable Python module functions. The `mybb_mcp` package does not export these functions as module attributes.

**Affected Areas:**
- `plugin_manager/installer.py` - ThemeInstaller.install_theme() method
- `plugin_manager/manager.py` - PluginManager.install_theme() method
- `mybb_mcp/mybb_mcp/handlers/themes.py` - handle_theme_install() handler

**Related Issues:**
- Similar pattern may exist in other installers (verified: PluginInstaller does NOT have this issue)


---
## Resolution Plan
<!-- ID: resolution_plan -->
### Immediate Actions
- [x] Pass MyBBDatabase instance from handler → manager → installer
- [x] Replace `mybb_mcp.mybb_list_stylesheets()` with `self.mybb_db.list_stylesheets()`
- [x] Replace `mybb_mcp.mybb_write_stylesheet()` with `self.mybb_db.update_stylesheet()`

### Long-Term Fixes
- [ ] Code review to ensure no other installers use this anti-pattern
- [ ] Add linting/static analysis rule to prevent `import mybb_mcp` in non-handler code

### Testing Strategy
- [x] Manual test: Run `mybb_theme_install(codename="flavor")`
- [ ] Verify stylesheets deployed count matches expected (5 CSS files)
- [ ] Integration test: Full theme install/uninstall cycle
- [ ] Regression test: Ensure other theme operations still work


---
## Timeline & Ownership
<!-- ID: timeline -->
| Phase | Owner | Target Date | Notes |
| --- | --- | --- | --- |
| Investigation | [Name] | [Date] | [Details] |
| Fix Development | [Name] | [Date] | [Details] |
| Testing | [Name] | [Date] | [Details] |
| Deployment | [Name] | [Date] | [Details] |


---
## Appendix
<!-- ID: appendix -->

### Fix Implementation

**Files Modified:**

1. **mybb_mcp/mybb_mcp/handlers/themes.py** (line 393)
   - Changed: Updated docstring to remove "(unused)" for db parameter
   - Changed: Pass db to manager: `manager.install_theme(codename, visibility, mybb_db=db)`

2. **plugin_manager/manager.py** (lines 1138-1149)
   - Added: `mybb_db: Optional[Any] = None` parameter to `install_theme()`
   - Changed: Pass mybb_db to ThemeInstaller: `ThemeInstaller(self.config, self.db, self.theme_workspace, mybb_db=mybb_db)`

3. **plugin_manager/installer.py** (lines 659-690, 736-763)
   - Added: `mybb_db: Optional[Any] = None` parameter to `__init__()`
   - Added: Fallback MyBBDatabase creation if not provided
   - Removed: `import mybb_mcp` (line 725)
   - Changed: `mybb_mcp.mybb_list_stylesheets(tid=tid)` → `self.mybb_db.list_stylesheets(tid=tid)`
   - Changed: `mybb_mcp.mybb_write_stylesheet(sid=sid, stylesheet=css_content)` → `self.mybb_db.update_stylesheet(sid=sid, stylesheet=css_content)`

**Code Diff:**

```diff
# handlers/themes.py
-        db: MyBBDatabase instance (unused)
+        db: MyBBDatabase instance
-        result = manager.install_theme(codename, visibility)
+        result = manager.install_theme(codename, visibility, mybb_db=db)

# manager.py
-    def install_theme(self, codename: str, visibility: Optional[str] = None) -> Dict[str, Any]:
+    def install_theme(self, codename: str, visibility: Optional[str] = None, mybb_db: Optional[Any] = None) -> Dict[str, Any]:
-        installer = ThemeInstaller(self.config, self.db, self.theme_workspace)
+        installer = ThemeInstaller(self.config, self.db, self.theme_workspace, mybb_db=mybb_db)

# installer.py __init__
     def __init__(
         self,
         config: Config,
         db: ProjectDatabase,
         theme_workspace: ThemeWorkspace,
+        mybb_db: Optional[Any] = None
     ):
+        # Initialize MyBB database if not provided
+        if mybb_db is None:
+            from mybb_mcp.db import MyBBDatabase
+            self.mybb_db = MyBBDatabase({...})
+        else:
+            self.mybb_db = mybb_db

# installer.py install_theme
-                import mybb_mcp
-                existing_stylesheets = mybb_mcp.mybb_list_stylesheets(tid=tid)
+                existing_stylesheets = self.mybb_db.list_stylesheets(tid=tid)
-                        mybb_mcp.mybb_write_stylesheet(sid=sid, stylesheet=css_content)
+                        self.mybb_db.update_stylesheet(sid=sid, stylesheet=css_content)
```

**Why This Fix Works:**
- The MCP handler already has access to `MyBBDatabase` instance
- Passing it through the call chain follows proper dependency injection pattern
- Installer can call DB methods directly without importing mybb_mcp module
- Fallback creation ensures backward compatibility for direct PluginManager usage

**Verification:**
- Bug ID: theme_install_stylesheet_deploy
- Scribe Project: theme-management-system
- Confidence: 98%

**Open Questions:**
- Should we add a type hint import for MyBBDatabase? (Currently using Optional[Any])
- Should uninstall_theme also receive mybb_db parameter for consistency?


---