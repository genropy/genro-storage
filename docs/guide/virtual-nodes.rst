Virtual Nodes Guide
===================

Virtual nodes are powerful abstractions for manipulating data without creating physical files.

.. contents:: Table of Contents
   :local:
   :depth: 2

Overview
--------

genro-storage provides two types of virtual nodes:

1. **iternode** - Lazily concatenates multiple files
2. **diffnode** - Generates unified diffs between files

Virtual nodes:

- Don't exist physically (``exists`` returns ``False``)
- Are read-only (cannot write to them)
- Can be materialized by copying to a real node
- Are computed lazily (only when read)

IterNode: File Concatenation
-----------------------------

Creating IterNodes
~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_create_iternode_with_nodes

Create an iternode from multiple source nodes. Example from `test_virtual_nodes.py::test_create_iternode_with_nodes <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L30-L39>`_:

.. code-block:: python

    from genro_storage import StorageManager

    storage = StorageManager()
    storage.configure([{'name': 'mem', 'type': 'memory'}])

    n1 = storage.node('mem:file1.txt')
    n1.write('Hello ')

    n2 = storage.node('mem:file2.txt')
    n2.write('World')

    # Create virtual concatenation
    iternode = storage.iternode(n1, n2)

Reading Concatenated Content
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_read_text_concatenates

Read concatenates all source content. Example from `test_virtual_nodes.py::test_iternode_read_text_concatenates <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L41-L55>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.txt')
    n1.write('One ')

    n2 = storage.node('mem:f2.txt')
    n2.write('Two ')

    n3 = storage.node('mem:f3.txt')
    n3.write('Three')

    iternode = storage.iternode(n1, n2, n3)
    result = iternode.read()

    assert result == 'One Two Three'

Lazy Evaluation
~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_is_lazy

IterNode doesn't read until materialized. Example from `test_virtual_nodes.py::test_iternode_is_lazy <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L57-L69>`_:

.. code-block:: python

    n1 = storage.node('mem:file1.txt')
    n1.write('original')

    iternode = storage.iternode(n1)

    # Change source AFTER creating iternode
    n1.write('modified')

    # Reads current content (lazy evaluation)
    result = iternode.read()
    assert result == 'modified'

Building IterNodes Incrementally
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_append

Append nodes after creation. Example from `test_virtual_nodes.py::test_iternode_append <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L71-L83>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.txt')
    n1.write('First ')

    n2 = storage.node('mem:f2.txt')
    n2.write('Second')

    iternode = storage.iternode(n1)
    iternode.append(n2)

    result = iternode.read()
    assert result == 'First Second'

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_extend

Extend with multiple nodes. Example from `test_virtual_nodes.py::test_iternode_extend <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L85-L100>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.txt')
    n1.write('A ')

    n2 = storage.node('mem:f2.txt')
    n2.write('B ')

    n3 = storage.node('mem:f3.txt')
    n3.write('C')

    iternode = storage.iternode(n1)
    iternode.extend(n2, n3)

    result = iternode.read()
    assert result == 'A B C'

Materializing IterNodes
~~~~~~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_copy_to_destination

Copy iternode content to a destination file. Example from `test_virtual_nodes.py::test_iternode_copy_to_destination <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L123-L137>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.txt')
    n1.write('Part 1 ')

    n2 = storage.node('mem:f2.txt')
    n2.write('Part 2')

    iternode = storage.iternode(n1, n2)

    # Materialize to real file
    dest = storage.node('mem:result.txt')
    iternode.copy_to(dest)

    assert dest.exists
    assert dest.read() == 'Part 1 Part 2'

Binary Content
~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_read_bytes

IterNode works with binary content. Example from `test_virtual_nodes.py::test_iternode_read_bytes <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L162-L173>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.bin')
    n1.write(b'Hello ', mode='wb')

    n2 = storage.node('mem:f2.bin')
    n2.write(b'World', mode='wb')

    iternode = storage.iternode(n1, n2)
    result = iternode.read(mode='rb')

    assert result == b'Hello World'

IterNode Properties
~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_exists_is_false

.. test: test_virtual_nodes.py::TestIterNode::test_iternode_write_raises_error

Virtual nodes have special properties. Examples from `test_virtual_nodes.py <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L146-L160>`_:

.. code-block:: python

    import pytest

    n1 = storage.node('mem:f1.txt')
    n1.write('content')

    iternode = storage.iternode(n1)

    # Virtual - doesn't exist physically
    assert iternode.exists is False

    # Read-only - cannot write
    with pytest.raises(ValueError, match='[Cc]annot write|virtual|no path'):
        iternode.write('content')

DiffNode: Unified Diff Generation
----------------------------------

Creating DiffNodes
~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestDiffNode::test_create_diffnode

Create a diffnode to compare two files. Example from `test_virtual_nodes.py::test_create_diffnode <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L179-L188>`_:

.. code-block:: python

    n1 = storage.node('mem:v1.txt')
    n1.write('content 1')

    n2 = storage.node('mem:v2.txt')
    n2.write('content 2')

    diffnode = storage.diffnode(n1, n2)
    assert diffnode is not None

Generating Diffs
~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_generates_diff

Read generates unified diff format. Example from `test_virtual_nodes.py::test_diffnode_generates_diff <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L190-L205>`_:

.. code-block:: python

    n1 = storage.node('mem:v1.txt')
    n1.write('line 1\\nline 2\\nline 3\\n')

    n2 = storage.node('mem:v2.txt')
    n2.write('line 1\\nline 2 modified\\nline 3\\n')

    diffnode = storage.diffnode(n1, n2)
    diff = diffnode.read()

    assert isinstance(diff, str)
    assert 'line 2' in diff
    assert 'modified' in diff
    # Check for unified diff markers
    assert '---' in diff or '+++' in diff or '@@ -' in diff

Identical Files
~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_identical_files

Diff of identical files is empty or minimal. Example from `test_virtual_nodes.py::test_diffnode_identical_files <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L207-L219>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.txt')
    n1.write('same content\\n')

    n2 = storage.node('mem:f2.txt')
    n2.write('same content\\n')

    diffnode = storage.diffnode(n1, n2)
    diff = diffnode.read()

    # Empty diff or only header
    assert len(diff) == 0 or diff.count('\\n') <= 2

Lazy Diff Generation
~~~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_is_lazy

DiffNode is also lazy. Example from `test_virtual_nodes.py::test_diffnode_is_lazy <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L221-L237>`_:

.. code-block:: python

    n1 = storage.node('mem:v1.txt')
    n1.write('original')

    n2 = storage.node('mem:v2.txt')
    n2.write('different')

    diffnode = storage.diffnode(n1, n2)

    # Change source after creating diffnode
    n1.write('modified')

    # Should read current content
    diff = diffnode.read()
    assert 'modified' in diff or 'different' in diff

Saving Diffs
~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_copy_to_destination

Save diff to a file. Example from `test_virtual_nodes.py::test_diffnode_copy_to_destination <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L239-L253>`_:

.. code-block:: python

    n1 = storage.node('mem:v1.txt')
    n1.write('line 1\\nline 2\\n')

    n2 = storage.node('mem:v2.txt')
    n2.write('line 1\\nline 2 changed\\n')

    diffnode = storage.diffnode(n1, n2)

    # Save diff to file
    dest = storage.node('mem:changes.diff')
    diffnode.copy_to(dest)

    assert dest.exists
    content = dest.read()
    assert 'line 2' in content

DiffNode Properties
~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_exists_is_false

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_write_raises_error

.. test: test_virtual_nodes.py::TestDiffNode::test_diffnode_binary_raises_error

DiffNode limitations. Examples from `test_virtual_nodes.py <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L255-L291>`_:

.. code-block:: python

    import pytest

    n1 = storage.node('mem:f1.txt')
    n1.write('content 1')

    n2 = storage.node('mem:f2.txt')
    n2.write('content 2')

    diffnode = storage.diffnode(n1, n2)

    # Virtual - doesn't exist
    assert diffnode.exists is False

    # Read-only
    with pytest.raises(ValueError, match='[Cc]annot write|virtual|no path'):
        diffnode.write('content')

    # Cannot diff binary files
    b1 = storage.node('mem:file1.bin')
    b1.write(b'\\x00\\x01', mode='wb')

    b2 = storage.node('mem:file2.bin')
    b2.write(b'\\x02\\x03', mode='wb')

    binary_diff = storage.diffnode(b1, b2)

    with pytest.raises(ValueError, match='[Cc]annot diff.*binary'):
        binary_diff.read()

ZIP Creation
------------

Creating ZIP Archives
~~~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestZipMethod::test_zip_single_file

Create ZIP from a single file. Example from `test_virtual_nodes.py::test_zip_single_file <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L297-L307>`_:

.. code-block:: python

    node = storage.node('local:file.txt')
    node.write('content')

    zip_bytes = node.zip()

    assert isinstance(zip_bytes, bytes)
    assert len(zip_bytes) > 0
    # Check ZIP signature
    assert zip_bytes[:2] == b'PK'

.. test: test_virtual_nodes.py::TestZipMethod::test_zip_directory_recursive

Create ZIP from entire directory. Example from `test_virtual_nodes.py::test_zip_directory_recursive <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L309-L334>`_:

.. code-block:: python

    import zipfile
    import io

    dir_node = storage.node('local:mydir')
    dir_node.mkdir()

    dir_node.child('file1.txt').write('content1')
    dir_node.child('file2.txt').write('content2')

    subdir = dir_node.child('subdir')
    subdir.mkdir()
    subdir.child('file3.txt').write('content3')

    zip_bytes = dir_node.zip()

    assert isinstance(zip_bytes, bytes)
    assert zip_bytes[:2] == b'PK'

    # Verify ZIP contains files
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert len(names) >= 3
        assert any('file1.txt' in n for n in names)
        assert any('file2.txt' in n for n in names)
        assert any('file3.txt' in n for n in names)

ZIP from IterNode
~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestZipMethod::test_zip_iternode

Create ZIP from iternode (multiple files). Example from `test_virtual_nodes.py::test_zip_iternode <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L336-L358>`_:

.. code-block:: python

    import zipfile
    import io

    n1 = storage.node('mem:file1.txt')
    n1.write('content1')

    n2 = storage.node('mem:file2.txt')
    n2.write('content2')

    iternode = storage.iternode(n1, n2)
    zip_bytes = iternode.zip()

    assert isinstance(zip_bytes, bytes)
    assert zip_bytes[:2] == b'PK'

    # Verify contents
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert 'file1.txt' in names
        assert 'file2.txt' in names
        assert zf.read('file1.txt') == b'content1'
        assert zf.read('file2.txt') == b'content2'

Saving ZIP Archives
~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestZipMethod::test_zip_and_write

Write ZIP to storage. Example from `test_virtual_nodes.py::test_zip_and_write <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L360-L374>`_:

.. code-block:: python

    n1 = storage.node('mem:f1.txt')
    n1.write('data1')

    n2 = storage.node('mem:f2.txt')
    n2.write('data2')

    iternode = storage.iternode(n1, n2)

    # Save as ZIP
    zip_node = storage.node('mem:archive.zip')
    zip_node.write(iternode.zip(), mode='wb')

    assert zip_node.exists
    assert zip_node.read(mode='rb')[:2] == b'PK'

Real-World Use Cases
--------------------

Building Documents
~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIntegration::test_iternode_workflow

Build reports from sections. Example from `test_virtual_nodes.py::test_iternode_workflow <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L394-L413>`_:

.. code-block:: python

    header = storage.node('mem:header.txt')
    header.write('# Report\\n\\n')

    body = storage.node('mem:body.txt')
    body.write('Content here.\\n\\n')

    footer = storage.node('mem:footer.txt')
    footer.write('End of report.')

    # Build report
    report_builder = storage.iternode(header, body, footer)

    # Write to destination
    report = storage.node('mem:report.txt')
    report_builder.copy_to(report)

    content = report.read()
    assert content == '# Report\\n\\nContent here.\\n\\nEnd of report.'

Tracking Changes
~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIntegration::test_diffnode_workflow

Generate and save change logs. Example from `test_virtual_nodes.py::test_diffnode_workflow <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L415-L431>`_:

.. code-block:: python

    v1 = storage.node('mem:config_v1.txt')
    v1.write('setting1=value1\\nsetting2=value2\\n')

    v2 = storage.node('mem:config_v2.txt')
    v2.write('setting1=value1\\nsetting2=new_value\\n')

    # Generate diff
    changes = storage.diffnode(v1, v2)

    # Save diff to file
    diff_file = storage.node('mem:changes.diff')
    changes.copy_to(diff_file)

    assert diff_file.exists
    assert 'setting2' in diff_file.read()

Creating Backups
~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIntegration::test_zip_iternode_and_save

Backup multiple files as ZIP. Example from `test_virtual_nodes.py::test_zip_iternode_and_save <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L433-L449>`_:

.. code-block:: python

    files = []
    for i in range(3):
        node = storage.node(f'mem:file{i}.txt')
        node.write(f'Content {i}')
        files.append(node)

    # Create ZIP
    archive_builder = storage.iternode(*files)

    # Save ZIP
    zip_file = storage.node('mem:backup.zip')
    zip_file.write(archive_builder.zip(), mode='wb')

    assert zip_file.exists
    assert zip_file.size > 0

Incremental Building
~~~~~~~~~~~~~~~~~~~~

.. test: test_virtual_nodes.py::TestIntegration::test_incremental_build_with_iternode

Build content progressively. Example from `test_virtual_nodes.py::test_incremental_build_with_iternode <https://github.com/genropy/genro-storage/blob/main/tests/test_virtual_nodes.py#L451-L473>`_:

.. code-block:: python

    builder = storage.iternode()

    # Add sections progressively
    intro = storage.node('mem:intro.txt')
    intro.write('Introduction\\n')
    builder.append(intro)

    # Add more sections
    for i in range(1, 4):
        section = storage.node(f'mem:section{i}.txt')
        section.write(f'Section {i}\\n')
        builder.append(section)

    # Finalize
    final = storage.node('mem:document.txt')
    builder.copy_to(final)

    content = final.read()
    assert 'Introduction' in content
    assert 'Section 1' in content
    assert 'Section 3' in content

Best Practices
--------------

When to Use Virtual Nodes
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Use IterNode for**:

- Combining log files
- Building documents from templates
- Merging data from multiple sources
- Creating archives without temporary files

**Use DiffNode for**:

- Version comparison
- Change tracking
- Code review tools
- Configuration auditing

**Use ZIP for**:

- Backups
- File downloads
- Archive creation
- Data export

Performance Tips
~~~~~~~~~~~~~~~~

1. **Lazy evaluation** - Virtual nodes only compute when read
2. **No temporary files** - Direct memory operations
3. **Streaming** - Large files don't need to fit in memory
4. **Efficient** - Minimal overhead compared to manual concatenation

Next Steps
----------

* See :doc:`/versioning` for S3 version control
* Check :doc:`copy-strategies` for efficient synchronization
* Explore :doc:`/examples` for more use cases
* Read :doc:`/backends` for backend capabilities
