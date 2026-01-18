# MyBB Playground Wiki

Welcome to the MyBB Playground documentation. This wiki provides comprehensive reference material for the MyBB MCP server, Plugin Manager, and development tools.

## What is MyBB Playground?

MyBB Playground is an AI-assisted MyBB development toolkit that provides:
- **85+ MCP Tools** for interacting with MyBB installations via Claude Code
- **Plugin Manager** with workspace management and PHP lifecycle integration
- **Disk Sync Service** for bidirectional template/stylesheet synchronization
- **Development Environment** with local MyBB instance and testing tools

This wiki documents all components with code-accurate reference material, usage examples, and best practices.

## Documentation Sections

### 🚀 [Getting Started](getting_started/index.md)
New to MyBB Playground? Start here to install, configure, and run your first commands.

**Contents:**
- [Installation Guide](getting_started/installation.md) - Prerequisites and setup instructions
- [Quickstart Guide](getting_started/quickstart.md) - First steps tutorial with common tasks

### 🔧 [MCP Tools Reference](mcp_tools/index.md)
Complete reference for all 85+ MCP tools available in the server.

**Tool Categories:**
- [Templates](mcp_tools/templates.md) - Template management (9 tools)
- [Themes & Stylesheets](mcp_tools/themes_stylesheets.md) - Theme and stylesheet tools (6 tools)
- [Plugins](mcp_tools/plugins.md) - Plugin development and management (15 tools)
- [Forums, Threads & Posts](mcp_tools/forums_threads_posts.md) - Content management (17 tools)
- [Users & Moderation](mcp_tools/users_moderation.md) - User and moderation tools (14 tools)
- [Search](mcp_tools/search.md) - Search functionality (4 tools)
- [Admin & Settings](mcp_tools/admin_settings.md) - Administrative tools (11 tools)
- [Scheduled Tasks](mcp_tools/tasks.md) - Task management (5 tools)
- [Disk Sync](mcp_tools/disk_sync.md) - File synchronization (5 tools)
- [Database](mcp_tools/database.md) - Direct database queries (1 tool)

### 🎯 [Plugin Manager](plugin_manager/index.md)
Learn how to use the Plugin Manager workspace system for plugin development.

**Contents:**
- [Workspace Structure](plugin_manager/workspace.md) - Directory layout and organization
- [File Deployment](plugin_manager/deployment.md) - Manifest system and deployment process
- [Plugin Lifecycle](plugin_manager/lifecycle.md) - PHP Bridge integration and lifecycle hooks
- [Project Database](plugin_manager/database.md) - SQLite tracking and metadata

### 🏗️ [Architecture](architecture/index.md)
Understand the internal architecture of MyBB Playground components.

**Contents:**
- [MCP Server Internals](architecture/mcp_server.md) - Server structure and tool registration
- [Disk Sync System](architecture/disk_sync.md) - Bidirectional synchronization architecture
- [Configuration Management](architecture/configuration.md) - Environment variables and config loading

### 📚 [Best Practices](best_practices/index.md)
MyBB-specific development patterns and security guidelines.

**Contents:**
- [Plugin Development](best_practices/plugin_development.md) - MyBB plugin patterns and conventions
- [Theme Development](best_practices/theme_development.md) - Theme and stylesheet best practices
- [Security Guidelines](best_practices/security.md) - Security considerations for MyBB development

## Quick Links

- **[CLAUDE.md](/CLAUDE.md)** - Quick setup and orchestration protocol
- **[Research Documents](.scribe/docs/dev_plans/mybb_playground_docs/research/)** - Detailed code analysis
- **[MyBB Official Docs](https://docs.mybb.com/1.8/)** - MyBB core documentation

## How to Use This Wiki

1. **New Users:** Start with [Getting Started](getting_started/index.md)
2. **Reference Lookup:** Use [MCP Tools Reference](mcp_tools/index.md) for specific tools
3. **Plugin Development:** Combine [Plugin Manager](plugin_manager/index.md) + [Best Practices](best_practices/index.md)
4. **System Understanding:** Read [Architecture](architecture/index.md) section

## Contributing

This wiki is maintained alongside the codebase. When code changes:
1. Update relevant documentation files
2. Verify all code examples still work
3. Update version numbers and timestamps

**Documentation Standards:**
- All content must be factually accurate to code
- Code examples must be copy-paste ready
- Parameter tables must include types and defaults
- No placeholder content or speculation

---

*Last Updated: 2026-01-18*
