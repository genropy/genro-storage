Backend Capabilities
====================

Capabilities describe **what a backend can do**. Instead of trying an operation and hoping it works,
you can ask the backend first if it supports it.

Why They Matter
---------------

Different storage types have different capabilities:

- **S3** supports versioning, metadata, temporary URLs
- **Local filesystem** supports symbolic links (Unix/Linux) but not versioning
- **HTTP** is read-only, no writes
- **Memory** supports everything but data is temporary

Capabilities let you:

1. **Write adaptive code** that works with different storage types
2. **Avoid errors** by checking before attempting an operation
3. **Give clear messages** to users about what they can/cannot do
4. **Enable conditional features** in your UI

How They Work
-------------

Each backend declares its capabilities. You check them before using a feature:

.. code-block:: python

    node = storage.node('s3:documents/file.pdf')

    # Check a capability
    if node.capabilities.versioning:
        print("I can access previous versions")
        versions = node.versions
    else:
        print("Versioning not available")

    # Check before generating URLs
    if node.capabilities.presigned_urls:
        url = node.get_presigned_url(expires_in=3600)
        print(f"Temporary link: {url}")
    else:
        print("Cannot generate URLs for this storage")

Available Capabilities
----------------------

Basic Operations
~~~~~~~~~~~~~~~~

``read`` : bool
    Can read files

``write`` : bool
    Can write files

``delete`` : bool
    Can delete files

``mkdir`` : bool
    Can create directories

``list_dir`` : bool
    Can list directory contents

Versioning
~~~~~~~~~~

``versioning`` : bool
    Supports file versioning (maintains history of changes)

``version_listing`` : bool
    Can list all available versions

``version_access`` : bool
    Can access specific versions

Metadata and URLs
~~~~~~~~~~~~~~~~~

``metadata`` : bool
    Supports custom metadata (key-value) on files

``presigned_urls`` : bool
    Can generate temporary signed URLs for direct access

``public_urls`` : bool
    Has public URLs accessible via HTTP

Advanced Features
~~~~~~~~~~~~~~~~~

``atomic_operations`` : bool
    Guarantees atomic operations (all or nothing)

``symbolic_links`` : bool
    Supports symbolic links (Unix/Linux filesystems)

``copy_optimization`` : bool
    Has server-side optimized copy (without download/upload)

``hash_on_metadata`` : bool
    MD5/ETag available in metadata without reading the file

Performance
~~~~~~~~~~~

``append_mode`` : bool
    Supports append mode to add content

``seek_support`` : bool
    Supports seek operations in file handles

Characteristics
~~~~~~~~~~~~~~~

``readonly`` : bool
    Backend is read-only (HTTP, read-only mounts)

``temporary`` : bool
    Temporary/ephemeral storage (memory backend)

Capabilities by Backend
-----------------------

S3
~~

.. code-block:: python

    # S3 with versioning enabled
    {
        'read': True,
        'write': True,
        'delete': True,
        'versioning': True,        # ✓ If enabled on bucket
        'metadata': True,          # ✓ Custom metadata
        'presigned_urls': True,    # ✓ Temporary URLs
        'hash_on_metadata': True,  # ✓ ETag = MD5
        'append_mode': False,      # ✗ S3 doesn't support append
    }

Local (Filesystem)
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    # Local filesystem
    {
        'read': True,
        'write': True,
        'delete': True,
        'symbolic_links': True,    # ✓ On Unix/Linux
        'versioning': False,       # ✗ No versioning
        'presigned_urls': False,   # ✗ No URLs
        'metadata': False,         # ✗ No custom metadata
    }

HTTP/HTTPS
~~~~~~~~~~

.. code-block:: python

    # HTTP storage (read-only)
    {
        'read': True,
        'write': False,            # ✗ Read-only
        'delete': False,           # ✗ Read-only
        'readonly': True,          # ✓ Explicitly read-only
        'public_urls': True,       # ✓ Public URLs
        'versioning': False,       # ✗ No versioning
    }

Memory
~~~~~~

.. code-block:: python

    # In-memory storage (testing)
    {
        'read': True,
        'write': True,
        'delete': True,
        'temporary': True,         # ✓ Data lost at end of process
        'versioning': False,       # ✗ No versioning
    }

Practical Use
-------------

Adaptive Code
~~~~~~~~~~~~~

Write code that adapts to the available backend:

.. code-block:: python

    def save_with_metadata(node, data, author, tags):
        """Save file with metadata if supported"""
        node.write_bytes(data)

        # Add metadata only if supported
        if node.capabilities.metadata:
            node.set_metadata({
                'author': author,
                'tags': ','.join(tags)
            })
            print("Metadata saved")
        else:
            print("Metadata not supported, only file saved")

Conditional Features in UI
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Show options only if available:

.. code-block:: python

    def get_file_actions(node):
        """Return available actions for a file"""
        actions = ['download']  # Always available

        if not node.capabilities.readonly:
            actions.append('edit')
            actions.append('delete')

        if node.capabilities.versioning:
            actions.append('view_history')
            actions.append('rollback')

        if node.capabilities.presigned_urls:
            actions.append('share_link')

        return actions

Preventive Validation
~~~~~~~~~~~~~~~~~~~~~~

Check before attempting operations:

.. code-block:: python

    def backup_with_versioning(source, destination):
        """Backup with versioning if available"""

        if not destination.capabilities.write:
            raise ValueError(f"{destination.fullpath} is read-only!")

        # Copy the file
        source.copy(destination)

        # Check if versioning is active
        if destination.capabilities.versioning:
            print(f"Backup saved, versions available: {destination.version_count}")
        else:
            print("Backup saved (versioning not available)")

Clear User Messages
~~~~~~~~~~~~~~~~~~~

Explain what's possible and what's not:

.. code-block:: python

    def explain_limitations(node):
        """Explain what you can do with this storage"""
        caps = node.capabilities

        print(f"Storage: {node._mount_name}")

        if caps.readonly:
            print("⚠️  Read-only - you cannot modify files")

        if caps.temporary:
            print("⚠️  Temporary storage - data will be lost")

        features = []
        if caps.versioning:
            features.append("versioning")
        if caps.metadata:
            features.append("metadata")
        if caps.presigned_urls:
            features.append("temporary URLs")

        if features:
            print(f"✓ Supports: {', '.join(features)}")
        else:
            print("• Basic file operations (read/write)")

Capability String
~~~~~~~~~~~~~~~~~

Each backend has a ``__str__()`` method that lists features:

.. code-block:: python

    print(node.capabilities)
    # Output: "versioning, metadata, presigned URLs, fast hashing"

    # Use in error messages
    try:
        versions = node.versions
    except PermissionError as e:
        print(e)
        # "s3 backend does not support versioning.
        #  Supported features: basic file operations"

When to Use Capabilities
-------------------------

✅ **Use capabilities when:**

- You write libraries/tools that work with different storage types
- You build UI where some features might not be available
- You want to give clear and useful error messages
- You do operations that not all backends support

❌ **No need to check them if:**

- You always use the same storage type
- You only do basic operations (read/write) supported everywhere
- Your code is specific to one backend

Complete Example
----------------

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([
        {'name': 's3', 'type': 's3', 'bucket': 'my-bucket'},
        {'name': 'local', 'type': 'local', 'path': '/data'},
        {'name': 'web', 'type': 'http', 'base_url': 'https://example.com'}
    ])

    def analyze_storage(mount_name):
        """Analyze capabilities of a storage"""
        node = storage.node(f'{mount_name}:test.txt')
        caps = node.capabilities

        print(f"\n=== Storage: {mount_name} ===")
        print(f"Type: {node._backend.__class__.__name__}")
        print(f"Available features: {caps}")

        # Check basic operations
        can_write = caps.write and not caps.readonly
        print(f"Can write: {'✓' if can_write else '✗'}")

        # Advanced features
        if caps.versioning:
            print("✓ Versioning available")

        if caps.metadata:
            print("✓ Custom metadata")

        if caps.presigned_urls:
            print("✓ Can generate temporary URLs")

        # Limitations
        if caps.readonly:
            print("⚠️  Read-only")

        if caps.temporary:
            print("⚠️  Temporary storage")

    # Analyze all storages
    analyze_storage('s3')
    analyze_storage('local')
    analyze_storage('web')

Adding New Capabilities
-----------------------

If you extend genro-storage with a new backend, declare its capabilities:

.. code-block:: python

    from genro_storage.backends.base import StorageBackend
    from genro_storage.capabilities import BackendCapabilities

    class MyCustomBackend(StorageBackend):
        @property
        def capabilities(self) -> BackendCapabilities:
            return BackendCapabilities(
                read=True,
                write=True,
                versioning=False,  # My backend doesn't have versioning
                metadata=True,     # But supports metadata
                # ... other capabilities
            )

Capabilities are **explicit and verifiable**. No surprises!
