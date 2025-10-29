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
    content = node.read()  # Returns "Hello World"

    # Write creates/updates the base64 path (writable with mutable paths)
    node = storage.node('data:')
    node.write("New content")
    print(node.path)  # TmV3IGNvbnRlbnQ= (base64 encoded)

    # Copy from other storage to base64 for inline use
    s3_image = storage.node('uploads:photo.jpg')
    b64_image = storage.node('data:')
    s3_image.copy_to(b64_image)
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

SMB/CIFS Storage
----------------

Access Windows and Samba network shares.

**Installation:**

.. code-block:: bash

    pip install genro-storage[smb]

**Configuration:**

.. code-block:: python

    {
        'name': 'fileserver',
        'type': 'smb',
        'host': '192.168.1.100',      # required: SMB server
        'share': 'documents',         # required: share name
        'username': 'user',           # optional
        'password': 'secret',         # optional
        'domain': 'WORKGROUP',        # optional
        'port': 445                   # optional (default: 445)
    }

**Authentication:**

SMB supports both guest access (no credentials) and authenticated access with username/password.
For domain environments, specify the domain parameter.

**Use cases:**

- Access files on Windows file servers
- Connect to NAS devices with SMB/CIFS support
- Integrate with corporate network shares
- Cross-platform file sharing in enterprise environments

**Features:**

- Full read/write support
- Directory operations (mkdir, list, delete)
- Works with Windows, Samba, and NAS devices
- Supports SMB2/SMB3 protocols

SFTP/SSH Storage
----------------

Secure file transfer over SSH.

**Installation:**

.. code-block:: bash

    pip install genro-storage[sftp]

**Configuration:**

.. code-block:: python

    # Password authentication
    {
        'name': 'server1',
        'type': 'sftp',
        'host': 'server.example.com',    # required
        'username': 'deploy',             # required
        'password': 'secret',             # optional
        'port': 22                        # optional (default: 22)
    }

    # Key-based authentication
    {
        'name': 'server2',
        'type': 'sftp',
        'host': '192.168.1.50',
        'username': 'user',
        'key_filename': '/home/user/.ssh/id_rsa',  # optional
        'passphrase': 'keypass',                    # optional
        'timeout': 30                               # optional
    }

**Authentication:**

Supports both password and SSH key-based authentication. Key-based authentication
is recommended for automated deployments and CI/CD pipelines.

**Use cases:**

- Secure file transfer to Linux/Unix servers
- Automated deployments via SSH
- Access files on VPS and cloud instances
- Backup and sync operations over secure connections

**Features:**

- Full read/write support
- Directory operations
- SSH key and password authentication
- Configurable timeouts

ZIP Archives
------------

Access ZIP archives as virtual filesystems.

**Configuration:**

.. code-block:: python

    # Read from existing ZIP
    {
        'name': 'backup',
        'type': 'zip',
        'file': '/backups/data.zip',     # required: path to ZIP file
        'mode': 'r'                       # optional: 'r', 'w', 'a' (default: 'r')
    }

    # Create new ZIP
    {
        'name': 'archive',
        'type': 'zip',
        'file': '/output/archive.zip',
        'mode': 'w'
    }

**Usage:**

.. code-block:: python

    # Read from ZIP archive
    node = storage.node('backup:config/settings.json')
    config = node.read()

    # Extract specific file
    log = storage.node('backup:logs/app.log')
    log.copy_to(storage.node('home:extracted_log.txt'))

    # Create new archive
    source = storage.node('home:documents/report.pdf')
    source.copy_to(storage.node('archive:reports/report.pdf'))

**Use cases:**

- Read configuration from deployment archives
- Extract specific files without full decompression
- Create backup archives programmatically
- Distribute application bundles

**Features:**

- Read and write support
- Transparent compression
- Standard ZIP format compatibility
- Fast random access to archived files

**Note:** Built-in to fsspec, no additional dependencies required.

TAR Archives
------------

Read TAR archives (including compressed .tar.gz, .tar.bz2, .tar.xz).

**Configuration:**

.. code-block:: python

    # Read TAR archive
    {
        'name': 'logs',
        'type': 'tar',
        'file': '/var/log/archive.tar.gz'   # required: path to TAR file
    }

    # Compression auto-detected from extension
    {
        'name': 'backup',
        'type': 'tar',
        'file': '/backups/data.tar.bz2'
    }

**Usage:**

.. code-block:: python

    # Read from TAR archive
    node = storage.node('logs:app.log')
    content = node.read()

    # List archive contents
    for item in storage.node('logs:').list():
        print(item)

    # Extract to local storage
    archived = storage.node('backup:important.txt')
    archived.copy_to(storage.node('home:restored.txt'))

**Supported compressions:**

- ``.tar`` - Uncompressed TAR
- ``.tar.gz`` or ``.tgz`` - Gzip compressed
- ``.tar.bz2`` - Bzip2 compressed
- ``.tar.xz`` - XZ/LZMA compressed

Compression is automatically detected from the file extension.

**Use cases:**

- Process log archives without extraction
- Access files in backup archives
- Read distribution packages
- Analyze compressed TAR files

**Features:**

- Automatic compression detection
- Multiple compression format support
- Fast archive browsing
- No temporary extraction required

**Limitations:**

- **Read-only**: TAR archives cannot be modified
- **No write support**: Cannot create or update TAR files
- Use ZIP backend if write access is needed

**Note:** Built-in to fsspec, no additional dependencies required.
