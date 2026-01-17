# MyBB Playground

**AI-Assisted MyBB Development Toolkit**

A complete development environment for building MyBB plugins, themes, and templates with AI assistance. This project provides MCP (Model Context Protocol) tools that connect Claude Code directly to your MyBB installation.

## What's Included

```
MyBB_Playground/
├── mybb_mcp/           # MCP Server for Claude Code integration
├── TestForum/          # Local MyBB 1.8.x installation
├── vscode-mybbbridge/  # VSCode extension (legacy, reference)
├── setup_dev_env.sh    # One-time environment setup
├── start_mybb.sh       # Start development server
└── stop_mybb.sh        # Stop development server
```

## Quick Start

### 1. Set Up Development Environment

```bash
# Clone the repository
git clone https://github.com/CortaLabs/MyBB_Playground.git
cd MyBB_Playground

# Run setup (installs PHP, MariaDB, creates database)
./setup_dev_env.sh

# Start MyBB server
./start_mybb.sh
```

Open http://localhost:8022/install/ and complete the MyBB installation.

### 2. Install the MCP Server

```bash
cd mybb_mcp
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 3. Add to Claude Code

```bash
claude mcp add --scope user --transport stdio mybb \
  -- $(pwd)/.venv/bin/python -m mybb_mcp.server
```

### 4. Start Building

In Claude Code, you can now:

```
"Create a MyBB plugin that adds user reputation badges"
"Show me the header template and add a custom banner"
"What hooks are available for the member profile page?"
"Analyze the hello.php example plugin"
```

## MCP Tools Available

| Category | Tools |
|----------|-------|
| **Templates** | `mybb_list_template_sets`, `mybb_list_templates`, `mybb_read_template`, `mybb_write_template`, `mybb_list_template_groups` |
| **Themes** | `mybb_list_themes`, `mybb_list_stylesheets`, `mybb_read_stylesheet`, `mybb_write_stylesheet` |
| **Plugins** | `mybb_list_plugins`, `mybb_read_plugin`, `mybb_create_plugin`, `mybb_list_hooks`, `mybb_analyze_plugin` |
| **Database** | `mybb_db_query` (read-only) |

## Use Cases

### Plugin Development

Ask Claude to scaffold complete plugins with:
- Hook registrations
- Settings in Admin CP
- Custom templates
- Database tables
- Language files

### Theme Customization

- Read and modify templates with inheritance awareness
- Edit stylesheets with automatic cache refresh
- Explore template groups and structure

### Learning MyBB

- Analyze existing plugins to understand patterns
- Browse available hooks by category
- Query the database structure

## Configuration

The MCP server reads from a `.env` file in the project root:

```bash
MYBB_DB_HOST=localhost
MYBB_DB_NAME=mybb_dev
MYBB_DB_USER=mybb_user
MYBB_DB_PASS=your_password
MYBB_DB_PREFIX=mybb_
MYBB_ROOT=/path/to/TestForum
MYBB_URL=http://localhost:8022
```

## Project Components

### mybb_mcp/

The main MCP server. See [mybb_mcp/README.md](mybb_mcp/README.md) for detailed documentation.

### TestForum/

A clean MyBB 1.8.x installation for development. Not committed to git (download from mybb.com).

### vscode-mybbbridge/

Legacy VSCode extension for direct MyBB integration. Provides:
- Template editing with database sync
- Stylesheet management with cache refresh
- PHP bridge files for cache clearing

This is kept as reference for the MCP server implementation.

## Requirements

- **OS**: Linux (WSL supported), macOS
- **Python**: 3.10+
- **PHP**: 8.0+ (installed by setup script)
- **Database**: MariaDB/MySQL (installed by setup script)
- **AI**: Claude Code with MCP support

## Contributing

This is an open-source project for the MyBB community. Contributions welcome!

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License - See [LICENSE](mybb_mcp/LICENSE) for details.

---

**Making MyBB development accessible with AI assistance.**
