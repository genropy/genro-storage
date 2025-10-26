API Reference
=============

This page provides detailed API documentation for all public classes and methods in ``genro-storage``.

StorageManager
--------------

.. class:: StorageManager()

   Main entry point for configuring and accessing storage.

   The StorageManager is responsible for managing mount points and creating StorageNode instances.

   **Example:**

   .. code-block:: python

       from genro_storage import StorageManager

       storage = StorageManager()
       storage.configure([
           {'name': 'home', 'type': 'local', 'path': '/home/user'}
       ])

   .. method:: configure(source)

      Configure mount points from various sources.

      :param source: Configuration source - either a file path (str) or list of configuration dictionaries
      :type source: str | list[dict]
      :raises FileNotFoundError: If file path doesn't exist
      :raises ValueError: If configuration format is invalid
      :raises TypeError: If source is neither str nor list

      **Configuration Dictionary Format:**

      Each mount configuration must include:

      * ``name`` (str, required): Mount point name
      * ``type`` (str, required): Backend type (``local``, ``s3``, ``gcs``, ``azure``, ``http``, ``memory``)
      * Additional fields depend on the backend type

      **Local Storage:**

      .. code-block:: python

          {
              'name': 'home',
              'type': 'local',
              'path': '/home/user'  # required
          }

      **S3 Storage:**

      .. code-block:: python

          {
              'name': 'uploads',
              'type': 's3',
              'bucket': 'my-bucket',     # required
              'prefix': 'uploads/',      # optional
              'region': 'eu-west-1',     # optional
              'anon': False              # optional
          }

      **GCS Storage:**

      .. code-block:: python

          {
              'name': 'backups',
              'type': 'gcs',
              'bucket': 'my-backups',    # required
              'prefix': '',              # optional
              'token': 'path/to/key.json'  # optional
          }

      **Azure Blob Storage:**

      .. code-block:: python

          {
              'name': 'archive',
              'type': 'azure',
              'container': 'archives',   # required
              'account_name': 'myaccount',  # required
              'account_key': '...'       # optional
          }

      **HTTP Storage (read-only):**

      .. code-block:: python

          {
              'name': 'cdn',
              'type': 'http',
              'base_url': 'https://cdn.example.com'  # required
          }

      **Memory Storage:**

      .. code-block:: python

          {
              'name': 'test',
              'type': 'memory'
          }

      **Examples:**

      .. code-block:: python

          # From list
          storage.configure([
              {'name': 'home', 'type': 'local', 'path': '/home/user'},
              {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
          ])

          # From YAML file
          storage.configure('config/storage.yaml')

          # From JSON file
          storage.configure('config/storage.json')

          # Multiple calls (last wins if same name)
          storage.configure([{'name': 'home', 'type': 'local', 'path': '/tmp'}])
          storage.configure([{'name': 'uploads', 'type': 's3', 'bucket': 'prod'}])

   .. method:: node(mount_or_path, *path_parts)

      Create a StorageNode pointing to a file or directory.

      :param mount_or_path: Full path (``mount:path``) or just mount name
      :type mount_or_path: str
      :param path_parts: Additional path components to join
      :type path_parts: str
      :returns: StorageNode instance
      :rtype: StorageNode
      :raises KeyError: If mount point doesn't exist
      :raises ValueError: If path format is invalid (e.g., contains ``..``)

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
          node = storage.node('uploads', 'users', user_id, 'avatar.jpg')

          # Mount root
          node = storage.node('home')

StorageNode
-----------

.. class:: StorageNode

   Represents a file or directory in a storage backend.

   StorageNode instances should not be created directly. Use :meth:`StorageManager.node` instead.

   Properties
   ~~~~~~~~~~

   .. attribute:: fullpath

      Full path including mount point.

      :type: str

      .. code-block:: python

          node = storage.node('home:documents/file.txt')
          print(node.fullpath)  # 'home:documents/file.txt'

   .. attribute:: exists

      True if file or directory exists.

      :type: bool

      .. code-block:: python

          if node.exists:
              print("File exists!")

   .. attribute:: isfile

      True if node points to a file.

      :type: bool

      .. code-block:: python

          if node.isfile:
              data = node.read_bytes()

   .. attribute:: isdir

      True if node points to a directory.

      :type: bool

      .. code-block:: python

          if node.isdir:
              for child in node.children():
                  print(child.basename)

   .. attribute:: size

      File size in bytes.

      :type: int
      :raises Exception: If not a file or doesn't exist

      .. code-block:: python

          print(f"File size: {node.size} bytes")

   .. attribute:: mtime

      Last modification time as Unix timestamp.

      :type: float
      :raises Exception: If path doesn't exist

      .. code-block:: python

          from datetime import datetime
          mod_time = datetime.fromtimestamp(node.mtime)

   .. attribute:: basename

      Filename with extension.

      :type: str

      .. code-block:: python

          node = storage.node('home:path/report.pdf')
          print(node.basename)  # 'report.pdf'

   .. attribute:: stem

      Filename without extension.

      :type: str

      .. code-block:: python

          node = storage.node('home:report.pdf')
          print(node.stem)  # 'report'

   .. attribute:: suffix

      File extension including dot.

      :type: str

      .. code-block:: python

          node = storage.node('home:report.pdf')
          print(node.suffix)  # '.pdf'

   .. attribute:: parent

      Parent directory as StorageNode.

      :type: StorageNode

      .. code-block:: python

          node = storage.node('home:documents/reports/q4.pdf')
          parent = node.parent
          print(parent.fullpath)  # 'home:documents/reports'

   Methods
   ~~~~~~~

   .. method:: open(mode='rb')

      Open file and return file-like object.

      :param mode: File mode ('r', 'rb', 'w', 'wb', 'a', 'ab')
      :type mode: str
      :returns: File-like object (context manager)
      :rtype: BinaryIO | TextIO

      .. code-block:: python

          with node.open('rb') as f:
              data = f.read()

          with node.open('w') as f:
              f.write("Hello World")

   .. method:: read_bytes()

      Read entire file as bytes.

      :returns: File content as bytes
      :rtype: bytes
      :raises FileNotFoundError: If file doesn't exist

      .. code-block:: python

          data = node.read_bytes()

   .. method:: read_text(encoding='utf-8')

      Read entire file as string.

      :param encoding: Text encoding
      :type encoding: str
      :returns: File content as string
      :rtype: str
      :raises FileNotFoundError: If file doesn't exist
      :raises UnicodeDecodeError: If encoding is incorrect

      .. code-block:: python

          content = node.read_text()
          content = node.read_text('latin-1')

   .. method:: write_bytes(data)

      Write bytes to file.

      :param data: Bytes to write
      :type data: bytes

      .. code-block:: python

          node.write_bytes(b'Hello World')

   .. method:: write_text(text, encoding='utf-8')

      Write string to file.

      :param text: String to write
      :type text: str
      :param encoding: Text encoding
      :type encoding: str

      .. code-block:: python

          node.write_text("Hello World")
          node.write_text("Café", encoding='utf-8')

   .. method:: delete()

      Delete file or directory.

      For directories, deletes recursively. Idempotent (no error if doesn't exist).

      .. code-block:: python

          node.delete()

   .. method:: copy(dest)

      Copy file or directory to destination.

      :param dest: Destination as StorageNode or path string
      :type dest: StorageNode | str
      :returns: Destination StorageNode
      :rtype: StorageNode

      Works across different storage backends. Copies directories recursively.

      .. code-block:: python

          # Same storage
          node.copy(storage.node('home:backup/file.txt'))

          # Cross-storage
          node.copy(storage.node('s3:uploads/file.txt'))

          # String destination
          node.copy('home:backup/file.txt')

   .. method:: move(dest)

      Move file or directory to destination.

      :param dest: Destination as StorageNode or path string
      :type dest: StorageNode | str
      :returns: Destination StorageNode
      :rtype: StorageNode

      Uses efficient rename within same backend, or copy+delete across backends.
      Updates current node to point to new location.

      .. code-block:: python

          node.move(storage.node('home:archive/file.txt'))
          # node now points to home:archive/file.txt

   .. method:: children()

      List child nodes (if directory).

      :returns: List of child StorageNode objects
      :rtype: list[StorageNode]
      :raises Exception: If not a directory

      .. code-block:: python

          if node.isdir:
              for child in node.children():
                  print(f"{child.basename}: {child.size} bytes")

   .. method:: child(name)

      Get a child node by name.

      :param name: Child name (filename or subdirectory)
      :type name: str
      :returns: Child StorageNode (may not exist)
      :rtype: StorageNode

      .. code-block:: python

          docs = storage.node('home:documents')
          report = docs.child('report.pdf')

   .. method:: mkdir(parents=False, exist_ok=False)

      Create directory.

      :param parents: If True, create parent directories as needed
      :type parents: bool
      :param exist_ok: If True, don't raise error if already exists
      :type exist_ok: bool
      :raises FileExistsError: If exists and ``exist_ok=False``
      :raises FileNotFoundError: If parent doesn't exist and ``parents=False``

      .. code-block:: python

          node.mkdir()
          node.mkdir(parents=True, exist_ok=True)

Exceptions
----------

.. exception:: StorageError

   Base exception for all storage errors.

.. exception:: StorageNotFoundError

   File or mount point not found. Inherits from :exc:`FileNotFoundError`.

.. exception:: StoragePermissionError

   Permission denied. Inherits from :exc:`PermissionError`.

.. exception:: StorageConfigError

   Invalid configuration. Inherits from :exc:`ValueError`.

**Example:**

.. code-block:: python

    from genro_storage import StorageNotFoundError

    try:
        node.read_bytes()
    except StorageNotFoundError:
        print("File not found")
