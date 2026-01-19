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
[85+ MCP Tools](docs/wiki/mcp_tools/index.md) •
[Plugin Manager](docs/wiki/plugin_manager/index.md)

</div>

---

## What is MyBB Playground?

MyBB Playground connects **Claude Code** directly to your MyBB installation through **85+ MCP tools**. Instead of manually editing PHP files, writing SQL queries, and navigating the admin panel, you can develop plugins and themes using natural language.

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
| **85+ MCP Tools** | Full MyBB API coverage — templates, themes, plugins, forums, users, moderation, settings |
| **Disk Sync** | Edit templates/stylesheets in your editor, auto-syncs to database |
| **Plugin Manager** | Structured workspace for plugin development with deployment tracking |
| **PHP Bridge** | Execute actual PHP lifecycle functions (_install, _activate, etc.) |
| **AI-Native** | Built specifically for Claude Code integration |

---

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/CortaLabs/MyBB_Playground.git
cd MyBB_Playground

# Install PHP, MariaDB, create database (Ubuntu/Debian/WSL)
./setup_dev_env.sh

# Start MyBB server on port 8022
./start_mybb.sh
```

Complete MyBB installation at http://localhost:8022/install/

### 2. Install MCP Server

```bash
cd mybb_mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Connect to Claude Code

```bash
# Add MCP server (run from mybb_mcp directory)
claude mcp add --scope user --transport stdio mybb \
  -- $(pwd)/.venv/bin/python -m mybb_mcp.server
```

Restart Claude Code to load the MCP server.

### 4. Start Building

```
"List all available template sets"
"Create a plugin called user_badges that displays badges based on post count"
"Show me the index template and add a welcome banner"
"What hooks are available for the member profile page?"
```

> **Full setup guide:** [docs/wiki/getting_started/installation.md](docs/wiki/getting_started/installation.md)

---

## Project Structure

```
MyBB_Playground/
├── mybb_mcp/                 # MCP Server (85+ tools)
│   ├── server.py             # Server orchestration (116 lines)
│   ├── tools_registry.py     # Tool definitions (85 tools)
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
├── TestForum/                # MyBB Installation
│   ├── inc/plugins/          # Deployed plugins
│   └── mcp_bridge.php        # PHP lifecycle bridge
│
├── docs/wiki/                # Documentation (340KB)
│   ├── getting_started/      # Installation & quickstart
│   ├── mcp_tools/            # All 85+ tools documented
│   ├── plugin_manager/       # Workspace & deployment
│   ├── architecture/         # System internals
│   └── best_practices/       # Development patterns
│
└── .scribe/                  # Development tracking
```

---

## MCP Tools (85+)

Full reference: [docs/wiki/mcp_tools/index.md](docs/wiki/mcp_tools/index.md)

| Category | Tools | Description |
|----------|-------|-------------|
| [**Templates**](docs/wiki/mcp_tools/templates.md) | 9 | List, read, write, batch operations, find/replace, outdated detection |
| [**Themes**](docs/wiki/mcp_tools/themes_stylesheets.md) | 6 | Theme management, stylesheet CRUD, theme creation |
| [**Plugins**](docs/wiki/mcp_tools/plugins.md) | 15 | Full lifecycle — create, install, activate, hooks discovery |
| [**Forums/Threads/Posts**](docs/wiki/mcp_tools/forums_threads_posts.md) | 17 | Complete content management |
| [**Users/Moderation**](docs/wiki/mcp_tools/users_moderation.md) | 14 | User management, mod actions, logging |
| [**Search**](docs/wiki/mcp_tools/search.md) | 4 | Posts, threads, users, advanced search |
| [**Admin/Settings**](docs/wiki/mcp_tools/admin_settings.md) | 11 | Settings, cache control, statistics |
| [**Tasks**](docs/wiki/mcp_tools/tasks.md) | 6 | Scheduled task management |
| [**Disk Sync**](docs/wiki/mcp_tools/disk_sync.md) | 5 | Export, import, file watcher control |
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
4. **Iterate:** Changes tracked, easy rollback

> **Full guide:** [docs/wiki/plugin_manager/index.md](docs/wiki/plugin_manager/index.md)

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
| [**MCP Tools Reference**](docs/wiki/mcp_tools/index.md) | All 85+ tools with parameters and examples |
| [**Plugin Manager**](docs/wiki/plugin_manager/index.md) | Workspace, deployment, PHP lifecycle |
| [**Architecture**](docs/wiki/architecture/index.md) | MCP server, disk sync, configuration |
| [**Best Practices**](docs/wiki/best_practices/index.md) | Plugin/theme patterns, security |

---

## Configuration

Create `.env` in project root:

```bash
# Database
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=your_password
MYBB_DB_PREFIX=mybb_

# Paths
MYBB_ROOT=/path/to/MyBB_Playground/TestForum
MYBB_URL=http://localhost:8022
MYBB_PORT=8022
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
