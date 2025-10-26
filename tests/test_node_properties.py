"""Tests for StorageNode properties."""

import os
import time
import pytest


class TestStorageNodeFullpath:
    """Test StorageNode.fullpath property."""
    
    def test_fullpath_includes_mount_and_path(self, configured_storage):
        """fullpath returns 'mount:path' format."""
        node = configured_storage.node('test:documents/file.txt')
        assert node.fullpath == 'test:documents/file.txt'
    
    def test_fullpath_for_root(self, configured_storage):
        """fullpath for mount root shows 'mount:'."""
        node = configured_storage.node('test')
        assert node.fullpath == 'test:'
    
    def test_fullpath_is_normalized(self, configured_storage):
        """fullpath shows normalized path."""
        node = configured_storage.node('test://path//to///file.txt/')
        assert node.fullpath == 'test:path/to/file.txt'


class TestStorageNodeExists:
    """Test StorageNode.exists property."""
    
    def test_exists_false_for_nonexistent_file(self, configured_storage):
        """exists returns False for file that doesn't exist."""
        node = configured_storage.node('test:nonexistent.txt')
        assert node.exists is False
    
    def test_exists_true_for_existing_file(self, configured_storage, temp_dir):
        """exists returns True for existing file."""
        file_path = os.path.join(temp_dir, 'existing.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:existing.txt')
        assert node.exists is True
    
    def test_exists_true_for_existing_directory(self, configured_storage, temp_dir):
        """exists returns True for existing directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        assert node.exists is True
    
    def test_exists_false_for_deleted_file(self, configured_storage, temp_dir):
        """exists returns False after file is deleted."""
        file_path = os.path.join(temp_dir, 'temp.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:temp.txt')
        assert node.exists is True
        
        os.remove(file_path)
        assert node.exists is False


class TestStorageNodeIsfile:
    """Test StorageNode.isfile property."""
    
    def test_isfile_true_for_file(self, configured_storage, temp_dir):
        """isfile returns True for regular file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:file.txt')
        assert node.isfile is True
    
    def test_isfile_false_for_directory(self, configured_storage, temp_dir):
        """isfile returns False for directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        assert node.isfile is False
    
    def test_isfile_false_for_nonexistent(self, configured_storage):
        """isfile returns False for nonexistent path."""
        node = configured_storage.node('test:nonexistent.txt')
        assert node.isfile is False


class TestStorageNodeIsdir:
    """Test StorageNode.isdir property."""
    
    def test_isdir_true_for_directory(self, configured_storage, temp_dir):
        """isdir returns True for directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        assert node.isdir is True
    
    def test_isdir_false_for_file(self, configured_storage, temp_dir):
        """isdir returns False for file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:file.txt')
        assert node.isdir is False
    
    def test_isdir_false_for_nonexistent(self, configured_storage):
        """isdir returns False for nonexistent path."""
        node = configured_storage.node('test:nonexistent')
        assert node.isdir is False
    
    def test_isdir_true_for_mount_root(self, configured_storage):
        """isdir returns True for mount root."""
        node = configured_storage.node('test:')
        assert node.isdir is True


class TestStorageNodeSize:
    """Test StorageNode.size property."""
    
    def test_size_returns_file_size_in_bytes(self, configured_storage, temp_dir):
        """size returns correct file size in bytes."""
        content = b'Hello World'  # 11 bytes
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        assert node.size == 11
    
    def test_size_for_empty_file(self, configured_storage, temp_dir):
        """size returns 0 for empty file."""
        file_path = os.path.join(temp_dir, 'empty.txt')
        open(file_path, 'w').close()
        
        node = configured_storage.node('test:empty.txt')
        assert node.size == 0
    
    def test_size_for_large_file(self, configured_storage, temp_dir):
        """size returns correct size for large file."""
        content = b'X' * 10000  # 10KB
        file_path = os.path.join(temp_dir, 'large.bin')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:large.bin')
        assert node.size == 10000
    
    def test_size_raises_for_nonexistent_file(self, configured_storage):
        """size raises exception for nonexistent file."""
        node = configured_storage.node('test:nonexistent.txt')
        with pytest.raises(Exception):
            _ = node.size
    
    def test_size_raises_for_directory(self, configured_storage, temp_dir):
        """size raises exception for directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        with pytest.raises(Exception):
            _ = node.size


class TestStorageNodeMtime:
    """Test StorageNode.mtime property."""
    
    def test_mtime_returns_unix_timestamp(self, configured_storage, temp_dir):
        """mtime returns Unix timestamp as float."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        node = configured_storage.node('test:file.txt')
        mtime = node.mtime
        
        assert isinstance(mtime, float)
        assert mtime > 0
    
    def test_mtime_reflects_modification(self, configured_storage, temp_dir):
        """mtime changes when file is modified."""
        file_path = os.path.join(temp_dir, 'file.txt')
        
        # Create file
        with open(file_path, 'w') as f:
            f.write('original')
        
        node = configured_storage.node('test:file.txt')
        mtime1 = node.mtime
        
        # Wait a bit and modify
        time.sleep(0.01)
        with open(file_path, 'w') as f:
            f.write('modified')
        
        mtime2 = node.mtime
        assert mtime2 >= mtime1
    
    def test_mtime_for_directory(self, configured_storage, temp_dir):
        """mtime returns timestamp for directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        mtime = node.mtime
        
        assert isinstance(mtime, float)
        assert mtime > 0
    
    def test_mtime_raises_for_nonexistent(self, configured_storage):
        """mtime raises exception for nonexistent path."""
        node = configured_storage.node('test:nonexistent.txt')
        with pytest.raises(Exception):
            _ = node.mtime


class TestStorageNodeBasename:
    """Test StorageNode.basename property."""
    
    def test_basename_returns_filename_with_extension(self, configured_storage):
        """basename returns filename with extension."""
        node = configured_storage.node('test:path/to/report.pdf')
        assert node.basename == 'report.pdf'
    
    def test_basename_for_file_without_extension(self, configured_storage):
        """basename returns filename without extension."""
        node = configured_storage.node('test:path/to/README')
        assert node.basename == 'README'
    
    def test_basename_for_hidden_file(self, configured_storage):
        """basename returns hidden filename."""
        node = configured_storage.node('test:.gitignore')
        assert node.basename == '.gitignore'
    
    def test_basename_for_directory(self, configured_storage):
        """basename returns directory name."""
        node = configured_storage.node('test:path/to/mydir')
        assert node.basename == 'mydir'
    
    def test_basename_for_root(self, configured_storage):
        """basename returns empty string for root."""
        node = configured_storage.node('test:')
        assert node.basename == ''


class TestStorageNodeStem:
    """Test StorageNode.stem property."""
    
    def test_stem_returns_filename_without_extension(self, configured_storage):
        """stem returns filename without extension."""
        node = configured_storage.node('test:report.pdf')
        assert node.stem == 'report'
    
    def test_stem_for_multiple_extensions(self, configured_storage):
        """stem removes only last extension."""
        node = configured_storage.node('test:archive.tar.gz')
        assert node.stem == 'archive.tar'
    
    def test_stem_for_file_without_extension(self, configured_storage):
        """stem returns full filename if no extension."""
        node = configured_storage.node('test:README')
        assert node.stem == 'README'
    
    def test_stem_for_hidden_file_with_extension(self, configured_storage):
        """stem handles hidden files with extensions."""
        node = configured_storage.node('test:.config.yaml')
        assert node.stem == '.config'


class TestStorageNodeSuffix:
    """Test StorageNode.suffix property."""
    
    def test_suffix_returns_extension_with_dot(self, configured_storage):
        """suffix returns extension including dot."""
        node = configured_storage.node('test:report.pdf')
        assert node.suffix == '.pdf'
    
    def test_suffix_for_multiple_extensions(self, configured_storage):
        """suffix returns only last extension."""
        node = configured_storage.node('test:archive.tar.gz')
        assert node.suffix == '.gz'
    
    def test_suffix_empty_for_no_extension(self, configured_storage):
        """suffix returns empty string if no extension."""
        node = configured_storage.node('test:README')
        assert node.suffix == ''
    
    def test_suffix_for_hidden_file(self, configured_storage):
        """suffix empty for hidden file without extension."""
        node = configured_storage.node('test:.gitignore')
        assert node.suffix == ''


class TestStorageNodeParent:
    """Test StorageNode.parent property."""
    
    def test_parent_returns_parent_directory_node(self, configured_storage):
        """parent returns StorageNode of parent directory."""
        node = configured_storage.node('test:documents/reports/q4.pdf')
        parent = node.parent
        
        assert parent.fullpath == 'test:documents/reports'
    
    def test_parent_of_root_file(self, configured_storage):
        """parent of root-level file is mount root."""
        node = configured_storage.node('test:file.txt')
        parent = node.parent
        
        assert parent.fullpath == 'test:'
    
    def test_parent_of_mount_root(self, configured_storage):
        """parent of mount root is itself."""
        node = configured_storage.node('test:')
        parent = node.parent
        
        assert parent.fullpath == 'test:'
    
    def test_parent_chain(self, configured_storage):
        """parent can be chained to navigate up."""
        node = configured_storage.node('test:a/b/c/file.txt')
        
        assert node.parent.fullpath == 'test:a/b/c'
        assert node.parent.parent.fullpath == 'test:a/b'
        assert node.parent.parent.parent.fullpath == 'test:a'
        assert node.parent.parent.parent.parent.fullpath == 'test:'
    
    def test_parent_is_storage_node(self, configured_storage):
        """parent returns StorageNode instance."""
        from genro_storage import StorageNode
        
        node = configured_storage.node('test:path/file.txt')
        parent = node.parent
        
        assert isinstance(parent, StorageNode)
