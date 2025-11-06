Copy Skip Strategies
====================

Advanced copy operations with intelligent skip strategies for efficient file synchronization.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

When copying files, especially in backup or sync scenarios, you often want to skip files that haven't changed. genro-storage provides multiple skip strategies to optimize copy operations.

**Skip Strategies**:

* ``never`` - Always copy (default)
* ``exists`` - Skip if destination exists
* ``size`` - Skip if same size
* ``hash`` - Skip if same content (MD5 comparison)
* ``custom`` - Use custom skip function

Default Behavior (skip='never')
--------------------------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_never_default

By default, files are always copied. Example from `test_copy_skip_strategies.py::test_copy_skip_never_default <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L26-L42>`_:

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([
        {'name': 'src', 'type': 'local', 'path': '/path/to/source'},
        {'name': 'dest', 'type': 'local', 'path': '/path/to/dest'},
    ])

    # Create source file
    src = storage.node('src:file.txt')
    src.write("version 1")

    # First copy
    dest = storage.node('dest:file.txt')
    src.copy_to(dest)
    assert dest.read() == "version 1"

    # Modify source
    src.write("version 2")

    # Copy again (overwrites by default)
    src.copy_to(dest)
    assert dest.read() == "version 2"

Skip If Exists
--------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_exists

Skip copying if destination file already exists. Example from `test_copy_skip_strategies.py::test_copy_skip_exists <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L44-L60>`_:

.. code-block:: python

    # Create source
    src = storage.node('src:file.txt')
    src.write("version 1")

    # First copy
    dest = storage.node('dest:file.txt')
    src.copy_to(dest, skip='exists')
    assert dest.read() == "version 1"

    # Modify source
    src.write("version 2")

    # Copy again with skip='exists' (skips because dest exists)
    src.copy_to(dest, skip='exists')
    assert dest.read() == "version 1"  # Still old version

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_exists_string_and_enum

You can use string or enum for skip strategy. Example from `test_copy_skip_strategies.py::test_copy_skip_exists_string_and_enum <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L62-L77>`_:

.. code-block:: python

    from genro_storage import SkipStrategy

    src = storage.node('src:file.txt')
    src.write("content")
    dest = storage.node('dest:file.txt')

    # With string
    src.copy_to(dest, skip='exists')
    assert dest.exists

    # With enum
    src2 = storage.node('src:file2.txt')
    src2.write("content")
    dest2 = storage.node('dest:file2.txt')
    src2.copy_to(dest2, skip=SkipStrategy.EXISTS)
    assert dest2.exists

**Use case**: Initial upload where you don't want to overwrite existing files.

Skip by Size
------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_size

Skip if files have the same size. Example from `test_copy_skip_strategies.py::test_copy_skip_size <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L79-L102>`_:

.. code-block:: python

    # Create source
    src = storage.node('src:file.txt')
    src.write("12345")  # 5 bytes

    # First copy
    dest = storage.node('dest:file.txt')
    src.copy_to(dest, skip='size')
    assert dest.read() == "12345"

    # Modify source with SAME SIZE
    src.write("abcde")  # Still 5 bytes

    # Copy with skip='size' (skips because same size)
    src.copy_to(dest, skip='size')
    assert dest.read() == "12345"  # Still old content

    # Modify source with DIFFERENT SIZE
    src.write("123456")  # 6 bytes

    # Copy with skip='size' (copies because different size)
    src.copy_to(dest, skip='size')
    assert dest.read() == "123456"  # New content

**Use case**: Fast sync when file size is a good indicator of changes. Faster than hash comparison.

Skip by Hash (Content Comparison)
----------------------------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_hash

Skip if files have the same content (MD5 hash). Example from `test_copy_skip_strategies.py::test_copy_skip_hash <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L104-L127>`_:

.. code-block:: python

    # Create source
    src = storage.node('src:file.txt')
    src.write("content")

    # First copy
    dest = storage.node('dest:file.txt')
    src.copy_to(dest, skip='hash')
    assert dest.read() == "content"

    # Modify source with SAME CONTENT (same MD5)
    src.write("content")

    # Copy with skip='hash' (skips because same hash)
    src.copy_to(dest, skip='hash')
    assert dest.read() == "content"

    # Modify source with DIFFERENT CONTENT
    src.write("new content")

    # Copy with skip='hash' (copies because different hash)
    src.copy_to(dest, skip='hash')
    assert dest.read() == "new content"

**Use case**: Reliable sync where content must be identical. Best for ensuring data integrity.

Custom Skip Function
--------------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_custom

Use custom logic to decide when to skip. Example from `test_copy_skip_strategies.py::test_copy_skip_custom <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L129-L148>`_:

.. code-block:: python

    import time

    # Create files with different mtimes
    src = storage.node('src:file.txt')
    src.write("new")

    dest = storage.node('dest:file.txt')
    dest.write("old")

    # Custom function: skip if dest is newer
    def skip_if_dest_newer(src_node, dest_node):
        return dest_node.exists and dest_node.mtime > src_node.mtime

    # Make dest newer
    time.sleep(0.01)
    dest.write("newer")

    # Skip because dest is newer
    src.copy_to(dest, skip='custom', skip_fn=skip_if_dest_newer)
    assert dest.read() == "newer"  # Not copied

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_custom_requires_function

Custom strategy requires skip_fn parameter. Example from `test_copy_skip_strategies.py::test_copy_skip_custom_requires_function <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L150-L157>`_:

.. code-block:: python

    src = storage.node('src:file.txt')
    src.write("content")
    dest = storage.node('dest:file.txt')

    # Raises ValueError without skip_fn
    with pytest.raises(ValueError, match="skip='custom' requires skip_fn"):
        src.copy_to(dest, skip='custom')

**Use case**: Advanced scenarios like:

- Skip if destination is newer (don't overwrite newer files)
- Skip based on custom metadata
- Skip based on file naming patterns
- Skip based on external database state

Directory Synchronization
--------------------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_directory_skip_exists

Apply skip strategies to directory copies. Example from `test_copy_skip_strategies.py::test_copy_directory_skip_exists <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L159-L183>`_:

.. code-block:: python

    # Create source directory structure
    storage.node('src:dir/file1.txt').write("file1")
    storage.node('src:dir/file2.txt').write("file2")
    storage.node('src:dir/sub/file3.txt').write("file3")

    # First copy
    src_dir = storage.node('src:dir')
    dest_dir = storage.node('dest:dir')
    src_dir.copy_to(dest_dir, skip='exists')

    assert storage.node('dest:dir/file1.txt').read() == "file1"
    assert storage.node('dest:dir/file2.txt').read() == "file2"
    assert storage.node('dest:dir/sub/file3.txt').read() == "file3"

    # Modify sources
    storage.node('src:dir/file1.txt').write("modified1")
    storage.node('src:dir/file2.txt').write("modified2")

    # Copy again with skip='exists' (skips existing files)
    src_dir.copy_to(dest_dir, skip='exists')

    assert storage.node('dest:dir/file1.txt').read() == "file1"  # Old
    assert storage.node('dest:dir/file2.txt').read() == "file2"  # Old

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_directory_skip_hash

Use hash-based sync for incremental backups. Example from `test_copy_skip_strategies.py::test_copy_directory_skip_hash <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L185-L210>`_:

.. code-block:: python

    # Create source structure
    storage.node('src:dir/unchanged.txt').write("same")
    storage.node('src:dir/changed.txt').write("old")

    # First copy
    src_dir = storage.node('src:dir')
    dest_dir = storage.node('dest:dir')
    src_dir.copy_to(dest_dir)

    # Modify only one file
    storage.node('src:dir/changed.txt').write("new")

    # Copy with skip='hash'
    copied = []
    skipped = []

    src_dir.copy_to(dest_dir, skip='hash',
                 on_file=lambda n: copied.append(n.basename),
                 on_skip=lambda n, r: skipped.append(n.basename))

    # Only changed file was copied
    assert 'changed.txt' in copied
    assert 'unchanged.txt' in skipped
    assert storage.node('dest:dir/changed.txt').read() == "new"

Progress and Callbacks
-----------------------

Progress Callback
~~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_with_progress_callback

Track copy progress with callback. Example from `test_copy_skip_strategies.py::test_copy_with_progress_callback <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L212-L230>`_:

.. code-block:: python

    # Create directory with multiple files
    for i in range(5):
        storage.node(f'src:dir/file{i}.txt').write(f"content{i}")

    progress_calls = []

    def progress(current, total):
        progress_calls.append((current, total))

    src_dir = storage.node('src:dir')
    dest_dir = storage.node('dest:dir')
    src_dir.copy_to(dest_dir, progress=progress)

    # Called once per file
    assert len(progress_calls) == 5
    assert progress_calls[0] == (1, 5)
    assert progress_calls[-1] == (5, 5)

**Use case**: Display progress bars in CLI or GUI applications.

on_file Callback
~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_with_on_file_callback

Execute code after each file is copied. Example from `test_copy_skip_strategies.py::test_copy_with_on_file_callback <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L232-L246>`_:

.. code-block:: python

    storage.node('src:dir/file1.txt').write("a")
    storage.node('src:dir/file2.txt').write("b")

    copied_files = []

    def on_file(node):
        copied_files.append(node.basename)

    src_dir = storage.node('src:dir')
    dest_dir = storage.node('dest:dir')
    src_dir.copy_to(dest_dir, on_file=on_file)

    assert set(copied_files) == {'file1.txt', 'file2.txt'}

**Use case**: Logging, database updates, post-processing.

on_skip Callback
~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_with_on_skip_callback

Execute code when files are skipped. Example from `test_copy_skip_strategies.py::test_copy_with_on_skip_callback <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L248-L268>`_:

.. code-block:: python

    # Create and copy
    storage.node('src:file1.txt').write("a")

    src = storage.node('src:file1.txt')
    dest = storage.node('dest:file1.txt')
    src.copy_to(dest)

    # Copy again with skip='exists'
    skipped_files = []

    def on_skip(node, reason):
        skipped_files.append((node.basename, reason))

    src.copy_to(dest, skip='exists', on_skip=on_skip)

    assert len(skipped_files) == 1
    assert skipped_files[0][0] == 'file1.txt'
    assert 'exists' in skipped_files[0][1]

**Use case**: Audit trails, skip statistics, debugging.

Complete Synchronization Example
---------------------------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_skip_hash_with_directory_tracking

Full directory sync with detailed tracking. Example from `test_copy_skip_strategies.py::test_copy_skip_hash_with_directory_tracking <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L270-L308>`_:

.. code-block:: python

    # Create source structure
    storage.node('src:dir/unchanged1.txt').write("same1")
    storage.node('src:dir/unchanged2.txt').write("same2")
    storage.node('src:dir/changed.txt').write("old")
    storage.node('src:dir/new.txt').write("new")

    # First copy (without new.txt)
    src_dir = storage.node('src:dir')
    dest_dir = storage.node('dest:dir')

    for name in ['unchanged1.txt', 'unchanged2.txt', 'changed.txt']:
        src = storage.node(f'src:dir/{name}')
        dst = storage.node(f'dest:dir/{name}')
        src.copy_to(dst)

    # Modify one file
    storage.node('src:dir/changed.txt').write("new content")

    # Track what happens
    copied = []
    skipped = []

    def on_file(node):
        copied.append(node.basename)

    def on_skip(node, reason):
        skipped.append((node.basename, reason))

    # Sync with skip='hash'
    src_dir.copy_to(dest_dir, skip='hash', on_file=on_file, on_skip=on_skip)

    # Verify results
    assert 'changed.txt' in copied  # Modified file copied
    assert 'new.txt' in copied  # New file copied
    assert len(skipped) == 2  # Two unchanged files skipped
    assert any('unchanged1.txt' == s[0] for s in skipped)
    assert any('unchanged2.txt' == s[0] for s in skipped)

Single File with Callbacks
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_copy_single_file_with_callbacks

Callbacks work for single files too. Example from `test_copy_skip_strategies.py::test_copy_single_file_with_callbacks <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L310-L324>`_:

.. code-block:: python

    src = storage.node('src:file.txt')
    src.write("content")
    dest = storage.node('dest:file.txt')

    # First copy
    copied = []
    src.copy_to(dest, on_file=lambda n: copied.append(n.path))
    assert len(copied) == 1

    # Second copy with skip
    skipped = []
    src.copy_to(dest, skip='hash', on_skip=lambda n, r: skipped.append(n.path))
    assert len(skipped) == 1

Edge Cases and Error Handling
------------------------------

Missing Destination
~~~~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_skip_size_handles_missing_dest

Skip strategies handle missing destinations gracefully. Example from `test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_skip_size_handles_missing_dest <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L373-L382>`_:

.. code-block:: python

    src = storage.node('src:file.txt')
    src.write("content")
    dest = storage.node('dest:file.txt')

    # Dest doesn't exist - should copy (not skip)
    src.copy_to(dest, skip='size')
    assert dest.exists
    assert dest.read() == "content"

.. test: test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_skip_hash_handles_missing_dest

Hash strategy also handles missing destination. Example from `test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_skip_hash_handles_missing_dest <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L384-L392>`_:

.. code-block:: python

    src = storage.node('src:file.txt')
    src.write("content")
    dest = storage.node('dest:file.txt')

    # Should copy because dest doesn't exist
    src.copy_to(dest, skip='hash')
    assert dest.exists

Empty Directories
~~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_empty_directory_copy

Empty directories are copied correctly. Example from `test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_empty_directory_copy <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L394-L404>`_:

.. code-block:: python

    src_dir = storage.node('src:empty_dir')
    src_dir.mkdir()

    dest_dir = storage.node('dest:empty_dir')
    src_dir.copy_to(dest_dir)

    assert dest_dir.exists
    assert dest_dir.isdir
    assert len(dest_dir.children()) == 0

Deep Directory Trees
~~~~~~~~~~~~~~~~~~~~

.. test: test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_nested_directory_copy_with_skip

Skip strategies work with deeply nested structures. Example from `test_copy_skip_strategies.py::TestCopySkipEdgeCases::test_nested_directory_copy_with_skip <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L406-L416>`_:

.. code-block:: python

    # Create deep structure
    storage.node('src:a/b/c/d/file.txt').write("deep")

    src = storage.node('src:a')
    dest = storage.node('dest:a')

    src.copy_to(dest, skip='hash')

    assert storage.node('dest:a/b/c/d/file.txt').read() == "deep"

SkipStrategy Enum
-----------------

.. test: test_copy_skip_strategies.py::TestCopySkipStrategies::test_skip_strategy_enum_values

The SkipStrategy enum provides type-safe constants. Example from `test_copy_skip_strategies.py::test_skip_strategy_enum_values <https://github.com/genropy/genro-storage/blob/main/tests/test_copy_skip_strategies.py#L346-L352>`_:

.. code-block:: python

    from genro_storage import SkipStrategy

    assert SkipStrategy.NEVER == 'never'
    assert SkipStrategy.EXISTS == 'exists'
    assert SkipStrategy.SIZE == 'size'
    assert SkipStrategy.HASH == 'hash'
    assert SkipStrategy.CUSTOM == 'custom'

**Usage**:

.. code-block:: python

    # Using enum (type-safe, IDE autocomplete)
    src.copy_to(dest, skip=SkipStrategy.HASH)

    # Using string (shorter)
    src.copy_to(dest, skip='hash')

Best Practices
--------------

Choosing the Right Strategy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **skip='never'** (default)
   - First-time backup
   - Force overwrite
   - Small file counts

2. **skip='exists'**
   - Initial upload (don't overwrite)
   - Resume interrupted transfers
   - Fast, no I/O needed

3. **skip='size'**
   - Quick sync when size indicates changes
   - Large file counts
   - Balanced speed/accuracy

4. **skip='hash'**
   - Critical data (ensure integrity)
   - Detect content changes regardless of size
   - Most reliable, slower

5. **skip='custom'**
   - Complex business logic
   - Time-based sync (mtime comparison)
   - Metadata-based decisions

Performance Considerations
~~~~~~~~~~~~~~~~~~~~~~~~~~

**From fastest to slowest**:

1. ``skip='exists'`` - Only checks file existence
2. ``skip='size'`` - Reads file metadata
3. ``skip='hash'`` - Computes MD5 hashes (reads full file)
4. ``skip='custom'`` - Depends on your function

**For S3/Cloud Storage**:

- Use ``skip='hash'`` with ETag (efficient, no download)
- Metadata reads are fast (no data transfer)
- See :doc:`/backends` for backend-specific optimizations

Monitoring and Logging
~~~~~~~~~~~~~~~~~~~~~~

Always use callbacks for production sync:

.. code-block:: python

    def sync_directory(src_path, dest_path):
        src = storage.node(src_path)
        dest = storage.node(dest_path)

        stats = {'copied': 0, 'skipped': 0, 'errors': 0}

        def on_file(node):
            stats['copied'] += 1
            logger.info(f"Copied: {node.fullpath}")

        def on_skip(node, reason):
            stats['skipped'] += 1
            logger.debug(f"Skipped: {node.fullpath} ({reason})")

        try:
            src.copy_to(dest, skip='hash', on_file=on_file, on_skip=on_skip)
        except Exception as e:
            stats['errors'] += 1
            logger.error(f"Sync failed: {e}")

        return stats

Next Steps
----------

* Learn about :doc:`virtual-nodes` for advanced file operations
* See :doc:`/versioning` for S3 version control
* Check :doc:`/backends` for backend-specific features
* Explore :doc:`/examples` for complete use cases
