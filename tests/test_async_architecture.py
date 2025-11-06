"""Test suite for async architecture.

Tests async-native operations and parallel execution.
"""

import pytest
import pytest_asyncio
import asyncio
import tempfile
import time
from pathlib import Path

from genro_storage.async_storage_manager import AsyncStorageManager


@pytest_asyncio.fixture
async def async_storage():
    """Fixture for async storage manager with local backend."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AsyncStorageManager()
        await storage.configure([
            {
                'name': 'local',
                'protocol': 'local',
                'root_path': tmpdir
            }
        ])
        yield storage
        await storage.close_all()


@pytest_asyncio.fixture
async def memory_storage():
    """Fixture for async storage manager with memory backend."""
    storage = AsyncStorageManager()
    await storage.configure([
        {
            'name': 'mem',
            'protocol': 'memory'
        }
    ])
    yield storage
    await storage.close_all()


class TestAsyncBasicOperations:
    """Test basic async file operations."""

    @pytest.mark.asyncio
    async def test_async_write_and_read(self, async_storage):
        """Test async write and read operations."""
        node = async_storage.node('local:test.txt')

        # Write
        await node.write(b'Hello Async World')

        # Read
        content = await node.read()
        assert content == b'Hello Async World'

    @pytest.mark.asyncio
    async def test_async_text_operations(self, async_storage):
        """Test async text operations."""
        node = async_storage.node('local:test.txt')

        await node.write_text('Hello Async Text')
        text = await node.read_text()

        assert text == 'Hello Async Text'

    @pytest.mark.asyncio
    async def test_async_properties(self, async_storage):
        """Test async properties."""
        node = async_storage.node('local:test.txt')
        await node.write(b'test data')

        # All properties should be awaitable
        exists = await node.exists
        is_file = await node.is_file
        is_dir = await node.is_dir
        size = await node.size

        assert exists is True
        assert is_file is True
        assert is_dir is False
        assert size == 9

    @pytest.mark.asyncio
    async def test_async_mkdir_and_list(self, async_storage):
        """Test async directory operations."""
        dir_node = async_storage.node('local:testdir')
        await dir_node.mkdir()

        # Create files in directory
        file1 = async_storage.node('local:testdir/file1.txt')
        file2 = async_storage.node('local:testdir/file2.txt')

        await file1.write(b'content1')
        await file2.write(b'content2')

        # List directory
        children = await dir_node.list()
        names = sorted([c.basename for c in children])

        assert names == ['file1.txt', 'file2.txt']

    @pytest.mark.asyncio
    async def test_async_copy(self, async_storage):
        """Test async copy operation."""
        src = async_storage.node('local:source.txt')
        await src.write(b'copy me')

        dest = async_storage.node('local:dest.txt')
        await src.copy(dest)

        # Verify copy
        dest_content = await dest.read()
        assert dest_content == b'copy me'

    @pytest.mark.asyncio
    async def test_async_delete(self, async_storage):
        """Test async delete operation."""
        node = async_storage.node('local:delete_me.txt')
        await node.write(b'temporary')

        assert await node.exists

        await node.delete()

        assert not await node.exists


class TestAsyncParallelOperations:
    """Test parallel async operations."""

    @pytest.mark.asyncio
    async def test_parallel_writes(self, memory_storage):
        """Test multiple parallel write operations."""
        # Create 10 nodes
        nodes = [
            memory_storage.node(f'mem:file_{i}.txt')
            for i in range(10)
        ]

        # Write in parallel
        await asyncio.gather(
            *[node.write(f'content_{i}'.encode()) for i, node in enumerate(nodes)]
        )

        # Verify all files exist
        exists_results = await asyncio.gather(
            *[node.exists for node in nodes]
        )

        assert all(exists_results)

    @pytest.mark.asyncio
    async def test_parallel_reads(self, memory_storage):
        """Test multiple parallel read operations."""
        # Create files
        nodes = []
        for i in range(10):
            node = memory_storage.node(f'mem:file_{i}.txt')
            await node.write(f'content_{i}'.encode())
            nodes.append(node)

        # Read in parallel
        contents = await asyncio.gather(
            *[node.read() for node in nodes]
        )

        # Verify content
        for i, content in enumerate(contents):
            assert content == f'content_{i}'.encode()

    @pytest.mark.asyncio
    async def test_parallel_copy(self, memory_storage):
        """Test parallel copy operations."""
        # Create source files
        sources = []
        for i in range(5):
            node = memory_storage.node(f'mem:src_{i}.txt')
            await node.write(f'data_{i}'.encode())
            sources.append(node)

        # Parallel copy
        dests = [memory_storage.node(f'mem:dst_{i}.txt') for i in range(5)]

        await asyncio.gather(
            *[src.copy(dst) for src, dst in zip(sources, dests)]
        )

        # Verify all destinations
        dest_exists = await asyncio.gather(
            *[dst.exists for dst in dests]
        )

        assert all(dest_exists)

    @pytest.mark.asyncio
    async def test_parallel_mixed_operations(self, memory_storage):
        """Test mixed parallel operations."""
        # Mix of write, read, copy operations
        node1 = memory_storage.node('mem:file1.txt')
        node2 = memory_storage.node('mem:file2.txt')
        node3 = memory_storage.node('mem:file3.txt')

        # Setup
        await node1.write(b'data1')

        # Parallel mixed operations
        results = await asyncio.gather(
            node2.write(b'data2'),          # Write
            node1.read(),                    # Read
            node1.copy(node3),               # Copy
        )

        # Verify
        assert results[1] == b'data1'  # Read result
        assert await node2.exists
        assert await node3.exists


class TestAsyncPerformance:
    """Test async performance benefits."""

    @pytest.mark.asyncio
    async def test_async_vs_sequential_writes(self, memory_storage):
        """Compare async parallel vs sequential writes."""
        num_files = 20

        # Sequential writes
        start_seq = time.time()
        for i in range(num_files):
            node = memory_storage.node(f'mem:seq_{i}.txt')
            await node.write(b'x' * 1000)
        seq_time = time.time() - start_seq

        # Parallel writes
        start_par = time.time()
        nodes = [memory_storage.node(f'mem:par_{i}.txt') for i in range(num_files)]
        await asyncio.gather(
            *[node.write(b'x' * 1000) for node in nodes]
        )
        par_time = time.time() - start_par

        # Parallel should be faster or similar
        # (For memory backend, might not see huge difference, but structure is correct)
        print(f"\nSequential: {seq_time:.4f}s, Parallel: {par_time:.4f}s")
        assert par_time <= seq_time * 1.5  # Allow some overhead


class TestAsyncCaching:
    """Test async property caching."""

    @pytest.mark.asyncio
    async def test_cached_properties(self, memory_storage):
        """Test that cached properties work with async."""
        node = memory_storage.node('mem:cached.txt', cached=True)
        await node.write(b'test data')

        # First access - should query
        size1 = await node.size

        # Second access - should use cache
        size2 = await node.size

        assert size1 == size2 == 9

        # Modify file
        await node.write(b'new longer data')

        # Should still return cached value
        size3 = await node.size
        assert size3 == 9  # Still cached

        # Invalidate cache
        node.invalidate_cache()

        # Should get new value
        size4 = await node.size
        assert size4 == 15  # New size


class TestAsyncContextManager:
    """Test async context managers."""

    @pytest.mark.asyncio
    async def test_local_path_context(self, async_storage):
        """Test async local_path context manager."""
        node = async_storage.node('local:test.txt')
        await node.write(b'test content')

        # Use async context manager
        async with node.local_path(mode='r') as local_path:
            # Should be a real file path
            assert Path(local_path).exists()

            # Read using standard file operations
            with open(local_path, 'rb') as f:
                content = f.read()

            assert content == b'test content'


class TestAsyncMemoryBackend:
    """Test memory backend specific features."""

    @pytest.mark.skip(reason="fsspec MemoryFileSystem uses shared class-level storage, isolation not possible without custom implementation")
    @pytest.mark.asyncio
    async def test_memory_backend_isolation(self):
        """Test that memory backends with private stores are isolated.

        NOTE: This test is skipped because fsspec.implementations.memory.MemoryFileSystem
        uses a class-level shared `store` attribute that cannot be overridden per-instance.
        All MemoryFileSystem instances share the same storage dict.

        To support true isolation, we would need to implement a custom memory backend.
        """
        storage1 = AsyncStorageManager()
        await storage1.configure([{'name': 'mem1', 'protocol': 'memory'}])

        storage2 = AsyncStorageManager()
        await storage2.configure([{'name': 'mem2', 'protocol': 'memory'}])

        # Write to storage1
        node1 = storage1.node('mem1:test.txt')
        await node1.write(b'data1')

        # storage2 should have its own empty storage (but doesn't due to fsspec limitation)
        node2 = storage2.node('mem2:test.txt')
        assert not await node2.exists

        await storage1.close_all()
        await storage2.close_all()

    @pytest.mark.asyncio
    async def test_memory_backend_performance(self, memory_storage):
        """Test memory backend is fast for many operations."""
        num_ops = 100

        start = time.time()

        # Many parallel operations
        nodes = [memory_storage.node(f'mem:file_{i}.txt') for i in range(num_ops)]

        # Write
        await asyncio.gather(*[node.write(b'x') for node in nodes])

        # Read
        await asyncio.gather(*[node.read() for node in nodes])

        # Delete
        await asyncio.gather(*[node.delete() for node in nodes])

        elapsed = time.time() - start

        print(f"\n{num_ops} write+read+delete operations: {elapsed:.4f}s")

        # Should be very fast (< 1 second for 100 ops)
        assert elapsed < 1.0


class TestAsyncErrorHandling:
    """Test async error handling."""

    @pytest.mark.asyncio
    async def test_async_file_not_found(self, memory_storage):
        """Test FileNotFoundError with async."""
        node = memory_storage.node('mem:nonexistent.txt')

        with pytest.raises(FileNotFoundError):
            await node.read()

    @pytest.mark.asyncio
    async def test_async_parent_not_found_without_autocreate(self, memory_storage):
        """Test parent directory creation."""
        node = memory_storage.node('mem:deep/nested/file.txt', autocreate=False)

        with pytest.raises(FileNotFoundError):
            await node.write(b'data', parents=False)

    @pytest.mark.asyncio
    async def test_async_directory_delete_not_recursive(self, memory_storage):
        """Test directory delete requires recursive flag."""
        dir_node = memory_storage.node('mem:testdir')
        await dir_node.mkdir()

        file_node = memory_storage.node('mem:testdir/file.txt')
        await file_node.write(b'data')

        # Should fail without recursive
        with pytest.raises(ValueError):
            await dir_node.delete(recursive=False)

        # Should work with recursive
        await dir_node.delete(recursive=True)
        assert not await dir_node.exists
