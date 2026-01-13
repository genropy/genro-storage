API Quick Reference
===================

This appendix provides a quick reference for all genro-storage APIs.

.. note::
   All I/O methods support both sync and async contexts via ``@smartasync``.
   In sync context, call directly. In async context, use ``await``.

StorageManager API
------------------

Configuration
~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Method
     - Description
   * - ``configure(source)``
     - Configure mount points from YAML/JSON file or list of dicts
   * - ``get_mount_names()``
     - Get list of configured mount point names
   * - ``has_mount(name)``
     - Check if a mount point is configured

Node Creation
~~~~~~~~~~~~~

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Method
     - Description
   * - ``node(mount_or_path, *parts, version=None)``
     - Create a StorageNode. If version specified, creates read-only snapshot
   * - ``iternode(*nodes)``
     - Create virtual node for lazy concatenation of multiple nodes
   * - ``diffnode(node1, node2)``
     - Create virtual node for lazy unified diff between two nodes

StorageNode API
---------------

File I/O
~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``read_bytes()``
     - Read entire file as bytes
     - ``read``
   * - ``read_text(encoding='utf-8')``
     - Read entire file as string
     - ``read``
   * - ``write_bytes(data)``
     - Write bytes to file
     - ``write``
   * - ``write_text(text, encoding='utf-8')``
     - Write string to file
     - ``write``
   * - ``open(mode='r')``
     - Open file for reading/writing (context manager)
     - ``read`` or ``write``

Directory Operations
~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``mkdir(parents=False, exist_ok=False)``
     - Create directory
     - ``write``
   * - ``children()``
     - List child nodes (if directory)
     - ``read``
   * - ``child(*parts)``
     - Get child node by path components
     - None (navigation)

I/O Methods (use @smartasync)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These methods perform I/O and work in both sync and async contexts:

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``exists()``
     - True if file/directory exists
     - ``read``
   * - ``is_file()``
     - True if node is a file
     - ``read``
   * - ``is_dir()``
     - True if node is a directory
     - ``read``
   * - ``size()``
     - File size in bytes
     - ``read``
   * - ``mtime()``
     - Last modification time (Unix timestamp)
     - ``read``
   * - ``md5hash()``
     - MD5 hash of file content
     - ``read``

Non-I/O Properties (always sync)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

These properties do not perform I/O and are always synchronous:

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Property
     - Description
     - Type
   * - ``basename``
     - Filename with extension
     - ``str``
   * - ``stem``
     - Filename without extension
     - ``str``
   * - ``suffix``
     - File extension (including dot)
     - ``str``
   * - ``fullpath``
     - Full path including mount
     - ``str``
   * - ``path``
     - File system path (without mount prefix)
     - ``str``
   * - ``parent``
     - Parent directory node
     - ``StorageNode``
   * - ``capabilities``
     - Backend capabilities
     - ``BackendCapabilities``
   * - ``mimetype``
     - MIME type based on extension
     - ``str``

Copy and Move
~~~~~~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``copy_to(dest, skip='never', ...)``
     - Copy file/directory to destination with filtering and callbacks
     - ``read`` (source), ``write`` (dest)
   * - ``move_to(dest)``
     - Move file/directory to destination
     - ``read``, ``write``, ``delete``
   * - ``delete()``
     - Delete file/directory
     - ``delete``

Versioning
~~~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method/Property
     - Description
     - Capabilities Required
   * - ``version_count``
     - Number of versions (0 if not supported)
     - ``versioning``
   * - ``versions``
     - List of version metadata dicts
     - ``version_listing``
   * - ``open(version=-1)``
     - Open specific version for reading
     - ``version_access``
   * - ``compact_versions(dry_run=False)``
     - Remove consecutive duplicate versions
     - ``versioning``

Virtual Nodes
~~~~~~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Available On
   * - ``append(node)``
     - Append node to iternode
     - ``iternode`` only
   * - ``extend(*nodes)``
     - Extend iternode with multiple nodes
     - ``iternode`` only

Archiving
~~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``zip()``
     - Create ZIP archive: single file, directory (recursive), or iternode (multiple files)
     - ``read``

Metadata
~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``get_metadata()``
     - Get cloud metadata as dict
     - ``metadata``
   * - ``set_metadata(metadata)``
     - Set cloud metadata
     - ``metadata``

URLs
~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``url(expires_in=3600)``
     - Generate presigned URL (S3/GCS)
     - ``presigned_urls``
   * - ``internal_url(nocache=False)``
     - Get internal URL path
     - Backend-dependent
   * - ``to_base64(mime_type=None, data_uri=True)``
     - Encode file as base64/data URI
     - ``read``

Advanced
~~~~~~~~

.. list-table::
   :widths: 30 40 30
   :header-rows: 1

   * - Method
     - Description
     - Capabilities Required
   * - ``local_path(mode='r')``
     - Context manager for local filesystem path
     - ``read`` or ``write``
   * - ``call(command, *args, **kwargs)``
     - Execute external command with automatic temp file handling
     - ``read``, ``write``
   * - ``serve(environ, start_response, **kwargs)``
     - WSGI file serving with ETag support
     - ``read``
   * - ``fill_from_url(url, timeout=30)``
     - Download from URL and write to node
     - ``write``

Backend Capabilities
--------------------

Each backend reports its capabilities via the ``capabilities`` property.

Core Capabilities
~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 20 60 20
   :header-rows: 1

   * - Capability
     - Description
     - Default
   * - ``read``
     - Can read files
     - ``True``
   * - ``write``
     - Can write files
     - ``True``
   * - ``delete``
     - Can delete files/directories
     - ``True``
   * - ``readonly``
     - Backend is read-only
     - ``False``
   * - ``temporary``
     - Storage is temporary (memory)
     - ``False``

Advanced Capabilities
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 20 60 20
   :header-rows: 1

   * - Capability
     - Description
     - Default
   * - ``versioning``
     - Supports file versioning
     - ``False``
   * - ``version_listing``
     - Can list versions
     - ``False``
   * - ``version_access``
     - Can access specific versions
     - ``False``
   * - ``metadata``
     - Supports custom metadata
     - ``False``
   * - ``presigned_urls``
     - Can generate presigned URLs
     - ``False``

Backend Capability Matrix
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :widths: 15 15 15 15 15 15 10
   :header-rows: 1

   * - Backend
     - Read/Write
     - Delete
     - Versioning
     - Metadata
     - URLs
     - Temporary
   * - **Local**
     - ✓
     - ✓
     - ✗
     - ✗
     - ✗
     - ✗
   * - **S3**
     - ✓
     - ✓
     - ✓ *
     - ✓
     - ✓
     - ✗
   * - **GCS**
     - ✓
     - ✓
     - ✓ *
     - ✓
     - ✓
     - ✗
   * - **Azure**
     - ✓
     - ✓
     - ✓ *
     - ✓
     - ✓
     - ✗
   * - **HTTP**
     - Read only
     - ✗
     - ✗
     - ✗
     - ✗
     - ✗
   * - **Memory**
     - ✓
     - ✓
     - ✗
     - ✗
     - ✗
     - ✓
   * - **Base64**
     - Read/Write **
     - ✗
     - ✗
     - ✗
     - ✗
     - ✗

\* Versioning must be enabled on the bucket

\*\* Base64 backend is writable but path changes after write

Skip Strategies
---------------

When copying files, you can specify a skip strategy to avoid unnecessary operations.

.. list-table::
   :widths: 20 50 30
   :header-rows: 1

   * - Strategy
     - Behavior
     - Performance
   * - ``never``
     - Always copy (overwrite existing)
     - Fast (no checks)
   * - ``exists``
     - Skip if destination exists
     - Very fast (stat only)
   * - ``size``
     - Skip if same size
     - Fast (stat only)
   * - ``hash``
     - Skip if same MD5 hash
     - Medium (may use ETag)
   * - ``custom``
     - Use custom skip function via ``skip_fn`` parameter
     - Depends on function

Copy Parameters
---------------

Additional ``copy_to()`` parameters for advanced control:

.. list-table::
   :widths: 20 50 30
   :header-rows: 1

   * - Parameter
     - Description
     - Example
   * - ``filter``
     - Callable to filter files: ``filter(node, path) -> bool``
     - Filter by size, type, etc.
   * - ``skip_fn``
     - Custom skip function: ``skip_fn(src, dest) -> bool``
     - Required when ``skip='custom'``
   * - ``progress``
     - Progress callback: ``progress(current, total) -> None``
     - Update progress bar
   * - ``on_file``
     - Called for each file: ``on_file(node) -> None``
     - Logging, notifications
   * - ``on_skip``
     - Called when file skipped: ``on_skip(node, reason) -> None``
     - Track skipped files

Common Patterns
---------------

Incremental Backup
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Copy only changed files
    source.copy_to(dest, skip='hash')

Progress Tracking
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from tqdm import tqdm
    pbar = tqdm(desc="Copying")
    source.copy_to(dest, progress=lambda cur, tot: pbar.update(1))

Filter by Size
~~~~~~~~~~~~~~

.. code-block:: python

    # Copy only files smaller than 10MB
    source.copy_to(dest, filter=lambda node, path: node.size() < 10_000_000)

Custom Skip Logic
~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Skip if destination is newer
    def skip_if_newer(src, dest):
        if not dest.exists():
            return False
        return dest.mtime() > src.mtime()

    source.copy_to(dest, skip='custom', skip_fn=skip_if_newer)

Copy with Callbacks
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Log each file and track skips
    def log_file(node):
        print(f"Copied: {node.path}")

    def log_skip(node, reason):
        print(f"Skipped {node.path}: {reason}")

    source.copy_to(dest, skip='hash', on_file=log_file, on_skip=log_skip)

Lazy Concatenation
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Build document from parts
    builder = storage.iternode(header, body, footer)
    builder.append(appendix)
    builder.copy_to(storage.node('result.txt'))

Generate Diff
~~~~~~~~~~~~~

.. code-block:: python

    # Compare versions
    diff = storage.diffnode(version1, version2)
    diff.copy_to(storage.node('changes.diff'))

Create ZIP Archive
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Zip a single file
    file = storage.node('data:report.pdf')
    zip_bytes = file.zip()
    storage.node('data:report.zip').write_bytes(zip_bytes)

    # Zip entire directory (recursive)
    folder = storage.node('data:documents/')
    zip_bytes = folder.zip()

    # Zip multiple files (iternode)
    archive = storage.iternode(file1, file2, file3)
    zip_bytes = archive.zip()

Sync vs Async Usage
-------------------

All I/O methods work transparently in both contexts:

Sync Context
~~~~~~~~~~~~

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([
        {'name': 'data', 'protocol': 'local', 'base_path': '/data'}
    ])

    node = storage.node('data:file.txt')

    # Direct calls
    if node.exists():
        content = node.read_text()
        print(f"Size: {node.size()} bytes")

Async Context
~~~~~~~~~~~~~

.. code-block:: python

    from genro_storage import StorageManager
    import asyncio

    storage = StorageManager()
    storage.configure([
        {'name': 'data', 'protocol': 'local', 'base_path': '/data'}
    ])

    async def example():
        node = storage.node('data:file.txt')

        # Awaited calls
        if await node.exists():
            content = await node.read_text()
            print(f"Size: {await node.size()} bytes")

    asyncio.run(example())

FastAPI Integration
~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from fastapi import FastAPI, HTTPException
    from genro_storage import StorageManager

    app = FastAPI()
    storage = StorageManager()
    storage.configure([
        {'name': 'uploads', 'protocol': 's3', 'bucket': 'my-bucket'}
    ])

    @app.get("/files/{filepath:path}")
    async def get_file(filepath: str):
        node = storage.node(f'uploads:{filepath}')

        if not await node.exists():
            raise HTTPException(status_code=404)

        return {
            "data": await node.read_bytes(),
            "size": await node.size(),
            "mime_type": node.mimetype  # Non-I/O property (sync)
        }

Concurrent Operations
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    import asyncio

    async def process_multiple(file_list):
        async def process_one(filepath):
            node = storage.node(f'uploads:{filepath}')
            if await node.exists():
                data = await node.read_bytes()
                return len(data)
            return 0

        # Process all files concurrently
        sizes = await asyncio.gather(*[process_one(f) for f in file_list])
        return sum(sizes)

Implementation Notes
--------------------

- Built on ``@smartasync`` from ``genro-toolbox`` for automatic sync/async detection
- In sync context: methods execute directly
- In async context: methods use ``asyncio.to_thread()`` for non-blocking I/O
- Same ``StorageManager`` and ``StorageNode`` classes for both contexts
- No separate ``AsyncStorageManager`` needed (removed in v0.6.0)
