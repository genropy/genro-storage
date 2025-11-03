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

"""Async wrapper using asyncer for automatic sync→async conversion.

This module provides AsyncStorageManager and AsyncStorageNode classes that wrap
the synchronous genro-storage API and make it usable in async/await contexts
using the asyncer library (by Sebastián Ramírez, author of FastAPI).

Example:
    >>> from genro_storage.asyncer_wrapper import AsyncStorageManager
    >>>
    >>> storage = AsyncStorageManager()
    >>> storage.configure([{
    ...     'name': 's3',
    ...     'type': 's3',
    ...     'bucket': 'my-bucket'
    ... }])
    >>>
    >>> node = storage.node('s3:file.txt')
    >>> data = await node.read(mode='rb')
    >>> await node.write(b'new data', mode='wb')
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

try:
    from asyncer import asyncify
except ImportError:
    raise ImportError(
        "asyncer is required for async support. "
        "Install it with: pip install asyncer"
    )

from .manager import StorageManager
from .node import StorageNode

__all__ = ['AsyncStorageManager', 'AsyncStorageNode']


class AsyncStorageManager:
    """Async wrapper around sync StorageManager using asyncer.

    This class wraps the synchronous StorageManager and provides async-compatible
    methods for use in async/await contexts. It uses asyncer to automatically
    run blocking operations in a thread pool.

    Note:
        Configuration methods (configure, add_mount) are synchronous and should
        be called during application startup, not in async request handlers.

    Example:
        >>> storage = AsyncStorageManager()
        >>> storage.configure([{'name': 'local', 'type': 'local', 'path': '/tmp'}])
        >>>
        >>> # In async context
        >>> node = storage.node('local:test.txt')
        >>> await node.write('Hello async world')
    """

    def __init__(self):
        """Initialize the async storage manager with a sync StorageManager."""
        self._storage = StorageManager()

    def configure(self, source: str | list[dict[str, Any]]) -> None:
        """Configure mount points (synchronous).

        This is a synchronous method and should be called during application
        startup, not in async request handlers.

        Args:
            source: Configuration source (file path or list of mount configs)

        Example:
            >>> storage = AsyncStorageManager()
            >>> storage.configure([
            ...     {'name': 's3', 'type': 's3', 'bucket': 'my-bucket'},
            ...     {'name': 'local', 'type': 'local', 'path': '/tmp'}
            ... ])
        """
        self._storage.configure(source)

    def add_mount(self, config: dict[str, Any]) -> None:
        """Add a mount point at runtime (synchronous).

        This is a synchronous method that adds a single mount point dynamically.

        Args:
            config: Mount configuration dictionary

        Example:
            >>> storage.add_mount({
            ...     'name': 'uploads',
            ...     'type': 's3',
            ...     'bucket': 'uploads-bucket'
            ... })
        """
        self._storage.configure([config])

    def node(self, mount_or_path: str | None = None, *path_parts: str) -> AsyncStorageNode:
        """Create an async-wrapped StorageNode.

        Args:
            mount_or_path: Mount point and path (e.g., "s3:path/to/file")
            *path_parts: Additional path components

        Returns:
            AsyncStorageNode: Async wrapper around StorageNode

        Example:
            >>> node = storage.node('s3:documents/report.pdf')
            >>> # or
            >>> node = storage.node('s3', 'documents', 'report.pdf')
        """
        sync_node = self._storage.node(mount_or_path, *path_parts)
        return AsyncStorageNode(sync_node)

    def has_mount(self, name: str) -> bool:
        """Check if a mount point exists (synchronous).

        Args:
            name: Mount point name

        Returns:
            bool: True if mount exists
        """
        return self._storage.has_mount(name)

    def get_mount_names(self) -> list[str]:
        """Get list of configured mount names (synchronous).

        Returns:
            list[str]: List of mount point names
        """
        return self._storage.get_mount_names()


class AsyncStorageNode:
    """Async wrapper around sync StorageNode using asyncer.

    This class provides async methods for file operations by wrapping
    the synchronous StorageNode methods with asyncer.asyncify.

    All I/O operations are async. Properties that don't require I/O
    (like path, fullpath, basename) remain synchronous.

    Example:
        >>> node = storage.node('s3:file.txt')
        >>>
        >>> # Async I/O operations
        >>> if await node.exists():
        ...     data = await node.read_bytes()
        ...     await node.delete()
        >>>
        >>> # Sync properties
        >>> print(node.path)  # 'file.txt'
        >>> print(node.fullpath)  # 's3:file.txt'
    """

    def __init__(self, sync_node: StorageNode):
        """Initialize async node wrapper.

        Args:
            sync_node: The synchronous StorageNode to wrap
        """
        self._node = sync_node

    # Async I/O operations

    async def read(self, mode: str = 'r', encoding: str = 'utf-8') -> str | bytes:
        """Read file content in text or binary mode (async).

        Args:
            mode: Read mode - 'r' for text (default), 'rb' for binary
            encoding: Text encoding (used only for text mode)

        Returns:
            str | bytes: File content as text or bytes depending on mode

        Example:
            >>> # Read as text (default)
            >>> content = await node.read()
            >>> content = await node.read(mode='r')
            >>>
            >>> # Read as binary
            >>> data = await node.read(mode='rb')
        """
        return await asyncify(self._node.read)(mode, encoding)

    async def write(self, data: str | bytes, mode: str = 'w', encoding: str = 'utf-8', skip_if_unchanged: bool = False) -> bool:
        """Write data to file in text or binary mode (async).

        Args:
            data: Data to write (str for text mode, bytes for binary mode)
            mode: Write mode - 'w' for text (default), 'wb' for binary
            encoding: Text encoding (used only for text mode)
            skip_if_unchanged: If True, skip writing if content identical

        Returns:
            bool: True if written, False if skipped

        Example:
            >>> # Write text (default)
            >>> await node.write('Hello World')
            >>> await node.write('Hello', mode='w')
            >>>
            >>> # Write binary
            >>> await node.write(b'binary data', mode='wb')
        """
        return await asyncify(self._node.write)(data, mode, encoding, skip_if_unchanged)

    async def delete(self) -> None:
        """Delete file or directory (async).

        Example:
            >>> await node.delete()
        """
        await asyncify(self._node.delete)()

    async def copy_to(self, target: AsyncStorageNode | StorageNode, **kwargs) -> None:
        """Copy file to target location (async).

        Args:
            target: Target node (can be async or sync)
            **kwargs: Additional arguments for copy

        Example:
            >>> target = storage.node('s3:backup/file.txt')
            >>> await node.copy_to(target)
        """
        target_node = target._node if isinstance(target, AsyncStorageNode) else target
        await asyncify(self._node.copy_to)(target_node, **kwargs)

    async def move_to(self, target: AsyncStorageNode | StorageNode) -> None:
        """Move file to target location (async).

        Args:
            target: Target node (can be async or sync)

        Example:
            >>> target = storage.node('s3:archive/file.txt')
            >>> await node.move_to(target)
        """
        target_node = target._node if isinstance(target, AsyncStorageNode) else target
        await asyncify(self._node.move_to)(target_node)

    # Async property access (requires I/O)

    async def exists(self) -> bool:
        """Check if file exists (async).

        Returns:
            bool: True if file exists

        Example:
            >>> if await node.exists():
            ...     print("File exists")
        """
        return await asyncify(lambda: self._node.exists)()

    async def size(self) -> int:
        """Get file size in bytes (async).

        Returns:
            int: File size in bytes

        Example:
            >>> size = await node.size()
            >>> print(f"File is {size} bytes")
        """
        return await asyncify(lambda: self._node.size)()

    async def mtime(self) -> float:
        """Get last modification time (async).

        Returns:
            float: Unix timestamp of last modification

        Example:
            >>> mtime = await node.mtime()
        """
        return await asyncify(lambda: self._node.mtime)()

    async def isfile(self) -> bool:
        """Check if node is a file (async).

        Returns:
            bool: True if node is a file
        """
        return await asyncify(lambda: self._node.isfile)()

    async def isdir(self) -> bool:
        """Check if node is a directory (async).

        Returns:
            bool: True if node is a directory
        """
        return await asyncify(lambda: self._node.isdir)()

    # Sync properties (no I/O required)

    @property
    def path(self) -> str:
        """Get relative path within mount (synchronous).

        Returns:
            str: Path within mount point
        """
        return self._node.path

    @property
    def fullpath(self) -> str:
        """Get full path including mount (synchronous).

        Returns:
            str: Full path (e.g., "s3:path/to/file")
        """
        return self._node.fullpath

    @property
    def basename(self) -> str:
        """Get filename with extension (synchronous).

        Returns:
            str: Filename
        """
        return self._node.basename

    @property
    def stem(self) -> str:
        """Get filename without extension (synchronous).

        Returns:
            str: Filename stem
        """
        return self._node.stem

    @property
    def suffix(self) -> str:
        """Get file extension including dot (synchronous).

        Returns:
            str: File extension (e.g., ".txt")
        """
        return self._node.suffix

    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"AsyncStorageNode({self._node.fullpath!r})"

    def __str__(self) -> str:
        """String representation."""
        return self._node.fullpath
