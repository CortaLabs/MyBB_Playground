# Plugin & Theme Manager - Spec Proposal
**Author:** Austin + Claude
**Version:** Draft v0.1
**Date:** 2026-01-18

> A Nexus Mods-style management system for MyBB plugins and themes built with AI-assisted development.

---

## Vision

Create a **mod manager** for MyBB that:
- Organizes plugins/themes in isolated development folders
- Tracks project metadata in a database
- Supports private (gitignored) and public (uploadable) plugins
- Integrates with existing MCP tools (no new tools needed)
- Enables clean AI-assisted plugin development workflows

**Analogy:** Think Skyrim Nexus Mods / Vortex, but for MyBB plugins developed with Claude + MCP.

---

## Problem Statement

### Current Pain Points
1. **Plugins live directly in `TestForum/inc/plugins/`** - No isolation, hard to track what's in development vs installed
2. **No project metadata** - Can't track plugin version, status, dependencies, or development history
3. **Manual deployment** - Copy/paste from dev to install location
4. **No public/private separation** - Everything either gitignored or exposed
5. **81 MCP tools** - Already have plenty; need orchestration, not more tools

### Desired Workflow
```
[Development]     [Staging]           [Installed]
plugins/          plugins_staging/    TestForum/inc/plugins/
├── my_plugin/    ├── my_plugin.php   └── my_plugin.php
│   ├── src/
│   ├── tests/
│   └── meta.json
```

---

## Architecture Overview

### Directory Structure

```
MyBB_Playground/
├── plugins/                    # Plugin development workspace
│   ├── public/                 # Public plugins (committed to git)
│   │   ├── example_plugin/
│   │   │   ├── src/
│   │   │   │   └── example_plugin.php
│   │   │   ├── languages/
│   │   │   │   └── english/
│   │   │   │       └── example_plugin.lang.php
│   │   │   ├── templates/      # Plugin-specific templates
│   │   │   ├── tests/
│   │   │   ├── meta.json       # Plugin metadata
│   │   │   └── README.md
│   │   └── another_plugin/
│   │
│   └── private/                # Private plugins (gitignored)
│       └── my_secret_plugin/
│
├── themes/                     # Theme development workspace
│   ├── public/
│   │   └── my_theme/
│   │       ├── stylesheets/
│   │       ├── templates/      # Theme template overrides
│   │       └── meta.json
│   └── private/
│
├── mybb_sync/                  # Existing template sync (unchanged)
│
└── .plugin_manager/            # Manager database and state
    ├── projects.db             # SQLite database
    └── config.json             # Manager configuration
```

### Database Schema (SQLite)

```sql
-- Plugin/Theme Projects
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,              -- 'plugin' or 'theme'
    visibility TEXT DEFAULT 'public', -- 'public' or 'private'
    status TEXT DEFAULT 'development', -- 'development', 'testing', 'installed', 'archived'
    version TEXT DEFAULT '1.0.0',
    description TEXT,
    author TEXT,
    mybb_compatibility TEXT,         -- e.g., "1.8.x"
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    installed_at TIMESTAMP,          -- When deployed to TestForum
    path TEXT NOT NULL               -- Relative path from workspace root
);

-- Project Dependencies
CREATE TABLE dependencies (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    depends_on TEXT NOT NULL,        -- Plugin codename
    version_constraint TEXT,         -- e.g., ">=1.0.0"
    optional BOOLEAN DEFAULT FALSE
);

-- Development History (links to Scribe)
CREATE TABLE history (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    action TEXT NOT NULL,            -- 'created', 'updated', 'installed', 'uninstalled'
    details TEXT,                    -- JSON blob
    scribe_project TEXT,             -- Link to Scribe project if exists
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Hooks Registry (which hooks each plugin uses)
CREATE TABLE hook_usage (
    id INTEGER PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    hook_name TEXT NOT NULL,
    handler_function TEXT NOT NULL,
    priority INTEGER DEFAULT 10
);
```

### meta.json Schema

```json
{
    "name": "example_plugin",
    "display_name": "Example Plugin",
    "version": "1.0.0",
    "author": "Austin",
    "description": "An example plugin for demonstration",
    "mybb_compatibility": "1.8.x",
    "visibility": "public",

    "hooks": [
        {"name": "index_start", "handler": "example_plugin_index", "priority": 10},
        {"name": "postbit", "handler": "example_plugin_postbit", "priority": 5}
    ],

    "settings": [
        {"name": "example_enabled", "title": "Enable Plugin", "type": "yesno", "default": "1"}
    ],

    "templates": [
        "example_widget",
        "example_modal"
    ],

    "stylesheets": [
        "example_plugin.css"
    ],

    "dependencies": [
        {"name": "ougc_awards", "version": ">=2.0.0", "optional": true}
    ],

    "files": {
        "plugin": "src/example_plugin.php",
        "languages": "languages/",
        "templates": "templates/",
        "stylesheets": "stylesheets/"
    }
}
```

---

## Workflows

### 1. Create New Plugin

```
User: "Create a new private plugin called 'my_notifications'"

Claude:
1. Creates directory: plugins/private/my_notifications/
2. Scaffolds structure using existing mybb_create_plugin patterns
3. Creates meta.json with defaults
4. Registers in projects.db
5. Links to Scribe project for development tracking
```

### 2. Install Plugin to TestForum

```
User: "Install my_notifications to the forum"

Claude:
1. Reads meta.json for file mappings
2. Copies src/my_notifications.php → TestForum/inc/plugins/
3. Copies languages/* → TestForum/inc/languages/english/
4. Uses mybb_plugin_activate to enable in cache
5. Updates projects.db status = 'installed'
6. Warns: "Remember to activate in ACP to run _activate() hooks"
```

### 3. Sync Development Changes

```
User: "Sync my plugin changes to the forum"

Claude:
1. Detects modified files in plugins/private/my_notifications/
2. Copies updated files to TestForum locations
3. If templates changed, uses mybb_template_batch_write
4. If stylesheets changed, uses mybb_write_stylesheet + cache refresh
5. Logs sync in history table
```

### 4. Export Plugin for Distribution

```
User: "Package my_notifications for release"

Claude:
1. Validates meta.json completeness
2. Runs any tests in tests/ folder
3. Creates distributable ZIP:
   - my_notifications.php
   - languages/
   - templates/ (if any)
   - README.md
4. Generates install instructions from hooks/settings
```

### 5. Import External Plugin

```
User: "Import this plugin ZIP for development"

Claude:
1. Extracts to plugins/public/imported_plugin/
2. Analyzes PHP for hooks, settings, templates
3. Generates meta.json from analysis
4. Registers in projects.db
5. Links to Scribe for development tracking
```

---

## Integration with Existing Tools

### Tools We'll Use (No New Tools Needed)

| Existing Tool | Use Case |
|---------------|----------|
| `mybb_create_plugin` | Scaffold new plugin PHP |
| `mybb_analyze_plugin` | Parse hooks/settings from existing plugins |
| `mybb_list_hooks` | Hook discovery for meta.json |
| `mybb_hooks_discover` | Find hooks in MyBB core |
| `mybb_hooks_usage` | See which plugins use which hooks |
| `mybb_plugin_activate/deactivate` | Cache management |
| `mybb_plugin_is_installed` | Check installation status |
| `mybb_template_batch_write` | Deploy plugin templates |
| `mybb_write_stylesheet` | Deploy plugin stylesheets |
| `mybb_read_plugin` | Read plugin source for analysis |
| `mybb_db_query` | Direct DB operations for projects.db |

### New Orchestration Layer

Instead of adding tools, we add **orchestration scripts** that compose existing tools:

```python
# Plugin Manager CLI (or skill)
class PluginManager:
    def create_plugin(name, visibility='public', hooks=None):
        # 1. Create directory structure
        # 2. Call mybb_create_plugin for PHP scaffold
        # 3. Generate meta.json
        # 4. Register in SQLite
        # 5. Create Scribe project

    def install_plugin(name):
        # 1. Read meta.json
        # 2. Copy files to TestForum
        # 3. Call mybb_plugin_activate
        # 4. Update projects.db

    def sync_plugin(name):
        # 1. Detect changed files
        # 2. Copy to destinations
        # 3. Call template/stylesheet tools if needed
```

---

## Private vs Public Separation

### .gitignore Strategy

```gitignore
# Plugin Manager
plugins/private/          # All private plugins
themes/private/           # All private themes
.plugin_manager/          # Local database (optional)

# But NOT:
# plugins/public/         # These are committed
# themes/public/          # These are committed
```

### Visibility Rules

| Visibility | Location | Git Status | Use Case |
|------------|----------|------------|----------|
| `public` | `plugins/public/` | Tracked | Open source, shareable |
| `private` | `plugins/private/` | Ignored | Personal, proprietary, WIP |

---

## Implementation Phases

### Phase 1: Foundation (Core Structure)
- [ ] Create directory structure
- [ ] Set up SQLite database with schema
- [ ] Create meta.json schema validator
- [ ] Basic CRUD operations for projects table

### Phase 2: Plugin Workflows
- [ ] `create_plugin` workflow (scaffold + register)
- [ ] `install_plugin` workflow (deploy to TestForum)
- [ ] `sync_plugin` workflow (update deployed files)
- [ ] `uninstall_plugin` workflow (remove from TestForum)

### Phase 3: Theme Workflows
- [ ] `create_theme` workflow
- [ ] `install_theme` workflow (deploy templates + stylesheets)
- [ ] `sync_theme` workflow
- [ ] Integration with existing mybb_sync

### Phase 4: Advanced Features
- [ ] Dependency resolution
- [ ] Version management
- [ ] Export/package for distribution
- [ ] Import external plugins
- [ ] Scribe integration for development tracking

---

## Open Questions

1. **Database Location**: Should `.plugin_manager/` be gitignored or committed?
   - Gitignored: Each dev has own project list
   - Committed: Shared project registry

2. **Template/Stylesheet Storage**:
   - Keep in plugin folder and sync on demand?
   - Or integrate with mybb_sync directory?

3. **MyBB Admin CP Integration**:
   - Should `install_plugin` also click through ACP activation?
   - Or just handle file deployment + cache?

4. **CLI vs Skill**:
   - Implement as Claude Code skill (`/plugin create my_plugin`)?
   - Or as standalone orchestration scripts?

5. **Multi-Forum Support**:
   - Should we support deploying to multiple MyBB installations?
   - Or keep it single-forum focused?

---

## Success Metrics

- **Organization**: All plugins/themes in isolated, well-structured folders
- **Tracking**: Full metadata and history for every project
- **Workflow**: Create → Develop → Test → Install in clean steps
- **No Tool Bloat**: Zero new MCP tools; pure orchestration
- **Privacy**: Clear separation of public/private work

---

## Next Steps

1. Review and refine this spec
2. Launch Scribe Research Analyst to investigate existing plugin structures
3. Launch Scribe Architect to design detailed implementation
4. Implement in phases with Scribe Coders

---

*"Organize the chaos, orchestrate the tools, ship the plugins."*
