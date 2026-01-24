"""Template export and import for disk-sync.

Handles bidirectional synchronization of MyBB templates between database and disk files.
"""

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from mybb_mcp.db.connection import MyBBDatabase

# Environment variable to disable template set caching for development
DISABLE_CACHE_ENV = "MYBB_SYNC_DISABLE_CACHE"
from mybb_mcp.sync.router import PathRouter
from mybb_mcp.sync.groups import TemplateGroupManager

logger = logging.getLogger(__name__)


class TemplateExporter:
    """Exports templates from database to disk files."""

    def __init__(self, db: MyBBDatabase, router: PathRouter, group_manager: TemplateGroupManager):
        """Initialize template exporter.

        Args:
            db: MyBBDatabase instance for querying templates
            router: PathRouter for building file paths
            group_manager: TemplateGroupManager for categorizing templates
        """
        self.db = db
        self.router = router
        self.group_manager = group_manager

    async def export_template_set(self, set_name: str) -> dict[str, Any]:
        """Export all templates from a template set to disk.

        Fetches both master templates (sid=-2) and custom templates for the specified
        set, organizes them into group folders, and writes to disk.

        Args:
            set_name: Template set name (e.g., "Default", "MyCustomSet")

        Returns:
            Export statistics:
            {
                "files_exported": int,
                "directory": str,
                "template_set": str,
                "groups": dict[str, int]  # group_name -> count
            }

        Raises:
            ValueError: If template set not found
        """
        # Get template set ID (run blocking DB call in thread pool to avoid blocking event loop)
        template_set = await asyncio.to_thread(self.db.get_template_set_by_name, set_name)
        if not template_set:
            raise ValueError(f"Template set not found: {set_name}")

        sid = template_set['sid']

        # Fetch all templates for this set (run blocking DB call in thread pool)
        # Query pattern from research: WHERE sid IN (-2, ?)
        templates = await asyncio.to_thread(self._fetch_templates, sid)

        # Export templates organized by group
        stats = await self._export_templates_by_group(set_name, templates, sid)

        return stats

    def _fetch_templates(self, sid: int) -> list[dict[str, Any]]:
        """Fetch all templates for a template set.

        Includes both master templates (sid=-2) and custom templates (sid=specific_id).

        Args:
            sid: Template set ID

        Returns:
            List of template dictionaries with tid, sid, title, template fields
        """
        with self.db.cursor() as cur:
            # Fetch templates matching the pattern from research doc
            # Include both master (-2) and custom (sid) templates
            cur.execute(
                f"""
                SELECT DISTINCT t.tid, t.sid, t.title, t.template,
                       m.template as master_template
                FROM {self.db.table('templates')} t
                LEFT JOIN {self.db.table('templates')} m ON
                    (m.title = t.title AND m.sid = -2)
                WHERE t.sid IN (-2, %s)
                ORDER BY t.title
                """,
                (sid,)
            )
            return cur.fetchall()

    async def _export_templates_by_group(
        self, set_name: str, templates: list[dict[str, Any]], sid: int
    ) -> dict[str, Any]:
        """Export templates organized by group folders.

        Args:
            set_name: Template set name
            templates: List of template dictionaries
            sid: Template set ID for group categorization

        Returns:
            Export statistics dictionary
        """
        files_exported = 0
        group_counts: dict[str, int] = {}

        for template in templates:
            title = template['title']
            content = template['template']
            template_sid = template['sid']

            # Determine group folder
            group_name = self.group_manager.get_group_name(title, template_sid)

            # Build file path
            file_path = self.router.build_template_path(set_name, group_name, title)

            # Create directory if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write template file atomically (write to .tmp, then rename)
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
            group_counts[group_name] = group_counts.get(group_name, 0) + 1

        # Get base directory for reporting
        base_dir = self.router.sync_root / "template_sets" / set_name

        return {
            "files_exported": files_exported,
            "directory": str(base_dir),
            "template_set": set_name,
            "groups": group_counts
        }


class TemplateImporter:
    """Imports templates from disk files to database."""

    # Cache TTL in seconds (5 minutes)
    _cache_ttl = 300

    def __init__(self, db: MyBBDatabase):
        """Initialize template importer.

        Args:
            db: MyBBDatabase instance for template operations
        """
        self.db = db
        # Template set cache: maps set_name -> sid
        self._set_cache: Dict[str, int] = {}
        # Cache timestamp tracking: maps set_name -> timestamp
        self._cache_time: Dict[str, float] = {}
        # Check if caching is disabled via env var
        self._cache_disabled = os.environ.get(DISABLE_CACHE_ENV, "").lower() in ("1", "true", "yes")
        if self._cache_disabled:
            logger.info("Template set caching DISABLED via MYBB_SYNC_DISABLE_CACHE")

    def clear_cache(self) -> None:
        """Clear the template set cache.

        Useful for development or when template sets are modified.
        """
        self._set_cache.clear()
        self._cache_time.clear()
        logger.debug("Template set cache cleared")

    def _get_template_set_id(self, set_name: str) -> Optional[int]:
        """Get template set ID with caching.

        Checks cache for valid entry, otherwise queries database and caches result.
        Cache entries expire after _cache_ttl seconds (300s = 5 minutes).

        Args:
            set_name: Template set name (e.g., "Default Templates")

        Returns:
            Template set ID (sid) if found, None otherwise

        Cache Behavior:
            - Cache hit (valid): Returns cached sid, logs cache hit
            - Cache miss (not cached): Queries DB, caches result, logs cache miss
            - Cache expired: Queries DB, updates cache, logs cache expiry
        """
        # Skip cache if disabled
        if self._cache_disabled:
            logger.debug(f"Template set cache DISABLED - querying database for: {set_name}")
            template_set = self.db.get_template_set_by_name(set_name)
            return template_set['sid'] if template_set else None

        current_time = time.time()

        # Check if set_name is in cache and not expired
        if set_name in self._set_cache:
            cache_age = current_time - self._cache_time[set_name]
            if cache_age < self._cache_ttl:
                # Cache hit - valid entry
                logger.debug(
                    f"Template set cache HIT: {set_name} (sid={self._set_cache[set_name]}, age={cache_age:.1f}s)"
                )
                return self._set_cache[set_name]
            else:
                # Cache expired
                logger.debug(
                    f"Template set cache EXPIRED: {set_name} (age={cache_age:.1f}s, ttl={self._cache_ttl}s)"
                )

        # Cache miss or expired - query database
        logger.debug(f"Template set cache MISS: {set_name} - querying database")
        template_set = self.db.get_template_set_by_name(set_name)

        if template_set:
            sid = template_set['sid']
            # Store in cache with current timestamp
            self._set_cache[set_name] = sid
            self._cache_time[set_name] = current_time
            logger.debug(f"Template set cached: {set_name} -> sid={sid}")
            return sid
        else:
            # Template set not found - do not cache negative results
            logger.warning(f"Template set not found in database: {set_name}")
            return None

    async def import_template(self, set_name: str, template_name: str, content: str) -> bool:
        """Import a template from disk to database.

        Handles template inheritance by checking for both master and custom versions:
        1. Get template set ID from set name
        2. Check if master template exists (sid=-2)
        3. Check if custom template exists (sid=set_sid)
        4. If custom exists → UPDATE, else → INSERT

        Args:
            set_name: Template set name (e.g., "Default")
            template_name: Template title (e.g., "index_boardstats")
            content: Template HTML content

        Returns:
            True if import succeeded, False otherwise

        Raises:
            ValueError: If template set not found or content is empty
        """
        # Defense-in-depth: validate content even if watcher already checked
        if not content or len(content.strip()) == 0:
            raise ValueError(f"Cannot import empty template: {template_name}")

        # Step 1: Get template set ID (with caching)
        sid = self._get_template_set_id(set_name)
        if sid is None:
            raise ValueError(f"Template set not found: {set_name}")

        # Step 2: Check if master template exists (sid=-2)
        master = self.db.get_template(template_name, sid=-2)

        # Step 3: Check if custom template exists (sid=set_sid)
        custom = self.db.get_template(template_name, sid=sid)

        # Step 4: UPDATE existing custom or INSERT new custom
        if custom:
            # Custom template exists → UPDATE
            return self.db.update_template(custom['tid'], content)
        else:
            # Custom template doesn't exist → INSERT
            # Use version from master if it exists, otherwise default to "1800"
            version = master['version'] if master else "1800"
            tid = self.db.create_template(template_name, content, sid=sid, version=version)
            return tid > 0
