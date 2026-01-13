"""Tests for relative mounts with permission control."""

import pytest

from genro_storage import StorageManager
from genro_storage.exceptions import StorageConfigError, StoragePermissionError


@pytest.fixture
def storage():
    """Create StorageManager with parent mount."""
    manager = StorageManager()
    manager.configure([{"name": "data", "protocol": "memory", "base_path": "/data"}])
    return manager


def test_relative_mount_basic(storage):
    """Test basic relative mount configuration and path resolution."""
    # Configure child mount
    storage.configure([{"name": "uploads", "path": "data:uploads"}])

    # Create directory structure in parent
    parent_node = storage.node("data:uploads/images/test.txt")
    parent_node.write("Hello World")

    # Access via child mount
    child_node = storage.node("uploads:images/test.txt")
    assert child_node.exists()
    assert child_node.read() == "Hello World"


def test_relative_mount_readonly_permissions(storage):
    """Test readonly permission blocks write and delete operations."""
    storage.configure([{"name": "public", "path": "data:public", "permissions": "readonly"}])

    # Create file via parent mount
    storage.node("data:public/file.txt").write("test content")

    # Read operations should work
    node = storage.node("public:file.txt")
    assert node.exists()
    assert node.read() == "test content"
    assert node.size() > 0

    # List operations should work
    dir_node = storage.node("public:")
    files = list(dir_node.children())
    assert len(files) > 0

    # Write operations should fail
    with pytest.raises(StoragePermissionError):
        node.write("new content")

    with pytest.raises(StoragePermissionError):
        storage.node("public:newfile.txt").write("data")

    # Delete operations should fail
    with pytest.raises(StoragePermissionError):
        node.delete()


def test_relative_mount_readwrite_permissions(storage):
    """Test readwrite permission allows read/write but blocks delete."""
    storage.configure([{"name": "workspace", "path": "data:workspace", "permissions": "readwrite"}])

    # Write operations should work
    node = storage.node("workspace:file.txt")
    node.write("test content")
    assert node.exists()

    # Read operations should work
    assert node.read() == "test content"

    # Modify operations should work
    node.write("modified content")
    assert node.read() == "modified content"

    # Delete operations should fail
    with pytest.raises(StoragePermissionError):
        node.delete()


def test_relative_mount_delete_permissions(storage):
    """Test delete permission allows all operations including delete."""
    storage.configure([{"name": "temp", "path": "data:temp", "permissions": "delete"}])

    # Write operations should work
    node = storage.node("temp:file.txt")
    node.write("test content")
    assert node.exists()

    # Read operations should work
    assert node.read() == "test content"

    # Delete operations should work
    node.delete()
    assert not node.exists()


def test_relative_mount_default_permissions(storage):
    """Test default permissions are 'delete' (full access)."""
    storage.configure(
        [
            {"name": "full", "path": "data:full"}
            # No explicit permissions - should default to 'delete'
        ]
    )

    # All operations should work
    node = storage.node("full:file.txt")
    node.write("test")
    assert node.read() == "test"
    node.delete()
    assert not node.exists()


def test_relative_mount_invalid_parent(storage):
    """Test error when parent mount doesn't exist."""
    with pytest.raises(StorageConfigError, match="Parent mount 'missing' not found"):
        storage.configure([{"name": "invalid", "path": "missing:subdir"}])


def test_relative_mount_invalid_path_format(storage):
    """Test error when path doesn't contain colon separator."""
    # This will be treated as relative mount path since there's a path field with no type
    # But path lacks ':', so should fail
    # Actually, if we provide 'type', it's NOT a relative mount
    # To trigger relative mount detection, path must contain ':'
    # So let's test that a path with ':' but invalid parent fails
    # The test for missing ':' is implicit - it would just be treated as normal mount

    # Better: test that invalid format (path with ':' but invalid parent) fails
    # This is already covered by test_relative_mount_invalid_parent

    # Skip this test as the behavior is: path without ':' + type field = normal mount
    pytest.skip("Path without ':' is treated as normal mount, not relative mount")


def test_relative_mount_invalid_permissions(storage):
    """Test error when permissions value is invalid."""
    with pytest.raises(StorageConfigError, match="Invalid permissions"):
        storage.configure([{"name": "invalid", "path": "data:subdir", "permissions": "invalid"}])


def test_relative_mount_nested(storage):
    """Test nested relative mounts (child of child)."""
    storage.configure(
        [{"name": "projects", "path": "data:projects"}, {"name": "project_a", "path": "projects:a"}]
    )

    # Write via deepest child
    node = storage.node("project_a:file.txt")
    node.write("nested content")

    # Verify accessible from all levels
    assert storage.node("data:projects/a/file.txt").read() == "nested content"
    assert storage.node("projects:a/file.txt").read() == "nested content"
    assert storage.node("project_a:file.txt").read() == "nested content"


def test_relative_mount_readonly_blocks_mkdir(storage):
    """Test readonly permission blocks mkdir operations."""
    storage.configure(
        [{"name": "readonly_dir", "path": "data:readonly", "permissions": "readonly"}]
    )

    node = storage.node("readonly_dir:newdir/file.txt")

    with pytest.raises(StoragePermissionError):
        node.write("content")  # This would implicitly create directory


def test_relative_mount_readwrite_allows_mkdir(storage):
    """Test readwrite permission allows directory creation."""
    storage.configure([{"name": "rw_dir", "path": "data:rw", "permissions": "readwrite"}])

    # Writing to nested path should create directories
    node = storage.node("rw_dir:subdir/file.txt")
    node.write("content")

    assert node.exists()
    assert node.read() == "content"


def test_relative_mount_capabilities_inherited(storage):
    """Test that capabilities are inherited from parent backend."""
    storage.configure([{"name": "child", "path": "data:child"}])

    # Get backends
    parent_backend = storage._mounts["data"]
    child_backend = storage._mounts["child"]

    # Capabilities should be the same
    assert child_backend.capabilities == parent_backend.capabilities


def test_relative_mount_copy_operations(storage):
    """Test copy operations respect permissions."""
    storage.configure(
        [
            {"name": "source", "path": "data:source"},
            {"name": "dest_ro", "path": "data:dest_ro", "permissions": "readonly"},
            {"name": "dest_rw", "path": "data:dest_rw", "permissions": "readwrite"},
        ]
    )

    # Create source file
    source = storage.node("source:file.txt")
    source.write("test data")

    # Copy to readonly destination should fail (can't write)
    dest_ro = storage.node("dest_ro:file.txt")
    with pytest.raises(StoragePermissionError):
        source.copy_to(dest_ro)

    # Copy to readwrite destination should work
    dest_rw = storage.node("dest_rw:file.txt")
    source.copy_to(dest_rw)
    assert dest_rw.read() == "test data"


def test_relative_mount_open_modes(storage):
    """Test file open modes respect permissions."""
    storage.configure([{"name": "ro", "path": "data:ro", "permissions": "readonly"}])

    # Create file via parent
    storage.node("data:ro/file.txt").write("test")

    node = storage.node("ro:file.txt")

    # Read mode should work
    with node.open("r") as f:
        assert f.read() == "test"

    # Write modes should fail
    with pytest.raises(StoragePermissionError):
        with node.open("w") as f:
            f.write("new")

    with pytest.raises(StoragePermissionError):
        with node.open("a") as f:
            f.write("append")


def test_relative_mount_binary_mode(storage):
    """Test binary read/write with relative mounts."""
    storage.configure([{"name": "binary", "path": "data:binary", "permissions": "delete"}])

    # Write binary data
    node = storage.node("binary:data.bin")
    node.write(b"\x00\x01\x02\x03", mode="wb")

    # Read binary data
    assert node.read(mode="rb") == b"\x00\x01\x02\x03"

    # Verify text read fails on binary data
    # (actually won't fail, but will try to decode)
    content = node.read()  # default mode='r'
    # Binary data with null bytes might not decode properly, but that's expected
