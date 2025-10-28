"""Tests for LocalStorage backend and StorageNode integration."""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from genro_storage import StorageManager, StorageNotFoundError, StorageConfigError


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
    mgr.configure([{
        'name': 'test',
        'type': 'local',
        'path': temp_dir
    }])
    return mgr


class TestStorageManager:
    """Test StorageManager configuration and mount management."""
    
    def test_configure_from_list(self, temp_dir):
        """Test configuring from Python list."""
        storage = StorageManager()
        storage.configure([
            {'name': 'test', 'type': 'local', 'path': temp_dir}
        ])
        
        assert storage.has_mount('test')
        assert 'test' in storage.get_mount_names()
    
    def test_configure_missing_name(self):
        """Test error when mount name is missing."""
        storage = StorageManager()
        
        with pytest.raises(StorageConfigError, match="missing required field: 'name'"):
            storage.configure([{'type': 'local', 'path': '/tmp'}])
    
    def test_configure_missing_type(self):
        """Test error when type is missing."""
        storage = StorageManager()
        
        with pytest.raises(StorageConfigError, match="missing required field: 'type'"):
            storage.configure([{'name': 'test', 'path': '/tmp'}])
    
    def test_configure_missing_local_path(self):
        """Test error when local storage path is missing."""
        storage = StorageManager()
        
        with pytest.raises(StorageConfigError, match="missing required field: 'path'"):
            storage.configure([{'name': 'test', 'type': 'local'}])
    
    def test_configure_unknown_type(self):
        """Test error for unknown storage type."""
        storage = StorageManager()
        
        with pytest.raises(StorageConfigError, match="Unknown storage type"):
            storage.configure([{'name': 'test', 'type': 'unknown'}])
    
    def test_configure_replace_mount(self, temp_dir):
        """Test that configuring same mount name replaces it."""
        storage = StorageManager()
        storage.configure([{'name': 'test', 'type': 'local', 'path': temp_dir}])
        
        # Configure again with same name
        storage.configure([{'name': 'test', 'type': 'local', 'path': temp_dir}])
        
        # Should still have only one mount
        assert len(storage.get_mount_names()) == 1
    
    def test_node_mount_not_found(self, storage):
        """Test error when accessing non-existent mount."""
        with pytest.raises(StorageNotFoundError, match="Mount point 'missing' not found"):
            storage.node('missing:file.txt')


class TestFileOperations:
    """Test basic file operations."""
    
    def test_write_and_read_text(self, storage):
        """Test writing and reading text files."""
        node = storage.node('test:file.txt')
        
        # Write
        node.write_text("Hello World")
        
        # Read
        content = node.read_text()
        assert content == "Hello World"
    
    def test_write_and_read_bytes(self, storage):
        """Test writing and reading binary files."""
        node = storage.node('test:file.bin')
        data = b'\x00\x01\x02\x03\x04'
        
        # Write
        node.write_bytes(data)
        
        # Read
        read_data = node.read_bytes()
        assert read_data == data
    
    def test_file_exists(self, storage):
        """Test checking if file exists."""
        node = storage.node('test:file.txt')
        
        # Initially doesn't exist
        assert not node.exists
        
        # After writing, exists
        node.write_text("content")
        assert node.exists
    
    def test_is_file_is_dir(self, storage):
        """Test isfile and isdir properties."""
        file_node = storage.node('test:file.txt')
        dir_node = storage.node('test:directory')
        
        # Create file
        file_node.write_text("content")
        assert file_node.isfile
        assert not file_node.isdir
        
        # Create directory
        dir_node.mkdir()
        assert dir_node.isdir
        assert not dir_node.isfile
    
    def test_file_size(self, storage):
        """Test getting file size."""
        node = storage.node('test:file.txt')
        content = "Hello World"
        
        node.write_text(content)
        
        assert node.size == len(content.encode('utf-8'))
    
    def test_file_mtime(self, storage):
        """Test getting modification time."""
        node = storage.node('test:file.txt')

        before = datetime.now().timestamp()
        node.write_text("content")

        mtime = node.mtime
        # Allow small timing tolerance (filesystem may round timestamps)
        assert abs(mtime - before) < 2  # Within 2 seconds is reasonable
    
    def test_file_path_properties(self, storage):
        """Test path-related properties."""
        node = storage.node('test:documents/report.pdf')
        
        assert node.fullpath == 'test:documents/report.pdf'
        assert node.basename == 'report.pdf'
        assert node.stem == 'report'
        assert node.suffix == '.pdf'
    
    def test_file_open_context_manager(self, storage):
        """Test using open() with context manager."""
        node = storage.node('test:file.txt')
        
        # Write using context manager
        with node.open('w') as f:
            f.write("Line 1\n")
            f.write("Line 2\n")
        
        # Read using context manager
        with node.open('r') as f:
            content = f.read()
        
        assert content == "Line 1\nLine 2\n"
    
    def test_file_delete(self, storage):
        """Test deleting a file."""
        node = storage.node('test:file.txt')
        
        # Create file
        node.write_text("content")
        assert node.exists
        
        # Delete
        node.delete()
        assert not node.exists
        
        # Delete again (idempotent)
        node.delete()  # Should not raise error


class TestDirectoryOperations:
    """Test directory operations."""
    
    def test_mkdir(self, storage):
        """Test creating a directory."""
        node = storage.node('test:mydir')
        
        assert not node.exists
        
        node.mkdir()
        
        assert node.exists
        assert node.isdir
    
    def test_mkdir_parents(self, storage):
        """Test creating nested directories."""
        node = storage.node('test:a/b/c/d')
        
        node.mkdir(parents=True)
        
        assert node.exists
        assert node.isdir
    
    def test_mkdir_exist_ok(self, storage):
        """Test mkdir with exist_ok flag."""
        node = storage.node('test:mydir')
        
        node.mkdir()
        
        # Should raise error without exist_ok
        with pytest.raises(FileExistsError):
            node.mkdir(exist_ok=False)
        
        # Should not raise with exist_ok
        node.mkdir(exist_ok=True)
    
    def test_list_directory(self, storage):
        """Test listing directory contents."""
        # Create directory with files
        dir_node = storage.node('test:mydir')
        dir_node.mkdir()

        # Create some files
        dir_node.child('file1.txt').write_text("content1")
        dir_node.child('file2.txt').write_text("content2")
        dir_node.child('subdir').mkdir()

        # List children
        children = dir_node.children()
        names = [c.basename for c in children]

        assert len(children) == 3
        assert 'file1.txt' in names
        assert 'file2.txt' in names
        assert 'subdir' in names

    def test_child_method(self, storage):
        """Test child() with single path and varargs."""
        parent = storage.node('test:documents')
        parent.mkdir()

        # Single component
        child = parent.child('report.pdf')
        child.write_text("content")

        assert child.fullpath == 'test:documents/report.pdf'
        assert child.exists

        # Single path with slashes
        child2 = parent.child('2024/reports/q4.pdf')
        assert child2.fullpath == 'test:documents/2024/reports/q4.pdf'

        # Varargs
        child3 = parent.child('2024', 'reports', 'q4.pdf')
        assert child3.fullpath == 'test:documents/2024/reports/q4.pdf'
    
    def test_parent_property(self, storage):
        """Test parent property."""
        node = storage.node('test:documents/reports/file.pdf')
        
        parent = node.parent
        assert parent.fullpath == 'test:documents/reports'
        
        grandparent = parent.parent
        assert grandparent.fullpath == 'test:documents'
    
    def test_delete_directory(self, storage):
        """Test deleting a directory recursively."""
        dir_node = storage.node('test:mydir')
        dir_node.mkdir()

        # Create files inside
        dir_node.child('file1.txt').write_text("content")
        dir_node.child('subdir').mkdir()
        dir_node.child('subdir', 'file2.txt').write_text("content")

        # Delete recursively
        dir_node.delete()

        assert not dir_node.exists


class TestCopyMove:
    """Test copy and move operations."""
    
    def test_copy_file(self, storage):
        """Test copying a file."""
        src = storage.node('test:source.txt')
        src.write_text("Hello World")
        
        dest = storage.node('test:destination.txt')
        
        # Copy
        result = src.copy(dest)
        
        # Both should exist
        assert src.exists
        assert dest.exists
        assert result.fullpath == dest.fullpath
        
        # Content should be the same
        assert dest.read_text() == "Hello World"
    
    def test_copy_with_string_dest(self, storage):
        """Test copying with string destination."""
        src = storage.node('test:source.txt')
        src.write_text("content")
        
        # Copy using string
        dest = src.copy('test:destination.txt')
        
        assert dest.exists
        assert dest.fullpath == 'test:destination.txt'
    
    def test_move_file(self, storage):
        """Test moving a file."""
        src = storage.node('test:source.txt')
        src.write_text("Hello World")
        
        dest = storage.node('test:destination.txt')
        
        # Move
        result = src.move(dest)
        
        # Source should not exist, dest should
        assert not storage.node('test:source.txt').exists
        assert dest.exists
        assert result.fullpath == dest.fullpath
        
        # Content preserved
        assert dest.read_text() == "Hello World"
    
    def test_move_updates_self(self, storage):
        """Test that move updates the node itself."""
        node = storage.node('test:old.txt')
        node.write_text("content")
        
        original_id = id(node)
        
        # Move
        node.move('test:new.txt')
        
        # Same object, updated path
        assert id(node) == original_id
        assert node.fullpath == 'test:new.txt'
        assert node.exists
    
    def test_copy_directory(self, storage):
        """Test copying a directory recursively."""
        # Create source directory with contents
        src = storage.node('test:src_dir')
        src.mkdir()
        src.child('file1.txt').write_text("content1")
        src.child('subdir').mkdir()
        src.child('subdir', 'file2.txt').write_text("content2")

        # Copy
        dest = storage.node('test:dest_dir')
        src.copy(dest)

        # Check structure copied
        assert dest.exists
        assert dest.child('file1.txt').exists
        assert dest.child('subdir').exists
        assert dest.child('subdir', 'file2.txt').exists

        # Check content
        assert dest.child('file1.txt').read_text() == "content1"
        assert dest.child('subdir', 'file2.txt').read_text() == "content2"


class TestPathNormalization:
    """Test path handling and normalization."""
    
    def test_path_with_slashes(self, storage):
        """Test various path formats."""
        # These should all work
        n1 = storage.node('test:a/b/c')
        n2 = storage.node('test', 'a', 'b', 'c')
        n3 = storage.node('test:a', 'b', 'c')
        
        assert n1.fullpath == 'test:a/b/c'
        assert n2.fullpath == 'test:a/b/c'
        assert n3.fullpath == 'test:a/b/c'
    
    def test_path_parent_traversal_blocked(self, storage):
        """Test that .. in paths is blocked."""
        with pytest.raises(ValueError, match="Parent directory traversal"):
            storage.node('test:documents/../etc/passwd')
    
    def test_root_of_mount(self, storage):
        """Test accessing root of mount."""
        root = storage.node('test:')
        
        assert root.fullpath == 'test:'
        assert root.isdir


class TestEncodings:
    """Test different text encodings."""
    
    def test_utf8_encoding(self, storage):
        """Test UTF-8 encoding (default)."""
        node = storage.node('test:utf8.txt')
        content = "Hello 世界 🌍"
        
        node.write_text(content)
        assert node.read_text() == content
    
    def test_latin1_encoding(self, storage):
        """Test Latin-1 encoding."""
        node = storage.node('test:latin1.txt')
        content = "Héllo Wørld"
        
        node.write_text(content, encoding='latin-1')
        assert node.read_text(encoding='latin-1') == content


class TestEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_read_nonexistent_file(self, storage):
        """Test reading a file that doesn't exist."""
        node = storage.node('test:missing.txt')
        
        with pytest.raises(FileNotFoundError):
            node.read_text()
    
    def test_size_of_nonexistent_file(self, storage):
        """Test getting size of nonexistent file."""
        node = storage.node('test:missing.txt')
        
        with pytest.raises(FileNotFoundError):
            _ = node.size
    
    def test_size_of_directory(self, storage):
        """Test getting size of directory (should error)."""
        node = storage.node('test:mydir')
        node.mkdir()
        
        with pytest.raises(ValueError, match="directory"):
            _ = node.size
    
    def test_empty_file(self, storage):
        """Test working with empty files."""
        node = storage.node('test:empty.txt')
        
        node.write_text("")
        assert node.exists
        assert node.size == 0
        assert node.read_text() == ""
    
    def test_nested_directory_creation(self, storage):
        """Test creating deeply nested directories."""
        deep = storage.node('test:a/b/c/d/e/f/g/h')
        deep.mkdir(parents=True)
        
        assert deep.exists
        assert deep.isdir


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
