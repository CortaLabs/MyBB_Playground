"""SQLite database management for plugin/theme projects."""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any


class ProjectDatabase:
    """Manages SQLite database for tracking plugin/theme projects."""

    def __init__(self, db_path: str | Path):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Enable column access by name

        # Auto-initialize schema if tables don't exist
        self._ensure_tables()
        # Ensure deployed_files column exists (migration for existing DBs)
        self._ensure_deployed_files_column()

    def create_tables(self, schema_path: Optional[str | Path] = None) -> None:
        """Execute schema SQL to create tables.

        Args:
            schema_path: Path to projects.sql file. If None, uses default location.
        """
        if schema_path is None:
            schema_path = self.db_path.parent / "schema" / "projects.sql"
        else:
            schema_path = Path(schema_path)

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")

        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        self.conn.executescript(schema_sql)
        self.conn.commit()

    def _ensure_tables(self) -> None:
        """Check if tables exist and create them if not.

        This is called automatically on connection to handle first-run setup.
        """
        cursor = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
        )
        if cursor.fetchone() is None:
            # Tables don't exist, create them
            try:
                self.create_tables()
            except FileNotFoundError:
                # Schema file not found - create tables inline as fallback
                self.conn.executescript("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        codename TEXT UNIQUE NOT NULL,
                        display_name TEXT NOT NULL,
                        type TEXT NOT NULL DEFAULT 'plugin',
                        visibility TEXT NOT NULL DEFAULT 'public',
                        status TEXT NOT NULL DEFAULT 'development',
                        version TEXT NOT NULL DEFAULT '1.0.0',
                        description TEXT,
                        author TEXT,
                        mybb_compatibility TEXT DEFAULT '18*',
                        workspace_path TEXT NOT NULL,
                        deployed_files TEXT DEFAULT NULL,
                        created_at TEXT DEFAULT (datetime('now')),
                        updated_at TEXT DEFAULT (datetime('now')),
                        installed_at TEXT DEFAULT NULL
                    );
                    CREATE TABLE IF NOT EXISTS history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        action TEXT NOT NULL,
                        details TEXT,
                        timestamp TEXT DEFAULT (datetime('now')),
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    );
                    CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(type);
                    CREATE INDEX IF NOT EXISTS idx_projects_visibility ON projects(visibility);
                    CREATE INDEX IF NOT EXISTS idx_history_project_id ON history(project_id);
                """)
                self.conn.commit()

    def _ensure_deployed_files_column(self) -> None:
        """Ensure deployed_files column exists (migration for existing databases)."""
        cursor = self.conn.execute("PRAGMA table_info(projects)")
        columns = [row[1] for row in cursor.fetchall()]
        if 'deployed_files' not in columns:
            self.conn.execute("ALTER TABLE projects ADD COLUMN deployed_files TEXT DEFAULT NULL")
            self.conn.commit()

    def set_deployed_manifest(
        self,
        codename: str,
        files: List[Dict[str, Any]],
        directories: List[str],
        backups: Optional[List[str]] = None
    ) -> bool:
        """Store the deployment manifest for a project with full metadata.

        The manifest tracks all files and directories deployed to TestForum,
        enabling complete cleanup on uninstall. Includes file metadata for
        verification and auditing.

        Args:
            codename: Project codename
            files: List of file info dicts with keys:
                - path: Absolute path to deployed file
                - size: File size in bytes
                - mtime: Modification time (ISO format)
                - checksum: MD5 hash of file content
                - source: Original source path from workspace
            directories: List of absolute directory paths CREATED by us
            backups: List of backup file paths created (optional)

        Returns:
            True if updated successfully
        """
        timestamp = datetime.utcnow().isoformat()
        manifest = {
            "deployed_at": timestamp,
            "files": files,
            "directories": directories,
            "backups": backups or [],
            "file_count": len(files),
            "dir_count": len(directories)
        }
        manifest_json = json.dumps(manifest, indent=2)
        cursor = self.conn.execute(
            "UPDATE projects SET deployed_files = ?, updated_at = ? WHERE codename = ?",
            (manifest_json, timestamp, codename)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def get_deployed_manifest(self, codename: str) -> Dict[str, Any]:
        """Get the deployment manifest for a project.

        Args:
            codename: Project codename

        Returns:
            Dict with manifest data:
            - deployed_at: Timestamp of deployment
            - files: List of file info dicts (or paths for legacy)
            - directories: List of directory paths we created
            - backups: List of backup paths created
            - file_count: Number of files deployed
            - dir_count: Number of directories created
            Returns empty manifest structure if none found.
        """
        cursor = self.conn.execute(
            "SELECT deployed_files FROM projects WHERE codename = ?",
            (codename,)
        )
        row = cursor.fetchone()
        empty_manifest = {
            "deployed_at": None,
            "files": [],
            "directories": [],
            "backups": [],
            "file_count": 0,
            "dir_count": 0
        }

        if row and row[0]:
            try:
                data = json.loads(row[0])
                # Handle legacy format (simple list of paths)
                if isinstance(data, list):
                    return {
                        "deployed_at": None,
                        "files": [{"path": p} for p in data],  # Convert to new format
                        "directories": [],
                        "backups": [],
                        "file_count": len(data),
                        "dir_count": 0,
                        "_legacy": True
                    }
                # Handle old dict format (files as list of strings)
                if data.get("files") and isinstance(data["files"][0], str):
                    return {
                        "deployed_at": data.get("deployed_at"),
                        "files": [{"path": p} for p in data["files"]],
                        "directories": data.get("directories", []),
                        "backups": data.get("backups", []),
                        "file_count": len(data.get("files", [])),
                        "dir_count": len(data.get("directories", [])),
                        "_legacy": True
                    }
                # New format with full metadata
                return {
                    "deployed_at": data.get("deployed_at"),
                    "files": data.get("files", []),
                    "directories": data.get("directories", []),
                    "backups": data.get("backups", []),
                    "file_count": data.get("file_count", len(data.get("files", []))),
                    "dir_count": data.get("dir_count", len(data.get("directories", [])))
                }
            except json.JSONDecodeError:
                pass
        return empty_manifest

    def clear_deployed_manifest(self, codename: str) -> bool:
        """Clear the deployment manifest for a project.

        Args:
            codename: Project codename

        Returns:
            True if updated successfully
        """
        cursor = self.conn.execute(
            "UPDATE projects SET deployed_files = NULL, updated_at = ? WHERE codename = ?",
            (datetime.utcnow().isoformat(), codename)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def add_project(
        self,
        codename: str,
        display_name: str,
        workspace_path: str,
        type: str = "plugin",
        visibility: str = "public",
        status: str = "development",
        version: str = "1.0.0",
        description: Optional[str] = None,
        author: Optional[str] = None,
        mybb_compatibility: str = "18*"
    ) -> int:
        """Insert a new project.

        Args:
            codename: Unique plugin codename (e.g., "my_plugin")
            display_name: Human-readable name
            workspace_path: Relative path from workspace root
            type: 'plugin' or 'theme'
            visibility: 'public' or 'private'
            status: 'development', 'testing', 'installed', or 'archived'
            version: Semantic version string
            description: Plugin description
            author: Author name
            mybb_compatibility: MyBB version compatibility (e.g., "18*")

        Returns:
            The ID of the newly created project

        Raises:
            sqlite3.IntegrityError: If codename already exists
        """
        cursor = self.conn.execute(
            """
            INSERT INTO projects (
                codename, display_name, type, visibility, status, version,
                description, author, mybb_compatibility, workspace_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (codename, display_name, type, visibility, status, version,
             description, author, mybb_compatibility, workspace_path)
        )
        self.conn.commit()
        project_id = cursor.lastrowid

        # Log creation in history
        self.add_history(
            project_id,
            "created",
            json.dumps({"version": version, "visibility": visibility})
        )

        return project_id

    def get_project(self, codename: str) -> Optional[Dict[str, Any]]:
        """Retrieve project by codename.

        Args:
            codename: The project's unique codename

        Returns:
            Dict with project fields, or None if not found
        """
        cursor = self.conn.execute(
            "SELECT * FROM projects WHERE codename = ?",
            (codename,)
        )
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

    def update_project(self, codename: str, **kwargs) -> bool:
        """Update project fields.

        Args:
            codename: The project to update
            **kwargs: Fields to update (version, status, description, etc.)

        Returns:
            True if project was updated, False if not found
        """
        # Filter out None values and build SET clause
        updates = {k: v for k, v in kwargs.items() if v is not None}
        if not updates:
            return False

        # Always update updated_at timestamp
        updates['updated_at'] = datetime.utcnow().isoformat()

        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [codename]

        cursor = self.conn.execute(
            f"UPDATE projects SET {set_clause} WHERE codename = ?",
            values
        )
        self.conn.commit()

        if cursor.rowcount > 0:
            # Log update in history
            project = self.get_project(codename)
            if project:
                self.add_history(
                    project['id'],
                    "updated",
                    json.dumps(updates)
                )
            return True
        return False

    def delete_project(self, codename: str) -> bool:
        """Delete a project.

        Args:
            codename: The project to delete

        Returns:
            True if project was deleted, False if not found
        """
        cursor = self.conn.execute(
            "DELETE FROM projects WHERE codename = ?",
            (codename,)
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def list_projects(
        self,
        type: Optional[str] = None,
        visibility: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List projects with optional filters.

        Args:
            type: Filter by 'plugin' or 'theme'
            visibility: Filter by 'public' or 'private'
            status: Filter by status ('development', 'testing', etc.)

        Returns:
            List of project dicts
        """
        query = "SELECT * FROM projects WHERE 1=1"
        params = []

        if type is not None:
            query += " AND type = ?"
            params.append(type)
        if visibility is not None:
            query += " AND visibility = ?"
            params.append(visibility)
        if status is not None:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def add_history(
        self,
        project_id: int,
        action: str,
        details: Optional[str] = None
    ) -> int:
        """Log a history entry for a project.

        Args:
            project_id: The project ID
            action: Action name ('created', 'installed', 'synced', etc.)
            details: Optional JSON string with action-specific data

        Returns:
            The ID of the history entry
        """
        cursor = self.conn.execute(
            "INSERT INTO history (project_id, action, details) VALUES (?, ?, ?)",
            (project_id, action, details)
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_history(
        self,
        codename: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Retrieve history entries.

        Args:
            codename: Optional project codename to filter by
            limit: Maximum number of entries to return

        Returns:
            List of history entry dicts
        """
        if codename:
            query = """
                SELECT h.* FROM history h
                JOIN projects p ON h.project_id = p.id
                WHERE p.codename = ?
                ORDER BY h.timestamp DESC
                LIMIT ?
            """
            params = (codename, limit)
        else:
            query = """
                SELECT * FROM history
                ORDER BY timestamp DESC
                LIMIT ?
            """
            params = (limit,)

        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def close(self) -> None:
        """Close database connection."""
        self.conn.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
