"""genro-storage - Unified storage abstraction for the Genropy framework.

This package provides a clean, consistent API for accessing files across
different storage backends (local, S3, GCS, Azure, HTTP, etc.) using a
mount-point abstraction inspired by Unix filesystems.

Main Components:
    - StorageManager: Configure and manage storage backends
    - StorageNode: Interact with files and directories
    - Exceptions: Storage-specific exception hierarchy

Quick Start:
    >>> from genro_storage import StorageManager
    >>> 
    >>> # Setup
    >>> storage = StorageManager()
    >>> storage.configure([
    ...     {'name': 'home', 'type': 'local', 'path': '/home/user'},
    ...     {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
    ... ])
    >>> 
    >>> # Access files
    >>> node = storage.node('home:documents/report.pdf')
    >>> content = node.read_text()
    >>> 
    >>> # Copy across backends
    >>> node.copy(storage.node('uploads:backup/report.pdf'))

For more information, see the documentation at:
https://genro-storage.readthedocs.io
"""

__version__ = '0.1.0'

from .manager import StorageManager
from .node import StorageNode, SkipStrategy
from .exceptions import (
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageConfigError,
)

__all__ = [
    # Version
    '__version__',

    # Main classes
    'StorageManager',
    'StorageNode',
    'SkipStrategy',

    # Exceptions
    'StorageError',
    'StorageNotFoundError',
    'StoragePermissionError',
    'StorageConfigError',
]
