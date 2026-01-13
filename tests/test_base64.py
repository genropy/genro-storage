"""Tests for Base64Backend - inline data URI style storage."""

import pytest
import base64

from genro_storage import StorageManager, StorageNotFoundError


@pytest.fixture
def storage():
    """Create a StorageManager with base64 backend."""
    mgr = StorageManager()
    mgr.configure([{"name": "b64", "protocol": "base64"}])
    return mgr


class TestBase64Backend:
    """Test Base64Backend functionality."""

    def test_configure_base64_backend(self):
        """Test configuring base64 backend."""
        storage = StorageManager()
        storage.configure([{"name": "data", "protocol": "base64"}])

        assert storage.has_mount("data")
        assert "data" in storage.get_mount_names()

    def test_read_text_from_base64(self, storage):
        """Test reading text data from base64."""
        # "Hello World" in base64
        b64_data = base64.b64encode(b"Hello World").decode()

        node = storage.node(f"b64:{b64_data}")
        content = node.read()

        assert content == "Hello World"

    def test_read_bytes_from_base64(self, storage):
        """Test reading binary data from base64."""
        data = b"\x00\x01\x02\x03\xff"
        b64_data = base64.b64encode(data).decode()

        node = storage.node(f"b64:{b64_data}")
        result = node.read(mode="rb")

        assert result == data

    def test_exists_valid_base64(self, storage):
        """Test exists() returns True for valid base64."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        assert node.exists() is True

    def test_exists_invalid_base64(self, storage):
        """Test exists() returns False for invalid base64."""
        node = storage.node("b64:invalid!!!base64")

        assert node.exists() is False

    def test_is_file_valid_base64(self, storage):
        """Test isfile returns True for valid base64."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        assert node.is_file() is True

    def test_is_dir_always_false(self, storage):
        """Test isdir always returns False."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        assert node.is_dir() is False

    def test_size_returns_decoded_size(self, storage):
        """Test size returns the decoded data size."""
        data = b"Hello World"
        b64_data = base64.b64encode(data).decode()
        node = storage.node(f"b64:{b64_data}")

        assert node.size() == len(data)

    def test_mtime_returns_timestamp(self, storage):
        """Test mtime returns a valid timestamp."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        mtime = node.mtime()
        assert isinstance(mtime, float)
        assert mtime > 0

    def test_md5hash_property(self, storage):
        """Test MD5 hash calculation."""
        data = b"Hello World"
        b64_data = base64.b64encode(data).decode()
        node = storage.node(f"b64:{b64_data}")

        # Calculate expected hash
        import hashlib

        expected_hash = hashlib.md5(data).hexdigest()

        assert node.md5hash() == expected_hash

    def test_read_text_with_encoding(self, storage):
        """Test reading text with specific encoding."""
        text = "Ciao mondo"
        b64_data = base64.b64encode(text.encode("utf-8")).decode()
        node = storage.node(f"b64:{b64_data}")

        content = node.read(encoding="utf-8")
        assert content == text

    def test_write_text_updates_path(self, storage):
        """Test that write_text updates the node's path."""
        # Start with empty or any base64
        node = storage.node("b64:")

        # Write new content
        node.write("Hello World")

        # Path should be updated to new base64
        expected_b64 = base64.b64encode(b"Hello World").decode()
        assert node.path == expected_b64

        # Reading should return the new content
        assert node.read() == "Hello World"

    def test_write_bytes_updates_path(self, storage):
        """Test that write_bytes updates the node's path."""
        # Start with empty or any base64
        node = storage.node("b64:")

        data = b"\x00\x01\x02\xff"
        node.write(data, mode="wb")

        # Path should be updated to new base64
        expected_b64 = base64.b64encode(data).decode()
        assert node.path == expected_b64

        # Reading should return the new content
        assert node.read(mode="rb") == data

    def test_delete_raises_permission_error(self, storage):
        """Test that delete raises PermissionError."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        with pytest.raises(PermissionError, match="read-only"):
            node.delete()

    def test_mkdir_raises_permission_error(self, storage):
        """Test that mkdir raises PermissionError."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        with pytest.raises(PermissionError, match="read-only"):
            node.mkdir()

    def test_list_dir_raises_value_error(self, storage):
        """Test that list_dir raises ValueError on backend."""
        from genro_storage.backends.base64 import Base64Backend

        backend = Base64Backend()

        b64_data = base64.b64encode(b"test").decode()

        with pytest.raises(ValueError, match="no directory structure"):
            backend.list_dir(b64_data)

    def test_invalid_base64_raises_file_not_found(self, storage):
        """Test that invalid base64 raises FileNotFoundError."""
        node = storage.node("b64:not-valid-base64!!!")

        with pytest.raises(FileNotFoundError, match="Invalid base64"):
            node.read()

    def test_empty_path_raises_file_not_found(self, storage):
        """Test that empty path raises FileNotFoundError."""
        node = storage.node("b64:")

        with pytest.raises(FileNotFoundError, match="cannot be empty"):
            node.read(mode="rb")

    def test_base64_with_whitespace(self, storage):
        """Test base64 with whitespace is handled correctly."""
        data = b"Hello World"
        b64_data = base64.b64encode(data).decode()
        # Add whitespace
        b64_with_spaces = f"  {b64_data}  \n"

        node = storage.node(f"b64:{b64_with_spaces}")
        result = node.read(mode="rb")

        assert result == data

    def test_copy_to_memory_backend(self, storage):
        """Test copying base64 data to another backend."""
        # Setup memory backend for destination
        storage.configure([{"name": "mem", "protocol": "memory"}])

        # Create base64 source
        data = b"Test data for copy"
        b64_data = base64.b64encode(data).decode()
        src = storage.node(f"b64:{b64_data}")

        # Copy to memory
        dest = storage.node("mem:copied_file.txt")
        src.copy_to(dest)

        # Verify copy
        assert dest.exists()
        assert dest.read(mode="rb") == data

    def test_equality_between_base64_nodes(self, storage):
        """Test content-based equality between base64 nodes."""
        data = b"Same content"
        b64_data1 = base64.b64encode(data).decode()
        b64_data2 = base64.b64encode(data).decode()

        node1 = storage.node(f"b64:{b64_data1}")
        node2 = storage.node(f"b64:{b64_data2}")

        # Should be equal (same content)
        assert node1 == node2

    def test_inequality_different_content(self, storage):
        """Test inequality with different content."""
        b64_data1 = base64.b64encode(b"Content 1").decode()
        b64_data2 = base64.b64encode(b"Content 2").decode()

        node1 = storage.node(f"b64:{b64_data1}")
        node2 = storage.node(f"b64:{b64_data2}")

        assert node1 != node2

    def test_multiline_base64(self, storage):
        """Test base64 with newlines (MIME format)."""
        data = b"A" * 100  # Long data that might be formatted with newlines
        b64_data = base64.b64encode(data).decode()

        # Add newlines every 64 chars (MIME format)
        formatted = "\n".join(b64_data[i : i + 64] for i in range(0, len(b64_data), 64))

        node = storage.node(f"b64:{formatted}")
        result = node.read(mode="rb")

        assert result == data

    def test_open_read_binary(self, storage):
        """Test opening base64 as binary file."""
        data = b"File content"
        b64_data = base64.b64encode(data).decode()
        node = storage.node(f"b64:{b64_data}")

        with node.open("rb") as f:
            content = f.read()

        assert content == data

    def test_open_read_text(self, storage):
        """Test opening base64 as text file."""
        text = "Text content"
        b64_data = base64.b64encode(text.encode()).decode()
        node = storage.node(f"b64:{b64_data}")

        with node.open("r") as f:
            content = f.read()

        assert content == text

    def test_open_write_mode(self, storage):
        """Test that opening for write returns empty buffer."""
        b64_data = base64.b64encode(b"test").decode()
        node = storage.node(f"b64:{b64_data}")

        # Write mode should return empty buffer
        with node.open("wb") as f:
            assert f.read() == b""

        # Text write mode
        with node.open("w") as f:
            assert f.read() == ""

    def test_unicode_text(self, storage):
        """Test reading Unicode text from base64."""
        text = "Hello 世界 🌍"
        b64_data = base64.b64encode(text.encode("utf-8")).decode()
        node = storage.node(f"b64:{b64_data}")

        result = node.read()
        assert result == text

    def test_readme_example(self, storage):
        """Test the example from documentation."""
        # Example: embed a small text file
        text = "Configuration data"
        b64_encoded = base64.b64encode(text.encode()).decode()

        # Access it
        node = storage.node(f"b64:{b64_encoded}")
        content = node.read()

        assert content == text
        assert node.exists()
        assert node.is_file()

    def test_image_data_example(self, storage):
        """Test with binary data (simulating an image)."""
        # Simulate a small PNG header
        png_header = b"\x89PNG\r\n\x1a\n"
        b64_data = base64.b64encode(png_header).decode()

        node = storage.node(f"b64:{b64_data}")
        data = node.read(mode="rb")

        assert data == png_header
        assert len(data) == 8

    def test_path_changes_after_write(self, storage):
        """Test that path changes after each write operation."""
        node = storage.node("b64:")

        # First write
        node.write("First")
        first_path = node.path
        assert first_path == base64.b64encode(b"First").decode()
        assert node.read() == "First"

        # Second write - path should change
        node.write("Second")
        second_path = node.path
        assert second_path == base64.b64encode(b"Second").decode()
        assert second_path != first_path
        assert node.read() == "Second"

    def test_copy_from_memory_to_base64(self, storage):
        """Test copying from memory backend to base64 (the main use case)."""
        # Setup memory backend with source data
        storage.configure([{"name": "mem", "protocol": "memory"}])

        # Create source file in memory
        src = storage.node("mem:test.txt")
        src.write("Test data for base64")

        # Create empty base64 destination
        dest = storage.node("b64:")

        # Copy to base64
        src.copy_to(dest)

        # Destination should now have base64-encoded content in its path
        expected_b64 = base64.b64encode(b"Test data for base64").decode()
        assert dest.path == expected_b64
        assert dest.read() == "Test data for base64"

    def test_multiple_writes_maintain_reference(self, storage):
        """Test that node reference remains valid after multiple writes."""
        node = storage.node("b64:")

        # Multiple writes
        for i in range(5):
            node.write(f"Content {i}")
            assert node.read() == f"Content {i}"
            assert node.exists()

        # Final check
        assert node.read() == "Content 4"
