"""Tests for native permission support on all backend types."""

import pytest
import tempfile

from genro_storage import StorageManager
from genro_storage.exceptions import StorageConfigError, StoragePermissionError


class TestLocalBackendPermissions:
    """Test permissions on local filesystem backend."""

    def test_local_readonly_permission(self):
        """Local backend with readonly permission blocks writes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [{"name": "local", "protocol": "local", "path": tmpdir, "permissions": "readonly"}]
            )

            node = storage.node("local:test.txt")

            # Write operations should fail
            with pytest.raises(StoragePermissionError):
                node.write("content")

    def test_local_readwrite_permission(self):
        """Local backend with readwrite permission allows write but blocks delete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [{"name": "local", "protocol": "local", "path": tmpdir, "permissions": "readwrite"}]
            )

            # Write should work
            node = storage.node("local:test.txt")
            node.write("content")
            assert node.read() == "content"

            # Delete should fail
            with pytest.raises(StoragePermissionError):
                node.delete()

    def test_local_delete_permission(self):
        """Local backend with delete permission allows all operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [{"name": "local", "protocol": "local", "path": tmpdir, "permissions": "delete"}]
            )

            # All operations should work
            node = storage.node("local:test.txt")
            node.write("content")
            assert node.read() == "content"
            node.delete()
            assert not node.exists()

    def test_local_default_no_permission(self):
        """Local backend without permission field has full access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "local", "protocol": "local", "path": tmpdir}
                    # No permissions field - should have full access
                ]
            )

            # All operations should work
            node = storage.node("local:test.txt")
            node.write("content")
            assert node.read() == "content"
            node.delete()
            assert not node.exists()


class TestMemoryBackendPermissions:
    """Test permissions on memory backend."""

    def test_memory_readonly_permission(self):
        """Memory backend with readonly permission blocks writes."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory", "permissions": "readonly"}])

        node = storage.node("mem:test.txt")

        with pytest.raises(StoragePermissionError):
            node.write("content")

    def test_memory_readwrite_permission(self):
        """Memory backend with readwrite permission allows write but blocks delete."""
        storage = StorageManager()
        # First configure without permission to write data
        storage.configure([{"name": "mem", "protocol": "memory"}])
        storage.node("mem:test.txt").write("content")

        # Reconfigure with readwrite permission
        storage.configure([{"name": "mem", "protocol": "memory", "permissions": "readwrite"}])

        node = storage.node("mem:test.txt")
        # Write should work
        node.write("modified")
        assert node.read() == "modified"

        # Delete should fail
        with pytest.raises(StoragePermissionError):
            node.delete()

    def test_memory_delete_permission(self):
        """Memory backend with delete permission allows all operations."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory", "permissions": "delete"}])

        node = storage.node("mem:test.txt")
        node.write("content")
        assert node.read() == "content"
        node.delete()
        assert not node.exists()


@pytest.mark.integration
class TestS3BackendPermissions:
    """Test permissions on S3 backend (using MinIO)."""

    def test_s3_readonly_permission(self, minio_bucket, minio_config, storage_manager):
        """S3 backend with readonly permission blocks writes."""
        # First write data without permission restriction
        storage_manager.configure(
            [
                {
                    "name": "s3_temp",
                    "protocol": "s3",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                }
            ]
        )
        storage_manager.node("s3_temp:test.txt").write("content")

        # Reconfigure with readonly permission
        storage_manager.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                    "permissions": "readonly",
                }
            ]
        )

        node = storage_manager.node("s3:test.txt")
        assert node.read() == "content"

        # Write should fail
        with pytest.raises(StoragePermissionError):
            node.write("new content")

    def test_s3_readwrite_permission(self, minio_bucket, minio_config, storage_manager):
        """S3 backend with readwrite permission allows write but blocks delete."""
        storage_manager.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                    "permissions": "readwrite",
                }
            ]
        )

        node = storage_manager.node("s3:test.txt")
        node.write("content")
        assert node.read() == "content"

        # Delete should fail
        with pytest.raises(StoragePermissionError):
            node.delete()

    def test_s3_delete_permission(self, minio_bucket, minio_config, storage_manager):
        """S3 backend with delete permission allows all operations."""
        storage_manager.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                    "permissions": "delete",
                }
            ]
        )

        node = storage_manager.node("s3:test.txt")
        node.write("content")
        assert node.read() == "content"
        node.delete()
        assert not node.exists()


class TestReadOnlyBackendValidation:
    """Test validation when configuring permissions on read-only backends."""

    def test_http_readonly_is_ok(self):
        """HTTP backend can be configured with readonly permission."""
        storage = StorageManager()
        # This should succeed
        storage.configure(
            [
                {
                    "name": "http",
                    "protocol": "http",
                    "base_url": "http://example.com",
                    "permissions": "readonly",
                }
            ]
        )

        # Verify mount exists
        assert "http" in storage._mounts

    def test_http_readwrite_fails(self):
        """HTTP backend cannot be configured with readwrite permission."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="read-only"):
            storage.configure(
                [
                    {
                        "name": "http",
                        "protocol": "http",
                        "base_url": "http://example.com",
                        "permissions": "readwrite",
                    }
                ]
            )

    def test_http_delete_fails(self):
        """HTTP backend cannot be configured with delete permission."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="read-only"):
            storage.configure(
                [
                    {
                        "name": "http",
                        "protocol": "http",
                        "base_url": "http://example.com",
                        "permissions": "delete",
                    }
                ]
            )


class TestInvalidPermissions:
    """Test validation of permission values."""

    def test_invalid_permission_value(self):
        """Invalid permission value raises error."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="Invalid permissions"):
            storage.configure([{"name": "local", "protocol": "memory", "permissions": "invalid_value"}])


class TestPermissionMixedOperations:
    """Test permission enforcement on various operations."""

    def test_readonly_blocks_mkdir(self):
        """Readonly permission blocks directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [{"name": "local", "protocol": "local", "path": tmpdir, "permissions": "readonly"}]
            )

            node = storage.node("local:subdir/file.txt")

            # Writing to nested path (requires mkdir) should fail
            with pytest.raises(StoragePermissionError):
                node.write("content")

    def test_readonly_blocks_copy_as_destination(self):
        """Readonly permission blocks copy to that mount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "source", "protocol": "memory"},
                    {"name": "dest", "protocol": "local", "path": tmpdir, "permissions": "readonly"},
                ]
            )

            # Create source file
            source = storage.node("source:file.txt")
            source.write("content")

            # Copy to readonly destination should fail
            dest = storage.node("dest:file.txt")
            with pytest.raises(StoragePermissionError):
                source.copy_to(dest)

    def test_readwrite_allows_copy(self):
        """Readwrite permission allows copy operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "source", "protocol": "memory"},
                    {"name": "dest", "protocol": "local", "path": tmpdir, "permissions": "readwrite"},
                ]
            )

            source = storage.node("source:file.txt")
            source.write("content")

            dest = storage.node("dest:file.txt")
            source.copy_to(dest)

            assert dest.read() == "content"

    def test_readonly_blocks_open_write_mode(self):
        """Readonly permission blocks open() in write mode."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory", "permissions": "readonly"}])

        node = storage.node("mem:file.txt")

        with pytest.raises(StoragePermissionError):
            with node.open("w") as f:
                f.write("content")

    def test_readonly_allows_open_read_mode(self):
        """Readonly permission allows open() in read mode."""
        storage = StorageManager()
        # First create file without restrictions
        storage.configure([{"name": "mem", "protocol": "memory"}])
        storage.node("mem:file.txt").write("content")

        # Reconfigure with readonly
        storage.configure([{"name": "mem", "protocol": "memory", "permissions": "readonly"}])

        node = storage.node("mem:file.txt")

        # Read mode should work
        with node.open("r") as f:
            assert f.read() == "content"


class TestRelativeBackendCompleteCoverage:
    """Test all RelativeMountBackend methods to ensure complete coverage."""

    def test_is_file_and_is_dir(self):
        """Test is_file() and is_dir() methods."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "data", "protocol": "local", "path": tmpdir},
                    {"name": "readonly", "path": "data:subdir", "permissions": "readonly"},
                ]
            )

            # Create file and directory
            storage.node("data:subdir/file.txt").write("content")
            storage.node("data:subdir/folder/test.txt").write("test")

            # Test via backend directly
            backend = storage._mounts["readonly"]
            assert backend.is_file("file.txt") is True
            assert backend.is_dir("file.txt") is False
            assert backend.is_dir("folder") is True
            assert backend.is_file("folder") is False

    def test_mtime(self):
        """Test mtime() method."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "data", "protocol": "local", "path": tmpdir},
                    {"name": "readonly", "path": "data:subdir", "permissions": "readonly"},
                ]
            )

            storage.node("data:subdir/file.txt").write("content")

            backend = storage._mounts["readonly"]
            mtime = backend.mtime("file.txt")
            assert isinstance(mtime, float)
            assert mtime > 0

    def test_write_text_direct(self):
        """Test write_text() method directly on backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "data", "protocol": "local", "path": tmpdir},
                    {"name": "readonly", "path": "data:subdir", "permissions": "readonly"},
                    {"name": "readwrite", "path": "data:subdir2", "permissions": "readwrite"},
                ]
            )

            # Readonly backend should block write_text
            backend_ro = storage._mounts["readonly"]
            with pytest.raises(StoragePermissionError):
                backend_ro.write_text("file.txt", "content")

            # Readwrite backend should allow write_text
            backend_rw = storage._mounts["readwrite"]
            backend_rw.write_text("file.txt", "content", encoding="utf-8")
            assert backend_rw.read_text("file.txt") == "content"

    def test_mkdir_direct(self):
        """Test mkdir() method directly on backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "data", "protocol": "local", "path": tmpdir},
                    {"name": "readonly", "path": "data:subdir", "permissions": "readonly"},
                    {"name": "readwrite", "path": "data:subdir2", "permissions": "readwrite"},
                ]
            )

            # Readonly should block mkdir
            backend_ro = storage._mounts["readonly"]
            with pytest.raises(StoragePermissionError):
                backend_ro.mkdir("newdir", parents=True, exist_ok=False)

            # Readwrite should allow mkdir
            backend_rw = storage._mounts["readwrite"]
            backend_rw.mkdir("newdir", parents=True, exist_ok=True)
            assert backend_rw.is_dir("newdir")

    def test_get_hash(self):
        """Test get_hash() method."""
        storage = StorageManager()
        storage.configure(
            [
                {"name": "mem", "protocol": "memory"},
                {"name": "readonly", "path": "mem:data", "permissions": "readonly"},
            ]
        )

        storage.node("mem:data/file.txt").write("content")

        backend = storage._mounts["readonly"]
        # Most backends return None for get_hash (only S3 has ETag)
        hash_result = backend.get_hash("file.txt")
        assert hash_result is None or isinstance(hash_result, str)

    @pytest.mark.integration
    @pytest.mark.skip(reason="S3 set_metadata has implementation bug in fsspec backend")
    def test_metadata_methods(self, minio_bucket, minio_config, storage_manager):
        """Test get_metadata() and set_metadata() methods."""
        storage_manager.configure(
            [
                {
                    "name": "s3_parent",
                    "protocol": "s3",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                }
            ]
        )

        storage_manager.node("s3_parent:test.txt").write("content")

        # Configure relative mount with readwrite
        storage_manager.configure(
            [{"name": "s3_rw", "path": "s3_parent:", "permissions": "readwrite"}]
        )

        backend = storage_manager._mounts["s3_rw"]

        # set_metadata should work with readwrite
        backend.set_metadata("test.txt", {"key": "value"})

        # get_metadata should work (read operation)
        metadata = backend.get_metadata("test.txt")
        assert isinstance(metadata, dict)

        # Readonly should block set_metadata
        storage_manager.configure(
            [{"name": "s3_ro", "path": "s3_parent:", "permissions": "readonly"}]
        )

        backend_ro = storage_manager._mounts["s3_ro"]
        with pytest.raises(StoragePermissionError):
            backend_ro.set_metadata("test.txt", {"key2": "value2"})

    @pytest.mark.integration
    def test_versioning_methods(self, minio_versioned_bucket, minio_config, storage_manager):
        """Test get_versions(), open_version(), and delete_version() methods."""
        storage_manager.configure(
            [
                {
                    "name": "s3_parent",
                    "protocol": "s3",
                    "bucket": minio_versioned_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                }
            ]
        )

        # Create versions
        storage_manager.node("s3_parent:file.txt").write("v1")
        storage_manager.node("s3_parent:file.txt").write("v2")

        # Configure relative mount with readonly
        storage_manager.configure(
            [{"name": "s3_ro", "path": "s3_parent:", "permissions": "readonly"}]
        )

        backend_ro = storage_manager._mounts["s3_ro"]

        # get_versions should work (read operation)
        versions = backend_ro.get_versions("file.txt")
        assert len(versions) >= 2
        assert isinstance(versions[0], dict)
        assert "version_id" in versions[0]

        # open_version should work (read operation)
        first_version_id = versions[0]["version_id"]
        with backend_ro.open_version("file.txt", first_version_id, mode="rb") as f:
            content = f.read()
            assert content == b"v1"

        # delete_version should fail with readonly
        with pytest.raises(StoragePermissionError):
            backend_ro.delete_version("file.txt", first_version_id)

        # delete_version should work with delete permission
        storage_manager.configure(
            [{"name": "s3_delete", "path": "s3_parent:", "permissions": "delete"}]
        )

        backend_del = storage_manager._mounts["s3_delete"]
        # Create a new version to delete
        storage_manager.node("s3_parent:file2.txt").write("v1")
        storage_manager.node("s3_parent:file2.txt").write("v2")
        versions = backend_del.get_versions("file2.txt")
        backend_del.delete_version("file2.txt", versions[0]["version_id"])
        # Verify version was deleted
        versions_after = backend_del.get_versions("file2.txt")
        assert len(versions_after) < len(versions)

    @pytest.mark.integration
    def test_url_generation(self, minio_bucket, minio_config, storage_manager):
        """Test url() and internal_url() methods."""
        storage_manager.configure(
            [
                {
                    "name": "s3_parent",
                    "protocol": "s3",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "key": minio_config["aws_access_key_id"],
                    "secret": minio_config["aws_secret_access_key"],
                }
            ]
        )

        storage_manager.node("s3_parent:test.txt").write("content")

        # Configure relative mount
        storage_manager.configure(
            [{"name": "s3_ro", "path": "s3_parent:", "permissions": "readonly"}]
        )

        backend = storage_manager._mounts["s3_ro"]

        # url() should work (generates presigned URL)
        url = backend.url("test.txt", expires_in=3600)
        # S3 returns a URL string
        assert url is None or isinstance(url, str)

        # internal_url() should work
        internal = backend.internal_url("test.txt", nocache=False)
        assert internal is None or isinstance(internal, str)

    def test_local_path_with_write_mode(self):
        """Test local_path() with write mode blocks on readonly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure(
                [
                    {"name": "data", "protocol": "local", "path": tmpdir},
                    {"name": "readonly", "path": "data:subdir", "permissions": "readonly"},
                ]
            )

            storage.node("data:subdir/file.txt").write("content")

            backend = storage._mounts["readonly"]

            # Read mode should work
            with backend.local_path("file.txt", mode="r") as ctx:
                assert ctx is not None

            # Write mode should fail
            with pytest.raises(StoragePermissionError):
                with backend.local_path("newfile.txt", mode="w") as ctx:
                    pass

    def test_copy_method_direct(self):
        """Test copy() method directly on backend."""
        storage = StorageManager()
        storage.configure(
            [
                {"name": "source", "protocol": "memory"},
                {"name": "dest", "protocol": "memory"},
                {"name": "source_ro", "path": "source:", "permissions": "readonly"},
            ]
        )

        # Create source file
        storage.node("source:file.txt").write("content")

        backend_source = storage._mounts["source_ro"]
        backend_dest = storage._mounts["dest"]

        # Copy should work (source is readonly but reading is allowed)
        result = backend_source.copy("file.txt", backend_dest, "copied.txt")
        # Result can be None or version_id depending on backend
        assert result is None or isinstance(result, str)

        # Verify file was copied
        assert backend_dest.exists("copied.txt")

    def test_close_method(self):
        """Test close() method (should be no-op for relative mounts)."""
        storage = StorageManager()
        storage.configure(
            [
                {"name": "data", "protocol": "memory"},
                {"name": "child", "path": "data:subdir", "permissions": "readonly"},
            ]
        )

        backend = storage._mounts["child"]
        # close() should not raise any errors
        backend.close()

        # Parent should still be usable after child close
        parent_backend = storage._mounts["data"]
        parent_backend.write_bytes("test.txt", b"data")
        assert parent_backend.exists("test.txt")
