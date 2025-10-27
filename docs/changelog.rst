Changelog
=========

All notable changes to genro-storage will be documented here.

The format is based on `Keep a Changelog <https://keepachangelog.com/en/1.0.0/>`_,
and this project adheres to `Semantic Versioning <https://semver.org/spec/v2.0.0.html>`_.

Unreleased
----------

In development for next release.

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
