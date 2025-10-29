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

Git Repositories
----------------

Read files from local Git repositories at specific commits, branches, or tags.

**Installation:**

.. code-block:: bash

    pip install pygit2

**Configuration:**

.. code-block:: python

    # Access repository at HEAD
    {
        'name': 'myrepo',
        'type': 'git',
        'path': '/path/to/repo.git'   # required: path to Git repository
    }

    # Access specific branch/tag/commit
    {
        'name': 'production',
        'type': 'git',
        'path': '/path/to/repo.git',
        'ref': 'v1.0.0'               # optional: branch, tag, or commit SHA
    }

**Usage:**

.. code-block:: python

    # Read file from repository
    node = storage.node('myrepo:src/main.py')
    content = node.read()

    # List repository files
    for item in storage.node('myrepo:src').list():
        print(item)

    # Compare different versions
    current = storage.node('production:config.yaml')
    staging = storage.node('staging:config.yaml')
    if current.md5 != staging.md5:
        print("Configuration differs between production and staging")

**Use cases:**

- Read configuration from specific Git commits
- Access historical versions of files
- Compare files across branches
- Browse repository contents without checkout
- Build tools that need version-specific access

**Features:**

- Access any commit, branch, or tag
- Read files without full checkout
- Version history access
- Fast repository browsing
- No working directory required

**Limitations:**

- **Read-only**: Cannot commit or modify repository
- **No write support**: Git repositories are read-only via fsspec
- Requires pygit2 library
- Only works with local repositories (use GitHub backend for remote)

**Note:** Requires ``pygit2`` package for Git access.

GitHub Repositories
-------------------

Read files from GitHub repositories via API, with support for branches, tags, and commits.

**Configuration:**

.. code-block:: python

    # Public repository (no authentication)
    {
        'name': 'opensource',
        'type': 'github',
        'org': 'genropy',              # required: GitHub organization/user
        'repo': 'genro-storage'        # required: repository name
    }

    # Specific branch/tag/commit
    {
        'name': 'release',
        'type': 'github',
        'org': 'genropy',
        'repo': 'genro-storage',
        'sha': 'v1.0.0'                # optional: branch, tag, or commit SHA
    }

    # Private repository (with authentication)
    {
        'name': 'private',
        'type': 'github',
        'org': 'mycompany',
        'repo': 'secret-project',
        'username': 'myusername',      # required for private repos
        'token': 'ghp_xxxxxxxxxxxxx'   # required for private repos
    }

**Usage:**

.. code-block:: python

    # Read file from GitHub
    node = storage.node('opensource:README.md')
    content = node.read()

    # Download configuration from release tag
    config_node = storage.node('release:config/production.yaml')
    config_node.copy_to(storage.node('local:config.yaml'))

    # List repository contents
    for item in storage.node('opensource:src').list():
        print(f"File: {item.name}, Size: {item.size}")

**Authentication:**

For private repositories or to increase API rate limits:

1. Create a Personal Access Token at https://github.com/settings/tokens
2. Include both ``username`` and ``token`` in configuration
3. Token needs ``repo`` scope for private repository access

**Use cases:**

- Download configuration from GitHub releases
- Access documentation files
- Fetch schemas or templates from repositories
- CI/CD pipelines reading from GitHub
- Tools that process files from multiple GitHub repos

**Features:**

- Access public and private repositories
- Read any commit, branch, or tag
- No local clone required
- Works over HTTPS
- Efficient API-based access

**Limitations:**

- **Read-only**: Cannot push commits
- **API rate limits**: 60 req/hour (unauthenticated), 5000 req/hour (authenticated)
- Requires internet connection
- Not suitable for large binary files (use Git clone for that)

**Note:** Built-in to fsspec, no additional dependencies required. Authentication requires GitHub Personal Access Token.

WebDAV Storage
--------------

Access remote files via WebDAV protocol (Nextcloud, ownCloud, SharePoint, etc.).

**Installation:**

.. code-block:: bash

    pip install genro-storage[webdav]
    # or
    pip install webdav4

**Configuration:**

.. code-block:: python

    # Basic configuration
    {
        'name': 'nextcloud',
        'type': 'webdav',
        'url': 'https://cloud.example.com/remote.php/dav/files/username'
    }

    # With username/password authentication
    {
        'name': 'sharepoint',
        'type': 'webdav',
        'url': 'https://sharepoint.company.com/documents',
        'username': 'user@company.com',
        'password': 'secret'
    }

    # With bearer token authentication
    {
        'name': 'owncloud',
        'type': 'webdav',
        'url': 'https://owncloud.example.com/remote.php/webdav',
        'token': 'bearer_token_here'
    }

**Usage:**

.. code-block:: python

    # Read file from WebDAV
    node = storage.node('nextcloud:Documents/report.pdf')
    data = node.read_bytes()

    # Upload file to WebDAV
    local = storage.node('home:photo.jpg')
    local.copy_to(storage.node('nextcloud:Photos/vacation.jpg'))

    # Create directory
    storage.node('sharepoint:Projects/NewProject').mkdir()

    # List remote files
    for item in storage.node('owncloud:Documents').list():
        print(f"{item.name}: {item.size} bytes")

    # Delete remote file
    storage.node('nextcloud:temp/old_file.txt').delete()

**Supported services:**

- **Nextcloud** - Open-source file sync and share
- **ownCloud** - Enterprise file sync and share
- **SharePoint** - Microsoft collaboration platform
- **Box** - Cloud content management
- **Any WebDAV server** - Standard protocol support

**Use cases:**

- Sync files with Nextcloud/ownCloud
- Access corporate SharePoint documents
- Remote file backup and restore
- Collaborative document management
- Cross-platform file sharing

**Features:**

- Full read/write support
- Create and delete files
- Directory operations
- Works with any WebDAV-compliant server
- Standard HTTP/HTTPS protocol

**Limitations:**

- Requires network connection
- Performance depends on network speed
- Authentication required for most servers
- Some servers may have file size limits

**Note:** Requires ``webdav4`` package. Ensure your WebDAV server URL is correct (often includes ``/remote.php/dav/`` for Nextcloud/ownCloud).

LibArchive Storage
------------------

Read files from various archive formats using libarchive (ZIP, TAR, RAR, 7z, ISO, and more).

**Installation:**

.. code-block:: bash

    pip install genro-storage[libarchive]
    # or
    pip install libarchive-c

Note: Also requires system libarchive library:

- **macOS**: ``brew install libarchive``
- **Ubuntu/Debian**: ``apt-get install libarchive-dev``
- **CentOS/RHEL**: ``yum install libarchive-devel``
- **Windows**: Pre-built binaries available

**Configuration:**

.. code-block:: python

    # Read any archive format
    {
        'name': 'backup',
        'type': 'libarchive',
        'file': '/backups/data.tar.gz'
    }

    {
        'name': 'install',
        'type': 'libarchive',
        'file': '/downloads/software.zip'
    }

    {
        'name': 'iso',
        'type': 'libarchive',
        'file': '/images/linux.iso'
    }

**Usage:**

.. code-block:: python

    # Read from archive
    node = storage.node('backup:important.txt')
    content = node.read()

    # List archive contents
    for item in storage.node('install:').list():
        print(f"{item.name}: {item.size} bytes")

    # Extract specific files
    archived = storage.node('backup:database/config.json')
    archived.copy_to(storage.node('local:restored_config.json'))

    # Browse ISO image contents
    for file in storage.node('iso:boot').list():
        print(file.name)

**Supported formats:**

- **ZIP** - ZIP archives
- **TAR** - TAR archives (with gzip, bzip2, xz, lzma compression)
- **RAR** - RAR archives
- **7z** - 7-Zip archives
- **ISO** - ISO disk images
- **ARJ** - ARJ archives
- **CAB** - Microsoft Cabinet files
- **LHA/LZH** - LHA/LZH archives
- **And many more** - See libarchive documentation

**Use cases:**

- Read files from RAR archives (unlike ZIP backend)
- Browse ISO disk images
- Access files in 7z archives
- Extract from various legacy archive formats
- Unified interface for all archive types

**Features:**

- Supports 20+ archive formats
- Automatic format detection
- Compression support for most formats
- Fast archive browsing
- No temporary extraction required

**Limitations:**

- **Read-only**: Cannot create or modify archives
- **System dependency**: Requires libarchive library installed
- **Performance**: May be slower than format-specific backends
- Not all archive formats support random access

**Note:** Requires both ``libarchive-c`` Python package and system ``libarchive`` library. For write access to ZIP/TAR, use the dedicated ZIP or TAR backends instead.
