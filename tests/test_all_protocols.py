"""Test suite for all 14 storage protocols.

Tests protocol registration, configuration validation, and basic operations
for each supported protocol.
"""

import pytest
import tempfile
import socket
from pathlib import Path

from genro_storage.providers.registry import ProviderRegistry
from genro_storage.async_storage_manager import AsyncStorageManager


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


class TestProtocolRegistration:
    """Test that all protocols are correctly registered."""

    def test_all_protocols_registered(self):
        """Verify all 14 protocols are registered."""
        protocols = ProviderRegistry.list_protocols()

        expected = [
            "azure",
            "base64",
            "ftp",
            "gcs",
            "github",
            "http",
            "local",
            "memory",
            "s3_aws",
            "s3_minio",
            "sftp",
            "smb",
            "tar",
            "zip",
        ]

        assert len(protocols) == 14, f"Expected 14 protocols, got {len(protocols)}"

        for protocol in expected:
            assert protocol in protocols, f"Protocol '{protocol}' not registered"

    def test_protocol_providers(self):
        """Test protocol grouping by provider."""
        providers = ProviderRegistry.list_providers()

        # Should have AsyncProvider (all protocols use this base)
        assert "AsyncProvider" in providers

        # AsyncProvider should have all 14 protocols
        all_protocols = providers["AsyncProvider"]
        assert len(all_protocols) == 14

        # Check base64 is included
        assert "base64" in all_protocols


class TestProtocolConfiguration:
    """Test configuration models for all protocols."""

    def test_s3_aws_config(self):
        """Test S3 AWS configuration."""
        config = ProviderRegistry.get_protocol("s3_aws")
        Model = config["model"]

        # Valid configuration
        instance = Model(bucket="my-bucket", region="us-east-1")
        assert instance.bucket == "my-bucket"
        assert instance.region == "us-east-1"

        # Missing required field
        with pytest.raises(Exception):  # Pydantic ValidationError
            Model(region="us-east-1")  # Missing bucket

    def test_s3_minio_config(self):
        """Test S3 MinIO configuration."""
        config = ProviderRegistry.get_protocol("s3_minio")
        Model = config["model"]

        instance = Model(
            bucket="my-bucket",
            endpoint_url="http://localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
        )
        assert instance.endpoint_url == "http://localhost:9000"

    def test_gcs_config(self):
        """Test Google Cloud Storage configuration."""
        config = ProviderRegistry.get_protocol("gcs")
        Model = config["model"]

        instance = Model(bucket="my-bucket")
        assert instance.bucket == "my-bucket"
        assert instance.project is None

    def test_azure_config(self):
        """Test Azure Blob Storage configuration."""
        config = ProviderRegistry.get_protocol("azure")
        Model = config["model"]

        instance = Model(account_name="myaccount", container="mycontainer", account_key="key123")
        assert instance.account_name == "myaccount"
        assert instance.container == "mycontainer"

    def test_local_config(self):
        """Test local filesystem configuration."""
        config = ProviderRegistry.get_protocol("local")
        Model = config["model"]

        with tempfile.TemporaryDirectory() as tmpdir:
            instance = Model(root_path=tmpdir)
            assert instance.root_path == tmpdir

    def test_memory_config(self):
        """Test memory filesystem configuration."""
        config = ProviderRegistry.get_protocol("memory")
        Model = config["model"]

        instance = Model()  # No required fields
        assert instance is not None

    def test_http_config(self):
        """Test HTTP protocol configuration."""
        config = ProviderRegistry.get_protocol("http")
        Model = config["model"]

        instance = Model(base_url="https://example.com/files")
        assert instance.base_url == "https://example.com/files"

        # Should reject invalid URLs
        with pytest.raises(Exception):
            Model(base_url="not-a-url")

    def test_ftp_config(self):
        """Test FTP configuration."""
        config = ProviderRegistry.get_protocol("ftp")
        Model = config["model"]

        instance = Model(host="ftp.example.com")
        assert instance.host == "ftp.example.com"
        assert instance.port == 21
        assert instance.username == "anonymous"

    def test_sftp_config(self):
        """Test SFTP configuration."""
        config = ProviderRegistry.get_protocol("sftp")
        Model = config["model"]

        instance = Model(host="sftp.example.com", username="user")
        assert instance.host == "sftp.example.com"
        assert instance.port == 22
        assert instance.username == "user"

    def test_smb_config(self):
        """Test SMB configuration."""
        config = ProviderRegistry.get_protocol("smb")
        Model = config["model"]

        instance = Model(host="server", share="files")
        assert instance.host == "server"
        assert instance.share == "files"

    def test_zip_config(self):
        """Test ZIP archive configuration."""
        config = ProviderRegistry.get_protocol("zip")
        Model = config["model"]

        instance = Model(zip_file="/path/to/archive.zip")
        assert instance.zip_file == "/path/to/archive.zip"

        # Should reject non-.zip files
        with pytest.raises(Exception):
            Model(zip_file="/path/to/file.tar")

    def test_tar_config(self):
        """Test TAR archive configuration."""
        config = ProviderRegistry.get_protocol("tar")
        Model = config["model"]

        # Should accept various tar formats
        for ext in [".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tar.xz"]:
            instance = Model(tar_file=f"/path/to/archive{ext}")
            assert instance.tar_file == f"/path/to/archive{ext}"

        # Should reject invalid extensions
        with pytest.raises(Exception):
            Model(tar_file="/path/to/file.zip")

    def test_github_config(self):
        """Test GitHub repository configuration."""
        config = ProviderRegistry.get_protocol("github")
        Model = config["model"]

        instance = Model(org="python", repo="cpython")
        assert instance.org == "python"
        assert instance.repo == "cpython"
        assert instance.ref == "main"

    def test_base64_config(self):
        """Test base64 protocol configuration."""
        config = ProviderRegistry.get_protocol("base64")
        Model = config["model"]

        instance = Model()  # No required fields
        assert instance is not None


class TestProtocolCapabilities:
    """Test capabilities for each protocol."""

    @pytest.mark.parametrize(
        "protocol,expected_caps",
        [
            ("s3_aws", ["read", "write", "delete", "list", "metadata", "versioning", "hash"]),
            ("s3_minio", ["read", "write", "delete", "list", "metadata", "versioning", "hash"]),
            ("gcs", ["read", "write", "delete", "list", "metadata", "hash"]),
            ("azure", ["read", "write", "delete", "list", "metadata", "hash"]),
            ("local", ["read", "write", "delete", "list"]),
            ("memory", ["read", "write", "delete", "list"]),
            ("http", ["read"]),  # Read-only
            ("ftp", ["read", "write", "delete", "list"]),
            ("sftp", ["read", "write", "delete", "list"]),
            ("smb", ["read", "write", "delete", "list"]),
            ("zip", ["read", "list"]),  # Read-only
            ("tar", ["read", "list"]),  # Read-only
            ("github", ["read", "list"]),  # Read-only
            ("base64", ["read", "write"]),  # Read and write base64 data
        ],
    )
    def test_protocol_capabilities(self, protocol, expected_caps):
        """Test that each protocol has correct capabilities."""
        config = ProviderRegistry.get_protocol(protocol)
        capabilities = config["capabilities"]

        assert capabilities == expected_caps, f"Protocol '{protocol}' capabilities mismatch"


@pytest.mark.asyncio
class TestProtocolIntegration:
    """Integration tests for protocols (require actual backends)."""

    async def test_local_protocol_basic_operations(self):
        """Test local protocol with actual filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = AsyncStorageManager()
            await storage.configure([{"name": "local", "protocol": "local", "root_path": tmpdir}])

            # Write
            node = storage.node("local:test.txt")
            await node.write(b"Hello Local")

            # Read
            content = await node.read()
            assert content == b"Hello Local"

            # Properties
            assert await node.exists
            assert await node.is_file
            assert await node.size == 11

            # Delete
            await node.delete()
            assert not await node.exists

            await storage.close_all()

    async def test_memory_protocol_basic_operations(self):
        """Test memory protocol."""
        storage = AsyncStorageManager()
        await storage.configure([{"name": "mem", "protocol": "memory"}])

        # Write
        node = storage.node("mem:test.txt")
        await node.write(b"Hello Memory")

        # Read
        content = await node.read()
        assert content == b"Hello Memory"

        # List
        node2 = storage.node("mem:test2.txt")
        await node2.write(b"data")

        root = storage.node("mem:")
        children = await root.list()
        names = [c.basename for c in children]
        assert "test.txt" in names
        assert "test2.txt" in names

        await storage.close_all()

    async def test_base64_protocol_read(self):
        """Test base64 protocol (read-only)."""
        storage = AsyncStorageManager()
        await storage.configure([{"name": "b64", "protocol": "base64"}])

        # base64 encoded "Hello World"
        encoded = "SGVsbG8gV29ybGQ="
        node = storage.node(f"b64:{encoded}")

        content = await node.read()
        assert content == b"Hello World"

        await storage.close_all()

    async def test_s3_minio_protocol_integration(self, minio_bucket, minio_config):
        """Integration test for S3 using MinIO."""
        storage = AsyncStorageManager()
        await storage.configure(
            [
                {
                    "name": "s3",
                    "protocol": "s3_minio",
                    "bucket": minio_bucket,
                    "endpoint_url": minio_config["endpoint_url"],
                    "access_key": minio_config["aws_access_key_id"],
                    "secret_key": minio_config["aws_secret_access_key"],
                }
            ]
        )

        # Write
        node = storage.node("s3:test.txt")
        await node.write(b"Hello MinIO")

        # Read
        content = await node.read()
        assert content == b"Hello MinIO"

        # Properties
        assert await node.exists
        assert await node.is_file
        assert await node.size == 11

        # Delete
        await node.delete()
        assert not await node.exists

        await storage.close_all()

    async def test_gcs_protocol_integration(self):
        """Integration test for GCS using fake-gcs-server.

        Skipped if fake-gcs-server is not available (docker-compose).
        """
        import os

        gcs_host = os.getenv("STORAGE_EMULATOR_HOST", "http://localhost:4443")

        # Check if fake-gcs-server is available
        if not is_service_available("localhost", 4443):
            pytest.skip("fake-gcs-server not available (run docker-compose up)")

        storage = AsyncStorageManager()
        await storage.configure(
            [{"name": "gcs", "protocol": "gcs", "bucket": "test-bucket", "endpoint": gcs_host}]
        )

        node = storage.node("gcs:test.txt")
        await node.write(b"Hello GCS")

        content = await node.read()
        assert content == b"Hello GCS"

        await storage.close_all()

    async def test_azure_protocol_integration(self):
        """Integration test for Azure using Azurite emulator.

        Skipped if Azurite is not available (docker-compose).
        """
        # Check if Azurite is available
        if not is_service_available("localhost", 10000):
            pytest.skip("Azurite not available (run docker-compose up)")

        storage = AsyncStorageManager()
        await storage.configure(
            [
                {
                    "name": "azure",
                    "protocol": "azure",
                    "account_name": "devstoreaccount1",
                    "account_key": "Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==",
                    "container": "test-container",
                }
            ]
        )

        node = storage.node("azure:test.txt")
        await node.write(b"Hello Azure")

        content = await node.read()
        assert content == b"Hello Azure"

        await storage.close_all()

    async def test_sftp_protocol_integration(self):
        """Integration test for SFTP.

        Skipped if SFTP server is not available (docker-compose).
        """
        # Check if SFTP is available
        if not is_service_available("localhost", 2222):
            pytest.skip("SFTP server not available (run docker-compose up)")

        storage = AsyncStorageManager()
        await storage.configure(
            [
                {
                    "name": "sftp",
                    "protocol": "sftp",
                    "host": "localhost",
                    "port": 2222,
                    "username": "testuser",
                    "password": "testpass",
                }
            ]
        )

        node = storage.node("sftp:upload/test.txt")
        await node.write(b"Hello SFTP")

        content = await node.read()
        assert content == b"Hello SFTP"

        await storage.close_all()

    async def test_smb_protocol_integration(self):
        """Integration test for SMB.

        Skipped if SMB server is not available (docker-compose).
        """
        # Check if SMB is available
        if not is_service_available("localhost", 445):
            pytest.skip("SMB server not available (run docker-compose up)")

        storage = AsyncStorageManager()
        await storage.configure(
            [
                {
                    "name": "smb",
                    "protocol": "smb",
                    "host": "localhost",
                    "share": "share",
                    "username": "testuser",
                    "password": "testpass",
                }
            ]
        )

        node = storage.node("smb:test.txt")
        await node.write(b"Hello SMB")

        content = await node.read()
        assert content == b"Hello SMB"

        await storage.close_all()


class TestProtocolErrorHandling:
    """Test error handling for protocols."""

    def test_invalid_protocol_name(self):
        """Test error for non-existent protocol."""
        with pytest.raises(ValueError, match="Protocol 'invalid' not found"):
            ProviderRegistry.get_protocol("invalid")

    def test_protocol_validation_errors(self):
        """Test Pydantic validation errors."""
        config = ProviderRegistry.get_protocol("s3_aws")
        Model = config["model"]

        # Empty bucket name
        with pytest.raises(Exception):
            Model(bucket="", region="us-east-1")

        # Whitespace only
        with pytest.raises(Exception):
            Model(bucket="   ", region="us-east-1")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
