"""Tests for backend capabilities and advanced versioning features."""

import pytest
import tempfile
from datetime import datetime, timedelta
from genro_storage import StorageManager
from genro_storage.capabilities import BackendCapabilities


class TestCapabilities:
    """Tests for backend capabilities system."""

    def test_memory_backend_capabilities(self):
        """Memory backend has correct capabilities."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        caps = node.capabilities

        assert isinstance(caps, BackendCapabilities)
        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.versioning is False
        assert caps.metadata is False
        assert caps.presigned_urls is False
        assert caps.temporary is True  # Memory is temporary

    def test_local_backend_capabilities(self):
        """Local backend has correct capabilities."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([{"name": "local", "protocol": "local", "path": temp_dir}])

        node = storage.node("local:test.txt")
        caps = node.capabilities

        assert isinstance(caps, BackendCapabilities)
        assert caps.read is True
        assert caps.write is True
        assert caps.delete is True
        assert caps.versioning is False
        assert caps.metadata is False
        assert caps.presigned_urls is False
        assert caps.temporary is False

    def test_base64_backend_capabilities(self):
        """Base64 backend has correct capabilities."""
        storage = StorageManager()
        storage.configure([{"name": "b64", "protocol": "base64"}])

        node = storage.node("b64:dGVzdA==")
        caps = node.capabilities

        assert isinstance(caps, BackendCapabilities)
        assert caps.read is True
        assert caps.write is False  # Read-only
        assert caps.delete is False
        assert caps.readonly is True
        assert caps.versioning is False

    def test_capabilities_string_representation(self):
        """Capabilities have string representation."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        caps_str = str(node.capabilities)

        # Should be a string
        assert isinstance(caps_str, str)
        # Should mention some capabilities
        assert len(caps_str) > 0


class TestVersionCount:
    """Tests for version_count property."""

    def test_version_count_zero_for_nonversioned(self):
        """version_count returns 0 for non-versioned backends."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("content")

        assert node.version_count == 0

    def test_version_count_zero_for_local(self):
        """version_count returns 0 for local storage."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([{"name": "local", "protocol": "local", "path": temp_dir}])

        node = storage.node("local:test.txt")
        node.write("content")

        assert node.version_count == 0


class TestWriteIfChanged:
    """Tests for write with skip_if_unchanged parameter."""

    def test_write_bytes_skip_if_unchanged_creates_file(self):
        """write_bytes(skip_if_unchanged=True) creates file if it doesn't exist."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")

        # First write should succeed
        changed = node.write(b"Hello", skip_if_unchanged=True, mode="wb")
        assert changed is True
        assert node.exists()
        assert node.read(mode="rb") == b"Hello"

    def test_write_bytes_skip_if_unchanged_skips_duplicate(self):
        """write_bytes(skip_if_unchanged=True) skips if content is identical."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write(b"Hello", mode="wb")

        # Second write with same content should be skipped
        # Memory backend will read and compare content
        changed = node.write(b"Hello", skip_if_unchanged=True, mode="wb")
        assert changed is False  # Content is identical, should skip
        assert node.read(mode="rb") == b"Hello"

    def test_write_bytes_skip_if_unchanged_updates_different_content(self):
        """write_bytes(skip_if_unchanged=True) writes if content is different."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write(b"Hello", mode="wb")

        # Write different content
        changed = node.write(b"World", skip_if_unchanged=True, mode="wb")
        assert changed is True
        assert node.read(mode="rb") == b"World"

    def test_write_text_skip_if_unchanged_creates_file(self):
        """write_text(skip_if_unchanged=True) creates file if it doesn't exist."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")

        changed = node.write("Hello", skip_if_unchanged=True)
        assert changed is True
        assert node.read() == "Hello"

    def test_write_text_skip_if_unchanged_updates_different_content(self):
        """write_text(skip_if_unchanged=True) writes if content is different."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("Hello")

        changed = node.write("World", skip_if_unchanged=True)
        assert changed is True
        assert node.read() == "World"


class TestOpenWithVersion:
    """Tests for open() with version parameter."""

    def test_open_with_version_raises_on_nonversioned(self):
        """open(version=...) raises PermissionError on non-versioned backend."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("content")

        with pytest.raises(PermissionError, match="does not support versioning"):
            with node.open(version=-2):
                pass

    def test_open_with_as_of_raises_on_nonversioned(self):
        """open(as_of=...) raises PermissionError on non-versioned backend."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("content")

        yesterday = datetime.now() - timedelta(days=1)

        with pytest.raises(PermissionError, match="does not support versioning"):
            with node.open(as_of=yesterday):
                pass

    def test_open_with_both_version_and_as_of_raises(self):
        """open() with both version and as_of raises ValueError."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")

        with pytest.raises(ValueError, match="Cannot specify both"):
            with node.open(version=-2, as_of=datetime.now()):
                pass


class TestCompactVersions:
    """Tests for compact_versions method."""

    def test_compact_versions_raises_on_nonversioned(self):
        """compact_versions raises PermissionError on non-versioned backend."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("content")

        with pytest.raises(PermissionError, match="does not support versioning"):
            node.compact_versions()

    def test_compact_versions_dry_run_on_nonversioned(self):
        """compact_versions with dry_run raises PermissionError on non-versioned backend."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("content")

        with pytest.raises(PermissionError, match="does not support versioning"):
            node.compact_versions(dry_run=True)


class TestDeleteVersion:
    """Tests for delete_version backend method."""

    def test_delete_version_raises_on_memory(self):
        """delete_version raises PermissionError on memory backend."""
        storage = StorageManager()
        storage.configure([{"name": "mem", "protocol": "memory"}])

        node = storage.node("mem:test.txt")
        node.write("content")

        with pytest.raises(PermissionError, match="does not support version deletion"):
            node._backend.delete_version("test.txt", "dummy_version_id")

    def test_delete_version_raises_on_local(self):
        """delete_version raises PermissionError on local backend."""
        storage = StorageManager()
        temp_dir = tempfile.mkdtemp()
        storage.configure([{"name": "local", "protocol": "local", "path": temp_dir}])

        node = storage.node("local:test.txt")
        node.write("content")

        with pytest.raises(PermissionError, match="does not support version deletion"):
            node._backend.delete_version("test.txt", "dummy_version_id")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
