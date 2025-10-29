Configuration Guide
===================

This guide explains how to configure storage backends in genro-storage.

Overview
--------

Storage backends are configured through the ``StorageManager.configure()`` method.
You can configure storage from:

1. **Python dictionaries** - for programmatic configuration
2. **YAML files** - for declarative configuration
3. **JSON files** - for declarative configuration

All configuration methods support the same format and backends.

Configuration Methods
---------------------

From Python Dictionaries
~~~~~~~~~~~~~~~~~~~~~~~~~

The most flexible method for programmatic configuration:

.. code-block:: python

    from genro_storage import StorageManager
    
    storage = StorageManager()
    storage.configure([
        {
            'name': 'home',
            'type': 'local',
            'path': '/home/user'
        },
        {
            'name': 'uploads',
            'type': 's3',
            'bucket': 'my-app-uploads',
            'region': 'eu-west-1'
        }
    ])

From YAML Files
~~~~~~~~~~~~~~~

Best for environment-specific configuration files:

**storage.yaml:**

.. code-block:: yaml

    # Local development storage
    - name: home
      type: local
      path: /home/user
    
    - name: temp
      type: local
      path: /tmp/app
    
    # Production S3 storage
    - name: uploads
      type: s3
      bucket: prod-app-uploads
      region: eu-west-1
      prefix: uploads/
    
    - name: backups
      type: s3
      bucket: prod-app-backups
      region: eu-west-1

**Python code:**

.. code-block:: python

    storage = StorageManager()
    storage.configure('/etc/app/storage.yaml')

From JSON Files
~~~~~~~~~~~~~~~

Alternative to YAML:

**storage.json:**

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
            "bucket": "prod-app-uploads",
            "region": "eu-west-1"
        }
    ]

**Python code:**

.. code-block:: python

    storage = StorageManager()
    storage.configure('./config/storage.json')

Storage Backend Types
---------------------

Local Filesystem
~~~~~~~~~~~~~~~~

Access files on the local filesystem.

**Required fields:**

- ``name``: Mount point name
- ``type``: Must be ``"local"``
- ``path``: Absolute path to base directory

**Example:**

.. code-block:: yaml

    - name: home
      type: local
      path: /home/user
    
    - name: temp
      type: local
      path: /tmp/app

.. code-block:: python

    storage.configure([
        {'name': 'home', 'type': 'local', 'path': '/home/user'},
        {'name': 'temp', 'type': 'local', 'path': '/tmp/app'}
    ])

**Usage:**

.. code-block:: python

    node = storage.node('home:documents/report.pdf')
    content = node.read_text()

Amazon S3
~~~~~~~~~

Access files in Amazon S3 buckets.

**Required fields:**

- ``name``: Mount point name
- ``type``: Must be ``"s3"``
- ``bucket``: S3 bucket name

**Optional fields:**

- ``prefix``: Path prefix within bucket (default: ``""``)
- ``region``: AWS region (default: from AWS config)
- ``anon``: Anonymous access (default: ``False``)
- ``key``: AWS access key (default: from AWS config)
- ``secret``: AWS secret key (default: from AWS config)
- ``endpoint_url``: Custom S3 endpoint for S3-compatible services

**Example:**

.. code-block:: yaml

    # Standard S3
    - name: uploads
      type: s3
      bucket: my-app-uploads
      region: eu-west-1
      prefix: uploads/
    
    # With credentials
    - name: backups
      type: s3
      bucket: my-app-backups
      region: us-east-1
      key: AKIAIOSFODNN7EXAMPLE
      secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
    
    # Anonymous public bucket
    - name: public-data
      type: s3
      bucket: public-datasets
      anon: true

**Usage:**

.. code-block:: python

    # Upload file
    node = storage.node('uploads:2024/report.pdf')
    node.write_bytes(pdf_data)
    
    # List directory
    folder = storage.node('uploads:2024')
    for file in folder.children():
        print(f"{file.basename}: {file.size} bytes")

Google Cloud Storage
~~~~~~~~~~~~~~~~~~~~

Access files in Google Cloud Storage buckets.

**Required fields:**

- ``name``: Mount point name
- ``type``: Must be ``"gcs"``
- ``bucket``: GCS bucket name

**Optional fields:**

- ``prefix``: Path prefix within bucket (default: ``""``)
- ``token``: Path to service account JSON key file
- ``project``: GCP project ID

**Example:**

.. code-block:: yaml

    - name: backups
      type: gcs
      bucket: my-app-backups
      project: my-gcp-project
      token: /etc/secrets/gcp-service-account.json

.. code-block:: python

    storage.configure([{
        'name': 'backups',
        'type': 'gcs',
        'bucket': 'my-app-backups',
        'token': '/etc/secrets/gcp-service-account.json'
    }])

Azure Blob Storage
~~~~~~~~~~~~~~~~~~

Access files in Azure Blob Storage containers.

**Required fields:**

- ``name``: Mount point name
- ``type``: Must be ``"azure"``
- ``container``: Container name
- ``account_name``: Storage account name

**Optional fields:**

- ``account_key``: Storage account key
- ``sas_token``: Shared access signature token
- ``connection_string``: Full connection string

**Example:**

.. code-block:: yaml

    - name: archive
      type: azure
      container: archives
      account_name: mystorageaccount
      account_key: xxxxxxxxxxxxxxxxxxxxx

HTTP Storage (Read-Only)
~~~~~~~~~~~~~~~~~~~~~~~~~

Access files via HTTP/HTTPS (read-only).

**Required fields:**

- ``name``: Mount point name
- ``type``: Must be ``"http"``
- ``base_url``: Base URL for HTTP requests

**Example:**

.. code-block:: yaml

    - name: cdn
      type: http
      base_url: https://cdn.example.com

.. code-block:: python

    storage.configure([{
        'name': 'cdn',
        'type': 'http',
        'base_url': 'https://cdn.example.com'
    }])
    
    # Read-only access
    node = storage.node('cdn:assets/logo.png')
    image_data = node.read_bytes()

Memory Storage (Testing)
~~~~~~~~~~~~~~~~~~~~~~~~~

In-memory storage for testing and development.

**Required fields:**

- ``name``: Mount point name
- ``type``: Must be ``"memory"``

**Example:**

.. code-block:: python

    # Perfect for unit tests
    storage.configure([{'name': 'test', 'type': 'memory'}])
    
    node = storage.node('test:temp.txt')
    node.write_text("test data")
    assert node.read_text() == "test data"

Advanced Configuration
----------------------

Multiple Configurations
~~~~~~~~~~~~~~~~~~~~~~~

You can call ``configure()`` multiple times. Mounts with the same name
are replaced:

.. code-block:: python

    # Initial setup
    storage.configure([
        {'name': 'home', 'type': 'local', 'path': '/home/user'}
    ])
    
    # Add more mounts later
    storage.configure([
        {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
    ])
    
    # Replace existing mount
    storage.configure([
        {'name': 'home', 'type': 'local', 'path': '/mnt/newlocation'}
    ])

Environment-Specific Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Use different configuration files per environment:

.. code-block:: python

    import os
    
    storage = StorageManager()
    
    # Load environment-specific config
    env = os.getenv('APP_ENV', 'development')
    config_file = f'/etc/app/storage-{env}.yaml'
    storage.configure(config_file)

**storage-development.yaml:**

.. code-block:: yaml

    - name: uploads
      type: local
      path: /tmp/dev-uploads

**storage-production.yaml:**

.. code-block:: yaml

    - name: uploads
      type: s3
      bucket: prod-uploads
      region: eu-west-1

Configuration from Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Build configuration dynamically from environment:

.. code-block:: python

    import os
    
    storage = StorageManager()
    storage.configure([
        {
            'name': 'uploads',
            'type': 's3',
            'bucket': os.getenv('S3_BUCKET'),
            'region': os.getenv('AWS_REGION', 'eu-west-1'),
            'key': os.getenv('AWS_ACCESS_KEY_ID'),
            'secret': os.getenv('AWS_SECRET_ACCESS_KEY')
        }
    ])

Checking Configured Mounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # List all configured mounts
    print(storage.get_mount_names())
    # ['home', 'uploads', 'temp']
    
    # Check if mount exists
    if storage.has_mount('uploads'):
        node = storage.node('uploads:file.txt')
    else:
        print("Uploads storage not configured")

Complete Example
----------------

**config/storage-prod.yaml:**

.. code-block:: yaml

    # Local temporary storage
    - name: temp
      type: local
      path: /tmp/app
    
    # User uploads to S3
    - name: uploads
      type: s3
      bucket: prod-app-uploads
      region: eu-west-1
      prefix: uploads/
    
    # Backups to GCS
    - name: backups
      type: gcs
      bucket: prod-app-backups
      token: /etc/secrets/gcp-key.json
    
    # Static assets from CDN
    - name: cdn
      type: http
      base_url: https://cdn.example.com

**Python application:**

.. code-block:: python

    from genro_storage import StorageManager
    
    # Initialize and configure
    storage = StorageManager()
    storage.configure('/etc/app/storage-prod.yaml')
    
    # Process upload
    upload = storage.node('temp:processing/image.jpg')
    upload.write_bytes(uploaded_data)
    
    # Save to S3
    final = storage.node('uploads:2024/images/photo.jpg')
    upload.copy_to(final)
    
    # Backup to GCS
    backup = storage.node('backups:daily/2024-10-26/photo.jpg')
    final.copy_to(backup)
    
    # Cleanup temp
    upload.delete()
    
    # Access CDN asset
    logo = storage.node('cdn:assets/logo.png')
    logo_data = logo.read_bytes()

Best Practices
--------------

1. **Use YAML for declarative configs** - easier to read and maintain
2. **Separate configs per environment** - development, staging, production
3. **Store credentials securely** - use secrets managers, not config files
4. **Use meaningful mount names** - ``uploads``, ``backups``, not ``s3_1``
5. **Configure once at startup** - don't reconfigure during runtime
6. **Use prefixes in cloud storage** - organize files within buckets
7. **Test with memory backend** - fast, no cleanup needed

Troubleshooting
---------------

**Mount not found error:**

.. code-block:: python

    # Error: StorageNotFoundError: Mount point 'uploads' not found
    node = storage.node('uploads:file.txt')
    
    # Check configured mounts
    print(storage.get_mount_names())
    
    # Verify mount is configured
    if not storage.has_mount('uploads'):
        storage.configure([{'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}])

**Invalid configuration:**

.. code-block:: python

    # Missing required field
    storage.configure([{'name': 'uploads', 'type': 's3'}])  # Missing 'bucket'!
    # Raises: StorageConfigError: Missing required field 'bucket' for S3 storage

**Path escaping base directory:**

.. code-block:: python

    storage.configure([{'name': 'home', 'type': 'local', 'path': '/home/user'}])
    node = storage.node('home:../../../etc/passwd')
    # Raises: ValueError: Path escapes base directory
