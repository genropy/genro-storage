"""The public API is synchronous, in every calling context.

Up to 0.7 these methods carried ``@smartasync``, so inside an event loop they
returned awaitables instead of values. That is the behaviour this module pins
against: whatever the caller looks like, an I/O method performs the work and
returns the result (issue #67, genro-asgi SPECIFICATION.md D22).
"""

import asyncio
import inspect

import pytest

import genro_storage.node
from genro_storage import StorageManager, StorageNode

# Every I/O method that used to be decorated.
IO_METHODS = [
    "exists",
    "is_file",
    "is_dir",
    "size",
    "mtime",
    "md5hash",
    "read",
    "write",
    "read_text",
    "read_bytes",
    "write_text",
    "write_bytes",
    "delete",
    "copy_to",
    "children",
    "mkdir",
]


@pytest.fixture
def storage(empty_memory_filesystem):
    """Create a StorageManager backed by an empty memory filesystem."""
    manager = StorageManager()
    manager.configure([{"name": "mem", "protocol": "memory"}])
    return manager


@pytest.mark.parametrize("method_name", IO_METHODS)
def test_io_method_is_a_plain_function(method_name):
    """Test that no I/O method is a coroutine function."""
    method = getattr(StorageNode, method_name)
    assert not inspect.iscoroutinefunction(method)
    assert not inspect.isasyncgenfunction(method)


def test_calls_return_values_in_sync_context(storage):
    """Test that a plain call returns the value, not an awaitable."""
    node = storage.node("mem:file.txt")

    assert node.exists() is False

    node.write("content")

    assert node.exists() is True
    assert node.read() == "content"
    assert node.size() == len("content")


def test_calls_return_values_inside_an_event_loop(storage):
    """Test that the same calls behave identically from a coroutine."""

    async def scenario():
        node = storage.node("mem:in_loop.txt")

        # No await: the value must come back directly, not a coroutine.
        node.write("from a loop")
        content = node.read()
        exists = node.exists()

        return content, exists

    content, exists = asyncio.run(scenario())

    assert content == "from a loop"
    assert exists is True


def test_offloading_to_a_thread_is_how_async_callers_use_it(storage):
    """Test the documented pattern for async callers."""

    async def scenario():
        node = storage.node("mem:offloaded.txt")

        await asyncio.to_thread(node.write, "offloaded")
        return await asyncio.to_thread(node.read)

    assert asyncio.run(scenario()) == "offloaded"


def test_package_does_not_import_smartasync():
    """Test that the decorator is gone from the public surface."""
    assert not hasattr(genro_storage.node, "smartasync")
