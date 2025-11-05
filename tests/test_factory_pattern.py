"""Tests for factory pattern and subclassing support."""

import pytest
import tempfile
import shutil
from pathlib import Path

from genro_storage import StorageManager, StorageNode


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


class TestFactoryPatternBasic:
    """Test basic factory pattern functionality."""

    def test_base_node_creates_same_type(self, storage):
        """Test that StorageNode creates StorageNode children."""
        node = storage.node('test:documents/')
        child = node.child('file.txt')

        assert type(node) == StorageNode
        assert type(child) == StorageNode

    def test_parent_creates_same_type(self, storage):
        """Test that parent() preserves node type."""
        node = storage.node('test:documents/reports/file.txt')
        parent = node.parent

        assert type(node) == StorageNode
        assert type(parent) == StorageNode

    def test_children_creates_same_type(self, storage, temp_dir):
        """Test that children() preserves node type."""
        # Create test files
        test_dir = Path(temp_dir) / 'testdir'
        test_dir.mkdir()
        (test_dir / 'file1.txt').write_text('content1')
        (test_dir / 'file2.txt').write_text('content2')

        node = storage.node('test:testdir/')
        children = node.children()

        assert type(node) == StorageNode
        assert all(type(child) == StorageNode for child in children)


class CustomNode(StorageNode):
    """Custom subclass with extra attributes for testing."""

    def __init__(self, manager, mount_name, path, custom_attr=None):
        super().__init__(manager, mount_name, path)
        self.custom_attr = custom_attr or "default"

    def _create_node(self, manager, mount_name, path):
        """Override factory to preserve custom_attr."""
        return self.__class__(manager, mount_name, path, self.custom_attr)

    def custom_method(self):
        """Custom method to verify subclass functionality."""
        return f"Custom: {self.custom_attr}"


class TestFactoryPatternSubclass:
    """Test factory pattern with subclass."""

    def test_subclass_child_preserves_type(self, storage):
        """Test that subclass child() returns subclass instance."""
        node = CustomNode(storage, 'test', 'documents/', 'myvalue')
        child = node.child('file.txt')

        assert type(node) == CustomNode
        assert type(child) == CustomNode
        assert child.custom_attr == 'myvalue'
        assert child.custom_method() == 'Custom: myvalue'

    def test_subclass_parent_preserves_type(self, storage):
        """Test that subclass parent property returns subclass instance."""
        node = CustomNode(storage, 'test', 'documents/reports/file.txt', 'myvalue')
        parent = node.parent

        assert type(parent) == CustomNode
        assert parent.custom_attr == 'myvalue'
        assert parent.custom_method() == 'Custom: myvalue'

    def test_subclass_children_preserves_type(self, storage, temp_dir):
        """Test that subclass children() returns subclass instances."""
        # Create test files
        test_dir = Path(temp_dir) / 'testdir'
        test_dir.mkdir()
        (test_dir / 'file1.txt').write_text('content1')
        (test_dir / 'file2.txt').write_text('content2')

        node = CustomNode(storage, 'test', 'testdir/', 'myvalue')
        children = node.children()

        assert type(node) == CustomNode
        assert len(children) == 2
        assert all(type(child) == CustomNode for child in children)
        assert all(child.custom_attr == 'myvalue' for child in children)
        assert all(child.custom_method() == 'Custom: myvalue' for child in children)

    def test_subclass_nested_navigation(self, storage, temp_dir):
        """Test that subclass type is preserved through nested navigation."""
        # Create nested structure
        Path(temp_dir, 'a', 'b', 'c').mkdir(parents=True)

        node = CustomNode(storage, 'test', 'a/', 'myvalue')

        # Navigate down
        child1 = node.child('b')
        child2 = child1.child('c')

        # All should be CustomNode with preserved attribute
        assert type(child1) == CustomNode
        assert type(child2) == CustomNode
        assert child1.custom_attr == 'myvalue'
        assert child2.custom_attr == 'myvalue'

        # Navigate up
        parent1 = child2.parent
        parent2 = parent1.parent

        assert type(parent1) == CustomNode
        assert type(parent2) == CustomNode
        assert parent1.custom_attr == 'myvalue'
        assert parent2.custom_attr == 'myvalue'


class TestFactoryPatternEdgeCases:
    """Test edge cases and error conditions."""

    def test_root_level_parent(self, storage):
        """Test parent of root-level node."""
        node = storage.node('test:file.txt')
        parent = node.parent

        # Parent of root should be mount root
        assert parent.fullpath == 'test:'
        assert type(parent) == StorageNode

    def test_multiple_path_components(self, storage):
        """Test child() with multiple path components."""
        node = storage.node('test:documents/')
        child = node.child('2024', 'reports', 'q4.pdf')

        assert child.fullpath == 'test:documents/2024/reports/q4.pdf'
        assert type(child) == StorageNode


class ComplexCustomNode(StorageNode):
    """Subclass with complex constructor for testing."""

    def __init__(self, manager, mount_name, path, param1, param2=None):
        super().__init__(manager, mount_name, path)
        self.param1 = param1
        self.param2 = param2 or {}

    def _create_node(self, manager, mount_name, path):
        """Override factory with complex parameters."""
        return self.__class__(manager, mount_name, path, self.param1, self.param2)


class TestFactoryPatternComplexSubclass:
    """Test factory pattern with complex subclass constructor."""

    def test_complex_constructor_preservation(self, storage):
        """Test that complex constructor parameters are preserved."""
        node = ComplexCustomNode(
            storage,
            'test',
            'documents/',
            'value1',
            {'key': 'value'}
        )

        child = node.child('file.txt')

        assert type(child) == ComplexCustomNode
        assert child.param1 == 'value1'
        assert child.param2 == {'key': 'value'}
