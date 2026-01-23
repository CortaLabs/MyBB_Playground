# MCP Bridge Changelog

All notable changes to the MCP Bridge are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and [Semantic Versioning](https://semver.org/).

---

## [1.3.0] - 2026-01-23

### Added
- **Version compatibility checking** - Bridge now reports MyBB version compatibility
- `mybb_compat` field in info response with min/max/tested versions and warnings
- `MCP_BRIDGE_MYBB_COMPAT` constant for version tracking
- **MyBB API compliance** for user:ban, user:unban, forum:delete
  - `admin_user_banning_start_commit` hook in user:ban
  - `admin_user_banning_lift_commit` hook in user:unban
  - `admin_forum_management_delete_commit` hook in forum:delete
  - `log_admin_action()` calls for all three operations
- `force_content_deletion` parameter for forum:delete
  - Uses MyBB's Moderation class for proper thread/post deletion
  - Batch deletion (50 at a time) matching MyBB core pattern

### Changed
- user:ban no longer calls `$cache->update_moderators()` (matches MyBB behavior)
- user:unban operation order fixed: delete banned record BEFORE updating users
- Bumped version to 1.3.0

### Compatibility
- **MyBB:** 1.8.39 (only tested version)
- **PHP:** 8.0+

---

## [1.2.0] - 2026-01-23

### Added
- **Bridge health check** (`bridge:health_check` action)
  - Quick mode: read-only verification of all subsystems
  - Full mode: write tests using proper MyBB APIs (PostDataHandler, Moderation class)
  - Returns structured health report with pass/fail for each subsystem
- `mybb_bridge_health_check` MCP tool

### Changed
- Bumped version to 1.2.0

---

## [1.1.0] - 2026-01-23

### Added
- `setting:set` action with `rebuild_settings()` cache invalidation
- `task:enable` action with `$cache->update_tasks()`
- `task:disable` action with `$cache->update_tasks()`
- `task:update_nextrun` action with `$cache->update_tasks()`
- `forum:delete` action with proper cache invalidation (4 caches)
  - Safety check prevents deletion of forums with content
  - Cleans up 5 related tables (moderators, subscriptions, permissions, etc.)

### Changed
- All task mutations now go through bridge instead of direct DB
- Bumped version to 1.1.0

---

## [1.0.0] - 2026-01-21

### Added
- Initial release with bridge hardening complete
- **Template operations**
  - `template:write` with cache invalidation
  - `template:find_replace` for plugin-style modifications
  - `template:batch_write` for bulk operations
- **Stylesheet operations**
  - `stylesheet:write` with cache refresh
- **Plugin lifecycle**
  - `plugin:status`, `plugin:activate`, `plugin:deactivate`, `plugin:list`
- **Content operations**
  - `forum:create`, `forum:update`
  - `thread:create`, `thread:edit`, `thread:delete`, `thread:move`
  - `post:create`, `post:edit`, `post:delete`
- **User operations**
  - `user:update_group`, `user:ban`, `user:unban`
- **Moderation operations**
  - `mod:close_thread`, `mod:stick_thread`
  - `mod:approve_thread`, `mod:approve_post`
  - `mod:soft_delete_thread`, `mod:restore_thread`
  - `mod:soft_delete_post`, `mod:restore_post`
  - `modlog:add`
- **Cache operations**
  - `cache:read`, `cache:rebuild`, `cache:rebuild_smilies`
- **Info**
  - `info` action with version, supported actions, MyBB details

### Compatibility
- **MyBB:** 1.8.39 (only tested version)
- **PHP:** 8.0+

---

## Version Archive

When upgrading MyBB, check if your bridge version is compatible:

| Bridge Version | MyBB Tested | Notes |
|----------------|-------------|-------|
| 1.3.0 | 1.8.39 | API compliance, version checking |
| 1.2.0 | 1.8.39 | Health check |
| 1.1.0 | 1.8.39 | Settings, tasks, forum delete |
| 1.0.0 | 1.8.39 | Initial hardened release |

**Note:** Each bridge version is only tested on the listed MyBB version. Other versions may work but are not guaranteed.

### Archived Versions

Tagged releases are available for older MyBB installations:

```bash
# Get specific bridge version
git checkout bridge-v1.3.0 -- install_files/mcp_bridge.php

# List all bridge versions
git tag -l "bridge-v*"
```

---

## Upgrade Guide

### From 1.2.x to 1.3.0

1. Copy `install_files/mcp_bridge.php` to `TestForum/mcp_bridge.php`
2. No MCP server changes required
3. New features available immediately

### From 1.1.x to 1.2.0

1. Copy `install_files/mcp_bridge.php` to `TestForum/mcp_bridge.php`
2. Restart MCP server to get `mybb_bridge_health_check` tool

### From 1.0.x to 1.1.0

1. Copy `install_files/mcp_bridge.php` to `TestForum/mcp_bridge.php`
2. Restart MCP server to get new setting/task tools
