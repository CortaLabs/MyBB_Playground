# Lifecycle Management

**Module:** `plugin_manager/lifecycle.py` (283 lines)
**Classes:** `BridgeResult`, `PluginLifecycle`
**PHP Bridge:** `TestForum/mcp_bridge.php` (486 lines)

## Overview

The lifecycle management system executes MyBB plugin lifecycle functions (_install, _activate, _deactivate, _uninstall) via a PHP bridge. This provides full compatibility with MyBB's plugin system while maintaining Python-based orchestration.

## PHP Bridge Architecture

### Bootstrap Sequence

The MCP Bridge bootstraps MyBB without HTTP overhead:

```
1. Security check: php_sapi_name() == 'cli' (line 26)
2. Parse CLI args: getopt() for --action, --plugin, --json, etc. (lines 34-42)
3. chdir(__DIR__) to MyBB root (line 127)
4. Define IN_MYBB=1, NO_PLUGINS=1 (lines 130-135)
5. ob_start() capture output (line 138)
6. require_once inc/init.php (line 142)
7. ob_end_clean() suppress bootstrap output (line 149)
8. Verify $mybb, $db, $cache globals exist (lines 152-154)
9. Route action via switch statement (lines 159-488)
```

**Security:**
- **CLI-only enforcement:** `php_sapi_name()` check at entry (line 26)
- **HTTP 403 response** if accessed via web
- `.htaccess` blocks HTTP access as additional layer

**NO_PLUGINS Constant:** Prevents plugin hooks from firing during CLI operations (avoids side effects).

### Response Format

All actions return consistent JSON structure via `respond()` function (lines 93-121):

```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:00+00:00",
  "data": { /* action-specific data */ },
  "error": null
}
```

**Exit Codes:**
- `0` — Success
- `1` — Failure

**JSON Flags:** `JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES`

## Available Actions (7 Total)

### 1. plugin:status

**Purpose:** Get status and info for a single plugin

**CLI Signature:**
```bash
php mcp_bridge.php --action=plugin:status --plugin=<codename> --json
```

**Required Parameters:**
- `--plugin=<codename>` — Plugin codename (alphanumeric + underscore)

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:00+00:00",
  "data": {
    "codename": "hello_world",
    "info": {
      "name": "Hello World",
      "version": "1.0.0",
      "author": "Developer",
      "compatibility": "18*"
    },
    "is_installed": true,
    "is_active": true,
    "is_compatible": true,
    "has_install": false,
    "has_uninstall": false,
    "has_activate": true,
    "has_deactivate": true,
    "file_path": "/path/to/TestForum/inc/plugins/hello_world.php"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": "Plugin file not found: hello_world.php",
  "timestamp": "2026-01-18T08:10:00+00:00",
  "data": {}
}
```

---

### 2. plugin:activate

**Purpose:** Install (if needed) and activate a plugin

**CLI Signature:**
```bash
php mcp_bridge.php --action=plugin:activate --plugin=<codename> [--force] --json
```

**Required Parameters:**
- `--plugin=<codename>` — Plugin codename

**Optional Parameters:**
- `--force` — Skip compatibility check (boolean flag)

**Behavior:**
1. Check compatibility (unless --force) — compares plugin's compatibility string with $mybb->version
2. Run _install() if plugin not installed and function exists
3. Run _activate() if function exists
4. Update plugins cache

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:05+00:00",
  "data": {
    "codename": "hello_world",
    "actions_taken": ["installed", "activated", "cache_updated"],
    "info": { /* plugin info from _info() */ }
  }
}
```

**Error Conditions:**
- Plugin file not found
- Missing _info() function
- Incompatible with MyBB version (unless --force)
- Exception in _install() or _activate()

---

### 3. plugin:deactivate

**Purpose:** Deactivate a plugin (optionally uninstall)

**CLI Signature:**
```bash
php mcp_bridge.php --action=plugin:deactivate --plugin=<codename> [--uninstall] --json
```

**Required Parameters:**
- `--plugin=<codename>` — Plugin codename

**Optional Parameters:**
- `--uninstall` — Also run _uninstall() function (boolean flag)

**Behavior:**
1. Run _deactivate() if function exists
2. Run _uninstall() if --uninstall and function exists
3. Update plugins cache (remove from active)

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:10+00:00",
  "data": {
    "codename": "hello_world",
    "actions_taken": ["deactivated", "cache_updated"],
    "uninstalled": false
  }
}
```

**Note:** If plugin not in cache, deactivate still succeeds (idempotent operation).

---

### 4. plugin:list

**Purpose:** List all plugins with status

**CLI Signature:**
```bash
php mcp_bridge.php --action=plugin:list --json
```

**No Parameters Required**

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:15+00:00",
  "data": {
    "plugins": [
      {
        "codename": "hello_world",
        "file": "hello_world.php",
        "is_active": true,
        "name": "Hello World",
        "version": "1.0.0",
        "author": "Developer",
        "compatibility": "18*",
        "is_compatible": true,
        "is_installed": true
      }
    ],
    "count": 1,
    "active_count": 1
  }
}
```

**Behavior:** Scans `inc/plugins/` directory (except index.php and hello.php), loads each, calls _info()

---

### 5. cache:read

**Purpose:** Read a MyBB cache entry

**CLI Signature:**
```bash
php mcp_bridge.php --action=cache:read --cache=<name> --json
```

**Required Parameters:**
- `--cache=<name>` — Cache name (e.g., "plugins", "settings")

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:20+00:00",
  "data": {
    "cache_name": "plugins",
    "content": { /* cache content */ }
  }
}
```

---

### 6. cache:rebuild

**Purpose:** Rebuild all MyBB caches

**CLI Signature:**
```bash
php mcp_bridge.php --action=cache:rebuild --json
```

**No Parameters Required**

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:25+00:00",
  "data": {
    "message": "All caches rebuilt successfully"
  }
}
```

**Behavior:** Calls `$cache->update()` for all standard MyBB caches.

---

### 7. info

**Purpose:** Get MyBB installation info

**CLI Signature:**
```bash
php mcp_bridge.php --action=info --json
```

**No Parameters Required**

**Response (success):**
```json
{
  "success": true,
  "timestamp": "2026-01-18T08:10:30+00:00",
  "data": {
    "version": "1.8.38",
    "version_code": 1838,
    "php_version": "8.0.30",
    "mybb_root": "/path/to/TestForum"
  }
}
```

---

## BridgeResult Dataclass

### Definition

```python
from dataclasses import dataclass, field
from typing import Dict, Any, Optional

@dataclass
class BridgeResult:
    """Result from a bridge operation."""
    success: bool
    action: str
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    timestamp: Optional[str] = None
```

### Factory Methods

#### from_json()

```python
@classmethod
def from_json(cls, action: str, json_data: Dict[str, Any]) -> 'BridgeResult':
    """Create BridgeResult from JSON response.

    Args:
        action: Action name
        json_data: Parsed JSON response from bridge

    Returns:
        BridgeResult instance
    """
```

**Usage:**
```python
json_response = {"success": True, "data": {...}, "timestamp": "..."}
result = BridgeResult.from_json("plugin:status", json_response)
```

#### from_error()

```python
@classmethod
def from_error(cls, action: str, error: str) -> 'BridgeResult':
    """Create error BridgeResult.

    Args:
        action: Action name
        error: Error message

    Returns:
        BridgeResult with success=False
    """
```

**Usage:**
```python
result = BridgeResult.from_error("plugin:activate", "Timeout exceeded")
```

---

## PluginLifecycle Class

### Initialization

```python
from plugin_manager.lifecycle import PluginLifecycle

lifecycle = PluginLifecycle(
    mybb_root: Path,
    php_binary: str = "php",
    timeout: int = 30
)
```

**Parameters:**
- `mybb_root` — Path to MyBB installation (TestForum)
- `php_binary` — PHP CLI executable (default: "php")
- `timeout` — Subprocess timeout in seconds (default: 30)

**Bridge Location:** `{mybb_root}/mcp_bridge.php`

**Validation:** Raises `FileNotFoundError` if bridge not found.

### Core Methods

#### get_status()

```python
def get_status(self, codename: str) -> BridgeResult:
    """Get plugin status and info.

    Args:
        codename: Plugin codename

    Returns:
        BridgeResult with status data
    """
```

**Returns Data:**
- `is_installed` — Whether _is_installed() returns true
- `is_active` — Whether plugin is in active cache
- `is_compatible` — Whether compatible with MyBB version
- `info` — Plugin info from _info() function

**Example:**
```python
result = lifecycle.get_status("hello_world")
if result.success:
    print(f"Active: {result.data['is_active']}")
```

---

#### activate()

```python
def activate(self, codename: str, force: bool = False) -> BridgeResult:
    """Activate a plugin (runs _install and _activate if needed).

    Args:
        codename: Plugin codename
        force: Skip compatibility check

    Returns:
        BridgeResult with activation data
    """
```

**Steps:**
1. Check compatibility (unless force=True)
2. Run _install() if not installed
3. Run _activate()
4. Update plugins cache

**Example:**
```python
result = lifecycle.activate("my_plugin")
if result.success:
    print(f"Actions: {result.data['actions_taken']}")
else:
    print(f"Error: {result.error}")
```

---

#### deactivate()

```python
def deactivate(self, codename: str, uninstall: bool = False) -> BridgeResult:
    """Deactivate a plugin (optionally uninstall).

    Args:
        codename: Plugin codename
        uninstall: Also run _uninstall()

    Returns:
        BridgeResult with deactivation data
    """
```

**Steps:**
1. Run _deactivate()
2. Run _uninstall() if uninstall=True
3. Update plugins cache

**Example:**
```python
# Deactivate only
result = lifecycle.deactivate("my_plugin")

# Deactivate and uninstall
result = lifecycle.deactivate("my_plugin", uninstall=True)
```

---

#### list_plugins()

```python
def list_plugins(self) -> BridgeResult:
    """List all plugins with their status.

    Returns:
        BridgeResult with plugins list
    """
```

**Returns Data:**
- `plugins` — List of plugin info dictionaries
- `count` — Total plugin count
- `active_count` — Active plugin count

---

#### get_mybb_info()

```python
def get_mybb_info(self) -> BridgeResult:
    """Get MyBB installation info.

    Returns:
        BridgeResult with MyBB version and environment info
    """
```

---

#### read_cache()

```python
def read_cache(self, cache_name: str) -> BridgeResult:
    """Read a MyBB cache entry.

    Args:
        cache_name: Cache name (e.g., "plugins", "settings")

    Returns:
        BridgeResult with cache content
    """
```

**Example:**
```python
result = lifecycle.read_cache("plugins")
if result.success:
    active_plugins = result.data["content"]
```

---

#### rebuild_cache()

```python
def rebuild_cache(self) -> BridgeResult:
    """Rebuild all MyBB caches.

    Returns:
        BridgeResult with success status
    """
```

---

### Private Method

#### _call_bridge()

```python
def _call_bridge(self, action: str, **kwargs) -> BridgeResult:
    """Execute a bridge action via subprocess.

    Args:
        action: Action name (e.g., "plugin:status")
        **kwargs: Additional CLI arguments

    Returns:
        BridgeResult from bridge response
    """
```

**Command Format:**
```bash
php {bridge_path} --action={action} --json [--key=value ...]
```

**Error Handling:**
- `subprocess.TimeoutExpired` → timeout error BridgeResult
- `json.JSONDecodeError` → returns raw output as error
- `FileNotFoundError` → PHP binary not found error

**Subprocess Configuration:**
- `cwd=mybb_root` — Execute in MyBB directory
- `capture_output=True` — Capture stdout/stderr
- `timeout=self.timeout` — Configurable timeout

---

## Convenience Functions

### activate_plugin()

```python
from plugin_manager.lifecycle import activate_plugin

result = activate_plugin(
    mybb_root: Path,
    codename: str,
    force: bool = False,
    php_binary: str = "php"
) -> BridgeResult
```

**One-shot activation** without creating PluginLifecycle instance.

### deactivate_plugin()

```python
from plugin_manager.lifecycle import deactivate_plugin

result = deactivate_plugin(
    mybb_root: Path,
    codename: str,
    uninstall: bool = False,
    php_binary: str = "php"
) -> BridgeResult
```

**One-shot deactivation** without creating PluginLifecycle instance.

---

## Full Lifecycle Workflows

### activate_full Workflow (PluginManager)

```python
from plugin_manager import PluginManager

pm = PluginManager()

# Full activation: deploy files + PHP lifecycle
result = pm.activate_full("my_plugin", force=False)
```

**Steps:**
1. Check if plugin already installed (skip deployment if yes)
2. Deploy files via `install_plugin()` (if not installed)
3. Run PHP lifecycle via `lifecycle.activate()`
4. Update project status in database
5. Create history entry

**Returns:** `BridgeResult` from activation

### deactivate_full Workflow (PluginManager)

```python
# Full deactivation: PHP lifecycle + remove files
result = pm.deactivate_full("my_plugin", uninstall=True)
```

**Steps:**
1. Run PHP lifecycle via `lifecycle.deactivate(uninstall=True)`
2. Remove files via `uninstall_plugin()` (if uninstall=True)
3. Update project status in database
4. Create history entry

**Returns:** `BridgeResult` from deactivation

---

## Error Handling

### Common Errors

**TimeoutError:**
```python
result = lifecycle.activate("slow_plugin")
if not result.success and "timeout" in result.error.lower():
    print("Plugin _install() took too long")
```

**Compatibility Error:**
```python
result = lifecycle.activate("old_plugin")
if not result.success and "incompatible" in result.error.lower():
    # Retry with force=True
    result = lifecycle.activate("old_plugin", force=True)
```

**PHP Binary Not Found:**
```python
try:
    lifecycle = PluginLifecycle(mybb_root, php_binary="/usr/bin/php8.0")
except FileNotFoundError as e:
    print(f"PHP not found: {e}")
```

### Error Response Handling

```python
result = lifecycle.activate("my_plugin")

if result.success:
    print(f"Success: {result.data}")
else:
    print(f"Failed: {result.error}")
    print(f"Timestamp: {result.timestamp}")
```

---

## Security Considerations

### CLI-Only Enforcement

**PHP Bridge:**
```php
// Line 26-29
if (php_sapi_name() !== 'cli') {
    http_response_code(403);
    die("Forbidden: This script can only be run via CLI.");
}
```

**.htaccess Protection:**
```apache
# Deny HTTP access to mcp_bridge.php
<Files "mcp_bridge.php">
    Require all denied
</Files>
```

### Input Sanitization

**Codename Sanitization:**
```php
// Line 36
$plugin = preg_replace('/[^a-zA-Z0-9_]/', '', $options['plugin'] ?? '');
```

**Prevents:**
- Path traversal attacks
- Code injection via codename parameter
- Special character exploits

---

## Best Practices

### Lifecycle Operations

✅ **DO:**
- Use PluginManager.activate_full() for complete workflow
- Check result.success before proceeding
- Handle timeout errors gracefully
- Use force=True only when necessary

❌ **DON'T:**
- Call PHP lifecycle before deploying files
- Ignore result.error messages
- Hardcode timeouts (use configurable values)
- Skip compatibility checks in production

### Error Handling

✅ **DO:**
- Always check BridgeResult.success
- Log errors with result.timestamp
- Provide fallback for timeout errors
- Validate codename before calling bridge

❌ **DON'T:**
- Assume operations succeed
- Ignore result.data (contains important info)
- Retry failed operations without delay
- Suppress bridge errors

### Security

✅ **DO:**
- Verify .htaccess blocks HTTP access
- Sanitize all user input
- Use configurable PHP binary path
- Check bridge file permissions

❌ **DON'T:**
- Allow HTTP access to bridge
- Trust user-provided codenames
- Hardcode PHP binary path
- Expose bridge output to web

---

## Related Documentation

- [Deployment System](deployment.md) — File deployment before lifecycle
- [Database Schema](database.md) — Status tracking after lifecycle operations
- [Plugin Manager Index](index.md) — System overview
- [Workspace Management](workspace.md) — Pre-deployment workspace structure
