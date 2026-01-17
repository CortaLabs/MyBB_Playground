# MyBB MCP Server

**AI-assisted MyBB forum development via the Model Context Protocol.**

An open-source MCP server that connects Claude Code (and other MCP clients) to your MyBB installation, enabling AI-assisted plugin development, theme customization, and template management.

## Features

- **Template Management** — List, read, and write MyBB templates with full inheritance support (master → custom)
- **Theme & Stylesheet Management** — Edit CSS with automatic cache refresh
- **Plugin Scaffolding** — Generate complete plugin structures with hooks, settings, templates, and database tables
- **Hook Reference** — Browse 50+ MyBB hooks organized by category
- **Plugin Analysis** — Analyze existing plugins to understand their structure
- **Database Exploration** — Execute read-only SQL queries for exploration

## Requirements

- Python 3.10+
- MyBB 1.8.x installation
- MySQL/MariaDB database
- Claude Code (or any MCP-compatible client)

## Installation

### 1. Clone and Install

```bash
cd /path/to/your/project
git clone https://github.com/your-org/mybb-mcp.git mybb_mcp
cd mybb_mcp

# Create virtual environment and install
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. Configure Environment

Create a `.env` file in your project root (parent of `mybb_mcp/`):

```bash
# MyBB Database Configuration
MYBB_DB_HOST=localhost
MYBB_DB_PORT=3306
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=your_password_here
MYBB_DB_PREFIX=mybb_

# MyBB Installation
MYBB_ROOT=/path/to/your/mybb/installation
MYBB_URL=http://localhost:8022
MYBB_PORT=8022
```

### 3. Add to Claude Code

Use the `claude mcp add` command to register the server:

```bash
# Add the MyBB MCP server (user scope - available across all projects)
claude mcp add --scope user --transport stdio mybb \
  -- /path/to/mybb_mcp/.venv/bin/python -m mybb_mcp.server

# Or for project-local scope (default)
claude mcp add --transport stdio mybb \
  -- /path/to/mybb_mcp/.venv/bin/python -m mybb_mcp.server
```

**With environment variables inline:**

```bash
claude mcp add --transport stdio \
  --env MYBB_DB_HOST=localhost \
  --env MYBB_DB_NAME=mybb_dev \
  --env MYBB_DB_USER=mybb_user \
  --env MYBB_DB_PASS=your_password \
  --env MYBB_ROOT=/path/to/mybb \
  mybb -- /path/to/mybb_mcp/.venv/bin/python -m mybb_mcp.server
```

### 4. Verify Installation

```bash
# List configured MCP servers
claude mcp list

# Check server details
claude mcp get mybb

# In Claude Code, check status
/mcp
```

## Available Tools

### Template Tools

| Tool | Description |
|------|-------------|
| `mybb_list_template_sets` | List all template sets (Default Templates, custom sets) |
| `mybb_list_templates` | List templates with optional filtering by set ID or search term |
| `mybb_read_template` | Read template content, shows both master (sid=-2) and custom versions |
| `mybb_write_template` | Create or update templates with automatic inheritance handling |
| `mybb_list_template_groups` | List template groups (calendar, forum, usercp, etc.) |

### Theme & Style Tools

| Tool | Description |
|------|-------------|
| `mybb_list_themes` | List all themes with parent/child relationships |
| `mybb_list_stylesheets` | List CSS files, optionally filtered by theme |
| `mybb_read_stylesheet` | Read stylesheet CSS content |
| `mybb_write_stylesheet` | Update stylesheet with automatic cache refresh |

### Plugin Development Tools

| Tool | Description |
|------|-------------|
| `mybb_list_plugins` | List all plugins in the `inc/plugins/` directory |
| `mybb_read_plugin` | Read a plugin's PHP source code |
| `mybb_create_plugin` | Scaffold a new plugin with hooks, settings, templates, database |
| `mybb_list_hooks` | Browse MyBB hooks by category (index, showthread, member, admin, etc.) |
| `mybb_analyze_plugin` | Analyze an existing plugin's structure and hooks |

### Database Tools

| Tool | Description |
|------|-------------|
| `mybb_db_query` | Execute read-only SELECT queries for exploration |

## Usage Examples

### Create a New Plugin

Ask Claude Code:

```
Create a MyBB plugin called "User Badges" that:
- Displays custom badges on user profiles
- Has an ACP setting to enable/disable
- Hooks into member_profile_end
- Stores badge data in a custom database table
```

Claude will use `mybb_create_plugin` to scaffold the complete plugin structure.

### Modify a Template

```
Show me the header template and add a custom announcement bar at the top
```

Claude will use `mybb_read_template` to fetch the template, then `mybb_write_template` to save changes.

### Explore Available Hooks

```
What hooks are available for modifying the thread display page?
```

Claude will use `mybb_list_hooks` with `category: showthread` to show relevant hooks.

### Analyze an Existing Plugin

```
Analyze the hello.php plugin and explain how it works
```

Claude will use `mybb_analyze_plugin` and `mybb_read_plugin` to examine the plugin structure.

## Template Inheritance

MyBB uses a template inheritance system that this MCP server fully supports:

| SID | Type | Description |
|-----|------|-------------|
| `-2` | Master | Base templates, source of truth |
| `-1` | Global | Shared across all template sets |
| `1+` | Custom | Template set-specific overrides |

When you write a template:
- If updating a master template (sid=-2), it updates the base
- If creating a custom template for a set, it creates an override
- Custom templates appear green in MyBB ACP (indicating modification)

## Configuration Options

The server reads configuration from environment variables or a `.env` file:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYBB_DB_HOST` | `localhost` | Database host |
| `MYBB_DB_PORT` | `3306` | Database port |
| `MYBB_DB_NAME` | `mybb_dev` | Database name |
| `MYBB_DB_USER` | `mybb_user` | Database user |
| `MYBB_DB_PASS` | *(required)* | Database password |
| `MYBB_DB_PREFIX` | `mybb_` | Table prefix |
| `MYBB_ROOT` | Auto-detected | Path to MyBB installation |
| `MYBB_URL` | `http://localhost:8022` | MyBB URL (for cache refresh) |
| `MYBB_PORT` | `8022` | MyBB port |

## Managing the MCP Server

```bash
# List all MCP servers
claude mcp list

# Get details about the mybb server
claude mcp get mybb

# Remove the server
claude mcp remove mybb

# Check status in Claude Code
/mcp
```

## Project Structure

```
mybb_mcp/
├── __init__.py          # Package init
├── server.py            # Main MCP server with all tool handlers
├── config.py            # Configuration loader (env vars, .env file)
├── db/
│   ├── __init__.py
│   └── connection.py    # MySQL database wrapper
├── tools/
│   ├── __init__.py
│   └── plugins.py       # Plugin scaffolding + hooks reference
├── pyproject.toml       # Package configuration
└── README.md            # This file
```

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest
```

### Testing Database Connection

```bash
source .venv/bin/activate
python -c "
from mybb_mcp.config import load_config
from mybb_mcp.db import MyBBDatabase

config = load_config()
db = MyBBDatabase(config.db)
print('Template sets:', db.list_template_sets())
print('Themes:', db.list_themes())
db.close()
"
```

## Companion Tools

This MCP server is part of the **MyBB Playground** project:

- **TestForum/** — Local MyBB 1.8.x installation for development
- **vscode-mybbbridge/** — VSCode extension for direct template/style editing
- **start_mybb.sh** — Script to start the development server

## Security Considerations

- Database credentials are stored in `.env` (gitignored)
- The `mybb_db_query` tool only allows SELECT statements
- Plugin files are written to the MyBB `inc/plugins/` directory
- No remote code execution or shell access is provided

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See LICENSE file for details.

---

**Built for the MyBB community** — Making forum development accessible with AI assistance.
