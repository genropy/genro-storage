"""Tests for HTTP backend."""

import pytest
import tempfile
import threading
import http.server
import socketserver
from pathlib import Path
import time

from genro_storage import StorageManager, StorageConfigError


# Simple HTTP server for testing
class TestHTTPServer:
    """Context manager for test HTTP server."""

    def __init__(self, port=0):
        """Initialize test HTTP server.

        Args:
            port: Port number to use. If 0, uses a random available port.
        """
        self.port = port
        self.tmpdir = None
        self.httpd = None
        self.thread = None

    def __enter__(self):
        # Create temp directory with test files
        self.tmpdir = tempfile.mkdtemp()
        test_file = Path(self.tmpdir) / 'test.txt'
        test_file.write_text('Hello HTTP!')

        # Start HTTP server
        Handler = http.server.SimpleHTTPRequestHandler
        self.httpd = socketserver.TCPServer(("", self.port), Handler)

        # Get the actual port assigned (if port was 0, it gets a random port)
        self.port = self.httpd.server_address[1]

        # Change to temp dir so server serves those files
        import os
        self.original_dir = os.getcwd()
        os.chdir(self.tmpdir)

        # Run server in thread
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

        # Give server time to start
        time.sleep(0.5)

        return f'http://localhost:{self.port}'

    def __exit__(self, *args):
        import os
        import shutil

        if self.httpd:
            self.httpd.shutdown()
        if self.original_dir:
            os.chdir(self.original_dir)
        if self.tmpdir:
            shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestHTTPBackend:
    """Tests for HTTP backend."""

    @pytest.mark.integration
    def test_http_configuration_basic(self):
        """Test basic HTTP configuration."""
        storage = StorageManager()
        storage.configure([{
            'name': 'http_test',
            'type': 'http',
            'base_url': 'http://example.com'
        }])

        assert 'http_test' in storage._mounts

    def test_http_configuration_missing_base_url(self):
        """Test HTTP configuration with missing base_url raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'base_url'"):
            storage.configure([{
                'name': 'http_test',
                'type': 'http'
            }])

    @pytest.mark.integration
    def test_http_read_file(self):
        """Test reading file from HTTP server."""
        with TestHTTPServer() as base_url:
            storage = StorageManager()
            storage.configure([{
                'name': 'http_test',
                'type': 'http',
                'base_url': base_url
            }])

            node = storage.node('http_test:test.txt')
            content = node.read(mode='r')
            assert content == 'Hello HTTP!'

    @pytest.mark.integration
    def test_http_capabilities(self):
        """Test HTTP backend capabilities."""
        storage = StorageManager()
        storage.configure([{
            'name': 'http_test',
            'type': 'http',
            'base_url': 'http://example.com'
        }])

        backend = storage._mounts['http_test']
        caps = backend.capabilities

        # HTTP is read-only
        assert caps.read is True
        assert caps.write is False
        assert caps.delete is False
        assert caps.mkdir is False
        assert caps.readonly is True
