"""Language validation handlers for MCP tools.

Handlers for language file validation:
- mybb_lang_validate: Full validation report
- mybb_lang_generate_stub: Generate missing definitions
- mybb_lang_scan_usage: Low-level usage scan
"""

from pathlib import Path
from typing import Any


async def handle_lang_validate(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Validate language files for a plugin.

    Args:
        args: Tool arguments:
            - codename: Plugin codename (required)
            - include_templates: Scan templates (default: True)
            - fix_suggestions: Include fix suggestions (default: True)
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Markdown validation report
    """
    from ..tools.lang_validator import LanguageValidator

    codename = args.get("codename")
    if not codename:
        return "Error: 'codename' parameter is required."

    include_templates = args.get("include_templates", True)
    fix_suggestions = args.get("fix_suggestions", True)

    # Get repo root from config
    repo_root = Path(config.mybb_root).parent

    validator = LanguageValidator(repo_root)
    report = validator.validate(codename, include_templates=include_templates)

    # Build markdown report
    lines = [f"# Language Validation Report: `{codename}`\n"]

    # Errors first
    if report.errors:
        lines.append("## ⚠️ Errors\n")
        for err in report.errors:
            lines.append(f"- {err}")
        lines.append("")

    # Summary
    total_defs = len(report.definitions)
    total_usages = len([u for u in report.usages if not u.is_dynamic])
    template_usages = len([u for u in report.usages if u.context == 'template'])
    missing_count = len(set(u.key for u in report.missing))
    unused_count = len(report.unused)
    dynamic_count = len(report.dynamic_usages)

    lines.append("## Summary\n")
    lines.append(f"- **Definitions:** {total_defs}")
    lines.append(f"- **Usages found:** {total_usages}")
    if template_usages:
        lines.append(f"- **Template usages:** {template_usages}")
    if missing_count:
        lines.append(f"- **Missing definitions:** {missing_count} ❌")
    if unused_count:
        lines.append(f"- **Unused definitions:** {unused_count} ⚠️")
    if dynamic_count:
        lines.append(f"- **Dynamic usages:** {dynamic_count} (can't validate)")
    lines.append("")

    # Missing definitions
    if report.missing:
        lines.append("## Missing Definitions\n")
        lines.append("Code uses these variables but they're not defined in language files:\n")
        lines.append("| Variable | Used In | Line | Context |")
        lines.append("|----------|---------|------|---------|")

        # Group by key to dedupe
        seen_keys = set()
        for usage in sorted(report.missing, key=lambda u: u.key):
            if usage.key in seen_keys:
                continue
            seen_keys.add(usage.key)

            # Get workspace-relative path
            workspace = validator.get_workspace_path(codename)
            if workspace:
                try:
                    rel_path = usage.file.relative_to(workspace)
                except ValueError:
                    rel_path = usage.file.name
            else:
                rel_path = usage.file.name

            fallback_note = " (has fallback)" if usage.has_fallback else ""
            lines.append(f"| `{usage.key}` | {rel_path} | {usage.line} | {usage.context}{fallback_note} |")

        if fix_suggestions:
            lines.append("\n**Quick fix:** Run `mybb_lang_generate_stub(codename=\"{}\")` to generate definitions.".format(codename))
        lines.append("")

    # Unused definitions
    if report.unused:
        lines.append("## Unused Definitions\n")
        lines.append("These are defined but never used in code:\n")
        lines.append("| Variable | Defined In | Line | Action |")
        lines.append("|----------|-----------|------|--------|")

        for defn in sorted(report.unused, key=lambda d: d.key):
            workspace = validator.get_workspace_path(codename)
            if workspace:
                try:
                    rel_path = defn.file.relative_to(workspace)
                except ValueError:
                    rel_path = defn.file.name
            else:
                rel_path = defn.file.name

            lines.append(f"| `{defn.key}` | {rel_path} | {defn.line} | Safe to remove |")
        lines.append("")

    # Potential typos
    if report.typos:
        lines.append("## Potential Typos\n")
        lines.append("These used variables closely match defined ones:\n")
        lines.append("| Used | Defined | Similarity |")
        lines.append("|------|---------|------------|")

        for used, defined, similarity in report.typos[:10]:  # Limit to top 10
            pct = int(similarity * 100)
            lines.append(f"| `{used}` | `{defined}` | {pct}% |")
        lines.append("")

    # Dynamic usages
    if report.dynamic_usages:
        lines.append("## Dynamic Usages (Cannot Validate)\n")
        lines.append("These use variable property names (`$lang->$var`):\n")

        for usage in report.dynamic_usages[:5]:  # Limit display
            workspace = validator.get_workspace_path(codename)
            if workspace:
                try:
                    rel_path = usage.file.relative_to(workspace)
                except ValueError:
                    rel_path = usage.file.name
            else:
                rel_path = usage.file.name

            lines.append(f"- `$lang->{usage.key}` in {rel_path}:{usage.line}")

        if len(report.dynamic_usages) > 5:
            lines.append(f"- *...and {len(report.dynamic_usages) - 5} more*")
        lines.append("")

    # Success message if clean
    if not report.missing and not report.unused and not report.typos and not report.errors:
        lines.append("## ✅ All Clear!\n")
        lines.append("No issues found. All language variables are properly defined and used.")

    return "\n".join(lines)


async def handle_lang_generate_stub(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Generate missing language definitions as PHP code.

    Args:
        args: Tool arguments:
            - codename: Plugin codename (required)
            - output: 'stub', 'patch', or 'inline' (default: 'stub')
            - default_values: 'empty', 'key_as_value', 'placeholder' (default: 'placeholder')
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Generated PHP code for missing definitions
    """
    from ..tools.lang_validator import LanguageValidator

    codename = args.get("codename")
    if not codename:
        return "Error: 'codename' parameter is required."

    output = args.get("output", "stub")
    default_values = args.get("default_values", "placeholder")

    if default_values not in ("empty", "key_as_value", "placeholder"):
        return "Error: 'default_values' must be 'empty', 'key_as_value', or 'placeholder'."

    # Get repo root from config
    repo_root = Path(config.mybb_root).parent

    validator = LanguageValidator(repo_root)
    php_code, missing_keys = validator.generate_stub(codename, default_values=default_values)

    if not missing_keys:
        return f"# No Missing Definitions\n\nPlugin `{codename}` has no missing language definitions."

    lines = [f"# Generated Language Stub for `{codename}`\n"]
    lines.append(f"**Missing keys:** {len(missing_keys)}\n")

    if output == "inline":
        lines.append("```php")
        lines.append(php_code)
        lines.append("```")
    else:
        lines.append("## PHP Code\n")
        lines.append("Add these to your language file:\n")
        lines.append("```php")
        lines.append(php_code)
        lines.append("```")

        # Show where to add
        workspace = validator.get_workspace_path(codename)
        if workspace:
            frontend_lang = workspace / "inc" / "languages" / "english" / f"{codename}.lang.php"
            admin_lang = workspace / "inc" / "languages" / "english" / "admin" / f"{codename}.lang.php"

            lines.append("\n## Where to Add\n")

            # Check which context the missing vars are from
            report = validator.validate(codename)
            admin_missing = set(u.key for u in report.missing if u.is_admin_context)
            frontend_missing = set(u.key for u in report.missing if not u.is_admin_context)

            if frontend_missing:
                rel_path = frontend_lang.relative_to(workspace)
                lines.append(f"- **Frontend:** `{rel_path}`")

            if admin_missing:
                rel_path = admin_lang.relative_to(workspace)
                lines.append(f"- **Admin:** `{rel_path}`")

    return "\n".join(lines)


async def handle_lang_scan_usage(
    args: dict, db: Any, config: Any, sync_service: Any
) -> str:
    """Scan files for language variable usage.

    Args:
        args: Tool arguments:
            - path: File or directory to scan (required)
            - output: 'list', 'grouped', or 'json' (default: 'grouped')
        db: MyBBDatabase instance (unused)
        config: Server configuration
        sync_service: Disk sync service (unused)

    Returns:
        Scan results in specified format
    """
    from ..tools.lang_validator import LanguageValidator

    path = args.get("path")
    if not path:
        return "Error: 'path' parameter is required."

    output = args.get("output", "grouped")
    if output not in ("list", "grouped", "json"):
        return "Error: 'output' must be 'list', 'grouped', or 'json'."

    # Resolve path - could be absolute or relative to repo root
    scan_path = Path(path)
    if not scan_path.is_absolute():
        repo_root = Path(config.mybb_root).parent
        scan_path = repo_root / path

    if not scan_path.exists():
        return f"Error: Path not found: {path}"

    # Get repo root from config
    repo_root = Path(config.mybb_root).parent

    validator = LanguageValidator(repo_root)
    results = validator.scan_path(scan_path, output=output)

    # Format output
    lines = [f"# Language Usage Scan: `{path}`\n"]

    if output == "grouped":
        total_keys = results.get("total_keys", 0)
        total_usages = results.get("total_usages", 0)

        lines.append(f"**Unique keys:** {total_keys}")
        lines.append(f"**Total usages:** {total_usages}\n")

        if results.get("usages"):
            lines.append("## By Variable\n")

            for key in sorted(results["usages"].keys()):
                locations = results["usages"][key]
                lines.append(f"### `{key}` ({len(locations)} usages)")

                for loc in locations[:5]:  # Limit per key
                    # Make path relative if possible
                    try:
                        rel_path = Path(loc["file"]).relative_to(repo_root)
                    except ValueError:
                        rel_path = Path(loc["file"]).name

                    lines.append(f"- {rel_path}:{loc['line']} ({loc['context']})")

                if len(locations) > 5:
                    lines.append(f"- *...and {len(locations) - 5} more*")
                lines.append("")
        else:
            lines.append("No language usages found.")

    elif output == "list":
        usages = results.get("usages", [])
        lines.append(f"**Total usages:** {len(usages)}\n")

        if usages:
            lines.append("| Variable | File | Line | Context |")
            lines.append("|----------|------|------|---------|")

            for u in usages[:50]:  # Limit display
                try:
                    rel_path = Path(u["file"]).relative_to(repo_root)
                except ValueError:
                    rel_path = Path(u["file"]).name

                lines.append(f"| `{u['key']}` | {rel_path} | {u['line']} | {u['context']} |")

            if len(usages) > 50:
                lines.append(f"\n*...and {len(usages) - 50} more*")
        else:
            lines.append("No language usages found.")

    else:  # json
        import json
        lines.append("```json")
        lines.append(json.dumps(results, indent=2, default=str))
        lines.append("```")

    return "\n".join(lines)


# Handler registry for language tools
LANGUAGE_HANDLERS = {
    "mybb_lang_validate": handle_lang_validate,
    "mybb_lang_generate_stub": handle_lang_generate_stub,
    "mybb_lang_scan_usage": handle_lang_scan_usage,
}
