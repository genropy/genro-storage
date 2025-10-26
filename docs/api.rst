API Reference
=============

StorageManager
--------------

.. class:: StorageManager()

   .. method:: configure(source)
      
      Configure mounts.

   .. method:: node(mount_or_path, *path_parts)
      
      Create StorageNode.

StorageNode
-----------

.. class:: StorageNode

   Properties: fullpath, exists, isfile, isdir, size, mtime, basename, stem, suffix, parent

   Methods: open, read_bytes, read_text, write_bytes, write_text, delete, copy, move, children, child, mkdir

Exceptions
----------

.. exception:: StorageError
.. exception:: StorageNotFoundError
.. exception:: StoragePermissionError
.. exception:: StorageConfigError
