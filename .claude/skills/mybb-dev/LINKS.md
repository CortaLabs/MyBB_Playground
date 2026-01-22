# MyBB Development Documentation Links

A curated collection of links to relevant documentation. **Update this file** when you find useful docs or create new documentation.

---

## Core Project Documentation

### Essential Reading
| Document | Purpose | Path |
|----------|---------|------|
| **CLAUDE.md** | Full project instructions, rules, architecture | [CLAUDE.md](../../../CLAUDE.md) |
| **AGENTS.md** | Agent operational framework, constraints | [AGENTS.md](../../../AGENTS.md) |
| **.env** | Environment variables (DB, paths) | `.env` (gitignored) |

### Configuration
| Document | Purpose | Path |
|----------|---------|------|
| **.mybb-forge.yaml** | Developer metadata, defaults | [.mybb-forge.yaml](../../../.mybb-forge.yaml) |
| **.mybb-forge.env** | Private remotes (gitignored) | `.mybb-forge.env` |

---

## Wiki Documentation

### Getting Started
| Document | Purpose |
|----------|---------|
| [Installation Guide](../../../docs/wiki/getting_started/installation.md) | First-time setup |
| [Quick Start Tutorial](../../../docs/wiki/getting_started/quickstart.md) | Create first plugin |
| [Prerequisites](../../../docs/wiki/getting_started/prerequisites.md) | System requirements |

### MCP Tools Reference
| Document | Tools Covered |
|----------|---------------|
| [Index](../../../docs/wiki/mcp_tools/index.md) | Overview of all 100+ tools |
| [Templates](../../../docs/wiki/mcp_tools/templates.md) | 9 template tools |
| [Themes & Stylesheets](../../../docs/wiki/mcp_tools/themes_stylesheets.md) | 6 theme/style tools |
| [Plugins](../../../docs/wiki/mcp_tools/plugins.md) | 15 plugin tools |
| [Forums, Threads, Posts](../../../docs/wiki/mcp_tools/forums_threads_posts.md) | 17 content tools |
| [Users & Moderation](../../../docs/wiki/mcp_tools/users_moderation.md) | 14 user/mod tools |
| [Search](../../../docs/wiki/mcp_tools/search.md) | 4 search tools |
| [Admin & Settings](../../../docs/wiki/mcp_tools/admin_settings.md) | 11 admin tools |
| [Tasks](../../../docs/wiki/mcp_tools/tasks.md) | 6 scheduled task tools |
| [Disk Sync](../../../docs/wiki/mcp_tools/disk_sync.md) | 5 sync tools |
| [Languages](../../../docs/wiki/mcp_tools/languages.md) | 3 language validation tools |
| [Database](../../../docs/wiki/mcp_tools/database.md) | 1 query tool |

### Plugin Manager
| Document | Purpose |
|----------|---------|
| [Index](../../../docs/wiki/plugin_manager/index.md) | Plugin Manager overview |
| [Workspace Structure](../../../docs/wiki/plugin_manager/workspace.md) | Directory layout, meta.json |
| [Deployment](../../../docs/wiki/plugin_manager/deployment.md) | Install/uninstall workflow |
| [PHP Lifecycle](../../../docs/wiki/plugin_manager/lifecycle.md) | _install, _activate, etc. |

### Architecture
| Document | Purpose |
|----------|---------|
| [Index](../../../docs/wiki/architecture/index.md) | System architecture overview |
| [MCP Server](../../../docs/wiki/architecture/mcp_server.md) | Server internals |
| [Disk Sync](../../../docs/wiki/architecture/disk_sync.md) | Template/stylesheet sync system |
| [Configuration](../../../docs/wiki/architecture/configuration.md) | Config loading |

### Best Practices
| Document | Purpose |
|----------|---------|
| [Index](../../../docs/wiki/best_practices/index.md) | Development guidelines overview |
| [Plugin Development](../../../docs/wiki/best_practices/plugin_development.md) | Plugin patterns, security |
| [Theme Development](../../../docs/wiki/best_practices/theme_development.md) | Theme/stylesheet patterns |

---

## Agent Definitions

Specialized agents with deep MyBB knowledge:

| Agent | Expertise | Path |
|-------|-----------|------|
| mybb-research-analyst | MCP tools, plugin/template analysis | [.claude/agents/mybb-research-analyst.md](../agents/mybb-research-analyst.md) |
| mybb-architect | System design, phase planning | [.claude/agents/mybb-architect.md](../agents/mybb-architect.md) |
| mybb-coder | PHP implementation, Plugin Manager | [.claude/agents/mybb-coder.md](../agents/mybb-coder.md) |
| mybb-review-agent | Quality assurance, compliance | [.claude/agents/mybb-review-agent.md](../agents/mybb-review-agent.md) |
| mybb-bug-hunter | Debugging MyBB issues | [.claude/agents/mybb-bug-hunter.md](../agents/mybb-bug-hunter.md) |
| mybb-plugin-specialist | Plugin lifecycle, hooks, security | [.claude/agents/mybb-plugin-specialist.md](../agents/mybb-plugin-specialist.md) |
| mybb-template-specialist | Templates, Cortex, disk sync | [.claude/agents/mybb-template-specialist.md](../agents/mybb-template-specialist.md) |

---

## External MyBB Documentation

### Official Docs
| Resource | URL |
|----------|-----|
| MyBB Plugin Development | https://docs.mybb.com/1.8/development/plugins/ |
| MyBB Hooks Reference | https://docs.mybb.com/1.8/development/plugins/hooks/ |
| MyBB Database Schema | https://docs.mybb.com/1.8/development/database/ |
| MyBB Template System | https://docs.mybb.com/1.8/development/templates/ |

### Community Resources
| Resource | URL |
|----------|-----|
| MyBB Community Forums | https://community.mybb.com/ |
| MyBB Extend (Plugins) | https://community.mybb.com/mods.php |

---

## Scribe Documentation

| Document | Purpose |
|----------|---------|
| [Scribe Usage Guide](../../../docs/Scribe_Usage.md) | How to use Scribe for logging |
| [PROTOCOL Spec](../../../.scribe/docs/dev_plans/mybb_dev_protocol/PROTOCOL_SPEC.md) | 6-phase development workflow |

---

## Bug Documentation

| Document | Purpose |
|----------|---------|
| [Bug Index](../../../docs/bugs/INDEX.md) | Known bugs and fixes |

---

## Add Links Below

When you find or create useful documentation, add it here:

### Recently Added
<!-- Add new links here with date -->

---
