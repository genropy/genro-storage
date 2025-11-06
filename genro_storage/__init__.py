# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""genro-storage - Unified storage abstraction for the Genropy framework.

This package provides a clean, consistent API for accessing files across
different storage backends (local, S3, GCS, Azure, HTTP, etc.) using a
mount-point abstraction inspired by Unix filesystems.

Main Components:
    - AsyncStorageManager: Async manager for storage backends (base implementation)
    - AsyncStorageNode: Async interface for files and directories
    - StorageManager: Sync wrapper around AsyncStorageManager
    - StorageNode: Sync wrapper around AsyncStorageNode
    - Exceptions: Storage-specific exception hierarchy

Quick Start (Sync):
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

Quick Start (Async):
    >>> from genro_storage import AsyncStorageManager
    >>>
    >>> storage = AsyncStorageManager()
    >>> storage.configure([
    ...     {'name': 's3', 'type': 's3', 'bucket': 'my-bucket'}
    ... ])
    >>>
    >>> node = storage.node('s3:file.txt')
    >>> data = await node.read_bytes()
    >>> await node.write_bytes(b'new data')

For more information, see the documentation at:
https://genro-storage.readthedocs.io
"""

__version__ = "0.5.0"

from .node import SkipStrategy
from .exceptions import (
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageConfigError,
)
from .api_introspection import get_api_structure, get_api_structure_multi

# Async/Sync unified implementation with SmartSync
try:
    from .async_storage_manager import AsyncStorageManager
    from .async_storage_node import AsyncStorageNode

    # StorageManager is now just AsyncStorageManager - use _sync parameter to control mode
    # Sync mode: StorageManager(_sync=True) or AsyncStorageManager(_sync=True)
    # Async mode: StorageManager() or AsyncStorageManager() [default]
    StorageManager = AsyncStorageManager

    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    AsyncStorageManager = None  # type: ignore
    AsyncStorageNode = None  # type: ignore
    StorageManager = None  # type: ignore

__all__ = [
    # Version
    "__version__",
    # Main classes (sync)
    "StorageManager",
    "StorageNode",
    "SkipStrategy",
    # Async classes (optional)
    "AsyncStorageManager",
    "AsyncStorageNode",
    # Exceptions
    "StorageError",
    "StorageNotFoundError",
    "StoragePermissionError",
    "StorageConfigError",
    # API Introspection
    "get_api_structure",
    "get_api_structure_multi",
]
