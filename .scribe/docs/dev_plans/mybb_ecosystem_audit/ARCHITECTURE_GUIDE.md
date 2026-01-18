# Architecture Guide - MyBB Ecosystem Enhancement
**Author:** ArchitectAgent
**Version:** v1.0
**Status:** Approved
**Last Updated:** 2026-01-17 14:25 UTC

> Comprehensive architecture for MyBB MCP server security remediation and feature expansion based on 8 research audits covering hooks, templates, plugins, security, database schema, admin CP, VSCode integration, and strategic roadmap.

---

## 1. Problem Statement
<!-- ID: problem_statement -->

**Context:** The MyBB MCP (Model Context Protocol) server provides AI-assisted development tools for MyBB forum customization. Eight comprehensive research audits have identified significant gaps and security issues requiring systematic remediation and enhancement.

**Current State:**
- 20 MCP tools across templates, themes, plugins, and database query
- 2 CRITICAL security vulnerabilities (asyncio threading, empty password default)
- 3 HIGH priority issues (no connection pooling, generic exceptions, static hooks)
- MCP covers only 7% of MyBB database tables (5/75)
- Static hook catalog contains ~60 hooks vs 200-400+ in actual MyBB codebase
- Plugin creator missing critical patterns (rebuild_settings, multi-DB, security boilerplate)
- Template tools lacking find_replace_templatesets() - most common plugin operation

**Goals:**
1. Remediate 2 CRITICAL security vulnerabilities before any expansion work
2. Enhance plugin creator with all required MyBB patterns
3. Expand template tools with find_replace_templatesets() and batch operations
4. Implement dynamic hook discovery to replace static catalog
5. Expand MCP coverage to 50%+ of MyBB database tables
6. Add 52+ new tools across content, user, admin, and moderation categories

**Non-Goals:**
- Full MyBB admin panel replacement (MCP augments, not replaces)
- User-facing forum features (development tools only)
- MyBB version upgrades or migrations

**Success Criteria:**
- Zero critical/high security vulnerabilities
- Plugin creator generates production-ready plugins (all 10 patterns from research)
- Template tools support full plugin development workflow (7 identified gaps addressed)
- Hook catalog 95%+ coverage of actual MyBB hooks
- Content management tools enable AI-assisted forum development

---

## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->

### Functional Requirements

**Security (BLOCKING - Must Complete First):**
- FR-SEC-1: Fix asyncio threading anti-pattern in file watcher (watcher.py:150,180,189)
- FR-SEC-2: Require explicit database password (config.py:45)
- FR-SEC-3: Add database connection pooling
- FR-SEC-4: Improve error handling with structured error types

**Plugin Creator Enhancement:**
- FR-PLG-1: Add rebuild_settings() calls in activate/uninstall
- FR-PLG-2: Generate multi-DB support (MySQL, PostgreSQL, SQLite switch statements)
- FR-PLG-3: Add security boilerplate (IN_MYBB check, CSRF protection, input validation)
- FR-PLG-4: Add template caching pattern ($templatelist)
- FR-PLG-5: Support find_replace_templatesets() for template modification
- FR-PLG-6: Generate task file structure when requested
- FR-PLG-7: Add hook priority support

**Template Tool Enhancement:**
- FR-TPL-1: Implement find_replace_templatesets() wrapper (CRITICAL - most common operation)
- FR-TPL-2: Add batch template operations (bulk read/write)
- FR-TPL-3: Add template diff/merge tools
- FR-TPL-4: Add outdated template detection
- FR-TPL-5: Add template validation

**Hook System Enhancement:**
- FR-HKS-1: Implement dynamic hook discovery from MyBB codebase
- FR-HKS-2: Add hook documentation with argument patterns
- FR-HKS-3: Add missing categories (parser, moderation class, core functions, editpost)

**Content Management Expansion:**
- FR-CNT-1: Posts CRUD (list, read, create, update)
- FR-CNT-2: Threads CRUD (list, read, create, update)
- FR-CNT-3: Forums CRUD (list, read, create, update, delete)
- FR-CNT-4: Search functionality (posts, threads, users)

**Admin Operations Expansion:**
- FR-ADM-1: Settings management (groups, individual settings)
- FR-ADM-2: Plugin lifecycle (activate, deactivate, install, uninstall)
- FR-ADM-3: Cache management (list, rebuild, rebuild_all)
- FR-ADM-4: Database backup (create, list, download)
- FR-ADM-5: Scheduled tasks (CRUD, run)

### Non-Functional Requirements

- NFR-1: API response times < 100ms for read, < 500ms for write operations
- NFR-2: Zero SQL injection vulnerabilities (maintain parameterized queries)
- NFR-3: 100% audit logging for write operations
- NFR-4: Backward compatibility with existing MCP tools
- NFR-5: Support MyBB 1.8.x (all minor versions)

### Constraints

- MUST use MyBB datahandlers for content/user operations (security critical)
- MUST respect MyBB permission system for all operations
- MUST trigger MyBB hooks for plugin compatibility
- Security fixes BLOCK all expansion work - sequential dependency
- No changes to MyBB core files
- MCP server runs as separate process, communicates via stdio

### Assumptions

- MyBB 1.8.x installation accessible via database
- Python 3.10+ runtime available
- Network access to MyBB server for cache refresh
- Developer has appropriate MyBB admin credentials

---

## 3. Architecture Overview
<!-- ID: architecture_overview -->

### Solution Summary

The MyBB MCP Enhancement architecture follows a layered approach with clear separation of concerns:

```
+-------------------------------------------------------------------+
|                        MCP Client (Claude, etc.)                   |
+-------------------------------------------------------------------+
                                   |
                                   v
+-------------------------------------------------------------------+
|                          MCP Server Layer                          |
|  +-------------------+  +-------------------+  +-----------------+ |
|  | Tool Registry     |  | Error Handler     |  | Logging         | |
|  | (20 existing +    |  | (structured       |  | (audit trail)   | |
|  |  52+ new tools)   |  |  error types)     |  |                 | |
|  +-------------------+  +-------------------+  +-----------------+ |
+-------------------------------------------------------------------+
                                   |
         +------------------------+------------------------+
         |                        |                        |
         v                        v                        v
+------------------+   +------------------+   +------------------+
| Template Tools   |   | Plugin Tools     |   | Content Tools    |
| (CRUD + batch +  |   | (create + hooks  |   | (posts, threads, |
|  find_replace)   |   |  + lifecycle)    |   |  forums, users)  |
+------------------+   +------------------+   +------------------+
         |                        |                        |
         v                        v                        v
+-------------------------------------------------------------------+
|                       Database Abstraction Layer                   |
|  +------------------+  +------------------+  +------------------+  |
|  | Connection Pool  |  | Query Builder    |  | Transaction Mgr  |  |
|  | (NEW - replace   |  | (parameterized   |  | (context manager |  |
|  |  single conn)    |  |  queries)        |  |  with rollback)  |  |
|  +------------------+  +------------------+  +------------------+  |
+-------------------------------------------------------------------+
         |                        |                        |
         v                        v                        v
+-------------------------------------------------------------------+
|                    MyBB Database (75 tables)                       |
|  templates, themes, plugins, posts, threads, forums, users, etc.  |
+-------------------------------------------------------------------+
```

### Component Breakdown

**1. MCP Server Layer (server.py - 614 lines)**
- Purpose: Tool registration, request routing, error handling
- Interfaces: MCP protocol via stdio
- Enhancement: Add structured error types, tool registry pattern

**2. Database Layer (db/connection.py - 350 lines)**
- Purpose: Database abstraction, query execution, transaction management
- Interfaces: MyBBDatabase class
- Enhancement: Add connection pooling, retry logic, timeouts

**3. Template Tools Module (tools/templates.py - NEW)**
- Purpose: Template CRUD + find_replace_templatesets + batch operations
- Interfaces: Wrap MyBB's adminfunctions_templates.php patterns
- Dependencies: Database layer

**4. Plugin Tools Module (tools/plugins.py - 354 lines)**
- Purpose: Plugin scaffolding, hooks reference, analysis
- Interfaces: create_plugin(), analyze_plugin(), list_hooks()
- Enhancement: Add all 10 MyBB patterns, lifecycle management

**5. Content Tools Module (tools/content.py - NEW)**
- Purpose: Posts, threads, forums, search
- Interfaces: Wrap MyBB datahandlers (post.php, user.php)
- Dependencies: Database layer + MyBB datahandler patterns

**6. Admin Tools Module (tools/admin.py - NEW)**
- Purpose: Settings, cache, backup, tasks
- Interfaces: Wrap admin module patterns
- Dependencies: Database layer

**7. Sync Module (sync/* - 5 files)**
- Purpose: Disk-based template/stylesheet editing with file watcher
- Enhancement: Fix threading issue, add queue-based async bridge

### Data Flow

**Template Edit Flow:**
```
User -> MCP Client -> write_template tool -> Database Layer ->
MyBB templates table -> Cache Refresh (HTTP) -> MyBB frontend updated
```

**Plugin Creation Flow:**
```
User -> MCP Client -> create_plugin tool -> Plugin Generator ->
Filesystem (inc/plugins/) -> Plugin ready for activation
```

**Content Creation Flow (NEW):**
```
User -> MCP Client -> create_thread tool -> PostDataHandler wrapper ->
Validation (all 12+ checks) -> Database insert -> Thread/Post created
```

### External Integrations

- **MyBB Database:** MySQL via mysql-connector-python (upgrade to pooling)
- **MyBB Cache Refresh:** HTTP POST to cachecss.php endpoint
- **Filesystem:** Template/stylesheet sync, plugin file creation
- **File Watcher:** watchdog library for auto-sync (needs threading fix)

---

## 4. Detailed Design
<!-- ID: detailed_design -->

### 4.1 Security Fixes (BLOCKING)

#### 4.1.1 Asyncio Threading Fix

**Problem:** File watcher uses asyncio.run() on non-main thread (watcher.py:150,180,189)

**Solution:** Implement thread-safe queue bridge

```python
# sync/watcher.py - Proposed fix

import queue
import threading

class SyncEventHandler:
    def __init__(self, template_importer, stylesheet_importer):
        self.import_queue = queue.Queue()
        self._worker_loop = None
        self._worker_thread = None
        self._start_worker()

    def _start_worker(self):
        """Start dedicated event loop on worker thread"""
        self._worker_loop = asyncio.new_event_loop()
        self._worker_thread = threading.Thread(
            target=self._run_worker_loop,
            daemon=True
        )
        self._worker_thread.start()

    def _run_worker_loop(self):
        asyncio.set_event_loop(self._worker_loop)
        self._worker_loop.run_forever()

    def _handle_template_change(self, path: Path):
        """Queue template change instead of asyncio.run()"""
        content = path.read_text()
        # Schedule on worker loop instead of asyncio.run()
        asyncio.run_coroutine_threadsafe(
            self.template_importer.import_template(...),
            self._worker_loop
        )
```

**Verification:** Unit test with concurrent file changes, no crashes

#### 4.1.2 Database Password Security

**Problem:** Empty password default allows passwordless connection (config.py:45)

**Solution:** Require explicit password

```python
# config.py - Proposed fix

password = os.getenv("MYBB_DB_PASS")
if not password:
    raise ValueError(
        "MYBB_DB_PASS environment variable is required. "
        "Set it in your .env file or environment."
    )
```

**Verification:** MCP startup fails without password set

#### 4.1.3 Connection Pooling

**Problem:** Single persistent connection, no failover

**Solution:** mysql-connector-python pooling

```python
# db/connection.py - Proposed enhancement

from mysql.connector.pooling import MySQLConnectionPool

class MyBBDatabase:
    def __init__(self, config: DatabaseConfig):
        self._pool = MySQLConnectionPool(
            pool_name="mybb_mcp",
            pool_size=5,
            pool_reset_session=True,
            host=config.host,
            port=config.port,
            database=config.database,
            user=config.user,
            password=config.password,
            connect_timeout=10,
            read_timeout=30
        )

    @contextmanager
    def connection(self):
        conn = self._pool.get_connection()
        try:
            yield conn
        finally:
            conn.close()  # Returns to pool
```

### 4.2 Plugin Creator Enhancement

**Current Parameters:**
```python
mybb_create_plugin(
    codename, name, description,
    author="Developer", version="1.0.0",
    hooks=[], has_settings=False, has_templates=False, has_database=False
)
```

**Enhanced Parameters:**
```python
mybb_create_plugin(
    codename, name, description,
    author="Developer", version="1.0.0",
    # Existing (enhanced)
    hooks=[],  # Now with priority support: [{"name": "hook", "priority": 10}]
    has_settings=False,  # Now includes rebuild_settings() calls
    has_templates=False,  # Now includes template caching pattern
    has_database=False,  # Now generates multi-DB switch statements
    # NEW parameters
    has_tasks=False,  # Generate task file
    task_name="",  # Task function name
    security_level="standard",  # "minimal", "standard", "strict"
    template_modifications=[],  # [{template, find, replace}]
    admin_hooks=[],  # Admin-specific hooks
    db_support=["mysql", "pgsql", "sqlite"],  # DB types to support
)
```

**Generated Code Must Include:**
1. IN_MYBB check at file start
2. rebuild_settings() in activate() and uninstall()
3. Multi-DB table creation with switch statement
4. Template caching via $templatelist
5. Hook registration at file level (not in functions)
6. CSRF protection template for forms
7. find_replace_templatesets() for template modifications

### 4.3 Template Tool Enhancement

**New Tools:**

```python
mybb_find_replace_template(
    title: str,           # Template name (e.g., "header")
    find_regex: str,      # Regex pattern to find
    replace: str,         # Replacement string
    autocreate: bool = True,  # Create custom templates if not exist
    sid: int = None       # Specific set or all sets
) -> dict

mybb_batch_write_templates(
    templates: list[dict]  # [{title, template, sid}]
) -> dict

mybb_diff_template(
    title: str,
    sid: int = None       # Compare custom to master
) -> dict

mybb_list_outdated_templates(
    sid: int = None
) -> list[dict]

mybb_validate_template(
    template_content: str
) -> dict  # {valid: bool, errors: [], warnings: []}
```

### 4.4 Hook System Enhancement

**Dynamic Hook Discovery:**

```python
def discover_hooks(mybb_root: str) -> dict:
    """Parse MyBB codebase to extract all run_hooks() calls"""
    hooks = {}

    # Scan all PHP files
    for php_file in Path(mybb_root).rglob("*.php"):
        content = php_file.read_text()

        # Find run_hooks calls with regex
        pattern = r'\$plugins->run_hooks\([\'"](\w+)[\'"]'
        for match in re.finditer(pattern, content):
            hook_name = match.group(1)
            if hook_name not in hooks:
                hooks[hook_name] = {
                    "files": [],
                    "category": categorize_hook(hook_name),
                    "argument_pattern": detect_argument_pattern(content, match)
                }
            hooks[hook_name]["files"].append({
                "file": str(php_file.relative_to(mybb_root)),
                "line": content[:match.start()].count('\n') + 1
            })

    return hooks
```

**Enhanced Categories (15 vs current 12):**
- index, showthread, member, usercp, forumdisplay
- newthread, newreply, editpost (NEW)
- modcp, admin, global, misc
- datahandler, parser (NEW), moderation (NEW)

### 4.5 Content Management Tools

**Architecture:** Wrap MyBB datahandlers, never bypass validation

```python
# tools/content.py

class ContentManager:
    """Wraps MyBB datahandlers for content operations"""

    def __init__(self, db: MyBBDatabase, mybb_root: str):
        self.db = db
        self.mybb_root = mybb_root

    async def create_thread(
        self,
        fid: int,
        subject: str,
        message: str,
        author_uid: int,
        options: dict = None
    ) -> dict:
        """
        Create thread using PostDataHandler validation

        Uses: TestForum/inc/datahandlers/post.php
        Validates: author, subject, message, flooding, permissions
        """
        # Build data array matching PostDataHandler expectations
        data = {
            "fid": fid,
            "subject": subject,
            "message": message,
            "uid": author_uid,
            "posthash": generate_posthash(),
            "options": options or {}
        }

        # Execute validation (PostDataHandler pattern)
        # ... validation logic matching datahandler ...

        # Insert if valid
        # ... database insert with proper fields ...

        return {"tid": thread_id, "pid": first_post_id}
```

### 4.6 Admin Operations Tools

**Settings Management:**
```python
mybb_list_setting_groups() -> list[dict]
mybb_create_setting_group(name, title, description, disporder) -> dict
mybb_list_settings(gid=None) -> list[dict]
mybb_get_setting(name) -> dict
mybb_update_setting(name, value) -> dict
```

**Cache Management:**
```python
mybb_list_caches() -> list[dict]
mybb_rebuild_cache(cache_name) -> dict
mybb_rebuild_all_caches() -> dict
```

**Plugin Lifecycle:**
```python
mybb_activate_plugin(codename) -> dict
mybb_deactivate_plugin(codename) -> dict
mybb_install_plugin(codename) -> dict
mybb_uninstall_plugin(codename) -> dict
mybb_get_plugin_status(codename) -> dict
```

---

## 5. Directory Structure
<!-- ID: directory_structure -->

```
/home/austin/projects/MyBB_Playground/mybb_mcp/
├── mybb_mcp/
│   ├── __init__.py
│   ├── server.py              # MCP server entry point (614 lines)
│   ├── config.py              # Configuration management (62 lines)
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   └── connection.py      # Database layer (350 lines) [ENHANCE: pooling]
│   │
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── plugins.py         # Plugin scaffolding (354 lines) [ENHANCE]
│   │   ├── templates.py       # [NEW] Template tools with find_replace
│   │   ├── content.py         # [NEW] Posts, threads, forums
│   │   ├── admin.py           # [NEW] Settings, cache, backup, tasks
│   │   └── hooks.py           # [NEW] Dynamic hook discovery
│   │
│   └── sync/
│       ├── __init__.py
│       ├── service.py         # Sync orchestrator (128 lines)
│       ├── watcher.py         # File watcher (247 lines) [FIX: threading]
│       ├── templates.py       # Template export/import (194 lines)
│       ├── stylesheets.py     # Stylesheet export/import
│       ├── cache.py           # Cache refresh via HTTP (70 lines)
│       ├── router.py          # Path routing
│       ├── groups.py          # Template group management
│       └── config.py          # Sync configuration
│
├── tests/                     # [NEW] Test suite
│   ├── test_security.py
│   ├── test_plugins.py
│   ├── test_templates.py
│   ├── test_content.py
│   └── test_admin.py
│
├── .env.example               # Environment template
├── pyproject.toml             # Package configuration
└── README.md                  # Documentation
```

---

## 6. Data & Storage
<!-- ID: data_storage -->

### Datastores

**Primary: MyBB MySQL Database (75 tables)**

| Category | Tables | MCP Coverage | Enhancement |
|----------|--------|--------------|-------------|
| Templates | 3 | 100% | Add find_replace |
| Themes/Styles | 2 | 100% | - |
| Plugins | 1 | 50% | Add lifecycle |
| Posts | 1 | 0% | NEW |
| Threads | 1 | 0% | NEW |
| Forums | 1 | 0% | NEW |
| Users | 3 | 0% | NEW |
| Settings | 2 | 0% | NEW |
| Cache | 1 | 0% | NEW |
| Tasks | 1 | 0% | NEW |

**Secondary: Filesystem**
- Template sync directory (configurable)
- Stylesheet sync directory
- Plugin files (inc/plugins/)
- Database backups (admin/backups/)

### Connection Pool Configuration

```python
POOL_CONFIG = {
    "pool_name": "mybb_mcp",
    "pool_size": 5,           # 5 connections
    "pool_reset_session": True,
    "connect_timeout": 10,    # 10 second connection timeout
    "read_timeout": 30,       # 30 second query timeout
}
```

### Indexes & Performance

- MyBB maintains indexes on all foreign keys
- Template queries use title + sid index
- Post queries benefit from tid + dateline index
- Settings queries use name index

---

## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->

### Unit Tests

**Security Tests:**
- Connection pooling behavior
- Password requirement enforcement
- Thread-safe async operations

**Plugin Tests:**
- Generated code includes all patterns
- rebuild_settings() presence
- Multi-DB syntax correctness

**Template Tests:**
- find_replace regex handling
- Batch operation atomicity
- Diff algorithm correctness

### Integration Tests

**Content Workflow:**
1. Create forum -> Create thread -> Create post -> Verify hierarchy

**Plugin Workflow:**
1. Create plugin -> Activate -> Verify hooks registered -> Deactivate

**Template Workflow:**
1. Export templates -> Modify files -> Watcher syncs -> Verify DB

### Security Tests

- SQL injection vectors (all new parameters)
- Permission bypass attempts
- CSRF validation
- Rate limit enforcement

### Performance Benchmarks

- Read operations: < 100ms
- Write operations: < 500ms
- Batch operations: < 2s for 100 items
- Connection pool utilization: > 80%

---

## 8. Deployment & Operations
<!-- ID: deployment_operations -->

### Environments

- **Development:** Local MyBB with test data
- **Testing:** Isolated MyBB instance for CI
- **Production:** Connected to live MyBB installation

### Release Process

1. All tests pass (unit, integration, security)
2. Code review approved
3. Version bump in pyproject.toml
4. Git tag created
5. Changelog updated

### Configuration Management

**Required Environment Variables:**
```bash
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=mybb
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=required       # MUST be set (no default)
MYBB_ROOT=/path/to/mybb     # MyBB installation directory
MYBB_URL=http://localhost   # For cache refresh
```

### Maintenance & Monitoring

- Structured logging for all operations
- Audit trail for write operations
- Error aggregation for debugging
- Performance metrics for optimization

---

## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Authentication strategy for content operations | Architect | TODO | Options: service account, API keys, session tokens |
| Pagination pattern standardization | Coder | TODO | Recommendation: cursor-based pagination |
| Async operations for bulk tasks | Architect | TODO | Consider job queue for Phase 4 |
| MyBB permission system deep dive | Research | TODO | Need comprehensive permission matrix |
| Database transaction boundaries | Architect | Resolved | Use context manager with rollback |

---

## 10. References & Appendix
<!-- ID: references_appendix -->

### Source Research Documents

1. **RESEARCH_MyBB_MCP_Security_Audit_20260117_1405.md** (Confidence: 0.92)
   - 2 critical issues, 3 high priority issues
   - Security patterns analysis

2. **RESEARCH_MYBB_PLUGIN_PATTERNS_20260117_1405.md** (Confidence: 0.95)
   - 10 findings on plugin development
   - 6 lifecycle functions documented

3. **RESEARCH_MyBB_Template_System_20260117_1407.md** (Confidence: 0.94)
   - 9 findings on template architecture
   - 7 MCP gaps identified

4. **RESEARCH_MyBB_Hooks_System_20260117_1406.md** (Confidence: 0.95)
   - 200+ hooks cataloged
   - MCP coverage gap (15-30%)

5. **RESEARCH_VSCode_Extension_Audit_20260117_1406.md** (Confidence: 0.90)
   - 8 findings on VSCode integration
   - Cache refresh gap identified

6. **RESEARCH_MYBB_DATABASE_SCHEMA_20260117_1410.md** (Confidence: 0.95)
   - 75 tables analyzed
   - 70 unexposed tables identified

7. **RESEARCH_AdminCP_MCP_Expansion_20260117_1404.md** (Confidence: 0.92)
   - 15 admin CP opportunities
   - 52+ tool proposals

8. **RESEARCH_MyBB_MCP_Expansion_Roadmap_20260117_1405.md** (Confidence: 0.95)
   - 4-phase implementation plan
   - 10-14 week estimate

### Key File References

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Threading Issue | sync/watcher.py | 150, 180, 189 | asyncio.run() anti-pattern |
| Password Default | config.py | 45 | Empty password default |
| Connection | db/connection.py | 17, 25-35 | Single connection pattern |
| Tool Registry | server.py | 52-275 | Tool definitions |
| Handlers | server.py | 293-594 | Tool implementations |
| Plugin Hooks | tools/plugins.py | 11-24 | Static HOOKS_REFERENCE |
| Template Import | sync/templates.py | 141-194 | TemplateImporter class |

### MyBB Core References

| File | Lines | Purpose |
|------|-------|---------|
| inc/class_plugins.php | 248 | Hook system architecture |
| inc/plugins/hello.php | 589 | Reference plugin implementation |
| inc/datahandlers/post.php | 2037 | Post validation patterns |
| inc/datahandlers/user.php | 1878 | User validation patterns |
| inc/class_moderation.php | 3832 | Moderation operations |
| inc/adminfunctions_templates.php | 94 | find_replace_templatesets() |

---

**Document Status:** Approved for Implementation
**Next Step:** Create PHASE_PLAN.md with detailed implementation schedule
