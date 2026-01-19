---
id: private_plugin_infra-spec
title: Private Plugin Infrastructure - SPEC
doc_name: SPEC
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
# Private Plugin Infrastructure - SPEC

## Problem

MyBB_Playground is PUBLIC. Private plugins need to:
1. Live in same workspace for dev convenience
2. Push to PRIVATE repos on GitHub
3. Never leak into public repo history

## Solution: Nested Git Repos

```
MyBB_Playground/                          (PUBLIC GitHub repo)
├── .mybb-forge.yaml                      (config: repo naming, org)
├── plugin_manager/plugins/
│   ├── public/                           (tracked in parent)
│   └── private/                          (gitignored by parent)
│       ├── .registry.yaml                (manifest of private plugins)
│       └── invite_system/                (PRIVATE GitHub repo, nested)
│           ├── .git/                     → github.com/CortaLabs/mybb_playground_invite_system
│           └── ...plugin files...
```

## Config Addition: `.mybb-forge.yaml`

```yaml
private_repos:
  prefix: "mybb_playground_"    # Repo name prefix
  org: "CortaLabs"              # GitHub org/user
  auth_method: "ssh"            # ssh or https_gh
```

## Registry: `plugin_manager/plugins/private/.registry.yaml`

```yaml
plugins:
  invite_system:
    repo: git@github.com:CortaLabs/mybb_playground_invite_system.git
    created: 2026-01-19
    version: 1.0.0
```

## Git Auth Options

### SSH Keys (recommended)
```bash
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub  # Add to GitHub Settings → SSH Keys
```

### GitHub CLI
```bash
sudo apt install gh
gh auth login
```

## New MCP Tools

| Tool | Purpose |
|------|--------|
| `mybb_private_init` | Init nested git, set remote, add to registry |
| `mybb_private_commit` | Commit changes in private plugin |
| `mybb_private_push` | Push to private remote |
| `mybb_private_status` | Git status of all private plugins |

## Install Script: `install.sh`

Production-grade interactive installer. Features:

### OS Detection
- Ubuntu/Debian (apt)
- macOS (Homebrew)
- Fedora/RHEL (dnf)
- Arch (pacman)
- WSL detection

### Previous Installation Handling
- Detects .env, TestForum/, database
- Options: Update/repair, Fresh install, Skip, Exit
- Confirmation prompt for destructive actions

### Interactive Prompts
- Database name, user, password (with generated defaults)
- Server port
- Git authentication method

### Git Authentication Setup
- SSH key generation + instructions to add to GitHub
- GitHub CLI installation + login flow
- Skip option for later configuration

### Dependency Installation
- PHP 8+ with extensions (mysql, gd, mbstring, xml, curl, zip)
- MariaDB server + client
- git, curl, unzip

### MyBB Bootstrap
- Downloads MyBB 1.8.38 from GitHub releases
- Extracts to TestForum/
- Sets correct permissions
- Preserves existing data in update mode

### Output Files
- `.env` - Database credentials, paths, ports
- `.mybb-forge.env` - Private repo URLs (template)

### Flow
```
1. Banner
2. OS Detection
3. Previous Install Check → Prompt action
4. Install Dependencies (optional)
5. Database Setup
6. MyBB Download/Extract
7. Git Auth Setup
8. Save Configuration
9. Summary + Next Steps
```

## Phases

1. **Install Script** - `install.sh` with full features (DONE - needs review)
2. **Research** - Best practices, edge cases, error handling
3. **Architect** - Solidify design, handle edge cases
4. **Private Plugin Automation** - `mybb_create_plugin` auto-init for private
5. **MCP Tools** - Add commit/push/status tools
6. **Private Plugin Registry** - Clone on fresh install
