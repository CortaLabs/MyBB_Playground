---
id: disk_sync-architecture-guide
title: "\U0001F3D7\uFE0F Architecture Guide \u2014 disk-sync"
doc_name: ARCHITECTURE_GUIDE
category: engineering
status: draft
version: '0.1'
last_updated: '2026-01-17'
maintained_by: Corta Labs
created_by: Corta Labs
owners: []
related_docs: []
tags: []
summary: ''
---

# 🏗️ Architecture Guide — disk-sync
**Author:** Scribe
**Version:** Draft v0.1
**Status:** Draft
**Last Updated:** 2026-01-17 11:30:14 UTC

> Architecture guide for disk-sync.

---
## 1. Problem Statement
<!-- ID: problem_statement -->
## 1. Problem Statement
<!-- ID: problem_statement -->

**Context:** MyBB templates and stylesheets are stored in the database, making local editing difficult. The vscode-mybbbridge VSCode extension provides bidirectional sync between disk files and database, but requires VSCode. We need a standalone Python service integrated with our MCP server to provide the same functionality.

**Goals:**
- Enable editing MyBB templates/stylesheets as local files with any editor
- Provide bidirectional sync: export DB to disk, import disk changes to DB
- Support automatic sync on file save (file watching)
- Maintain compatibility with vscode-mybbbridge directory structure
- Integrate with existing mybb_mcp infrastructure

**Non-Goals:**
- GUI/visual editor (use any text editor)
- Template validation/linting (separate concern)
- Version control integration (git is external)
- Multi-user concurrent editing conflict resolution

**Success Metrics:**
- Templates export to correct directory structure matching vscode-mybbbridge
- File saves automatically sync to database within 1 second
- Stylesheet cache refreshes work reliably
- Zero data loss during sync operations
<!-- ID: requirements_constraints -->
## 2. Requirements & Constraints
<!-- ID: requirements_constraints -->

**Functional Requirements:**
- FR1: Export all templates from a template set to disk as .html files
- FR2: Export all stylesheets from a theme to disk as .css files
- FR3: Import template changes from disk to database on file save
- FR4: Import stylesheet changes from disk to database on file save
- FR5: Trigger CSS cache refresh after stylesheet updates
- FR6: Support template inheritance (master sid=-2 vs custom)
- FR7: Organize templates into group folders based on prefix matching

**Non-Functional Requirements:**
- NFR1: Path structure must exactly match vscode-mybbbridge patterns
- NFR2: File watching must be cross-platform (Windows, macOS, Linux)
- NFR3: Sync operations must be atomic (no partial writes)
- NFR4: Database connection must use existing MyBBDatabase class
- NFR5: Configuration must extend existing MyBBConfig dataclass

**Assumptions:**
- MyBB database is accessible via MySQL connection
- cachecss.php is installed in MyBB root for cache refresh
- User has filesystem read/write access to sync directory
- Python 3.11+ runtime with watchdog library available

**Risks & Mitigations:**
- Risk: Concurrent edits from multiple sources - Mitigation: Last write wins (match vscode-mybbbridge)
- Risk: Database connection drops mid-sync - Mitigation: Retry logic with transaction rollback
- Risk: Cache refresh fails silently - Mitigation: Log errors and notify user
- Risk: File watcher misses events - Mitigation: Provide manual sync command
<!-- ID: architecture_overview -->
## 3. Architecture Overview
<!-- ID: architecture_overview -->

**Solution Summary:** A new `sync/` module within mybb_mcp provides bidirectional synchronization between MyBB database and local disk files, using the existing database infrastructure and adding file watching capability.

**Component Breakdown:**

| Component | Purpose | Location |
|-----------|---------|----------|
| **DiskSyncService** | Main orchestrator, manages lifecycle | `mybb_mcp/sync/service.py` |
| **PathRouter** | Parse/validate file paths, route to handlers | `mybb_mcp/sync/router.py` |
| **TemplateExporter** | Export templates from DB to disk | `mybb_mcp/sync/templates.py` |
| **TemplateImporter** | Import templates from disk to DB | `mybb_mcp/sync/templates.py` |
| **StylesheetExporter** | Export stylesheets from DB to disk | `mybb_mcp/sync/stylesheets.py` |
| **StylesheetImporter** | Import stylesheets from disk to DB | `mybb_mcp/sync/stylesheets.py` |
| **TemplateGroupManager** | Determine template group from prefix | `mybb_mcp/sync/groups.py` |
| **CacheRefresher** | HTTP calls to cachecss.php | `mybb_mcp/sync/cache.py` |
| **FileWatcher** | Monitor filesystem for changes | `mybb_mcp/sync/watcher.py` |
| **SyncConfig** | Configuration dataclass | `mybb_mcp/sync/config.py` |

**Data Flow (Export - DB to Disk):**
```
User Request -> DiskSyncService.export_templates(set_name)
  -> TemplateExporter.export(set_name)
    -> MyBBDatabase.list_templates(sid)
    -> TemplateGroupManager.get_group(template_title)
    -> Write to: sync_root/template_sets/{set}/{group}/{template}.html
```

**Data Flow (Import - Disk to DB):**
```
FileWatcher detects .html change
  -> PathRouter.parse(path) -> {type: 'template', set_name, template_name}
  -> TemplateImporter.import_template(set_name, template_name, content)
    -> MyBBDatabase.get_template(title, sid=-2)  # Check master
    -> MyBBDatabase.get_template(title, sid)     # Check custom
    -> MyBBDatabase.update_template() or create_template()
```

**Data Flow (Stylesheet Import with Cache Refresh):**
```
FileWatcher detects .css change
  -> PathRouter.parse(path) -> {type: 'stylesheet', theme_name, stylesheet_name}
  -> StylesheetImporter.import_stylesheet(theme_name, stylesheet_name, content)
    -> MyBBDatabase.update_stylesheet(sid, content)
    -> CacheRefresher.refresh(theme_name, stylesheet_name)
      -> HTTP POST to {mybb_url}/cachecss.php
```

**External Integrations:**
- **MyBB Database:** Via existing MyBBDatabase class (mysql-connector-python)
- **MyBB Cache System:** Via cachecss.php HTTP endpoint
- **File System:** Via watchdog library for cross-platform monitoring
<!-- ID: detailed_design -->
## 4. Detailed Design
<!-- ID: detailed_design -->

### 4.1 PathRouter

**Purpose:** Parse file paths and route to appropriate handlers.

```python
@dataclass
class ParsedPath:
    type: Literal['template', 'stylesheet', 'unknown']
    set_name: str | None = None      # Template set name
    group_name: str | None = None    # Template group (ignored on import)
    template_name: str | None = None # Template title (without .html)
    theme_name: str | None = None    # Theme name
    stylesheet_name: str | None = None  # Stylesheet name (with .css)
    raw_path: str = ""

class PathRouter:
    def parse(self, relative_path: str) -> ParsedPath:
        """Parse path like template_sets/Default/Header/header.html"""
    
    def build_template_path(self, set_name: str, group: str, title: str) -> Path:
        """Build: sync_root/template_sets/{set}/{group}/{title}.html"""
    
    def build_stylesheet_path(self, theme_name: str, name: str) -> Path:
        """Build: sync_root/styles/{theme}/{name}"""
```

### 4.2 TemplateGroupManager

**Purpose:** Determine which group folder a template belongs to.

```python
class TemplateGroupManager:
    HARDCODED_PATTERNS = {
        'global_': 'Global Templates',
        'header_': 'Header Templates',
        'footer_': 'Footer Templates',
        'usercp_': 'User CP Templates',
        'modcp_': 'Moderator CP Templates',
        'admin_': 'Admin Templates',
        'forum_': 'Forum Templates',
        'member_': 'Member Templates',
        'post_': 'Posting Templates',
        'poll_': 'Poll Templates',
        'pm_': 'Private Message Templates',
    }
    
    def __init__(self, db: MyBBDatabase):
        self.db = db
        self._db_groups: dict[str, str] = {}  # prefix -> title
    
    def load_groups(self) -> None:
        """Load templategroups from database."""
    
    def get_group(self, template_title: str, sid: int = -1) -> str:
        """Get group name for template using priority matching."""
```

### 4.3 TemplateExporter / TemplateImporter

**Export Flow:**
1. Get sid from template set name
2. Fetch all templates WHERE sid IN (-2, target_sid)
3. For each template, determine group via TemplateGroupManager
4. Write to `sync_root/template_sets/{set}/{group}/{title}.html`

**Import Flow:**
1. Parse path to get set_name and template_name
2. Get sid from template set name
3. Check if master template exists (sid=-2)
4. Check if custom template exists (sid=target_sid)
5. UPDATE existing custom or INSERT new custom

```python
class TemplateImporter:
    def import_template(self, set_name: str, template_name: str, content: str) -> bool:
        sid = self.db.get_template_set_sid(set_name)
        master = self.db.get_template(template_name, sid=-2)
        custom = self.db.get_template(template_name, sid=sid)
        
        if custom:
            return self.db.update_template(custom['tid'], content)
        else:
            self.db.create_template(template_name, content, sid=sid)
            return True
```

### 4.4 CacheRefresher

**Purpose:** Trigger MyBB stylesheet cache regeneration via HTTP.

```python
class CacheRefresher:
    def __init__(self, mybb_url: str, token: str | None = None):
        self.endpoint = f"{mybb_url}/cachecss.php"
        self.token = token
    
    async def refresh(self, theme_name: str, stylesheet_name: str) -> bool:
        """POST to cachecss.php to trigger cache rebuild."""
        async with httpx.AsyncClient() as client:
            response = await client.post(self.endpoint, data={
                'theme_name': theme_name,
                'stylesheet': stylesheet_name,
                'token': self.token or ''
            })
            result = response.json()
            return result.get('success', False)
```

### 4.5 FileWatcher

**Purpose:** Monitor sync directory for file changes.

```python
class SyncEventHandler(FileSystemEventHandler):
    def __init__(self, service: DiskSyncService):
        self.service = service
    
    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix == '.html' and 'template_sets' in path.parts:
            self.service.handle_template_change(path)
        elif path.suffix == '.css' and 'styles' in path.parts:
            self.service.handle_stylesheet_change(path)

class FileWatcher:
    def __init__(self, sync_root: Path, service: DiskSyncService):
        self.observer = Observer()
        self.handler = SyncEventHandler(service)
        self.sync_root = sync_root
    
    def start(self):
        self.observer.schedule(self.handler, str(self.sync_root), recursive=True)
        self.observer.start()
    
    def stop(self):
        self.observer.stop()
        self.observer.join()
```
<!-- ID: directory_structure -->
## 5. Directory Structure
<!-- ID: directory_structure -->

**Module Structure (mybb_mcp/sync/):**
```
mybb_mcp/
├── __init__.py
├── config.py              # Existing - add SyncConfig
├── server.py              # Existing - add sync tools
├── db/
│   ├── __init__.py
│   └── connection.py      # Existing - add new methods
└── sync/                  # NEW MODULE
    ├── __init__.py
    ├── config.py          # SyncConfig dataclass
    ├── service.py         # DiskSyncService orchestrator
    ├── router.py          # PathRouter
    ├── groups.py          # TemplateGroupManager
    ├── templates.py       # TemplateExporter, TemplateImporter
    ├── stylesheets.py     # StylesheetExporter, StylesheetImporter
    ├── cache.py           # CacheRefresher
    └── watcher.py         # FileWatcher, SyncEventHandler
```

**Sync Directory Structure (on disk):**
```
{sync_root}/                        # Configurable, default: ./mybb_sync/
├── template_sets/
│   └── {set_name}/                 # e.g., "Default Templates"
│       ├── Global Templates/
│       │   ├── global_start.html
│       │   └── global_end.html
│       ├── Header Templates/
│       │   ├── header.html
│       │   └── header_welcomeblock.html
│       ├── Footer Templates/
│       │   └── footer.html
│       └── {other_groups}/
│           └── {template_name}.html
└── styles/
    └── {theme_name}/               # e.g., "Default"
        ├── global.css
        ├── usercp.css
        └── {stylesheet_name}.css
```
<!-- ID: data_storage -->
## 6. Data & Storage
<!-- ID: data_storage -->

**Database Tables Used (MyBB):**

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `mybb_templates` | Template storage | tid, title, template, sid, version, dateline |
| `mybb_templatesets` | Template set definitions | sid, title |
| `mybb_templategroups` | Group prefix mappings | gid, prefix, title |
| `mybb_themes` | Theme definitions | tid, name, properties |
| `mybb_themestylesheets` | Stylesheet storage | sid, tid, name, stylesheet, cachefile, lastmodified |

**New Database Methods Required (MyBBDatabase):**

```python
# Add to mybb_mcp/db/connection.py
def get_template_set_by_name(self, name: str) -> dict | None:
    """Get template set by name, returns {sid, title}."""

def list_template_groups(self) -> list[dict]:
    """List all template groups, returns [{gid, prefix, title}]."""

def get_theme_by_name(self, name: str) -> dict | None:
    """Get theme by name, returns {tid, name, ...}."""

def get_stylesheet_by_name(self, tid: int, name: str) -> dict | None:
    """Get stylesheet by theme ID and name."""
```

**File Storage:**
- Templates: UTF-8 encoded .html files
- Stylesheets: UTF-8 encoded .css files
- No metadata files needed (path encodes all info)
<!-- ID: testing_strategy -->
## 7. Testing & Validation Strategy
<!-- ID: testing_strategy -->

**Unit Tests:**
- PathRouter: Test path parsing for valid/invalid paths
- TemplateGroupManager: Test all matching strategies (global, prefix, hardcoded, fallback)
- Template/Stylesheet importers: Test inheritance logic (master exists, custom exists, both, neither)

**Integration Tests:**
- Export templates to disk, verify file structure
- Import templates from disk, verify database updates
- Stylesheet update + cache refresh (mock HTTP)
- FileWatcher event handling

**Test Files:**
```
tests/
├── test_router.py          # PathRouter unit tests
├── test_groups.py          # TemplateGroupManager tests
├── test_templates.py       # Template export/import tests
├── test_stylesheets.py     # Stylesheet export/import tests
├── test_watcher.py         # FileWatcher tests
└── test_integration.py     # Full sync cycle tests
```

**Manual QA Checklist:**
- [ ] Export "Default Templates" set, verify folder structure
- [ ] Edit template in editor, verify auto-sync to DB
- [ ] Edit stylesheet, verify cache refresh works
- [ ] Start/stop file watcher without errors
<!-- ID: deployment_operations -->
## 8. Deployment & Operations
<!-- ID: deployment_operations -->

**Dependencies (add to pyproject.toml):**
```toml
[project]
dependencies = [
    "mysql-connector-python>=8.0",  # Existing
    "python-dotenv>=1.0",           # Existing
    "mcp>=0.1",                     # Existing
    "watchdog>=3.0",                # NEW - file watching
    "httpx>=0.25",                  # NEW - async HTTP for cache refresh
]
```

**Configuration (add to .env):**
```bash
# Existing
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=password
MYBB_DB_PREFIX=mybb_
MYBB_URL=http://localhost:8022

# NEW - Disk Sync
SYNC_ROOT=./mybb_sync           # Directory for synced files
SYNC_AUTO_UPLOAD=true           # Enable file watching
SYNC_CACHE_TOKEN=               # Optional auth token for cachecss.php
```

**MCP Tools to Add:**
- `mybb_sync_export_templates` - Export template set to disk
- `mybb_sync_export_stylesheets` - Export theme stylesheets to disk
- `mybb_sync_start_watcher` - Start file watching
- `mybb_sync_stop_watcher` - Stop file watching
- `mybb_sync_status` - Show sync status
<!-- ID: open_questions -->
## 9. Open Questions & Follow-Ups
<!-- ID: open_questions -->

| Item | Owner | Status | Notes |
|------|-------|--------|-------|
| Should we add debouncing for rapid file saves? | Architect | DECIDED | No - match vscode-mybbbridge behavior (no debounce) |
| How to handle cachecss.php not installed? | Coder | TODO | Log warning, continue without cache refresh |
| Support for binary assets (images in themes)? | Future | DEFERRED | Out of scope for v1, only .html/.css |
| Conflict detection for concurrent edits? | Future | DEFERRED | Last write wins for v1 |
<!-- ID: references_appendix -->
## 10. References & Appendix
<!-- ID: references_appendix -->

**Research Document:**
- `RESEARCH_VSCODE_SYNC_PATTERNS.md` - Comprehensive analysis of vscode-mybbbridge sync patterns

**Source Code References:**
- vscode-mybbbridge TypeScript source (sync logic, queries, path handling)
- MyBB template/stylesheet database schema

**Key SQL Queries (from research):**

```sql
-- Fetch templates with group assignment
SELECT DISTINCT t.*, t.template as template,
       CASE
           WHEN t.title LIKE 'global_%' THEN 'Global Templates'
           WHEN t.title LIKE 'header_%' THEN 'Header Templates'
           -- ... more patterns
           ELSE tg.title
       END as group_name
FROM mybb_templates t
LEFT JOIN mybb_templategroups tg ON t.title LIKE CONCAT(tg.prefix, '%')
WHERE t.sid IN (-2, ?)
ORDER BY t.title;

-- Fetch stylesheets for theme
SELECT name, stylesheet FROM mybb_themestylesheets
WHERE tid = (SELECT tid FROM mybb_themes WHERE name = ?);
```

**Confidence Score:** 0.92
- Architecture based on verified research (0.95 confidence)
- Integration points verified against actual mybb_mcp code
- Some new database methods required (verified schema exists)
