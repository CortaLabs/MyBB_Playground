# MyBB Playground

<div align="center">

**AI-Powered MyBB Development Toolkit**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PHP 8.0+](https://img.shields.io/badge/php-8.0+-purple.svg)](https://www.php.net/)
[![MyBB 1.8.x](https://img.shields.io/badge/mybb-1.8.x-orange.svg)](https://mybb.com/)
[![MCP Protocol](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io/)

*Making MyBB plugin and theme development accessible through natural language.*

[Getting Started](#-quick-start) •
[Documentation](docs/wiki/index.md) •
[112 MCP Tools](docs/wiki/mcp_tools/index.md) •
[Plugin Manager](docs/wiki/plugin_manager/index.md)

</div>

---

## What is MyBB Playground?

MyBB Playground connects **Claude Code** directly to your MyBB installation through **112 MCP tools**. Instead of manually editing PHP files, writing SQL queries, and navigating the admin panel, you can develop plugins and themes using natural language.

```
You: "Create a plugin that shows user badges based on post count"

Claude: Creates complete plugin with:
        ✓ Plugin structure (_info, _activate, _deactivate, _install, _uninstall)
        ✓ Database table for badge definitions
        ✓ Admin CP settings page
        ✓ Template injection via hooks
        ✓ Proper MyBB security patterns
```

### Key Features

| Feature | Description |
|---------|-------------|
| **112 MCP Tools** | Full MyBB API coverage — templates, themes, plugins, forums, users, moderation, settings, server |
| **Theme Manager** | Complete theme development workflow with stylesheets, template overrides, and jscripts |
| **Plugin Manager** | Structured workspace for plugin development with deployment tracking |
| **Workspace Sync** | Hash-based change detection syncs only modified files between workspace and database |
| **PHP Bridge** | Execute actual PHP lifecycle functions (_install, _activate, etc.) |
| **AI-Native** | Built specifically for Claude Code integration |

---

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/CortaLabs/MyBB_Playground.git
cd MyBB_Playground

# Interactive installer handles everything:
# - OS detection (Ubuntu/Debian/macOS/WSL)
# - PHP, MariaDB installation
# - Database setup
# - MyBB download & extraction
# - Default plugin deployment
# - Git authentication (optional)
# - Claude Code MCP integration
./install.sh
```

The installer will prompt you through each step and save your configuration to `.env`.

### 2. Start the Server

```bash
./start_mybb.sh
```

This starts PHP's built-in server on port 8022 (configurable in `.env`).

### 3. Connect to Claude Code

The installer sets up MCP automatically, but you can also do it manually:

```bash
cd mybb_mcp

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# Register MCP server (project scope - only active in this directory)
claude mcp add --scope project --transport stdio mybb \
  -- $(pwd)/.venv/bin/python -m mybb_mcp.server
```

Restart Claude Code to load the MCP server. Verify with `claude mcp get mybb`.

### 3b. Optional: Chrome DevTools MCP

The Chrome DevTools MCP server gives Claude browser control — navigate pages, take screenshots, inspect elements, and test CSS live. This is used heavily by the frontend agent for visual verification and template discovery.

```bash
# Install the Chrome DevTools MCP server
npm install -g @anthropic/claude-chrome-devtools-mcp

# Register with Claude Code (project scope)
claude mcp add --scope project --transport stdio chrome-devtools \
  -- npx @anthropic/claude-chrome-devtools-mcp --isolated

# Launch Chrome with remote debugging enabled
google-chrome --remote-debugging-port=9222
# or on macOS:
# /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222
```

Restart Claude Code and verify with `claude mcp get chrome-devtools`.

> **Note:** The `--isolated` flag avoids profile conflicts. You need Chrome/Chromium installed on your system.

### 3c. Optional: Scribe MCP (Development Audit Logging)

[Scribe MCP](https://github.com/CortaLabs/scribe_mcp) provides structured development logging, project tracking, and document management. All of the Claude Code agents in this repo are configured to use Scribe for audit trails.

Follow the installation instructions at **https://github.com/CortaLabs/scribe_mcp**.

**If you don't want Scribe:** Remove or modify the Scribe-specific instructions in `CLAUDE.md`, `AGENTS.md`, and the agent definitions in `.claude/agents/`. The MyBB MCP tools work independently of Scribe.

### Codex CLI Setup (MCP)

Do **not** change existing Claude Code instructions.

Register the MCP server with Codex:
```bash
codex mcp add mybb -- bash -lc 'cd /home/austin/projects/MyBB_Playground && exec mybb_mcp/.venv/bin/python -m mybb_mcp.server'

# Verify
codex mcp list
codex mcp get mybb
```

Repo workflow + constraints: `AGENTS.md`.

### 4. Complete MyBB Web Setup

Open http://localhost:8022/install/ and follow the MyBB installer:
- Use the database credentials shown at the end of `install.sh`
- Remove `TestForum/install/` after completing setup (or just delete `lock` file)

### 5. Start Building

```
"List all available template sets"
"Create a plugin called user_badges that displays badges based on post count"
"Show me the index template and add a welcome banner"
"What hooks are available for the member profile page?"
```

### Non-Interactive Mode

For CI/CD or scripted setups:

```bash
# Set environment variables, then run non-interactively
export MYBB_DB_NAME=mybb_dev
export MYBB_DB_USER=mybb_user
export MYBB_DB_PASS=secretpassword
export MYBB_INSTALL_MODE=fresh  # fresh, update, or skip

./install.sh -y
```

> **Full setup guide:** [docs/wiki/getting_started/installation.md](docs/wiki/getting_started/installation.md)

---

## Project Structure

```
MyBB_Playground/
├── mybb_mcp/                 # MCP Server (99 tools)
│   ├── server.py             # Server orchestration (116 lines)
│   ├── tools_registry.py     # Tool definitions (99 tools)
│   ├── handlers/             # Modular tool handlers
│   │   ├── dispatcher.py     # Central routing
│   │   ├── templates.py      # 8 template handlers
│   │   ├── themes.py         # 5 theme handlers
│   │   ├── plugins.py        # 15 plugin handlers
│   │   ├── content.py        # 16 forum/thread/post handlers
│   │   └── ...               # 14 modules total
│   ├── db/                   # Database operations
│   ├── sync/                 # Disk sync system
│   └── tools/                # Plugin scaffolding
│
├── mybb_sync/                # Disk Sync Working Directory
│   ├── template_sets/        # Templates as .html files
│   └── themes/               # Stylesheets as .css files
│
├── plugin_manager/           # Plugin Development Workspace
│   ├── plugins/public/       # Shared plugins
│   ├── plugins/private/      # Local-only plugins
│   └── themes/               # Theme workspaces
│
├── TestForum/                # MyBB Installation (downloaded by install.sh)
│   ├── inc/plugins/          # Deployed plugins
│   └── mcp_bridge.php        # PHP lifecycle bridge (from install_files/)
│
├── docs/wiki/                # Documentation (340KB)
│   ├── getting_started/      # Installation & quickstart
│   ├── mcp_tools/            # All 94 tools documented
│   ├── plugin_manager/       # Workspace & deployment
│   ├── architecture/         # System internals
│   └── best_practices/       # Development patterns
│
└── .scribe/                  # Development tracking
```

---

## MCP Tools (112)

Full reference: [docs/wiki/mcp_tools/index.md](docs/wiki/mcp_tools/index.md)

| Category | Tools | Description |
|----------|-------|-------------|
| [**Templates**](docs/wiki/mcp_tools/templates.md) | 9 | List, read, write, batch operations, find/replace, outdated detection |
| [**Themes**](docs/wiki/mcp_tools/themes_stylesheets.md) | 18 | Theme install/uninstall, stylesheet CRUD, XML import/export, template sets |
| [**Plugins**](docs/wiki/mcp_tools/plugins.md) | 15 | Full lifecycle — create, install, activate, hooks discovery |
| [**Workspace Git**](docs/wiki/mcp_tools/plugins.md#git-tools) | 7 | Init, GitHub create, status, commit, push, pull (plugins & themes) |
| [**Workspace Sync**](docs/wiki/mcp_tools/disk_sync.md) | 6 | Bidirectional sync with hash-based change detection |
| [**Forums/Threads/Posts**](docs/wiki/mcp_tools/forums_threads_posts.md) | 17 | Complete content management |
| [**Users/Moderation**](docs/wiki/mcp_tools/users_moderation.md) | 14 | User management, mod actions, logging |
| [**Search**](docs/wiki/mcp_tools/search.md) | 4 | Posts, threads, users, advanced search |
| [**Admin/Settings**](docs/wiki/mcp_tools/admin_settings.md) | 11 | Settings, cache control, statistics |
| [**Tasks**](docs/wiki/mcp_tools/tasks.md) | 6 | Scheduled task management |
| [**Server Orchestration**](docs/wiki/mcp_tools/orchestration.md) | 5 | Start, stop, restart, status, query logs |
| [**Database**](docs/wiki/mcp_tools/database.md) | 1 | Read-only SQL queries |

### Tool Examples

```python
# Create a plugin with templates and settings
mybb_create_plugin(
    codename="user_badges",
    name="User Badges",
    description="Display badges based on post count",
    hooks=["postbit", "member_profile"],
    has_settings=True,
    has_templates=True
)

# Install and activate (runs actual PHP lifecycle)
mybb_plugin_install(codename="user_badges")

# Edit templates via disk sync
mybb_sync_export_templates("Default Templates")
# Now edit files in mybb_sync/template_sets/Default Templates/
# Watcher auto-syncs changes to database

# Search forum content
mybb_search_advanced(
    query="badge",
    content_type="both",
    forums=[2, 5],
    limit=25
)

# Server management
mybb_server_status()                         # Check if server running
mybb_server_start()                          # Start PHP dev server
mybb_server_logs(errors_only=True)           # View PHP errors only
mybb_server_logs(since_minutes=5, limit=100) # Last 5 minutes
```

---

## Development Workflows

### Plugin Development

```
plugin_manager/plugins/public/
└── my_plugin/
    ├── meta.json                    # Plugin metadata
    ├── inc/plugins/my_plugin.php    # Main plugin file
    └── inc/languages/english/       # Language files
```

1. **Create:** `mybb_create_plugin(codename="my_plugin", ...)`
2. **Develop:** Edit files in workspace
3. **Deploy:** `mybb_plugin_install(codename="my_plugin")`
4. **Iterate:** `mybb_workspace_sync(codename="my_plugin", type="plugin")` for quick syncs

> **Full guide:** [docs/wiki/plugin_manager/index.md](docs/wiki/plugin_manager/index.md)

### Theme Development

```
plugin_manager/themes/public/
└── my_theme/
    ├── meta.json              # Theme metadata
    ├── stylesheets/           # CSS files (synced to database)
    │   ├── global.css
    │   └── custom.css
    ├── templates/             # Template overrides (organized by group)
    │   ├── Header Templates/
    │   └── Footer Templates/
    └── jscripts/              # JavaScript (deployed to TestForum)
```

1. **Install:** `mybb_theme_install(codename="my_theme", set_default=True)`
2. **Export from DB:** `mybb_workspace_sync(codename="my_theme", type="theme", direction="from_db")`
3. **Edit:** Modify stylesheets/templates in workspace
4. **Sync to DB:** `mybb_workspace_sync(codename="my_theme", type="theme")` — only changed files sync

**Key theme tools:**
- `mybb_theme_install` / `mybb_theme_uninstall` — Full lifecycle management
- `mybb_workspace_sync` — Hash-based sync (only changed files)
- `mybb_theme_export_xml` / `mybb_theme_import_xml` — MyBB-compatible XML format

### Private Plugins & Git Integration

Private plugins use **nested git repositories** — each plugin has its own independent repo:

```
plugin_manager/plugins/
├── public/               # Default plugins (tracked in parent repo)
│   ├── cortex/
│   └── dice_roller/
└── private/              # Private plugins (nested git repos)
    └── my_plugin/
        └── .git/         # Independent repo
```

**Git workflow via MCP tools:**

```python
# PLUGINS - type defaults to "plugin", use visibility for public/private
mybb_workspace_git_init(codename="my_plugin", visibility="private")
mybb_workspace_github_create(codename="my_plugin", repo_visibility="private")
mybb_workspace_git_commit(codename="my_plugin", message="Add feature X")
mybb_workspace_git_push(codename="my_plugin")

# THEMES - type="theme" is REQUIRED, no visibility param
mybb_workspace_git_init(codename="my_theme", type="theme")
mybb_workspace_github_create(codename="my_theme", type="theme", repo_visibility="public")
mybb_workspace_git_commit(codename="my_theme", type="theme", message="Update styles")
mybb_workspace_git_push(codename="my_theme", type="theme")
```

**Workspace vs parent repo:**
- **Parent repo (MyBB Playground):** CLI git for MCP server, scripts, docs
- **Plugin/theme workspaces:** MCP git tools (`mybb_workspace_git_*`) with `type` parameter

### Template/Stylesheet Editing

```bash
# Export templates to disk
mybb_sync_export_templates("Default Templates")

# Start file watcher
mybb_sync_start_watcher()

# Edit files in your editor
# mybb_sync/template_sets/Default Templates/Header Templates/header.html

# Watcher auto-syncs to database
```

> **Full guide:** [docs/wiki/architecture/disk_sync.md](docs/wiki/architecture/disk_sync.md)

---

## Documentation

| Section | Description |
|---------|-------------|
| [**Getting Started**](docs/wiki/getting_started/index.md) | Installation, quickstart tutorial |
| [**MCP Tools Reference**](docs/wiki/mcp_tools/index.md) | All 112 tools with parameters and examples |
| [**Plugin Manager**](docs/wiki/plugin_manager/index.md) | Workspace, deployment, PHP lifecycle |
| [**Architecture**](docs/wiki/architecture/index.md) | MCP server, disk sync, configuration |
| [**Best Practices**](docs/wiki/best_practices/index.md) | Plugin/theme patterns, security |

---

## Configuration

### Environment (`.env`)

Generated automatically by `install.sh`. You can edit manually if needed:

```bash
# Database
MYBB_DB_HOST=localhost
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=your_password
MYBB_DB_PREFIX=mybb_

# Server
MYBB_PORT=8022
MYBB_ROOT=/path/to/MyBB_Playground/TestForum
MYBB_URL=http://localhost:8022
```

### Forge Config (`.mybb-forge.yaml`)

Developer settings and defaults for plugin creation:

```yaml
# Developer metadata (auto-fills plugin meta.json)
developer:
  name: "Your Name"
  website: "https://yoursite.com"
  email: "you@example.com"

# Defaults for new plugins
defaults:
  compatibility: "18*"
  license: "MIT"
  visibility: "public"

# GitHub settings
github:
  repo_prefix: "mybb_playground_"  # Prefix for GitHub repos

# Default plugins to deploy on fresh install
default_plugins:
  - cortex        # Secure template conditionals
  - dice_roller   # BBCode dice rolling
```

> **Full configuration guide:** [docs/wiki/architecture/configuration.md](docs/wiki/architecture/configuration.md)

---

## Requirements

| Requirement | Version | Notes |
|-------------|---------|-------|
| **OS** | Linux, WSL, macOS | Windows native not tested |
| **Python** | 3.10+ | For MCP server |
| **PHP** | 8.0+ | Installed by setup script |
| **MariaDB/MySQL** | 10.x+ | Installed by setup script |
| **Claude Code** | Latest | With MCP support |

---

## Why MyBB Playground?

**MyBB is 15+ years old** — it's stable, battle-tested forum software with a dedicated community. But development is challenging:

- PHP 8 compatibility issues
- Complex hook system to learn
- Template inheritance confusing
- Manual file management tedious

**MyBB Playground bridges this gap** by giving AI the tools to work with MyBB properly:

- Understands MyBB's architecture (hooks, templates, settings)
- Follows MyBB coding standards automatically
- Handles lifecycle functions correctly
- Manages file deployment and tracking

We're not trying to modernize MyBB — we're making it easier to work with.

---

## Contributing

Contributions welcome! This is an open-source project for the MyBB community.

1. Fork the repository
2. Create a feature branch
3. Follow the [Scribe Protocol](CLAUDE.md#scribe-orchestration-protocol) for tracking
4. Submit a pull request

---

## License

MIT License — See [LICENSE](mybb_mcp/LICENSE) for details.

---

<div align="center">

**Built with Claude Code and the [Model Context Protocol](https://modelcontextprotocol.io/)**

[Documentation](docs/wiki/index.md) •
[MCP Tools](docs/wiki/mcp_tools/index.md) •
[Report Issues](https://github.com/CortaLabs/MyBB_Playground/issues)

</div>
