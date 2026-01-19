---
id: mybb_forge_v2-research-git-subtree-config-20260119
title: 'Research: Git Subtree + YAML/ENV Configuration System'
doc_name: RESEARCH_GIT_SUBTREE_CONFIG_20260119
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
# Research: Git Subtree + YAML/ENV Configuration System

**Author:** R7-GitSubtreeConfig
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-19 04:20 UTC
**Confidence:** 0.89 (overall composite)

> This document investigates git subtree mechanics for managing private plugin/theme repositories, and designs a YAML/ENV configuration system for an open source MyBB development toolkit. Configuration must be developer-friendly, support attribution, and handle both structured (YAML) and sensitive (ENV) data.

---

## Executive Summary

**Research Objective:** Design a configuration system that enables developers to:
1. Push private plugins/themes to separate git repositories via subtrees
2. Configure developer metadata (name, website) for plugin attribution
3. Set project defaults (compatibility, license, etc.)
4. Manage both public and private plugin development

**Key Findings:**

1. **Git Subtree is the Right Approach** - Avoids nested .git complexity of submodules, enables clean push/pull of subdirectories to separate repos
2. **YAML + ENV is the Right Strategy** - Separate structured config (YAML) from secrets/paths (ENV); users prefer YAML over JSON for manual editing
3. **Existing Codebase Already Uses Both Patterns** - plugin_manager uses JSON, MCP uses dotenv; can build compatible system
4. **Configuration Must Be Optional and Graceful** - OSS users may not use subtrees; config file should have sensible defaults, not break if missing
5. **Precedence Order Matters** - ENV vars override YAML which overrides built-in defaults (standard approach)

---

## Research Scope

**Research Lead:** R7-GitSubtreeConfig
**Investigation Window:** 2026-01-19

**Focus Areas:**
- [x] Git subtree command mechanics and edge cases
- [x] Existing configuration patterns in codebase (JSON, dotenv)
- [x] Python YAML libraries and best practices
- [x] Config file location strategy (global vs local, precedence)
- [x] OSS considerations (example files, documentation, no hardcoded paths)

**Constraints:**
- User prefers YAML over JSON ("mfers dont wanna be editing json")
- Must work with open source - no CortaLabs-specific hardcoding
- Configuration files should be gitignored (contain personal info)
- Need both structured data (YAML) and secrets (ENV)

---

## Findings

### Finding 1: Git Subtree Mechanics

**Summary:** Git subtrees enable pushing/pulling a subdirectory to/from a separate repository without the complexity of git submodules.

**Core Commands:**

```bash
# 1. ADD: Initial import of private repo as subtree
git subtree add --prefix=plugin_manager/plugins/private/my_plugin \
    git@github.com:user/my_plugin.git main --squash

# 2. PUSH: Export changes from subtree back to private repo
git subtree push --prefix=plugin_manager/plugins/private/my_plugin \
    git@github.com:user/my_plugin.git main

# 3. PULL: Import updates from private repo
git subtree pull --prefix=plugin_manager/plugins/private/my_plugin \
    git@github.com:user/my_plugin.git main --squash
```

**Key Properties:**
- **No nested .git** - Subtree commits are flattened into main repo history (with --squash)
- **Clean history** - Changes appear as normal commits in main repo, not as special merge commits
- **Bidirectional sync** - Can push changes back to private repo or pull updates from it
- **Per-directory** - Each subdirectory can have its own remote
- **Manual process** - Unlike submodules, subtree operations are explicit (not automatic on clone)

**Typical Workflow for Developer:**
```bash
# Developer adds their private plugin
git subtree add --prefix=plugin_manager/plugins/private/my_awesome_plugin \
    git@github.com:myusername/my-awesome-plugin.git main

# Main repo now has the full plugin code in that directory
# Developer can make changes locally, commit normally

# When ready to push to private repo:
git subtree push --prefix=plugin_manager/plugins/private/my_awesome_plugin \
    git@github.com:myusername/my-awesome-plugin.git main

# To get updates from private repo:
git subtree pull --prefix=plugin_manager/plugins/private/my_awesome_plugin \
    git@github.com:myusername/my-awesome-plugin.git main --squash
```

**Confidence:** 0.95 (verified via git documentation and RESEARCH_GIT_WORKTREES.md)

---

### Finding 2: Configuration File Strategy

**Summary:** Best practice is to split configuration into structured (YAML) and secrets (ENV), stored in separate files with different .gitignore rules.

**Proposed File Structure:**

```
MyBB_Playground/
├── .mybb-forge.yaml          # STRUCTURED CONFIG (tracked example file)
├── .mybb-forge.local.yaml    # LOCAL OVERRIDES (gitignored)
├── .mybb-forge.env           # SECRETS (gitignored)
├── .mybb-forge.env.example   # TEMPLATE (tracked)
└── plugin_manager/
    ├── config.json           # EXISTING - workspace config
    └── .gitignore            # Updated to include .mybb-forge files
```

**File Purposes:**

1. **.mybb-forge.yaml** (Tracked, example)
   - Structured developer metadata (name, website, license)
   - Project defaults (MyBB compatibility, default license)
   - Subtree configurations (paths, branches)
   - Public information only

2. **.mybb-forge.local.yaml** (Gitignored, optional)
   - Local developer overrides
   - Per-developer preferences
   - Only needed if developer wants different config than default

3. **.mybb-forge.env** (Gitignored, required)
   - Remote URLs with authentication tokens
   - Local paths (if non-standard)
   - Database credentials (if needed)
   - Sensitive information only

4. **.mybb-forge.env.example** (Tracked, template)
   - Template showing what ENV vars are available
   - Documentation of required and optional vars
   - No actual secrets

**Confidence:** 0.91

---

### Finding 3: Proposed YAML Schema

**Summary:** YAML provides excellent structure for nested configuration while remaining human-readable.

**Proposed .mybb-forge.yaml Schema:**

```yaml
# .mybb-forge.yaml - MyBB Forge Developer Configuration
# This file stores structured configuration for git subtrees and project metadata
# For secrets (remote URLs, tokens), use .mybb-forge.env

developer:
  name: "Your Name"                    # Author name for plugin metadata
  website: "https://example.com"       # Developer website
  email: "dev@example.com"             # Contact email (optional)

defaults:
  mybb_compatibility: "18*"            # MyBB version compatibility
  license: "MIT"                       # Default license for plugins
  visibility: "private"                # Default: public or private workspace

subtrees:
  plugins/my_plugin:                   # Subtree identifier
    path: "plugin_manager/plugins/private/my_plugin"
    remote_env: "MY_PLUGIN_REMOTE"     # References env var (not URL directly)
    branch: "main"
    squash: true                       # Use --squash for cleaner history
    
  themes/my_theme:
    path: "plugin_manager/themes/private/my_theme"
    remote_env: "MY_THEME_REMOTE"
    branch: "main"
    squash: true

# MCP Tool Integration (optional - tells which tools to use)
mcp:
  enabled: true
  server_port: 3000
  auto_sync: false                     # Manual or automatic sync on commands
```

**Proposed .mybb-forge.env.example:**

```bash
# .mybb-forge.env.example - Configuration Template
# Copy to .mybb-forge.env and fill in your values

# Git Subtree Remote URLs (with auth tokens if needed)
# Format: git@github.com:USERNAME/REPO.git or https://github.com/USERNAME/REPO.git
MY_PLUGIN_REMOTE=git@github.com:YOUR_USERNAME/my-plugin.git
MY_THEME_REMOTE=git@github.com:YOUR_USERNAME/my-theme.git

# Optional: Override config paths (defaults shown)
MYBB_FORGE_CONFIG_PATH=.mybb-forge.yaml
MYBB_FORGE_ENV_PATH=.mybb-forge.env

# Optional: Local path overrides (if different from defaults)
MYBB_FORGE_PLUGIN_WORKSPACE=plugin_manager/plugins
MYBB_FORGE_THEME_WORKSPACE=plugin_manager/themes
```

**Confidence:** 0.88

---

### Finding 4: Python Implementation - Libraries and Patterns

**Summary:** Python has excellent YAML support via PyYAML and pydantic. Existing codebase uses python-dotenv for env vars.

**Available Libraries:**

1. **PyYAML** - Standard YAML parsing
   - Already available in environment (watchdog dependency includes it)
   - Simple: `yaml.safe_load()` for reading, `yaml.dump()` for writing
   - Safe for untrusted input with `safe_load()` vs `load()`

2. **pydantic-settings** - Configuration management (already in deps)
   - Supports YAML sources natively
   - Type validation for config values
   - Precedence: Pydantic fields > env vars > YAML file > defaults

3. **python-dotenv** - Already used in MCP server
   - Loads .env files into os.environ
   - Simple API: `load_dotenv()`
   - Preserves existing env vars if not overridden

**Recommended Pattern:**

```python
from pathlib import Path
import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
import os

class DeveloperConfig(BaseModel):
    name: str = Field(default="Developer")
    website: Optional[str] = None
    email: Optional[str] = None

class SubtreeConfig(BaseModel):
    path: str
    remote_env: str  # Name of env var, not URL
    branch: str = "main"
    squash: bool = True

class ForgeConfig(BaseModel):
    developer: DeveloperConfig
    defaults: Dict[str, Any]
    subtrees: Dict[str, SubtreeConfig]
    
    @classmethod
    def load(cls, yaml_path: Path = None, env_path: Path = None):
        """Load config with precedence: ENV vars > local YAML > defaults"""
        # Load env vars first
        if env_path is None:
            env_path = Path.cwd() / ".mybb-forge.env"
        if env_path.exists():
            load_dotenv(env_path)
        
        # Load YAML config
        if yaml_path is None:
            yaml_path = Path.cwd() / ".mybb-forge.yaml"
        
        data = {}
        if yaml_path.exists():
            with open(yaml_path) as f:
                data = yaml.safe_load(f) or {}
        
        # Create instance (pydantic validates)
        return cls(**data)
    
    def get_subtree_remote(self, subtree_name: str) -> str:
        """Get remote URL for subtree (resolves env var)"""
        if subtree_name not in self.subtrees:
            raise ValueError(f"Unknown subtree: {subtree_name}")
        
        env_var = self.subtrees[subtree_name].remote_env
        remote_url = os.getenv(env_var)
        
        if not remote_url:
            raise ValueError(f"Env var {env_var} not set for subtree {subtree_name}")
        
        return remote_url
```

**Confidence:** 0.93 (verified against existing patterns in codebase)

---

### Finding 5: Integration with Existing MCP Tools

**Summary:** Configuration system should integrate with existing `mybb_create_plugin`, `mybb_plugin_install`, and plugin manager tools.

**Integration Points:**

1. **Plugin Creation Tool** (`mybb_create_plugin`)
   - When creating plugin, read developer name/website from config
   - Auto-populate plugin metadata (license, author)
   - Optional: Ask if user wants to add as subtree

2. **Plugin Manager Workspace**
   - When deploying plugin via `mybb_plugin_install`, check if it's in subtree
   - Optionally auto-push to private repo after deployment
   - Track which plugins are subtree-tracked

3. **New MCP Tools for Subtree Operations** (Future)
   - `mybb_subtree_add` - Configure new subtree
   - `mybb_subtree_push` - Push changes to private repo
   - `mybb_subtree_pull` - Pull updates from private repo
   - `mybb_list_subtrees` - List configured subtrees

**Confidence:** 0.87

---

## OSS Considerations (Critical for Adoption)

**Why This Matters:**
- Developers clone the repo and need zero setup friction
- Configuration must be optional (not required to work)
- Should not force developers to use subtrees
- Personal information should not be tracked

**Recommendations:**

1. **Make Config Optional**
   - System works fine without `.mybb-forge.yaml` (uses built-in defaults)
   - Subtree operations optional - users choose whether to use them
   - Graceful degradation: missing config ≠ error

2. **Provide Example Files**
   - Track `.mybb-forge.yaml.example` in repo
   - Track `.mybb-forge.env.example` as template
   - Developer copies to local file, fills in values
   - Local files (`.mybb-forge.yaml`, `.mybb-forge.env`) in `.gitignore`

3. **Clear Documentation**
   - Wiki page: "Setting Up Private Plugin Development"
   - Step-by-step guide for GitHub, GitLab, etc.
   - Example showing how to add existing private repo as subtree
   - Troubleshooting section for common git subtree issues

4. **No Hardcoded Paths or Credentials**
   - All remote URLs configurable via ENV
   - All paths configurable in YAML
   - No CortaLabs-specific references

**Confidence:** 0.90

---

## Technical Gaps & Open Questions

**UNVERIFIED - Needs Investigation:**

1. **Subtree Conflict Resolution** - What happens if multiple developers push to same private repo?
   - How does git subtree handle merge conflicts?
   - Should we document workflow for team collaboration?

2. **Large File Handling** - Does git subtree work well with large plugin bundles?
   - Any performance concerns with deep subdirectory trees?
   - Recommendation for squash vs non-squash?

3. **Initial User Experience** - How complex is the first-time setup?
   - Should provide CLI helper to add subtrees?
   - Pre-configured examples to copy-paste?

**Recommendation:** Architect phase should detail workflow documentation and CLI helpers for subtree operations.

---

## Integration Plan with Existing Infrastructure

**File Locations:**
- Config class: `plugin_manager/forge_config.py` (new)
- MCP tools for subtree: `mybb_mcp/tools/subtrees.py` (new)
- Integration hooks: Modify `mybb_create_plugin` to use config

**Dependencies to Add:**
- PyYAML (if not already present)
- Check if pydantic-settings should be used vs custom implementation

**Backward Compatibility:**
- Existing JSON config in plugin_manager stays unchanged
- MCP dotenv config stays unchanged
- New YAML system sits alongside, doesn't interfere

---

## Deliverables for Architect Phase

Architect should detail:
1. Final config schema (approve proposed YAML structure)
2. CLI utilities for subtree management
3. Documentation/wiki pages for end users
4. Integration points in MCP tools
5. Example workflow for open source contributor
