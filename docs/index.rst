genro-storage Documentation
===========================

**Universal storage abstraction for Python with pluggable backends**

``genro-storage`` provides a unified interface for accessing files across local filesystems, 
cloud storage (S3, GCS, Azure), and remote protocols (HTTP, SFTP). Built on top of **fsspec**, 
it adds an intuitive mount-point system and user-friendly API inspired by Unix filesystems.

Features
--------

* **Async/await support** - Use in FastAPI, asyncio apps with AsyncStorageManager (NEW in v0.3.0!)
* **Powered by fsspec** - Leverage 20+ battle-tested storage backends
* **Mount point system** - Organize storage with logical names like ``home:``, ``uploads:``, ``s3:``
* **Intuitive API** - Pathlib-inspired interface that feels natural and Pythonic
* **Dynamic paths** - Callable paths that resolve at runtime for user-specific directories
* **External tool integration** - ``local_path()`` for seamless ffmpeg, imagemagick integration
* **Cloud metadata** - Get/set custom metadata on S3, GCS, Azure files
* **URL generation** - Generate presigned URLs, data URIs for sharing
* **S3 versioning** - Access historical file versions when versioning enabled
* **Flexible configuration** - Load mounts from YAML, JSON, databases, or code
* **Test-friendly** - In-memory backend for fast, isolated testing
* **Production-ready** - Built on 6+ years of Genropy production experience
* **Cross-storage operations** - Copy/move files between different storage types seamlessly

Quick Example
-------------

Synchronous Usage
~~~~~~~~~~~~~~~~~

.. code-block:: python

    from genro_storage import StorageManager

    # Configure storage backends
    storage = StorageManager()
    storage.configure([
        {'name': 'home', 'type': 'local', 'path': '/home/user'},
        {'name': 'uploads', 'type': 's3', 'bucket': 'my-app-uploads'},
        {'name': 'backups', 'type': 'gcs', 'bucket': 'my-backups'}
    ])

    # Work with files using a unified API
    node = storage.node('uploads:users/123/avatar.jpg')
    if node.exists:
        # Copy from S3 to local
        node.copy_to(storage.node('home:cache/avatar.jpg'))

        # Read and process
        data = node.read_bytes()

        # Backup to GCS
        node.copy_to(storage.node('backups:avatars/user_123.jpg'))

Async Usage (NEW in v0.3.0!)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from genro_storage import AsyncStorageManager

    # Configure
    storage = AsyncStorageManager()
    storage.configure([
        {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
    ])

    # Use in async context
    async def process_file(filepath: str):
        node = storage.node(f'uploads:{filepath}')

        if await node.exists():
            data = await node.read_bytes()
            size = await node.size()
            return data

Installation
------------

.. code-block:: bash

    # Basic installation (local storage only)
    pip install genro-storage

    # With cloud storage support
    pip install genro-storage[s3]      # Amazon S3
    pip install genro-storage[gcs]     # Google Cloud Storage
    pip install genro-storage[azure]   # Azure Blob Storage
    pip install genro-storage[async]   # Async support (NEW in v0.3.0!)
    pip install genro-storage[all]     # All backends + async

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   overview
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   configuration
   backends
   examples
   advanced

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

.. toctree::
   :maxdepth: 2
   :caption: Appendices

   api_reference
   capabilities
   versioning

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
