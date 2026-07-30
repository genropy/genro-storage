Changelog
=========

All notable changes to genro-storage will be documented here.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

0.7.1 - July 2026
-----------------

Added
~~~~~

- ``StorageConfig`` is now exported from the package: ``from genro_storage
  import StorageConfig``. It is the grammar ``configure()`` accepts as a
  source, so it belongs on the public surface next to ``StorageManager``;
  0.7.0 only exposed it as ``genro_storage.config.StorageConfig``. The
  grammar mixin itself stays reachable as ``StorageManager.grammar``.

0.7.0 - July 2026
-----------------

Added
~~~~~

- At-rest encryption: a mount declared ``encrypted`` stores ciphertext, with
  transparent encrypt/decrypt on the node read/write surface. Key material is
  comma-separated Fernet keys with ``MultiFernet`` semantics (first key
  encrypts, all keys decrypt) supplied as ``storage_key`` or via
  ``set_encryption_keys()``; ``encryption_active`` and
  ``mount_is_encrypted()`` report the state. Requires the new optional extra
  ``genro-storage[encryption]``. See :doc:`encryption`, including the coverage
  boundary — ``open()``, ``local_path()``, ``call()``, ``serve()`` and
  ``copy_to()``/``move_to()`` carry the stored bytes untouched.
- Pythonic configuration through the ``StorageConfig`` builder grammar, with
  closed element signatures validated at the recipe line.
- ``StorageGrammar``, the grammar mixin, exposed as ``StorageManager.grammar``
  so a host dialect can govern a storage section by reference.
- Resolver support on every field whose value may come from the environment:
  a ``BagResolver`` can be passed in place of a literal and is read when
  ``configure()`` consumes it.

Changed
~~~~~~~

- Service-backed SMB and SFTP tests now skip when the service is unreachable
  instead of failing, so a bare ``pytest`` is green with no Docker services
  running.

Removed
~~~~~~~

- **Breaking**: Python 3.10 is no longer supported. The floor is 3.11,
  matching genro-bag and genro-toolbox.
- **Breaking**: the ``^pointer`` / ``${template}`` idiom in the builder
  adapter. Pass a ``BagResolver`` as the value instead — no seeding step and
  no name to keep in sync.

Dependencies
~~~~~~~~~~~~

- ``genro-builders`` floor raised to 0.22.0 (resolver-aware ``runtime_values``,
  sub-builder by reference).
- ``genro-bag>=0.20.1`` added as a direct dependency (0.20.0 imports
  ``typing_extensions`` without declaring it, so a clean install fails).

0.4.2 - October 2025
--------------------

Added
~~~~~

- Git backend support for Git repositories
- GitHub backend support for GitHub repositories
- WebDAV backend support (Nextcloud, ownCloud, SharePoint)
- LibArchive backend support (RAR, 7z, ISO, and 20+ formats)
- Native permission control for all backends (readonly, readwrite, delete)
- Comprehensive permission tests for all backend types
- Validation of permissions against backend capabilities at configuration time
- Test coverage improvements: 79% → 85% (411 tests, 401 passing)
- Complete test coverage for RelativeMountBackend (75% → 96%)
- Complete test coverage for BackendCapabilities (88% → 100%)
- Docker services for integration testing (Azurite, fake-gcs-server, SFTP, SMB, WebDAV)

Changed
~~~~~~~

- Improved CI workflow with all Docker services for integration tests
- Enhanced test infrastructure with service emulators

0.4.1 - October 2025
--------------------

Added
~~~~~

- SMB/CIFS backend support for Windows and Samba shares
- SFTP backend support for SSH File Transfer Protocol
- ZIP archive backend support (read and write)
- TAR archive backend support (with gzip, bzip2, xz compression)
- Configuration tests for new backends
- Backend capability tests

0.4.0 - October 2025
--------------------

Added
~~~~~

- Relative mounts with permissions
- Unified read/write API
- RelativeMountBackend for path prefixing and permission enforcement

Changed
~~~~~~~

- Improved permission handling architecture
- Enhanced backend configuration system

0.3.0 - October 2025
--------------------

Added
~~~~~

- Async/await support via AsyncStorageManager
- AsyncStorageNode for async file operations
- Integration with asyncer for automatic sync→async conversion
- FastAPI compatibility examples
- Async tests and documentation

0.2.0 - October 2025
--------------------

Added
~~~~~

- Virtual nodes (iternode, diffnode)
- Interactive Jupyter notebooks tutorials
- Binder support for online tutorials
- Enhanced testing infrastructure
- Copy strategy improvements

0.1.0-beta - October 2025
-------------------------

**Beta Release** - Ready for production testing

Added
~~~~~

- Complete API implementation with stable interface
- Support for 7 storage backends: Local, S3, GCS, Azure, HTTP, Memory, Base64
- Comprehensive test suite with 195 tests (79% coverage)
- CI/CD testing on Python 3.9, 3.10, 3.11, 3.12
- Full ReadTheDocs documentation
- Mount point configuration system
- StorageManager for managing mount points
- StorageNode for file/directory operations
- Configuration from YAML and JSON files
- Cross-storage copy and move operations
- Intelligent copy skip strategies (exists, size, hash, custom)
- MD5 hashing and content-based equality
- Base64 backend with writable mutable paths
- call() method for external tool integration (ffmpeg, imagemagick, etc.)
- serve() method for WSGI file serving (Flask, Django, Pyramid)
- mimetype property for automatic content-type detection
- local_path() context manager for external tools
- Callable path support for dynamic directories
- Cloud metadata get/set (S3, GCS, Azure)
- URL generation (presigned URLs, data URIs)
- S3 versioning support
- MinIO integration testing

Technical
~~~~~~~~~

- Battle-tested code extracted from Genropy (Python web framework since 2006)
- Storage abstraction layer refined over 6+ years of production use (since 2018)
- Full type hints with Python 3.9+ compatibility
- Powered by fsspec for backend abstraction
