Examples
========

This page provides complete working examples for common use cases.

Basic File Operations
---------------------

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([
        {'name': 'data', 'type': 'local', 'path': './data'}
    ])

    # Write a file
    node = storage.node('data:report.txt')
    node.write_text("Q4 Report: Sales increased by 15%")

    # Read the file
    content = node.read_text()
    print(content)

    # Check file properties
    print(f"Size: {node.size} bytes")
    print(f"Exists: {node.exists}")

Multi-Cloud Setup
-----------------

.. code-block:: python

    storage = StorageManager()
    storage.configure([
        {'name': 'local', 'type': 'local', 'path': '/tmp'},
        {'name': 's3', 'type': 's3', 'bucket': 'my-bucket'},
        {'name': 'gcs', 'type': 'gcs', 'bucket': 'my-backups'}
    ])

    # Process locally
    local = storage.node('local:processing/data.json')
    local.write_text('{"result": "processed"}')

    # Upload to S3
    local.copy('s3:results/data.json')

    # Backup to GCS
    local.copy('gcs:backups/data.json')

Directory Operations
--------------------

.. code-block:: python

    # Create nested directories
    storage.node('data:reports/2024/Q4').mkdir(parents=True)

    # List directory contents
    reports = storage.node('data:reports')
    for child in reports.children():
        if child.isfile:
            print(f"File: {child.basename} ({child.size} bytes)")
        else:
            print(f"Dir: {child.basename}")

Configuration from File
-----------------------

Create config.yaml:

.. code-block:: yaml

    - name: home
      type: local
      path: /home/user

    - name: uploads
      type: s3
      bucket: prod-uploads
      region: eu-west-1

Load and use:

.. code-block:: python

    storage = StorageManager()
    storage.configure('config.yaml')
    
    node = storage.node('uploads:users/123/avatar.jpg')
