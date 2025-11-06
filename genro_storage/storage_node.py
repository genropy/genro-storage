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

"""StorageNode - Sync wrapper around AsyncStorageNode.

This provides a synchronous API by wrapping async operations with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .async_storage_node import AsyncStorageNode


class StorageNode:
    """Sync wrapper for AsyncStorageNode.

    Provides synchronous API by wrapping all async operations with asyncio.run().

    Examples:
        >>> node = storage.node('uploads:documents/report.pdf')
        >>>
        >>> # Properties
        >>> if node.exists:
        ...     print(f"Size: {node.size} bytes")
        ...     print(f"Modified: {node.mtime}")
        >>>
        >>> # Read operations
        >>> content = node.read()
        >>> text = node.read_text()
        >>>
        >>> # Write operations
        >>> node.write(b'data')
        >>> node.write_text('Hello World')
        >>>
        >>> # Copy
        >>> dest = storage.node('backups:report.pdf')
        >>> node.copy(dest)
    """

    def __init__(self, async_node: AsyncStorageNode):
        """Initialize StorageNode with async backend.

        Args:
            async_node: AsyncStorageNode instance to wrap
        """
        self._async_node = async_node

    # Forward simple attributes
    @property
    def manager(self):
        return self._async_node.manager

    @property
    def mount_point(self) -> str:
        return self._async_node.mount_point

    @property
    def path(self) -> str:
        return self._async_node.path

    @property
    def full_path(self) -> str:
        return self._async_node.full_path

    @property
    def must_exist(self) -> bool | None:
        return self._async_node.must_exist

    @property
    def autocreate_parents(self) -> bool:
        return self._async_node.autocreate_parents

    # PROPERTIES - States (sync wrappers with asyncio.run)

    @property
    def exists(self) -> bool:
        """Check if file or directory exists."""
        return asyncio.run(self._async_node.exists)

    @property
    def is_file(self) -> bool:
        """Check if path is a file."""
        return asyncio.run(self._async_node.is_file)

    @property
    def is_dir(self) -> bool:
        """Check if path is a directory."""
        return asyncio.run(self._async_node.is_dir)

    @property
    def size(self) -> int:
        """Get file size in bytes."""
        return asyncio.run(self._async_node.size)

    @property
    def mtime(self) -> float:
        """Get last modification time as Unix timestamp."""
        return asyncio.run(self._async_node.mtime)

    # Path utilities (direct passthrough - no async)

    @property
    def basename(self) -> str:
        """Filename with extension (e.g., 'file.txt')."""
        return self._async_node.basename

    @property
    def stem(self) -> str:
        """Filename without extension (e.g., 'file')."""
        return self._async_node.stem

    @property
    def suffix(self) -> str:
        """File extension including dot (e.g., '.txt')."""
        return self._async_node.suffix

    @property
    def parent(self) -> StorageNode:
        """Parent directory as StorageNode."""
        async_parent = self._async_node.parent
        return StorageNode(async_parent)

    # METHODS - Actions (sync wrappers with asyncio.run)

    def read(self) -> bytes:
        """Read entire file as bytes.

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        return asyncio.run(self._async_node.read())

    def read_text(self, encoding: str = 'utf-8') -> str:
        """Read entire file as text.

        Args:
            encoding: Text encoding (default: utf-8)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        return asyncio.run(self._async_node.read_text(encoding))

    def write(self, data: bytes, parents: bool = True) -> None:
        """Write bytes to file.

        Args:
            data: Bytes to write
            parents: If True, create parent directories (default: True)
        """
        asyncio.run(self._async_node.write(data, parents))

    def write_text(self, text: str, encoding: str = 'utf-8', parents: bool = True) -> None:
        """Write text to file.

        Args:
            text: Text to write
            encoding: Text encoding (default: utf-8)
            parents: If True, create parent directories (default: True)
        """
        asyncio.run(self._async_node.write_text(text, encoding, parents))

    def delete(self, recursive: bool = False) -> None:
        """Delete file or directory.

        Args:
            recursive: If True, delete directories recursively

        Raises:
            FileNotFoundError: If file doesn't exist (if must_exist=True)
        """
        asyncio.run(self._async_node.delete(recursive))

    def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory.

        Args:
            parents: If True, create parent directories
            exist_ok: If True, don't error if directory exists
        """
        asyncio.run(self._async_node.mkdir(parents, exist_ok))

    def copy(self, dest: StorageNode) -> None:
        """Copy file to another node.

        Args:
            dest: Destination StorageNode
        """
        asyncio.run(self._async_node.copy(dest._async_node))

    def list(self) -> list[StorageNode]:
        """List directory contents as StorageNodes.

        Returns:
            List of StorageNode objects for directory contents

        Raises:
            NotADirectoryError: If path is not a directory
        """
        async_nodes = asyncio.run(self._async_node.list())
        return [StorageNode(node) for node in async_nodes]

    def local_path(self, mode: str = 'r'):
        """Get context manager for local filesystem path.

        For local storage: returns direct path
        For remote storage: downloads to temp, uploads on exit

        Args:
            mode: Access mode ('r', 'w', 'rw')

        Returns:
            Context manager yielding local path

        Examples:
            >>> with node.local_path(mode='r') as local:
            ...     subprocess.run(['ffmpeg', '-i', local, 'output.mp4'])
        """
        # Return a sync wrapper context manager
        return SyncLocalPathContext(self._async_node, mode)

    # Advanced features

    def get_hash(self) -> str | None:
        """Get MD5 hash from metadata if available.

        Returns:
            MD5 hash string, or None if not available
        """
        return asyncio.run(self._async_node.get_hash())

    def get_metadata(self) -> dict[str, str]:
        """Get custom metadata.

        Returns:
            Dictionary of metadata key-value pairs
        """
        return asyncio.run(self._async_node.get_metadata())

    def set_metadata(self, metadata: dict[str, str]) -> None:
        """Set custom metadata.

        Args:
            metadata: Dictionary of metadata to set
        """
        asyncio.run(self._async_node.set_metadata(metadata))

    # Cache management

    def invalidate_cache(self) -> None:
        """Invalidate all cached property values."""
        self._async_node.invalidate_cache()

    def refresh(self) -> None:
        """Alias for invalidate_cache (more user-friendly)."""
        self._async_node.refresh()

    def __repr__(self) -> str:
        """String representation."""
        return repr(self._async_node)

    def __str__(self) -> str:
        """String representation."""
        return str(self._async_node)


class SyncLocalPathContext:
    """Sync wrapper for async local_path context manager."""

    def __init__(self, async_node: AsyncStorageNode, mode: str):
        self._async_node = async_node
        self._mode = mode
        self._async_context = None
        self._local_path = None

    def __enter__(self) -> str:
        """Enter context synchronously."""
        # Get async context manager
        async def _enter():
            self._async_context = await self._async_node.local_path(self._mode)
            return await self._async_context.__aenter__()

        self._local_path = asyncio.run(_enter())
        return self._local_path

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context synchronously."""
        async def _exit():
            await self._async_context.__aexit__(exc_type, exc_val, exc_tb)

        asyncio.run(_exit())
        return False
