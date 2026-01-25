#!/usr/bin/env python3
"""Test Task Package 1.5: SyncManifest utility methods."""

from pathlib import Path
import tempfile
import os
from mybb_mcp.sync.manifest import SyncManifest


def test_utility_methods():
    """Test update_file, remove_file, get_tracked_files, find_deleted_files."""

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)

        # Create manifest
        manifest_path = tmpdir / "test_manifest.json"
        m = SyncManifest(manifest_path)

        # Create test file
        test_file = tmpdir / "update_test.txt"
        test_file.write_text("test content")

        # Test update_file
        print("Testing update_file...")
        m.update_file(test_file, sync_direction="to_db", db_entity_type="template", db_sid=1)
        assert m._dirty == True, "Expected _dirty to be True after update_file"
        assert len(m.files) == 1, f"Expected 1 file, got {len(m.files)}"
        print("✓ update_file adds file and sets _dirty flag")

        # Test get_tracked_files
        print("\nTesting get_tracked_files...")
        tracked = m.get_tracked_files()
        assert len(tracked) == 1, f"Expected 1 tracked file, got {len(tracked)}"
        print(f"✓ get_tracked_files returns {len(tracked)} file(s): {tracked}")

        # Test remove_file (existing file)
        print("\nTesting remove_file on existing file...")
        removed = m.remove_file(test_file)
        assert removed == True, "Expected remove_file to return True for existing file"
        assert len(m.files) == 0, f"Expected 0 files after removal, got {len(m.files)}"
        print("✓ remove_file removes existing file and returns True")

        # Test remove_file (non-existent file)
        print("\nTesting remove_file on non-existent file...")
        removed2 = m.remove_file(Path(tmpdir / "nonexistent.txt"))
        assert removed2 == False, "Expected remove_file to return False for non-existent file"
        print("✓ remove_file returns False for non-existent file")

        # Test find_deleted_files
        print("\nTesting find_deleted_files...")
        # Add two files to manifest
        m.update_file(test_file)
        deleted_file = tmpdir / "deleted.txt"
        deleted_file.write_text("will be deleted")
        m.update_file(deleted_file)

        # Simulate deletion by only passing test_file as existing
        deleted = m.find_deleted_files({test_file})
        assert len(deleted) == 1, f"Expected 1 deleted file, got {len(deleted)}"
        assert "deleted.txt" in deleted[0], f"Expected 'deleted.txt' in result, got {deleted}"
        print(f"✓ find_deleted_files found: {deleted}")

        # Test with all files present
        no_deleted = m.find_deleted_files({test_file, deleted_file})
        assert len(no_deleted) == 0, f"Expected 0 deleted files when all present, got {len(no_deleted)}"
        print("✓ find_deleted_files returns empty list when all files present")

        # Test update_file with all parameters
        print("\nTesting update_file with all parameters...")
        m2 = SyncManifest(tmpdir / "test_manifest2.json")
        full_file = tmpdir / "full_params.txt"
        full_file.write_text("full test")

        m2.update_file(
            full_file,
            current_hash="abc123",  # Pre-computed hash
            sync_direction="from_db",
            db_entity_type="stylesheet",
            db_entity_id=42,
            db_sid=5,
            db_dateline=1234567890
        )

        rel_path = m2._relative_path(full_file)
        entry = m2.files[rel_path]
        assert entry.hash == "abc123", f"Expected hash 'abc123', got {entry.hash}"
        assert entry.sync_direction == "from_db", f"Expected 'from_db', got {entry.sync_direction}"
        assert entry.db_entity_type == "stylesheet", f"Expected 'stylesheet', got {entry.db_entity_type}"
        assert entry.db_entity_id == 42, f"Expected 42, got {entry.db_entity_id}"
        assert entry.db_sid == 5, f"Expected 5, got {entry.db_sid}"
        assert entry.db_dateline == 1234567890, f"Expected 1234567890, got {entry.db_dateline}"
        print("✓ update_file correctly stores all parameters")

        # Test save/load cycle
        print("\nTesting save/load persistence...")
        m2.save()
        m3 = SyncManifest(tmpdir / "test_manifest2.json")
        assert len(m3.files) == 1, "Expected saved manifest to persist"
        assert m3.files[rel_path].hash == "abc123", "Expected hash to persist"
        print("✓ Manifest saves and loads correctly")

        print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_utility_methods()
