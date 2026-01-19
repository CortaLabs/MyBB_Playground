---
id: mybb_forge_v2-requirements-brief
title: MyBB Forge v2 - Requirements Brief
doc_name: REQUIREMENTS_BRIEF
category: engineering
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
# MyBB Forge v2 - Requirements Brief

## Vision Statement

Transform MyBB Playground from a functional development toolkit into an **optimal multi-agent MyBB development platform** with:
- Git worktree integration for parallel agent workflows
- Restructured plugin architecture with disk-first template management
- Robust manifest tracking for clean install/uninstall
- Near-instant db-sync performance
- Beautiful, consistent plugin output

---

## 1. Git Integration Strategy

### 1.1 Git Worktrees - NOT Recommended ❌
**Research Conclusion (R1):** Worktrees provide excellent FILE isolation but **database sharing kills it** for our use case.

- Multiple agents writing to same MySQL templates table = race conditions
- `mybb_sync` watcher is single-instance only (no distributed locking)
- Would require per-agent database setup - too complex

**Decision:** Use scope-based parallelism instead (different plugins/features per agent on same branch).

### 1.2 Git Subtrees for Private Repos ✓
**Problem:** Want private git repos for proprietary plugins/themes without nested git hell.

**Solution:** Git subtrees - cleaner than submodules, no nested `.git` directories.

```bash
# Add private plugins as subtree
git subtree add --prefix=plugin_manager/plugins/private \
    git@github.com:CortaLabs/mybb-private-plugins.git main --squash

# Push changes to private repo
git subtree push --prefix=plugin_manager/plugins/private \
    git@github.com:CortaLabs/mybb-private-plugins.git main
```

**Benefits:**
- No nested `.git` complexity
- Clean commit history in main repo
- Bidirectional sync (push/pull)
- Per-directory remote configuration

---

## 2. Plugin Architecture Restructure

### 2.1 New Directory Structure
**Current:**
```
plugin_manager/plugins/public/codename/
├── meta.json
├── src/codename.php
└── (other files scattered)
```

**Proposed:**
```
inc/plugins/
├── codename.php              # Main entry point (lean loader)
└── codename/
    ├── src/                  # PHP classes, handlers, utilities
    │   ├── core.php
    │   ├── hooks.php
    │   └── admin.php
    ├── templates/            # Individual .html files (disk-first!)
    │   ├── codename_main.html
    │   ├── codename_row.html
    │   └── codename_form.html
    ├── languages/            # Language files
    │   └── english.lang.php
    ├── styles/               # CSS files
    │   └── codename.css
    └── meta.json             # Plugin metadata + manifest
```

### 2.2 Disk-First Template Management
**Key Change:** Templates live as `.html` files on disk, mirroring db-sync structure exactly.

**On Install:**
- Read template files from `codename/templates/`
- Insert into MyBB database via `$db->insert_query('templates', ...)`
- Track in manifest for clean uninstall

**Benefits:**
- Version control for templates
- Agents can edit templates directly
- No more "plugin templates get overwritten" issues
- Consistent with db-sync workflow

### 2.3 Manifest System
**Purpose:** Track every file a plugin installs for proper cleanup.

**Manifest Structure (in meta.json):**
```json
{
  "manifest": {
    "files": [
      {"source": "src/core.php", "dest": "inc/plugins/codename/src/core.php", "hash": "abc123"},
      {"source": "codename.php", "dest": "inc/plugins/codename.php", "hash": "def456"}
    ],
    "templates": [
      {"name": "codename_main", "file": "templates/codename_main.html"}
    ],
    "settings": [...],
    "database_tables": [...],
    "stylesheets": [...]
  }
}
```

**Research Questions:**
- Does MyBB have built-in file hashing we can leverage?
- How does MyBB's plugin system track what to uninstall?
- Should we use SHA256 or MD5 for hashes?

---

## 3. Configuration System (YAML + .env)

**User preference:** "mfers dont wanna be editing json" - use YAML for config, .env for secrets.

### 3.1 Configuration Files

```
plugin_manager/
├── .mybb-forge.yaml          # Structured config (TRACKED in git)
├── .mybb-forge.env           # Secrets/remotes (GITIGNORED)
├── .mybb-forge.yaml.example  # Template for new devs (TRACKED)
└── .mybb-forge.env.example   # Template for secrets (TRACKED)
```

### 3.2 YAML Config Schema
```yaml
# .mybb-forge.yaml
developer:
  name: "Your Name"
  website: "https://example.com"
  email: "you@example.com"

defaults:
  compatibility: "18*"
  license: "MIT"
  visibility: "public"

subtrees:
  plugins/private:
    remote_env: PRIVATE_PLUGINS_REMOTE  # References .env
    branch: main
    squash: true
  themes/private:
    remote_env: PRIVATE_THEMES_REMOTE
    branch: main
    squash: true
```

### 3.3 Environment File
```bash
# .mybb-forge.env (GITIGNORED - contains credentials)
PRIVATE_PLUGINS_REMOTE=git@github.com:YourOrg/mybb-private-plugins.git
PRIVATE_THEMES_REMOTE=git@github.com:YourOrg/mybb-private-themes.git
```

### 3.4 Config Precedence
1. Environment variables (highest priority)
2. `.mybb-forge.yaml` local config
3. Built-in defaults (lowest priority)

### 3.5 mybb_create_plugin Enhancements
- Auto-fill author from YAML config
- Generate initial manifest structure
- Create template directory with stub files
- Better scaffold for src/ organization
- Graceful fallback if no config exists

---

## 4. MCP Tool Fixes

### 4.1 Direct SQL → MyBB Bridge
**Problem:** Some MCP tools use direct SQL queries instead of MyBB's internal functions.

**Why This Matters:**
- Bypasses MyBB's security/escaping
- Doesn't trigger MyBB hooks/events
- Cache invalidation might be missed
- Not consistent with how plugins work

**Research Needed:**
- Inventory which tools use direct SQL
- Identify which MyBB functions should be used instead
- Determine if our PHP bridge can expose these cleanly

### 4.2 Potential global.php Integration
**Idea:** Hook into MyBB's `global.php` for direct MyBB object access.

**Benefits:**
- Access to `$mybb`, `$db`, `$cache`, `$plugins` objects
- Use MyBB's actual functions instead of reimplementing
- Proper cache handling built-in

**Concerns:**
- Security implications?
- Performance overhead?
- Session/user context handling?

---

## 5. DB-Sync Optimization

### 5.1 Performance Goals
**Current:** Noticeable delay on sync operations.
**Target:** Near-instant sync without CPU/memory spikes.

### 5.2 Research Areas
- Debouncing strategy (current implementation)
- Batch vs individual writes
- File watcher efficiency (watchdog alternatives?)
- Database connection pooling
- Incremental sync (only changed content)
- In-memory caching layer

---

## 6. MCP Server Modularization

### 6.1 The Problem
**`server.py` is 3,794 lines** - a monolith handling 85+ tools with a single 2,642-line if-elif chain.

### 6.2 Research Findings (R6)
- 85 tools across 12 categories
- Monolithic handler function (God Function anti-pattern)
- All logic inline, no service classes
- Existing `sync/` module shows proper separation pattern to follow

### 6.3 Proposed Module Structure
```
mybb_mcp/mybb_mcp/
├── server.py              # ~150 lines (init + dispatcher)
├── tools_registry.py      # ~1,080 lines (tool definitions)
├── handlers/
│   ├── common.py          # Shared utilities
│   ├── dispatcher.py      # Dictionary-based routing
│   ├── templates.py       # 9 handlers
│   ├── themes.py          # 6 handlers
│   ├── plugins.py         # 12 handlers
│   ├── content.py         # 17 handlers (forums/threads/posts)
│   ├── users.py           # 7 handlers
│   ├── moderation.py      # 8 handlers
│   ├── admin.py           # 11 handlers
│   ├── search.py          # 4 handlers
│   ├── sync.py            # 5 handlers
│   ├── tasks.py           # 6 handlers
│   └── database.py        # 1 handler
└── common/
    └── (existing db/, sync/, etc.)
```

### 6.4 Migration Strategy (6 Phases)
1. **Preparation** - Set up directories, create dispatcher framework
2. **Simple Categories** - Extract DB Query, Tasks, Admin (18 tools)
3. **Medium Complexity** - Extract Templates, Themes, Moderation, Search (27 tools)
4. **Complex Categories** - Extract Content CRUD, Disk Sync, Users (29 tools)
5. **Plugin Handlers** - Extract most complex category (12 tools)
6. **Finalization** - Move tool definitions, comprehensive testing

---

## 7. Research Swarm Strategy

### Phase 1: System Inventory (Completed ✓)
| Researcher | Focus Area | Status | Key Finding |
|------------|------------|--------|-------------|
| R1 (Opus) | Git worktrees | ✓ | DB sharing kills worktrees; subtrees are the answer |
| R2 | Plugin Manager | ✓ | Manifest exists in SQLite, not in meta.json |
| R3 | MCP tools audit | ✓ | Only 4 direct SQL ops, 87 wrapper methods exist |
| R4 | DB-sync | ✓ | 0.5s debounce is main bottleneck |
| R5 | MyBB internals | ✓ | SHA512 hashing, datacache ideal for manifest |
| R6 | server.py modularization | ✓ | 3,794 lines → 12 handler modules |
| R7 | Git subtree + config | ✓ | YAML + .env config system designed |

### Phase 2: Design Decisions (Sequential - Opus Architect)
Based on research findings, architect will:
- Define new plugin structure spec
- Design manifest schema
- Plan git workflow
- Spec MCP tool refactors

### Phase 3: Implementation Planning
Break into bounded task packages for parallel coders.

---

## 8. Out of Scope (For Now)

- Theme development workflow (future project after plugins refined)
- New plugin features (focus is on infrastructure)
- MyBB core modifications

---

## 9. Success Criteria

- [ ] ~~Agents can work in parallel via git worktrees~~ → Scope-based parallelism instead
- [ ] Plugin creation produces consistent, beautiful output
- [ ] Templates live on disk and install cleanly from files
- [ ] Full manifest tracking for clean uninstall
- [ ] DB-sync feels instant (reduced debounce, batching)
- [ ] No direct SQL in MCP tools (all via MyBB bridge)
- [ ] Private plugins/themes push to separate repos via subtrees
- [ ] Developer config auto-fills metadata (YAML + .env)
- [ ] **server.py modularized** (3,794 → ~150 lines + 12 handler modules)

---

## 10. Existing Context

**Already Built (Context for Researchers):**
- 3 plugins created with current system (dice_roller, cortex, invite_system)
- invite_system is complex - good reference for what "beautiful" plugins look like
- MCP server with 85+ tools in `mybb_mcp/`
- Plugin Manager with workspace at `plugin_manager/`
- DB-sync system at `mybb_sync/`
- PHP bridge exists in TestForum for lifecycle execution

**Pain Points Observed:**
- Template overwrites during plugin deployment
- Manual file tracking for uninstalls
- Direct SQL in some MCP tools
- DB-sync has noticeable latency
- No parallel agent isolation
- Private repos would require nested git (painful)
