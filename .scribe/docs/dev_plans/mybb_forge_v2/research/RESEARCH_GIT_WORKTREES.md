# Research: Git Worktrees for Multi-Agent Parallel Development

**Author:** R1-GitWorktrees
**Version:** v1.0
**Status:** Complete
**Last Updated:** 2026-01-19 03:56 UTC
**Confidence:** 0.88

> This document evaluates git worktrees as a solution for enabling multiple Claude Code agents to work on independent features simultaneously without conflicts.

---

## Executive Summary

**Primary Objective:** Determine how git worktrees can enable parallel agent development while managing shared resources (TestForum, MySQL database, mybb_sync watcher).

**Key Takeaways:**

1. **Git worktrees provide excellent FILE isolation** - each agent gets a separate working directory with independent branch, but shares git history
2. **Database sharing is the critical bottleneck** - multiple agents cannot safely write to the same MySQL templates/stylesheets tables concurrently
3. **The mybb_sync watcher is designed for single-instance operation** - multiple watchers on shared directory would conflict
4. **Private repo solution: git subtree beats submodules** - allows subdirectory to push to separate repo without nested .git hell
5. **Recommended approach: Per-worktree isolation OR scope-based parallelism** - either full isolation (own DB per agent) or careful scope separation

---

## Research Scope

**Research Lead:** R1-GitWorktrees
**Investigation Window:** 2026-01-19

**Focus Areas:**
- [x] Git worktree mechanics and branch strategy
- [x] Shared TestForum directory implications
- [x] Database sharing challenges for parallel agents
- [x] mybb_sync watcher multi-instance behavior
- [x] Private repo solutions without submodule pain

**Dependencies & Constraints:**
- Single MySQL database configured via `.env`
- mybb_sync watcher writes directly to shared database
- TestForum is partially tracked in git (758 files), plugins directory mostly ignored
- Current architecture assumes single-agent operation

---

## Findings

### Finding 1: Git Worktree Mechanics

**Summary:** Git worktrees create linked working directories that share the same repository but can checkout different branches independently.

**Evidence:**
```bash
# Current state - single worktree
$ git worktree list
/home/austin/projects/MyBB_Playground  f22c813 [main]

# Creating an agent worktree would look like:
$ git worktree add ../agent-1-feature-x -b feature-x
# Creates: /home/austin/projects/agent-1-feature-x with feature-x branch
```

**Key Properties:**
- Each worktree has independent HEAD, index, working directory
- Branches are shared - can't checkout same branch in multiple worktrees
- Git history (commits, refs) is shared via `$GIT_COMMON_DIR`
- Per-worktree config possible via `extensions.worktreeConfig`

**Confidence:** 0.95 (verified via git documentation)

### Finding 2: TestForum Sharing Problem

**Summary:** TestForum cannot be trivially shared across worktrees because:
1. 758 core MyBB files ARE tracked in git (would conflict)
2. Deployed plugins go to `TestForum/inc/plugins/` (NOT tracked, but shared state)
3. Runtime cache at `TestForum/cache/` is gitignored but shared

**Evidence from .gitignore:**
```
# Tracked: Core MyBB files (758 files)
TestForum/*.php, TestForum/inc/*, TestForum/admin/*, etc.

# Ignored: Runtime/sensitive
TestForum/inc/settings.php
TestForum/inc/config.php
TestForum/cache/*.php
TestForum/uploads/
plugin_manager/plugins/private/
```

**Implications:**
- Worktrees would each get their own TestForum copy (tracked files)
- BUT they'd need separate databases to avoid conflicts
- OR they share TestForum via symlink (complex, not recommended)

**Confidence:** 0.95

### Finding 3: Database Sharing is Dangerous

**Summary:** All MCP operations go through single MySQL database. Concurrent template writes = race conditions.

**Evidence from `mybb_mcp/config.py`:**
```python
db_config = DatabaseConfig(
    host=os.getenv("MYBB_DB_HOST", "localhost"),
    database=os.getenv("MYBB_DB_NAME", "mybb_dev"),  # SINGLE DB
    ...
)
```

**Evidence from `watcher.py` line 300-304:**
```python
await self.template_importer.import_template(
    work_item["set_name"],
    work_item["template_name"],
    work_item["content"]  # Direct DB write
)
```

**Scenarios:**
| Scenario | Risk | Mitigation |
|----------|------|------------|
| Agent A and B edit same template | **HIGH** - Last write wins, data loss | Scope separation |
| Agent A and B edit different templates | **MEDIUM** - Cache invalidation issues | Coordination |
| Agent A and B work on different plugins | **LOW** - If plugins don't share templates | Best approach |

**Confidence:** 0.95

### Finding 4: mybb_sync Watcher Limitations

**Summary:** FileWatcher is designed for single-instance operation. Multiple watchers would queue conflicting writes.

**Evidence from `watcher.py`:**
- Uses single `Observer()` instance (line 244)
- Work queue is instance-scoped (line 242)
- No distributed locking or coordination mechanism
- Pause/resume mechanism exists but not multi-instance aware

**Implications:**
- Each worktree would need its own MCP server instance
- Each MCP server would need its own database (or no watcher)
- Watcher conflicts would cause template corruption

**Confidence:** 0.92

### Finding 5: Private Repo Solutions

**Summary:** Git subtree is the recommended solution for private plugins without submodule complexity.

**Comparison:**

| Approach | Pros | Cons | Recommendation |
|----------|------|------|----------------|
| **Git Submodule** | Clean separation | Nested .git, complex workflow, `git clone --recursive` needed | Avoid |
| **Git Subtree** | No nested .git, clean commits in main repo, simple push to private | History can get messy with `--squash` | **Recommended** |
| **Separate Remote** | Simple `.gitignore` + manual push | No history tracking in main repo | OK for simple cases |
| **Git Sparse-Checkout** | Worktree-specific patterns | Experimental, complex | Future consideration |

**Git Subtree Workflow:**
```bash
# Initial setup - add private plugin as subtree
git subtree add --prefix=plugin_manager/plugins/private/my_plugin \
    git@github.com:user/my_plugin.git main --squash

# Push changes to private repo
git subtree push --prefix=plugin_manager/plugins/private/my_plugin \
    git@github.com:user/my_plugin.git main

# Pull updates from private repo
git subtree pull --prefix=plugin_manager/plugins/private/my_plugin \
    git@github.com:user/my_plugin.git main --squash
```

**Confidence:** 0.88

---

## Technical Analysis

### Code Patterns Identified

1. **Single-instance assumption**: MCP server, watcher, config all assume one active instance
2. **Environment-based config**: `.env` file determines all paths and DB connection
3. **No distributed coordination**: No locking, no message queue, no conflict detection

### System Interactions

```
+------------------+     +------------------+     +------------------+
|   Agent 1        |     |   Agent 2        |     |   Agent N        |
|   (Worktree)     |     |   (Worktree)     |     |   (Worktree)     |
+--------+---------+     +--------+---------+     +--------+---------+
         |                        |                        |
         | MCP Tools              | MCP Tools              | MCP Tools
         v                        v                        v
+---------------------------------------------------------------------+
|                     SHARED MYSQL DATABASE                           |
|  templates, stylesheets, settings, plugins cache                    |
|                   [!] RACE CONDITION ZONE [!]                       |
+---------------------------------------------------------------------+
```

### Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Template data loss from concurrent writes | High | High (if naive worktrees) | Per-agent DB or scope rules |
| Cache corruption | Medium | Medium | Clear cache between agent switches |
| Merge conflicts on tracked TestForum files | Medium | Low (core rarely changes) | Rebase strategy |
| Watcher conflicts | High | High (if shared mybb_sync) | Per-agent mybb_sync directory |

---

## Recommendations

### Strategy A: Full Isolation (Recommended for True Parallelism)

Each agent gets completely isolated environment:

```
/home/austin/projects/
├── MyBB_Playground/          # Main repo (orchestrator)
├── agent-1-feature-x/        # Worktree 1
│   ├── .env                  # MYBB_DB_NAME=mybb_agent1
│   ├── TestForum/            # Own MyBB installation
│   └── mybb_sync/            # Own sync directory
├── agent-2-feature-y/        # Worktree 2
│   ├── .env                  # MYBB_DB_NAME=mybb_agent2
│   └── ...
```

**Setup Script (proposed):**
```bash
#!/bin/bash
# create_agent_worktree.sh <agent-name> <branch-name>
AGENT=$1
BRANCH=$2

# Create worktree
git worktree add ../$AGENT -b $BRANCH

# Create agent-specific database
mysql -e "CREATE DATABASE mybb_$AGENT"
mysql mybb_$AGENT < mybb_dev_dump.sql

# Configure agent's .env
cat > ../$AGENT/.env << EOF
MYBB_DB_NAME=mybb_$AGENT
MYBB_ROOT=$(pwd)/../$AGENT/TestForum
MYBB_PORT=$((8022 + RANDOM % 1000))
EOF
```

**Pros:** True parallelism, no conflicts
**Cons:** DB setup overhead, disk space, merge complexity

### Strategy B: Scope-Based Parallelism (Simpler, Limited)

Agents work on non-overlapping scopes sharing one DB:

| Agent | Scope | Safe? |
|-------|-------|-------|
| Agent 1 | Plugin A development | Yes |
| Agent 2 | Plugin B development | Yes |
| Agent 3 | Template modifications | **Only if not overlapping A/B** |

**Rules:**
1. Only ONE agent can touch templates at a time
2. Plugin development is safe if plugins don't share templates
3. MCP server runs on main worktree only
4. Agents use main worktree for `git push`, then merge

**Pros:** Simple, no DB overhead
**Cons:** Limited parallelism, requires coordination

### Strategy C: Hybrid (Practical Recommendation)

1. **Development work**: Use Strategy B (scope-based) for most tasks
2. **Heavy template work**: Spin up isolated worktree (Strategy A) temporarily
3. **Private plugins**: Use git subtree for clean separation

### Immediate Next Steps

- [ ] Create `scripts/create_agent_worktree.sh` implementing Strategy A
- [ ] Document scope rules for Strategy B in CLAUDE.md
- [ ] Set up git subtree workflow for `plugin_manager/plugins/private/`
- [ ] Consider adding worktree-aware `.env` loading to MCP config

### Long-Term Opportunities

1. **Distributed locking**: Add Redis/file-based locks for template writes
2. **Branch-scoped templates**: Store templates with branch prefix in DB
3. **MCP multiplexing**: Single MCP server handling multiple worktree requests
4. **Container-based isolation**: Docker compose for per-agent MyBB instances

---

## Appendix

### Git Commands Reference

```bash
# List worktrees
git worktree list

# Create worktree with new branch
git worktree add <path> -b <branch>

# Create worktree on existing branch
git worktree add <path> <branch>

# Remove worktree
git worktree remove <path>

# Repair worktree links after moving
git worktree repair
```

### Files Examined

| File | Purpose | Key Findings |
|------|---------|--------------|
| `.gitignore` | Track patterns | private/ ignored, TestForum core tracked |
| `mybb_mcp/config.py` | DB config | Single DB via env vars |
| `mybb_mcp/sync/watcher.py` | File watcher | Single-instance design |
| `.git/config` | Repo config | Standard setup, no worktrees yet |

### Related Research

- R2: Plugin structure (how plugins interact with templates)
- R3: MCP tools audit (which tools write to DB)
- R4: DB-sync internals (performance and architecture)

---

*Research completed by R1-GitWorktrees on 2026-01-19*
