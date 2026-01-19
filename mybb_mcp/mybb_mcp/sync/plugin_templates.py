"""Plugin template import for disk-sync.

Handles synchronization of plugin templates from workspace to database.
Plugin templates are stored in master templates (sid=-2) by default, or in specific
template sets (sid>=1) when theme-specific overrides are provided.
"""

import logging
import os
from typing import Any, Optional

from mybb_mcp.db.connection import MyBBDatabase

# Environment variable to disable template set caching for development
DISABLE_CACHE_ENV = "MYBB_SYNC_DISABLE_CACHE"

logger = logging.getLogger(__name__)


class PluginTemplateImporter:
    """Imports plugin templates from workspace disk files to database."""

    def __init__(self, db: MyBBDatabase):
        """Initialize plugin template importer.

        Args:
            db: MyBBDatabase instance for template operations
        """
        self.db = db
        # Cache for template set sid lookups (theme_name -> sid)
        self._template_set_cache: dict[str, Optional[int]] = {}
        # Check if caching is disabled via env var
        self._cache_disabled = os.environ.get(DISABLE_CACHE_ENV, "").lower() in ("1", "true", "yes")
        if self._cache_disabled:
            logger.info("Plugin template set caching DISABLED via MYBB_SYNC_DISABLE_CACHE")

    def clear_cache(self) -> None:
        """Clear the template set cache.

        Useful for development or when template sets are modified.
        """
        self._template_set_cache.clear()
        logger.debug("Plugin template set cache cleared")

    def _get_template_set_sid(self, theme_name: str) -> Optional[int]:
        """Get template set sid by theme name with caching.

        Args:
            theme_name: Template set name to lookup

        Returns:
            Template set sid if found, None otherwise
        """
        # Skip cache if disabled
        if self._cache_disabled:
            logger.debug(f"Template set cache DISABLED - querying database for: {theme_name}")
            template_set = self.db.get_template_set_by_name(theme_name)
            if template_set:
                return template_set['sid']
            logger.warning(f"Template set not found: '{theme_name}', falling back to sid=-2")
            return None

        # Check cache first
        if theme_name in self._template_set_cache:
            return self._template_set_cache[theme_name]

        # Query database for template set
        template_set = self.db.get_template_set_by_name(theme_name)
        if template_set:
            sid = template_set['sid']
            logger.debug(f"Template set lookup: '{theme_name}' -> sid={sid}")
            self._template_set_cache[theme_name] = sid
            return sid
        else:
            logger.warning(f"Template set not found: '{theme_name}', falling back to sid=-2")
            self._template_set_cache[theme_name] = None
            return None

    async def import_template(
        self,
        codename: str,
        template_name: str,
        content: str,
        theme_name: Optional[str] = None
    ) -> bool:
        """Import a plugin template from disk to database.

        Plugin templates can be stored in master templates (sid=-2) by default,
        or in specific template sets (sid>=1) when theme_name is provided.

        Workflow:
        1. If theme_name is None or empty → use sid=-2 (master templates)
        2. If theme_name is provided → lookup template set sid by name
        3. If template set not found → fall back to sid=-2 with warning
        4. Template name is prefixed: {codename}_{template_name}
        5. Check if template exists by full name at the target sid
        6. If exists → UPDATE, else → INSERT

        Args:
            codename: Plugin codename (e.g., "cortex")
            template_name: Template name without codename prefix (e.g., "header")
            content: Template HTML content
            theme_name: Optional template set name for theme-specific templates

        Returns:
            True if import succeeded, False otherwise

        Raises:
            ValueError: If content is empty

        Examples:
            >>> importer = PluginTemplateImporter(db)
            >>> # Default template (master)
            >>> await importer.import_template("cortex", "header", "<div>...</div>")
            True
            >>> # Theme-specific template
            >>> await importer.import_template("cortex", "header", "<div>custom</div>", "Default Templates")
            True
        """
        # Defense-in-depth: validate content even if watcher already checked
        if not content or len(content.strip()) == 0:
            raise ValueError(f"Cannot import empty template: {codename}_{template_name}")

        # Build full template name with codename prefix
        full_template_name = f"{codename}_{template_name}"

        # Determine target sid based on theme_name
        if theme_name and len(theme_name.strip()) > 0:
            # Theme-specific template - lookup template set sid
            target_sid = self._get_template_set_sid(theme_name)
            if target_sid is None:
                # Template set not found, fall back to master templates
                logger.warning(f"Template set '{theme_name}' not found, using sid=-2 for {full_template_name}")
                target_sid = -2
        else:
            # Default to master templates
            target_sid = -2

        # Check if plugin template exists at target sid
        existing = self.db.get_template(full_template_name, sid=target_sid)

        if existing:
            # Plugin template exists → UPDATE
            logger.info(f"Updating plugin template: {full_template_name} (sid={target_sid})")
            success = self.db.update_template(existing['tid'], content)
            if success:
                logger.info(f"Successfully updated plugin template: {full_template_name}")
            else:
                logger.error(f"Failed to update plugin template: {full_template_name}")
            return success
        else:
            # Plugin template doesn't exist → INSERT
            logger.info(f"Creating new plugin template: {full_template_name} (sid={target_sid})")
            tid = self.db.create_template(
                title=full_template_name,
                template=content,
                sid=target_sid,
                version="1800"  # Default MyBB version
            )
            if tid > 0:
                logger.info(f"Successfully created plugin template: {full_template_name} (tid={tid}, sid={target_sid})")
                return True
            else:
                logger.error(f"Failed to create plugin template: {full_template_name}")
                return False
