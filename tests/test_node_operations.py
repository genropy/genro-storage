"""Tests for StorageNode operations (copy, move, delete, mkdir)."""

import os
import pytest


class TestStorageNodeDelete:
    """Test StorageNode.delete() method."""
    
    def test_delete_removes_file(self, configured_storage, temp_dir):
        """delete() removes existing file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:file.txt')
        assert node.exists
        
        node.delete()
        
        assert not node.exists
        assert not os.path.exists(file_path)
    
    def test_delete_removes_empty_directory(self, configured_storage, temp_dir):
        """delete() removes empty directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        assert node.exists
        
        node.delete()
        
        assert not node.exists
        assert not os.path.exists(dir_path)
    
    def test_delete_removes_directory_recursively(self, configured_storage, temp_dir):
        """delete() removes directory with contents recursively."""
        dir_path = os.path.join(temp_dir, 'mydir')
        subdir_path = os.path.join(dir_path, 'subdir')
        os.makedirs(subdir_path)
        
        with open(os.path.join(dir_path, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(subdir_path, 'file2.txt'), 'w') as f:
            f.write('content2')
        
        node = configured_storage.node('test:mydir')
        node.delete()
        
        assert not os.path.exists(dir_path)
        assert not os.path.exists(subdir_path)
    
    def test_delete_is_idempotent(self, configured_storage):
        """delete() doesn't raise error if file doesn't exist."""
        node = configured_storage.node('test:nonexistent.txt')
        
        # Should not raise
        node.delete()
        node.delete()  # Second call should also not raise
    
    def test_delete_returns_none(self, configured_storage, temp_dir):
        """delete() returns None."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:file.txt')
        result = node.delete()
        
        assert result is None


class TestStorageNodeCopy:
    """Test StorageNode.copy() method."""
    
    def test_copy_file_to_new_location(self, configured_storage, temp_dir):
        """copy() creates copy of file at new location."""
        # Create source file
        src_path = os.path.join(temp_dir, 'source.txt')
        content = b'File content'
        with open(src_path, 'wb') as f:
            f.write(content)
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:destination.txt')
        
        result = src_node.copy(dest_node)
        
        # Check destination exists
        assert dest_node.exists
        assert dest_node.read_bytes() == content
        
        # Check source still exists
        assert src_node.exists
        
        # Check return value
        assert result.fullpath == dest_node.fullpath
    
    def test_copy_file_to_string_path(self, configured_storage, temp_dir):
        """copy() accepts destination as string path."""
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'wb') as f:
            f.write(b'content')
        
        src_node = configured_storage.node('test:source.txt')
        result = src_node.copy('test:destination.txt')
        
        assert result.exists
        assert result.fullpath == 'test:destination.txt'
    
    def test_copy_overwrites_existing_file(self, configured_storage, temp_dir):
        """copy() overwrites existing destination file."""
        # Create source and destination
        src_path = os.path.join(temp_dir, 'source.txt')
        dest_path = os.path.join(temp_dir, 'dest.txt')
        
        with open(src_path, 'w') as f:
            f.write('new content')
        with open(dest_path, 'w') as f:
            f.write('old content')
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:dest.txt')
        
        src_node.copy(dest_node)
        
        assert dest_node.read_text() == 'new content'
    
    def test_copy_to_directory_uses_same_basename(self, configured_storage, temp_dir):
        """copy() to directory creates file with same basename inside."""
        src_path = os.path.join(temp_dir, 'file.txt')
        dest_dir = os.path.join(temp_dir, 'destination')
        os.makedirs(dest_dir)
        
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:file.txt')
        dest_dir_node = configured_storage.node('test:destination')
        
        result = src_node.copy(dest_dir_node)
        
        # Should create destination/file.txt
        expected_path = os.path.join(dest_dir, 'file.txt')
        assert os.path.exists(expected_path)
        assert result.basename == 'file.txt'
    
    def test_copy_creates_parent_directories(self, configured_storage, temp_dir):
        """copy() creates parent directories if they don't exist."""
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:nested/path/destination.txt')
        
        src_node.copy(dest_node)
        
        dest_path = os.path.join(temp_dir, 'nested', 'path', 'destination.txt')
        assert os.path.exists(dest_path)
    
    def test_copy_directory_recursively(self, configured_storage, temp_dir):
        """copy() copies directory with all contents recursively."""
        # Create source directory structure
        src_dir = os.path.join(temp_dir, 'source')
        subdir = os.path.join(src_dir, 'subdir')
        os.makedirs(subdir)
        
        with open(os.path.join(src_dir, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(subdir, 'file2.txt'), 'w') as f:
            f.write('content2')
        
        src_node = configured_storage.node('test:source')
        dest_node = configured_storage.node('test:destination')
        
        src_node.copy(dest_node)
        
        # Check all files were copied
        dest_dir = os.path.join(temp_dir, 'destination')
        assert os.path.exists(os.path.join(dest_dir, 'file1.txt'))
        assert os.path.exists(os.path.join(dest_dir, 'subdir', 'file2.txt'))
    
    def test_copy_across_different_mounts(self, multi_storage, temp_dir):
        """copy() works across different storage mounts."""
        # Create file in local1
        mount1_path = os.path.join(temp_dir, 'mount1')
        src_path = os.path.join(mount1_path, 'source.txt')
        content = b'Cross-mount content'
        with open(src_path, 'wb') as f:
            f.write(content)
        
        src_node = multi_storage.node('local1:source.txt')
        dest_node = multi_storage.node('local2:destination.txt')
        
        src_node.copy(dest_node)
        
        # Check file exists in local2
        mount2_path = os.path.join(temp_dir, 'mount2')
        dest_path = os.path.join(mount2_path, 'destination.txt')
        assert os.path.exists(dest_path)
        
        with open(dest_path, 'rb') as f:
            assert f.read() == content
    
    def test_copy_preserves_file_content(self, configured_storage, temp_dir):
        """copy() preserves exact file content including binary data."""
        content = bytes(range(256))  # All byte values
        src_path = os.path.join(temp_dir, 'source.bin')
        with open(src_path, 'wb') as f:
            f.write(content)
        
        src_node = configured_storage.node('test:source.bin')
        dest_node = configured_storage.node('test:destination.bin')
        
        src_node.copy(dest_node)
        
        assert dest_node.read_bytes() == content
    
    def test_copy_large_file(self, configured_storage, temp_dir):
        """copy() handles large files efficiently."""
        content = b'X' * 1000000  # 1MB
        src_path = os.path.join(temp_dir, 'large.bin')
        with open(src_path, 'wb') as f:
            f.write(content)
        
        src_node = configured_storage.node('test:large.bin')
        dest_node = configured_storage.node('test:large_copy.bin')
        
        src_node.copy(dest_node)
        
        assert dest_node.size == 1000000
    
    def test_copy_returns_destination_node(self, configured_storage, temp_dir):
        """copy() returns the destination StorageNode."""
        from genro_storage import StorageNode
        
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:source.txt')
        result = src_node.copy('test:destination.txt')
        
        assert isinstance(result, StorageNode)
        assert result.fullpath == 'test:destination.txt'


class TestStorageNodeMove:
    """Test StorageNode.move() method."""
    
    def test_move_file_to_new_location(self, configured_storage, temp_dir):
        """move() moves file to new location."""
        src_path = os.path.join(temp_dir, 'source.txt')
        content = b'File content'
        with open(src_path, 'wb') as f:
            f.write(content)
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:destination.txt')
        
        result = src_node.move(dest_node)
        
        # Check destination exists
        assert dest_node.exists
        assert dest_node.read_bytes() == content
        
        # Check source no longer exists
        assert not os.path.exists(src_path)
        
        # Check return value
        assert result.fullpath == dest_node.fullpath
    
    def test_move_updates_current_node(self, configured_storage, temp_dir):
        """move() updates the current node to point to new location."""
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:source.txt')
        original_path = node.fullpath
        
        node.move('test:destination.txt')
        
        # Node should now point to destination
        assert node.fullpath == 'test:destination.txt'
        assert node.exists
    
    def test_move_file_to_string_path(self, configured_storage, temp_dir):
        """move() accepts destination as string path."""
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:source.txt')
        result = src_node.move('test:destination.txt')
        
        assert result.exists
        assert result.fullpath == 'test:destination.txt'
        assert not os.path.exists(src_path)
    
    def test_move_overwrites_existing_file(self, configured_storage, temp_dir):
        """move() overwrites existing destination file."""
        src_path = os.path.join(temp_dir, 'source.txt')
        dest_path = os.path.join(temp_dir, 'dest.txt')
        
        with open(src_path, 'w') as f:
            f.write('new content')
        with open(dest_path, 'w') as f:
            f.write('old content')
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:dest.txt')
        
        src_node.move(dest_node)
        
        assert dest_node.read_text() == 'new content'
        assert not os.path.exists(src_path)
    
    def test_move_to_directory_uses_same_basename(self, configured_storage, temp_dir):
        """move() to directory moves file with same basename inside."""
        src_path = os.path.join(temp_dir, 'file.txt')
        dest_dir = os.path.join(temp_dir, 'destination')
        os.makedirs(dest_dir)
        
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:file.txt')
        dest_dir_node = configured_storage.node('test:destination')
        
        result = src_node.move(dest_dir_node)
        
        # Should create destination/file.txt
        expected_path = os.path.join(dest_dir, 'file.txt')
        assert os.path.exists(expected_path)
        assert not os.path.exists(src_path)
    
    def test_move_creates_parent_directories(self, configured_storage, temp_dir):
        """move() creates parent directories if they don't exist."""
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:nested/path/destination.txt')
        
        src_node.move(dest_node)
        
        dest_path = os.path.join(temp_dir, 'nested', 'path', 'destination.txt')
        assert os.path.exists(dest_path)
        assert not os.path.exists(src_path)
    
    def test_move_directory_recursively(self, configured_storage, temp_dir):
        """move() moves directory with all contents recursively."""
        src_dir = os.path.join(temp_dir, 'source')
        subdir = os.path.join(src_dir, 'subdir')
        os.makedirs(subdir)
        
        with open(os.path.join(src_dir, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(subdir, 'file2.txt'), 'w') as f:
            f.write('content2')
        
        src_node = configured_storage.node('test:source')
        dest_node = configured_storage.node('test:destination')
        
        src_node.move(dest_node)
        
        # Check all files were moved
        dest_dir = os.path.join(temp_dir, 'destination')
        assert os.path.exists(os.path.join(dest_dir, 'file1.txt'))
        assert os.path.exists(os.path.join(dest_dir, 'subdir', 'file2.txt'))
        
        # Check source no longer exists
        assert not os.path.exists(src_dir)
    
    def test_move_across_different_mounts(self, multi_storage, temp_dir):
        """move() works across different storage mounts (copy + delete)."""
        mount1_path = os.path.join(temp_dir, 'mount1')
        src_path = os.path.join(mount1_path, 'source.txt')
        content = b'Cross-mount content'
        with open(src_path, 'wb') as f:
            f.write(content)
        
        src_node = multi_storage.node('local1:source.txt')
        dest_node = multi_storage.node('local2:destination.txt')
        
        src_node.move(dest_node)
        
        # Check file exists in local2
        mount2_path = os.path.join(temp_dir, 'mount2')
        dest_path = os.path.join(mount2_path, 'destination.txt')
        assert os.path.exists(dest_path)
        
        # Check file deleted from local1
        assert not os.path.exists(src_path)
    
    def test_move_within_same_backend_is_efficient(self, configured_storage, temp_dir):
        """move() uses efficient rename when within same backend."""
        # This is more of a behavioral test - we can't directly test
        # that it uses rename vs copy+delete, but we can verify it works
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:source.txt')
        dest_node = configured_storage.node('test:subdir/destination.txt')
        
        # Create parent dir
        os.makedirs(os.path.join(temp_dir, 'subdir'))
        
        src_node.move(dest_node)
        
        dest_path = os.path.join(temp_dir, 'subdir', 'destination.txt')
        assert os.path.exists(dest_path)
        assert not os.path.exists(src_path)
    
    def test_move_returns_destination_node(self, configured_storage, temp_dir):
        """move() returns the destination StorageNode."""
        from genro_storage import StorageNode
        
        src_path = os.path.join(temp_dir, 'source.txt')
        with open(src_path, 'w') as f:
            f.write('content')
        
        src_node = configured_storage.node('test:source.txt')
        result = src_node.move('test:destination.txt')
        
        assert isinstance(result, StorageNode)
        assert result.fullpath == 'test:destination.txt'


class TestStorageNodeMkdir:
    """Test StorageNode.mkdir() method."""
    
    def test_mkdir_creates_directory(self, configured_storage, temp_dir):
        """mkdir() creates new directory."""
        node = configured_storage.node('test:newdir')
        node.mkdir()
        
        dir_path = os.path.join(temp_dir, 'newdir')
        assert os.path.exists(dir_path)
        assert os.path.isdir(dir_path)
    
    def test_mkdir_raises_if_already_exists(self, configured_storage, temp_dir):
        """mkdir() raises FileExistsError if directory already exists."""
        dir_path = os.path.join(temp_dir, 'existing')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:existing')
        
        with pytest.raises(FileExistsError):
            node.mkdir()
    
    def test_mkdir_with_exist_ok_true(self, configured_storage, temp_dir):
        """mkdir(exist_ok=True) doesn't raise if directory exists."""
        dir_path = os.path.join(temp_dir, 'existing')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:existing')
        
        # Should not raise
        node.mkdir(exist_ok=True)
    
    def test_mkdir_raises_if_parent_missing(self, configured_storage):
        """mkdir() raises FileNotFoundError if parent doesn't exist."""
        node = configured_storage.node('test:parent/child')
        
        with pytest.raises(FileNotFoundError):
            node.mkdir()
    
    def test_mkdir_with_parents_creates_intermediate_directories(self, configured_storage, temp_dir):
        """mkdir(parents=True) creates all intermediate directories."""
        node = configured_storage.node('test:level1/level2/level3')
        node.mkdir(parents=True)
        
        dir_path = os.path.join(temp_dir, 'level1', 'level2', 'level3')
        assert os.path.exists(dir_path)
        assert os.path.isdir(dir_path)
    
    def test_mkdir_with_parents_and_exist_ok(self, configured_storage, temp_dir):
        """mkdir(parents=True, exist_ok=True) is fully idempotent."""
        node = configured_storage.node('test:level1/level2')
        
        # Create first time
        node.mkdir(parents=True, exist_ok=True)
        
        # Create again - should not raise
        node.mkdir(parents=True, exist_ok=True)
        
        dir_path = os.path.join(temp_dir, 'level1', 'level2')
        assert os.path.exists(dir_path)
    
    def test_mkdir_creates_nested_structure(self, configured_storage, temp_dir):
        """mkdir(parents=True) creates deeply nested structure."""
        node = configured_storage.node('test:a/b/c/d/e/f')
        node.mkdir(parents=True)
        
        dir_path = os.path.join(temp_dir, 'a', 'b', 'c', 'd', 'e', 'f')
        assert os.path.exists(dir_path)
    
    def test_mkdir_returns_none(self, configured_storage):
        """mkdir() returns None."""
        node = configured_storage.node('test:newdir')
        result = node.mkdir()
        
        assert result is None
    
    def test_mkdir_default_parameters(self, configured_storage, temp_dir):
        """mkdir() defaults: parents=False, exist_ok=False."""
        # This should fail because parent doesn't exist
        node = configured_storage.node('test:parent/child')
        
        with pytest.raises(FileNotFoundError):
            node.mkdir()  # No parents, no exist_ok
