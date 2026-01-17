"""Template group management for disk-sync.

Determines which group/folder a template belongs to using multi-strategy matching:
1. Global templates (sid=-2 with global_ prefix)
2. Hardcoded pattern matching
3. Database templategroups prefix lookup
4. Fallback to capitalized prefix
"""

from typing import Any

from mybb_mcp.db.connection import MyBBDatabase


class TemplateGroupManager:
    """Manages template group categorization for organizing templates into folders."""

    # Hardcoded patterns for common template prefixes
    HARDCODED_PATTERNS = {
        'global_': 'Global Templates',
        'header_': 'Header Templates',
        'footer_': 'Footer Templates',
        'usercp_': 'User CP Templates',
        'modcp_': 'Moderator CP Templates',
        'admin_': 'Admin Templates',
        'forum_': 'Forum Templates',
        'member_': 'Member Templates',
        'post_': 'Posting Templates',
        'poll_': 'Poll Templates',
        'pm_': 'Private Message Templates',
        'showthread_': 'Show Thread Templates',
        'search_': 'Search Templates',
        'calendar_': 'Calendar Templates',
        'announcement_': 'Announcement Templates',
        'private_': 'Private Message Templates',
    }

    def __init__(self, db: MyBBDatabase):
        """Initialize group manager.

        Args:
            db: MyBBDatabase instance for querying templategroups table
        """
        self.db = db
        self._db_groups: dict[str, str] = {}  # prefix -> title mapping
        self._loaded = False

    def _load_groups(self) -> None:
        """Load template groups from database (lazy loading)."""
        if self._loaded:
            return

        groups = self.db.list_template_groups()
        for group in groups:
            prefix = group.get('prefix', '')
            title = group.get('title', '')
            if prefix and title:
                self._db_groups[prefix] = title

        self._loaded = True

    def get_group_name(self, template_title: str, sid: int = 0) -> str:
        """Determine group name for a template using multi-strategy matching.

        Matching strategies (in priority order):
        1. Global templates: sid=-2 and title starts with 'global_' -> "Global Templates"
        2. Hardcoded pattern matching against HARDCODED_PATTERNS
        3. Database templategroups prefix lookup
        4. Fallback: capitalize prefix + " Templates"

        Args:
            template_title: Template title (e.g., "header_welcome", "footer_links")
            sid: Template set ID (-2 for master templates)

        Returns:
            Group name for organizing into folders (e.g., "Header Templates")
        """
        # Strategy 1: Global templates
        if sid == -2 and template_title.startswith('global_'):
            return 'Global Templates'

        # Extract prefix (everything before first underscore)
        if '_' not in template_title:
            # No prefix - use full name capitalized
            return f"{template_title.capitalize()} Templates"

        prefix = template_title.split('_')[0] + '_'

        # Strategy 2: Hardcoded patterns
        if prefix in self.HARDCODED_PATTERNS:
            return self.HARDCODED_PATTERNS[prefix]

        # Strategy 3: Database lookup
        self._load_groups()
        if prefix in self._db_groups:
            return self._db_groups[prefix]

        # Strategy 4: Fallback - capitalize prefix
        prefix_name = prefix.rstrip('_').replace('_', ' ').title()
        return f"{prefix_name} Templates"
