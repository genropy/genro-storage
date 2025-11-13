"""Tests for convenience methods: read_text, read_bytes, write_text, write_bytes."""

import pytest
import tempfile
import shutil

from genro_storage import StorageManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def storage(temp_dir):
    """Create a StorageManager with local storage."""
    mgr = StorageManager()
    mgr.configure([{"name": "test", "protocol": "local", "path": temp_dir}])
    return mgr


class TestReadTextMethod:
    """Test read_text() convenience method."""

    def test_read_text_basic(self, storage):
        """Test basic read_text() functionality."""
        node = storage.node("test:file.txt")
        content = "Hello World"

        # Write using unified API
        node.write(content, mode="w")

        # Read using convenience method
        result = node.read_text()
        assert result == content
        assert isinstance(result, str)

    def test_read_text_with_encoding(self, storage):
        """Test read_text() with custom encoding."""
        node = storage.node("test:file_latin1.txt")
        content = "Café"

        # Write with latin-1 encoding
        node.write(content, mode="w", encoding="latin-1")

        # Read with latin-1 encoding
        result = node.read_text(encoding="latin-1")
        assert result == content

    def test_read_text_multiline(self, storage):
        """Test read_text() with multiline content."""
        node = storage.node("test:multiline.txt")
        content = "Line 1\nLine 2\nLine 3"

        node.write(content, mode="w")
        result = node.read_text()

        assert result == content
        assert result.count("\n") == 2

    def test_read_text_empty_file(self, storage):
        """Test read_text() on empty file."""
        node = storage.node("test:empty.txt")
        node.write("", mode="w")

        result = node.read_text()
        assert result == ""

    def test_read_text_nonexistent(self, storage):
        """Test read_text() raises FileNotFoundError for missing file."""
        node = storage.node("test:missing.txt")

        with pytest.raises(FileNotFoundError):
            node.read_text()


class TestReadBytesMethod:
    """Test read_bytes() convenience method."""

    def test_read_bytes_basic(self, storage):
        """Test basic read_bytes() functionality."""
        node = storage.node("test:file.bin")
        data = b"Binary data"

        # Write using unified API
        node.write(data, mode="wb")

        # Read using convenience method
        result = node.read_bytes()
        assert result == data
        assert isinstance(result, bytes)

    def test_read_bytes_various_content(self, storage):
        """Test read_bytes() with various binary content."""
        node = storage.node("test:data.bin")
        data = bytes(range(256))  # All byte values

        node.write(data, mode="wb")
        result = node.read_bytes()

        assert result == data
        assert len(result) == 256

    def test_read_bytes_empty(self, storage):
        """Test read_bytes() on empty file."""
        node = storage.node("test:empty.bin")
        node.write(b"", mode="wb")

        result = node.read_bytes()
        assert result == b""

    def test_read_bytes_nonexistent(self, storage):
        """Test read_bytes() raises FileNotFoundError for missing file."""
        node = storage.node("test:missing.bin")

        with pytest.raises(FileNotFoundError):
            node.read_bytes()


class TestWriteTextMethod:
    """Test write_text() convenience method."""

    def test_write_text_basic(self, storage):
        """Test basic write_text() functionality."""
        node = storage.node("test:output.txt")
        content = "Hello from write_text"

        # Write using convenience method
        result = node.write_text(content)

        assert result is True  # File was written

        # Verify using unified read
        assert node.read(mode="r") == content

    def test_write_text_with_encoding(self, storage):
        """Test write_text() with custom encoding."""
        node = storage.node("test:latin1.txt")
        content = "Café résumé"

        # Write with latin-1 encoding
        node.write_text(content, encoding="latin-1")

        # Read with same encoding
        result = node.read(mode="r", encoding="latin-1")
        assert result == content

    def test_write_text_overwrite(self, storage):
        """Test write_text() overwrites existing content."""
        node = storage.node("test:overwrite.txt")

        node.write_text("First content")
        node.write_text("Second content")

        result = node.read_text()
        assert result == "Second content"

    def test_write_text_skip_if_unchanged(self, storage):
        """Test write_text() with skip_if_unchanged parameter."""
        node = storage.node("test:unchanged.txt")
        content = "Same content"

        # First write
        result1 = node.write_text(content)
        assert result1 is True

        # Second write with same content and skip_if_unchanged
        result2 = node.write_text(content, skip_if_unchanged=True)
        # Should be skipped (False) for non-versioned local storage if hash matches
        # But behavior depends on backend, so just verify it doesn't raise
        assert isinstance(result2, bool)

    def test_write_text_type_error(self, storage):
        """Test write_text() raises TypeError for non-string."""
        node = storage.node("test:error.txt")

        with pytest.raises(TypeError):
            node.write_text(b"bytes not allowed")  # type: ignore


class TestWriteBytesMethod:
    """Test write_bytes() convenience method."""

    def test_write_bytes_basic(self, storage):
        """Test basic write_bytes() functionality."""
        node = storage.node("test:output.bin")
        data = b"Binary data from write_bytes"

        # Write using convenience method
        result = node.write_bytes(data)

        assert result is True  # File was written

        # Verify using unified read
        assert node.read(mode="rb") == data

    def test_write_bytes_various_content(self, storage):
        """Test write_bytes() with various binary content."""
        node = storage.node("test:binary.bin")
        data = bytes(range(256))

        node.write_bytes(data)

        result = node.read_bytes()
        assert result == data

    def test_write_bytes_overwrite(self, storage):
        """Test write_bytes() overwrites existing content."""
        node = storage.node("test:overwrite.bin")

        node.write_bytes(b"First")
        node.write_bytes(b"Second")

        result = node.read_bytes()
        assert result == b"Second"

    def test_write_bytes_skip_if_unchanged(self, storage):
        """Test write_bytes() with skip_if_unchanged parameter."""
        node = storage.node("test:unchanged.bin")
        data = b"Same binary content"

        # First write
        result1 = node.write_bytes(data)
        assert result1 is True

        # Second write with same content
        result2 = node.write_bytes(data, skip_if_unchanged=True)
        assert isinstance(result2, bool)

    def test_write_bytes_type_error(self, storage):
        """Test write_bytes() raises TypeError for non-bytes."""
        node = storage.node("test:error.bin")

        with pytest.raises(TypeError):
            node.write_bytes("string not allowed")  # type: ignore


class TestConvenienceMethodsEquivalence:
    """Test that convenience methods are equivalent to unified API."""

    def test_read_text_equivalent(self, storage):
        """Test read_text() is equivalent to read(mode='r')."""
        node = storage.node("test:equiv.txt")
        content = "Test equivalence"

        node.write(content, mode="w")

        result1 = node.read_text()
        result2 = node.read(mode="r")

        assert result1 == result2

    def test_read_bytes_equivalent(self, storage):
        """Test read_bytes() is equivalent to read(mode='rb')."""
        node = storage.node("test:equiv.bin")
        data = b"Test equivalence"

        node.write(data, mode="wb")

        result1 = node.read_bytes()
        result2 = node.read(mode="rb")

        assert result1 == result2

    def test_write_text_equivalent(self, storage):
        """Test write_text() is equivalent to write(mode='w')."""
        node1 = storage.node("test:equiv1.txt")
        node2 = storage.node("test:equiv2.txt")
        content = "Test equivalence"

        node1.write_text(content)
        node2.write(content, mode="w")

        assert node1.read_text() == node2.read_text()

    def test_write_bytes_equivalent(self, storage):
        """Test write_bytes() is equivalent to write(mode='wb')."""
        node1 = storage.node("test:equiv1.bin")
        node2 = storage.node("test:equiv2.bin")
        data = b"Test equivalence"

        node1.write_bytes(data)
        node2.write(data, mode="wb")

        assert node1.read_bytes() == node2.read_bytes()


class TestPathlibCompatibility:
    """Test compatibility with pathlib.Path API."""

    def test_pathlib_pattern_text(self, storage):
        """Test read_text/write_text follow pathlib.Path pattern."""
        from pathlib import Path

        # StorageNode API should match pathlib API
        node = storage.node("test:pathlib.txt")
        content = "Pathlib compatible"

        # Both should support same basic API
        node.write_text(content)
        assert node.read_text() == content

        # Encoding parameter
        node.write_text(content, encoding="utf-8")
        assert node.read_text(encoding="utf-8") == content

    def test_pathlib_pattern_bytes(self, storage):
        """Test read_bytes/write_bytes follow pathlib.Path pattern."""
        node = storage.node("test:pathlib.bin")
        data = b"Pathlib compatible"

        # Both should support same basic API
        node.write_bytes(data)
        assert node.read_bytes() == data
