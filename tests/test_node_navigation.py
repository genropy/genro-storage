"""Tests for StorageNode navigation methods."""

import os
import pytest


class TestStorageNodeChildren:
    """Test StorageNode.children() method."""
    
    def test_children_returns_list_of_storage_nodes(self, configured_storage, temp_dir):
        """children() returns list of StorageNode objects."""
        from genro_storage import StorageNode
        
        # Create directory with files
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        open(os.path.join(dir_path, 'file1.txt'), 'w').close()
        open(os.path.join(dir_path, 'file2.txt'), 'w').close()
        
        node = configured_storage.node('test:mydir')
        children = node.children()
        
        assert isinstance(children, list)
        assert len(children) == 2
        assert all(isinstance(child, StorageNode) for child in children)
    
    def test_children_returns_empty_list_for_empty_directory(self, configured_storage, temp_dir):
        """children() returns empty list for empty directory."""
        dir_path = os.path.join(temp_dir, 'empty')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:empty')
        children = node.children()
        
        assert children == []
    
    def test_children_includes_files_and_directories(self, configured_storage, temp_dir):
        """children() returns both files and subdirectories."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        os.makedirs(os.path.join(dir_path, 'subdir'))
        open(os.path.join(dir_path, 'file.txt'), 'w').close()
        
        node = configured_storage.node('test:parent')
        children = node.children()
        
        assert len(children) == 2
        
        basenames = {child.basename for child in children}
        assert basenames == {'subdir', 'file.txt'}
    
    def test_children_nodes_have_correct_paths(self, configured_storage, temp_dir):
        """children() nodes have correct fullpath."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        open(os.path.join(dir_path, 'file1.txt'), 'w').close()
        open(os.path.join(dir_path, 'file2.txt'), 'w').close()
        
        node = configured_storage.node('test:parent')
        children = node.children()
        
        paths = {child.fullpath for child in children}
        assert paths == {'test:parent/file1.txt', 'test:parent/file2.txt'}
    
    def test_children_sorted_by_name(self, configured_storage, temp_dir):
        """children() returns nodes sorted by basename."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        
        # Create files in non-alphabetical order
        for name in ['c.txt', 'a.txt', 'b.txt']:
            open(os.path.join(dir_path, name), 'w').close()
        
        node = configured_storage.node('test:parent')
        children = node.children()
        
        basenames = [child.basename for child in children]
        assert basenames == ['a.txt', 'b.txt', 'c.txt']
    
    def test_children_with_nested_structure(self, configured_storage, temp_dir):
        """children() only returns direct children, not nested."""
        dir_path = os.path.join(temp_dir, 'parent')
        subdir_path = os.path.join(dir_path, 'subdir')
        os.makedirs(subdir_path)
        
        open(os.path.join(dir_path, 'parent_file.txt'), 'w').close()
        open(os.path.join(subdir_path, 'nested_file.txt'), 'w').close()
        
        node = configured_storage.node('test:parent')
        children = node.children()
        
        # Should only see direct children
        basenames = {child.basename for child in children}
        assert basenames == {'parent_file.txt', 'subdir'}
        assert 'nested_file.txt' not in basenames
    
    def test_children_raises_for_file(self, configured_storage, temp_dir):
        """children() raises exception for file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        open(file_path, 'w').close()
        
        node = configured_storage.node('test:file.txt')
        
        with pytest.raises(Exception):
            node.children()
    
    def test_children_raises_for_nonexistent(self, configured_storage):
        """children() raises exception for nonexistent path."""
        node = configured_storage.node('test:nonexistent')
        
        with pytest.raises(Exception):
            node.children()
    
    def test_children_with_hidden_files(self, configured_storage, temp_dir):
        """children() includes hidden files (starting with dot)."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        
        open(os.path.join(dir_path, '.hidden'), 'w').close()
        open(os.path.join(dir_path, 'visible.txt'), 'w').close()
        
        node = configured_storage.node('test:parent')
        children = node.children()
        
        basenames = {child.basename for child in children}
        assert basenames == {'.hidden', 'visible.txt'}
    
    def test_children_preserves_file_types(self, configured_storage, temp_dir):
        """children() nodes correctly report isfile/isdir."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        os.makedirs(os.path.join(dir_path, 'subdir'))
        open(os.path.join(dir_path, 'file.txt'), 'w').close()
        
        node = configured_storage.node('test:parent')
        children = node.children()
        
        files = [c for c in children if c.isfile]
        dirs = [c for c in children if c.isdir]
        
        assert len(files) == 1
        assert len(dirs) == 1
        assert files[0].basename == 'file.txt'
        assert dirs[0].basename == 'subdir'


class TestStorageNodeChild:
    """Test StorageNode.child() method."""
    
    def test_child_returns_child_node(self, configured_storage):
        """child() returns StorageNode for child path."""
        from genro_storage import StorageNode
        
        parent = configured_storage.node('test:parent')
        child = parent.child('file.txt')
        
        assert isinstance(child, StorageNode)
        assert child.fullpath == 'test:parent/file.txt'
    
    def test_child_with_subdirectory(self, configured_storage):
        """child() can reference subdirectory."""
        parent = configured_storage.node('test:parent')
        child = parent.child('subdir')
        
        assert child.fullpath == 'test:parent/subdir'
    
    def test_child_does_not_require_existence(self, configured_storage):
        """child() returns node even if it doesn't exist."""
        parent = configured_storage.node('test:parent')
        child = parent.child('nonexistent.txt')
        
        # Should create node, even though file doesn't exist
        assert child.fullpath == 'test:parent/nonexistent.txt'
        assert not child.exists
    
    def test_child_from_root(self, configured_storage):
        """child() works from mount root."""
        root = configured_storage.node('test:')
        child = root.child('file.txt')
        
        assert child.fullpath == 'test:file.txt'
    
    def test_child_chaining(self, configured_storage):
        """child() can be chained to navigate deeper."""
        root = configured_storage.node('test:')
        
        nested = root.child('a').child('b').child('c').child('file.txt')
        
        assert nested.fullpath == 'test:a/b/c/file.txt'
    
    def test_child_with_path_containing_slash(self, configured_storage):
        """child() handles name containing slashes."""
        parent = configured_storage.node('test:parent')
        child = parent.child('subdir/file.txt')
        
        # Should treat as nested path
        assert child.fullpath == 'test:parent/subdir/file.txt'
    
    def test_child_normalizes_path(self, configured_storage):
        """child() normalizes path (removes extra slashes)."""
        parent = configured_storage.node('test:parent')
        child = parent.child('subdir//file.txt')
        
        assert child.fullpath == 'test:parent/subdir/file.txt'
    
    def test_child_strips_leading_trailing_slashes(self, configured_storage):
        """child() strips leading/trailing slashes from name."""
        parent = configured_storage.node('test:parent')
        child = parent.child('/file.txt/')
        
        assert child.fullpath == 'test:parent/file.txt'
    
    def test_child_with_empty_string(self, configured_storage):
        """child('') returns same node."""
        parent = configured_storage.node('test:parent')
        child = parent.child('')
        
        assert child.fullpath == 'test:parent'
    
    def test_child_with_dot(self, configured_storage):
        """child('.') refers to current directory."""
        parent = configured_storage.node('test:parent')
        child = parent.child('.')
        
        # Should normalize to parent itself
        assert child.fullpath == 'test:parent'
    
    def test_child_rejects_parent_traversal(self, configured_storage):
        """child('..') raises ValueError for parent traversal."""
        parent = configured_storage.node('test:parent')
        
        with pytest.raises(ValueError, match=".."):
            parent.child('..')
    
    def test_child_with_actual_file(self, configured_storage, temp_dir):
        """child() node can be used to access actual file."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        
        file_path = os.path.join(dir_path, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        parent = configured_storage.node('test:parent')
        child = parent.child('file.txt')
        
        assert child.exists
        assert child.read_text() == 'content'


class TestStorageNodeParentNavigation:
    """Test navigation using parent property."""
    
    def test_parent_child_roundtrip(self, configured_storage):
        """parent.child(name) and child.parent are consistent."""
        parent = configured_storage.node('test:documents')
        child = parent.child('file.txt')
        
        # Going back to parent
        assert child.parent.fullpath == parent.fullpath
    
    def test_navigating_directory_tree(self, configured_storage, temp_dir):
        """Can navigate directory tree using parent and child."""
        # Create structure: root/a/b/c/file.txt
        path = os.path.join(temp_dir, 'a', 'b', 'c')
        os.makedirs(path)
        file_path = os.path.join(path, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        
        # Navigate down
        root = configured_storage.node('test:')
        file_node = root.child('a').child('b').child('c').child('file.txt')
        
        assert file_node.exists
        
        # Navigate up
        c_dir = file_node.parent
        assert c_dir.basename == 'c'
        assert c_dir.isdir
        
        b_dir = c_dir.parent
        assert b_dir.basename == 'b'
        
        a_dir = b_dir.parent
        assert a_dir.basename == 'a'
        
        back_to_root = a_dir.parent
        assert back_to_root.fullpath == 'test:'
    
    def test_listing_and_navigating_children(self, configured_storage, temp_dir):
        """Can list children and navigate into them."""
        # Create structure
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        
        subdir_path = os.path.join(dir_path, 'subdir')
        os.makedirs(subdir_path)
        
        with open(os.path.join(subdir_path, 'nested.txt'), 'w') as f:
            f.write('nested content')
        
        # Navigate
        parent = configured_storage.node('test:parent')
        
        # List children
        children = parent.children()
        subdir = [c for c in children if c.basename == 'subdir'][0]
        
        # Go into subdirectory
        nested_children = subdir.children()
        assert len(nested_children) == 1
        assert nested_children[0].basename == 'nested.txt'
        assert nested_children[0].read_text() == 'nested content'
    
    def test_sibling_navigation(self, configured_storage, temp_dir):
        """Can navigate to sibling files."""
        dir_path = os.path.join(temp_dir, 'parent')
        os.makedirs(dir_path)
        
        with open(os.path.join(dir_path, 'file1.txt'), 'w') as f:
            f.write('content1')
        with open(os.path.join(dir_path, 'file2.txt'), 'w') as f:
            f.write('content2')
        
        # Start at file1
        file1 = configured_storage.node('test:parent/file1.txt')
        
        # Navigate to sibling via parent
        file2 = file1.parent.child('file2.txt')
        
        assert file2.exists
        assert file2.read_text() == 'content2'
    
    def test_finding_specific_child_in_directory(self, configured_storage, temp_dir):
        """Can find specific child among many."""
        dir_path = os.path.join(temp_dir, 'data')
        os.makedirs(dir_path)
        
        # Create many files
        for i in range(10):
            with open(os.path.join(dir_path, f'file{i}.txt'), 'w') as f:
                f.write(f'content{i}')
        
        parent = configured_storage.node('test:data')
        
        # Find specific file
        target = parent.child('file5.txt')
        assert target.exists
        assert target.read_text() == 'content5'
    
    def test_checking_if_path_is_child_of_parent(self, configured_storage):
        """Can check if a path is a child of another."""
        parent = configured_storage.node('test:documents')
        child = configured_storage.node('test:documents/reports/q4.pdf')
        not_child = configured_storage.node('test:other/file.txt')
        
        # Check if paths start with parent path
        assert child.fullpath.startswith(parent.fullpath)
        assert not not_child.fullpath.startswith(parent.fullpath)


class TestStorageNodeIterationPatterns:
    """Test common iteration patterns with navigation."""
    
    def test_recursive_file_listing(self, configured_storage, temp_dir):
        """Recursively list all files in directory tree."""
        # Create nested structure
        os.makedirs(os.path.join(temp_dir, 'a', 'b'))
        os.makedirs(os.path.join(temp_dir, 'a', 'c'))
        
        open(os.path.join(temp_dir, 'file1.txt'), 'w').close()
        open(os.path.join(temp_dir, 'a', 'file2.txt'), 'w').close()
        open(os.path.join(temp_dir, 'a', 'b', 'file3.txt'), 'w').close()
        open(os.path.join(temp_dir, 'a', 'c', 'file4.txt'), 'w').close()
        
        def list_all_files(node):
            """Recursively list all files."""
            if node.isfile:
                return [node]
            elif node.isdir:
                files = []
                for child in node.children():
                    files.extend(list_all_files(child))
                return files
            return []
        
        root = configured_storage.node('test:')
        all_files = list_all_files(root)
        
        basenames = {f.basename for f in all_files}
        assert basenames == {'file1.txt', 'file2.txt', 'file3.txt', 'file4.txt'}
    
    def test_filter_children_by_extension(self, configured_storage, temp_dir):
        """Filter children by file extension."""
        dir_path = os.path.join(temp_dir, 'mixed')
        os.makedirs(dir_path)
        
        open(os.path.join(dir_path, 'doc1.txt'), 'w').close()
        open(os.path.join(dir_path, 'doc2.txt'), 'w').close()
        open(os.path.join(dir_path, 'image.jpg'), 'w').close()
        open(os.path.join(dir_path, 'data.csv'), 'w').close()
        
        parent = configured_storage.node('test:mixed')
        
        txt_files = [c for c in parent.children() if c.suffix == '.txt']
        
        assert len(txt_files) == 2
        basenames = {f.basename for f in txt_files}
        assert basenames == {'doc1.txt', 'doc2.txt'}
    
    def test_sum_directory_size(self, configured_storage, temp_dir):
        """Calculate total size of all files in directory."""
        dir_path = os.path.join(temp_dir, 'data')
        os.makedirs(dir_path)
        
        # Create files with known sizes
        for i, size in enumerate([100, 200, 300]):
            file_path = os.path.join(dir_path, f'file{i}.bin')
            with open(file_path, 'wb') as f:
                f.write(b'X' * size)
        
        parent = configured_storage.node('test:data')
        
        total_size = sum(child.size for child in parent.children() if child.isfile)
        
        assert total_size == 600
    
    def test_find_newest_file(self, configured_storage, temp_dir):
        """Find most recently modified file in directory."""
        import time
        
        dir_path = os.path.join(temp_dir, 'data')
        os.makedirs(dir_path)
        
        # Create files with delays to ensure different mtimes
        for i in range(3):
            file_path = os.path.join(dir_path, f'file{i}.txt')
            with open(file_path, 'w') as f:
                f.write(f'content{i}')
            time.sleep(0.01)  # Small delay
        
        parent = configured_storage.node('test:data')
        children = parent.children()
        
        newest = max(children, key=lambda c: c.mtime)
        
        assert newest.basename == 'file2.txt'
    
    def test_copy_directory_contents(self, configured_storage, temp_dir):
        """Copy all files from one directory to another."""
        # Setup source
        src_dir = os.path.join(temp_dir, 'source')
        os.makedirs(src_dir)
        
        for i in range(3):
            with open(os.path.join(src_dir, f'file{i}.txt'), 'w') as f:
                f.write(f'content{i}')
        
        # Setup destination
        dest_dir = os.path.join(temp_dir, 'destination')
        os.makedirs(dest_dir)
        
        src_node = configured_storage.node('test:source')
        dest_node = configured_storage.node('test:destination')
        
        # Copy all children
        for child in src_node.children():
            if child.isfile:
                child.copy(dest_node.child(child.basename))
        
        # Verify
        dest_children = dest_node.children()
        assert len(dest_children) == 3
        
        basenames = {c.basename for c in dest_children}
        assert basenames == {'file0.txt', 'file1.txt', 'file2.txt'}
