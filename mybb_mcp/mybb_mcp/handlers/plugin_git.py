"""Git handlers for plugin/theme nested repositories."""

import subprocess
import json
import sys
from pathlib import Path
from typing import Any, Optional, Dict, List

# Add plugin_manager to path for ForgeConfig
# Path: handlers -> mybb_mcp -> mybb_mcp -> MyBB_Playground
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "plugin_manager"))
from forge_config import ForgeConfig


def get_plugin_path(config: Any, codename: str, visibility: str = "public") -> Path:
    """Get the path to a plugin workspace directory."""
    repo_root = Path(config.mybb_root).parent
    return repo_root / "plugin_manager" / "plugins" / visibility / codename


def get_theme_path(config: Any, codename: str) -> Path:
    """Get the path to a theme workspace directory."""
    repo_root = Path(config.mybb_root).parent
    return repo_root / "plugin_manager" / "themes" / codename


def run_git(cwd: Path, *args, timeout: int = 30) -> subprocess.CompletedProcess:
    """Run a git command in a directory."""
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=timeout
    )


def has_git(path: Path) -> bool:
    """Check if a directory has git initialized."""
    return (path / ".git").exists()


def get_git_remote(path: Path) -> Optional[str]:
    """Get the origin remote URL if set."""
    if not has_git(path):
        return None
    result = run_git(path, "remote", "get-url", "origin")
    if result.returncode == 0:
        return result.stdout.strip()
    return None


async def handle_plugin_git_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all plugins/themes that have git initialized.

    Args:
        args: Tool arguments:
            - type (str, optional): "plugins", "themes", or "all" (default: "all")
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Formatted list of git-enabled plugins/themes
    """
    item_type = args.get("type", "all")
    repo_root = Path(config.mybb_root).parent

    results = []

    # Check plugins
    if item_type in ("plugins", "all"):
        for visibility in ("public", "private"):
            plugins_dir = repo_root / "plugin_manager" / "plugins" / visibility
            if plugins_dir.exists():
                for plugin_dir in plugins_dir.iterdir():
                    if plugin_dir.is_dir() and not plugin_dir.name.startswith('.'):
                        if has_git(plugin_dir):
                            remote = get_git_remote(plugin_dir) or "no remote"
                            results.append({
                                "type": "plugin",
                                "visibility": visibility,
                                "codename": plugin_dir.name,
                                "path": str(plugin_dir.relative_to(repo_root)),
                                "remote": remote
                            })

    # Check themes
    if item_type in ("themes", "all"):
        themes_dir = repo_root / "plugin_manager" / "themes"
        if themes_dir.exists():
            for theme_dir in themes_dir.iterdir():
                if theme_dir.is_dir() and not theme_dir.name.startswith('.'):
                    if has_git(theme_dir):
                        remote = get_git_remote(theme_dir) or "no remote"
                        results.append({
                            "type": "theme",
                            "visibility": "n/a",
                            "codename": theme_dir.name,
                            "path": str(theme_dir.relative_to(repo_root)),
                            "remote": remote
                        })

    if not results:
        return "No plugins or themes have git initialized.\n\nUse `mybb_plugin_git_init` to initialize git for a plugin."

    # Format output
    lines = [f"# Git-Enabled {'Plugins' if item_type == 'plugins' else 'Themes' if item_type == 'themes' else 'Plugins & Themes'}\n"]

    for item in results:
        lines.append(f"## {item['codename']} ({item['type']})")
        lines.append(f"- **Path:** `{item['path']}`")
        lines.append(f"- **Visibility:** {item['visibility']}")
        lines.append(f"- **Remote:** `{item['remote']}`")
        lines.append("")

    return "\n".join(lines)


async def handle_plugin_git_init(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Initialize git in a plugin or theme directory.

    Args:
        args: Tool arguments:
            - codename (str, required): Plugin or theme codename
            - type (str, optional): "plugin" or "theme" (default: "plugin")
            - visibility (str, optional): "public" or "private" (default: "public", plugins only)
            - remote (str, optional): Remote URL to add as origin
            - branch (str, optional): Initial branch name (default: "main")
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    codename = args.get("codename")
    if not codename:
        return "Error: codename parameter is required"

    item_type = args.get("type", "plugin")
    visibility = args.get("visibility", "public")
    remote = args.get("remote")
    branch = args.get("branch", "main")

    # Get path
    if item_type == "theme":
        path = get_theme_path(config, codename)
    else:
        path = get_plugin_path(config, codename, visibility)

    if not path.exists():
        return f"Error: {item_type} '{codename}' not found at `{path}`"

    if has_git(path):
        existing_remote = get_git_remote(path)
        if existing_remote:
            return f"Git already initialized for '{codename}' with remote: `{existing_remote}`"
        elif remote:
            # Add remote to existing repo
            result = run_git(path, "remote", "add", "origin", remote)
            if result.returncode != 0:
                return f"Error adding remote:\n```\n{result.stderr}\n```"
            return f"✅ Added remote to existing git repo:\n- **Codename:** `{codename}`\n- **Remote:** `{remote}`"
        else:
            return f"Git already initialized for '{codename}' (no remote configured)"

    try:
        # Sync parent .gitignore to ensure this plugin is ignored (unless it's a default)
        repo_root = Path(config.mybb_root).parent
        forge_config = ForgeConfig(repo_root)
        forge_config.sync_gitignore()

        # Initialize git
        result = run_git(path, "init", "-b", branch)
        if result.returncode != 0:
            return f"Error: git init failed:\n```\n{result.stderr}\n```"

        # Add remote if provided
        if remote:
            result = run_git(path, "remote", "add", "origin", remote)
            if result.returncode != 0:
                return f"Warning: git init succeeded but adding remote failed:\n```\n{result.stderr}\n```"

        # Create .gitignore if it doesn't exist
        gitignore = path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("# Auto-generated\n*.pyc\n__pycache__/\n.DS_Store\n")

        # Initial commit
        run_git(path, "add", "-A")
        result = run_git(path, "commit", "-m", "Initial commit")

        output = [
            f"✅ Git initialized for {item_type}:",
            f"- **Codename:** `{codename}`",
            f"- **Path:** `{path}`",
            f"- **Branch:** `{branch}`",
        ]
        if remote:
            output.append(f"- **Remote:** `{remote}`")
            output.append("")
            output.append("To push: `git push -u origin main`")
        else:
            output.append("")
            output.append("No remote configured. Add one with:")
            output.append(f"```")
            output.append(f"cd {path}")
            output.append(f"git remote add origin <your-repo-url>")
            output.append(f"git push -u origin main")
            output.append(f"```")

        return "\n".join(output)

    except subprocess.TimeoutExpired:
        return "Error: git command timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def handle_plugin_github_create(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Create a GitHub repo and link it to a plugin/theme.

    Requires GitHub CLI (gh) to be authenticated.

    Args:
        args: Tool arguments:
            - codename (str, required): Plugin or theme codename
            - type (str, optional): "plugin" or "theme" (default: "plugin")
            - visibility (str, optional): "public" or "private" (default: "public", plugins only)
            - repo_visibility (str, optional): GitHub repo visibility "public" or "private" (default: "private")
            - repo_name (str, optional): GitHub repo name (default: codename)
            - description (str, optional): Repo description
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    codename = args.get("codename")
    if not codename:
        return "Error: codename parameter is required"

    item_type = args.get("type", "plugin")
    visibility = args.get("visibility", "public")
    repo_visibility = args.get("repo_visibility", "private")
    description = args.get("description", f"MyBB {item_type}: {codename}")

    # Load ForgeConfig to get repo prefix
    repo_root = Path(config.mybb_root).parent
    forge_config = ForgeConfig(repo_root)
    prefix = forge_config.github_repo_prefix

    # Apply prefix to repo name (unless user explicitly provided repo_name)
    repo_name = args.get("repo_name") or f"{prefix}{codename}"

    # Get path
    if item_type == "theme":
        path = get_theme_path(config, codename)
    else:
        path = get_plugin_path(config, codename, visibility)

    if not path.exists():
        return f"Error: {item_type} '{codename}' not found at `{path}`"

    # Check if gh CLI is available and authenticated
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode != 0:
            return "Error: GitHub CLI not authenticated. Run `gh auth login` first."
    except FileNotFoundError:
        return "Error: GitHub CLI (gh) not installed. Install from https://cli.github.com/"
    except subprocess.TimeoutExpired:
        return "Error: GitHub CLI timed out"

    # Check if already has remote
    if has_git(path):
        existing_remote = get_git_remote(path)
        if existing_remote:
            return f"Error: '{codename}' already has a remote: `{existing_remote}`\n\nRemove it first with: `git remote remove origin`"

    try:
        # Create GitHub repo
        cmd = [
            "gh", "repo", "create", repo_name,
            f"--{repo_visibility}",
            "--description", description,
            "--source", str(path),
            "--remote", "origin",
            "--push"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return f"Error creating GitHub repo:\n```\n{result.stderr}\n```"

        # Get the repo URL
        repo_url = result.stdout.strip()
        if not repo_url:
            # Try to get it from git remote
            repo_url = get_git_remote(path) or "unknown"

        return "\n".join([
            f"✅ GitHub repo created and linked:",
            f"- **Codename:** `{codename}`",
            f"- **Repo:** `{repo_name}`",
            f"- **Visibility:** {repo_visibility}",
            f"- **URL:** `{repo_url}`",
            "",
            "Initial commit pushed to GitHub."
        ])

    except subprocess.TimeoutExpired:
        return "Error: GitHub CLI timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def handle_plugin_git_status(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Get git status for a plugin or theme.

    Args:
        args: Tool arguments:
            - codename (str, required): Plugin or theme codename
            - type (str, optional): "plugin" or "theme" (default: "plugin")
            - visibility (str, optional): "public" or "private" (default: "public", plugins only)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Git status output
    """
    codename = args.get("codename")
    if not codename:
        return "Error: codename parameter is required"

    item_type = args.get("type", "plugin")
    visibility = args.get("visibility", "public")

    # Get path
    if item_type == "theme":
        path = get_theme_path(config, codename)
    else:
        path = get_plugin_path(config, codename, visibility)

    if not path.exists():
        return f"Error: {item_type} '{codename}' not found at `{path}`"

    if not has_git(path):
        return f"Git not initialized for '{codename}'. Use `mybb_plugin_git_init` first."

    try:
        result = run_git(path, "status", "--short", "--branch")
        remote = get_git_remote(path) or "no remote"

        return "\n".join([
            f"# Git Status: {codename}",
            f"- **Path:** `{path}`",
            f"- **Remote:** `{remote}`",
            "",
            "```",
            result.stdout.strip() if result.stdout.strip() else "(clean)",
            "```"
        ])

    except Exception as e:
        return f"Error: {str(e)}"


async def handle_plugin_git_commit(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Commit changes in a plugin or theme repository.

    Args:
        args: Tool arguments:
            - codename (str, required): Plugin or theme codename
            - message (str, required): Commit message
            - type (str, optional): "plugin" or "theme" (default: "plugin")
            - visibility (str, optional): "public" or "private" (default: "public", plugins only)
            - files (list, optional): Specific files to stage and commit (relative to plugin root).
                                      If omitted, stages all changes (-A).
                                      Useful when multiple agents work on same repo.
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    codename = args.get("codename")
    if not codename:
        return "Error: codename parameter is required"

    message = args.get("message")
    if not message:
        return "Error: message parameter is required"

    item_type = args.get("type", "plugin")
    visibility = args.get("visibility", "public")
    files = args.get("files")  # Optional: list of specific files to commit

    # Get path
    if item_type == "theme":
        path = get_theme_path(config, codename)
    else:
        path = get_plugin_path(config, codename, visibility)

    if not path.exists():
        return f"Error: {item_type} '{codename}' not found at `{path}`"

    if not has_git(path):
        return f"Git not initialized for '{codename}'. Use `mybb_plugin_git_init` first."

    try:
        # Check if there are changes to commit
        status = run_git(path, "status", "--porcelain")
        if not status.stdout.strip():
            return f"Nothing to commit for '{codename}' - working tree clean."

        # Stage changes
        if files:
            # Stage only specified files
            staged_files = []
            missing_files = []
            for f in files:
                file_path = path / f
                if file_path.exists() or f in status.stdout:  # exists or is tracked (deleted)
                    result = run_git(path, "add", f)
                    if result.returncode == 0:
                        staged_files.append(f)
                    else:
                        missing_files.append(f)
                else:
                    missing_files.append(f)

            if not staged_files:
                return f"Error: None of the specified files could be staged:\n- " + "\n- ".join(missing_files)

            if missing_files:
                warning = f"\n\n⚠️ Warning: Could not stage: {', '.join(missing_files)}"
            else:
                warning = ""
        else:
            # Stage all changes
            run_git(path, "add", "-A")
            staged_files = None  # indicates all files
            warning = ""

        # Commit
        result = run_git(path, "commit", "-m", message)
        if result.returncode != 0:
            # Check if nothing was staged
            if "nothing to commit" in result.stdout.lower() or "nothing to commit" in result.stderr.lower():
                return f"Nothing to commit for '{codename}' - specified files have no changes."
            return f"Error committing:\n```\n{result.stderr}\n```"

        # Get commit hash
        hash_result = run_git(path, "rev-parse", "--short", "HEAD")
        commit_hash = hash_result.stdout.strip()

        output = [
            f"✅ Committed changes to '{codename}'",
            f"- **Commit:** `{commit_hash}`",
            f"- **Message:** {message}",
        ]

        if staged_files:
            output.append(f"- **Files:** {len(staged_files)} file(s)")
            for f in staged_files[:5]:  # Show first 5
                output.append(f"  - `{f}`")
            if len(staged_files) > 5:
                output.append(f"  - ... and {len(staged_files) - 5} more")
        else:
            output.append("- **Files:** all changes")

        output.append("")
        output.append("Use `mybb_plugin_git_push` to push to remote.")

        if warning:
            output.append(warning)

        return "\n".join(output)

    except subprocess.TimeoutExpired:
        return "Error: git command timed out"
    except Exception as e:
        return f"Error: {str(e)}"


async def handle_plugin_git_push(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Push commits to remote repository.

    Args:
        args: Tool arguments:
            - codename (str, required): Plugin or theme codename
            - type (str, optional): "plugin" or "theme" (default: "plugin")
            - visibility (str, optional): "public" or "private" (default: "public", plugins only)
            - set_upstream (bool, optional): Set upstream tracking (default: False)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    codename = args.get("codename")
    if not codename:
        return "Error: codename parameter is required"

    item_type = args.get("type", "plugin")
    visibility = args.get("visibility", "public")
    set_upstream = args.get("set_upstream", False)

    # Get path
    if item_type == "theme":
        path = get_theme_path(config, codename)
    else:
        path = get_plugin_path(config, codename, visibility)

    if not path.exists():
        return f"Error: {item_type} '{codename}' not found at `{path}`"

    if not has_git(path):
        return f"Git not initialized for '{codename}'. Use `mybb_plugin_git_init` first."

    remote = get_git_remote(path)
    if not remote:
        return f"No remote configured for '{codename}'. Use `mybb_plugin_github_create` first."

    try:
        # Get current branch
        branch_result = run_git(path, "branch", "--show-current")
        branch = branch_result.stdout.strip() or "main"

        # Push
        if set_upstream:
            result = run_git(path, "push", "-u", "origin", branch, timeout=60)
        else:
            result = run_git(path, "push", timeout=60)

        if result.returncode != 0:
            # Check if it's an upstream issue
            if "no upstream branch" in result.stderr.lower() or "set-upstream" in result.stderr.lower():
                result = run_git(path, "push", "-u", "origin", branch, timeout=60)
                if result.returncode != 0:
                    return f"Error pushing:\n```\n{result.stderr}\n```"
            else:
                return f"Error pushing:\n```\n{result.stderr}\n```"

        return "\n".join([
            f"✅ Pushed '{codename}' to remote",
            f"- **Branch:** `{branch}`",
            f"- **Remote:** `{remote}`"
        ])

    except subprocess.TimeoutExpired:
        return "Error: git push timed out (60s limit)"
    except Exception as e:
        return f"Error: {str(e)}"


async def handle_plugin_git_pull(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Pull changes from remote repository.

    Args:
        args: Tool arguments:
            - codename (str, required): Plugin or theme codename
            - type (str, optional): "plugin" or "theme" (default: "plugin")
            - visibility (str, optional): "public" or "private" (default: "public", plugins only)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    codename = args.get("codename")
    if not codename:
        return "Error: codename parameter is required"

    item_type = args.get("type", "plugin")
    visibility = args.get("visibility", "public")

    # Get path
    if item_type == "theme":
        path = get_theme_path(config, codename)
    else:
        path = get_plugin_path(config, codename, visibility)

    if not path.exists():
        return f"Error: {item_type} '{codename}' not found at `{path}`"

    if not has_git(path):
        return f"Git not initialized for '{codename}'. Use `mybb_plugin_git_init` first."

    remote = get_git_remote(path)
    if not remote:
        return f"No remote configured for '{codename}'."

    try:
        result = run_git(path, "pull", timeout=60)

        if result.returncode != 0:
            return f"Error pulling:\n```\n{result.stderr}\n```"

        output = result.stdout.strip()
        if "Already up to date" in output:
            return f"'{codename}' is already up to date."

        return "\n".join([
            f"✅ Pulled changes for '{codename}'",
            f"- **Remote:** `{remote}`",
            "",
            "```",
            output,
            "```"
        ])

    except subprocess.TimeoutExpired:
        return "Error: git pull timed out (60s limit)"
    except Exception as e:
        return f"Error: {str(e)}"


# Handler registry for plugin git tools
PLUGIN_GIT_HANDLERS = {
    "mybb_plugin_git_list": handle_plugin_git_list,
    "mybb_plugin_git_init": handle_plugin_git_init,
    "mybb_plugin_github_create": handle_plugin_github_create,
    "mybb_plugin_git_status": handle_plugin_git_status,
    "mybb_plugin_git_commit": handle_plugin_git_commit,
    "mybb_plugin_git_push": handle_plugin_git_push,
    "mybb_plugin_git_pull": handle_plugin_git_pull,
}
