Async Operations Guide
======================

Transparent sync/async support via ``@smartasync`` decorator.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

genro-storage provides transparent async/await support through the ``@smartasync`` decorator
from ``genro-toolbox``. The same ``StorageManager`` and ``StorageNode`` classes work
seamlessly in both sync and async contexts:

- **Sync context**: Methods execute directly, returning values
- **Async context**: Methods return awaitables that must be awaited
- No separate ``AsyncStorageManager`` needed
- Parallel operations with ``asyncio.gather()``
- Compatible with FastAPI, asyncio applications

How It Works
------------

The ``@smartasync`` decorator automatically detects the execution context:

.. code-block:: python

    # In SYNC context (no event loop)
    node = storage.node('home:file.txt')
    if node.exists():           # Direct call, returns bool
        content = node.read()   # Direct call, returns bytes

    # In ASYNC context (inside async function)
    async def process():
        node = storage.node('home:file.txt')
        if await node.exists():           # Must await, returns bool
            content = await node.read()   # Must await, returns bytes

Basic Setup
-----------

The same configuration works for both sync and async usage:

.. code-block:: python

    from genro_storage import StorageManager

    # Create storage manager (same class for sync and async)
    storage = StorageManager()

    # Configure storage backends
    storage.configure([
        {
            'name': 'local',
            'protocol': 'local',
            'base_path': '/path/to/storage'
        },
        {
            'name': 'uploads',
            'protocol': 's3',
            'bucket': 'my-bucket'
        }
    ])

Sync Usage
----------

In synchronous code, all methods work as regular function calls:

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([
        {'name': 'local', 'protocol': 'local', 'base_path': '/tmp/storage'}
    ])

    # Get node reference
    node = storage.node('local:test.txt')

    # Write and read - direct calls
    node.write_bytes(b'Hello World')
    content = node.read_bytes()

    # Check properties - now methods with @smartasync
    if node.exists():
        print(f"File size: {node.size()} bytes")
        print(f"Is file: {node.is_file()}")

Async Usage
-----------

In async context, all I/O methods must be awaited:

.. code-block:: python

    import asyncio
    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([
        {'name': 'local', 'protocol': 'local', 'base_path': '/tmp/storage'}
    ])

    async def example():
        node = storage.node('local:test.txt')

        # All I/O operations are awaitable
        await node.write_bytes(b'Hello Async World')
        content = await node.read_bytes()

        # Properties are now methods - must await
        if await node.exists():
            size = await node.size()
            is_file = await node.is_file()
            print(f"File size: {size}, Is file: {is_file}")

    asyncio.run(example())

Methods vs Properties
---------------------

With ``@smartasync``, I/O operations that were previously properties are now methods:

.. list-table:: API Changes
   :header-rows: 1
   :widths: 30 30 40

   * - Old (property)
     - New (method)
     - Description
   * - ``node.exists``
     - ``node.exists()``
     - Check if file/directory exists
   * - ``node.is_file``
     - ``node.is_file()``
     - Check if node is a file
   * - ``node.is_dir``
     - ``node.is_dir()``
     - Check if node is a directory
   * - ``node.size``
     - ``node.size()``
     - Get file size in bytes
   * - ``node.mtime``
     - ``node.mtime()``
     - Get modification timestamp
   * - ``node.md5hash``
     - ``node.md5hash()``
     - Get MD5 hash of content

**Non-I/O properties remain unchanged** (no await needed):

- ``node.basename`` - Filename with extension
- ``node.stem`` - Filename without extension
- ``node.suffix`` - File extension
- ``node.parent`` - Parent directory as StorageNode
- ``node.mimetype`` - MIME type from extension

Directory Operations
--------------------

Async directory operations:

.. code-block:: python

    async def directory_example():
        dir_node = storage.node('local:testdir')
        await dir_node.mkdir()

        # Create files in directory
        file1 = storage.node('local:testdir/file1.txt')
        file2 = storage.node('local:testdir/file2.txt')

        await file1.write_bytes(b'content1')
        await file2.write_bytes(b'content2')

        # List directory
        children = await dir_node.children()
        names = sorted([c.basename for c in children])

        assert names == ['file1.txt', 'file2.txt']

Parallel Operations
-------------------

Parallel Writes
~~~~~~~~~~~~~~~

Write multiple files in parallel:

.. code-block:: python

    import asyncio

    async def parallel_writes():
        # Create 10 nodes
        nodes = [
            storage.node(f'mem:file_{i}.txt')
            for i in range(10)
        ]

        # Write in parallel
        await asyncio.gather(
            *[node.write_bytes(f'content_{i}'.encode()) for i, node in enumerate(nodes)]
        )

        # Verify all files exist
        exists_results = await asyncio.gather(
            *[node.exists() for node in nodes]
        )

        assert all(exists_results)

Parallel Reads
~~~~~~~~~~~~~~

Read multiple files in parallel:

.. code-block:: python

    async def parallel_reads():
        # Create files first
        nodes = []
        for i in range(10):
            node = storage.node(f'mem:file_{i}.txt')
            await node.write_bytes(f'content_{i}'.encode())
            nodes.append(node)

        # Read in parallel
        contents = await asyncio.gather(
            *[node.read_bytes() for node in nodes]
        )

        # Verify content
        for i, content in enumerate(contents):
            assert content == f'content_{i}'.encode()

FastAPI Integration
-------------------

Basic File Serving
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fastapi import FastAPI, HTTPException
    from genro_storage import StorageManager

    app = FastAPI()

    # Configure storage at module level
    storage = StorageManager()
    storage.configure([
        {'name': 'uploads', 'protocol': 's3', 'bucket': 'my-bucket'}
    ])

    @app.get("/files/{filepath:path}")
    async def get_file(filepath: str):
        node = storage.node(f'uploads:{filepath}')

        if not await node.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "data": await node.read_bytes(),
            "size": await node.size(),
            "mtime": await node.mtime()
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
        await node.write_bytes(content)

        return {
            "filepath": filepath,
            "size": await node.size()
        }

Batch Operations
~~~~~~~~~~~~~~~~

.. code-block:: python

    @app.post("/backup")
    async def backup_all(file_list: list[str]):
        async def backup_one(filepath):
            source = storage.node(f'uploads:{filepath}')
            target = storage.node(f'backups:{filepath}')

            if not await source.exists():
                return {"filepath": filepath, "status": "not found"}

            data = await source.read_bytes()
            await target.write_bytes(data)

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
        # Startup - configure storage
        storage = StorageManager()
        storage.configure([
            {'name': 'data', 'protocol': 'local', 'base_path': '/data'}
        ])

        app.state.storage = storage

        yield

        # Cleanup (if needed)
        pass

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

1. **Configure once**: Call ``configure()`` once during app initialization
2. **Use gather()**: Batch parallel operations with ``asyncio.gather()``
3. **Error handling**: Use try/except around async operations
4. **Timeouts**: Consider ``asyncio.wait_for()`` for long-running operations
5. **Same manager**: Use the same ``StorageManager`` instance throughout

Migration Notes
---------------

If upgrading from a version with ``AsyncStorageManager``:

.. code-block:: python

    # OLD (before v0.6.0) - DEPRECATED
    from genro_storage import AsyncStorageManager
    storage = AsyncStorageManager()
    await storage.configure([...])
    if await node.exists:  # property
        ...

    # NEW (v0.6.0+) - Use StorageManager for both
    from genro_storage import StorageManager
    storage = StorageManager()
    storage.configure([...])  # Sync configure
    if await node.exists():   # Method with ()
        ...

Key changes:

- Use ``StorageManager`` (not ``AsyncStorageManager``)
- ``configure()`` is sync (no await)
- I/O properties are now methods: ``exists()`` not ``exists``

Next Steps
----------

* See :doc:`/quickstart` for basic usage
* Check :doc:`/backends` for storage configuration
* Read :doc:`copy-strategies` for efficient sync
* Explore :doc:`/examples` for more patterns
