# RESEARCH: Plugin Manager Git Integration

**Research Goal:** Investigate git integration for Plugin Manager private plugins/themes, focusing on nested repo approach as replacement for deprecated git subtrees.

**Research Date:** 2026-01-19  
**Researcher:** MyBB-ResearchAgent  
**Confidence Score:** 0.95 (high - verified against actual codebase)

---

## Executive Summary

Current Status:
- **Subtrees are deprecated** - User confirmed subtree approach was unsuccessful
- **Infrastructure is ready** - Plugin structure and .gitignore already support nested repos
- **Gap exists** - MCP plugin creation tool has NO git integration
- **Integration point identified** - Best location is `PluginManager.create_plugin()` method

Recommendation: Implement opt-in git initialization at plugin creation time with support for automatic GitHub CLI repo creation.

---

## 1. Current State Analysis

### 1.1 .mybb-forge.yaml Configuration

**File:** `.mybb-forge.yaml` (lines 16-28)

```yaml
subtrees:
  mybb_mcp:
    remote: "https://github.com/CortaLabs/mybb_mcp.git"
    branch: main
    squash: true

  # Private plugins (uses env var for remote URL)
  # plugin_manager/plugins/private:
  #   remote_env: PRIVATE_PLUGINS_REMOTE
  #   branch: main
  #   squash: true
```

**Status:** Subtree configuration exists but is COMMENTED OUT for private plugins.

**Finding:** The infrastructure is prepared for subtree-style organization, but user has explicitly rejected this approach in favor of nested repos.

**Confidence:** 0.95

---

### 1.2 Plugin Manager Structure

**Directory Layout:**
```
plugin_manager/
├── plugins/
│   ├── public/
│   │   ├── cortex/               # Self-contained plugin (no .git)
│   │   ├── dice_roller/          # Self-contained plugin (no .git)
│   │   └── test_tracker/         # Self-contained plugin (no .git)
│   └── private/
│       ├── invite_system/        # Self-contained plugin (no .git)
│       ├── test_scaffold/        # Self-contained plugin (no .git)
│       └── .gitkeep
└── themes/private/               # Similar structure
```

**Per-Plugin Structure (e.g., cortex/):**
```
cortex/
├── meta.json                     # Plugin metadata
├── README.md                     # Plugin documentation
├── inc/plugins/cortex.php        # Main plugin file
├── inc/languages/english/        # Language files
├── jscripts/                     # JavaScript assets
└── images/                       # Image assets
```

**Finding:** Each plugin is self-contained and ready for individual git repos.

**Confidence:** 0.98

---

### 1.3 .gitignore Pattern Analysis

**File:** `.gitignore` (lines 170-179)

```gitignore
# Plugin Manager
# NOTE: Private plugins/themes managed via git subtree should NOT be ignored.
# Add negation patterns below for subtree-managed items.
plugin_manager/plugins/private/
plugin_manager/themes/private/

# Subtree-managed private plugins (tracked for subtree push/pull)
!plugin_manager/plugins/private/invite_system/
.plugin_manager/projects.db
```

**Pattern Analysis:**
1. Private plugins dir is ignored by default: `plugin_manager/plugins/private/`
2. Individual plugins are whitelisted: `!plugin_manager/plugins/private/invite_system/`
3. Pattern is scalable - can add more negation patterns per nested repo

**Current Status:** Only `invite_system` is whitelisted (but it's not yet a nested repo).

**Finding:** .gitignore is ALREADY PREPARED for nested repo approach. The infrastructure exists; implementation is the gap.

**Confidence:** 0.99

---

### 1.4 Plugin Manager API - No Git Integration

**File:** `plugin_manager/manager.py` (lines 267-460)

**Method:** `PluginManager.create_plugin()`

**Responsibilities:**
- Create workspace directory structure
- Generate meta.json with plugin metadata
- Scaffold PHP plugin file with hooks
- Generate language files
- Create README.md
- Register plugin in database
- Return success dict with workspace_path, project_id, files_created

**Git Integration:** NONE

**Finding:** The `create_plugin()` method has complete plugin scaffolding but zero git handling. No `git init`, no repo creation, no remote linking.

**Confidence:** 0.98

---

### 1.5 MCP Tool Entry Point

**File:** `mybb_mcp/mybb_mcp/handlers/plugins.py` (lines 199-280)

**Handler:** `handle_create_plugin()`

Responsibilities:
- Maps MCP arguments to PluginManager parameters
- Loads ForgeConfig for developer defaults
- Calls `manager.create_plugin()`
- Formats response as markdown

**Current Flow:**
```
MCP: mybb_create_plugin
  ↓
handle_create_plugin()
  ↓
PluginManager.create_plugin()
  ↓
Returns workspace_path, files_created, project_id
```

**Finding:** MCP tool could pass through git_init parameters, but downstream handler has no support.

**Confidence:** 0.95

---

### 1.6 Install Script - Git Authentication Ready

**File:** `install.sh` (lines 558-650)

**Functions:**
- `setup_git_auth()` - detects SSH and GitHub CLI authentication
- `setup_ssh_auth()` - creates project-specific SSH key for MyBB Playground
- `setup_gh_cli()` - GitHub CLI setup (not shown in excerpt)

**SSH Key Management:**
- Project-specific key: `$HOME/.ssh/id_ed25519_mybb_playground`
- SSH config entry: `Host github.com-mybb` (for private key isolation)
- Key is loaded into ssh-agent

**Finding:** Git authentication infrastructure is ALREADY SOLID. SSH and GitHub CLI setup is complete.

**Confidence:** 0.95

---

## 2. Git Approaches: Comparative Analysis

### 2.1 Git Subtrees (DEPRECATED)

**Why User Rejected:**
- Complexity in split/merge workflow
- Difficult to manage multiple nested repos
- Confusing commits that reference subtree state

**Current Implementation:**
- Configured in `.mybb-forge.yaml` but commented out
- MCP tools exist: `mybb_subtree_add()`, `mybb_subtree_push()`, `mybb_subtree_pull()`
- Only one active subtree: `mybb_mcp` (main MCP server repo)

**Future:** User indicated these tools will be replaced for nested repos.

---

### 2.2 Git Submodules

**Pros:**
- Simple git init per module
- Explicit version pinning via `.gitmodules`
- Easy to clone recursively: `git clone --recurse-submodules`

**Cons:**
- Submodules are read-only from parent perspective
- Updating parent must explicitly commit submodule refs
- Workflow is unintuitive for distributed teams
- Plugin developers would need to work in detached HEAD state

**Verdict:** Better than subtrees, but not ideal for plugin development.

---

### 2.3 Nested Git Repos (RECOMMENDED)

**Pros:**
- Each plugin is fully independent git repo
- Developers can work naturally within their repo
- No special git machinery needed
- Parent repo ignores child repos via `.gitignore` negation
- Private repos can have their own access controls
- Plugin visibility (public/private) naturally aligns with repo access

**Cons:**
- Parent repo needs to explicitly manage nested repo .gitignore patterns
- Cloning parent repo doesn't automatically clone nested plugins
- Requires explicit documentation for workflow

**Verdict:** BEST APPROACH - aligns with plugin autonomy, matches plugin_manager structure.

---

## 3. Technical Architecture for Nested Repos

### 3.1 .gitignore Pattern Strategy

**Current Pattern:**
```gitignore
plugin_manager/plugins/private/           # Ignore directory by default
!plugin_manager/plugins/private/invite_system/  # Whitelist specific plugin
```

**Scalable Pattern:**
```gitignore
# Nested private plugin repos - ignore by default
plugin_manager/plugins/private/
plugin_manager/plugins/private/**/.git/

# Whitelist tracked private plugins
!plugin_manager/plugins/private/invite_system/
!plugin_manager/plugins/private/invite_system/.git/
```

**For Public Plugins:** No ignoring needed - all public plugins are in parent repo.

### 3.2 Git Init Workflow

**Per-Plugin Initialization:**
```bash
cd plugin_manager/plugins/{visibility}/{codename}
git init                                   # Initialize repo
git add .                                  # Stage all files
git commit -m "Initial commit: {codename}"  # Create first commit
git remote add origin {remote_url}         # Link to GitHub
git push -u origin main                    # Push to remote
```

**Integration Points:**
1. **During plugin creation** - `PluginManager.create_plugin()` (RECOMMENDED)
2. **Post-creation opt-in** - Separate `mybb_plugin_enable_git()` tool
3. **During plugin installation** - `mybb_plugin_install()` could link existing repos

### 3.3 GitHub CLI Integration

**Prerequisites:**
- `gh` CLI installed and authenticated (already in `install.sh`)
- SSH key configured for `git@github.com-mybb` host

**Workflow for Automatic Repo Creation:**
```bash
# User option during plugin creation:
# "Create remote GitHub repo? (yes/no)"

if [ "$create_remote" = "yes" ]; then
    # Create private repo via GitHub CLI
    gh repo create {owner}/{repo-name} \
        --private \
        --description "{plugin_description}" \
        --source=. \
        --push \
        --remote=origin
fi
```

**Advantages:**
- One-command remote creation and push
- Respects user's GitHub token (no manual auth needed if `gh auth` is configured)
- Automatic `.git/config` setup with correct remote

---

## 4. Integration Points in Plugin Manager

### 4.1 MCP Tool: mybb_create_plugin()

**Current Parameters:**
```python
{
    "codename": str,
    "name": str,
    "description": str,
    "author": str (optional),
    "version": str (optional),
    "visibility": str (optional: "public"/"private"),
    "hooks": list,
    "has_templates": bool,
    "has_database": bool
}
```

**Proposed New Parameters:**
```python
{
    # ... existing parameters ...
    "git_init": bool = False,           # Initialize git repo?
    "git_remote": str = None,           # GitHub remote URL (optional)
    "github_create": bool = False,      # Auto-create remote via gh CLI?
    "github_private": bool = True       # If auto-creating, make it private?
}
```

**Handler Responsibility:** Pass git parameters to PluginManager, but don't execute git commands directly in MCP server. Return git-related info in response.

### 4.2 PluginManager.create_plugin() Enhancement

**New Responsibility (optional, if `git_init=true`):**
1. Create workspace directory (existing)
2. Write all plugin files (existing)
3. **NEW:** Initialize git repo in workspace
4. **NEW:** Create initial commit
5. **NEW:** Optionally link to remote via GitHub CLI
6. Return git_repo_path, git_status in response

**Error Handling:**
- If git init fails: log warning, continue plugin creation (non-blocking)
- If GitHub CLI fails: log warning, return success but git_status="remote_failed"
- Plugin creation should NEVER fail due to git operations

### 4.3 Separate Tool: mybb_plugin_link_git()

**Purpose:** Enable developers to manually add git to existing plugins

**Parameters:**
```python
{
    "codename": str,
    "visibility": str,
    "git_remote": str,              # GitHub URL
    "github_create": bool = False   # Auto-create remote?
}
```

**Workflow:**
1. Verify plugin exists and is not already a git repo
2. Initialize git repo in plugin directory
3. Add all files and create initial commit
4. If `github_create=true`, use GitHub CLI to create remote
5. Push to remote

---

## 5. Workflow Examples

### 5.1 Example 1: Create Plugin with Git Init

**User Command:**
```
User: Create a private plugin called "karma" with git repo
```

**Flow:**
```
MCP: mybb_create_plugin(
    codename="karma",
    name="Karma System",
    visibility="private",
    git_init=True,
    github_create=True
)

PluginManager.create_plugin():
1. Create workspace: plugin_manager/plugins/private/karma/
2. Create meta.json, README.md, karma.php, language files
3. Register in database
4. git init in karma/
5. git add .
6. git commit -m "Initial commit: Karma System"
7. gh repo create owner/mybb-karma --private --source=. --push
8. Return success with git_status="initialized", git_remote="github.com:owner/mybb-karma.git"

.gitignore Update (manual after first plugin):
  !plugin_manager/plugins/private/karma/
  !plugin_manager/plugins/private/karma/.git/

Result:
  - Plugin created and registered
  - Local git repo initialized
  - Remote created and pushed
  - Ready for collaborative development
```

### 5.2 Example 2: Link Git to Existing Plugin

**User Command:**
```
User: Link existing private plugin "reputation" to GitHub repo
```

**Flow:**
```
MCP: mybb_plugin_link_git(
    codename="reputation",
    visibility="private",
    git_remote="github.com:owner/mybb-reputation.git"
)

1. Verify plugin exists: plugin_manager/plugins/private/reputation/
2. Check for existing .git - ERROR if found
3. git init
4. git add .
5. git commit -m "Initial commit: reputation"
6. git remote add origin github.com:owner/mybb-reputation.git
7. git push -u origin main
8. Return success

.gitignore Update (manual):
  !plugin_manager/plugins/private/reputation/
  !plugin_manager/plugins/private/reputation/.git/

Result:
  - Existing plugin now tracked in GitHub
```

---

## 6. Challenges & Solutions

### Challenge 1: .gitignore Maintenance

**Problem:** Each new nested repo requires .gitignore negation pattern.

**Solution:**
- Maintain template pattern in CLAUDE.md for developers
- Document: "After creating/linking a private plugin repo, add these lines to .gitignore"
- Consider future automation: script to scan and update .gitignore on demand

**Recommended Pattern:**
```gitignore
# Generated - do NOT edit manually (use: python scripts/update_gitignore.py)
# Private plugin repos
!plugin_manager/plugins/private/{codename}/
!plugin_manager/plugins/private/{codename}/.git/
```

### Challenge 2: Clone Workflow

**Problem:** Cloning MyBB_Playground doesn't automatically fetch private plugin repos.

**Solution:** Document clone workflow:
```bash
# Clone main repo
git clone https://github.com/CortaLabs/MyBB_Playground.git

# Clone nested private plugins manually
cd plugin_manager/plugins/private
git clone git@github.com:owner/mybb-karma.git karma
git clone git@github.com:owner/mybb-reputation.git reputation
```

**Alternative:** Provision initialization script `scripts/clone_private_plugins.sh` that reads plugin metadata and clones all registered private repos.

### Challenge 3: SSH Key Isolation

**Problem:** Developers might use same key for multiple GitHub accounts.

**Solution:** Leverage existing `install.sh` approach:
- SSH config uses `Host github.com-mybb` for project-specific key
- Git remotes should use: `git@github.com-mybb:owner/repo.git` (custom hostname)
- This ensures correct key is used without conflicts

### Challenge 4: GitHub CLI Availability

**Problem:** Not all developers may have GitHub CLI installed or authenticated.

**Solution:** Make GitHub CLI integration OPTIONAL:
- `git_init=true` without `github_create=true` - manual remote linking
- `github_create=true` but `gh` not installed - log warning, manual push needed
- Default to local git only; remote creation is opt-in

---

## 7. Implementation Roadmap

### Phase 1: Groundwork
1. Update .gitignore documentation in CLAUDE.md
2. Plan MCP tool interface changes
3. Prepare PluginManager enhancement design

### Phase 2: Core Implementation
1. Extend `PluginManager.create_plugin()` with git_init parameters
2. Add git initialization logic (non-blocking)
3. Test local git repo creation

### Phase 3: GitHub Integration
1. Add GitHub CLI integration (optional, best-effort)
2. Implement `mybb_plugin_link_git()` tool
3. Test repo creation and push

### Phase 4: Workflow & Documentation
1. Update CLAUDE.md with nested repo workflow
2. Create example .gitignore patterns
3. Document clone and sync procedures
4. Update plugin creation examples in wiki

### Phase 5: Subtree Replacement
1. Deprecate `mybb_subtree_*` tools
2. Migrate existing subtrees to nested repos
3. Remove subtree config from `.mybb-forge.yaml`

---

## 8. Open Questions & Assumptions

### Assumptions Made:
1. **Private plugin repos live in developer's own GitHub account** - not MyBB_Playground org repo
2. **SSH key management is developer's responsibility** - install.sh provides setup guidance
3. **Public plugins remain in parent repo** - no nested repos for public
4. **Plugin metadata (meta.json) documents git remote** - for dependency tracking

### Questions for Architect:
1. Should GitHub CLI integration be required or optional?
2. Should we auto-commit .gitignore changes when plugins are created?
3. Should private plugin repos have strict visibility (private GitHub repo)?
4. How should we handle plugin deletion - remove .gitignore pattern?
5. Should we provide a management script for batch .gitignore updates?

---

## 9. Recommended Next Steps

1. **Architect Review:** Review this research and design MCP tool interface
2. **Design Spec:** Create detailed design doc for nested repo architecture
3. **Implementation:** Enhance PluginManager with git_init capability
4. **Testing:** Create test plugins with git repos
5. **Documentation:** Update CLAUDE.md and wiki with nested repo workflow

---

## Appendix: Reference Files

| File | Lines | Status | Relevance |
|------|-------|--------|-----------|
| `.mybb-forge.yaml` | 1-40 | Current | Config structure for repos |
| `.gitignore` | 170-179 | Current | .gitignore pattern foundation |
| `plugin_manager/manager.py` | 267-460 | Current | Target for git integration |
| `mybb_mcp/handlers/plugins.py` | 199-280 | Current | MCP tool entry point |
| `install.sh` | 558-650 | Current | Git auth setup reference |

---

## Summary

**Current State:**
- Infrastructure is READY for nested repos
- Plugin structure is IDEAL for independent git repos
- .gitignore patterns are PREPARED
- Git authentication is CONFIGURED
- MCP integration point is IDENTIFIED

**Gap:**
- NO git initialization in `PluginManager.create_plugin()`
- NO MCP parameters for git operations
- NO opt-in workflow for developers

**Recommendation:**
Implement nested git repos with optional GitHub CLI integration. Plugin creation becomes:
1. Create workspace and files (current)
2. Init git repo (new - opt-in)
3. Create initial commit (new - opt-in)
4. Link to remote (new - opt-in)

**Confidence in Recommendation:** 0.95
