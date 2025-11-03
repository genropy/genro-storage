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
    - StorageManager: Configure and manage storage backends (sync)
    - StorageNode: Interact with files and directories (sync)
    - AsyncStorageManager: Async wrapper around StorageManager
    - AsyncStorageNode: Async wrapper around StorageNode
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
    >>> from genro_storage.asyncer_wrapper import AsyncStorageManager
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

__version__ = '0.4.0'

from .manager import StorageManager
from .node import StorageNode, SkipStrategy
from .exceptions import (
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageConfigError,
)
from .api_introspection import get_api_structure, get_api_structure_multi

# Async support is optional (requires asyncer)
try:
    from .asyncer_wrapper import AsyncStorageManager, AsyncStorageNode
    _ASYNC_AVAILABLE = True
except ImportError:
    _ASYNC_AVAILABLE = False
    AsyncStorageManager = None  # type: ignore
    AsyncStorageNode = None  # type: ignore

__all__ = [
    # Version
    '__version__',

    # Main classes (sync)
    'StorageManager',
    'StorageNode',
    'SkipStrategy',

    # Async classes (optional)
    'AsyncStorageManager',
    'AsyncStorageNode',

    # Exceptions
    'StorageError',
    'StorageNotFoundError',
    'StoragePermissionError',
    'StorageConfigError',

    # API Introspection
    'get_api_structure',
    'get_api_structure_multi',
]
