File Versioning
===============

Versioning automatically preserves all versions of a file every time you modify it.
genro-storage **makes it easier to access these versions** that backends (like S3) already maintain.

Availability
------------

Versioning only works **with backends that expose this capability natively**.

You can check if your storage supports versioning by checking capabilities:

.. code-block:: python

    node = storage.node('s3:documents/contract.pdf')

    if node.capabilities.versioning:
        print("This storage supports versioning!")
        versions = node.versions
    else:
        print("Versioning not available on this backend")

**Supported backends:**

- **S3**: Fully supported (requires versioning enabled on bucket)
- **Local/Memory/HTTP/FTP**: Not supported
- **GCS/Azure**: Have native versioning but not yet implemented

What You Can Do
---------------

Access Previous Versions
~~~~~~~~~~~~~~~~~~~~~~~~

You can read any past version of a file in three ways:

**By relative position** - Python-style negative indexing:

.. code-block:: python

    # Current version (default)
    with node.open() as f:
        current = f.read()

    # Previous version
    with node.open(version=-2) as f:
        previous = f.read()

    # Two versions ago
    with node.open(version=-3) as f:
        older = f.read()

    # First version ever created
    with node.open(version=0) as f:
        original = f.read()

**By date** - Time travel:

.. code-block:: python

    from datetime import datetime, timedelta

    # How was this file yesterday?
    yesterday = datetime.now() - timedelta(days=1)
    with node.open(as_of=yesterday) as f:
        data = f.read()

    # Version from January 15, 2024
    with node.open(as_of=datetime(2024, 1, 15)) as f:
        data = f.read()

**By specific ID** - If you know the version identifier:

.. code-block:: python

    with node.open(version='abc123xyz...') as f:
        data = f.read()

Explore History
~~~~~~~~~~~~~~~

You can see the list of all available versions:

.. code-block:: python

    # How many versions exist?
    print(f"Total versions: {node.version_count}")

    # Complete list
    for v in node.versions:
        print(f"Created: {v['last_modified']}")
        print(f"Size: {v['size']} bytes")
        print(f"MD5: {v['etag']}")
        print(f"Current: {v['is_latest']}")

Restore a Version
~~~~~~~~~~~~~~~~~

You can rollback by creating a new version with the content of a previous one:

.. code-block:: python

    # Restore previous version
    node.rollback()

    # Or restore a specific version
    node.rollback(-4)  # Four versions ago

.. note::
   Rollback **creates a new version**, it doesn't delete anything.
   You can always go back further.

Avoid Duplicate Versions
~~~~~~~~~~~~~~~~~~~~~~~~~

The system can automatically check if the content is identical to the current version
and skip writing:

.. code-block:: python

    # Writes only if content is different
    if node.write_bytes_if_changed(new_data):
        print("File updated - new version created")
    else:
        print("Content identical - no new version")

This is useful for:

- Saving S3 space
- Reducing storage costs
- Avoiding useless versions in frequent backup/sync

Compact Version History
~~~~~~~~~~~~~~~~~~~~~~~

If you already have redundant versions in your history, you can clean them up
by compacting the version history. This removes consecutive duplicate versions
while preserving meaningful changes:

.. code-block:: python

    # Check how many redundant versions exist
    count = node.compact_versions(dry_run=True)
    print(f"Found {count} redundant versions")

    # Remove consecutive duplicates
    removed = node.compact_versions()
    print(f"Removed {removed} versions, saved storage space!")

**How it works:**

The compaction process examines the version history and removes versions that
have identical content (same ETag/MD5) to the immediately preceding version.

**Important:** Non-consecutive duplicates are **preserved** to maintain history.
For example, if you modify a file, then revert to the original, both states
are kept to show the change history.

Example scenario:

.. code-block:: text

    v1: content A (etag: xxx)  ← KEPT
    v2: content A (etag: xxx)  ← REMOVED (duplicate of v1)
    v3: content B (etag: yyy)  ← KEPT (change from A to B)
    v4: content B (etag: yyy)  ← REMOVED (duplicate of v3)
    v5: content A (etag: xxx)  ← KEPT (revert from B back to A)

This is useful when:

- You have automated processes that write files frequently
- Content doesn't change on every write
- You want to reduce S3 storage costs
- You need to clean up after bulk operations

.. note::
   Compaction is **irreversible**. Use ``dry_run=True`` first to preview
   what will be removed. The operation requires S3 versioning to be enabled
   and appropriate permissions to delete versions.

Compare Versions
~~~~~~~~~~~~~~~~

You can read two versions and compare them:

.. code-block:: python

    # Compare current version with previous
    current, previous = node.diff_versions()

    if current == previous:
        print("No changes")
    else:
        print("File was modified")

    # Compare with older versions
    current, old = node.diff_versions(-1, -5)

.. note::
   ``diff_versions()`` returns raw contents (bytes).
   It's up to you to decide how to compare or analyze them in your code.

When to Use Versioning
-----------------------

✅ **Use versioning if:**

- You need to recover from errors (file overwritten by mistake)
- You want to track file history
- You work with critical data (configs, contracts, financial data)
- You do frequent backup/sync but content rarely changes

❌ **Don't need it if:**

- You use local storage (not supported)
- Files are temporary or cache
- You don't care about file history
- Files are very large and change completely each time

Limitations
-----------

Backend Specific
~~~~~~~~~~~~~~~~

Versioning only works with backends that:

- Expose the capability ``versioning=True``
- Implement ``get_versions()`` and ``open_version()`` methods

Currently only S3 is fully supported.

Read-Only on Historical Versions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You cannot modify a historical version directly:

.. code-block:: python

    # This raises ValueError
    with node.open(version=-2, mode='wb') as f:
        f.write(b'data')  # ❌ Error!

If you want to "modify" an old version, you must read it and write it as a new version,
or use ``rollback()``.

Storage Costs
~~~~~~~~~~~~~

Each version takes up space on the backend. For S3:

- Each version is billed separately
- Use lifecycle policies to automatically delete old versions
- Use ``write_bytes_if_changed()`` to avoid creating duplicate versions
- Use ``compact_versions()`` to clean up existing redundant versions

Complete Example
----------------

.. code-block:: python

    from genro_storage import StorageManager
    from datetime import datetime, timedelta

    storage = StorageManager()
    storage.configure([{
        'name': 's3',
        'type': 's3',
        'bucket': 'my-bucket'
    }])

    node = storage.node('s3:config/app-settings.json')

    # Check if versioning is available
    if not node.capabilities.versioning:
        print("Versioning not supported")
        exit()

    # Show history
    print(f"Available versions: {node.version_count}")
    for i, v in enumerate(node.versions):
        index = -i - 1
        marker = "⭐" if v['is_latest'] else "  "
        print(f"{marker} Version {index}: {v['last_modified']}")

    # Read yesterday's version
    yesterday = datetime.now() - timedelta(days=1)
    with node.open(as_of=yesterday) as f:
        old_config = f.read()

    # Compare with current version
    current, previous = node.diff_versions()
    if current != previous:
        print("Configuration has changed!")

    # Rollback if needed
    # node.rollback()  # Restore previous version

    # Write new version only if different
    new_config = b'{"setting": "new_value"}'
    if node.write_bytes_if_changed(new_config):
        print("Configuration updated")
