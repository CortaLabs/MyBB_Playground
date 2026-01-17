"""MySQL database connection for MyBB."""

from contextlib import contextmanager
from typing import Any, Generator
import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor

from ..config import DatabaseConfig


class MyBBDatabase:
    """Database wrapper for MyBB operations."""

    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._connection: MySQLConnection | None = None

    @property
    def prefix(self) -> str:
        return self.config.prefix

    def connect(self) -> MySQLConnection:
        """Establish database connection."""
        if self._connection is None or not self._connection.is_connected():
            self._connection = mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                charset='utf8mb4',
                collation='utf8mb4_unicode_ci',
            )
        return self._connection

    def close(self):
        """Close database connection."""
        if self._connection and self._connection.is_connected():
            self._connection.close()
            self._connection = None

    @contextmanager
    def cursor(self, dictionary: bool = True) -> Generator[MySQLCursor, None, None]:
        """Get a database cursor."""
        conn = self.connect()
        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def table(self, name: str) -> str:
        """Get prefixed table name."""
        return f"{self.prefix}{name}"

    # ==================== Template Operations ====================

    def list_template_sets(self) -> list[dict[str, Any]]:
        """List all template sets."""
        with self.cursor() as cur:
            cur.execute(f"SELECT sid, title FROM {self.table('templatesets')} ORDER BY sid")
            return cur.fetchall()

    def get_template_set_by_name(self, name: str) -> dict[str, Any] | None:
        """Get template set by name.

        Args:
            name: Template set name (title)

        Returns:
            Dictionary with sid and title, or None if not found
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT sid, title FROM {self.table('templatesets')} WHERE title = %s",
                (name,)
            )
            return cur.fetchone()

    def list_template_groups(self) -> list[dict[str, Any]]:
        """List all template groups.

        Returns:
            List of dictionaries with gid, prefix, title
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT gid, prefix, title FROM {self.table('templategroups')} ORDER BY title"
            )
            return cur.fetchall()

    def list_templates(self, sid: int | None = None, search: str | None = None) -> list[dict[str, Any]]:
        """List templates, optionally filtered by set ID or search term."""
        query = f"SELECT tid, title, sid, version, status FROM {self.table('templates')}"
        params = []
        conditions = []

        if sid is not None:
            conditions.append("sid = %s")
            params.append(sid)

        if search:
            conditions.append("title LIKE %s")
            params.append(f"%{search}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY title LIMIT 500"

        with self.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def get_template(self, title: str, sid: int = -1) -> dict[str, Any] | None:
        """Get a specific template by title and set ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT tid, title, template, sid, version, status, dateline "
                f"FROM {self.table('templates')} WHERE title = %s AND sid = %s",
                (title, sid)
            )
            return cur.fetchone()

    def get_template_by_tid(self, tid: int) -> dict[str, Any] | None:
        """Get a specific template by ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT tid, title, template, sid, version, status, dateline "
                f"FROM {self.table('templates')} WHERE tid = %s",
                (tid,)
            )
            return cur.fetchone()

    def update_template(self, tid: int, template: str) -> bool:
        """Update a template's content."""
        import time
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('templates')} SET template = %s, dateline = %s WHERE tid = %s",
                (template, int(time.time()), tid)
            )
            return cur.rowcount > 0

    def create_template(self, title: str, template: str, sid: int = -1, version: str = "1800") -> int:
        """Create a new template."""
        import time
        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table('templates')} (title, template, sid, version, status, dateline) "
                f"VALUES (%s, %s, %s, %s, '', %s)",
                (title, template, sid, version, int(time.time()))
            )
            return cur.lastrowid

    # ==================== Theme Operations ====================

    def list_themes(self) -> list[dict[str, Any]]:
        """List all themes."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT tid, name, pid, def, properties FROM {self.table('themes')} ORDER BY name"
            )
            return cur.fetchall()

    def get_theme(self, tid: int) -> dict[str, Any] | None:
        """Get theme by ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT tid, name, pid, def, properties, stylesheets "
                f"FROM {self.table('themes')} WHERE tid = %s",
                (tid,)
            )
            return cur.fetchone()

    def get_theme_by_name(self, name: str) -> dict[str, Any] | None:
        """Get theme by name.

        Args:
            name: Theme name

        Returns:
            Dictionary with theme data, or None if not found
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT tid, name, pid, def, properties, stylesheets "
                f"FROM {self.table('themes')} WHERE name = %s",
                (name,)
            )
            return cur.fetchone()

    def list_stylesheets(self, tid: int | None = None) -> list[dict[str, Any]]:
        """List stylesheets, optionally filtered by theme."""
        query = f"SELECT sid, name, tid, cachefile, lastmodified FROM {self.table('themestylesheets')}"
        params = []

        if tid is not None:
            query += " WHERE tid = %s"
            params.append(tid)

        query += " ORDER BY name"

        with self.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def get_stylesheet(self, sid: int) -> dict[str, Any] | None:
        """Get stylesheet by ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT sid, name, tid, attachedto, stylesheet, cachefile, lastmodified "
                f"FROM {self.table('themestylesheets')} WHERE sid = %s",
                (sid,)
            )
            return cur.fetchone()

    def get_stylesheet_by_name(self, tid: int, name: str) -> dict[str, Any] | None:
        """Get stylesheet by theme ID and name.

        Args:
            tid: Theme ID
            name: Stylesheet name

        Returns:
            Dictionary with stylesheet data, or None if not found
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT sid, name, tid, attachedto, stylesheet, cachefile, lastmodified "
                f"FROM {self.table('themestylesheets')} WHERE tid = %s AND name = %s",
                (tid, name)
            )
            return cur.fetchone()

    def update_stylesheet(self, sid: int, stylesheet: str) -> bool:
        """Update stylesheet content."""
        import time
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('themestylesheets')} SET stylesheet = %s, lastmodified = %s WHERE sid = %s",
                (stylesheet, int(time.time()), sid)
            )
            return cur.rowcount > 0

    def create_stylesheet(self, tid: int, name: str, stylesheet: str, attachedto: str = "") -> int:
        """Create a new stylesheet.

        Args:
            tid: Theme ID
            name: Stylesheet name
            stylesheet: Stylesheet CSS content
            attachedto: Pages/actions this stylesheet applies to (copy from parent for overrides)

        Returns:
            New stylesheet ID (sid)
        """
        import time
        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table('themestylesheets')} (tid, name, stylesheet, cachefile, lastmodified, attachedto) "
                f"VALUES (%s, %s, %s, %s, %s, %s)",
                (tid, name, stylesheet, name, int(time.time()), attachedto)
            )
            return cur.lastrowid

    def find_inherited_stylesheet(self, tid: int, name: str) -> dict[str, Any] | None:
        """Find a stylesheet by walking up the theme inheritance chain.

        Args:
            tid: Starting theme ID
            name: Stylesheet name to find

        Returns:
            Dictionary with stylesheet data from first parent that has it, or None
        """
        with self.cursor() as cur:
            current_tid = tid

            while current_tid:
                # Check if stylesheet exists in current theme
                cur.execute(
                    f"SELECT sid, name, tid, attachedto, stylesheet, cachefile, lastmodified "
                    f"FROM {self.table('themestylesheets')} WHERE tid = %s AND name = %s",
                    (current_tid, name)
                )
                result = cur.fetchone()
                if result:
                    return result

                # Get parent theme
                cur.execute(
                    f"SELECT pid FROM {self.table('themes')} WHERE tid = %s",
                    (current_tid,)
                )
                parent = cur.fetchone()
                current_tid = parent['pid'] if parent and parent['pid'] else None

            return None

    # ==================== Plugin Operations ====================

    def get_active_plugins(self) -> list[str]:
        """Get list of active plugins from cache."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT cache FROM {self.table('datacache')} WHERE title = 'plugins'"
            )
            row = cur.fetchone()
            if row and row['cache']:
                import json
                try:
                    # MyBB stores PHP serialized data, but we can try JSON first
                    data = json.loads(row['cache'])
                    return list(data.get('active', {}).values())
                except (json.JSONDecodeError, TypeError):
                    # PHP serialized format - would need phpserialize library
                    return []
            return []

    # ==================== Settings Operations ====================

    def list_setting_groups(self) -> list[dict[str, Any]]:
        """List all setting groups."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT gid, name, title, description, disporder, isdefault "
                f"FROM {self.table('settinggroups')} ORDER BY disporder"
            )
            return cur.fetchall()

    def list_settings(self, gid: int | None = None) -> list[dict[str, Any]]:
        """List settings, optionally filtered by group."""
        query = f"SELECT sid, name, title, description, optionscode, value, gid FROM {self.table('settings')}"
        params = []

        if gid is not None:
            query += " WHERE gid = %s"
            params.append(gid)

        query += " ORDER BY disporder"

        with self.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()
