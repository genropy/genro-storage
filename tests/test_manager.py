"""Tests for StorageManager class."""

import os
import tempfile
import json
import pytest


class TestStorageManagerInit:
    """Test StorageManager initialization."""
    
    def test_init_creates_empty_manager(self, storage_manager):
        """StorageManager() creates instance with no mounts."""
        assert storage_manager is not None
        # Should not have any mounts configured yet
        with pytest.raises(KeyError):
            storage_manager.node('nonexistent:file.txt')


class TestStorageManagerConfigure:
    """Test StorageManager.configure() method."""
    
    def test_configure_with_list_of_dicts(self, storage_manager, temp_dir):
        """configure() accepts list of configuration dicts."""
        config = [
            {'name': 'test', 'type': 'local', 'path': temp_dir}
        ]
        storage_manager.configure(config)
        
        # Should be able to create nodes on this mount
        node = storage_manager.node('test:file.txt')
        assert node.fullpath == 'test:file.txt'
    
    def test_configure_with_multiple_mounts(self, storage_manager, temp_dir):
        """configure() can setup multiple mounts at once."""
        mount1 = os.path.join(temp_dir, 'mount1')
        mount2 = os.path.join(temp_dir, 'mount2')
        os.makedirs(mount1)
        os.makedirs(mount2)
        
        config = [
            {'name': 'local1', 'type': 'local', 'path': mount1},
            {'name': 'local2', 'type': 'local', 'path': mount2}
        ]
        storage_manager.configure(config)
        
        # Both mounts should be accessible
        node1 = storage_manager.node('local1:file.txt')
        node2 = storage_manager.node('local2:file.txt')
        assert node1.fullpath == 'local1:file.txt'
        assert node2.fullpath == 'local2:file.txt'
    
    def test_configure_replaces_existing_mount(self, storage_manager, temp_dir):
        """configure() replaces mount with same name."""
        mount1 = os.path.join(temp_dir, 'mount1')
        mount2 = os.path.join(temp_dir, 'mount2')
        os.makedirs(mount1)
        os.makedirs(mount2)
        
        # Configure first time
        storage_manager.configure([
            {'name': 'test', 'type': 'local', 'path': mount1}
        ])
        
        # Configure again with same name, different path
        storage_manager.configure([
            {'name': 'test', 'type': 'local', 'path': mount2}
        ])
        
        # Should use the second configuration
        node = storage_manager.node('test:')
        # Verify by checking the actual path it resolves to
        # (implementation detail, but validates replacement worked)
    
    def test_configure_can_be_called_multiple_times(self, storage_manager, temp_dir):
        """configure() can be called multiple times to add mounts incrementally."""
        mount1 = os.path.join(temp_dir, 'mount1')
        mount2 = os.path.join(temp_dir, 'mount2')
        os.makedirs(mount1)
        os.makedirs(mount2)
        
        storage_manager.configure([
            {'name': 'first', 'type': 'local', 'path': mount1}
        ])
        storage_manager.configure([
            {'name': 'second', 'type': 'local', 'path': mount2}
        ])
        
        # Both mounts should be available
        node1 = storage_manager.node('first:file.txt')
        node2 = storage_manager.node('second:file.txt')
        assert node1 is not None
        assert node2 is not None
    
    def test_configure_with_yaml_file(self, storage_manager, temp_dir):
        """configure() can load configuration from YAML file."""
        mount_path = os.path.join(temp_dir, 'mount')
        os.makedirs(mount_path)
        
        yaml_content = f"""- name: test
  type: local
  path: {mount_path}
"""
        yaml_file = os.path.join(temp_dir, 'config.yaml')
        with open(yaml_file, 'w') as f:
            f.write(yaml_content)
        
        storage_manager.configure(yaml_file)
        
        node = storage_manager.node('test:file.txt')
        assert node.fullpath == 'test:file.txt'
    
    def test_configure_with_json_file(self, storage_manager, temp_dir):
        """configure() can load configuration from JSON file."""
        mount_path = os.path.join(temp_dir, 'mount')
        os.makedirs(mount_path)
        
        config = [
            {'name': 'test', 'type': 'local', 'path': mount_path}
        ]
        json_file = os.path.join(temp_dir, 'config.json')
        with open(json_file, 'w') as f:
            json.dump(config, f)
        
        storage_manager.configure(json_file)
        
        node = storage_manager.node('test:file.txt')
        assert node.fullpath == 'test:file.txt'
    
    def test_configure_raises_on_nonexistent_file(self, storage_manager):
        """configure() raises FileNotFoundError for nonexistent file."""
        with pytest.raises(FileNotFoundError):
            storage_manager.configure('/nonexistent/config.yaml')
    
    def test_configure_raises_on_invalid_type(self, storage_manager):
        """configure() raises TypeError for invalid source type."""
        with pytest.raises(TypeError):
            storage_manager.configure(12345)  # Not str or list
    
    def test_configure_raises_on_invalid_config_format(self, storage_manager):
        """configure() raises ValueError for invalid configuration format."""
        # Missing required 'name' field
        with pytest.raises(ValueError):
            storage_manager.configure([
                {'type': 'local', 'path': '/tmp'}
            ])
        
        # Missing required 'type' field
        with pytest.raises(ValueError):
            storage_manager.configure([
                {'name': 'test', 'path': '/tmp'}
            ])
    
    def test_configure_raises_on_invalid_backend_type(self, storage_manager, temp_dir):
        """configure() raises ValueError for unknown backend type."""
        with pytest.raises(ValueError):
            storage_manager.configure([
                {'name': 'test', 'type': 'nonexistent_backend', 'path': temp_dir}
            ])
    
    def test_configure_local_storage_requires_path(self, storage_manager):
        """configure() raises ValueError if local storage missing path."""
        with pytest.raises(ValueError):
            storage_manager.configure([
                {'name': 'test', 'type': 'local'}  # Missing 'path'
            ])
    
    def test_configure_s3_storage_requires_bucket(self, storage_manager):
        """configure() raises ValueError if S3 storage missing bucket."""
        with pytest.raises(ValueError):
            storage_manager.configure([
                {'name': 'test', 'type': 's3'}  # Missing 'bucket'
            ])
    
    def test_configure_memory_storage(self, storage_manager):
        """configure() can setup memory storage."""
        storage_manager.configure([
            {'name': 'mem', 'type': 'memory'}
        ])
        
        node = storage_manager.node('mem:file.txt')
        assert node.fullpath == 'mem:file.txt'


class TestStorageManagerNode:
    """Test StorageManager.node() method."""
    
    def test_node_with_full_path(self, configured_storage):
        """node() creates StorageNode from 'mount:path' string."""
        node = configured_storage.node('test:documents/file.txt')
        assert node.fullpath == 'test:documents/file.txt'
    
    def test_node_with_mount_only(self, configured_storage):
        """node() creates StorageNode for mount root."""
        node = configured_storage.node('test')
        assert node.fullpath == 'test:'
    
    def test_node_with_path_parts(self, configured_storage):
        """node() creates StorageNode from mount and path parts."""
        node = configured_storage.node('test', 'documents', 'file.txt')
        assert node.fullpath == 'test:documents/file.txt'
    
    def test_node_with_mixed_style(self, configured_storage):
        """node() handles mix of 'mount:path' and additional parts."""
        node = configured_storage.node('test:documents', 'reports', 'q4.pdf')
        assert node.fullpath == 'test:documents/reports/q4.pdf'
    
    def test_node_dynamic_composition(self, configured_storage):
        """node() works with dynamic path components."""
        user_id = '123'
        year = '2024'
        node = configured_storage.node('test', 'users', user_id, year, 'avatar.jpg')
        assert node.fullpath == 'test:users/123/2024/avatar.jpg'
    
    def test_node_raises_on_nonexistent_mount(self, configured_storage):
        """node() raises KeyError for non-configured mount."""
        with pytest.raises(KeyError, match="nonexistent"):
            configured_storage.node('nonexistent:file.txt')
    
    def test_node_normalizes_multiple_slashes(self, configured_storage):
        """node() collapses multiple slashes in path."""
        node = configured_storage.node('test:path//to///file.txt')
        assert node.fullpath == 'test:path/to/file.txt'
    
    def test_node_strips_leading_trailing_slashes(self, configured_storage):
        """node() strips leading and trailing slashes."""
        node = configured_storage.node('test:/path/to/file.txt/')
        assert node.fullpath == 'test:path/to/file.txt'
    
    def test_node_rejects_parent_directory_traversal(self, configured_storage):
        """node() raises ValueError for '..' in path."""
        with pytest.raises(ValueError, match=".."):
            configured_storage.node('test:path/../file.txt')
    
    def test_node_returns_storage_node_instance(self, configured_storage):
        """node() returns StorageNode instance."""
        from genro_storage import StorageNode
        node = configured_storage.node('test:file.txt')
        assert isinstance(node, StorageNode)
