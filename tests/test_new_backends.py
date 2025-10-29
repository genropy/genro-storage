"""Tests for new backends: SMB, SFTP, ZIP, TAR.

These are basic configuration tests. Full integration tests would require
actual SMB/SFTP servers and are better suited for manual testing or CI
environments with test servers.
"""

import pytest
import tempfile
import zipfile
import tarfile
from pathlib import Path

from genro_storage import StorageManager
from genro_storage.exceptions import StorageConfigError

# Check for optional dependencies
try:
    import smbprotocol
    HAS_SMB = True
except ImportError:
    HAS_SMB = False

try:
    import paramiko
    HAS_SFTP = True
except ImportError:
    HAS_SFTP = False


class TestSMBConfiguration:
    """Test SMB backend configuration."""

    def test_smb_requires_host(self):
        """SMB backend requires 'host' field."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="missing required field: 'host'"):
            storage.configure([{
                'name': 'smb_test',
                'type': 'smb',
                'share': 'documents'
            }])

    def test_smb_requires_share(self):
        """SMB backend requires 'share' field."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="missing required field: 'share'"):
            storage.configure([{
                'name': 'smb_test',
                'type': 'smb',
                'host': '192.168.1.100'
            }])

    @pytest.mark.skipif(not HAS_SMB, reason="smbprotocol not installed")
    def test_smb_configuration_basic(self):
        """Test basic SMB configuration."""
        storage = StorageManager()

        storage.configure([{
            'name': 'smb_test',
            'type': 'smb',
            'host': '192.168.1.100',
            'share': 'documents'
        }])

        assert 'smb_test' in storage._mounts

    @pytest.mark.skipif(not HAS_SMB, reason="smbprotocol not installed")
    def test_smb_configuration_with_auth(self):
        """Test SMB configuration with authentication."""
        storage = StorageManager()

        storage.configure([{
            'name': 'smb_test',
            'type': 'smb',
            'host': 'fileserver.local',
            'share': 'docs',
            'username': 'user',
            'password': 'secret',
            'domain': 'WORKGROUP',
            'port': 445
        }])

        assert 'smb_test' in storage._mounts


class TestSFTPConfiguration:
    """Test SFTP backend configuration."""

    def test_sftp_requires_host(self):
        """SFTP backend requires 'host' field."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="missing required field: 'host'"):
            storage.configure([{
                'name': 'sftp_test',
                'type': 'sftp',
                'username': 'user'
            }])

    def test_sftp_requires_username(self):
        """SFTP backend requires 'username' field."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="missing required field: 'username'"):
            storage.configure([{
                'name': 'sftp_test',
                'type': 'sftp',
                'host': 'server.example.com'
            }])

    @pytest.mark.skipif(not HAS_SFTP, reason="paramiko not installed")
    @pytest.mark.skip(reason="SFTP requires actual server connection")
    def test_sftp_configuration_basic(self):
        """Test basic SFTP configuration."""
        storage = StorageManager()

        storage.configure([{
            'name': 'sftp_test',
            'type': 'sftp',
            'host': 'server.example.com',
            'username': 'user'
        }])

        assert 'sftp_test' in storage._mounts

    @pytest.mark.skipif(not HAS_SFTP, reason="paramiko not installed")
    @pytest.mark.skip(reason="SFTP requires actual server connection")
    def test_sftp_configuration_with_password(self):
        """Test SFTP configuration with password."""
        storage = StorageManager()

        storage.configure([{
            'name': 'sftp_test',
            'type': 'sftp',
            'host': '192.168.1.100',
            'port': 22,
            'username': 'user',
            'password': 'secret'
        }])

        assert 'sftp_test' in storage._mounts

    @pytest.mark.skipif(not HAS_SFTP, reason="paramiko not installed")
    @pytest.mark.skip(reason="SFTP requires actual server connection")
    def test_sftp_configuration_with_key(self):
        """Test SFTP configuration with SSH key."""
        storage = StorageManager()

        storage.configure([{
            'name': 'sftp_test',
            'type': 'sftp',
            'host': 'server.example.com',
            'username': 'deploy',
            'key_filename': '/home/user/.ssh/id_rsa',
            'passphrase': 'keypassword'
        }])

        assert 'sftp_test' in storage._mounts


class TestZIPBackend:
    """Test ZIP archive backend."""

    def test_zip_requires_file(self):
        """ZIP backend requires 'file' field."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="missing required field: 'file'"):
            storage.configure([{
                'name': 'zip_test',
                'type': 'zip'
            }])

    def test_zip_configuration_basic(self):
        """Test basic ZIP configuration."""
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = tmp.name

        try:
            # Create a test ZIP file
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('test.txt', 'Hello ZIP!')

            storage.configure([{
                'name': 'zip_test',
                'type': 'zip',
                'file': zip_path,
                'mode': 'r'
            }])

            assert 'zip_test' in storage._mounts

            # Test reading from ZIP
            node = storage.node('zip_test:test.txt')
            content = node.read(mode='r')
            assert content == 'Hello ZIP!'

        finally:
            Path(zip_path).unlink(missing_ok=True)

    def test_zip_write_mode(self):
        """Test ZIP archive write mode configuration.

        Note: Full write testing requires explicit filesystem closing which
        is not easily accessible through the StorageNode API. This test
        verifies that the configuration is accepted for write mode.
        """
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = tmp.name

        try:
            storage.configure([{
                'name': 'zip_write',
                'type': 'zip',
                'file': zip_path,
                'mode': 'w'
            }])

            assert 'zip_write' in storage._mounts

            # Verify backend is configured with write capabilities
            backend = storage._mounts['zip_write']
            assert backend.capabilities.write is True

        finally:
            Path(zip_path).unlink(missing_ok=True)


class TestTARBackend:
    """Test TAR archive backend."""

    def test_tar_requires_file(self):
        """TAR backend requires 'file' field."""
        storage = StorageManager()

        with pytest.raises(StorageConfigError, match="missing required field: 'file'"):
            storage.configure([{
                'name': 'tar_test',
                'type': 'tar'
            }])

    def test_tar_configuration_basic(self):
        """Test basic TAR configuration."""
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
            tar_path = tmp.name

        try:
            # Create a test TAR file
            with tarfile.open(tar_path, 'w') as tf:
                # Create a temporary file to add to tar
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as content_file:
                    content_file.write('Hello TAR!')
                    content_path = content_file.name

                tf.add(content_path, arcname='test.txt')
                Path(content_path).unlink()

            storage.configure([{
                'name': 'tar_test',
                'type': 'tar',
                'file': tar_path
            }])

            assert 'tar_test' in storage._mounts

            # Test reading from TAR
            node = storage.node('tar_test:test.txt')
            content = node.read(mode='r')
            assert content == 'Hello TAR!'

        finally:
            Path(tar_path).unlink(missing_ok=True)

    def test_tar_gzip_configuration(self):
        """Test TAR.GZ configuration."""
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
            tar_path = tmp.name

        try:
            # Create a test TAR.GZ file
            with tarfile.open(tar_path, 'w:gz') as tf:
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as content_file:
                    content_file.write('Compressed!')
                    content_path = content_file.name

                tf.add(content_path, arcname='compressed.txt')
                Path(content_path).unlink()

            storage.configure([{
                'name': 'tar_gz_test',
                'type': 'tar',
                'file': tar_path
                # Compression is auto-detected from .tar.gz extension
            }])

            assert 'tar_gz_test' in storage._mounts

            # Test reading from TAR.GZ
            node = storage.node('tar_gz_test:compressed.txt')
            content = node.read(mode='r')
            assert content == 'Compressed!'

        finally:
            Path(tar_path).unlink(missing_ok=True)

    def test_tar_readonly(self):
        """Verify TAR is read-only."""
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
            tar_path = tmp.name

        try:
            # Create empty TAR
            with tarfile.open(tar_path, 'w') as tf:
                pass

            storage.configure([{
                'name': 'tar_test',
                'type': 'tar',
                'file': tar_path
            }])

            backend = storage._mounts['tar_test']
            assert backend.capabilities.readonly is True
            assert backend.capabilities.write is False

        finally:
            Path(tar_path).unlink(missing_ok=True)


class TestBackendCapabilities:
    """Test backend capabilities are correctly set."""

    @pytest.mark.skipif(not HAS_SMB, reason="smbprotocol not installed")
    def test_smb_capabilities(self):
        """Test SMB backend capabilities."""
        storage = StorageManager()
        storage.configure([{
            'name': 'smb_test',
            'type': 'smb',
            'host': 'server',
            'share': 'docs'
        }])

        backend = storage._mounts['smb_test']
        caps = backend.capabilities

        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.list_dir is True
        assert caps.versioning is False
        assert caps.readonly is False

    @pytest.mark.skipif(not HAS_SFTP, reason="paramiko not installed")
    @pytest.mark.skip(reason="SFTP requires actual server connection")
    def test_sftp_capabilities(self):
        """Test SFTP backend capabilities."""
        storage = StorageManager()
        storage.configure([{
            'name': 'sftp_test',
            'type': 'sftp',
            'host': 'server',
            'username': 'user'
        }])

        backend = storage._mounts['sftp_test']
        caps = backend.capabilities

        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.list_dir is True
        assert caps.readonly is False

    def test_zip_capabilities(self):
        """Test ZIP backend capabilities."""
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            zip_path = tmp.name

        try:
            with zipfile.ZipFile(zip_path, 'w') as zf:
                zf.writestr('dummy.txt', 'test')

            storage.configure([{
                'name': 'zip_test',
                'type': 'zip',
                'file': zip_path
            }])

            backend = storage._mounts['zip_test']
            caps = backend.capabilities

            assert caps.read is True
            assert caps.write is True
            assert caps.delete is True
            assert caps.list_dir is True
            assert caps.readonly is False

        finally:
            Path(zip_path).unlink(missing_ok=True)

    def test_tar_capabilities(self):
        """Test TAR backend capabilities."""
        storage = StorageManager()

        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
            tar_path = tmp.name

        try:
            with tarfile.open(tar_path, 'w') as tf:
                pass

            storage.configure([{
                'name': 'tar_test',
                'type': 'tar',
                'file': tar_path
            }])

            backend = storage._mounts['tar_test']
            caps = backend.capabilities

            assert caps.read is True
            assert caps.write is False
            assert caps.delete is False
            assert caps.list_dir is True
            assert caps.readonly is True

        finally:
            Path(tar_path).unlink(missing_ok=True)
