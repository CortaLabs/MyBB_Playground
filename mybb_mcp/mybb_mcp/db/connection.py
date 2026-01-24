"""MySQL database connection for MyBB."""

from contextlib import contextmanager
from typing import Any, Generator
import time
import logging
import threading
import mysql.connector
from mysql.connector import MySQLConnection
from mysql.connector.cursor import MySQLCursor
from mysql.connector.pooling import MySQLConnectionPool, PoolError
from mysql.connector import Error as MySQLError

from ..config import DatabaseConfig

logger = logging.getLogger(__name__)

# Pool acquisition timeout in seconds
POOL_ACQUIRE_TIMEOUT = 10

# Global connection tracking for debugging leaks
_active_connections: dict[int, dict] = {}
_connection_lock = threading.Lock()


def _track_connection_acquired(conn_id: int, caller: str):
    """Track when a connection is acquired."""
    with _connection_lock:
        _active_connections[conn_id] = {
            "acquired_at": time.time(),
            "caller": caller,
            "thread": threading.current_thread().name
        }
        if len(_active_connections) > 3:  # Warn if holding many connections
            logger.warning(f"High connection count: {len(_active_connections)} active. "
                          f"Callers: {[v['caller'] for v in _active_connections.values()]}")


def _track_connection_released(conn_id: int):
    """Track when a connection is released."""
    with _connection_lock:
        if conn_id in _active_connections:
            held_time = time.time() - _active_connections[conn_id]["acquired_at"]
            if held_time > 5:  # Warn if held for more than 5 seconds
                logger.warning(f"Connection {conn_id} held for {held_time:.1f}s by "
                              f"{_active_connections[conn_id]['caller']}")
            del _active_connections[conn_id]


class MyBBDatabase:
    """Database wrapper for MyBB operations with connection pooling."""

    def __init__(self, config: DatabaseConfig, pool_size: int | None = None, pool_name: str | None = None):
        """Initialize database with connection pooling.

        Args:
            config: Database configuration
            pool_size: Maximum number of connections in the pool (default: uses config.pool_size)
            pool_name: Name for the connection pool (default: uses config.pool_name)
        """
        self.config = config
        self._connection: MySQLConnection | None = None
        self._pool: MySQLConnectionPool | None = None

        # Use explicit parameters or fall back to config values
        self._pool_size = pool_size if pool_size is not None else config.pool_size
        self._pool_name = pool_name if pool_name is not None else config.pool_name
        self._use_pooling = self._pool_size > 1

        # Retry configuration
        self._max_retries = 3
        self._base_retry_delay = 0.5  # seconds
        self._max_retry_delay = 5.0  # seconds

    @property
    def prefix(self) -> str:
        return self.config.prefix

    def _get_connection_config(self) -> dict[str, Any]:
        """Get connection configuration dictionary."""
        return {
            'host': self.config.host,
            'port': self.config.port,
            'database': self.config.database,
            'user': self.config.user,
            'password': self.config.password,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci',
            'autocommit': False,
            'pool_reset_session': True,
        }

    def _init_pool(self) -> MySQLConnectionPool:
        """Initialize connection pool if not already initialized."""
        if self._pool is None:
            try:
                config = self._get_connection_config()
                self._pool = MySQLConnectionPool(
                    pool_name=self._pool_name,
                    pool_size=self._pool_size,
                    **config
                )
                logger.info(f"Connection pool initialized: {self._pool_name} (size={self._pool_size})")
            except MySQLError as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                raise
        return self._pool

    def _get_connection_with_timeout(self, pool: MySQLConnectionPool, timeout: float) -> MySQLConnection:
        """Get connection from pool with timeout to prevent indefinite blocking.

        NOTE: Timeout is enforced by the pool itself via connection_timeout parameter
        set during pool initialization. We don't use ThreadPoolExecutor here to avoid
        nested thread pool deadlocks when this is called from asyncio.to_thread().

        Args:
            pool: The connection pool
            timeout: Maximum seconds to wait (informational only - pool handles timeout)

        Returns:
            MySQL connection from pool

        Raises:
            MySQLError: If timeout expires or pool error occurs
        """
        try:
            # Direct call - no ThreadPoolExecutor wrapper to avoid nested thread pool deadlock
            # The pool's connection_timeout parameter (set in __init__) handles timeouts
            conn = pool.get_connection()
            return conn
        except PoolError as e:
            # Pool exhaustion or timeout
            logger.error(f"Pool error getting connection: {e}")
            raise MySQLError(f"Connection pool error: {e}. "
                           f"Consider increasing MYBB_DB_POOL_SIZE (current: {self._pool_size})")

    def _connect_with_retry(self) -> MySQLConnection:
        """Establish database connection with retry logic and exponential backoff."""
        last_error = None

        for attempt in range(self._max_retries):
            try:
                if self._use_pooling:
                    pool = self._init_pool()
                    conn = self._get_connection_with_timeout(pool, POOL_ACQUIRE_TIMEOUT)
                    logger.debug(f"Got connection from pool (attempt {attempt + 1})")
                else:
                    config = self._get_connection_config()
                    conn = mysql.connector.connect(**config)
                    logger.debug(f"Created direct connection (attempt {attempt + 1})")

                # Verify connection is healthy
                if conn.is_connected():
                    return conn
                else:
                    raise MySQLError("Connection established but not healthy")

            except MySQLError as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    # Exponential backoff: 0.5s, 1s, 2s (capped at max_retry_delay)
                    delay = min(self._base_retry_delay * (2 ** attempt), self._max_retry_delay)
                    logger.warning(
                        f"Database connection attempt {attempt + 1}/{self._max_retries} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"All {self._max_retries} connection attempts failed: {e}")

        # All retries exhausted
        raise MySQLError(f"Failed to connect after {self._max_retries} attempts: {last_error}")

    def connect(self) -> MySQLConnection:
        """Establish database connection with pooling and retry logic.

        Returns:
            Active MySQL connection

        Raises:
            MySQLError: If connection fails after all retry attempts
        """
        # For pooled connections, always get a fresh connection from pool
        if self._use_pooling:
            return self._connect_with_retry()

        # For non-pooled connections, maintain single persistent connection
        if self._connection is None or not self._is_connection_healthy(self._connection):
            self._connection = self._connect_with_retry()

        return self._connection

    def _is_connection_healthy(self, conn: MySQLConnection | None) -> bool:
        """Check if connection is healthy and usable.

        Args:
            conn: Connection to check

        Returns:
            True if connection is healthy, False otherwise
        """
        if conn is None:
            return False

        try:
            # Check basic connectivity
            if not conn.is_connected():
                return False

            # Perform a simple ping to verify connection is responsive
            conn.ping(reconnect=False, attempts=1, delay=0)
            return True

        except MySQLError:
            return False

    def close(self):
        """Close database connection or return to pool."""
        if self._use_pooling:
            # Pool connections are automatically returned when closed
            # No need to track individual connections
            logger.debug("Pooled connection will be returned automatically")
        else:
            # Close single persistent connection
            if self._connection and self._connection.is_connected():
                try:
                    self._connection.close()
                    logger.debug("Direct connection closed")
                except MySQLError as e:
                    logger.warning(f"Error closing connection: {e}")
                finally:
                    self._connection = None

    @contextmanager
    def cursor(self, dictionary: bool = True) -> Generator[MySQLCursor, None, None]:
        """Get a database cursor with automatic connection management.

        For pooled connections, acquires a connection from the pool and returns it
        after use. For non-pooled connections, uses the persistent connection.

        Args:
            dictionary: If True, return rows as dictionaries (default: True)

        Yields:
            MySQLCursor: Database cursor for executing queries
        """
        import traceback
        caller = ''.join(traceback.format_stack()[-4:-2])  # Get caller info

        conn = self.connect()
        conn_id = id(conn)

        if self._use_pooling:
            _track_connection_acquired(conn_id, caller[:200])  # Truncate long traces

        cursor = conn.cursor(dictionary=dictionary)
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            # Return pooled connections to the pool
            if self._use_pooling:
                _track_connection_released(conn_id)
                try:
                    conn.close()
                except MySQLError as e:
                    logger.warning(f"Error returning connection to pool: {e}")

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

    def find_templates_for_replace(self, title: str, template_sets: list[int] = None) -> list[dict[str, Any]]:
        """Find all templates matching title across specified template sets for find/replace operations.

        Args:
            title: Template title to match
            template_sets: List of sid values to search, or empty/None for all sets

        Returns:
            List of template dicts with tid, title, template, sid, version
        """
        query = f"SELECT tid, title, template, sid, version FROM {self.table('templates')} WHERE title = %s"
        params = [title]

        if template_sets:
            # Search only in specified sets
            placeholders = ','.join(['%s'] * len(template_sets))
            query += f" AND sid IN ({placeholders})"
            params.extend(template_sets)

        query += " ORDER BY sid"

        with self.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def find_outdated_templates(self, sid: int) -> list[dict[str, Any]]:
        """Find custom templates in a set that are outdated compared to master.

        A template is outdated if:
        - It exists in the custom set (sid)
        - A master template exists with the same title (sid=-2)
        - The custom version number < master version number

        Args:
            sid: Template set ID to check (must be > 0)

        Returns:
            List of dicts with title, tid, custom_version, master_version
        """
        query = f"""
            SELECT
                c.tid,
                c.title,
                c.version as custom_version,
                m.version as master_version
            FROM {self.table('templates')} c
            INNER JOIN {self.table('templates')} m
                ON c.title = m.title AND m.sid = -2
            WHERE c.sid = %s
                AND CAST(c.version AS UNSIGNED) < CAST(m.version AS UNSIGNED)
            ORDER BY c.title
        """

        with self.cursor() as cur:
            cur.execute(query, (sid,))
            return cur.fetchall()

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

    # ==================== Forum Operations ====================

    def list_forums(self) -> list[dict[str, Any]]:
        """List all forums with hierarchy."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT fid, name, description, type, pid, parentlist, disporder, active, threads, posts "
                f"FROM {self.table('forums')} ORDER BY disporder"
            )
            return cur.fetchall()

    def get_forum(self, fid: int) -> dict[str, Any] | None:
        """Get forum by ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT fid, name, description, type, pid, parentlist, disporder, active, open, "
                f"threads, posts, lastpost, lastposter, lastposteruid, unapprovedthreads, unapprovedposts "
                f"FROM {self.table('forums')} WHERE fid = %s",
                (fid,)
            )
            return cur.fetchone()

    def create_forum(self, name: str, description: str = "", forum_type: str = "f",
                     pid: int = 0, parentlist: str = "", disporder: int = 1) -> int:
        """Create a new forum or category.

        Args:
            name: Forum name
            description: Forum description
            forum_type: 'f' for forum, 'c' for category
            pid: Parent forum ID
            parentlist: Comma-separated ancestor path
            disporder: Display order

        Returns:
            New forum ID (fid)
        """
        if not parentlist:
            parentlist = str(pid) if pid else "0"

        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table('forums')} "
                f"(name, description, type, pid, parentlist, disporder, active, open, rules) "
                f"VALUES (%s, %s, %s, %s, %s, %s, 1, 1, %s)",
                (name, description, forum_type, pid, parentlist, disporder, "")
            )
            return cur.lastrowid

    def update_forum(self, fid: int, **kwargs) -> bool:
        """Update forum properties.

        Args:
            fid: Forum ID
            **kwargs: Properties to update (name, description, type, pid, parentlist, disporder, active, open)

        Returns:
            True if updated, False otherwise
        """
        allowed_fields = {'name', 'description', 'type', 'pid', 'parentlist', 'disporder', 'active', 'open'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [fid]

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('forums')} SET {set_clause} WHERE fid = %s",
                values
            )
            return cur.rowcount > 0

    def delete_forum(self, fid: int) -> bool:
        """Delete a forum.

        Note: This does NOT handle cascading deletes of threads/posts.
        Caller should handle content migration or deletion first.

        Args:
            fid: Forum ID

        Returns:
            True if deleted, False otherwise
        """
        with self.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table('forums')} WHERE fid = %s", (fid,))
            return cur.rowcount > 0

    def update_forum_counters(self, fid: int, threads_delta: int = 0, posts_delta: int = 0):
        """Update forum thread and post counters.

        Args:
            fid: Forum ID
            threads_delta: Amount to increment/decrement threads counter
            posts_delta: Amount to increment/decrement posts counter
        """
        if threads_delta == 0 and posts_delta == 0:
            return

        with self.cursor() as cur:
            updates = []
            if threads_delta != 0:
                updates.append(f"threads = threads + {int(threads_delta)}")
            if posts_delta != 0:
                updates.append(f"posts = posts + {int(posts_delta)}")

            cur.execute(
                f"UPDATE {self.table('forums')} SET {', '.join(updates)} WHERE fid = %s",
                (fid,)
            )

    # ==================== Thread Operations ====================

    def list_threads(self, fid: int | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List threads, optionally filtered by forum with pagination.

        Args:
            fid: Forum ID to filter by (None for all threads)
            limit: Maximum threads to return
            offset: Number of threads to skip

        Returns:
            List of thread dictionaries
        """
        query = (f"SELECT tid, fid, subject, prefix, uid, username, dateline, firstpost, "
                f"lastpost, lastposter, replies, views, closed, sticky, visible "
                f"FROM {self.table('threads')}")
        params = []

        if fid is not None:
            query += " WHERE fid = %s"
            params.append(fid)

        query += " ORDER BY lastpost DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def get_thread(self, tid: int) -> dict[str, Any] | None:
        """Get thread by ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT tid, fid, subject, prefix, icon, poll, uid, username, dateline, "
                f"firstpost, lastpost, lastposter, lastposteruid, views, replies, closed, "
                f"sticky, visible, unapprovedposts, deletedposts, attachmentcount "
                f"FROM {self.table('threads')} WHERE tid = %s",
                (tid,)
            )
            return cur.fetchone()

    def create_thread(self, fid: int, subject: str, uid: int, username: str,
                      firstpost_pid: int, message: str, prefix: int = 0) -> int:
        """Create a new thread.

        Note: This creates ONLY the thread record. The first post must be created separately
        and its pid passed as firstpost_pid. Use create_thread_with_post for atomic creation.

        Args:
            fid: Forum ID
            subject: Thread subject
            uid: Author user ID
            username: Author username
            firstpost_pid: First post ID
            message: Post message (for lastpost update)
            prefix: Thread prefix ID

        Returns:
            New thread ID (tid)
        """
        import time
        dateline = int(time.time())

        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table('threads')} "
                f"(fid, subject, prefix, uid, username, dateline, firstpost, lastpost, lastposter, lastposteruid, replies, visible, notes) "
                f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, 1, '')",
                (fid, subject, prefix, uid, username, dateline, firstpost_pid, dateline, username, uid)
            )
            return cur.lastrowid

    def update_thread(self, tid: int, **kwargs) -> bool:
        """Update thread properties.

        Args:
            tid: Thread ID
            **kwargs: Properties to update (subject, prefix, closed, sticky, visible, etc.)

        Returns:
            True if updated, False otherwise
        """
        allowed_fields = {'subject', 'prefix', 'fid', 'closed', 'sticky', 'visible'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [tid]

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET {set_clause} WHERE tid = %s",
                values
            )
            return cur.rowcount > 0

    def delete_thread(self, tid: int, soft: bool = True) -> bool:
        """Delete a thread (soft delete by default).

        Args:
            tid: Thread ID
            soft: If True, set visible=-1. If False, actually delete.

        Returns:
            True if deleted, False otherwise
        """
        import time
        with self.cursor() as cur:
            if soft:
                cur.execute(
                    f"UPDATE {self.table('threads')} SET visible = -1, deletetime = %s WHERE tid = %s",
                    (int(time.time()), tid)
                )
            else:
                cur.execute(f"DELETE FROM {self.table('threads')} WHERE tid = %s", (tid,))
            return cur.rowcount > 0

    def move_thread(self, tid: int, new_fid: int) -> bool:
        """Move thread to a different forum.

        Note: Caller must update forum counters for both old and new forums.

        Args:
            tid: Thread ID
            new_fid: New forum ID

        Returns:
            True if moved, False otherwise
        """
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET fid = %s WHERE tid = %s",
                (new_fid, tid)
            )
            return cur.rowcount > 0

    def update_thread_counters(self, tid: int, replies_delta: int = 0):
        """Update thread reply counter.

        Args:
            tid: Thread ID
            replies_delta: Amount to increment/decrement replies counter
        """
        if replies_delta == 0:
            return

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET replies = replies + %s WHERE tid = %s",
                (replies_delta, tid)
            )

    def update_thread_lastpost(self, tid: int, lastpost: int, lastposter: str, lastposteruid: int):
        """Update thread's lastpost metadata.

        Args:
            tid: Thread ID
            lastpost: Last post timestamp
            lastposter: Last poster username
            lastposteruid: Last poster user ID
        """
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET lastpost = %s, lastposter = %s, lastposteruid = %s "
                f"WHERE tid = %s",
                (lastpost, lastposter, lastposteruid, tid)
            )

    # ==================== Post Operations ====================

    def list_posts(self, tid: int | None = None, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        """List posts, optionally filtered by thread with pagination.

        Args:
            tid: Thread ID to filter by (None for all posts)
            limit: Maximum posts to return
            offset: Number of posts to skip

        Returns:
            List of post dictionaries
        """
        query = (f"SELECT pid, tid, fid, subject, uid, username, dateline, message, "
                f"visible, edituid, edittime FROM {self.table('posts')}")
        params = []

        if tid is not None:
            query += " WHERE tid = %s"
            params.append(tid)

        query += " ORDER BY dateline ASC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()

    def get_post(self, pid: int) -> dict[str, Any] | None:
        """Get post by ID."""
        with self.cursor() as cur:
            cur.execute(
                f"SELECT pid, tid, replyto, fid, subject, icon, uid, username, dateline, "
                f"message, ipaddress, includesig, smilieoff, edituid, edittime, editreason, visible "
                f"FROM {self.table('posts')} WHERE pid = %s",
                (pid,)
            )
            return cur.fetchone()

    def create_post(self, tid: int, fid: int, subject: str, message: str,
                    uid: int, username: str, ipaddress: str = "", replyto: int = 0) -> int:
        """Create a new post in a thread.

        Note: This does NOT update thread/forum counters. Caller must handle that.

        Args:
            tid: Thread ID
            fid: Forum ID
            subject: Post subject
            message: Post content (BBCode)
            uid: Author user ID
            username: Author username
            ipaddress: Author IP address (optional, privacy concern)
            replyto: Parent post ID for threading

        Returns:
            New post ID (pid)
        """
        import time
        dateline = int(time.time())

        with self.cursor() as cur:
            cur.execute(
                f"INSERT INTO {self.table('posts')} "
                f"(tid, replyto, fid, subject, uid, username, dateline, message, ipaddress, visible) "
                f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)",
                (tid, replyto, fid, subject, uid, username, dateline, message, ipaddress)
            )
            return cur.lastrowid

    def update_post(self, pid: int, message: str = None, subject: str = None,
                    edituid: int = None, editreason: str = "") -> bool:
        """Edit a post.

        Args:
            pid: Post ID
            message: New message content (None to keep existing)
            subject: New subject (None to keep existing)
            edituid: Editor user ID
            editreason: Edit reason text

        Returns:
            True if updated, False otherwise
        """
        import time
        updates = {}

        if message is not None:
            updates['message'] = message
        if subject is not None:
            updates['subject'] = subject
        if edituid is not None:
            updates['edituid'] = edituid
            updates['edittime'] = int(time.time())
            updates['editreason'] = editreason

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [pid]

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('posts')} SET {set_clause} WHERE pid = %s",
                values
            )
            return cur.rowcount > 0

    def delete_post(self, pid: int, soft: bool = True) -> bool:
        """Delete a post (soft delete by default).

        Note: This does NOT update thread/forum counters. Caller must handle that.

        Args:
            pid: Post ID
            soft: If True, set visible=-1. If False, actually delete.

        Returns:
            True if deleted, False otherwise
        """
        with self.cursor() as cur:
            if soft:
                cur.execute(
                    f"UPDATE {self.table('posts')} SET visible = -1 WHERE pid = %s",
                    (pid,)
                )
            else:
                cur.execute(f"DELETE FROM {self.table('posts')} WHERE pid = %s", (pid,))
            return cur.rowcount > 0

    def update_post_field(self, pid: int, field: str, value: Any) -> bool:
        """Update a single field of a post with whitelisted fields.

        Args:
            pid: Post ID
            field: Field name to update (must be in whitelist)
            value: New value for the field

        Returns:
            True if updated, False otherwise

        Raises:
            ValueError: If field is not in whitelist
        """
        allowed_fields = {'tid', 'fid', 'visible', 'message', 'subject'}

        if field not in allowed_fields:
            raise ValueError(
                f"Field '{field}' not allowed. Allowed fields: {', '.join(sorted(allowed_fields))}"
            )

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('posts')} SET {field} = %s WHERE pid = %s",
                (value, pid)
            )
            return cur.rowcount > 0

    def update_posts_by_thread(self, tid: int, **fields) -> int:
        """Update multiple posts in a thread with whitelisted fields.

        Args:
            tid: Thread ID
            **fields: Fields to update (must be in whitelist)

        Returns:
            Number of posts updated (rowcount)

        Raises:
            ValueError: If any field is not in whitelist
        """
        allowed_fields = {'fid', 'visible'}

        # Validate all fields
        invalid_fields = set(fields.keys()) - allowed_fields
        if invalid_fields:
            raise ValueError(
                f"Fields not allowed: {', '.join(sorted(invalid_fields))}. "
                f"Allowed fields: {', '.join(sorted(allowed_fields))}"
            )

        if not fields:
            return 0

        # Build SET clause dynamically
        set_clause = ", ".join([f"{k} = %s" for k in fields.keys()])
        values = list(fields.values()) + [tid]

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('posts')} SET {set_clause} WHERE tid = %s",
                values
            )
            return cur.rowcount

    # ==================== Search Operations ====================

    def search_posts(
        self,
        query: str,
        forums: list[int] | None = None,
        author: str | None = None,
        date_from: int | None = None,
        date_to: int | None = None,
        limit: int = 25,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Search post content with optional filters.

        Args:
            query: Search term to find in post message
            forums: Optional list of forum IDs to search within
            author: Optional username to filter by
            date_from: Optional start timestamp
            date_to: Optional end timestamp
            limit: Maximum results (default 25, max 100)
            offset: Pagination offset

        Returns:
            List of posts with thread info (no sensitive data)
        """
        # Sanitize limit
        limit = min(max(1, limit), 100)

        # Build query - exclude sensitive ipaddress field
        sql = f"""
            SELECT
                p.pid, p.tid, p.fid, p.subject, p.uid, p.username,
                p.dateline, p.message, p.visible, p.edittime, p.editreason,
                t.subject as thread_subject, t.fid as thread_fid
            FROM {self.table('posts')} p
            LEFT JOIN {self.table('threads')} t ON p.tid = t.tid
            WHERE p.visible = 1
        """
        params = []

        # Add search condition - use LIKE with wildcards
        # Escape special characters for LIKE
        escaped_query = query.replace('%', '\\%').replace('_', '\\_')
        sql += " AND p.message LIKE %s"
        params.append(f"%{escaped_query}%")

        # Add optional filters
        if forums:
            placeholders = ','.join(['%s'] * len(forums))
            sql += f" AND p.fid IN ({placeholders})"
            params.extend(forums)

        if author:
            sql += " AND p.username = %s"
            params.append(author)

        if date_from:
            sql += " AND p.dateline >= %s"
            params.append(date_from)

        if date_to:
            sql += " AND p.dateline <= %s"
            params.append(date_to)

        sql += " ORDER BY p.dateline DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def search_threads(
        self,
        query: str,
        forums: list[int] | None = None,
        author: str | None = None,
        prefix: int | None = None,
        limit: int = 25,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Search thread subjects with optional filters.

        Args:
            query: Search term to find in thread subject
            forums: Optional list of forum IDs to search within
            author: Optional username to filter by
            prefix: Optional thread prefix ID
            limit: Maximum results (default 25, max 100)
            offset: Pagination offset

        Returns:
            List of matching threads
        """
        # Sanitize limit
        limit = min(max(1, limit), 100)

        sql = f"""
            SELECT
                tid, fid, subject, prefix, uid, username, dateline,
                lastpost, lastposter, views, replies, closed, sticky, visible
            FROM {self.table('threads')}
            WHERE visible = 1
        """
        params = []

        # Add search condition
        escaped_query = query.replace('%', '\\%').replace('_', '\\_')
        sql += " AND subject LIKE %s"
        params.append(f"%{escaped_query}%")

        # Add optional filters
        if forums:
            placeholders = ','.join(['%s'] * len(forums))
            sql += f" AND fid IN ({placeholders})"
            params.extend(forums)

        if author:
            sql += " AND username = %s"
            params.append(author)

        if prefix is not None:
            sql += " AND prefix = %s"
            params.append(prefix)

        sql += " ORDER BY lastpost DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def search_users(
        self,
        query: str,
        field: str = "username",
        limit: int = 25,
        offset: int = 0
    ) -> list[dict[str, Any]]:
        """Search users by username or email.

        Args:
            query: Search term
            field: Field to search ("username" or "email")
            limit: Maximum results (default 25, max 100)
            offset: Pagination offset

        Returns:
            List of matching users (no password/salt/loginkey)
        """
        # Sanitize limit
        limit = min(max(1, limit), 100)

        # Validate field
        if field not in ["username", "email"]:
            raise ValueError("field must be 'username' or 'email'")

        # Select only safe columns - exclude password, salt, loginkey
        sql = f"""
            SELECT
                uid, username, usergroup, displaygroup, postnum, threadnum,
                avatar, usertitle, regdate, lastactive, lastvisit
            FROM {self.table('users')}
            WHERE {field} LIKE %s
        """

        escaped_query = query.replace('%', '\\%').replace('_', '\\_')
        params = [f"%{escaped_query}%"]

        sql += " ORDER BY username LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        with self.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def search_advanced(
        self,
        query: str,
        content_type: str = "both",
        forums: list[int] | None = None,
        date_from: int | None = None,
        date_to: int | None = None,
        sort_by: str = "date",
        limit: int = 25,
        offset: int = 0
    ) -> dict[str, Any]:
        """Combined search with multiple filters.

        Args:
            query: Search term
            content_type: "posts", "threads", or "both"
            forums: Optional list of forum IDs
            date_from: Optional start timestamp
            date_to: Optional end timestamp
            sort_by: Sort order ("date" or "relevance")
            limit: Maximum results per type (default 25, max 100)
            offset: Pagination offset

        Returns:
            Dict with posts and/or threads results
        """
        results = {}

        if content_type in ["posts", "both"]:
            results["posts"] = self.search_posts(
                query=query,
                forums=forums,
                date_from=date_from,
                date_to=date_to,
                limit=limit,
                offset=offset
            )

        if content_type in ["threads", "both"]:
            results["threads"] = self.search_threads(
                query=query,
                forums=forums,
                limit=limit,
                offset=offset
            )

        return results

    # ==================== Settings Management ====================

    def get_setting(self, name: str) -> dict[str, Any] | None:
        """Get a setting by name.

        Args:
            name: Setting name (e.g., 'boardclosed', 'bbname')

        Returns:
            Setting dict with sid, name, title, value, etc. or None if not found
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT sid, name, title, description, optionscode, value, disporder, gid, isdefault "
                f"FROM {self.table('settings')} WHERE name = %s",
                (name,)
            )
            return cur.fetchone()

    def set_setting(self, name: str, value: str) -> bool:
        """Update a setting value by name.

        Args:
            name: Setting name
            value: New value

        Returns:
            True if updated successfully

        Note:
            After updating settings, cache should be rebuilt with rebuild_cache('settings')
        """
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('settings')} SET value = %s WHERE name = %s",
                (value, name)
            )
            return cur.rowcount > 0

    def list_settings(self, gid: int | None = None) -> list[dict[str, Any]]:
        """List all settings or by group.

        Args:
            gid: Optional setting group ID to filter by

        Returns:
            List of setting dicts
        """
        with self.cursor() as cur:
            if gid is not None:
                cur.execute(
                    f"SELECT sid, name, title, description, optionscode, value, disporder, gid, isdefault "
                    f"FROM {self.table('settings')} WHERE gid = %s ORDER BY disporder",
                    (gid,)
                )
            else:
                cur.execute(
                    f"SELECT sid, name, title, description, optionscode, value, disporder, gid, isdefault "
                    f"FROM {self.table('settings')} ORDER BY gid, disporder"
                )
            return cur.fetchall()

    def list_setting_groups(self) -> list[dict[str, Any]]:
        """List all setting groups.

        Returns:
            List of setting group dicts with gid, name, title, description
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT gid, name, title, description, disporder, isdefault "
                f"FROM {self.table('settinggroups')} ORDER BY disporder"
            )
            return cur.fetchall()

    # ==================== Cache Management ====================

    def read_cache(self, title: str) -> str | None:
        """Read a cache entry by title.

        Args:
            title: Cache title (e.g., 'settings', 'plugins', 'usergroups')

        Returns:
            Serialized cache data (PHP serialized string) or None if not found
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT cache FROM {self.table('datacache')} WHERE title = %s",
                (title,)
            )
            result = cur.fetchone()
            return result['cache'] if result else None

    def rebuild_cache(self, cache_type: str = "all") -> dict[str, Any]:
        """Rebuild MyBB cache entries.

        Args:
            cache_type: Cache type to rebuild or 'all' for all caches

        Returns:
            Dict with status and affected caches

        Note:
            This clears cache entries from datacache table.
            MyBB will regenerate them on next access.
            Common cache types: settings, plugins, usergroups, forums,
                               badwords, smilies, posticons, etc.
        """
        with self.cursor() as cur:
            if cache_type == "all":
                # Clear all cache entries
                cur.execute(f"DELETE FROM {self.table('datacache')}")
                return {
                    "status": "success",
                    "message": "All caches cleared",
                    "rows_affected": cur.rowcount
                }
            else:
                # Clear specific cache
                cur.execute(
                    f"DELETE FROM {self.table('datacache')} WHERE title = %s",
                    (cache_type,)
                )
                return {
                    "status": "success",
                    "message": f"Cache '{cache_type}' cleared",
                    "rows_affected": cur.rowcount
                }

    def list_caches(self) -> list[dict[str, Any]]:
        """List all cache entries.

        Returns:
            List of cache dicts with title and cache data length
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT title, LENGTH(cache) as size FROM {self.table('datacache')} ORDER BY title"
            )
            return cur.fetchall()

    def clear_cache(self, title: str | None = None) -> bool:
        """Clear specific cache or all caches.

        Args:
            title: Cache title to clear, or None for all

        Returns:
            True if cleared successfully
        """
        with self.cursor() as cur:
            if title is None:
                cur.execute(f"DELETE FROM {self.table('datacache')}")
            else:
                cur.execute(
                    f"DELETE FROM {self.table('datacache')} WHERE title = %s",
                    (title,)
                )
            return cur.rowcount > 0

    # ==================== Statistics ====================

    def get_forum_stats(self) -> dict[str, Any]:
        """Get forum statistics (users, threads, posts, newest member).

        Returns:
            Dict with total_users, total_threads, total_posts, newest_user info
        """
        with self.cursor() as cur:
            # Get counts
            cur.execute(
                f"SELECT "
                f"(SELECT COUNT(*) FROM {self.table('users')}) as total_users, "
                f"(SELECT COUNT(*) FROM {self.table('threads')}) as total_threads, "
                f"(SELECT COUNT(*) FROM {self.table('posts')}) as total_posts"
            )
            stats = cur.fetchone()

            # Get newest member
            cur.execute(
                f"SELECT uid, username, regdate FROM {self.table('users')} "
                f"ORDER BY regdate DESC LIMIT 1"
            )
            newest = cur.fetchone()

            return {
                "total_users": stats['total_users'],
                "total_threads": stats['total_threads'],
                "total_posts": stats['total_posts'],
                "newest_member": {
                    "uid": newest['uid'],
                    "username": newest['username'],
                    "regdate": newest['regdate']
                } if newest else None
            }

    def get_board_stats(self) -> dict[str, Any]:
        """Get overall board statistics.

        Returns:
            Dict with comprehensive board stats including forums, users, posts, threads
        """
        with self.cursor() as cur:
            # Get comprehensive counts
            cur.execute(
                f"SELECT "
                f"(SELECT COUNT(*) FROM {self.table('forums')}) as total_forums, "
                f"(SELECT COUNT(*) FROM {self.table('users')}) as total_users, "
                f"(SELECT COUNT(*) FROM {self.table('threads')}) as total_threads, "
                f"(SELECT COUNT(*) FROM {self.table('posts')}) as total_posts, "
                f"(SELECT COUNT(*) FROM {self.table('privatemessages')}) as total_pms"
            )
            stats = cur.fetchone()

            # Get most recent post
            cur.execute(
                f"SELECT pid, tid, fid, subject, dateline, username "
                f"FROM {self.table('posts')} ORDER BY dateline DESC LIMIT 1"
            )
            latest_post = cur.fetchone()

            # Get most active forum
            cur.execute(
                f"SELECT fid, name, threads, posts FROM {self.table('forums')} "
                f"WHERE type = 'f' ORDER BY posts DESC LIMIT 1"
            )
            active_forum = cur.fetchone()

            return {
                "total_forums": stats['total_forums'],
                "total_users": stats['total_users'],
                "total_threads": stats['total_threads'],
                "total_posts": stats['total_posts'],
                "total_private_messages": stats['total_pms'],
                "latest_post": {
                    "pid": latest_post['pid'],
                    "tid": latest_post['tid'],
                    "fid": latest_post['fid'],
                    "subject": latest_post['subject'],
                    "dateline": latest_post['dateline'],
                    "username": latest_post['username']
                } if latest_post else None,
                "most_active_forum": {
                    "fid": active_forum['fid'],
                    "name": active_forum['name'],
                    "threads": active_forum['threads'],
                    "posts": active_forum['posts']
                } if active_forum else None
            }

    # ==================== Plugin Operations ====================

    def get_plugins_cache(self) -> dict[str, Any]:
        """Get active plugins from datacache.

        Returns:
            Dict with 'raw' (serialized PHP) and 'plugins' (list of active plugin codenames)
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT cache FROM {self.table('datacache')} WHERE title = %s",
                ("plugins",)
            )
            row = cur.fetchone()
            if not row:
                return {"raw": "", "plugins": []}

            raw_cache = row["cache"]
            # Parse PHP serialized array (simple case: a:0:{} or a:N:{i:0;s:X:"name";...})
            plugins = []
            if raw_cache and raw_cache != "a:0:{}":
                # Extract plugin names from PHP serialized format
                # Pattern: s:LENGTH:"plugin_codename"
                import re
                pattern = r's:\d+:"([^"]+)"'
                plugins = re.findall(pattern, raw_cache)

            return {"raw": raw_cache, "plugins": plugins}

    def update_plugins_cache(self, plugins: list[str]) -> None:
        """Update active plugins in datacache.

        Note: This updates the cache but does NOT execute PHP _activate/_deactivate functions.
        The MCP server cannot execute PHP code.

        Args:
            plugins: List of active plugin codenames
        """
        # Generate PHP serialized array format
        if not plugins:
            serialized = "a:0:{}"
        else:
            # Format: a:N:{i:0;s:LEN:"name";i:1;s:LEN:"name2";...}
            parts = []
            for i, plugin in enumerate(plugins):
                parts.append(f'i:{i};s:{len(plugin)}:"{plugin}"')
            serialized = f"a:{len(plugins)}:{{{';'.join(parts)}}}"

        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('datacache')} SET cache = %s WHERE title = %s",
                (serialized, "plugins")
            )

    def is_plugin_installed(self, codename: str) -> bool:
        """Check if a plugin is currently active.

        Args:
            codename: Plugin codename

        Returns:
            True if plugin is in active plugins cache
        """
        cache = self.get_plugins_cache()
        return codename in cache["plugins"]

    # ==================== Task Operations ====================

    def list_tasks(self, enabled_only: bool = False) -> list[dict[str, Any]]:
        """List all scheduled tasks.

        Args:
            enabled_only: If True, only return enabled tasks

        Returns:
            List of task records
        """
        with self.cursor() as cur:
            if enabled_only:
                cur.execute(
                    f"SELECT * FROM {self.table('tasks')} WHERE enabled = 1 ORDER BY title"
                )
            else:
                cur.execute(
                    f"SELECT * FROM {self.table('tasks')} ORDER BY title"
                )
            return cur.fetchall()

    def get_task(self, tid: int) -> dict[str, Any] | None:
        """Get task details by ID.

        Args:
            tid: Task ID

        Returns:
            Task record or None if not found
        """
        with self.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self.table('tasks')} WHERE tid = %s",
                (tid,)
            )
            return cur.fetchone()

    def enable_task(self, tid: int) -> bool:
        """Enable a scheduled task.

        Args:
            tid: Task ID

        Returns:
            True if task was updated
        """
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('tasks')} SET enabled = 1 WHERE tid = %s",
                (tid,)
            )
            return cur.rowcount > 0

    def disable_task(self, tid: int) -> bool:
        """Disable a scheduled task.

        Args:
            tid: Task ID

        Returns:
            True if task was updated
        """
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('tasks')} SET enabled = 0 WHERE tid = %s",
                (tid,)
            )
            return cur.rowcount > 0

    def update_task_nextrun(self, tid: int, nextrun: int) -> bool:
        """Update task next run time.

        Args:
            tid: Task ID
            nextrun: Unix timestamp for next run

        Returns:
            True if task was updated
        """
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('tasks')} SET nextrun = %s WHERE tid = %s",
                (nextrun, tid)
            )
            return cur.rowcount > 0

    def get_task_logs(self, tid: int | None = None, limit: int = 50) -> list[dict[str, Any]]:
        """Get task execution log.

        Args:
            tid: Optional task ID to filter by
            limit: Maximum number of log entries (default 50, max 500)

        Returns:
            List of task log records
        """
        limit = max(1, min(limit, 500))

        with self.cursor() as cur:
            if tid is not None:
                cur.execute(
                    f"SELECT * FROM {self.table('tasklogs')} WHERE tid = %s ORDER BY dateline DESC LIMIT %s",
                    (tid, limit)
                )
            else:
                cur.execute(
                    f"SELECT * FROM {self.table('tasklogs')} ORDER BY dateline DESC LIMIT %s",
                    (limit,)
                )
            return cur.fetchall()

    # ==================== Moderation Methods ====================

    def close_thread(self, tid: int, closed: bool = True) -> bool:
        """Close or open a thread.

        Args:
            tid: Thread ID
            closed: True to close, False to open

        Returns:
            True if updated, False otherwise
        """
        closed_value = 1 if closed else 0
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET closed = %s WHERE tid = %s",
                (closed_value, tid)
            )
            return cur.rowcount > 0

    def stick_thread(self, tid: int, sticky: bool = True) -> bool:
        """Stick or unstick a thread.

        Args:
            tid: Thread ID
            sticky: True to stick, False to unstick

        Returns:
            True if updated, False otherwise
        """
        sticky_value = 1 if sticky else 0
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET sticky = %s WHERE tid = %s",
                (sticky_value, tid)
            )
            return cur.rowcount > 0

    def approve_thread(self, tid: int, approve: bool = True) -> bool:
        """Approve or unapprove a thread.

        Args:
            tid: Thread ID
            approve: True to approve (visible=1), False to unapprove (visible=0)

        Returns:
            True if updated, False otherwise
        """
        visible_value = 1 if approve else 0
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('threads')} SET visible = %s WHERE tid = %s",
                (visible_value, tid)
            )
            return cur.rowcount > 0

    def approve_post(self, pid: int, approve: bool = True) -> bool:
        """Approve or unapprove a post.

        Args:
            pid: Post ID
            approve: True to approve (visible=1), False to unapprove (visible=0)

        Returns:
            True if updated, False otherwise
        """
        visible_value = 1 if approve else 0
        with self.cursor() as cur:
            cur.execute(
                f"UPDATE {self.table('posts')} SET visible = %s WHERE pid = %s",
                (visible_value, pid)
            )
            return cur.rowcount > 0

    def soft_delete_post(self, pid: int, delete: bool = True) -> bool:
        """Soft delete or restore a post.

        Args:
            pid: Post ID
            delete: True to soft delete (visible=-1), False to restore (visible=1)

        Returns:
            True if updated, False otherwise
        """
        import time
        visible_value = -1 if delete else 1
        with self.cursor() as cur:
            if delete:
                cur.execute(
                    f"UPDATE {self.table('posts')} SET visible = %s, deletetime = %s WHERE pid = %s",
                    (visible_value, int(time.time()), pid)
                )
            else:
                cur.execute(
                    f"UPDATE {self.table('posts')} SET visible = %s WHERE pid = %s",
                    (visible_value, pid)
                )
            return cur.rowcount > 0

    def add_modlog_entry(self, uid: int, fid: int, tid: int, pid: int, action: str, data: str = "", ipaddress: str = "") -> int:
        """Add a moderation log entry.

        Args:
            uid: User ID performing the action
            fid: Forum ID (0 if not applicable)
            tid: Thread ID (0 if not applicable)
            pid: Post ID (0 if not applicable)
            action: Action description
            data: Additional data (serialized)
            ipaddress: IP address of moderator

        Returns:
            Log entry ID if successful, 0 otherwise
        """
        import time
        with self.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {self.table('moderatorlog')}
                (uid, fid, tid, pid, action, data, ipaddress, dateline)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (uid, fid, tid, pid, action, data, ipaddress, int(time.time()))
            )
            return cur.lastrowid

    def list_modlog_entries(self, uid: int = None, fid: int = None, tid: int = None, limit: int = 50) -> list[dict]:
        """List moderation log entries with optional filters.

        Args:
            uid: Filter by moderator user ID
            fid: Filter by forum ID
            tid: Filter by thread ID
            limit: Maximum number of entries to return (1-100)

        Returns:
            List of moderation log entries
        """
        limit = max(1, min(100, limit))
        conditions = []
        params = []

        if uid is not None:
            conditions.append("uid = %s")
            params.append(uid)
        if fid is not None:
            conditions.append("fid = %s")
            params.append(fid)
        if tid is not None:
            conditions.append("tid = %s")
            params.append(tid)

        where_clause = f" WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        with self.cursor() as cur:
            cur.execute(
                f"SELECT * FROM {self.table('moderatorlog')}{where_clause} ORDER BY dateline DESC LIMIT %s",
                params
            )
            return cur.fetchall()

    # ==================== User Management Methods ====================

    def get_user(self, uid: int = None, username: str = None, sanitize: bool = True) -> dict | None:
        """Get user by UID or username.

        Args:
            uid: User ID
            username: Username
            sanitize: If True, exclude sensitive fields (password, salt, loginkey, regip, lastip)

        Returns:
            User dict if found, None otherwise
        """
        if not uid and not username:
            return None

        # Define sensitive fields to exclude
        sensitive_fields = ['password', 'salt', 'loginkey', 'regip', 'lastip']

        with self.cursor() as cur:
            if uid:
                cur.execute(f"SELECT * FROM {self.table('users')} WHERE uid = %s", (uid,))
            else:
                cur.execute(f"SELECT * FROM {self.table('users')} WHERE username = %s", (username,))

            user = cur.fetchone()

            if user and sanitize:
                # Remove sensitive fields
                for field in sensitive_fields:
                    user.pop(field, None)

            return user

    def list_users(self, usergroup: int = None, limit: int = 50, offset: int = 0) -> list[dict]:
        """List users with optional filters.

        Args:
            usergroup: Filter by usergroup ID
            limit: Maximum number of users to return (1-100)
            offset: Number of users to skip

        Returns:
            List of sanitized user dicts
        """
        limit = max(1, min(100, limit))
        offset = max(0, offset)

        # Always exclude sensitive fields in list operations
        sensitive_fields = ['password', 'salt', 'loginkey', 'regip', 'lastip']

        with self.cursor() as cur:
            if usergroup is not None:
                cur.execute(
                    f"SELECT * FROM {self.table('users')} WHERE usergroup = %s ORDER BY uid DESC LIMIT %s OFFSET %s",
                    (usergroup, limit, offset)
                )
            else:
                cur.execute(
                    f"SELECT * FROM {self.table('users')} ORDER BY uid DESC LIMIT %s OFFSET %s",
                    (limit, offset)
                )

            users = cur.fetchall()

            # Remove sensitive fields from all users
            for user in users:
                for field in sensitive_fields:
                    user.pop(field, None)

            return users

    def update_user_group(self, uid: int, usergroup: int, additionalgroups: str = None) -> bool:
        """Update user's usergroup and optionally additional groups.

        Args:
            uid: User ID
            usergroup: Primary usergroup ID
            additionalgroups: Comma-separated additional group IDs (optional)

        Returns:
            True if updated, False otherwise
        """
        with self.cursor() as cur:
            if additionalgroups is not None:
                cur.execute(
                    f"UPDATE {self.table('users')} SET usergroup = %s, additionalgroups = %s WHERE uid = %s",
                    (usergroup, additionalgroups, uid)
                )
            else:
                cur.execute(
                    f"UPDATE {self.table('users')} SET usergroup = %s WHERE uid = %s",
                    (usergroup, uid)
                )
            return cur.rowcount > 0

    def ban_user(self, uid: int, gid: int, admin: int, dateline: int, bantime: str, reason: str = "") -> int:
        """Add user to banned list.

        Args:
            uid: User ID to ban
            gid: Banned usergroup ID
            admin: Admin user ID performing the ban
            dateline: Ban timestamp
            bantime: Ban duration (e.g., "perm", "---")
            reason: Ban reason

        Returns:
            Ban entry ID if successful, 0 otherwise
        """
        with self.cursor() as cur:
            cur.execute(
                f"""INSERT INTO {self.table('banned')}
                (uid, gid, admin, dateline, bantime, reason)
                VALUES (%s, %s, %s, %s, %s, %s)""",
                (uid, gid, admin, dateline, bantime, reason)
            )
            return cur.lastrowid

    def unban_user(self, uid: int) -> bool:
        """Remove user from banned list.

        Args:
            uid: User ID to unban

        Returns:
            True if unbanned, False otherwise
        """
        with self.cursor() as cur:
            cur.execute(f"DELETE FROM {self.table('banned')} WHERE uid = %s", (uid,))
            return cur.rowcount > 0

    def list_usergroups(self) -> list[dict]:
        """List all usergroups.

        Returns:
            List of usergroup dicts
        """
        with self.cursor() as cur:
            cur.execute(f"SELECT * FROM {self.table('usergroups')} ORDER BY gid")
            return cur.fetchall()
