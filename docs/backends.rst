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
