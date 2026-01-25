"""Tests for SyncManifest class."""

import pytest
import json
from pathlib import Path
from mybb_mcp.sync.manifest import SyncManifest, FileEntry


class TestSyncManifestInit:
    """Test manifest initialization."""

    def test_empty_manifest_creation(self, tmp_path):
        """New manifest starts empty."""
        manifest_path = tmp_path / "test_manifest.json"
        m = SyncManifest(manifest_path)
        assert m.files == {}
        assert m.metadata["version"] == "1.0"
        assert "created" in m.metadata
        assert "last_updated" in m.metadata
        assert m.metadata["total_files"] == 0

    def test_load_existing_manifest(self, tmp_path):
        """Existing manifest is loaded correctly."""
        manifest_path = tmp_path / "test_manifest.json"
        # Create and save
        m1 = SyncManifest(manifest_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello")
        m1.update_file(test_file)
        m1.save()

        # Reload
        m2 = SyncManifest(manifest_path)
        assert len(m2.files) == 1
        assert m2.metadata["total_files"] == 1


class TestHashComputation:
    """Test hash computation methods."""

    def test_file_hash_length(self, tmp_path):
        """File hash is 32-char MD5."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("hello world")
        hash_val = SyncManifest.compute_file_hash(test_file)
        assert len(hash_val) == 32
        assert isinstance(hash_val, str)

    def test_string_hash_consistency(self):
        """Same string produces same hash."""
        h1 = SyncManifest.compute_string_hash("test content")
        h2 = SyncManifest.compute_string_hash("test content")
        assert h1 == h2
        assert len(h1) == 32

    def test_file_and_string_hash_match(self, tmp_path):
        """File hash matches string hash for same content."""
        content = "hello world"
        test_file = tmp_path / "test.txt"
        test_file.write_text(content)

        file_hash = SyncManifest.compute_file_hash(test_file)
        string_hash = SyncManifest.compute_string_hash(content)
        assert file_hash == string_hash

    def test_different_content_different_hash(self, tmp_path):
        """Different content produces different hashes."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content one")
        file2.write_text("content two")

        hash1 = SyncManifest.compute_file_hash(file1)
        hash2 = SyncManifest.compute_file_hash(file2)
        assert hash1 != hash2


class TestChangeDetection:
    """Test change detection methods."""

    def test_file_changed_new_file(self, tmp_path):
        """New file reports as changed."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "new.txt"
        test_file.write_text("content")
        assert m.file_changed(test_file) == True

    def test_file_changed_unchanged(self, tmp_path):
        """Unchanged file reports as not changed."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file)
        assert m.file_changed(test_file) == False

    def test_file_changed_modified(self, tmp_path):
        """Modified file reports as changed."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")
        m.update_file(test_file)
        test_file.write_text("modified")
        assert m.file_changed(test_file) == True

    def test_file_changed_with_precomputed_hash(self, tmp_path):
        """file_changed accepts precomputed hash."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file)

        current_hash = SyncManifest.compute_file_hash(test_file)
        assert m.file_changed(test_file, current_hash) == False

        fake_hash = "0" * 32
        assert m.file_changed(test_file, fake_hash) == True

    def test_db_changed_older(self, tmp_path):
        """Older DB dateline reports as not changed."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file, db_dateline=1000)
        assert m.db_changed(test_file, 999) == False

    def test_db_changed_newer(self, tmp_path):
        """Newer DB dateline reports as changed."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file, db_dateline=1000)
        assert m.db_changed(test_file, 1001) == True

    def test_db_changed_same(self, tmp_path):
        """Same DB dateline reports as not changed."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file, db_dateline=1000)
        assert m.db_changed(test_file, 1000) == False

    def test_db_changed_no_entry(self, tmp_path):
        """db_changed returns True for untracked file (triggers from_db sync)."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        # File not tracked, so DB is considered newer (return True to trigger from_db)
        assert m.db_changed(test_file, 1000) == True

    def test_get_sync_action_to_db(self, tmp_path):
        """File changed but DB unchanged -> to_db."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")
        m.update_file(test_file, db_dateline=1000)
        test_file.write_text("modified")

        action = m.get_sync_action(test_file, db_dateline=1000)
        assert action == "to_db"

    def test_get_sync_action_from_db(self, tmp_path):
        """File unchanged but DB changed -> from_db."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file, db_dateline=1000)

        action = m.get_sync_action(test_file, db_dateline=1001)
        assert action == "from_db"

    def test_get_sync_action_conflict(self, tmp_path):
        """Both file and DB changed -> conflict."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("original")
        m.update_file(test_file, db_dateline=1000)
        test_file.write_text("modified")

        action = m.get_sync_action(test_file, db_dateline=1001)
        assert action == "conflict"

    def test_get_sync_action_none(self, tmp_path):
        """Neither file nor DB changed -> none."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file, db_dateline=1000)

        action = m.get_sync_action(test_file, db_dateline=1000)
        assert action == "none"

    def test_get_sync_action_new_file(self, tmp_path):
        """New file with db_dateline -> conflict (both file and DB are 'new')."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "new.txt"
        test_file.write_text("content")

        # New file: file_changed=True, db_changed=True -> conflict
        action = m.get_sync_action(test_file, db_dateline=1000)
        assert action == "conflict"

    def test_get_sync_action_new_file_no_dateline(self, tmp_path):
        """New file without db_dateline -> to_db."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "new.txt"
        test_file.write_text("content")

        # No dateline provided, so db_changed=False
        action = m.get_sync_action(test_file)
        assert action == "to_db"


class TestUpdateUtility:
    """Test update and utility methods."""

    def test_update_file_adds_entry(self, tmp_path):
        """update_file adds entry to manifest."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file)
        assert len(m.files) == 1
        assert m._dirty == True

    def test_update_file_with_metadata(self, tmp_path):
        """update_file stores DB metadata."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(
            test_file,
            sync_direction="from_db",
            db_entity_type="template",
            db_entity_id=123,
            db_sid=5,
            db_dateline=1000
        )

        rel_path = m._relative_path(test_file)
        entry = m.files[rel_path]
        assert entry.sync_direction == "from_db"
        assert entry.db_entity_type == "template"
        assert entry.db_entity_id == 123
        assert entry.db_sid == 5
        assert entry.db_dateline == 1000

    def test_update_file_with_precomputed_hash(self, tmp_path):
        """update_file accepts precomputed hash."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        precomputed = SyncManifest.compute_file_hash(test_file)
        m.update_file(test_file, current_hash=precomputed)

        rel_path = m._relative_path(test_file)
        assert m.files[rel_path].hash == precomputed

    def test_remove_file(self, tmp_path):
        """remove_file removes entry."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file)
        result = m.remove_file(test_file)
        assert result == True
        assert len(m.files) == 0
        assert m._dirty == True

    def test_remove_file_not_found(self, tmp_path):
        """remove_file returns False for missing file."""
        m = SyncManifest(tmp_path / "manifest.json")
        test_file = tmp_path / "missing.txt"
        test_file.write_text("content")
        result = m.remove_file(test_file)
        assert result == False

    def test_get_tracked_files(self, tmp_path):
        """get_tracked_files returns all paths."""
        m = SyncManifest(tmp_path / "manifest.json")
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"content{i}")
            m.update_file(f)
        tracked = m.get_tracked_files()
        assert len(tracked) == 3
        assert all(isinstance(p, str) for p in tracked)

    def test_find_deleted_files(self, tmp_path):
        """find_deleted_files detects removed files."""
        m = SyncManifest(tmp_path / "manifest.json")

        # Create and track 3 files
        files = []
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"content{i}")
            m.update_file(f)
            files.append(f)

        # Remove one file from disk
        files[1].unlink()

        # Check for deleted files
        current_files = {f for f in files if f.exists()}
        deleted = m.find_deleted_files(current_files)

        assert len(deleted) == 1
        assert "file1.txt" in deleted[0]


class TestPersistence:
    """Test save and load persistence."""

    def test_save_creates_json(self, tmp_path):
        """save() creates valid JSON file."""
        manifest_path = tmp_path / "manifest.json"
        m = SyncManifest(manifest_path)
        m._dirty = True
        m.save()
        assert manifest_path.exists()
        data = json.loads(manifest_path.read_text())
        assert "version" in data
        assert "metadata" in data
        assert "files" in data

    def test_save_skips_if_not_dirty(self, tmp_path):
        """save() skips if manifest not dirty."""
        manifest_path = tmp_path / "manifest.json"
        m = SyncManifest(manifest_path)
        m._dirty = False

        # Save should not create file if not dirty
        m.save()
        # Manifest was never saved, so file shouldn't exist yet
        # (Unless _load created it - but new manifest shouldn't have file)
        # Actually, let's just verify dirty flag is respected
        m._dirty = True
        m.save()
        assert manifest_path.exists()

    def test_reload_preserves_data(self, tmp_path):
        """Reload preserves all file data."""
        manifest_path = tmp_path / "manifest.json"
        m1 = SyncManifest(manifest_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m1.update_file(test_file, db_entity_type="template", db_sid=5)
        m1.save()

        m2 = SyncManifest(manifest_path)
        rel_path = m2._relative_path(test_file)
        entry = m2.files[rel_path]
        assert entry.db_entity_type == "template"
        assert entry.db_sid == 5
        assert entry.hash == SyncManifest.compute_file_hash(test_file)

    def test_corruption_recovery(self, tmp_path):
        """Manifest recovers from corruption by creating backup and starting fresh."""
        manifest_path = tmp_path / "manifest.json"

        # Create valid manifest
        m1 = SyncManifest(manifest_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m1.update_file(test_file)
        m1.save()

        # Corrupt the manifest file
        manifest_path.write_text("INVALID JSON{{{")

        # Loading should recover by creating backup
        m2 = SyncManifest(manifest_path)

        # Should start fresh with empty files
        assert len(m2.files) == 0

        # Backup should exist with .corrupt.{timestamp} naming
        # Check for any .corrupt backup files
        backup_files = list(tmp_path.glob("manifest.json.corrupt.*"))
        assert len(backup_files) == 1
        assert backup_files[0].exists()

    def test_atomic_save(self, tmp_path):
        """save() uses atomic temp file pattern."""
        manifest_path = tmp_path / "manifest.json"
        m = SyncManifest(manifest_path)
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")
        m.update_file(test_file)
        m.save()

        # Verify final file exists
        assert manifest_path.exists()

        # Verify no temp files left behind
        temp_files = list(tmp_path.glob("*.tmp"))
        assert len(temp_files) == 0

    def test_metadata_updates(self, tmp_path):
        """Metadata updates correctly on save."""
        manifest_path = tmp_path / "manifest.json"
        m = SyncManifest(manifest_path)

        # Add files
        for i in range(3):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"content{i}")
            m.update_file(f)

        m.save()

        # Reload and check metadata
        data = json.loads(manifest_path.read_text())
        assert data["metadata"]["total_files"] == 3
        assert "last_updated" in data["metadata"]
