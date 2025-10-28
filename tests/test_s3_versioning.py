"""Integration tests for S3 versioning using MinIO.

These tests require MinIO to be running with versioning enabled.
Start it with: docker-compose up -d
"""

import pytest
import time
from datetime import datetime, timedelta
from genro_storage import StorageManager


pytestmark = pytest.mark.integration


@pytest.fixture
def minio_versioned_bucket(minio_client):
    """Create a bucket with versioning enabled.

    Args:
        minio_client: MinIO S3 client fixture

    Yields:
        str: Name of the versioned bucket
    """
    bucket_name = f"test-versioned-{int(time.time())}"

    # Create bucket
    minio_client.create_bucket(Bucket=bucket_name)

    # Enable versioning
    minio_client.put_bucket_versioning(
        Bucket=bucket_name,
        VersioningConfiguration={'Status': 'Enabled'}
    )

    yield bucket_name

    # Cleanup: delete all versions then bucket
    try:
        # List and delete all object versions
        paginator = minio_client.get_paginator('list_object_versions')
        for page in paginator.paginate(Bucket=bucket_name):
            # Delete versions
            if 'Versions' in page:
                versions = [
                    {'Key': v['Key'], 'VersionId': v['VersionId']}
                    for v in page['Versions']
                ]
                if versions:
                    minio_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': versions, 'Quiet': True}
                    )

            # Delete delete markers
            if 'DeleteMarkers' in page:
                markers = [
                    {'Key': m['Key'], 'VersionId': m['VersionId']}
                    for m in page['DeleteMarkers']
                ]
                if markers:
                    minio_client.delete_objects(
                        Bucket=bucket_name,
                        Delete={'Objects': markers, 'Quiet': True}
                    )

        # Delete bucket
        minio_client.delete_bucket(Bucket=bucket_name)
    except Exception as e:
        print(f"Warning: Failed to cleanup versioned bucket {bucket_name}: {e}")


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
    storage.configure([{
        'name': 's3',
        'type': 's3',
        'bucket': minio_versioned_bucket,
        'endpoint_url': minio_config['endpoint_url'],
        'key': minio_config['aws_access_key_id'],
        'secret': minio_config['aws_secret_access_key'],
    }])
    return storage


class TestS3Versioning:
    """Tests for S3 versioning support."""

    def test_versioning_capability(self, storage_with_versioning):
        """Versioned S3 bucket reports versioning capability."""
        node = storage_with_versioning.node('s3:test.txt')
        node.write_text('initial')

        caps = node.capabilities
        assert caps.versioning is True
        assert caps.version_listing is True
        assert caps.version_access is True

    def test_version_count(self, storage_with_versioning):
        """version_count returns number of versions."""
        node = storage_with_versioning.node('s3:test.txt')

        # Create first version
        node.write_text('v1')
        assert node.version_count >= 1  # At least one version

        # Create second version
        node.write_text('v2')
        assert node.version_count >= 2  # At least two versions

        # Create third version
        node.write_text('v3')
        assert node.version_count >= 3  # At least three versions

    def test_versions_list(self, storage_with_versioning):
        """versions property returns list with metadata."""
        node = storage_with_versioning.node('s3:document.txt')

        # Create multiple versions
        node.write_text('version 1')
        time.sleep(0.1)  # Small delay to ensure different timestamps
        node.write_text('version 2')
        time.sleep(0.1)
        node.write_text('version 3')

        versions = node.versions

        # Should have 3 versions
        assert len(versions) == 3

        # Check structure
        for v in versions:
            assert 'version_id' in v
            assert 'is_latest' in v
            assert 'last_modified' in v
            assert 'size' in v
            assert 'etag' in v

        # Latest version should be marked
        latest_versions = [v for v in versions if v['is_latest']]
        assert len(latest_versions) == 1

    def test_open_with_version_index(self, storage_with_versioning):
        """open() with version parameter accesses specific versions."""
        node = storage_with_versioning.node('s3:file.txt')

        # Create versions
        node.write_text('content v1')
        node.write_text('content v2')
        node.write_text('content v3')

        # Read current version (default)
        with node.open(mode='r') as f:
            assert f.read() == 'content v3'

        # Read previous version (negative indexing)
        with node.open(version=-2, mode='r') as f:
            assert f.read() == 'content v2'

        # Read first version
        with node.open(version=-3, mode='r') as f:
            assert f.read() == 'content v1'

    def test_open_with_version_id(self, storage_with_versioning):
        """open() accepts version_id string."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('original')
        node.write_text('modified')

        versions = node.versions
        first_version_id = versions[0]['version_id']  # Oldest (versions sorted oldest→newest)

        # Read by version_id
        with node.open(version=first_version_id, mode='r') as f:
            content = f.read()
            assert content == 'original'

    def test_open_version_read_only(self, storage_with_versioning):
        """Cannot write to historical versions."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('v1')
        node.write_text('v2')

        # Try to write to old version - should fail
        with pytest.raises(ValueError, match='Cannot write to historical versions'):
            with node.open(version=-2, mode='w'):
                pass

    def test_compare_versions_using_nodes(self, storage_with_versioning):
        """Compare versions using versioned nodes."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('first content')
        node.write_text('second content')
        node.write_text('third content')

        # Create versioned nodes
        current = storage_with_versioning.node('s3:file.txt', version=-1)
        previous = storage_with_versioning.node('s3:file.txt', version=-2)
        oldest = storage_with_versioning.node('s3:file.txt', version=-3)

        # Compare content
        assert current.read_text() == 'third content'
        assert previous.read_text() == 'second content'
        assert oldest.read_text() == 'first content'

        # Versioned nodes are read-only
        assert current.capabilities.versioning is False
        with pytest.raises(ValueError, match='Cannot write to versioned snapshot'):
            current.write_text('new')

    def test_restore_previous_version_by_reading_and_writing(self, storage_with_versioning):
        """Restore previous version by reading from versioned snapshot and writing."""
        node = storage_with_versioning.node('s3:config.json')

        node.write_text('{"version": 1}')
        node.write_text('{"version": 2}')
        node.write_text('{"version": 3, "broken": true}')

        # Restore previous version by reading from snapshot and writing to current
        previous = storage_with_versioning.node('s3:config.json', version=-2)
        node.write_text(previous.read_text())

        # Should have v2 content
        content = node.read_text()
        assert content == '{"version": 2}'

        # Should create a new version (not delete)
        assert node.version_count == 4  # v1, v2, v3, v2-restored

    def test_restore_specific_version_by_reading_and_writing(self, storage_with_versioning):
        """Restore any specific version by reading from versioned snapshot and writing."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('v1')
        node.write_text('v2')
        node.write_text('v3')
        node.write_text('v4')

        # Restore v2 (two versions back from v4) by reading and writing
        v2_snapshot = storage_with_versioning.node('s3:file.txt', version=-3)  # v1=index -4, v2=index -3, v3=index -2, v4=index -1
        node.write_text(v2_snapshot.read_text())

        assert node.read_text() == 'v2'

    def test_write_bytes_skip_if_unchanged_with_s3(self, storage_with_versioning):
        """write_bytes(skip_if_unchanged=True) uses ETag to detect duplicates on S3."""
        node = storage_with_versioning.node('s3:data.bin')

        data1 = b'Hello World'

        # First write - should succeed
        changed = node.write_bytes(data1, skip_if_unchanged=True)
        assert changed is True
        assert node.version_count == 1

        # Same content - should skip
        changed = node.write_bytes(data1, skip_if_unchanged=True)
        assert changed is False
        assert node.version_count == 1  # No new version

        # Different content - should write
        data2 = b'Different content'
        changed = node.write_bytes(data2, skip_if_unchanged=True)
        assert changed is True
        assert node.version_count == 2

    def test_write_text_skip_if_unchanged_with_s3(self, storage_with_versioning):
        """write_text(skip_if_unchanged=True) uses ETag to detect duplicates."""
        node = storage_with_versioning.node('s3:config.txt')

        # First write
        changed = node.write_text('config=value1', skip_if_unchanged=True)
        assert changed is True

        # Same content - skip
        changed = node.write_text('config=value1', skip_if_unchanged=True)
        assert changed is False

        # Different content - write
        changed = node.write_text('config=value2', skip_if_unchanged=True)
        assert changed is True

    def test_compact_versions_removes_consecutive_duplicates(self, storage_with_versioning):
        """compact_versions() removes consecutive duplicate versions."""
        node = storage_with_versioning.node('s3:file.txt')

        # Create version history with duplicates
        node.write_text('content A')  # v1
        node.write_text('content A')  # v2 - duplicate of v1
        node.write_text('content B')  # v3
        node.write_text('content B')  # v4 - duplicate of v3
        node.write_text('content A')  # v5 - not consecutive to v1, keep!

        assert node.version_count == 5

        # Compact - should remove v2 and v4
        removed = node.compact_versions()
        assert removed == 2

        # Should have 3 versions left: v1, v3, v5
        assert node.version_count == 3

        # Verify content progression
        versions = node.versions
        with node.open(version=-3) as f:  # Oldest remaining
            assert f.read() == 'content A'
        with node.open(version=-2) as f:  # Middle
            assert f.read() == 'content B'
        with node.open(version=-1) as f:  # Latest
            assert f.read() == 'content A'

    def test_compact_versions_dry_run(self, storage_with_versioning):
        """compact_versions(dry_run=True) reports without deleting."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('A')
        node.write_text('A')  # duplicate
        node.write_text('B')
        node.write_text('B')  # duplicate

        # Dry run
        would_remove = node.compact_versions(dry_run=True)
        assert would_remove == 2

        # Nothing actually deleted
        assert node.version_count == 4

    def test_compact_versions_no_duplicates(self, storage_with_versioning):
        """compact_versions() with no duplicates removes nothing."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('A')
        node.write_text('B')
        node.write_text('C')

        removed = node.compact_versions()
        assert removed == 0
        assert node.version_count == 3

    def test_open_with_as_of_datetime(self, storage_with_versioning):
        """open() with as_of parameter accesses version at specific time."""
        from datetime import timedelta

        node = storage_with_versioning.node('s3:timebased.txt')

        # Create first version
        node.write_text('past content')

        # Get the timestamp from S3 for the first version
        versions = node.versions
        first_version_time = versions[0]['last_modified']

        # Wait to ensure timestamp separation
        time.sleep(1)

        # Create newer version
        node.write_text('current content')

        # Use a time slightly after the first version but before the second
        query_time = first_version_time + timedelta(seconds=0.5)

        # Read version as it was at that time
        with node.open(as_of=query_time) as f:
            content = f.read()
            assert content == 'past content'

        # Read current version
        with node.open() as f:
            content = f.read()
            assert content == 'current content'

    def test_version_info_includes_etag(self, storage_with_versioning):
        """Version info includes ETag for content comparison."""
        node = storage_with_versioning.node('s3:file.txt')

        node.write_text('content')

        versions = node.versions
        assert len(versions) == 1

        version_info = versions[0]
        assert 'etag' in version_info
        assert version_info['etag']  # Not empty
        assert isinstance(version_info['etag'], str)


class TestS3VersioningEdgeCases:
    """Edge case tests for S3 versioning."""

    def test_restore_single_version_by_reading_and_writing(self, storage_with_versioning):
        """Reading and writing single-version file duplicates that version."""
        node = storage_with_versioning.node('s3:single.txt')

        node.write_text('only version')
        assert node.version_count == 1

        # Restore by reading from snapshot and writing - restores same content
        snapshot = storage_with_versioning.node('s3:single.txt', version=-1)
        node.write_text(snapshot.read_text())

        # Should have 2 identical versions now
        assert node.version_count == 2
        assert node.read_text() == 'only version'

    def test_compact_versions_preserves_non_consecutive(self, storage_with_versioning):
        """compact_versions() keeps non-consecutive duplicates."""
        node = storage_with_versioning.node('s3:file.txt')

        # Create pattern: A, A, B, A (last A is non-consecutive)
        node.write_text('A')  # v1
        node.write_text('A')  # v2 - consecutive duplicate, remove
        node.write_text('B')  # v3
        node.write_text('A')  # v4 - non-consecutive to v1, KEEP

        removed = node.compact_versions()
        assert removed == 1  # Only v2 removed

        # v1, v3, v4 should remain
        assert node.version_count == 3

    def test_versions_sorted_by_time(self, storage_with_versioning):
        """versions list is sorted by modification time."""
        node = storage_with_versioning.node('s3:file.txt')

        # Create versions with delays
        node.write_text('v1')
        time.sleep(0.1)
        node.write_text('v2')
        time.sleep(0.1)
        node.write_text('v3')

        versions = node.versions

        # Should be sorted oldest to newest
        for i in range(len(versions) - 1):
            assert versions[i]['last_modified'] <= versions[i + 1]['last_modified']


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])
