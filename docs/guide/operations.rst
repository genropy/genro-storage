File Operations Guide
=====================

This guide covers basic file and directory operations in genro-storage.

.. contents:: Table of Contents
   :local:
   :depth: 2

Basic File Operations
---------------------

Reading and Writing Files
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestFileOperations::test_write_and_read_text

Write and read text files. Example from `test_local_storage.py::test_write_and_read_text <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L93-L102>`_:

.. code-block:: python

    from genro_storage import StorageManager

    # Configure storage
    storage = StorageManager()
    storage.configure([
        {'name': 'test', 'type': 'local', 'path': '/path/to/storage'}
    ])

    # Get a node reference
    node = storage.node('test:file.txt')

    # Write text content
    node.write("Hello World")

    # Read it back
    content = node.read()
    assert content == "Hello World"

.. test: test_local_storage.py::TestFileOperations::test_write_and_read_bytes

For binary files, use mode='rb'/'wb'. Example from `test_local_storage.py::test_write_and_read_bytes <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L104-L114>`_:

.. code-block:: python

    node = storage.node('test:file.bin')
    data = b'\\x00\\x01\\x02\\x03\\x04'

    # Write binary
    node.write(data, mode='wb')

    # Read binary
    read_data = node.read(mode='rb')
    assert read_data == data

File Existence and Properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestFileOperations::test_file_exists

Check if a file exists. Example from `test_local_storage.py::test_file_exists <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L116-L125>`_:

.. code-block:: python

    node = storage.node('test:file.txt')

    # Initially doesn't exist
    assert not node.exists

    # After writing, exists
    node.write("content")
    assert node.exists

.. test: test_local_storage.py::TestFileOperations::test_is_file_is_dir

Check file type with ``isfile`` and ``isdir``. Example from `test_local_storage.py::test_is_file_is_dir <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L127-L140>`_:

.. code-block:: python

    file_node = storage.node('test:file.txt')
    dir_node = storage.node('test:directory')

    # Create file
    file_node.write("content")
    assert file_node.isfile
    assert not file_node.isdir

    # Create directory
    dir_node.mkdir()
    assert dir_node.isdir
    assert not dir_node.isfile

.. test: test_local_storage.py::TestFileOperations::test_file_size

Get file size in bytes. Example from `test_local_storage.py::test_file_size <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L142-L149>`_:

.. code-block:: python

    node = storage.node('test:file.txt')
    content = "Hello World"

    node.write(content)

    assert node.size == len(content.encode('utf-8'))

.. test: test_local_storage.py::TestFileOperations::test_file_mtime

Get file modification time. Example from `test_local_storage.py::test_file_mtime <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L151-L160>`_:

.. code-block:: python

    from datetime import datetime

    node = storage.node('test:file.txt')

    before = datetime.now().timestamp()
    node.write("content")

    mtime = node.mtime
    # mtime is close to current time
    assert abs(mtime - before) < 2  # Within 2 seconds

Using Context Managers
~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestFileOperations::test_file_open_context_manager

Use ``open()`` with context managers for streaming I/O. Example from `test_local_storage.py::test_file_open_context_manager <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L171-L184>`_:

.. code-block:: python

    node = storage.node('test:file.txt')

    # Write using context manager
    with node.open('w') as f:
        f.write("Line 1\\n")
        f.write("Line 2\\n")

    # Read using context manager
    with node.open('r') as f:
        content = f.read()

    assert content == "Line 1\\nLine 2\\n"

This is useful for:

- Large files that don't fit in memory
- Streaming data
- Line-by-line processing

Deleting Files
~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestFileOperations::test_file_delete

Delete files with ``delete()``. Example from `test_local_storage.py::test_file_delete <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L186-L199>`_:

.. code-block:: python

    node = storage.node('test:file.txt')

    # Create file
    node.write("content")
    assert node.exists

    # Delete
    node.delete()
    assert not node.exists

    # Delete again (idempotent - doesn't raise error)
    node.delete()

Directory Operations
--------------------

Creating Directories
~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestDirectoryOperations::test_mkdir

Create directories with ``mkdir()``. Example from `test_local_storage.py::test_mkdir <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L205-L214>`_:

.. code-block:: python

    node = storage.node('test:mydir')

    assert not node.exists

    node.mkdir()

    assert node.exists
    assert node.isdir

.. test: test_local_storage.py::TestDirectoryOperations::test_mkdir_parents

Create nested directories with ``parents=True``. Example from `test_local_storage.py::test_mkdir_parents <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L216-L223>`_:

.. code-block:: python

    node = storage.node('test:a/b/c/d')

    node.mkdir(parents=True)

    assert node.exists
    assert node.isdir

.. test: test_local_storage.py::TestDirectoryOperations::test_mkdir_exist_ok

Handle existing directories with ``exist_ok``. Example from `test_local_storage.py::test_mkdir_exist_ok <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L225-L236>`_:

.. code-block:: python

    node = storage.node('test:mydir')

    node.mkdir()

    # Should raise error without exist_ok
    with pytest.raises(FileExistsError):
        node.mkdir(exist_ok=False)

    # Should not raise with exist_ok
    node.mkdir(exist_ok=True)

Listing Directory Contents
~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestDirectoryOperations::test_list_directory

List directory contents with ``children()``. Example from `test_local_storage.py::test_list_directory <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L238-L256>`_:

.. code-block:: python

    # Create directory with files
    dir_node = storage.node('test:mydir')
    dir_node.mkdir()

    # Create some files
    dir_node.child('file1.txt').write("content1")
    dir_node.child('file2.txt').write("content2")
    dir_node.child('subdir').mkdir()

    # List children
    children = dir_node.children()
    names = [c.basename for c in children]

    assert len(children) == 3
    assert 'file1.txt' in names
    assert 'file2.txt' in names
    assert 'subdir' in names

Navigating the Directory Tree
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestDirectoryOperations::test_child_method

Use ``child()`` to navigate to child nodes. Example from `test_local_storage.py::test_child_method <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L258-L276>`_:

.. code-block:: python

    parent = storage.node('test:documents')
    parent.mkdir()

    # Single component
    child = parent.child('report.pdf')
    child.write("content")

    assert child.fullpath == 'test:documents/report.pdf'
    assert child.exists

    # Single path with slashes
    child2 = parent.child('2024/reports/q4.pdf')
    assert child2.fullpath == 'test:documents/2024/reports/q4.pdf'

    # Varargs (multiple components)
    child3 = parent.child('2024', 'reports', 'q4.pdf')
    assert child3.fullpath == 'test:documents/2024/reports/q4.pdf'

.. test: test_local_storage.py::TestDirectoryOperations::test_parent_property

Use ``parent`` to navigate up. Example from `test_local_storage.py::test_parent_property <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L278-L286>`_:

.. code-block:: python

    node = storage.node('test:documents/reports/file.pdf')

    parent = node.parent
    assert parent.fullpath == 'test:documents/reports'

    grandparent = parent.parent
    assert grandparent.fullpath == 'test:documents'

Deleting Directories
~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestDirectoryOperations::test_delete_directory

Delete directories recursively. Example from `test_local_storage.py::test_delete_directory <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L385-L398>`_:

.. code-block:: python

    dir_node = storage.node('test:mydir')
    dir_node.mkdir()

    # Create files inside
    dir_node.child('file1.txt').write("content")
    dir_node.child('subdir').mkdir()
    dir_node.child('subdir', 'file2.txt').write("content")

    # Delete recursively (directory and all contents)
    dir_node.delete()

    assert not dir_node.exists

Copy and Move Operations
-------------------------

Copying Files
~~~~~~~~~~~~~

.. test: test_local_storage.py::TestCopyMove::test_copy_file

Copy files with ``copy_to()``. Example from `test_local_storage.py::test_copy_file <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L404-L420>`_:

.. code-block:: python

    src = storage.node('test:source.txt')
    src.write("Hello World")

    dest = storage.node('test:destination.txt')

    # Copy
    result = src.copy_to(dest)

    # Both should exist
    assert src.exists
    assert dest.exists
    assert result.fullpath == dest.fullpath

    # Content should be the same
    assert dest.read() == "Hello World"

.. test: test_local_storage.py::TestCopyMove::test_copy_with_string_dest

You can pass strings as destinations. Example from `test_local_storage.py::test_copy_with_string_dest <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L422-L431>`_:

.. code-block:: python

    src = storage.node('test:source.txt')
    src.write("content")

    # Copy using string path
    dest = src.copy_to('test:destination.txt')

    assert dest.exists
    assert dest.fullpath == 'test:destination.txt'

Moving Files
~~~~~~~~~~~~

.. test: test_local_storage.py::TestCopyMove::test_move_file

Move files with ``move_to()``. Example from `test_local_storage.py::test_move_file <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L433-L449>`_:

.. code-block:: python

    src = storage.node('test:source.txt')
    src.write("Hello World")

    dest = storage.node('test:destination.txt')

    # Move
    result = src.move_to(dest)

    # Source should not exist, dest should
    assert not storage.node('test:source.txt').exists
    assert dest.exists
    assert result.fullpath == dest.fullpath

    # Content preserved
    assert dest.read() == "Hello World"

.. test: test_local_storage.py::TestCopyMove::test_move_updates_self

The original node is updated after move. Example from `test_local_storage.py::test_move_updates_self <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L451-L464>`_:

.. code-block:: python

    node = storage.node('test:old.txt')
    node.write("content")

    original_id = id(node)

    # Move
    node.move_to('test:new.txt')

    # Same object, updated path
    assert id(node) == original_id
    assert node.fullpath == 'test:new.txt'
    assert node.exists

Copying Directories
~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestCopyMove::test_copy_directory

Copy entire directories recursively. Example from `test_local_storage.py::test_copy_directory <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L466-L487>`_:

.. code-block:: python

    # Create source directory with contents
    src = storage.node('test:src_dir')
    src.mkdir()
    src.child('file1.txt').write("content1")
    src.child('subdir').mkdir()
    src.child('subdir', 'file2.txt').write("content2")

    # Copy
    dest = storage.node('test:dest_dir')
    src.copy_to(dest)

    # Check structure copied
    assert dest.exists
    assert dest.child('file1.txt').exists
    assert dest.child('subdir').exists
    assert dest.child('subdir', 'file2.txt').exists

    # Check content
    assert dest.child('file1.txt').read() == "content1"
    assert dest.child('subdir', 'file2.txt').read() == "content2"

Path Properties
---------------

File Path Information
~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestFileOperations::test_file_path_properties

Access path components. Example from `test_local_storage.py::test_file_path_properties <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L162-L169>`_:

.. code-block:: python

    node = storage.node('test:documents/report.pdf')

    assert node.fullpath == 'test:documents/report.pdf'
    assert node.basename == 'report.pdf'
    assert node.stem == 'report'
    assert node.suffix == '.pdf'

.. test: test_local_storage.py::TestDirectoryOperations::test_dirname_property

Get directory name. Example from `test_local_storage.py::test_dirname_property <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L288-L302>`_:

.. code-block:: python

    node = storage.node('test:documents/reports/file.pdf')

    # dirname returns parent fullpath as string
    assert node.dirname == 'test:documents/reports'
    assert node.dirname == node.parent.fullpath

    # Test with parent's dirname
    parent = node.parent
    assert parent.dirname == 'test:documents'

    # Test with root level
    root_file = storage.node('test:file.txt')
    assert root_file.dirname == 'test:'

File Extensions
~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestDirectoryOperations::test_ext_property

Get file extension without dot. Example from `test_local_storage.py::test_ext_property <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L304-L323>`_:

.. code-block:: python

    # File with extension
    node = storage.node('test:document.pdf')
    assert node.ext == 'pdf'
    assert node.suffix == '.pdf'  # Compare with suffix

    # Multiple dots
    node_tar = storage.node('test:archive.tar.gz')
    assert node_tar.ext == 'gz'
    assert node_tar.suffix == '.gz'

    # No extension
    node_no_ext = storage.node('test:README')
    assert node_no_ext.ext == ''
    assert node_no_ext.suffix == ''

.. test: test_local_storage.py::TestDirectoryOperations::test_splitext_method

Split path and extension. Example from `test_local_storage.py::test_splitext_method <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L325-L349>`_:

.. code-block:: python

    # Simple case
    node = storage.node('test:documents/report.pdf')
    name, ext = node.splitext()
    assert name == 'documents/report'
    assert ext == '.pdf'

    # Multiple dots
    node_tar = storage.node('test:archive.tar.gz')
    name, ext = node_tar.splitext()
    assert name == 'archive.tar'
    assert ext == '.gz'

    # No extension
    node_no_ext = storage.node('test:README')
    name, ext = node_no_ext.splitext()
    assert name == 'README'
    assert ext == ''

Batch Attributes
~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestDirectoryOperations::test_ext_attributes_property

Get multiple attributes efficiently. Example from `test_local_storage.py::test_ext_attributes_property <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L351-L383>`_:

.. code-block:: python

    # Create a test file
    test_file = storage.node('test:testfile.txt')
    test_file.write('test content')

    # Get attributes together (more efficient than separate calls)
    mtime, size, isdir = test_file.ext_attributes

    assert mtime is not None
    assert isinstance(mtime, float)
    assert size == 12  # 'test content' is 12 bytes
    assert isdir is False

    # Test with directory
    dir_node = storage.node('test:testdir/')
    dir_node.mkdir()

    mtime_dir, size_dir, isdir_dir = dir_node.ext_attributes
    assert mtime_dir is not None
    assert size_dir is None  # Directories have None size
    assert isdir_dir is True

    # Test with non-existent file
    nonexistent = storage.node('test:nonexistent.txt')
    mtime_none, size_none, isdir_none = nonexistent.ext_attributes
    assert mtime_none is None
    assert size_none is None
    assert isdir_none is False

Path Normalization and Security
--------------------------------

Path Formats
~~~~~~~~~~~~

.. test: test_local_storage.py::TestPathNormalization::test_path_with_slashes

Multiple path formats are supported. Example from `test_local_storage.py::test_path_with_slashes <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L493-L502>`_:

.. code-block:: python

    # All these are equivalent
    n1 = storage.node('test:a/b/c')
    n2 = storage.node('test', 'a', 'b', 'c')
    n3 = storage.node('test:a', 'b', 'c')

    assert n1.fullpath == 'test:a/b/c'
    assert n2.fullpath == 'test:a/b/c'
    assert n3.fullpath == 'test:a/b/c'

Security: Parent Traversal Blocked
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestPathNormalization::test_path_parent_traversal_blocked

Parent directory traversal (``..``) is blocked for security. Example from `test_local_storage.py::test_path_parent_traversal_blocked <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L504-L507>`_:

.. code-block:: python

    import pytest

    # Attempting parent traversal raises ValueError
    with pytest.raises(ValueError, match="Parent directory traversal"):
        storage.node('test:documents/../etc/passwd')

This prevents users from accessing files outside the configured storage path.

Root Mount Access
~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestPathNormalization::test_root_of_mount

Access mount root with empty path. Example from `test_local_storage.py::test_root_of_mount <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L509-L514>`_:

.. code-block:: python

    root = storage.node('test:')

    assert root.fullpath == 'test:'
    assert root.isdir

Text Encodings
--------------

UTF-8 Encoding (Default)
~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestEncodings::test_utf8_encoding

UTF-8 is the default encoding. Example from `test_local_storage.py::test_utf8_encoding <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L520-L526>`_:

.. code-block:: python

    node = storage.node('test:utf8.txt')
    content = "Hello 世界 🌍"

    node.write(content)
    assert node.read() == content

Custom Encodings
~~~~~~~~~~~~~~~~

.. test: test_local_storage.py::TestEncodings::test_latin1_encoding

Specify custom encodings. Example from `test_local_storage.py::test_latin1_encoding <https://github.com/genropy/genro-storage/blob/main/tests/test_local_storage.py#L528-L534>`_:

.. code-block:: python

    node = storage.node('test:latin1.txt')
    content = "Héllo Wørld"

    node.write(content, mode='w', encoding='latin-1')
    assert node.read(mode='r', encoding='latin-1') == content

Next Steps
----------

* Learn about :doc:`copy-strategies` for efficient file synchronization
* Explore :doc:`virtual-nodes` for advanced data manipulation
* See :doc:`/versioning` for S3 version control
* Check :doc:`/backends` for cloud storage configuration
