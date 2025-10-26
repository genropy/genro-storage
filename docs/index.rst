genro-storage Documentation
===========================

**Universal storage abstraction for Python with pluggable backends**

``genro-storage`` provides a unified interface for accessing files across local filesystems, 
cloud storage (S3, GCS, Azure), and remote protocols (HTTP, SFTP). Built on top of **fsspec**, 
it adds an intuitive mount-point system and user-friendly API inspired by Unix filesystems.

Features
--------

* **Powered by fsspec** - Leverage 20+ battle-tested storage backends
* **Mount point system** - Organize storage with logical names like ``home:``, ``uploads:``, ``s3:``
* **Intuitive API** - Pathlib-inspired interface that feels natural and Pythonic
* **Flexible configuration** - Load mounts from YAML, JSON, databases, or code
* **Test-friendly** - In-memory backend for fast, isolated testing
* **Production-ready** - Built on 6+ years of Genropy production experience
* **Cross-storage operations** - Copy/move files between different storage types seamlessly

Quick Example
-------------

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
        node.copy(storage.node('home:cache/avatar.jpg'))
        
        # Read and process
        data = node.read_bytes()
        
        # Backup to GCS
        node.copy(storage.node('backups:avatars/user_123.jpg'))

Installation
------------

.. code-block:: bash

    # Basic installation (local storage only)
    pip install genro-storage

    # With cloud storage support
    pip install genro-storage[s3]      # Amazon S3
    pip install genro-storage[gcs]     # Google Cloud Storage
    pip install genro-storage[azure]   # Azure Blob Storage
    pip install genro-storage[full]    # All backends

Documentation Contents
----------------------

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   quickstart
   configuration
   backends
   examples

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api

.. toctree::
   :maxdepth: 1
   :caption: Development

   contributing
   changelog

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
