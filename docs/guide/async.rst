Async Operations Guide
======================

Complete async/await support for all storage operations.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

genro-storage provides full async/await support through ``AsyncStorageManager``:

- All I/O operations are async
- Parallel operations with ``asyncio.gather()``
- Compatible with FastAPI, asyncio applications
- Same API as synchronous version

Basic Setup
-----------

.. test: test_async_architecture.py::TestAsyncBasicOperations::test_async_write_and_read

Basic async setup and operations. Example from `test_async_architecture.py::test_async_write_and_read <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L50-L59>`_:

.. code-block:: python

    from genro_storage import AsyncStorageManager

    # Create async storage manager
    storage = AsyncStorageManager()

    # Configure (sync - call at startup)
    await storage.configure([
        {
            'name': 'local',
            'protocol': 'local',
            'root_path': '/path/to/storage'
        }
    ])

    # Get node reference
    node = storage.node('local:test.txt')

    # All operations are async
    await node.write(b'Hello Async World')

    # Read
    content = await node.read()
    assert content == b'Hello Async World'

Text Operations
---------------

.. test: test_async_architecture.py::TestAsyncBasicOperations::test_async_text_operations

Async text read/write. Example from `test_async_architecture.py::test_async_text_operations <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L62-L69>`_:

.. code-block:: python

    node = storage.node('local:test.txt')

    await node.write_text('Hello Async Text')
    text = await node.read_text()

    assert text == 'Hello Async Text'

Async Properties
----------------

.. test: test_async_architecture.py::TestAsyncBasicOperations::test_async_properties

All properties are awaitable. Example from `test_async_architecture.py::test_async_properties <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L72-L86>`_:

.. code-block:: python

    node = storage.node('local:test.txt')
    await node.write(b'test data')

    # All properties are awaitable
    exists = await node.exists
    is_file = await node.is_file
    is_dir = await node.is_dir
    size = await node.size

    assert exists is True
    assert is_file is True
    assert is_dir is False
    assert size == 9

Directory Operations
--------------------

.. test: test_async_architecture.py::TestAsyncBasicOperations::test_async_mkdir_and_list

Async directory operations. Example from `test_async_architecture.py::test_async_mkdir_and_list <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L88-L105>`_:

.. code-block:: python

    dir_node = storage.node('local:testdir')
    await dir_node.mkdir()

    # Create files in directory
    file1 = storage.node('local:testdir/file1.txt')
    file2 = storage.node('local:testdir/file2.txt')

    await file1.write(b'content1')
    await file2.write(b'content2')

    # List directory
    children = await dir_node.list()
    names = sorted([c.basename for c in children])

    assert names == ['file1.txt', 'file2.txt']

Copy and Delete
---------------

.. test: test_async_architecture.py::TestAsyncBasicOperations::test_async_copy

.. test: test_async_architecture.py::TestAsyncBasicOperations::test_async_delete

Copy and delete operations. Examples from `test_async_architecture.py <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L107-L130>`_:

.. code-block:: python

    # Copy
    src = storage.node('local:source.txt')
    await src.write(b'copy me')

    dest = storage.node('local:dest.txt')
    await src.copy(dest)

    # Verify copy
    dest_content = await dest.read()
    assert dest_content == b'copy me'

    # Delete
    node = storage.node('local:delete_me.txt')
    await node.write(b'temporary')

    assert await node.exists

    await node.delete()

    assert not await node.exists

Parallel Operations
-------------------

Parallel Writes
~~~~~~~~~~~~~~~

.. test: test_async_architecture.py::TestAsyncParallelOperations::test_parallel_writes

Write multiple files in parallel. Example from `test_async_architecture.py::test_parallel_writes <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L137-L155>`_:

.. code-block:: python

    import asyncio

    # Create 10 nodes
    nodes = [
        storage.node(f'mem:file_{i}.txt')
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

Parallel Reads
~~~~~~~~~~~~~~

.. test: test_async_architecture.py::TestAsyncParallelOperations::test_parallel_reads

Read multiple files in parallel. Example from `test_async_architecture.py::test_parallel_reads <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L158-L174>`_:

.. code-block:: python

    # Create files
    nodes = []
    for i in range(10):
        node = storage.node(f'mem:file_{i}.txt')
        await node.write(f'content_{i}'.encode())
        nodes.append(node)

    # Read in parallel
    contents = await asyncio.gather(
        *[node.read() for node in nodes]
    )

    # Verify content
    for i, content in enumerate(contents):
        assert content == f'content_{i}'.encode()

Parallel Copy
~~~~~~~~~~~~~

.. test: test_async_architecture.py::TestAsyncParallelOperations::test_parallel_copy

Copy files in parallel. Example from `test_async_architecture.py::test_parallel_copy <https://github.com/genropy/genro-storage/blob/main/tests/test_async_architecture.py#L176-L198>`_:

.. code-block:: python

    # Create source files
    sources = []
    for i in range(5):
        node = storage.node(f'mem:src_{i}.txt')
        await node.write(f'data_{i}'.encode())
        sources.append(node)

    # Parallel copy
    dests = [storage.node(f'mem:dst_{i}.txt') for i in range(5)]

    await asyncio.gather(
        *[src.copy(dst) for src, dst in zip(sources, dests)]
    )

    # Verify all destinations
    dest_exists = await asyncio.gather(
        *[dst.exists for dst in dests]
    )

    assert all(dest_exists)

FastAPI Integration
-------------------

Basic File Serving
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fastapi import FastAPI, HTTPException
    from genro_storage import AsyncStorageManager

    app = FastAPI()

    # Configure storage at startup
    storage = AsyncStorageManager()

    @app.on_event("startup")
    async def startup():
        await storage.configure([
            {'name': 'uploads', 'protocol': 's3', 'bucket': 'my-bucket'}
        ])

    @app.get("/files/{filepath:path}")
    async def get_file(filepath: str):
        node = storage.node(f'uploads:{filepath}')

        if not await node.exists:
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "data": await node.read(mode='rb'),
            "size": await node.size,
            "mtime": await node.mtime
        }

File Upload Endpoint
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fastapi import UploadFile

    @app.post("/upload/{filepath:path}")
    async def upload_file(filepath: str, file: UploadFile):
        node = storage.node(f'uploads:{filepath}')

        # Read uploaded file
        content = await file.read()

        # Write to storage
        await node.write(content, mode='wb')

        return {
            "filepath": filepath,
            "size": await node.size
        }

Batch Operations
~~~~~~~~~~~~~~~~

.. code-block:: python

    @app.post("/backup")
    async def backup_all(file_list: list[str]):
        async def backup_one(filepath):
            source = storage.node(f'uploads:{filepath}')
            target = storage.node(f'backups:{filepath}')

            if not await source.exists:
                return {"filepath": filepath, "status": "not found"}

            data = await source.read(mode='rb')
            await target.write(data, mode='wb')

            return {"filepath": filepath, "status": "ok"}

        # Process all files in parallel
        results = await asyncio.gather(*[backup_one(f) for f in file_list])

        return {"results": results}

Context Manager Pattern
-----------------------

Clean Resource Management
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup
        storage = AsyncStorageManager()
        await storage.configure([
            {'name': 'data', 'protocol': 'local', 'root_path': '/data'}
        ])

        app.state.storage = storage

        yield

        # Cleanup
        await storage.close_all()

    app = FastAPI(lifespan=lifespan)

Performance Considerations
--------------------------

Benefits of Async
~~~~~~~~~~~~~~~~~

1. **Non-blocking I/O** - Other tasks run while waiting for I/O
2. **Parallel operations** - Multiple files simultaneously
3. **Scalability** - Handle many concurrent requests
4. **Efficiency** - Better resource utilization

When to Use Async
~~~~~~~~~~~~~~~~~

**Good use cases**:

- Web servers (FastAPI, aiohttp)
- Batch processing with many files
- Real-time applications
- Microservices with I/O-bound operations

**Not necessary for**:

- Simple scripts
- Single-file operations
- CPU-bound tasks
- Synchronous codebases

Async vs Sync Performance
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Async shines with**:

- Multiple S3 operations (parallel downloads/uploads)
- Directory operations with many files
- Concurrent user requests

**Sync is fine for**:

- Single file read/write
- Sequential processing
- Simple batch scripts

Best Practices
--------------

1. **Configure at startup**: Call ``configure()`` once during app initialization
2. **Use gather()**: Batch parallel operations with ``asyncio.gather()``
3. **Close resources**: Always call ``await storage.close_all()`` on shutdown
4. **Error handling**: Use try/except around async operations
5. **Timeouts**: Consider ``asyncio.wait_for()`` for long-running operations

Migration from Sync
-------------------

Conversion is straightforward:

.. code-block:: python

    # Synchronous
    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([...])  # Sync

    node = storage.node('data:file.txt')
    content = node.read()

    # Asynchronous
    from genro_storage import AsyncStorageManager

    storage = AsyncStorageManager()
    await storage.configure([...])  # Await configure

    node = storage.node('data:file.txt')
    content = await node.read()  # Await operations

Next Steps
----------

* See :doc:`/quickstart` for basic usage
* Check :doc:`/backends` for storage configuration
* Read :doc:`copy-strategies` for efficient sync
* Explore :doc:`/examples` for more patterns
