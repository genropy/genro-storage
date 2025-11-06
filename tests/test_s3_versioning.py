"""Integration tests for S3 versioning using MinIO.

These tests require MinIO to be running with versioning enabled.
Start it with: docker-compose up -d
"""

import pytest
import time
from datetime import datetime, timedelta, timezone
from genro_storage import StorageManager


pytestmark = pytest.mark.integration

# Note: minio_versioned_bucket fixture is now in conftest.py


@pytest.fixture
def storage_with_versioning(minio_versioned_bucket, minio_config):
    """Create StorageManager with versioned S3 bucket.

    Args:
        minio_versioned_bucket: Versioned bucket fixture
        minio_config: MinIO configuration fixture

    Returns:
        StorageManager: Storage manager with versioned S3
    """
    storage = StorageManager()
    storage.configure(
        [
            {
                "name": "s3",
                "type": "s3",
                "bucket": minio_versioned_bucket,
                "endpoint_url": minio_config["endpoint_url"],
                "key": minio_config["aws_access_key_id"],
                "secret": minio_config["aws_secret_access_key"],
            }
        ]
    )
    return storage


class TestS3Versioning:
    """Tests for S3 versioning support."""

    def test_versioning_capability(self, storage_with_versioning):
        """Versioned S3 bucket reports versioning capability."""
        node = storage_with_versioning.node("s3:test.txt")
        node.write("initial")

        caps = node.capabilities
        assert caps.versioning is True
        assert caps.version_listing is True
        assert caps.version_access is True

    def test_version_count(self, storage_with_versioning):
        """version_count returns number of versions."""
        node = storage_with_versioning.node("s3:test.txt")

        # Create first version
        node.write("v1")
        assert node.version_count >= 1  # At least one version

        # Create second version
        node.write("v2")
        assert node.version_count >= 2  # At least two versions

        # Create third version
        node.write("v3")
        assert node.version_count >= 3  # At least three versions

    def test_versions_list(self, storage_with_versioning):
        """versions property returns list with metadata."""
        node = storage_with_versioning.node("s3:document.txt")

        # Create multiple versions
        node.write("version 1")
        time.sleep(0.1)  # Small delay to ensure different timestamps
        node.write("version 2")
        time.sleep(0.1)
        node.write("version 3")

        versions = node.versions

        # Should have 3 versions
        assert len(versions) == 3

        # Check structure
        for v in versions:
            assert "version_id" in v
            assert "is_latest" in v
            assert "last_modified" in v
            assert "size" in v
            assert "etag" in v

        # Latest version should be marked
        latest_versions = [v for v in versions if v["is_latest"]]
        assert len(latest_versions) == 1

    def test_open_with_version_index(self, storage_with_versioning):
        """open() with version parameter accesses specific versions."""
        node = storage_with_versioning.node("s3:file.txt")

        # Create versions
        node.write("content v1")
        node.write("content v2")
        node.write("content v3")

        # Read current version (default)
        with node.open(mode="r") as f:
            assert f.read() == "content v3"

        # Read previous version (negative indexing)
        with node.open(version=-2, mode="r") as f:
            assert f.read() == "content v2"

        # Read first version
        with node.open(version=-3, mode="r") as f:
            assert f.read() == "content v1"

    def test_open_with_version_id(self, storage_with_versioning):
        """open() accepts version_id string."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("original")
        node.write("modified")

        versions = node.versions
        first_version_id = versions[0]["version_id"]  # Oldest (versions sorted oldest→newest)

        # Read by version_id
        with node.open(version=first_version_id, mode="r") as f:
            content = f.read()
            assert content == "original"

    def test_open_version_read_only(self, storage_with_versioning):
        """Cannot write to historical versions."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("v1")
        node.write("v2")

        # Try to write to old version - should fail
        with pytest.raises(ValueError, match="Cannot write to historical versions"):
            with node.open(version=-2, mode="w"):
                pass

    def test_compare_versions_using_nodes(self, storage_with_versioning):
        """Compare versions using versioned nodes."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("first content")
        node.write("second content")
        node.write("third content")

        # Create versioned nodes
        current = storage_with_versioning.node("s3:file.txt", version=-1)
        previous = storage_with_versioning.node("s3:file.txt", version=-2)
        oldest = storage_with_versioning.node("s3:file.txt", version=-3)

        # Compare content
        assert current.read() == "third content"
        assert previous.read() == "second content"
        assert oldest.read() == "first content"

        # Versioned nodes are read-only
        assert current.capabilities.versioning is False
        with pytest.raises(ValueError, match="Cannot write to versioned snapshot"):
            current.write("new")

    def test_restore_previous_version_by_reading_and_writing(self, storage_with_versioning):
        """Restore previous version by reading from versioned snapshot and writing."""
        node = storage_with_versioning.node("s3:config.json")

        node.write('{"version": 1}')
        node.write('{"version": 2}')
        node.write('{"version": 3, "broken": true}')

        # Restore previous version by reading from snapshot and writing to current
        previous = storage_with_versioning.node("s3:config.json", version=-2)
        node.write(previous.read())

        # Should have v2 content
        content = node.read()
        assert content == '{"version": 2}'

        # Should create a new version (not delete)
        assert node.version_count == 4  # v1, v2, v3, v2-restored

    def test_restore_specific_version_by_reading_and_writing(self, storage_with_versioning):
        """Restore any specific version by reading from versioned snapshot and writing."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("v1")
        node.write("v2")
        node.write("v3")
        node.write("v4")

        # Restore v2 (two versions back from v4) by reading and writing
        v2_snapshot = storage_with_versioning.node(
            "s3:file.txt", version=-3
        )  # v1=index -4, v2=index -3, v3=index -2, v4=index -1
        node.write(v2_snapshot.read())

        assert node.read() == "v2"

    def test_write_bytes_skip_if_unchanged_with_s3(self, storage_with_versioning):
        """write_bytes(skip_if_unchanged=True) uses ETag to detect duplicates on S3."""
        node = storage_with_versioning.node("s3:data.bin")

        data1 = b"Hello World"

        # First write - should succeed
        changed = node.write(data1, skip_if_unchanged=True, mode="wb")
        assert changed is True
        assert node.version_count == 1

        # Same content - should skip
        changed = node.write(data1, skip_if_unchanged=True, mode="wb")
        assert changed is False
        assert node.version_count == 1  # No new version

        # Different content - should write
        data2 = b"Different content"
        changed = node.write(data2, skip_if_unchanged=True, mode="wb")
        assert changed is True
        assert node.version_count == 2

    def test_write_text_skip_if_unchanged_with_s3(self, storage_with_versioning):
        """write_text(skip_if_unchanged=True) uses ETag to detect duplicates."""
        node = storage_with_versioning.node("s3:config.txt")

        # First write
        changed = node.write("config=value1", skip_if_unchanged=True)
        assert changed is True

        # Same content - skip
        changed = node.write("config=value1", skip_if_unchanged=True)
        assert changed is False

        # Different content - write
        changed = node.write("config=value2", skip_if_unchanged=True)
        assert changed is True

    def test_compact_versions_removes_consecutive_duplicates(self, storage_with_versioning):
        """compact_versions() removes consecutive duplicate versions."""
        node = storage_with_versioning.node("s3:file.txt")

        # Create version history with duplicates
        node.write("content A")  # v1
        node.write("content A")  # v2 - duplicate of v1
        node.write("content B")  # v3
        node.write("content B")  # v4 - duplicate of v3
        node.write("content A")  # v5 - not consecutive to v1, keep!

        assert node.version_count == 5

        # Compact - should remove v2 and v4
        removed = node.compact_versions()
        assert removed == 2

        # Should have 3 versions left: v1, v3, v5
        assert node.version_count == 3

        # Verify content progression
        versions = node.versions
        with node.open(version=-3) as f:  # Oldest remaining
            assert f.read() == "content A"
        with node.open(version=-2) as f:  # Middle
            assert f.read() == "content B"
        with node.open(version=-1) as f:  # Latest
            assert f.read() == "content A"

    def test_compact_versions_dry_run(self, storage_with_versioning):
        """compact_versions(dry_run=True) reports without deleting."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("A")
        node.write("A")  # duplicate
        node.write("B")
        node.write("B")  # duplicate

        # Dry run
        would_remove = node.compact_versions(dry_run=True)
        assert would_remove == 2

        # Nothing actually deleted
        assert node.version_count == 4

    def test_compact_versions_no_duplicates(self, storage_with_versioning):
        """compact_versions() with no duplicates removes nothing."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("A")
        node.write("B")
        node.write("C")

        removed = node.compact_versions()
        assert removed == 0
        assert node.version_count == 3

    def test_open_with_as_of_datetime(self, storage_with_versioning):
        """open() with as_of parameter accesses version at specific time."""
        from datetime import timedelta

        node = storage_with_versioning.node("s3:timebased.txt")

        # Create first version
        node.write("past content")

        # Get the timestamp from S3 for the first version
        versions = node.versions
        first_version_time = versions[0]["last_modified"]

        # Wait to ensure timestamp separation
        time.sleep(1)

        # Create newer version
        node.write("current content")

        # Use a time slightly after the first version but before the second
        query_time = first_version_time + timedelta(seconds=0.5)

        # Read version as it was at that time
        with node.open(as_of=query_time) as f:
            content = f.read()
            assert content == "past content"

        # Read current version
        with node.open() as f:
            content = f.read()
            assert content == "current content"

    def test_version_info_includes_etag(self, storage_with_versioning):
        """Version info includes ETag for content comparison."""
        node = storage_with_versioning.node("s3:file.txt")

        node.write("content")

        versions = node.versions
        assert len(versions) == 1

        version_info = versions[0]
        assert "etag" in version_info
        assert version_info["etag"]  # Not empty
        assert isinstance(version_info["etag"], str)


class TestS3VersioningEdgeCases:
    """Edge case tests for S3 versioning."""

    def test_restore_single_version_by_reading_and_writing(self, storage_with_versioning):
        """Reading and writing single-version file duplicates that version."""
        node = storage_with_versioning.node("s3:single.txt")

        node.write("only version")
        assert node.version_count == 1

        # Restore by reading from snapshot and writing - restores same content
        snapshot = storage_with_versioning.node("s3:single.txt", version=-1)
        node.write(snapshot.read())

        # Should have 2 identical versions now
        assert node.version_count == 2
        assert node.read() == "only version"

    def test_compact_versions_preserves_non_consecutive(self, storage_with_versioning):
        """compact_versions() keeps non-consecutive duplicates."""
        node = storage_with_versioning.node("s3:file.txt")

        # Create pattern: A, A, B, A (last A is non-consecutive)
        node.write("A")  # v1
        node.write("A")  # v2 - consecutive duplicate, remove
        node.write("B")  # v3
        node.write("A")  # v4 - non-consecutive to v1, KEEP

        removed = node.compact_versions()
        assert removed == 1  # Only v2 removed

        # v1, v3, v4 should remain
        assert node.version_count == 3

    def test_versions_sorted_by_time(self, storage_with_versioning):
        """versions list is sorted by modification time."""
        node = storage_with_versioning.node("s3:file.txt")

        # Create versions with delays
        node.write("v1")
        time.sleep(0.1)
        node.write("v2")
        time.sleep(0.1)
        node.write("v3")

        versions = node.versions

        # Should be sorted oldest to newest
        for i in range(len(versions) - 1):
            assert versions[i]["last_modified"] <= versions[i + 1]["last_modified"]

    def test_versioning_not_enabled_on_bucket(self, minio_bucket, minio_config):
        """Bucket without versioning shows version_id as 'null'."""
        # Use bucket without versioning
        storage = StorageManager()
        storage.configure(
            [
                {
                    "name": "s3",
                    "type": "s3",
                    "bucket": minio_bucket,  # This bucket does NOT have versioning
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                }
            ]
        )

        node = storage.node("s3:test.txt")
        node.write("content")

        # S3 still returns a "version" even without versioning enabled,
        # but version_id will be 'null' (standard S3 behavior)
        versions = node.versions
        assert len(versions) == 1
        assert versions[0]["version_id"] == "null"
        assert node.version_count == 1

        # Writing again should NOT create a new version (overwrites)
        node.write("content2")
        versions_after = node.versions
        assert len(versions_after) == 1  # Still only one "version"
        assert versions_after[0]["version_id"] == "null"

    def test_version_at_index_no_versions_raises_error(self, storage_with_versioning):
        """_resolve_version_index() raises IndexError when no versions."""
        node = storage_with_versioning.node("s3:nonexistent.txt")

        # File doesn't exist, no versions
        with pytest.raises(IndexError, match="No versions available"):
            node._resolve_version_index(0)

    def test_version_at_index_out_of_range_raises_error(self, storage_with_versioning):
        """_resolve_version_index() raises IndexError when index out of range."""
        node = storage_with_versioning.node("s3:file.txt")
        node.write("v1")
        node.write("v2")

        # Only 2 versions, index 5 is out of range
        with pytest.raises(IndexError, match="out of range"):
            node._resolve_version_index(5)

        # Negative index out of range
        with pytest.raises(IndexError, match="out of range"):
            node._resolve_version_index(-10)

    def test_version_at_date_with_naive_datetime(self, storage_with_versioning):
        """_resolve_version_at_date() handles naive datetime (no timezone)."""
        node = storage_with_versioning.node("s3:file.txt")

        # Create version
        node.write("v1")
        time.sleep(0.5)

        # Use naive datetime (no timezone info)
        target_date = datetime.now() + timedelta(hours=1)

        # Should work - naive datetime converted to UTC
        version_id = node._resolve_version_at_date(target_date)
        assert version_id is not None

    def test_version_at_date_before_all_versions_returns_none(self, storage_with_versioning):
        """_resolve_version_at_date() returns None when date is before all versions."""
        node = storage_with_versioning.node("s3:file.txt")

        # Create version
        time.sleep(0.5)
        node.write("v1")

        # Date before file was created
        target_date = datetime.now(timezone.utc) - timedelta(days=1)

        # Should return None (no versions before this date)
        version_id = node._resolve_version_at_date(target_date)
        assert version_id is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
