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
            storage.configure([
                {'name': 'local', 'type': 'local', 'path': tmpdir, 'permissions': 'readonly'}
            ])

            node = storage.node('local:test.txt')

            # Write operations should fail
            with pytest.raises(StoragePermissionError):
                node.write('content')

    def test_local_readwrite_permission(self):
        """Local backend with readwrite permission allows write but blocks delete."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([
                {'name': 'local', 'type': 'local', 'path': tmpdir, 'permissions': 'readwrite'}
            ])

            # Write should work
            node = storage.node('local:test.txt')
            node.write('content')
            assert node.read() == 'content'

            # Delete should fail
            with pytest.raises(StoragePermissionError):
                node.delete()

    def test_local_delete_permission(self):
        """Local backend with delete permission allows all operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([
                {'name': 'local', 'type': 'local', 'path': tmpdir, 'permissions': 'delete'}
            ])

            # All operations should work
            node = storage.node('local:test.txt')
            node.write('content')
            assert node.read() == 'content'
            node.delete()
            assert not node.exists

    def test_local_default_no_permission(self):
        """Local backend without permission field has full access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([
                {'name': 'local', 'type': 'local', 'path': tmpdir}
                # No permissions field - should have full access
            ])

            # All operations should work
            node = storage.node('local:test.txt')
            node.write('content')
            assert node.read() == 'content'
            node.delete()
            assert not node.exists


class TestMemoryBackendPermissions:
    """Test permissions on memory backend."""

    def test_memory_readonly_permission(self):
        """Memory backend with readonly permission blocks writes."""
        storage = StorageManager()
        storage.configure([
            {'name': 'mem', 'type': 'memory', 'permissions': 'readonly'}
        ])

        node = storage.node('mem:test.txt')

        with pytest.raises(StoragePermissionError):
            node.write('content')

    def test_memory_readwrite_permission(self):
        """Memory backend with readwrite permission allows write but blocks delete."""
        storage = StorageManager()
        # First configure without permission to write data
        storage.configure([
            {'name': 'mem', 'type': 'memory'}
        ])
        storage.node('mem:test.txt').write('content')

        # Reconfigure with readwrite permission
        storage.configure([
            {'name': 'mem', 'type': 'memory', 'permissions': 'readwrite'}
        ])

        node = storage.node('mem:test.txt')
        # Write should work
        node.write('modified')
        assert node.read() == 'modified'

        # Delete should fail
        with pytest.raises(StoragePermissionError):
            node.delete()

    def test_memory_delete_permission(self):
        """Memory backend with delete permission allows all operations."""
        storage = StorageManager()
        storage.configure([
            {'name': 'mem', 'type': 'memory', 'permissions': 'delete'}
        ])

        node = storage.node('mem:test.txt')
        node.write('content')
        assert node.read() == 'content'
        node.delete()
        assert not node.exists


@pytest.mark.integration
class TestS3BackendPermissions:
    """Test permissions on S3 backend (using MinIO)."""

    def test_s3_readonly_permission(self, minio_bucket, minio_config, storage_manager):
        """S3 backend with readonly permission blocks writes."""
        # First write data without permission restriction
        storage_manager.configure([{
            'name': 's3_temp',
            'type': 's3',
            'bucket': minio_bucket,
            'endpoint_url': minio_config['endpoint_url'],
            'key': minio_config['aws_access_key_id'],
            'secret': minio_config['aws_secret_access_key']
        }])
        storage_manager.node('s3_temp:test.txt').write('content')

        # Reconfigure with readonly permission
        storage_manager.configure([{
            'name': 's3',
            'type': 's3',
            'bucket': minio_bucket,
            'endpoint_url': minio_config['endpoint_url'],
            'key': minio_config['aws_access_key_id'],
            'secret': minio_config['aws_secret_access_key'],
            'permissions': 'readonly'
        }])

        node = storage_manager.node('s3:test.txt')
        assert node.read() == 'content'

        # Write should fail
        with pytest.raises(StoragePermissionError):
            node.write('new content')

    def test_s3_readwrite_permission(self, minio_bucket, minio_config, storage_manager):
        """S3 backend with readwrite permission allows write but blocks delete."""
        storage_manager.configure([{
            'name': 's3',
            'type': 's3',
            'bucket': minio_bucket,
            'endpoint_url': minio_config['endpoint_url'],
            'key': minio_config['aws_access_key_id'],
            'secret': minio_config['aws_secret_access_key'],
            'permissions': 'readwrite'
        }])

        node = storage_manager.node('s3:test.txt')
        node.write('content')
        assert node.read() == 'content'

        # Delete should fail
        with pytest.raises(StoragePermissionError):
            node.delete()

    def test_s3_delete_permission(self, minio_bucket, minio_config, storage_manager):
        """S3 backend with delete permission allows all operations."""
        storage_manager.configure([{
            'name': 's3',
            'type': 's3',
            'bucket': minio_bucket,
            'endpoint_url': minio_config['endpoint_url'],
            'key': minio_config['aws_access_key_id'],
            'secret': minio_config['aws_secret_access_key'],
            'permissions': 'delete'
        }])

        node = storage_manager.node('s3:test.txt')
        node.write('content')
        assert node.read() == 'content'
        node.delete()
        assert not node.exists


class TestReadOnlyBackendValidation:
    """Test validation when configuring permissions on read-only backends."""

    def test_http_readonly_is_ok(self):
        """HTTP backend can be configured with readonly permission."""
        storage = StorageManager()
        # This should succeed
        storage.configure([{
            'name': 'http',
            'type': 'http',
            'base_url': 'http://example.com',
            'permissions': 'readonly'
        }])

        # Verify mount exists
        assert 'http' in storage._mounts

    def test_http_readwrite_fails(self):
        """HTTP backend cannot be configured with readwrite permission."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="read-only"):
            storage.configure([{
                'name': 'http',
                'type': 'http',
                'base_url': 'http://example.com',
                'permissions': 'readwrite'
            }])

    def test_http_delete_fails(self):
        """HTTP backend cannot be configured with delete permission."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="read-only"):
            storage.configure([{
                'name': 'http',
                'type': 'http',
                'base_url': 'http://example.com',
                'permissions': 'delete'
            }])


class TestInvalidPermissions:
    """Test validation of permission values."""

    def test_invalid_permission_value(self):
        """Invalid permission value raises error."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="Invalid permissions"):
            storage.configure([{
                'name': 'local',
                'type': 'memory',
                'permissions': 'invalid_value'
            }])


class TestPermissionMixedOperations:
    """Test permission enforcement on various operations."""

    def test_readonly_blocks_mkdir(self):
        """Readonly permission blocks directory creation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([
                {'name': 'local', 'type': 'local', 'path': tmpdir, 'permissions': 'readonly'}
            ])

            node = storage.node('local:subdir/file.txt')

            # Writing to nested path (requires mkdir) should fail
            with pytest.raises(StoragePermissionError):
                node.write('content')

    def test_readonly_blocks_copy_as_destination(self):
        """Readonly permission blocks copy to that mount."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([
                {'name': 'source', 'type': 'memory'},
                {'name': 'dest', 'type': 'local', 'path': tmpdir, 'permissions': 'readonly'}
            ])

            # Create source file
            source = storage.node('source:file.txt')
            source.write('content')

            # Copy to readonly destination should fail
            dest = storage.node('dest:file.txt')
            with pytest.raises(StoragePermissionError):
                source.copy_to(dest)

    def test_readwrite_allows_copy(self):
        """Readwrite permission allows copy operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([
                {'name': 'source', 'type': 'memory'},
                {'name': 'dest', 'type': 'local', 'path': tmpdir, 'permissions': 'readwrite'}
            ])

            source = storage.node('source:file.txt')
            source.write('content')

            dest = storage.node('dest:file.txt')
            source.copy_to(dest)

            assert dest.read() == 'content'

    def test_readonly_blocks_open_write_mode(self):
        """Readonly permission blocks open() in write mode."""
        storage = StorageManager()
        storage.configure([
            {'name': 'mem', 'type': 'memory', 'permissions': 'readonly'}
        ])

        node = storage.node('mem:file.txt')

        with pytest.raises(StoragePermissionError):
            with node.open('w') as f:
                f.write('content')

    def test_readonly_allows_open_read_mode(self):
        """Readonly permission allows open() in read mode."""
        storage = StorageManager()
        # First create file without restrictions
        storage.configure([{'name': 'mem', 'type': 'memory'}])
        storage.node('mem:file.txt').write('content')

        # Reconfigure with readonly
        storage.configure([
            {'name': 'mem', 'type': 'memory', 'permissions': 'readonly'}
        ])

        node = storage.node('mem:file.txt')

        # Read mode should work
        with node.open('r') as f:
            assert f.read() == 'content'
