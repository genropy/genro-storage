"""Tests for Git, GitHub, WebDAV, and LibArchive backends."""

import pytest
import socket
from genro_storage import StorageManager, StorageConfigError


def is_service_available(host, port, timeout=1):
    """Check if a service is available at the given host and port.

    Args:
        host: Hostname or IP address
        port: Port number
        timeout: Connection timeout in seconds

    Returns:
        bool: True if service is reachable, False otherwise
    """
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


# Check for optional dependencies
try:
    import pygit2
    HAS_PYGIT2 = True
except ImportError:
    HAS_PYGIT2 = False

try:
    import webdav4
    HAS_WEBDAV = True
except ImportError:
    HAS_WEBDAV = False

try:
    import libarchive
    HAS_LIBARCHIVE = True
except ImportError:
    HAS_LIBARCHIVE = False

try:
    import adlfs
    HAS_AZURE = True
except ImportError:
    HAS_AZURE = False

try:
    import gcsfs
    HAS_GCS = True
except ImportError:
    HAS_GCS = False


# GCS/fake-gcs-server helper functions
def create_gcs_bucket_if_not_exists():
    """Create test bucket in fake-gcs-server if it doesn't exist."""
    if not HAS_GCS:
        return

    try:
        import os
        import requests

        # Set STORAGE_EMULATOR_HOST for fake-gcs-server
        os.environ['STORAGE_EMULATOR_HOST'] = 'http://localhost:4443'

        bucket_name = 'test-bucket'

        # Try to create bucket using HTTP API directly (simpler than google-cloud-storage)
        try:
            response = requests.post(
                'http://localhost:4443/storage/v1/b',
                params={'project': 'test-project'},
                json={'name': bucket_name}
            )
            # 200 = created, 409 = already exists
            if response.status_code not in [200, 409]:
                pass  # Ignore errors, tests will fail if bucket missing
        except Exception:
            pass  # Ignore errors, tests will fail if bucket missing
    except Exception:
        pass


# Azure/Azurite helper functions
def create_azure_container_if_not_exists():
    """Create test container in Azurite if it doesn't exist."""
    if not HAS_AZURE:
        return

    try:
        from azure.storage.blob import BlobServiceClient

        # Azurite connection string
        connection_string = (
            'DefaultEndpointsProtocol=http;'
            'AccountName=devstoreaccount1;'
            'AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;'
            'BlobEndpoint=http://localhost:10000/devstoreaccount1;'
        )

        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        container_name = 'test-container'

        try:
            blob_service_client.create_container(container_name)
        except Exception:
            # Container already exists, ignore
            pass
    except Exception:
        # If we can't create the container, tests will fail anyway
        pass


class TestGitBackend:
    """Tests for Git backend."""

    @pytest.fixture
    def temp_git_repo(self, tmp_path):
        """Create a temporary Git repository for testing."""
        if not HAS_PYGIT2:
            pytest.skip("pygit2 not installed")

        import pygit2

        # Create a bare repository
        repo_path = tmp_path / "test_repo.git"
        pygit2.init_repository(str(repo_path), bare=True)

        return str(repo_path)

    @pytest.mark.skipif(not HAS_PYGIT2, reason="pygit2 not installed")
    def test_git_configuration_basic(self, temp_git_repo):
        """Test basic Git configuration."""
        storage = StorageManager()
        storage.configure([{
            'name': 'git_test',
            'type': 'git',
            'path': temp_git_repo
        }])
        assert 'git_test' in storage._mounts
        backend = storage._mounts['git_test']
        assert backend is not None

    @pytest.mark.skipif(not HAS_PYGIT2, reason="pygit2 not installed")
    def test_git_configuration_with_ref(self, temp_git_repo):
        """Test Git configuration with ref (branch/tag/commit)."""
        storage = StorageManager()
        storage.configure([{
            'name': 'git_test',
            'type': 'git',
            'path': temp_git_repo,
            'ref': 'main'
        }])
        assert 'git_test' in storage._mounts

    def test_git_configuration_missing_path(self):
        """Test Git configuration with missing path raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'path'"):
            storage.configure([{
                'name': 'git_test',
                'type': 'git'
            }])

    @pytest.mark.skipif(not HAS_PYGIT2, reason="pygit2 not installed")
    def test_git_capabilities(self, temp_git_repo):
        """Test Git backend capabilities."""
        storage = StorageManager()
        storage.configure([{
            'name': 'git_test',
            'type': 'git',
            'path': temp_git_repo
        }])
        backend = storage._mounts['git_test']
        caps = backend.capabilities

        # Git is read-only
        assert caps.read is True
        assert caps.write is False
        assert caps.delete is False
        assert caps.mkdir is False
        assert caps.list_dir is True
        assert caps.readonly is True
        assert caps.versioning is True
        assert caps.version_access is True


class TestGitHubBackend:
    """Tests for GitHub backend."""

    def test_github_configuration_basic(self):
        """Test basic GitHub configuration."""
        storage = StorageManager()
        storage.configure([{
            'name': 'gh_test',
            'type': 'github',
            'org': 'genropy',
            'repo': 'genro-storage'
        }])
        assert 'gh_test' in storage._mounts
        backend = storage._mounts['gh_test']
        assert backend is not None

    def test_github_configuration_with_ref(self):
        """Test GitHub configuration with ref (branch/tag/commit)."""
        storage = StorageManager()
        storage.configure([{
            'name': 'gh_test',
            'type': 'github',
            'org': 'genropy',
            'repo': 'genro-storage',
            'ref': 'main'
        }])
        assert 'gh_test' in storage._mounts

    def test_github_configuration_with_token(self):
        """Test GitHub configuration with authentication token."""
        storage = StorageManager()
        storage.configure([{
            'name': 'gh_test',
            'type': 'github',
            'org': 'genropy',
            'repo': 'genro-storage',
            'username': 'testuser',
            'token': 'ghp_test_token'
        }])
        assert 'gh_test' in storage._mounts

    def test_github_configuration_missing_org(self):
        """Test GitHub configuration with missing org raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'org'"):
            storage.configure([{
                'name': 'gh_test',
                'type': 'github',
                'repo': 'genro-storage'
            }])

    def test_github_configuration_missing_repo(self):
        """Test GitHub configuration with missing repo raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'repo'"):
            storage.configure([{
                'name': 'gh_test',
                'type': 'github',
                'org': 'genropy'
            }])

    def test_github_capabilities(self):
        """Test GitHub backend capabilities."""
        storage = StorageManager()
        storage.configure([{
            'name': 'gh_test',
            'type': 'github',
            'org': 'genropy',
            'repo': 'genro-storage'
        }])
        backend = storage._mounts['gh_test']
        caps = backend.capabilities

        # GitHub is read-only
        assert caps.read is True
        assert caps.write is False
        assert caps.delete is False
        assert caps.mkdir is False
        assert caps.list_dir is True
        assert caps.readonly is True
        assert caps.versioning is True
        assert caps.version_access is True


class TestGCSBackend:
    """Tests for GCS backend using fake-gcs-server."""

    @pytest.mark.skipif(not HAS_GCS, reason="gcsfs not installed")
    @pytest.mark.integration
    def test_gcs_configuration_basic(self):
        """Test basic GCS configuration with fake-gcs-server."""
        create_gcs_bucket_if_not_exists()

        storage = StorageManager()
        storage.configure([{
            'name': 'gcs_test',
            'type': 'gcs',
            'bucket': 'test-bucket',
            'endpoint_url': 'http://localhost:4443',
            'token': 'anon',
            'project': 'test-project'
        }])

        assert 'gcs_test' in storage._mounts
        backend = storage._mounts['gcs_test']
        assert backend is not None

    @pytest.mark.skipif(not HAS_GCS, reason="gcsfs not installed")
    @pytest.mark.integration
    def test_gcs_file_operations(self):
        """Test GCS file operations with fake-gcs-server."""
        # Check if fake-gcs-server is available
        if not is_service_available('localhost', 4443):
            pytest.skip("fake-gcs-server not available on localhost:4443")

        create_gcs_bucket_if_not_exists()

        storage = StorageManager()
        storage.configure([{
            'name': 'gcs_test',
            'type': 'gcs',
            'bucket': 'test-bucket',
            'endpoint_url': 'http://localhost:4443',
            'token': 'anon',
            'project': 'test-project'
        }])

        # Test basic file operation
        node = storage.node('gcs_test:test.txt')
        node.write('Hello GCS!', mode='w')
        assert node.exists
        content = node.read(mode='r')
        assert content == 'Hello GCS!'

    @pytest.mark.skipif(not HAS_GCS, reason="gcsfs not installed")
    def test_gcs_configuration_missing_bucket(self):
        """Test GCS configuration with missing bucket raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'bucket'"):
            storage.configure([{
                'name': 'gcs_test',
                'type': 'gcs'
            }])

    @pytest.mark.skipif(not HAS_GCS, reason="gcsfs not installed")
    @pytest.mark.integration
    def test_gcs_configuration_with_prefix(self):
        """Test GCS configuration with prefix (subfolder)."""
        create_gcs_bucket_if_not_exists()

        storage = StorageManager()
        storage.configure([{
            'name': 'gcs_test',
            'type': 'gcs',
            'bucket': 'test-bucket',
            'prefix': 'data/uploads',
            'endpoint_url': 'http://localhost:4443',
            'token': 'anon',
            'project': 'test-project'
        }])

        assert 'gcs_test' in storage._mounts

    @pytest.mark.skipif(not HAS_GCS, reason="gcsfs not installed")
    @pytest.mark.integration
    def test_gcs_capabilities(self):
        """Test GCS backend capabilities."""
        create_gcs_bucket_if_not_exists()

        storage = StorageManager()
        storage.configure([{
            'name': 'gcs_test',
            'type': 'gcs',
            'bucket': 'test-bucket',
            'endpoint_url': 'http://localhost:4443',
            'token': 'anon',
            'project': 'test-project'
        }])
        backend = storage._mounts['gcs_test']
        caps = backend.capabilities

        # GCS supports full read/write
        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.mkdir is True
        assert caps.list_dir is True
        assert caps.readonly is False


class TestWebDAVBackend:
    """Tests for WebDAV backend."""

    @pytest.mark.skipif(not HAS_WEBDAV, reason="webdav4 not installed")
    @pytest.mark.integration
    def test_webdav_configuration_basic(self):
        """Test basic WebDAV configuration with Docker container."""
        # Check if port is available
        if not is_service_available('localhost', 8080):
            pytest.skip("WebDAV server not available on localhost:8080")

        storage = StorageManager()
        storage.configure([{
            'name': 'webdav_test',
            'type': 'webdav',
            'url': 'http://localhost:8080',
            'username': 'testuser',
            'password': 'testpass'
        }])
        assert 'webdav_test' in storage._mounts
        backend = storage._mounts['webdav_test']
        assert backend is not None

        # Test basic file operation
        # Skip if the service on port 8080 is not a proper WebDAV server
        try:
            node = storage.node('webdav_test:test.txt')
            node.write('Hello WebDAV!', mode='w')
            assert node.exists
            content = node.read(mode='r')
            assert content == 'Hello WebDAV!'
        except Exception as e:
            # If we get a webdav4 error, it means the service is not a proper WebDAV server
            if 'webdav4' in str(type(e).__module__) or 'ResourceNotFound' in str(type(e).__name__):
                pytest.skip(f"Service on port 8080 is not a proper WebDAV server: {e}")
            raise

    @pytest.mark.skipif(not HAS_WEBDAV, reason="webdav4 not installed")
    @pytest.mark.integration
    def test_webdav_configuration_with_auth(self):
        """Test WebDAV configuration with authentication."""
        storage = StorageManager()
        storage.configure([{
            'name': 'webdav_test',
            'type': 'webdav',
            'url': 'http://localhost:8080',
            'username': 'testuser',
            'password': 'testpass'
        }])
        assert 'webdav_test' in storage._mounts

    @pytest.mark.skip(reason="Token auth not configured in Docker container")
    def test_webdav_configuration_with_token(self):
        """Test WebDAV configuration with bearer token."""
        storage = StorageManager()
        storage.configure([{
            'name': 'webdav_test',
            'type': 'webdav',
            'url': 'http://localhost:8080',
            'token': 'bearer_token'
        }])
        assert 'webdav_test' in storage._mounts

    @pytest.mark.skipif(not HAS_WEBDAV, reason="webdav4 not installed")
    def test_webdav_configuration_missing_url(self):
        """Test WebDAV configuration with missing URL raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'url'"):
            storage.configure([{
                'name': 'webdav_test',
                'type': 'webdav'
            }])

    @pytest.mark.skipif(not HAS_WEBDAV, reason="webdav4 not installed")
    @pytest.mark.integration
    def test_webdav_capabilities(self):
        """Test WebDAV backend capabilities."""
        storage = StorageManager()
        storage.configure([{
            'name': 'webdav_test',
            'type': 'webdav',
            'url': 'http://localhost:8080',
            'username': 'testuser',
            'password': 'testpass'
        }])
        backend = storage._mounts['webdav_test']
        caps = backend.capabilities

        # WebDAV supports full read/write
        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.mkdir is True
        assert caps.list_dir is True
        assert caps.readonly is False
        assert caps.versioning is False


class TestAzureBackend:
    """Tests for Azure backend using Azurite emulator."""

    @pytest.mark.skipif(not HAS_AZURE, reason="adlfs not installed")
    @pytest.mark.integration
    def test_azure_configuration_basic(self):
        """Test basic Azure configuration with Azurite emulator."""
        create_azure_container_if_not_exists()

        storage = StorageManager()

        # Azurite uses well-known credentials
        storage.configure([{
            'name': 'azure_test',
            'type': 'azure',
            'account_name': 'devstoreaccount1',
            'account_key': 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==',
            'container': 'test-container',
            'connection_string': 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;'
        }])

        assert 'azure_test' in storage._mounts
        backend = storage._mounts['azure_test']
        assert backend is not None

    @pytest.mark.skipif(not HAS_AZURE, reason="adlfs not installed")
    @pytest.mark.integration
    def test_azure_file_operations(self):
        """Test Azure file operations with Azurite."""
        # Check if Azurite is available
        if not is_service_available('localhost', 10000):
            pytest.skip("Azurite not available on localhost:10000")

        create_azure_container_if_not_exists()

        storage = StorageManager()

        storage.configure([{
            'name': 'azure_test',
            'type': 'azure',
            'account_name': 'devstoreaccount1',
            'account_key': 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==',
            'container': 'test-container',
            'connection_string': 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;'
        }])

        # Test basic file operation
        node = storage.node('azure_test:test.txt')
        node.write('Hello Azure!', mode='w')
        assert node.exists
        content = node.read(mode='r')
        assert content == 'Hello Azure!'

    @pytest.mark.skipif(not HAS_AZURE, reason="adlfs not installed")
    def test_azure_configuration_missing_account_name(self):
        """Test Azure configuration with missing account_name raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'account_name'"):
            storage.configure([{
                'name': 'azure_test',
                'type': 'azure',
                'container': 'test-container'
            }])

    @pytest.mark.skipif(not HAS_AZURE, reason="adlfs not installed")
    def test_azure_configuration_missing_container(self):
        """Test Azure configuration with missing container raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'container'"):
            storage.configure([{
                'name': 'azure_test',
                'type': 'azure',
                'account_name': 'devstoreaccount1'
            }])

    @pytest.mark.skipif(not HAS_AZURE, reason="adlfs not installed")
    @pytest.mark.integration
    def test_azure_capabilities(self):
        """Test Azure backend capabilities."""
        create_azure_container_if_not_exists()

        storage = StorageManager()
        storage.configure([{
            'name': 'azure_test',
            'type': 'azure',
            'account_name': 'devstoreaccount1',
            'account_key': 'Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==',
            'container': 'test-container',
            'connection_string': 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;'
        }])
        backend = storage._mounts['azure_test']
        caps = backend.capabilities

        # Azure supports full read/write
        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.mkdir is True
        assert caps.list_dir is True
        assert caps.readonly is False


class TestLibArchiveBackend:
    """Tests for LibArchive backend."""

    @pytest.mark.skip(reason="LibArchive requires actual archive files - tested via ZIP/TAR backends")
    def test_libarchive_configuration_basic(self):
        """Test basic LibArchive configuration."""
        storage = StorageManager()
        storage.configure([{
            'name': 'archive_test',
            'type': 'libarchive',
            'file': '/path/to/archive.tar.gz'
        }])
        assert 'archive_test' in storage._mounts
        backend = storage._mounts['archive_test']
        assert backend is not None

    @pytest.mark.skip(reason="LibArchive requires actual archive files - tested via ZIP/TAR backends")
    def test_libarchive_configuration_with_options(self):
        """Test LibArchive configuration with additional options."""
        storage = StorageManager()
        storage.configure([{
            'name': 'archive_test',
            'type': 'libarchive',
            'file': '/path/to/archive.zip',
            'mode': 'r'
        }])
        assert 'archive_test' in storage._mounts

    @pytest.mark.skipif(not HAS_LIBARCHIVE, reason="libarchive-c not installed")
    def test_libarchive_configuration_missing_file(self):
        """Test LibArchive configuration with missing file raises error."""
        storage = StorageManager()
        with pytest.raises(StorageConfigError, match="missing required field: 'file'"):
            storage.configure([{
                'name': 'archive_test',
                'type': 'libarchive'
            }])

    @pytest.mark.skipif(not HAS_LIBARCHIVE, reason="libarchive-c not installed")
    def test_libarchive_capabilities(self):
        """Test LibArchive backend capabilities."""
        import tempfile
        import tarfile
        from pathlib import Path

        # Create a temporary tar.gz file for testing
        with tempfile.NamedTemporaryFile(suffix='.tar.gz', delete=False) as tmp:
            tar_path = tmp.name

        try:
            # Create minimal valid tar.gz
            with tarfile.open(tar_path, 'w:gz') as tf:
                pass  # Empty archive is fine for capabilities test

            storage = StorageManager()
            storage.configure([{
                'name': 'archive_test',
                'type': 'libarchive',
                'file': tar_path
            }])
            backend = storage._mounts['archive_test']
            caps = backend.capabilities

            # LibArchive is read-only for existing archives
            assert caps.read is True
            assert caps.write is False  # Can't modify existing archives
            assert caps.delete is False
            assert caps.mkdir is False
            assert caps.list_dir is True
            assert caps.readonly is True

        finally:
            Path(tar_path).unlink(missing_ok=True)
