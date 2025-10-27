Storage Backends
================

This page describes the available storage backends and their configuration options.

Overview
--------

genro-storage supports multiple storage backends through fsspec. Each backend is configured
with a mount point name and backend-specific parameters.

Local Storage
-------------

Store files on the local filesystem.

**Configuration:**

.. code-block:: python

    {
        'name': 'home',
        'type': 'local',
        'path': '/home/user'  # required: absolute path
    }

**Use cases:**
- Development and testing
- Local file processing
- Temporary storage

Memory Storage
--------------

In-memory storage for testing.

**Configuration:**

.. code-block:: python

    {
        'name': 'test',
        'type': 'memory'
    }

**Use cases:**
- Unit testing
- Fast temporary storage
- Mock storage in tests

Amazon S3
---------

Store files in Amazon S3 buckets.

**Installation:**

.. code-block:: bash

    pip install genro-storage[s3]

**Configuration:**

.. code-block:: python

    {
        'name': 'uploads',
        'type': 's3',
        'bucket': 'my-bucket',      # required
        'prefix': 'uploads/',       # optional
        'region': 'eu-west-1',      # optional
        'anon': False               # optional: anonymous access
    }

**Authentication:**

Uses boto3 credentials (environment variables, ~/.aws/credentials, or IAM roles).

Google Cloud Storage
--------------------

Store files in Google Cloud Storage buckets.

**Installation:**

.. code-block:: bash

    pip install genro-storage[gcs]

**Configuration:**

.. code-block:: python

    {
        'name': 'backups',
        'type': 'gcs',
        'bucket': 'my-backups',           # required
        'prefix': '',                     # optional
        'token': 'path/to/key.json'       # optional
    }

Azure Blob Storage
------------------

Store files in Azure Blob Storage.

**Installation:**

.. code-block:: bash

    pip install genro-storage[azure]

**Configuration:**

.. code-block:: python

    {
        'name': 'archive',
        'type': 'azure',
        'container': 'archives',          # required
        'account_name': 'myaccount',      # required
        'account_key': '...'              # optional
    }

HTTP Storage
------------

Read-only access to files via HTTP.

**Configuration:**

.. code-block:: python

    {
        'name': 'cdn',
        'type': 'http',
        'base_url': 'https://cdn.example.com'  # required
    }

**Note:** HTTP storage is read-only.

Base64 Storage
--------------

Store data inline as base64-encoded strings, similar to data URIs.

**Configuration:**

.. code-block:: python

    {
        'name': 'data',
        'type': 'base64'
    }

**Usage:**

.. code-block:: python

    # Read inline base64 data
    node = storage.node('data:SGVsbG8gV29ybGQ=')  # "Hello World" encoded
    content = node.read_text()  # Returns "Hello World"

    # Write creates/updates the base64 path (writable with mutable paths)
    node = storage.node('data:')
    node.write_text("New content")
    print(node.path)  # TmV3IGNvbnRlbnQ= (base64 encoded)

    # Copy from other storage to base64 for inline use
    s3_image = storage.node('uploads:photo.jpg')
    b64_image = storage.node('data:')
    s3_image.copy(b64_image)
    data_uri = f"data:image/jpeg;base64,{b64_image.path}"

**Use cases:**

- Embed small files directly in configuration or databases
- Create data URIs for inline images in HTML/CSS
- Store secrets or tokens as encoded strings
- Testing with inline test data

**Features:**

- Read from base64-encoded paths
- Write to create/update base64 content (path updates automatically)
- Supports both text and binary data
- Automatic encoding/decoding
- Compatible with standard base64 encoding
- Handles multiline base64 strings

**Limitations:**

- Not suitable for large files (base64 increases size by ~33%)
- Path changes after every write (mutable path behavior)
- No directory operations (delete, mkdir, list_dir raise errors)
