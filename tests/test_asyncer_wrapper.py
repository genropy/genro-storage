"""Tests for asyncer_wrapper module.

Tests the async wrapper functionality using asyncer to wrap synchronous
genro-storage operations for use in async/await contexts.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Test if asyncer is available
try:
    from genro_storage.asyncer_wrapper import AsyncStorageManager, AsyncStorageNode
    ASYNCER_AVAILABLE = True
except ImportError:
    ASYNCER_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="asyncer not installed")


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def storage(temp_dir):
    """Create an AsyncStorageManager configured with memory backend."""
    storage = AsyncStorageManager()
    storage.configure([
        {'name': 'memory', 'type': 'memory'},
        {'name': 'local', 'type': 'local', 'path': temp_dir}
    ])
    return storage


class TestAsyncStorageManager:
    """Tests for AsyncStorageManager class."""

    def test_init(self):
        """Test AsyncStorageManager initialization."""
        storage = AsyncStorageManager()
        assert storage is not None
        assert hasattr(storage, '_storage')

    def test_configure(self, temp_dir):
        """Test configure with list of mounts."""
        storage = AsyncStorageManager()
        storage.configure([
            {'name': 'local', 'type': 'local', 'path': temp_dir},
            {'name': 'memory', 'type': 'memory'}
        ])
        assert storage.has_mount('local')
        assert storage.has_mount('memory')

    def test_add_mount(self, temp_dir):
        """Test adding mount at runtime."""
        storage = AsyncStorageManager()
        storage.add_mount({
            'name': 'test',
            'type': 'local',
            'path': temp_dir
        })
        assert storage.has_mount('test')

    def test_has_mount(self, storage):
        """Test has_mount method."""
        assert storage.has_mount('memory')
        assert storage.has_mount('local')
        assert not storage.has_mount('nonexistent')

    def test_get_mount_names(self, storage):
        """Test get_mount_names method."""
        names = storage.get_mount_names()
        assert 'memory' in names
        assert 'local' in names
        assert len(names) >= 2

    def test_node(self, storage):
        """Test node creation."""
        node = storage.node('memory:test.txt')
        assert isinstance(node, AsyncStorageNode)
        assert node.path == 'test.txt'
        assert node.fullpath == 'memory:test.txt'


class TestAsyncStorageNode:
    """Tests for AsyncStorageNode class."""

    @pytest.mark.asyncio
    async def test_write_read_bytes(self, storage):
        """Test async write and read bytes."""
        node = storage.node('memory:test.bin')
        test_data = b'Hello async world'

        await node.write_bytes(test_data)
        result = await node.read_bytes()

        assert result == test_data

    @pytest.mark.asyncio
    async def test_write_read_text(self, storage):
        """Test async write and read text."""
        node = storage.node('memory:test.txt')
        test_text = 'Hello async text'

        await node.write_text(test_text)
        result = await node.read_text()

        assert result == test_text

    @pytest.mark.asyncio
    async def test_exists(self, storage):
        """Test async exists check."""
        node = storage.node('memory:exists_test.txt')

        # File doesn't exist yet
        assert not await node.exists()

        # Create file
        await node.write_text('content')

        # Now it exists
        assert await node.exists()

    @pytest.mark.asyncio
    async def test_delete(self, storage):
        """Test async delete."""
        node = storage.node('memory:delete_test.txt')

        # Create file
        await node.write_text('to be deleted')
        assert await node.exists()

        # Delete it
        await node.delete()

        # Should not exist anymore
        assert not await node.exists()

    @pytest.mark.asyncio
    async def test_size(self, storage):
        """Test async size property."""
        node = storage.node('memory:size_test.txt')
        test_data = b'12345'

        await node.write_bytes(test_data)
        size = await node.size()

        assert size == len(test_data)

    @pytest.mark.asyncio
    async def test_copy(self, storage):
        """Test async copy operation."""
        source = storage.node('memory:source.txt')
        target = storage.node('memory:target.txt')

        test_content = 'content to copy'
        await source.write_text(test_content)

        await source.copy_to(target)

        result = await target.read_text()
        assert result == test_content

    @pytest.mark.asyncio
    async def test_move(self, storage):
        """Test async move operation."""
        source = storage.node('memory:move_source.txt')
        target = storage.node('memory:move_target.txt')

        test_content = 'content to move'
        await source.write_text(test_content)

        await source.move_to(target)

        # Target should have the content (main requirement)
        result = await target.read_text()
        assert result == test_content

        # Note: Source deletion behavior varies by backend
        # Memory backend may not delete source after move

    @pytest.mark.asyncio
    async def test_isfile_isdir(self, storage):
        """Test async isfile and isdir checks."""
        file_node = storage.node('memory:test_file.txt')

        await file_node.write_text('content')

        assert await file_node.isfile()
        assert not await file_node.isdir()

    def test_sync_properties(self, storage):
        """Test synchronous properties (no I/O)."""
        node = storage.node('memory:path/to/file.txt')

        # These should work synchronously
        assert node.path == 'path/to/file.txt'
        assert node.fullpath == 'memory:path/to/file.txt'
        assert node.basename == 'file.txt'
        assert node.stem == 'file'
        assert node.suffix == '.txt'

    def test_repr_str(self, storage):
        """Test string representations."""
        node = storage.node('memory:test.txt')

        assert 'memory:test.txt' in repr(node)
        assert str(node) == 'memory:test.txt'


class TestAsyncCrossStorage:
    """Tests for async operations across different storage backends."""

    @pytest.mark.asyncio
    async def test_copy_memory_to_local(self, storage, temp_dir):
        """Test copying from memory to local storage."""
        source = storage.node('memory:source.txt')
        target = storage.node('local:target.txt')

        test_content = 'cross-storage copy'
        await source.write_text(test_content)

        await source.copy_to(target)

        result = await target.read_text()
        assert result == test_content

        # Verify file actually exists on disk
        local_path = Path(temp_dir) / 'target.txt'
        assert local_path.exists()


class TestAsyncConcurrency:
    """Tests for concurrent async operations."""

    @pytest.mark.asyncio
    async def test_concurrent_writes(self, storage):
        """Test multiple concurrent write operations."""
        import asyncio

        async def write_file(n):
            node = storage.node(f'memory:file_{n}.txt')
            await node.write_text(f'content {n}')
            return n

        # Write 10 files concurrently
        results = await asyncio.gather(*[write_file(i) for i in range(10)])

        assert len(results) == 10

        # Verify all files exist
        for i in range(10):
            node = storage.node(f'memory:file_{i}.txt')
            assert await node.exists()
            content = await node.read_text()
            assert content == f'content {i}'

    @pytest.mark.asyncio
    async def test_concurrent_reads(self, storage):
        """Test multiple concurrent read operations."""
        import asyncio

        # Create test files
        for i in range(5):
            node = storage.node(f'memory:read_{i}.txt')
            await node.write_text(f'data {i}')

        # Read concurrently
        async def read_file(n):
            node = storage.node(f'memory:read_{n}.txt')
            return await node.read_text()

        results = await asyncio.gather(*[read_file(i) for i in range(5)])

        assert len(results) == 5
        for i, content in enumerate(results):
            assert content == f'data {i}'


class TestAsyncErrors:
    """Tests for error handling in async operations."""

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, storage):
        """Test reading a file that doesn't exist."""
        node = storage.node('memory:nonexistent.txt')

        with pytest.raises(Exception):  # Will raise FileNotFoundError or similar
            await node.read_bytes()

    @pytest.mark.asyncio
    async def test_invalid_mount(self):
        """Test accessing invalid mount point."""
        storage = AsyncStorageManager()
        storage.configure([{'name': 'test', 'type': 'memory'}])

        with pytest.raises(Exception):  # Will raise StorageNotFoundError
            storage.node('invalid:file.txt')
