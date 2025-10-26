API Reference
=============

This page provides the complete API documentation for genro-storage.

StorageManager
--------------

Main entry point for configuring and accessing storage.

.. class:: StorageManager()

   Creates a new storage manager instance with no configured mounts.

   **Example:**

   .. code-block:: python

      from genro_storage import StorageManager
      
      storage = StorageManager()

Methods
~~~~~~~

.. method:: configure(source: str | list[dict[str, Any]]) -> None

   Configure mount points from various sources.

   :param source: Configuration source - can be a path to YAML/JSON file or a list of mount configurations
   :type source: str | list[dict[str, Any]]
   :raises FileNotFoundError: If file path doesn't exist
   :raises ValueError: If configuration format is invalid
   :raises TypeError: If source is neither str nor list

   **Configuration Format:**

   Each mount configuration must have:
   
   - ``name`` (str, required): Mount point name (e.g., "home", "uploads")
   - ``type`` (str, required): Backend type ("local", "s3", "gcs", "azure", "http", "memory")
   
   **Local Storage:**

   .. code-block:: python

      {
          "name": "home",
          "type": "local",
          "path": "/home/user"  # required: absolute path
      }

   **S3 Storage:**

   .. code-block:: python

      {
          "name": "uploads",
          "type": "s3",
          "bucket": "my-bucket",  # required
          "prefix": "uploads/",   # optional, default: ""
          "region": "eu-west-1",  # optional
          "anon": False           # optional, default: False
      }

   **GCS Storage:**

   .. code-block:: python

      {
          "name": "backups",
          "type": "gcs",
          "bucket": "my-backups",  # required
          "prefix": "",            # optional
          "token": "path/to/service-account.json"  # optional
      }

   **Azure Blob Storage:**

   .. code-block:: python

      {
          "name": "archive",
          "type": "azure",
          "container": "archives",     # required
          "account_name": "myaccount", # required
          "account_key": "..."         # optional if using managed identity
      }

   **HTTP Storage (read-only):**

   .. code-block:: python

      {
          "name": "cdn",
          "type": "http",
          "base_url": "https://cdn.example.com"  # required
      }

   **Memory Storage (for testing):**

   .. code-block:: python

      {
          "name": "test",
          "type": "memory"
      }

   **Examples:**

   .. code-block:: python

      # From YAML file
      storage.configure('/etc/app/storage.yaml')
      
      # From JSON file
      storage.configure('./config/storage.json')
      
      # From list
      storage.configure([
          {'name': 'home', 'type': 'local', 'path': '/home/user'},
          {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
      ])

   **Behavior:**
   
   - If a mount with the same name already exists, it is replaced
   - Invalid configurations raise exceptions immediately
   - File paths are resolved relative to current working directory

.. method:: node(mount_or_path: str, *path_parts: str) -> StorageNode

   Create a StorageNode pointing to a file or directory.

   :param mount_or_path: Either full path with mount ("mount:path/to/file") or just mount name
   :type mount_or_path: str
   :param path_parts: Additional path components to join
   :type path_parts: str
   :returns: StorageNode instance
   :rtype: StorageNode
   :raises KeyError: If mount point doesn't exist
   :raises ValueError: If path format is invalid

   **Examples:**

   .. code-block:: python

      # Full path in one string
      node = storage.node('home:documents/report.pdf')
      
      # Mount + path parts
      node = storage.node('home', 'documents', 'report.pdf')
      
      # Mix styles
      node = storage.node('home:documents', 'reports', 'q4.pdf')
      
      # Dynamic composition
      user_id = '123'
      year = '2024'
      node = storage.node('uploads', 'users', user_id, year, 'avatar.jpg')
      # → uploads:users/123/2024/avatar.jpg
      
      # Just mount (root of storage)
      node = storage.node('home')
      # → home:

   **Path Normalization:**
   
   - Multiple slashes collapsed: ``a//b`` → ``a/b``
   - Leading/trailing slashes stripped
   - No support for ``..`` (parent directory) - raises ValueError

StorageNode
-----------

Represents a file or directory in a storage backend.

.. note::
   Users don't instantiate StorageNode directly - only via ``storage.node()``

Properties
~~~~~~~~~~

.. attribute:: fullpath
   :type: str

   Full path including mount point.

   .. code-block:: python

      node = storage.node('home:documents/file.txt')
      print(node.fullpath)  # "home:documents/file.txt"

.. attribute:: exists
   :type: bool

   True if file or directory exists.

   .. code-block:: python

      if node.exists:
          print("File exists!")

.. attribute:: isfile
   :type: bool

   True if node points to a file.

   .. code-block:: python

      if node.isfile:
          data = node.read_bytes()

.. attribute:: isdir
   :type: bool

   True if node points to a directory.

   .. code-block:: python

      if node.isdir:
          for child in node.children():
              print(child.basename)

.. attribute:: size
   :type: int

   File size in bytes. Raises exception if not a file.

   .. code-block:: python

      print(f"File size: {node.size} bytes")

.. attribute:: mtime
   :type: float

   Last modification time as Unix timestamp.

   .. code-block:: python

      from datetime import datetime
      mod_time = datetime.fromtimestamp(node.mtime)
      print(f"Modified: {mod_time}")

.. attribute:: basename
   :type: str

   Filename with extension.

   .. code-block:: python

      node = storage.node('home:documents/report.pdf')
      print(node.basename)  # "report.pdf"

.. attribute:: stem
   :type: str

   Filename without extension.

   .. code-block:: python

      node = storage.node('home:documents/report.pdf')
      print(node.stem)  # "report"

.. attribute:: suffix
   :type: str

   File extension including dot.

   .. code-block:: python

      node = storage.node('home:documents/report.pdf')
      print(node.suffix)  # ".pdf"

.. attribute:: parent
   :type: StorageNode

   Parent directory as StorageNode.

   .. code-block:: python

      node = storage.node('home:documents/reports/q4.pdf')
      parent = node.parent
      print(parent.fullpath)  # "home:documents/reports"

Methods
~~~~~~~

.. method:: open(mode: str = 'rb') -> BinaryIO | TextIO

   Open file and return file-like object.

   :param mode: File mode ('r', 'rb', 'w', 'wb', 'a', 'ab')
   :type mode: str
   :returns: File-like object (context manager)
   :rtype: BinaryIO | TextIO

   **Example:**

   .. code-block:: python

      with node.open('rb') as f:
          data = f.read()
      
      with node.open('w') as f:
          f.write("Hello World")

.. method:: read_bytes() -> bytes

   Read entire file as bytes.

   :returns: File contents
   :rtype: bytes
   :raises FileNotFoundError: If file doesn't exist

   **Example:**

   .. code-block:: python

      data = node.read_bytes()

.. method:: read_text(encoding: str = 'utf-8') -> str

   Read entire file as string.

   :param encoding: Text encoding (default: 'utf-8')
   :type encoding: str
   :returns: File contents
   :rtype: str

   **Example:**

   .. code-block:: python

      content = node.read_text()
      content = node.read_text('latin-1')

.. method:: write_bytes(data: bytes) -> None

   Write bytes to file.

   :param data: Bytes to write
   :type data: bytes

   **Example:**

   .. code-block:: python

      node.write_bytes(b'Hello World')

.. method:: write_text(text: str, encoding: str = 'utf-8') -> None

   Write string to file.

   :param text: String to write
   :type text: str
   :param encoding: Text encoding (default: 'utf-8')
   :type encoding: str

   **Example:**

   .. code-block:: python

      node.write_text("Hello World")
      node.write_text("Café", encoding='utf-8')

.. method:: delete() -> None

   Delete file or directory.

   **Behavior:**
   
   - For files: deletes the file
   - For directories: deletes recursively (like ``rm -rf``)
   - If doesn't exist: no error (idempotent)

   **Example:**

   .. code-block:: python

      node.delete()

.. method:: copy(dest: StorageNode | str) -> StorageNode

   Copy file or directory to destination.

   :param dest: Destination as StorageNode or path string
   :type dest: StorageNode | str
   :returns: Destination StorageNode
   :rtype: StorageNode

   **Behavior:**
   
   - Works across different storage backends
   - If dest is directory, creates file with same basename inside
   - Overwrites existing files
   - For directories: copies recursively

   **Example:**

   .. code-block:: python

      # Same storage
      node.copy(storage.node('home:backup/file.txt'))
      
      # Cross-storage
      node.copy(storage.node('s3:uploads/file.txt'))
      
      # String destination
      node.copy('home:backup/file.txt')

.. method:: move(dest: StorageNode | str) -> StorageNode

   Move file or directory to destination.

   :param dest: Destination as StorageNode or path string
   :type dest: StorageNode | str
   :returns: Destination StorageNode
   :rtype: StorageNode

   **Behavior:**
   
   - If same backend: efficient rename
   - If different backend: copy + delete
   - Updates current node to point to new location

   **Example:**

   .. code-block:: python

      node.move(storage.node('home:archive/file.txt'))
      # node now points to home:archive/file.txt

.. method:: children() -> list[StorageNode]

   List child nodes (if directory).

   :returns: List of StorageNode objects
   :rtype: list[StorageNode]
   :raises: Exception if not a directory

   **Example:**

   .. code-block:: python

      if node.isdir:
          for child in node.children():
              print(f"{child.basename}: {child.size} bytes")

.. method:: child(name: str) -> StorageNode

   Get a child node by name.

   :param name: Child name (filename or subdirectory)
   :type name: str
   :returns: StorageNode (may not exist)
   :rtype: StorageNode

   **Example:**

   .. code-block:: python

      docs = storage.node('home:documents')
      report = docs.child('report.pdf')

.. method:: mkdir(parents: bool = False, exist_ok: bool = False) -> None

   Create directory.

   :param parents: If True, create parent directories as needed
   :type parents: bool
   :param exist_ok: If True, don't raise error if already exists
   :type exist_ok: bool
   :raises FileExistsError: If exists and exist_ok=False
   :raises FileNotFoundError: If parent doesn't exist and parents=False

   **Example:**

   .. code-block:: python

      node.mkdir()
      node.mkdir(parents=True, exist_ok=True)

Exceptions
----------

All exceptions inherit from ``StorageError`` base class.

.. exception:: StorageError

   Base exception for all storage-related errors.

.. exception:: StorageNotFoundError

   Raised when a file, directory, or mount point is not found.
   Inherits from both ``StorageError`` and ``FileNotFoundError``.

.. exception:: StoragePermissionError

   Raised when a permission-related error occurs.
   Inherits from both ``StorageError`` and ``PermissionError``.

.. exception:: StorageConfigError

   Raised when configuration is invalid.
   Inherits from both ``StorageError`` and ``ValueError``.

**Exception Hierarchy:**

.. code-block:: text

   StorageError (base)
   ├── StorageNotFoundError (also FileNotFoundError)
   ├── StoragePermissionError (also PermissionError)
   └── StorageConfigError (also ValueError)

**Usage Example:**

.. code-block:: python

   from genro_storage import (
       StorageError,
       StorageNotFoundError,
       StoragePermissionError,
       StorageConfigError,
   )
   
   try:
       node = storage.node('missing:file.txt')
       data = node.read_bytes()
   except StorageNotFoundError:
       print("Storage or file not found")
   except StoragePermissionError:
       print("Permission denied")
   except StorageError as e:
       print(f"Storage error: {e}")
