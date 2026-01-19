"""Git subtree handlers for MyBB Forge v2."""

import subprocess
from pathlib import Path
from typing import Any, Optional, Dict

# Import ForgeConfig from plugin_manager (proper relative import)
# Calculate path to plugin_manager from mybb_mcp directory
import sys
plugin_manager_path = str(Path(__file__).parents[3] / "plugin_manager")
if plugin_manager_path not in sys.path:
    sys.path.insert(0, plugin_manager_path)
from forge_config import ForgeConfig


async def handle_subtree_list(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """List all configured subtrees from .mybb-forge.yaml.

    Args:
        args: Tool arguments (none required)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Formatted list of subtrees with prefix, remote, branch
    """
    try:
        # Get repo root from config
        repo_root = Path(config.mybb_root).parent
        forge_config = ForgeConfig(repo_root)

        # Check if config has subtrees section
        if not hasattr(forge_config, '_config') or 'subtrees' not in forge_config._config:
            return "No subtrees configured in .mybb-forge.yaml"

        subtrees = forge_config._config['subtrees']
        if not subtrees:
            return "No subtrees configured in .mybb-forge.yaml"

        # Format output
        lines = ["# Configured Subtrees\n"]
        for key, subtree_data in subtrees.items():
            prefix = subtree_data.get('prefix', key)
            remote = subtree_data.get('remote', 'not configured')
            branch = subtree_data.get('branch', 'main')

            lines.append(f"## {key}")
            lines.append(f"- **Prefix:** `{prefix}`")
            lines.append(f"- **Remote:** `{remote}`")
            lines.append(f"- **Branch:** `{branch}`")
            lines.append("")

        return "\n".join(lines)

    except FileNotFoundError:
        return "Error: .mybb-forge.yaml not found in repository root"
    except Exception as e:
        return f"Error loading subtree config: {str(e)}"


async def handle_subtree_add(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Add a git subtree to the repository.

    Args:
        args: Tool arguments:
            - prefix (str, required): Subtree prefix path
            - remote (str, optional): Remote URL (will lookup from config if not provided)
            - branch (str, optional): Branch name (default: main)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    prefix = args.get("prefix")
    if not prefix:
        return "Error: prefix parameter is required"

    remote = args.get("remote")
    branch = args.get("branch", "main")

    try:
        # Get repo root
        repo_root = Path(config.mybb_root).parent

        # If remote not provided, lookup from config
        if not remote:
            forge_config = ForgeConfig(repo_root)
            remote = forge_config.get_subtree_remote(prefix)
            if not remote:
                return f"Error: No remote configured for subtree prefix '{prefix}' and no remote URL provided"

        # Execute git subtree add
        cmd = [
            "git", "subtree", "add",
            "--prefix", prefix,
            remote,
            branch,
            "--squash"
        ]

        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode != 0:
            return f"Error: git subtree add failed:\n```\n{result.stderr}\n```"

        return f"✅ Successfully added subtree:\n- **Prefix:** `{prefix}`\n- **Remote:** `{remote}`\n- **Branch:** `{branch}`\n\n```\n{result.stdout}\n```"

    except subprocess.TimeoutExpired:
        return "Error: git subtree add timed out after 60 seconds"
    except Exception as e:
        return f"Error executing git subtree add: {str(e)}"


async def handle_subtree_push(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Push changes to a git subtree.

    Args:
        args: Tool arguments:
            - prefix (str, required): Subtree prefix path
            - remote (str, optional): Remote URL (will lookup from config if not provided)
            - branch (str, optional): Branch name (default: main)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    prefix = args.get("prefix")
    if not prefix:
        return "Error: prefix parameter is required"

    remote = args.get("remote")
    branch = args.get("branch", "main")

    try:
        # Get repo root
        repo_root = Path(config.mybb_root).parent

        # If remote not provided, lookup from config
        if not remote:
            forge_config = ForgeConfig(repo_root)
            remote = forge_config.get_subtree_remote(prefix)
            if not remote:
                return f"Error: No remote configured for subtree prefix '{prefix}' and no remote URL provided"

        # Execute git subtree push
        cmd = [
            "git", "subtree", "push",
            "--prefix", prefix,
            remote,
            branch
        ]

        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120  # Push can take longer
        )

        if result.returncode != 0:
            return f"Error: git subtree push failed:\n```\n{result.stderr}\n```"

        return f"✅ Successfully pushed subtree:\n- **Prefix:** `{prefix}`\n- **Remote:** `{remote}`\n- **Branch:** `{branch}`\n\n```\n{result.stdout}\n```"

    except subprocess.TimeoutExpired:
        return "Error: git subtree push timed out after 120 seconds"
    except Exception as e:
        return f"Error executing git subtree push: {str(e)}"


async def handle_subtree_pull(args: dict, db: Any, config: Any, sync_service: Any) -> str:
    """Pull changes from a git subtree.

    Args:
        args: Tool arguments:
            - prefix (str, required): Subtree prefix path
            - remote (str, optional): Remote URL (will lookup from config if not provided)
            - branch (str, optional): Branch name (default: main)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Success message or error
    """
    prefix = args.get("prefix")
    if not prefix:
        return "Error: prefix parameter is required"

    remote = args.get("remote")
    branch = args.get("branch", "main")

    try:
        # Get repo root
        repo_root = Path(config.mybb_root).parent

        # If remote not provided, lookup from config
        if not remote:
            forge_config = ForgeConfig(repo_root)
            remote = forge_config.get_subtree_remote(prefix)
            if not remote:
                return f"Error: No remote configured for subtree prefix '{prefix}' and no remote URL provided"

        # Execute git subtree pull
        cmd = [
            "git", "subtree", "pull",
            "--prefix", prefix,
            remote,
            branch,
            "--squash"
        ]

        result = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=120  # Pull can take longer
        )

        if result.returncode != 0:
            return f"Error: git subtree pull failed:\n```\n{result.stderr}\n```"

        return f"✅ Successfully pulled subtree:\n- **Prefix:** `{prefix}`\n- **Remote:** `{remote}`\n- **Branch:** `{branch}`\n\n```\n{result.stdout}\n```"

    except subprocess.TimeoutExpired:
        return "Error: git subtree pull timed out after 120 seconds"
    except Exception as e:
        return f"Error executing git subtree pull: {str(e)}"


# Handler registry for subtree tools
SUBTREE_HANDLERS = {
    "mybb_subtree_list": handle_subtree_list,
    "mybb_subtree_add": handle_subtree_add,
    "mybb_subtree_push": handle_subtree_push,
    "mybb_subtree_pull": handle_subtree_pull,
}
