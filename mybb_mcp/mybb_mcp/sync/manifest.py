"""Sync manifest for hash-based change detection.

Tracks file hashes to enable incremental sync - only sync files that changed.
"""

import hashlib
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any


@dataclass
class FileEntry:
    """Metadata for a single file in the sync manifest.

    Tracks file hash, size, modification time, and sync state to enable
    incremental syncing - only sync files whose content has changed.

    Attributes:
        hash: MD5 hash of file content (hex digest)
        size: File size in bytes
        mtime: File modification time (from os.stat)
        last_sync: ISO 8601 timestamp of last successful sync
        sync_direction: "to_db" or "from_db" - direction of last sync
        db_entity_type: Type of DB entity ("template" or "stylesheet")
        db_entity_id: Database ID (tid for templates, stylesheet id for stylesheets)
        db_sid: Template set ID (sid) or theme ID
        db_dateline: Database modification timestamp (MyBB dateline field)
    """
    hash: str
    size: int
    mtime: float
    last_sync: str
    sync_direction: str
    db_entity_type: Optional[str] = None
    db_entity_id: Optional[int] = None
    db_sid: Optional[int] = None
    db_dateline: Optional[int] = None


class SyncManifest:
    """Manages manifest file for tracking file states across syncs.

    The manifest tracks which files have been synced and their state at last sync,
    enabling incremental sync - only sync files whose content has changed.

    Manifest structure:
    {
        "version": "1.0",
        "metadata": {
            "created": "2026-01-25T10:00:00",
            "last_updated": "2026-01-25T10:30:00",
            "total_files": 42
        },
        "files": {
            "relative/path/to/file.html": {
                "hash": "abc123...",
                "size": 1024,
                "mtime": 1234567890.0,
                "last_sync": "2026-01-25T10:30:00",
                "sync_direction": "to_db",
                "db_entity_type": "template",
                "db_entity_id": 123,
                "db_sid": 1,
                "db_dateline": 1234567890
            }
        }
    }

    Attributes:
        VERSION: Manifest format version
        path: Path to manifest JSON file
        files: Dictionary mapping relative file paths to FileEntry objects
        metadata: Manifest metadata (version, created, last_updated, total_files)
        _dirty: Whether manifest has unsaved changes
    """

    VERSION = "1.0"

    def __init__(self, manifest_path: Path):
        """Initialize manifest and load from disk if exists.

        Args:
            manifest_path: Path to manifest JSON file
        """
        self.path = manifest_path
        self.files: Dict[str, FileEntry] = {}
        self.metadata: Dict[str, Any] = {
            "version": self.VERSION,
            "created": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "total_files": 0
        }
        self._dirty: bool = False
        self._load()

    def _load(self) -> None:
        """Load manifest from disk.

        If file doesn't exist, starts with empty manifest.
        If file is corrupt, backs it up and starts fresh.
        """
        if not self.path.exists():
            return

        try:
            with open(self.path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Load metadata
            self.metadata = data.get("metadata", self.metadata)

            # Parse files dict - convert each entry to FileEntry
            files_data = data.get("files", {})
            for rel_path, entry_data in files_data.items():
                self.files[rel_path] = FileEntry(**entry_data)

        except (json.JSONDecodeError, KeyError, TypeError) as e:
            # Corrupt manifest - backup and start fresh
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            backup_path = self.path.parent / f"{self.path.name}.corrupt.{timestamp}"
            self.path.rename(backup_path)
            print(f"Warning: Corrupt manifest detected, backed up to {backup_path}")
            print(f"Error: {e}")
            # Keep empty files dict and default metadata

    def save(self) -> None:
        """Save manifest to disk using atomic write.

        Only writes if manifest has been modified (_dirty flag).
        Uses atomic write pattern: write to .tmp file, then replace.
        """
        if not self._dirty:
            return

        # Update metadata
        self.metadata["last_updated"] = datetime.utcnow().isoformat()
        self.metadata["total_files"] = len(self.files)

        # Build output dict
        output = {
            "version": self.VERSION,
            "metadata": self.metadata,
            "files": {
                rel_path: asdict(entry)
                for rel_path, entry in self.files.items()
            }
        }

        # Atomic write: write to temp file, then replace
        tmp_path = self.path.parent / f"{self.path.name}.tmp"
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)

        tmp_path.replace(self.path)
        self._dirty = False

    @staticmethod
    def compute_file_hash(file_path: Path) -> str:
        """Compute MD5 hash of file contents.

        Args:
            file_path: Path to file to hash

        Returns:
            MD5 hexdigest (32-character lowercase hex string)
        """
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            while chunk := f.read(65536):  # 64KB chunks
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def compute_string_hash(content: str) -> str:
        """Compute MD5 hash of string content.

        Args:
            content: String to hash

        Returns:
            MD5 hexdigest (32-character lowercase hex string)
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()

    def _relative_path(self, file_path: Path) -> str:
        """Convert absolute path to relative path from manifest directory.

        Args:
            file_path: Absolute path to convert

        Returns:
            Relative path string from manifest directory, or absolute path if outside manifest root
        """
        try:
            return str(file_path.resolve().relative_to(self.path.parent.resolve()))
        except ValueError:
            # Path is outside manifest root, use absolute
            return str(file_path.resolve())

    def file_changed(self, file_path: Path, current_hash: Optional[str] = None) -> bool:
        """Check if file content has changed since last sync.

        Args:
            file_path: Path to the file
            current_hash: Pre-computed hash (optional, computed if not provided)

        Returns:
            True if file is new or content changed, False if unchanged
        """
        rel_path = self._relative_path(file_path)
        if rel_path not in self.files:
            return True  # New file

        if current_hash is None:
            current_hash = self.compute_file_hash(file_path)

        return current_hash != self.files[rel_path].hash

    def db_changed(self, file_path: Path, db_dateline: int) -> bool:
        """Check if database entity has changed since last sync.

        Args:
            file_path: Path to the local file (for manifest lookup)
            db_dateline: Current dateline from database

        Returns:
            True if DB has newer data, False if unchanged
        """
        rel_path = self._relative_path(file_path)
        if rel_path not in self.files:
            return True  # Not tracked

        entry = self.files[rel_path]
        if entry.db_dateline is None:
            return True  # No dateline stored

        return db_dateline > entry.db_dateline

    def get_sync_action(self, file_path: Path, current_hash: Optional[str] = None,
                        db_dateline: Optional[int] = None) -> str:
        """Determine what sync action is needed for a file.

        Args:
            file_path: Path to the file
            current_hash: Pre-computed file hash (optional)
            db_dateline: Current DB dateline (optional)

        Returns:
            One of: "to_db", "from_db", "conflict", "none"
        """
        file_changed = self.file_changed(file_path, current_hash)
        db_changed = self.db_changed(file_path, db_dateline) if db_dateline else False

        if file_changed and db_changed:
            return "conflict"
        elif file_changed:
            return "to_db"
        elif db_changed:
            return "from_db"
        else:
            return "none"

    def update_file(self, file_path: Path, current_hash: Optional[str] = None,
                    sync_direction: str = "to_db", db_entity_type: Optional[str] = None,
                    db_entity_id: Optional[int] = None, db_sid: Optional[int] = None,
                    db_dateline: Optional[int] = None) -> None:
        """Update or add a file entry in the manifest.

        Args:
            file_path: Path to the file
            current_hash: Pre-computed hash (computed if not provided)
            sync_direction: "to_db" or "from_db"
            db_entity_type: "template" or "stylesheet" (optional)
            db_entity_id: Database entity ID (optional)
            db_sid: Template set ID or theme ID (optional)
            db_dateline: Database modification timestamp (optional)
        """
        if current_hash is None:
            current_hash = self.compute_file_hash(file_path)

        stat = file_path.stat()
        rel_path = self._relative_path(file_path)

        self.files[rel_path] = FileEntry(
            hash=current_hash,
            size=stat.st_size,
            mtime=stat.st_mtime,
            last_sync=datetime.utcnow().isoformat(),
            sync_direction=sync_direction,
            db_entity_type=db_entity_type,
            db_entity_id=db_entity_id,
            db_sid=db_sid,
            db_dateline=db_dateline
        )
        self._dirty = True

    def remove_file(self, file_path: Path) -> bool:
        """Remove a file entry from the manifest.

        Args:
            file_path: Path to the file

        Returns:
            True if file was removed, False if not found
        """
        rel_path = self._relative_path(file_path)
        if rel_path in self.files:
            del self.files[rel_path]
            self._dirty = True
            return True
        return False

    def get_tracked_files(self) -> list[str]:
        """Get list of all tracked file paths.

        Returns:
            List of relative paths for all tracked files
        """
        return list(self.files.keys())

    def find_deleted_files(self, current_files: set[Path]) -> list[str]:
        """Find files that were tracked but no longer exist.

        Args:
            current_files: Set of currently existing file paths

        Returns:
            List of relative paths that are tracked but not in current_files
        """
        current_relative = {self._relative_path(f) for f in current_files}
        return [path for path in self.files.keys() if path not in current_relative]
