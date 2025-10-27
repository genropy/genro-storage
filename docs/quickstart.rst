Quick Start Guide
=================

This guide will help you get started with ``genro-storage`` in just a few minutes.

Installation
------------

Install the base package:

.. code-block:: bash

    pip install genro-storage

For cloud storage support, install optional dependencies:

.. code-block:: bash

    # Amazon S3
    pip install genro-storage[s3]
    
    # Google Cloud Storage
    pip install genro-storage[gcs]
    
    # Azure Blob Storage
    pip install genro-storage[azure]
    
    # All backends
    pip install genro-storage[full]

Basic Concepts
--------------

Mount Points
~~~~~~~~~~~~

A **mount point** is a logical name that maps to a storage backend. Think of it like Unix mount points:

* ``home:`` → local directory ``/home/user``
* ``uploads:`` → S3 bucket ``my-app-uploads``
* ``cache:`` → in-memory storage

Storage Paths
~~~~~~~~~~~~~

Files are referenced using the format ``mount:path/to/file``:

.. code-block:: python

    'home:documents/report.pdf'
    'uploads:users/123/avatar.jpg'
    's3:backups/2024/data.tar.gz'

First Steps
-----------

1. Create a Storage Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()

2. Configure Mount Points
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    storage.configure([
        {'name': 'home', 'type': 'local', 'path': '/home/user'},
        {'name': 'temp', 'type': 'local', 'path': '/tmp'}
    ])

3. Create Storage Nodes
~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Point to a file
    node = storage.node('home:documents/report.pdf')
    
    # Or build path dynamically
    node = storage.node('home', 'documents', 'report.pdf')

4. Work with Files
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Write
    node.write_text("Hello World")
    
    # Read
    content = node.read_text()
    
    # Check existence
    if node.exists:
        print(f"File size: {node.size} bytes")
    
    # Copy
    node.copy('temp:backup.pdf')
    
    # Delete
    node.delete()

Complete Example
----------------

Here's a complete working example:

.. code-block:: python

    from genro_storage import StorageManager

    # Setup
    storage = StorageManager()
    storage.configure([
        {'name': 'data', 'type': 'local', 'path': './data'},
        {'name': 'archive', 'type': 'local', 'path': './archive'}
    ])

    # Create and write a file
    report = storage.node('data:reports/2024-q4.txt')
    report.write_text(\"\"\"
Q4 2024 Sales Report
====================
Total Sales: 1234567
Growth: +15%
\"\"\")

    # Read and process
    content = report.read_text()
    print(f"Report size: {report.size} bytes")
    print(f"Modified: {report.mtime}")

    # Archive the report
    archive_node = storage.node('archive:reports/2024-q4.txt')
    report.copy(archive_node)

    # List all files in data/reports
    reports_dir = storage.node('data:reports')
    if reports_dir.isdir:
        for child in reports_dir.children():
            print(f"- {child.basename} ({child.size} bytes)")

Working with Directories
-------------------------

Create directories:

.. code-block:: python

    # Create single directory
    dir_node = storage.node('data:new_folder')
    dir_node.mkdir()
    
    # Create nested directories
    nested = storage.node('data:level1/level2/level3')
    nested.mkdir(parents=True)

List directory contents:

.. code-block:: python

    dir_node = storage.node('data:reports')
    
    for child in dir_node.children():
        if child.isfile:
            print(f"File: {child.basename}")
        elif child.isdir:
            print(f"Directory: {child.basename}")

Navigate directory tree:

.. code-block:: python

    file_node = storage.node('data:reports/2024/q4.pdf')
    
    # Get parent directory
    reports_2024 = file_node.parent
    
    # Get sibling file
    q3_report = reports_2024.child('q3.pdf')
    
    # Navigate up
    reports_dir = reports_2024.parent

Configuration from File
-----------------------

YAML Configuration
~~~~~~~~~~~~~~~~~~

Create ``storage.yaml``:

.. code-block:: yaml

    - name: home
      type: local
      path: /home/user
    
    - name: uploads
      type: s3
      bucket: my-app-uploads
      region: eu-west-1
    
    - name: cache
      type: memory

Load it:

.. code-block:: python

    storage = StorageManager()
    storage.configure('storage.yaml')

JSON Configuration
~~~~~~~~~~~~~~~~~~

Create ``storage.json``:

.. code-block:: json

    [
      {
        "name": "home",
        "type": "local",
        "path": "/home/user"
      },
      {
        "name": "uploads",
        "type": "s3",
        "bucket": "my-app-uploads",
        "region": "eu-west-1"
      }
    ]

Load it:

.. code-block:: python

    storage = StorageManager()
    storage.configure('storage.json')

Cross-Storage Operations
------------------------

Copy files between different storage backends:

.. code-block:: python

    storage.configure([
        {'name': 'local', 'type': 'local', 'path': '/tmp'},
        {'name': 's3', 'type': 's3', 'bucket': 'my-bucket'}
    ])

    # Process locally
    local_file = storage.node('local:processing/image.jpg')
    local_file.write_bytes(processed_data)

    # Upload to S3
    s3_file = storage.node('s3:uploads/2024/image.jpg')
    local_file.copy(s3_file)

    # Cleanup
    local_file.delete()

Next Steps
----------

* Learn about :doc:`configuration` options
* Explore available :doc:`backends`
* See more :doc:`examples`
* Read the complete :doc:`api` reference
