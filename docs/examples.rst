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

Working with External Tools
----------------------------

Use ``local_path()`` to integrate with external tools that require local filesystem access:

.. code-block:: python

    # Process video with ffmpeg
    video = storage.node('s3:videos/input.mp4')
    output = storage.node('s3:videos/output.mp4')

    with video.local_path(mode='r') as input_path:
        with output.local_path(mode='w') as output_path:
            import subprocess
            subprocess.run([
                'ffmpeg', '-i', input_path,
                '-vcodec', 'h264', '-crf', '28',
                output_path
            ])
    # Changes automatically uploaded to S3

    # Modify image in place
    image = storage.node('uploads:photo.jpg')
    with image.local_path(mode='rw') as path:
        subprocess.run(['convert', path, '-resize', '800x600', path])

Dynamic Paths for Multi-User Apps
----------------------------------

Use callable paths that resolve at runtime:

.. code-block:: python

    def get_user_directory():
        from flask import g  # or your framework's context
        return f'/data/users/{g.user_id}'

    storage.configure([
        {'name': 'user', 'type': 'local', 'path': get_user_directory}
    ])

    # Different user, different directory!
    # User 123: /data/users/123/
    # User 456: /data/users/456/
    user_prefs = storage.node('user:preferences.json')

Cloud Metadata Management
--------------------------

Set and retrieve custom metadata on cloud files:

.. code-block:: python

    # Set metadata
    doc = storage.node('s3:documents/report.pdf')
    doc.set_metadata({
        'Author': 'John Doe',
        'Department': 'Engineering',
        'Version': '1.0',
        'Classification': 'Internal'
    })

    # Get metadata
    metadata = doc.get_metadata()
    print(f"Author: {metadata.get('Author')}")
    print(f"Version: {metadata.get('Version')}")

URL Generation
--------------

Generate shareable URLs for files:

.. code-block:: python

    # Generate S3 presigned URL (expires in 1 hour)
    file = storage.node('s3:documents/report.pdf')
    url = file.url(expires_in=3600)
    print(f"Share this: {url}")

    # Custom expiration (24 hours)
    long_url = file.url(expires_in=86400)

    # Convert file to data URI
    logo = storage.node('local:assets/logo.png')
    data_uri = logo.to_base64()
    # Use in HTML: <img src="data:image/png;base64,...">

Download from URLs
------------------

Download files from the internet directly to storage:

.. code-block:: python

    # Download to local storage
    local_file = storage.node('data:downloads/dataset.csv')
    local_file.fill_from_url('https://example.com/data.csv')

    # Download to S3
    s3_file = storage.node('s3:archives/backup.zip')
    s3_file.fill_from_url('https://backups.example.com/latest.zip', timeout=300)

S3 Versioning
-------------

Access historical versions when S3 versioning is enabled:

.. code-block:: python

    # Get list of versions
    doc = storage.node('s3:documents/contract.pdf')
    versions = doc.versions

    for v in versions:
        print(f"Version {v['version_id']}")
        print(f"  Modified: {v['last_modified']}")
        print(f"  Size: {v['size']} bytes")
        print(f"  Latest: {v['is_latest']}")

    # Open specific version
    if versions:
        old_version_id = versions[1]['version_id']
        with doc.open_version(old_version_id) as f:
            old_content = f.read()
            print("Previous version:", old_content)
