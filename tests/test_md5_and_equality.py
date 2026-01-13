"""Tests for MD5 hash and node equality operators."""

import pytest
from genro_storage import StorageManager


class TestMD5Hash:
    """Test MD5 hash computation and retrieval."""

    def test_md5hash_local_file(self, storage_manager, tmp_path):
        """Test MD5 hash computation for local file."""
        # Configure local storage
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        # Create test file with known content
        test_content = b"Hello, World!"
        expected_md5 = "65a8e27d8879283831b664bd8b7f0ad4"  # Pre-computed

        node = storage_manager.node("local:test.txt")
        node.write(test_content, mode="wb")

        # Get hash
        hash_value = node.md5hash()

        assert hash_value == expected_md5
        assert len(hash_value) == 32  # MD5 is 32 hex chars
        assert hash_value.islower()  # Should be lowercase

    def test_md5hash_s3_from_etag(self, storage_manager, s3_fs):
        """Test MD5 hash retrieval from S3 ETag."""
        # Configure S3 storage
        storage_manager.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3",
                    "bucket": "test-bucket",
                    "key": "minioadmin",
                    "secret": "minioadmin",
                    "endpoint_url": "http://localhost:9000",
                }
            ]
        )

        # Create test file
        test_content = b"S3 test content for MD5"
        expected_md5 = "c5b5e0e0e0f5d5e5c5b5e0e0e0f5d5e5"  # Will be computed by S3

        node = storage_manager.node("s3:test-bucket/md5test.txt")
        node.write(test_content, mode="wb")

        # Get hash - should use ETag from S3, not compute
        hash_value = node.md5hash()

        assert hash_value is not None
        assert len(hash_value) == 32
        assert hash_value.islower()

        # Verify it matches content
        import hashlib

        computed_md5 = hashlib.md5(test_content).hexdigest()
        assert hash_value == computed_md5

    def test_md5hash_nonexistent_file(self, storage_manager, tmp_path):
        """Test MD5 hash on non-existent file raises error."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node = storage_manager.node("local:nonexistent.txt")

        with pytest.raises(FileNotFoundError):
            _ = node.md5hash()

    def test_md5hash_directory_raises_error(self, storage_manager, tmp_path):
        """Test MD5 hash on directory raises error."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        # Create directory
        node = storage_manager.node("local:testdir")
        node.mkdir()

        with pytest.raises(ValueError, match="Cannot compute hash of directory"):
            _ = node.md5hash()

    def test_md5hash_large_file(self, storage_manager, tmp_path):
        """Test MD5 hash on large file (tests block reading)."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        # Create 1MB file
        large_content = b"x" * (1024 * 1024)

        node = storage_manager.node("local:large.bin")
        node.write(large_content, mode="wb")

        # Compute hash
        hash_value = node.md5hash()

        # Verify
        import hashlib

        expected = hashlib.md5(large_content).hexdigest()
        assert hash_value == expected

    def test_md5hash_empty_file(self, storage_manager, tmp_path):
        """Test MD5 hash of empty file."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node = storage_manager.node("local:empty.txt")
        node.write(b"", mode="wb")

        # MD5 of empty string
        expected = "d41d8cd98f00b204e9800998ecf8427e"

        assert node.md5hash() == expected


class TestNodeEquality:
    """Test node equality operators (== and !=)."""

    def test_equality_same_content(self, storage_manager, tmp_path):
        """Test two files with same content are equal."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        content = b"Same content"

        node1 = storage_manager.node("local:file1.txt")
        node1.write(content, mode="wb")

        node2 = storage_manager.node("local:file2.txt")
        node2.write(content, mode="wb")

        assert node1 == node2
        assert not (node1 != node2)

    def test_inequality_different_content(self, storage_manager, tmp_path):
        """Test two files with different content are not equal."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node1 = storage_manager.node("local:file1.txt")
        node1.write(b"Content A", mode="wb")

        node2 = storage_manager.node("local:file2.txt")
        node2.write(b"Content B", mode="wb")

        assert node1 != node2
        assert not (node1 == node2)

    def test_equality_same_path(self, storage_manager, tmp_path):
        """Test node equals itself (same path)."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node1 = storage_manager.node("local:file.txt")
        node1.write(b"Content", mode="wb")

        node2 = storage_manager.node("local:file.txt")

        assert node1 == node2
        assert node1.fullpath == node2.fullpath

    def test_equality_across_backends(self, storage_manager, tmp_path):
        """Test equality works across different storage backends."""
        # Setup two different storages
        local_path = tmp_path / "local"
        backup_path = tmp_path / "backup"
        local_path.mkdir()
        backup_path.mkdir()

        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(local_path)}])
        storage_manager.configure([{"name": "backup", "protocol": "local", "path": str(backup_path)}])

        content = b"Cross-backend content"

        node1 = storage_manager.node("local:file.txt")
        node1.write(content, mode="wb")

        node2 = storage_manager.node("backup:file.txt")
        node2.write(content, mode="wb")

        assert node1 == node2

    def test_equality_s3_to_local(self, storage_manager, tmp_path, s3_fs):
        """Test equality between S3 and local file with same content."""
        # Configure both storages
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])
        storage_manager.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3",
                    "bucket": "test-bucket",
                    "key": "minioadmin",
                    "secret": "minioadmin",
                    "endpoint_url": "http://localhost:9000",
                }
            ]
        )

        content = b"S3 and local same content"

        local_node = storage_manager.node("local:file.txt")
        local_node.write(content, mode="wb")

        s3_node = storage_manager.node("s3:test-bucket/file.txt")
        s3_node.write(content, mode="wb")

        # Should be equal (one uses computed MD5, one uses ETag)
        assert local_node == s3_node

    def test_inequality_with_non_storagenode(self, storage_manager, tmp_path):
        """Test comparison with non-StorageNode returns NotImplemented."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node = storage_manager.node("local:file.txt")
        node.write(b"Content", mode="wb")

        # Comparing with string should not raise, but return False
        assert (node == "local:file.txt") is False
        assert (node != "local:file.txt") is True

        # Comparing with None
        assert (node == None) is False
        assert (node != None) is True

    def test_equality_nonexistent_files(self, storage_manager, tmp_path):
        """Test equality of non-existent files returns False."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node1 = storage_manager.node("local:missing1.txt")
        node2 = storage_manager.node("local:missing2.txt")

        # Non-existent files are not equal
        assert not (node1 == node2)
        assert node1 != node2

    def test_equality_directory_returns_false(self, storage_manager, tmp_path):
        """Test directories are never equal (can't compare content)."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        dir1 = storage_manager.node("local:dir1")
        dir1.mkdir()

        dir2 = storage_manager.node("local:dir2")
        dir2.mkdir()

        # Directories can't be compared by content
        assert not (dir1 == dir2)
        assert dir1 != dir2

    def test_equality_file_to_directory(self, storage_manager, tmp_path):
        """Test file vs directory comparison returns False."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        file_node = storage_manager.node("local:file.txt")
        file_node.write(b"Content", mode="wb")

        dir_node = storage_manager.node("local:dir")
        dir_node.mkdir()

        assert not (file_node == dir_node)
        assert file_node != dir_node


class TestMD5Performance:
    """Test MD5 hash performance and caching behavior."""

    def test_s3_hash_uses_etag_not_download(self, storage_manager, s3_fs):
        """Verify S3 uses ETag metadata, not file download."""
        storage_manager.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3",
                    "bucket": "test-bucket",
                    "key": "minioadmin",
                    "secret": "minioadmin",
                    "endpoint_url": "http://localhost:9000",
                }
            ]
        )

        # Create large file
        large_content = b"x" * (10 * 1024 * 1024)  # 10MB

        node = storage_manager.node("s3:test-bucket/large.bin")
        node.write(large_content, mode="wb")

        # Getting hash should be fast (uses ETag, no download)
        import time

        start = time.time()
        hash_value = node.md5hash()
        duration = time.time() - start

        # Should be very fast (< 1 second) since it uses metadata
        # If it downloaded, would take much longer
        assert duration < 1.0
        assert hash_value is not None

    def test_multiple_hash_calls_consistent(self, storage_manager, tmp_path):
        """Test multiple calls to md5hash return same value."""
        storage_manager.configure([{"name": "local", "protocol": "local", "path": str(tmp_path)}])

        node = storage_manager.node("local:file.txt")
        node.write(b"Test content", mode="wb")

        hash1 = node.md5hash()
        hash2 = node.md5hash()
        hash3 = node.md5hash()

        assert hash1 == hash2 == hash3
