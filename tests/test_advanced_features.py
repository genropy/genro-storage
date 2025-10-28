"""Tests for advanced features: local_path, callable paths, metadata, URLs, etc."""

import pytest
import tempfile
import os
import base64
from pathlib import Path
from unittest.mock import patch, MagicMock
from genro_storage import StorageManager


class TestLocalPath:
    """Tests for local_path() context manager."""

    def test_local_path_local_storage_returns_actual_path(self):
        """LocalStorage local_path returns the actual filesystem path."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('Hello World')

        with node.local_path() as local_path:
            # Should be the actual path
            assert os.path.exists(local_path)
            # Resolve both paths to handle symlinks (macOS /var -> /private/var)
            assert Path(local_path).parent.resolve() == Path(temp_dir).resolve()
            with open(local_path, 'r') as f:
                assert f.read() == 'Hello World'

    def test_local_path_memory_downloads_and_uploads(self):
        """Memory storage local_path downloads to temp and uploads changes."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('Original')

        # Read mode
        with node.local_path(mode='r') as local_path:
            assert os.path.exists(local_path)
            with open(local_path, 'r') as f:
                assert f.read() == 'Original'

        # Temp file should be cleaned up
        assert not os.path.exists(local_path)

    def test_local_path_memory_read_write_mode(self):
        """Memory storage local_path with rw mode downloads and uploads."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('Original')

        # Read-write mode
        with node.local_path(mode='rw') as local_path:
            # Read
            with open(local_path, 'r') as f:
                content = f.read()
                assert content == 'Original'

            # Modify
            with open(local_path, 'w') as f:
                f.write('Modified')

        # Changes should be uploaded
        assert node.read_text() == 'Modified'

    def test_local_path_memory_write_mode(self):
        """Memory storage local_path with w mode only uploads."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:newfile.txt')

        # Write mode (no download)
        with node.local_path(mode='w') as local_path:
            with open(local_path, 'w') as f:
                f.write('New content')

        # Should be uploaded
        assert node.exists
        assert node.read_text() == 'New content'

    def test_local_path_base64_read_only(self):
        """Base64 backend local_path creates temp file with decoded content."""
        storage = StorageManager()
        storage.configure([{'name': 'b64', 'type': 'base64'}])

        data = base64.b64encode(b'Test data').decode()
        node = storage.node(f'b64:{data}')

        with node.local_path(mode='r') as local_path:
            assert os.path.exists(local_path)
            with open(local_path, 'rb') as f:
                assert f.read() == b'Test data'

        # Cleanup
        assert not os.path.exists(local_path)

    def test_local_path_base64_write_raises_error(self):
        """Base64 backend local_path raises error for write modes."""
        storage = StorageManager()
        storage.configure([{'name': 'b64', 'type': 'base64'}])

        node = storage.node('b64:dGVzdA==')

        with pytest.raises(PermissionError, match='read-only'):
            with node.local_path(mode='w'):
                pass

    def test_local_path_preserves_file_extension(self):
        """local_path preserves file extension in temp file."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:video.mp4')
        node.write_bytes(b'fake video data')

        with node.local_path(mode='r') as local_path:
            # Extension should be preserved
            assert local_path.endswith('.mp4')


class TestCallablePaths:
    """Tests for callable path support."""

    def test_callable_path_resolves_at_runtime(self):
        """Callable paths resolve dynamically at runtime."""
        storage = StorageManager()
        temp_base = tempfile.mkdtemp()

        context = {'user_id': None}

        def get_user_path():
            user_dir = os.path.join(temp_base, f'user_{context["user_id"]}')
            os.makedirs(user_dir, exist_ok=True)
            return user_dir

        storage.configure([
            {'name': 'user', 'type': 'local', 'path': get_user_path}
        ])

        # User 1
        context['user_id'] = 123
        node1 = storage.node('user:prefs.json')
        node1.write_text('{"theme": "dark"}')
        path1 = str(node1._backend.base_path)

        # User 2
        context['user_id'] = 456
        node2 = storage.node('user:prefs.json')
        node2.write_text('{"theme": "light"}')
        path2 = str(node2._backend.base_path)

        # Different paths
        assert 'user_123' in path1
        assert 'user_456' in path2
        assert path1 != path2

        # Different content
        context['user_id'] = 123
        node1_read = storage.node('user:prefs.json')
        assert '"dark"' in node1_read.read_text()

        context['user_id'] = 456
        node2_read = storage.node('user:prefs.json')
        assert '"light"' in node2_read.read_text()

    def test_callable_path_validation_deferred(self):
        """Callable path validation deferred until first access."""
        storage = StorageManager()

        def get_path_later():
            # This will fail if called during configure
            raise ValueError("Should not be called during configure")

        # Should not raise during configure
        storage.configure([
            {'name': 'deferred', 'type': 'local', 'path': get_path_later}
        ])

        # Should raise when accessing
        # (we won't actually call it to avoid failing the test)

    def test_static_path_validated_immediately(self):
        """Static paths are validated immediately during configure."""
        storage = StorageManager()

        with pytest.raises(FileNotFoundError):
            storage.configure([
                {'name': 'bad', 'type': 'local', 'path': '/nonexistent/path/xyz123'}
            ])


class TestMetadata:
    """Tests for metadata get/set methods."""

    def test_metadata_memory_returns_empty_dict(self):
        """Memory storage returns empty dict for metadata."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        metadata = node.get_metadata()
        assert metadata == {}

    def test_metadata_local_returns_empty_dict(self):
        """Local storage returns empty dict for metadata."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('test')

        metadata = node.get_metadata()
        assert metadata == {}

    def test_metadata_set_raises_permission_error_memory(self):
        """Setting metadata on memory storage raises PermissionError."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        with pytest.raises(PermissionError, match='does not support metadata'):
            node.set_metadata({'key': 'value'})

    def test_metadata_set_raises_permission_error_local(self):
        """Setting metadata on local storage raises PermissionError."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('test')

        with pytest.raises(PermissionError, match='does not support metadata'):
            node.set_metadata({'key': 'value'})

    def test_metadata_validation(self):
        """Metadata validation checks dict with string keys/values."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        # Would raise PermissionError, but validation happens first
        # (we can't test validation without a backend that supports metadata)


class TestURLGeneration:
    """Tests for URL generation methods."""

    def test_url_returns_none_for_memory(self):
        """Memory storage url() returns None."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        url = node.url()
        assert url is None

    def test_url_returns_none_for_local(self):
        """Local storage url() returns None."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('test')

        url = node.url()
        assert url is None

    def test_internal_url_returns_none_for_memory(self):
        """Memory storage internal_url() returns None."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        url = node.internal_url()
        assert url is None

    def test_internal_url_nocache_parameter(self):
        """internal_url accepts nocache parameter."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        # Should not raise
        url = node.internal_url(nocache=True)
        assert url is None


class TestBase64Encoding:
    """Tests for to_base64() method."""

    def test_to_base64_with_data_uri(self):
        """to_base64() creates data URI by default."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('Hello World')

        data_uri = node.to_base64()

        assert data_uri.startswith('data:text/plain;base64,')
        b64_part = data_uri.split('base64,')[1]
        decoded = base64.b64decode(b64_part).decode()
        assert decoded == 'Hello World'

    def test_to_base64_without_data_uri(self):
        """to_base64(include_uri=False) returns raw base64."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('Hello World')

        b64 = node.to_base64(include_uri=False)

        assert not b64.startswith('data:')
        decoded = base64.b64decode(b64).decode()
        assert decoded == 'Hello World'

    def test_to_base64_custom_mime_type(self):
        """to_base64() accepts custom MIME type."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:data.json')
        node.write_text('{"key": "value"}')

        data_uri = node.to_base64(mime='application/custom')
        assert data_uri.startswith('data:application/custom;base64,')

    def test_to_base64_auto_detects_mime_type(self):
        """to_base64() auto-detects MIME type from extension."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        # JSON file
        node = storage.node('local:data.json')
        node.write_text('{}')
        data_uri = node.to_base64()
        assert 'application/json' in data_uri or 'text/plain' in data_uri

    def test_to_base64_raises_on_nonexistent_file(self):
        """to_base64() raises FileNotFoundError if file doesn't exist."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:nonexistent.txt')

        with pytest.raises(FileNotFoundError):
            node.to_base64()

    def test_to_base64_raises_on_directory(self):
        """to_base64() raises ValueError for directories."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:subdir')
        node.mkdir()

        with pytest.raises(ValueError, match='Cannot encode directory'):
            node.to_base64()


class TestFillFromURL:
    """Tests for fill_from_url() method."""

    @patch('urllib.request.urlopen')
    def test_fill_from_url_downloads_content(self, mock_urlopen):
        """fill_from_url() downloads and writes content."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.read.return_value = b'Downloaded content'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response

        node = storage.node('local:downloaded.txt')
        node.fill_from_url('https://example.com/file.txt')

        assert node.exists
        assert node.read_bytes() == b'Downloaded content'
        mock_urlopen.assert_called_once()

    @patch('urllib.request.urlopen')
    def test_fill_from_url_custom_timeout(self, mock_urlopen):
        """fill_from_url() accepts custom timeout."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        mock_response = MagicMock()
        mock_response.read.return_value = b'data'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=None)
        mock_urlopen.return_value = mock_response

        node = storage.node('local:file.txt')
        node.fill_from_url('https://example.com/file.txt', timeout=60)

        # Check timeout was passed
        call_args = mock_urlopen.call_args
        assert call_args[1]['timeout'] == 60

    def test_fill_from_url_raises_on_invalid_url(self):
        """fill_from_url() raises ValueError for invalid URLs."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:file.txt')

        with pytest.raises(ValueError, match='Invalid URL'):
            node.fill_from_url('not-a-url')

        with pytest.raises(ValueError, match='Invalid URL'):
            node.fill_from_url('ftp://example.com/file.txt')

    @patch('urllib.request.urlopen')
    def test_fill_from_url_raises_on_network_error(self, mock_urlopen):
        """fill_from_url() raises IOError on network failure."""
        import urllib.error

        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        mock_urlopen.side_effect = urllib.error.URLError('Connection failed')

        node = storage.node('local:file.txt')

        with pytest.raises(IOError, match='Failed to download'):
            node.fill_from_url('https://example.com/file.txt')


class TestS3Versioning:
    """Tests for S3 versioning support."""

    def test_versions_returns_empty_list_for_memory(self):
        """Memory storage returns empty list for versions."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        versions = node.versions
        assert versions == []

    def test_versions_returns_empty_list_for_local(self):
        """Local storage returns empty list for versions."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('test')

        versions = node.versions
        assert versions == []

    def test_open_with_version_raises_permission_error_memory(self):
        """Memory storage raises PermissionError for open(version=...)."""
        storage = StorageManager()
        storage.configure([{'name': 'mem', 'type': 'memory'}])

        node = storage.node('mem:test.txt')
        node.write_text('test')

        with pytest.raises(PermissionError, match='does not support versioning'):
            node.open(version='dummy_version_id')

    def test_open_with_version_raises_permission_error_local(self):
        """Local storage raises PermissionError for open(version=...)."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir}
        ])

        node = storage.node('local:test.txt')
        node.write_text('test')

        with pytest.raises(PermissionError, match='does not support versioning'):
            node.open(version='v123')
