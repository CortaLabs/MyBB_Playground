"""Language file validation tools for MyBB plugin workspaces.

This module provides the LanguageValidator class for validating language
files against code usage in plugin workspaces. It scans:
- Language file definitions: $l['key'] = 'value';
- PHP code usage: $lang->key
- Template usage: {$lang->key}

The validator works ONLY on plugin workspace files, not TestForum.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from difflib import SequenceMatcher


@dataclass
class LangDefinition:
    """A language definition found in a .lang.php file."""
    key: str
    value: str
    file: Path
    line: int
    is_admin: bool = False


@dataclass
class LangUsage:
    """A language usage found in PHP or template code."""
    key: str
    file: Path
    line: int
    context: str  # 'php' or 'template'
    is_admin_context: bool = False
    has_fallback: bool = False  # e.g., $lang->key ?? 'default'
    is_dynamic: bool = False  # e.g., $lang->$varname


@dataclass
class ValidationReport:
    """Complete validation report for a plugin."""
    codename: str
    definitions: List[LangDefinition] = field(default_factory=list)
    usages: List[LangUsage] = field(default_factory=list)
    missing: List[LangUsage] = field(default_factory=list)  # Used but not defined
    unused: List[LangDefinition] = field(default_factory=list)  # Defined but not used
    typos: List[Tuple[str, str, float]] = field(default_factory=list)  # (used, defined, similarity)
    dynamic_usages: List[LangUsage] = field(default_factory=list)  # Can't validate
    errors: List[str] = field(default_factory=list)


class LanguageValidator:
    """Validates MyBB language files against code usage in plugin workspaces."""

    # Patterns to match language constructs
    # Matches: $l['key'] or $l["key"] - the definition pattern
    LANG_DEF_PATTERN = re.compile(
        r"\$l\[(['\"])([a-zA-Z_][a-zA-Z0-9_]*)\1\]\s*=\s*(['\"])(.+?)\3\s*;",
        re.MULTILINE
    )

    # Matches: $lang->key or $this->lang->key - static property access in PHP
    # Uses word boundary + negative lookahead to exclude method calls like $lang->load()
    # Supports both procedural ($lang->) and OOP ($this->lang->) patterns
    PHP_USAGE_PATTERN = re.compile(
        r'(?:\$this->lang->|\$lang->)([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*\()'
    )

    # Matches: $lang->$variable or $this->lang->$variable - dynamic property access (can't validate)
    PHP_DYNAMIC_PATTERN = re.compile(
        r'(?:\$this->lang->|\$lang->)\$([a-zA-Z_][a-zA-Z0-9_]*)'
    )

    # Matches: $lang->{'prefix_'.$var} or $this->lang->{'prefix_'.$var} - curly brace dynamic access
    # Extracts the static prefix for partial matching (e.g., 'invite_type_' from 'invite_type_'.$type)
    PHP_CURLY_DYNAMIC_PATTERN = re.compile(
        r'(?:\$this->lang->|\$lang->)\{[\'"]([a-zA-Z_][a-zA-Z0-9_]*)[\'"]'
    )

    # Matches: {$lang->key} in templates
    TEMPLATE_USAGE_PATTERN = re.compile(
        r'\{\$lang->([a-zA-Z_][a-zA-Z0-9_]*)\}'
    )

    # Matches: $lang->key ?? 'fallback' or $this->lang->key ?? 'fallback' (null coalescing)
    FALLBACK_PATTERN = re.compile(
        r'(?:\$this->lang->|\$lang->)([a-zA-Z_][a-zA-Z0-9_]*)\s*\?\?'
    )

    # MyBB $lang method calls (not properties) - should never be flagged
    LANG_METHODS = frozenset([
        'load', 'sprintf', 'parse', 'set_path'
    ])

    # MyBB core language variables we should ignore (common ones)
    CORE_LANG_VARS = frozenset([
        'yes', 'no', 'on', 'off', 'none', 'all', 'and', 'or',
        'username', 'password', 'email', 'submit', 'cancel', 'save',
        'delete', 'edit', 'search', 'logout', 'login', 'register',
        'home', 'forum', 'forums', 'thread', 'threads', 'post', 'posts',
        'reply', 'quote', 'profile', 'member', 'members', 'user', 'users',
        'admin', 'moderator', 'settings', 'options', 'help', 'error',
        'warning', 'success', 'info', 'unknown_error', 'invalid_action',
        'no_permission', 'redirect', 'loading', 'please_wait', 'reset',
        'nav_sep', 'posted', 'by', 'at', 'today', 'yesterday',
        'welcome_back', 'logged_in_as', 'not_logged_in', 'close',
        'unknown_error', 'invalid_post_code', 'nav_panel', 'nav_calendar',
        'nav_search', 'nav_profile', 'nav_pms', 'nav_logout', 'nav_login',
        'nav_register', 'nav_memberlist', 'nav_portal', 'nav_help',
        'alt_trow', 'trow', 'pages', 'page', 'next', 'previous', 'first', 'last'
    ])

    def __init__(self, repo_root: Path):
        """Initialize the validator.

        Args:
            repo_root: Path to the repository root (contains plugin_manager/)
        """
        self.repo_root = Path(repo_root)
        self._project_db = None

    @property
    def project_db(self):
        """Lazy-load the ProjectDatabase."""
        if self._project_db is None:
            if str(self.repo_root) not in sys.path:
                sys.path.insert(0, str(self.repo_root))

            from plugin_manager.database import ProjectDatabase
            from plugin_manager.config import Config

            config = Config(repo_root=self.repo_root)
            self._project_db = ProjectDatabase(config.database_path)

        return self._project_db

    def get_workspace_path(self, codename: str) -> Optional[Path]:
        """Get the workspace path for a plugin by codename.

        Args:
            codename: Plugin codename

        Returns:
            Absolute path to plugin workspace, or None if not found
        """
        project = self.project_db.get_project(codename)
        if project:
            return self.repo_root / project['workspace_path']
        return None

    def scan_definitions(self, lang_file: Path, is_admin: bool = False) -> List[LangDefinition]:
        """Extract all $l['key'] definitions from a language file.

        Args:
            lang_file: Path to the .lang.php file
            is_admin: Whether this is an admin language file

        Returns:
            List of LangDefinition objects
        """
        definitions = []

        if not lang_file.exists():
            return definitions

        content = lang_file.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')

        # Find definitions line by line for accurate line numbers
        for line_num, line in enumerate(lines, 1):
            # Match $l['key'] = 'value'; or $l["key"] = "value";
            match = re.search(r"\$l\[(['\"])([a-zA-Z_][a-zA-Z0-9_]*)\1\]", line)
            if match:
                key = match.group(2)
                # Try to extract value (simplified - may not handle multiline)
                value_match = re.search(r"=\s*(['\"])(.+?)\1\s*;", line)
                value = value_match.group(2) if value_match else ""

                definitions.append(LangDefinition(
                    key=key,
                    value=value,
                    file=lang_file,
                    line=line_num,
                    is_admin=is_admin
                ))

        return definitions

    def scan_php_usages(self, php_file: Path, is_admin_context: bool = False) -> List[LangUsage]:
        """Find all $lang->key usages in a PHP file.

        Args:
            php_file: Path to the PHP file
            is_admin_context: Whether this file is in an admin context

        Returns:
            List of LangUsage objects
        """
        usages = []

        if not php_file.exists():
            return usages

        content = php_file.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.strip()
            if stripped.startswith('//') or stripped.startswith('*') or stripped.startswith('/*'):
                continue

            # Check for dynamic usage first ($lang->$var pattern)
            dynamic_matches = self.PHP_DYNAMIC_PATTERN.findall(line)
            for var_name in dynamic_matches:
                usages.append(LangUsage(
                    key=f"${var_name}",  # Mark as dynamic
                    file=php_file,
                    line=line_num,
                    context='php',
                    is_admin_context=is_admin_context,
                    is_dynamic=True
                ))

            # Check for curly brace dynamic usage ($lang->{'prefix_'.$var} pattern)
            curly_matches = self.PHP_CURLY_DYNAMIC_PATTERN.findall(line)
            for prefix in curly_matches:
                usages.append(LangUsage(
                    key=f"{prefix}*",  # Mark as dynamic prefix pattern
                    file=php_file,
                    line=line_num,
                    context='php',
                    is_admin_context=is_admin_context,
                    is_dynamic=True
                ))

            # Check for fallback usage
            fallback_matches = self.FALLBACK_PATTERN.findall(line)
            fallback_keys = set(fallback_matches)

            # Find all static usages
            for match in self.PHP_USAGE_PATTERN.finditer(line):
                key = match.group(1)

                # Skip if this is actually a dynamic access we already caught
                if f'$lang->${key}' in line:
                    continue

                usages.append(LangUsage(
                    key=key,
                    file=php_file,
                    line=line_num,
                    context='php',
                    is_admin_context=is_admin_context,
                    has_fallback=key in fallback_keys
                ))

        return usages

    def scan_template_usages(self, template_file: Path) -> List[LangUsage]:
        """Find all {$lang->key} usages in a template file.

        Args:
            template_file: Path to the template file

        Returns:
            List of LangUsage objects
        """
        usages = []

        if not template_file.exists():
            return usages

        content = template_file.read_text(encoding='utf-8', errors='replace')
        lines = content.split('\n')

        for line_num, line in enumerate(lines, 1):
            for match in self.TEMPLATE_USAGE_PATTERN.finditer(line):
                key = match.group(1)
                usages.append(LangUsage(
                    key=key,
                    file=template_file,
                    line=line_num,
                    context='template',
                    is_admin_context=False  # Templates are generally frontend
                ))

        return usages

    def find_typos(
        self,
        used_keys: Set[str],
        defined_keys: Set[str],
        threshold: float = 0.8
    ) -> List[Tuple[str, str, float]]:
        """Find potential typos using fuzzy matching.

        Args:
            used_keys: Set of keys used in code
            defined_keys: Set of keys defined in lang files
            threshold: Minimum similarity ratio (0.0-1.0)

        Returns:
            List of (used_key, defined_key, similarity) tuples
        """
        typos = []
        missing_keys = used_keys - defined_keys - self.LANG_METHODS - self.CORE_LANG_VARS

        for used in missing_keys:
            best_match = None
            best_ratio = 0.0

            for defined in defined_keys:
                ratio = SequenceMatcher(None, used, defined).ratio()
                if ratio >= threshold and ratio > best_ratio:
                    best_match = defined
                    best_ratio = ratio

            if best_match and best_ratio < 1.0:  # Not exact match
                typos.append((used, best_match, best_ratio))

        return sorted(typos, key=lambda x: -x[2])  # Sort by similarity desc

    def validate(self, codename: str, include_templates: bool = True) -> ValidationReport:
        """Run full validation on a plugin's language files.

        Args:
            codename: Plugin codename
            include_templates: Whether to scan templates for {$lang->x}

        Returns:
            ValidationReport with all findings
        """
        report = ValidationReport(codename=codename)

        # Get workspace path
        workspace = self.get_workspace_path(codename)
        if not workspace or not workspace.exists():
            report.errors.append(f"Plugin '{codename}' not found in workspace database.")
            return report

        # Define paths
        lang_dir = workspace / "inc" / "languages" / "english"
        frontend_lang = lang_dir / f"{codename}.lang.php"
        admin_lang = lang_dir / "admin" / f"{codename}.lang.php"
        plugin_main = workspace / "inc" / "plugins" / f"{codename}.php"
        plugin_dir = workspace / "inc" / "plugins" / codename
        templates_dir = workspace / "templates"

        # Scan language definitions
        if frontend_lang.exists():
            report.definitions.extend(self.scan_definitions(frontend_lang, is_admin=False))
        else:
            report.errors.append(f"Frontend language file not found: {frontend_lang.relative_to(workspace)}")

        if admin_lang.exists():
            report.definitions.extend(self.scan_definitions(admin_lang, is_admin=True))

        # Scan PHP usages
        if plugin_main.exists():
            report.usages.extend(self.scan_php_usages(plugin_main, is_admin_context=False))

        if plugin_dir.exists():
            for php_file in plugin_dir.rglob("*.php"):
                is_admin = "admin" in str(php_file.relative_to(plugin_dir)).lower()
                report.usages.extend(self.scan_php_usages(php_file, is_admin_context=is_admin))

        # Scan templates
        if include_templates and templates_dir.exists():
            for template_file in templates_dir.glob("*.html"):
                report.usages.extend(self.scan_template_usages(template_file))

        # Separate dynamic usages
        report.dynamic_usages = [u for u in report.usages if u.is_dynamic]
        static_usages = [u for u in report.usages if not u.is_dynamic]

        # Build key sets
        defined_keys = {d.key for d in report.definitions}
        used_keys = {u.key for u in static_usages}

        # Find missing (used but not defined, excluding core vars and methods)
        missing_keys = used_keys - defined_keys - self.CORE_LANG_VARS - self.LANG_METHODS
        report.missing = [u for u in static_usages if u.key in missing_keys]

        # Find unused (defined but not used)
        unused_keys = defined_keys - used_keys
        report.unused = [d for d in report.definitions if d.key in unused_keys]

        # Find potential typos
        report.typos = self.find_typos(used_keys, defined_keys)

        return report

    def generate_stub(
        self,
        codename: str,
        default_values: str = "placeholder"
    ) -> Tuple[str, List[str]]:
        """Generate missing language definitions as PHP code.

        Args:
            codename: Plugin codename
            default_values: How to generate default values:
                - 'empty': $l['key'] = '';
                - 'key_as_value': $l['key'] = 'key';
                - 'placeholder': $l['key'] = '[key]';

        Returns:
            Tuple of (PHP code string, list of missing keys)
        """
        report = self.validate(codename)

        if not report.missing:
            return "// No missing definitions found.", []

        # Get unique missing keys
        missing_keys = sorted(set(u.key for u in report.missing))

        lines = [
            f"// Missing language definitions for {codename}",
            f"// Generated by mybb_lang_generate_stub",
            ""
        ]

        for key in missing_keys:
            if default_values == "empty":
                value = ""
            elif default_values == "key_as_value":
                # Convert snake_case to Title Case
                value = key.replace('_', ' ').title()
            else:  # placeholder
                value = f"[{key}]"

            lines.append(f"$l['{key}'] = '{value}';")

        return "\n".join(lines), missing_keys

    def scan_path(self, path: Path, output: str = "grouped") -> Dict[str, Any]:
        """Scan a file or directory for language variable usage.

        Args:
            path: File or directory to scan
            output: Output format ('list', 'grouped', 'json')

        Returns:
            Dict with scan results
        """
        usages: List[LangUsage] = []
        path = Path(path)

        if path.is_file():
            if path.suffix == '.php':
                usages.extend(self.scan_php_usages(path))
            elif path.suffix == '.html':
                usages.extend(self.scan_template_usages(path))
        elif path.is_dir():
            for php_file in path.rglob("*.php"):
                usages.extend(self.scan_php_usages(php_file))
            for html_file in path.rglob("*.html"):
                usages.extend(self.scan_template_usages(html_file))

        if output == "list":
            return {
                "usages": [
                    {"key": u.key, "file": str(u.file), "line": u.line, "context": u.context}
                    for u in usages
                ]
            }
        elif output == "grouped":
            grouped: Dict[str, List[dict]] = {}
            for u in usages:
                if u.key not in grouped:
                    grouped[u.key] = []
                grouped[u.key].append({
                    "file": str(u.file),
                    "line": u.line,
                    "context": u.context
                })
            return {"usages": grouped, "total_keys": len(grouped), "total_usages": len(usages)}
        else:  # json
            return {
                "path": str(path),
                "usages": [
                    {
                        "key": u.key,
                        "file": str(u.file),
                        "line": u.line,
                        "context": u.context,
                        "is_admin": u.is_admin_context,
                        "has_fallback": u.has_fallback,
                        "is_dynamic": u.is_dynamic
                    }
                    for u in usages
                ]
            }
