"""Stylesheet export and import for disk-sync.

Handles bidirectional synchronization of MyBB stylesheets between database and disk files.
"""

from pathlib import Path
from typing import Any

from mybb_mcp.db.connection import MyBBDatabase
from mybb_mcp.sync.router import PathRouter


class StylesheetExporter:
    """Exports stylesheets from database to disk files."""

    def __init__(self, db: MyBBDatabase, router: PathRouter):
        """Initialize stylesheet exporter.

        Args:
            db: MyBBDatabase instance for querying stylesheets
            router: PathRouter for building file paths
        """
        self.db = db
        self.router = router

    async def export_theme_stylesheets(self, theme_name: str) -> dict[str, Any]:
        """Export all stylesheets from a theme to disk.

        Fetches all stylesheets for the specified theme and writes them as
        .css files in the styles/{theme_name}/ directory.

        Args:
            theme_name: Theme name (e.g., "Default", "MyCustomTheme")

        Returns:
            Export statistics:
            {
                "files_exported": int,
                "directory": str,
                "theme_name": str
            }

        Raises:
            ValueError: If theme not found
        """
        # Get theme by name
        theme = self.db.get_theme_by_name(theme_name)
        if not theme:
            raise ValueError(f"Theme not found: {theme_name}")

        tid = theme['tid']

        # Fetch all stylesheets for this theme
        stylesheets = self._fetch_stylesheets(tid)

        # Export stylesheets
        stats = await self._export_stylesheets(theme_name, stylesheets)

        return stats

    def _fetch_stylesheets(self, tid: int) -> list[dict[str, Any]]:
        """Fetch all stylesheets for a theme, including inherited ones.

        MyBB themes use inheritance - child themes only store overrides.
        This method walks up the inheritance chain (via pid) and collects
        all stylesheets, with child overrides taking precedence.

        Args:
            tid: Theme ID

        Returns:
            List of stylesheet dictionaries with name and stylesheet fields
        """
        # Collect stylesheets from theme and all ancestors
        # Child overrides take precedence, so we process child first
        stylesheets_by_name: dict[str, dict[str, Any]] = {}
        current_tid = tid

        with self.db.cursor() as cur:
            while current_tid:
                # Fetch stylesheets for current theme
                cur.execute(
                    f"""
                    SELECT name, stylesheet
                    FROM {self.db.table('themestylesheets')}
                    WHERE tid = %s
                    ORDER BY name
                    """,
                    (current_tid,)
                )
                rows = cur.fetchall()

                # Add to collection (only if not already present - child takes precedence)
                for row in rows:
                    if row['name'] not in stylesheets_by_name:
                        stylesheets_by_name[row['name']] = row

                # Get parent theme ID
                cur.execute(
                    f"""
                    SELECT pid FROM {self.db.table('themes')}
                    WHERE tid = %s
                    """,
                    (current_tid,)
                )
                parent = cur.fetchone()
                current_tid = parent['pid'] if parent and parent['pid'] else None

        # Return sorted list
        return sorted(stylesheets_by_name.values(), key=lambda x: x['name'])

    async def _export_stylesheets(
        self, theme_name: str, stylesheets: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Export stylesheets to disk.

        Args:
            theme_name: Theme name
            stylesheets: List of stylesheet dictionaries

        Returns:
            Export statistics dictionary
        """
        files_exported = 0

        for stylesheet in stylesheets:
            name = stylesheet['name']
            content = stylesheet['stylesheet']

            # Build file path (name already includes .css extension)
            file_path = self.router.build_stylesheet_path(theme_name, name)

            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write stylesheet file atomically (write to .tmp, then rename)
            temp_path = file_path.with_suffix('.tmp')
            try:
                temp_path.write_text(content, encoding='utf-8')
                # Atomic rename (POSIX guarantees atomicity for same-filesystem rename)
                temp_path.rename(file_path)
            except Exception as e:
                # Clean up temp file on any error
                if temp_path.exists():
                    temp_path.unlink()
                raise

            files_exported += 1

        # Get base directory for reporting
        base_dir = self.router.sync_root / "styles" / theme_name

        return {
            "files_exported": files_exported,
            "directory": str(base_dir),
            "theme_name": theme_name
        }


class StylesheetImporter:
    """Imports stylesheets from disk files to database.

    Implements copy-on-write inheritance: when editing an inherited stylesheet,
    creates an override in the child theme rather than modifying the parent.
    """

    def __init__(self, db: MyBBDatabase):
        """Initialize stylesheet importer.

        Args:
            db: MyBBDatabase instance for stylesheet operations
        """
        self.db = db

    async def import_stylesheet(self, theme_name: str, stylesheet_name: str, content: str) -> bool:
        """Import a stylesheet from disk to database with copy-on-write inheritance.

        If stylesheet exists in this theme: UPDATE it.
        If stylesheet only exists in parent: CREATE override in this theme (copy-on-write).
        If stylesheet doesn't exist anywhere: CREATE new stylesheet.

        Args:
            theme_name: Theme name (e.g., "Default")
            stylesheet_name: Stylesheet name (e.g., "global.css")
            content: Stylesheet CSS content

        Returns:
            True if import succeeded, False otherwise

        Raises:
            ValueError: If theme not found or content is empty
        """
        # Defense-in-depth: validate content even if watcher already checked
        if not content or len(content.strip()) == 0:
            raise ValueError(f"Cannot import empty stylesheet: {stylesheet_name}")

        # Step 1: Verify theme exists and get tid
        theme = self.db.get_theme_by_name(theme_name)
        if not theme:
            raise ValueError(f"Theme not found: {theme_name}")

        tid = theme['tid']

        # Step 2: Check if stylesheet exists IN THIS SPECIFIC THEME
        existing = self.db.get_stylesheet_by_name(tid, stylesheet_name)

        if existing:
            # Stylesheet exists in this theme → UPDATE
            return self.db.update_stylesheet(existing['sid'], content)

        # Step 3: Stylesheet doesn't exist in this theme - check inheritance
        inherited = self.db.find_inherited_stylesheet(tid, stylesheet_name)

        if inherited:
            # Inherited from parent → CREATE OVERRIDE (copy-on-write)
            # Copy attachedto from parent so it applies to same pages
            sid = self.db.create_stylesheet(
                tid,
                stylesheet_name,
                content,
                attachedto=inherited.get('attachedto', '')
            )
            return sid > 0
        else:
            # Doesn't exist anywhere → CREATE NEW
            # Default attachedto empty (applies to all pages)
            sid = self.db.create_stylesheet(tid, stylesheet_name, content)
            return sid > 0
