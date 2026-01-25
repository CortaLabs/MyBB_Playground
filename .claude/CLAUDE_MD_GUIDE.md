# 🧠 The Ultimate CLAUDE.md Guide
## A Comprehensive Reference for AI-Assisted Development

**Version:** 2.0
**Author:** CortaLabs
**Last Updated:** January 2026

---

## 📋 Table of Contents

1. [What is CLAUDE.md?](#what-is-claudemd)
2. [Core Philosophy](#core-philosophy)
3. [File Locations & Hierarchy](#file-locations--hierarchy)
4. [Document Structure](#document-structure)
5. [The Three Pillars: WHAT, WHY, HOW](#the-three-pillars-what-why-how)
6. [Monorepo Strategies](#monorepo-strategies)
7. [Context Engineering Principles](#context-engineering-principles)
8. [What NOT to Include](#what-not-to-include)
9. [Custom Slash Commands](#custom-slash-commands)
10. [Subagents Configuration](#subagents-configuration)
11. [MCP Integration](#mcp-integration)
12. [Companion: settings.json](#companion-settingsjson)
13. [Common Workflows](#common-workflows)
14. [Templates & Examples](#templates--examples)
15. [Troubleshooting & Optimization](#troubleshooting--optimization)

---

## What is CLAUDE.md?

CLAUDE.md is a special configuration file that Claude Code automatically pulls into context when starting a conversation. It serves as **persistent project memory**—the agent's "constitution" and primary source of truth for how your specific repository works.

Think of it as:
- A **briefing document** for an AI pair programmer joining your team
- A **system prompt extension** specific to your project
- **Institutional knowledge** that doesn't require repeated explanation
- A **contract** between you and the agent about how work should be done

### How It Works

1. Claude Code scans for CLAUDE.md files at session start
2. Contents are injected into the system prompt
3. The agent inherits project context without token-consuming exploration
4. Instructions persist across all conversations in that project

### Key Insight

> "Coding agents know absolutely nothing about your codebase at the beginning of each session. The agent must be told anything that's important to know about your codebase each time you start a session. CLAUDE.md is the preferred way of doing this."
> — HumanLayer Engineering

---

## Core Philosophy

### The Minimum Effective Dose

CLAUDE.md becomes part of every prompt. Anthropic recommends keeping it **concise and human-readable**—ideally under **10,000 words** for optimal performance. As instruction count increases, instruction-following quality decreases uniformly across ALL instructions.

**The Constraint Reality:**
- Claude Code's system prompt contains ~50 individual instructions
- That's nearly a third of reliable instruction-following capacity before your CLAUDE.md
- Every instruction you add competes for attention

### Guiding Principles

1. **Universally Applicable**: Only include instructions that apply to EVERY task
2. **High Signal**: Each line should provide meaningful context
3. **Human-Readable**: If a human can't parse it quickly, neither can the agent
4. **Evolving Document**: Treat it like living documentation, not a one-time setup
5. **Solve Real Problems**: Add content based on actual friction points, not theoretical concerns

---

## File Locations & Hierarchy

Claude Code reads CLAUDE.md files from multiple locations, merging them in order of precedence.

### Location Hierarchy (Lowest to Highest Priority)

```
~/.claude/CLAUDE.md           # Global - applies to ALL projects
├── /repo/CLAUDE.md           # Repository root - shared via git
│   └── /repo/module/CLAUDE.md    # Child directories - on-demand loading
└── CLAUDE.local.md           # Local overrides - gitignored
```

### Detailed Breakdown

| Location | Scope | Git Status | Use Case |
|----------|-------|------------|----------|
| `~/.claude/CLAUDE.md` | All projects | N/A | Personal preferences, universal tooling |
| `/repo/CLAUDE.md` | Project-wide | Committed | Team standards, project context |
| `/repo/CLAUDE.local.md` | Project-wide | Ignored | Personal experiments, sensitive paths |
| `/repo/module/CLAUDE.md` | Subdirectory | Committed | Module-specific context |
| Parent directories | Inherited | Varies | Monorepo root context |

### Loading Behavior

- **Root files**: Loaded immediately at session start
- **Parent files**: Auto-merged when running Claude from subdirectories
- **Child files**: Loaded on-demand when working with files in those directories
- **Local files**: Override committed versions for personal customization

### Example: Monorepo Structure

```
company-monorepo/
├── CLAUDE.md                    # Global standards, shared patterns
├── apps/
│   ├── frontend/
│   │   └── CLAUDE.md            # React/Vue conventions
│   └── backend/
│       └── CLAUDE.md            # API conventions
├── packages/
│   └── shared/
│       └── CLAUDE.md            # Shared library patterns
└── infrastructure/
    └── CLAUDE.md                # DevOps/IaC specifics
```

---

## Document Structure

### Recommended Section Order

The structure should follow logical information flow—high-level context first, then specifics.

```markdown
# Project Name

Brief one-liner describing the project.

## Quick Reference
Essential commands and critical context.

## Architecture Overview
High-level system design and key directories.

## Development Standards
Code style, testing, and workflow requirements.

## Common Commands
Build, test, lint, and deployment commands.

## Domain Context
Business logic, terminology, and edge cases.

## Workflow Instructions
How Claude should approach different task types.

## Known Issues & Warnings
Gotchas, deprecated patterns, environment quirks.
```

### Section Guidelines

#### Quick Reference (Top Priority)
Place the most critical information first—LLMs bias toward content at the beginning and end of prompts.

```markdown
## Quick Reference

- **Build**: `npm run build`
- **Test**: `npm run test:unit`
- **Lint**: `npm run lint:fix`
- **Branch naming**: `feature/TICKET-123-description`
```

#### Architecture Overview

Provide a mental map of the codebase. Essential for navigation efficiency.

```markdown
## Architecture

FastAPI REST API with PostgreSQL backend.

### Key Directories
- `app/api/` - Route handlers (versioned under v1/, v2/)
- `app/models/` - SQLAlchemy ORM models
- `app/services/` - Business logic layer
- `app/core/` - Config, security, dependencies
- `tests/` - Mirrors app/ structure
```

#### Development Standards

Be prescriptive but not exhaustive—let linters handle style.

```markdown
## Standards

- Type hints required on all functions
- Docstrings for public APIs (Google style)
- 100 character line limit
- Prefer composition over inheritance
```

#### Domain Context

Project-specific knowledge that can't be inferred from code.

```markdown
## Domain Context

### User Tiers
- FREE: 5 requests/day, no export
- PRO: Unlimited requests, CSV export
- ENTERPRISE: API access, SSO

### Critical Business Rules
- Never delete user data, only soft-delete
- All financial operations require audit logging
- PII must be encrypted at rest
```

---

## The Three Pillars: WHAT, WHY, HOW

Every effective CLAUDE.md answers three fundamental questions.

### WHAT: Project Context

Tell Claude about the tech stack, architecture, and project structure.

```markdown
## What This Project Is

A distributed task queue built on Redis and PostgreSQL.

### Tech Stack
- Python 3.11+ with FastAPI
- Celery for async task processing
- Redis for caching and message broker
- PostgreSQL 15 with SQLAlchemy 2.0
- Docker Compose for local development

### Project Structure
src/
├── api/          # HTTP endpoints
├── workers/      # Celery task definitions
├── models/       # Database models
├── services/     # Business logic
└── utils/        # Shared utilities
```

### WHY: Purpose and Rationale

Explain the purpose and reasoning behind architectural decisions.

```markdown
## Why It's Built This Way

### Why Celery over asyncio?
We need cross-process task distribution for CPU-bound jobs.
Asyncio would create GIL contention on heavy computation.

### Why separate services/ from api/?
API handlers should be thin orchestrators.
Business logic in services/ enables reuse from workers and CLI.

### Why PostgreSQL for everything?
Single database simplifies transactions and reduces operational overhead.
We use JSONB columns where flexibility > schema.
```

### HOW: Working Instructions

Tell Claude how to work effectively within this project.

```markdown
## How to Work Here

### Before Writing Code
1. Check if similar patterns exist in the codebase
2. Run `grep -r "class.*Service" src/services/` to find service patterns
3. If modifying API, check OpenAPI spec at `/docs`

### When Writing Tests
- Unit tests go in `tests/unit/` mirroring `src/` structure
- Integration tests in `tests/integration/` need Docker
- Run single test: `pytest tests/unit/test_foo.py::test_specific -v`

### When Committing
- Use conventional commits: `feat:`, `fix:`, `docs:`, `refactor:`
- Include ticket number: `feat(auth): add SSO login [PROJ-123]`
- Squash WIP commits before PR
```

---

## Monorepo Strategies

### The Hierarchical Approach

For large monorepos, use a tree of CLAUDE.md files that progressively disclose context.

```
repo-root/
├── CLAUDE.md                 # Universal standards + task routing
├── apps/
│   ├── web/
│   │   └── CLAUDE.md         # Frontend specifics
│   └── api/
│       └── CLAUDE.md         # Backend specifics
└── packages/
    └── ui/
        └── CLAUDE.md         # Component library patterns
```

### Root-Level Task Router

The root CLAUDE.md should route to specific contexts:

```markdown
# Acme Corp Monorepo

## Task Routing

When working on tasks, read the appropriate context:

- **Frontend work**: Read `@apps/web/CLAUDE.md`
- **API development**: Read `@apps/api/CLAUDE.md`
- **UI components**: Read `@packages/ui/CLAUDE.md`
- **Infrastructure**: Read `@infrastructure/CLAUDE.md`
- **Database migrations**: Read `@database/CLAUDE.md`

## Universal Standards

- All code must pass CI before merge
- Branch from `develop`, PR to `develop`
- Semantic versioning for all packages
```

### Context Reduction Strategy

If your CLAUDE.md exceeds 10k words:

1. **Split by domain**: Each major module gets its own file
2. **Lazy load references**: Use `See docs/testing.md` instead of `@docs/testing.md`
   - `@` syntax loads immediately (increases memory)
   - Plain references let Claude load on-demand
3. **Compress similar information**: Convert lists to tables
4. **Remove redundancy**: Eliminate duplicate instructions

### Size Management Example

**Before (47k words)**:
```markdown
## Frontend Guidelines
[2000 words of React patterns]

## Backend Guidelines
[2000 words of FastAPI patterns]

## Testing Guidelines
[3000 words of pytest patterns]
```

**After (9k words)**:
```markdown
## Guidelines

See domain-specific docs:
- Frontend: `docs/frontend-guide.md`
- Backend: `docs/backend-guide.md`
- Testing: `docs/testing-guide.md`

Claude should read these when working in respective areas.
```

---

## Context Engineering Principles

### The Primacy & Recency Effect

LLMs bias toward instructions at:
1. **The very beginning** (system message + CLAUDE.md start)
2. **The very end** (most recent user messages)

**Implication**: Put critical instructions at the TOP of your CLAUDE.md.

### Instruction Interference

As instruction count increases, adherence decreases uniformly—not just for later instructions, but for ALL of them.

**Implication**: Fewer, higher-quality instructions > many detailed ones.

### In-Context Learning

LLMs learn from patterns in their context. If your codebase follows conventions, Claude will tend to follow them without explicit instruction.

**Implication**: Well-structured code reduces CLAUDE.md requirements.

### Emphasis Techniques

When instructions must be followed, use emphasis sparingly:

```markdown
IMPORTANT: Always run tests before committing.
CRITICAL: Never commit directly to main.
YOU MUST: Include type hints on all public functions.
```

**Warning**: Overuse of emphasis dilutes its effectiveness.

### The Prompt Improver

Anthropic recommends occasionally running CLAUDE.md through their [prompt improver](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-improver) to optimize phrasing.

---

## What NOT to Include

### ❌ Code Style Guidelines in Detail

**Why**: Use linters instead. They're faster, cheaper, and deterministic.

**Bad**:
```markdown
## Code Style
- Use 2 spaces for indentation
- No trailing whitespace
- Semicolons required
- Single quotes for strings
- Maximum line length 80 characters
```

**Good**:
```markdown
## Code Style
Run `npm run lint:fix` after changes. See `.eslintrc` for rules.
```

### ❌ Information Claude Can Discover

**Why**: Wastes context on information Claude can grep/read.

**Bad**:
```markdown
## Available Utilities
- formatDate(date) - formats dates
- parseConfig(path) - parses config files
- validateEmail(email) - validates emails
```

**Good**:
```markdown
## Utilities
Check `src/utils/` for helper functions. Use existing utilities before creating new ones.
```

### ❌ Overly Specific Hotfixes

**Why**: Narrow instructions that don't apply universally degrade overall performance.

**Bad**:
```markdown
When working on the UserProfile component, don't use useState for the avatar URL.
```

**Good**: Fix the code or add a code comment explaining the constraint.

### ❌ Sensitive Information

**Why**: Security risk, especially if committed to version control.

**Never Include**:
- API keys or secrets
- Database connection strings
- Internal security vulnerability details
- Personal access tokens

### ❌ Everything Theoretically Needed

**Why**: Your CLAUDE.md should address real friction, not imagined scenarios.

**Approach**:
1. Start minimal
2. Add instructions when you find yourself repeating corrections
3. Use the `#` key to add notes during sessions
4. Review and prune regularly

---

## Custom Slash Commands

### What Are Slash Commands?

Markdown files in `.claude/commands/` that become available via `/` menu. They're reusable prompt templates.

### File Structure

```
.claude/
└── commands/
    ├── review.md           # /project:review
    ├── test-component.md   # /project:test-component
    └── fix-issue.md        # /project:fix-issue
```

Personal commands (all projects):
```
~/.claude/
└── commands/
    ├── debug.md            # /user:debug
    └── refactor.md         # /user:refactor
```

### Command Syntax

Use `$ARGUMENTS` for parameters:

```markdown
# /project:fix-issue

Analyze and fix GitHub issue: $ARGUMENTS

## Process

1. Fetch issue details: `gh issue view $ARGUMENTS`
2. Understand the problem
3. Search for relevant code
4. Implement fix
5. Write tests
6. Commit with message referencing issue
7. Create PR
```

Usage: `/project:fix-issue 1234`

### Numbered Arguments

For multiple parameters use `$1`, `$2`, etc:

```markdown
# /project:compare

Compare implementations of $1 and $2.
Show differences in approach, performance implications, and recommend which to keep.
```

Usage: `/project:compare UserService AuthService`

### Best Practices

1. **Keep commands simple**: If it needs extensive documentation, it's too complex
2. **Don't replace CLAUDE.md**: Commands are shortcuts, not instruction manuals
3. **Use for workflows**: Multi-step processes benefit most from commands
4. **Let Claude create them**: Ask Claude to make a command for workflows you repeat

**Example request**:
> "Create a custom slash command called /security-review that checks for common vulnerabilities, secrets in code, and SQL injection risks."

---

## Subagents Configuration

### What Are Subagents?

Specialized AI assistants that handle specific task types in isolated context windows. They prevent cross-contamination between different tasks.

### Built-in Subagents

| Subagent | Purpose | Tools |
|----------|---------|-------|
| `Explore` | Read-only codebase search | Read, Grep, Glob |
| `Plan` | Research for planning mode | Read, Grep, Glob |
| `general-purpose` | Complex multi-step tasks | Full toolset |

### Custom Subagent Configuration

Create `.claude/agents/[name].md`:

```markdown
---
name: security-auditor
description: Performs security analysis without modifying code
tools:
  - Read
  - Grep
  - Glob
  - WebFetch
model: claude-sonnet-4-5-20250929
---

# Security Auditor

You are a security-focused code reviewer. Your job is to identify:
- Potential vulnerabilities
- Secret exposure risks
- Injection attack vectors
- Authentication/authorization issues

NEVER suggest fixes in this role. Only identify and report issues.
Report findings in severity order: CRITICAL, HIGH, MEDIUM, LOW.
```

### Subagent Locations

- **Project**: `.claude/agents/[name].md` (shared with team)
- **User**: `~/.claude/agents/[name].md` (personal)

### Tool Restrictions

Limit subagent capabilities based on their role:

**Read-only agents** (reviewers, auditors):
```yaml
tools:
  - Read
  - Grep
  - Glob
```

**Research agents** (analysts):
```yaml
tools:
  - Read
  - Grep
  - Glob
  - WebFetch
  - WebSearch
```

**Code writers** (implementers):
```yaml
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
```

### Alternative: Master-Clone Architecture

Instead of specialized subagents, let the main agent delegate to copies of itself:

```markdown
## Delegation Pattern

When tasks require isolated context:
1. Use `Task(...)` to spawn a general-purpose clone
2. Put all context needs in this CLAUDE.md
3. Let the main agent decide when/how to delegate

This preserves holistic reasoning while managing context.
```

---

## MCP Integration

### What is MCP?

Model Context Protocol allows Claude to connect to external tools and data sources.

### Configuration Locations

```
~/.claude.json                    # Global MCP servers
.claude/settings.json             # Project MCP servers
.mcp.json                         # Checked-in (team-shared)
```

### Example .mcp.json

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed"]
    },
    "puppeteer": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-puppeteer"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@anthropic/mcp-server-github"],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

### Documenting MCP Usage in CLAUDE.md

```markdown
## Available MCP Tools

### Puppeteer (Browser Automation)
- Use for visual testing and screenshots
- Available commands: navigate, screenshot, click, type
- Prefer for UI validation over manual testing

### GitHub MCP
- Use for: creating issues, PRs, fetching comments
- Prefer over `gh` CLI for complex operations
- Rate limited: avoid rapid successive calls

### Database MCP
- Read-only access to staging database
- Use for: data exploration, query validation
- NEVER use for production data
```

### Debug Flag

When MCP tools aren't appearing:
```bash
claude --mcp-debug
```

---

## Companion: settings.json

### What settings.json Does

Complements CLAUDE.md with:
- Permission rules
- Environment variables
- Hook configurations
- Tool restrictions

### File Hierarchy

```
Enterprise managed-settings.json  (highest priority)
├── Project .claude/settings.json
│   └── Project .claude/settings.local.json
└── User ~/.claude/settings.json  (lowest priority)
```

### Example settings.json

```json
{
  "model": "claude-sonnet-4-5-20250929",
  "permissions": {
    "allow": [
      "Read",
      "Write(src/**)",
      "Edit",
      "Bash(git *)",
      "Bash(npm run *)",
      "Bash(pytest *)"
    ],
    "deny": [
      "Read(.env*)",
      "Read(secrets/**)",
      "Write(production.*)",
      "Bash(rm -rf *)",
      "Bash(sudo *)"
    ]
  },
  "env": {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "1",
    "BASH_DEFAULT_TIMEOUT_MS": "60000"
  },
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write(*.py)",
        "hooks": [
          {
            "type": "command",
            "command": "black $file && isort $file"
          }
        ]
      }
    ]
  }
}
```

### Permission Patterns

```
Tool                    # Allow all uses of tool
Tool(*)                 # Allow any argument
Tool(pattern)           # Allow matching pattern
Tool(prefix:*)          # Wildcard matching
```

**Examples**:
```json
{
  "allow": [
    "Bash(git commit:*)",      // Any git commit
    "Bash(npm run test:*)",    // Any test script
    "Write(src/**)",           // Write in src/
    "Read"                     // Read anything
  ],
  "deny": [
    "Bash(rm:*)",              // No rm commands
    "Write(*.config.*)"        // No config overwrites
  ]
}
```

### Recommended Safe Defaults

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "LS",
      "Edit",
      "Write(src/**)",
      "Write(tests/**)",
      "Bash(git status)",
      "Bash(git diff:*)",
      "Bash(git log:*)",
      "Bash(npm run lint:*)",
      "Bash(npm run test:*)",
      "Bash(pytest:*)"
    ],
    "deny": [
      "Read(.env*)",
      "Read(**/secrets/**)",
      "Bash(rm -rf:*)",
      "Bash(sudo:*)",
      "Bash(curl:*)"
    ]
  }
}
```

---

## Common Workflows

### Explore → Plan → Code → Commit

The universal workflow for most tasks:

```markdown
## Standard Workflow

### 1. Explore (No Code Yet)
- Read relevant files
- Understand existing patterns
- Use Explore subagent for complex codebases
- Ask clarifying questions

### 2. Plan (Think Hard)
- Create implementation plan
- Document in scratch file or GitHub issue
- Get approval before proceeding
- Use "think" / "think hard" / "ultrathink" for complex planning

### 3. Code (Implement)
- Follow established patterns
- Write tests alongside code
- Commit logical chunks

### 4. Verify & Commit
- Run tests: `npm run test`
- Run lint: `npm run lint:fix`
- Commit with conventional message
- Create PR if appropriate
```

### Test-Driven Development

```markdown
## TDD Workflow

1. **Write failing tests first**
   - Create test file in `tests/`
   - Define expected behavior with test cases
   - Run to confirm failures: `pytest tests/test_new.py -v`

2. **Implement until tests pass**
   - Write minimal code to pass tests
   - Don't modify tests during implementation
   - Iterate until green

3. **Refactor with confidence**
   - Clean up implementation
   - Tests provide safety net

4. **Commit tests and code together**
```

### Visual Iteration

```markdown
## UI Development Workflow

1. **Get visual target**
   - Screenshot or design mock
   - Paste image or provide file path

2. **Implement first pass**
   - Build component matching visual
   - Use existing component patterns

3. **Screenshot and compare**
   - Take screenshot of result
   - Compare to target
   - Iterate until match

4. **Polish and commit**
```

### Codebase Q&A (Onboarding)

```markdown
## Onboarding Questions Claude Can Answer

- "How does authentication work in this codebase?"
- "What's the pattern for creating new API endpoints?"
- "Why did we choose X over Y?" (check git history)
- "What edge cases does UserService handle?"
- "Show me an example of the repository pattern here"

Claude will search the codebase to answer—no special prompting needed.
```

---

## Templates & Examples

### Minimal CLAUDE.md (Starter)

```markdown
# Project Name

Brief description of what this project does.

## Quick Commands

- Build: `npm run build`
- Test: `npm run test`
- Lint: `npm run lint:fix`

## Key Directories

- `src/` - Source code
- `tests/` - Test files
- `docs/` - Documentation

## Standards

- TypeScript required
- Tests for all new features
- Conventional commits

## Notes

Add project-specific gotchas here as you discover them.
```

### Full-Featured CLAUDE.md

```markdown
# Acme Task Queue

Distributed task processing system built on Celery and Redis.

## Quick Reference

| Action | Command |
|--------|---------|
| Dev server | `docker-compose up` |
| Run tests | `pytest tests/ -v` |
| Single test | `pytest tests/test_foo.py::test_bar -v` |
| Lint | `ruff check . --fix` |
| Type check | `mypy src/` |
| Migrations | `alembic upgrade head` |

## Architecture

```
src/
├── api/           # FastAPI routes
│   ├── v1/        # Version 1 endpoints
│   └── deps.py    # Dependency injection
├── workers/       # Celery task definitions
│   ├── tasks.py   # Task implementations
│   └── celery.py  # Celery configuration
├── models/        # SQLAlchemy models
├── services/      # Business logic
├── schemas/       # Pydantic models
└── core/          # Config, security, utils
```

## Standards

- **Type hints**: Required on all functions
- **Docstrings**: Google style for public APIs
- **Testing**: pytest with fixtures in `conftest.py`
- **Commits**: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

## Domain Context

### Task States
- PENDING → RUNNING → SUCCESS | FAILURE | RETRY
- Max retries: 3 with exponential backoff

### Priority Levels
- CRITICAL: Process immediately (payment, auth)
- HIGH: Within 1 minute (notifications)
- NORMAL: Best effort (analytics, reports)
- LOW: Background (cleanup, archival)

## Workflow Guidance

### Before Implementing Features
1. Check if similar patterns exist (`grep -r "class.*Service"`)
2. Review related tests for expected behavior
3. Discuss approach if changing core abstractions

### When Writing Workers
- Always use `@celery.task(bind=True)` for self reference
- Include proper error handling with retries
- Log at INFO level for success, ERROR for failures

### When Modifying API
- Update OpenAPI descriptions
- Add request/response examples
- Ensure backward compatibility or version bump

## Known Issues

- Redis connection drops under heavy load—worker auto-reconnects
- Alembic migrations must be run manually in prod
- Legacy UserTask model—use TaskV2 for new code

## MCP Tools Available

- **Database**: Read-only staging access for queries
- **Sentry**: Error tracking and reporting
- **Slack**: #dev-notifications for deployment alerts
```

### Python Project Template

```markdown
# Python Project CLAUDE.md

## Environment

- Python 3.11+
- Virtual env: `.venv/`
- Package manager: `pip` with `requirements.txt`

## Commands

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Development
pytest tests/ -v                    # All tests
pytest tests/test_foo.py -v         # Single file
pytest -k "test_name" -v            # Pattern match
python -m mypy src/                 # Type check
ruff check . --fix                  # Lint & fix

# Run
python -m src.main                  # Main entry
```

## Project Structure

```
src/
├── __init__.py
├── main.py              # Entry point
├── config.py            # Settings
├── models/              # Data models
├── services/            # Business logic
└── utils/               # Helpers
tests/
├── conftest.py          # Fixtures
├── test_models.py
└── test_services.py
```

## Standards

- Type hints on all public functions
- Docstrings (Google style) on classes and public methods
- 100 char line length (enforced by ruff)
- Prefer dataclasses over dicts for structured data

## Patterns

### Service Pattern
```python
class UserService:
    def __init__(self, db: Database):
        self.db = db

    def get_user(self, user_id: str) -> User | None:
        ...
```

### Testing Pattern
```python
@pytest.fixture
def user_service(db_session):
    return UserService(db_session)

def test_get_user(user_service, sample_user):
    result = user_service.get_user(sample_user.id)
    assert result == sample_user
```
```

### React/TypeScript Template

```markdown
# React TypeScript Project

## Commands

```bash
npm run dev          # Development server (Vite)
npm run build        # Production build
npm run test         # Vitest unit tests
npm run test:e2e     # Playwright E2E
npm run lint         # ESLint + Prettier
npm run typecheck    # TypeScript check
```

## Structure

```
src/
├── components/      # Reusable UI components
│   ├── ui/          # Primitives (Button, Input, etc.)
│   └── features/    # Feature-specific components
├── hooks/           # Custom React hooks
├── lib/             # Utilities and helpers
├── pages/           # Route components
├── services/        # API clients
├── stores/          # State management
└── types/           # TypeScript definitions
```

## Standards

- Functional components only
- Named exports (no default exports)
- Props interfaces named `[Component]Props`
- Hooks prefixed with `use`
- Services suffixed with `Service`

## Component Pattern

```tsx
interface ButtonProps {
  variant?: 'primary' | 'secondary';
  onClick: () => void;
  children: React.ReactNode;
}

export function Button({ variant = 'primary', onClick, children }: ButtonProps) {
  return (
    <button className={styles[variant]} onClick={onClick}>
      {children}
    </button>
  );
}
```

## State Management

- Local state: `useState`
- Complex local: `useReducer`
- Global state: Zustand stores in `stores/`
- Server state: TanStack Query

## Testing

- Unit: Vitest + Testing Library
- E2E: Playwright
- Coverage target: 80%+ for services, 60%+ overall
```

---

## Troubleshooting & Optimization

### Common Issues

#### Claude Ignores Instructions

**Causes**:
- Too many instructions (dilution)
- Conflicting instructions
- Instructions buried in middle of file

**Solutions**:
1. Reduce total instruction count
2. Move critical instructions to top
3. Use emphasis for must-follow rules
4. Remove redundant/conflicting content

#### CLAUDE.md Too Large

**Warning threshold**: ~40k words
**Optimal size**: <10k words

**Solutions**:
1. Split into hierarchical files (see Monorepo Strategies)
2. Move detailed docs to reference files
3. Remove info Claude can discover via grep
4. Convert verbose explanations to concise rules

#### Claude Doesn't Follow Patterns

**Cause**: Patterns described but not demonstrated

**Solution**: Point to example files instead of describing patterns:
```markdown
## Component Patterns

See `src/components/Button/Button.tsx` for the canonical component structure.
Follow this pattern for all new components.
```

#### Context Gets Polluted

**Cause**: Long sessions accumulate irrelevant information

**Solutions**:
- Use `/clear` between distinct tasks
- Use subagents for isolated work
- Use `Task(...)` for parallel exploration

### Optimization Checklist

```markdown
□ CLAUDE.md under 10k words
□ Critical instructions at top
□ No detailed style guides (use linters)
□ No secrets or sensitive data
□ No information Claude can grep
□ Commands tested and accurate
□ Patterns demonstrated via example files
□ Monorepo uses hierarchical files
□ settings.json configured for safe defaults
□ Regular review and pruning
```

### The /init Command

When starting fresh or auditing existing config:

```bash
claude
/init
```

This generates a starter CLAUDE.md by analyzing:
- Package files (package.json, requirements.txt, etc.)
- Existing documentation
- Configuration files
- Code structure

**Always review generated content**—Claude may miss nuances or include unnecessary detail.

### Continuous Improvement

1. **During sessions**: Press `#` to add notes Claude should remember
2. **After friction**: Add instructions when repeating corrections
3. **Regular review**: Monthly audit to prune stale content
4. **Team sync**: Review changes in PRs like any documentation

---

## Appendix: Quick Reference Card

### File Locations
```
~/.claude/CLAUDE.md          # Global (all projects)
./CLAUDE.md                  # Project (committed)
./CLAUDE.local.md            # Project (gitignored)
.claude/settings.json        # Permissions & config
.claude/commands/*.md        # Slash commands
.claude/agents/*.md          # Custom subagents
.mcp.json                    # MCP servers
```

### Key Commands
```
/init                        # Generate CLAUDE.md
/clear                       # Reset context
/permissions                 # Manage tool access
/compact                     # Compress context
#                            # Add note to CLAUDE.md
```

### Permission Patterns
```
Read                         # Read any file
Write(src/**)                # Write in src/
Bash(git *)                  # Any git command
Bash(npm run test:*)         # Test scripts
```

### Thinking Levels
```
"think"       → Standard extended thinking
"think hard"  → More thinking budget
"think harder"→ Even more
"ultrathink"  → Maximum thinking
```

---

## About This Guide

Created by **CortaLabs** for internal agent orchestration and shared with the community.

This guide synthesizes best practices from:
- Anthropic's official documentation
- Anthropic Engineering blog posts
- Community expertise (HumanLayer, ClaudeLog, etc.)
- Production experience with multi-agent systems

**Contributing**: This is a living document. Update as new patterns emerge and tooling evolves.

---

*"The best configuration is one that evolves with your needs."* — Anthropic Engineering
