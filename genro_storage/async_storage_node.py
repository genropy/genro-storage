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

"""AsyncStorageNode - Async implementation with provider architecture.

This is the async implementation using the provider system.
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from pathlib import PurePosixPath

from .node_decorators import cacheable_property, resolved

if TYPE_CHECKING:
    from .async_storage_manager import AsyncStorageManager
    from .providers.base import AsyncImplementor


class AsyncStorageNode:
    """Represents a file or directory in async storage.

    AsyncStorageNode provides unified async interface for file operations across
    different storage backends (local, S3, GCS, Azure, etc.).

    Architecture:
    - Eager resolution: implementor and full_path set in __init__
    - Cacheable properties: exists, size, mtime (conditional caching)
    - Resolved decorator: handles must_exist and autocreate_parents
    - All operations are async coroutines

    Args:
        manager: AsyncStorageManager instance
        mount_point: Mount point name (e.g., 'uploads')
        path: Relative path (e.g., 'documents/file.txt')
        must_exist: If True, methods check file existence
        autocreate_parents: If True, write() creates parent dirs
        cached: If True, property values are cached

    Examples:
        >>> node = storage.node('uploads:documents/report.pdf')
        >>>
        >>> # Properties (with optional caching)
        >>> if await node.exists:
        ...     print(f"Size: {await node.size} bytes")
        ...     print(f"Modified: {await node.mtime}")
        >>>
        >>> # Read operations
        >>> content = await node.read()
        >>> text = await node.read_text()
        >>>
        >>> # Write operations (auto-creates parents by default)
        >>> await node.write(b'data')
        >>> await node.write_text('Hello World')
        >>>
        >>> # Copy
        >>> dest = storage.node('backups:report.pdf')
        >>> await node.copy(dest)
    """

    def __init__(
        self,
        manager: AsyncStorageManager,
        mount_point: str,
        path: str,
        must_exist: bool | None = None,
        autocreate_parents: bool = True,
        cached: bool = False
    ):
        """Initialize AsyncStorageNode with eager resolution."""
        self.manager = manager
        self.mount_point = mount_point
        self.path = path

        # Configuration
        self.must_exist = must_exist
        self.autocreate_parents = autocreate_parents
        self._cached = cached

        # Eager resolution (cheap: dict lookup + string concat)
        mount_info = manager._mounts[mount_point]
        self.implementor: AsyncImplementor = mount_info['implementor']
        base_path = mount_info.get('base_path', '')

        # Calculate full_path (what we pass to implementor)
        if base_path:
            self.full_path = f"{base_path}/{path}".strip('/')
        else:
            self.full_path = path

    # PROPERTIES - States (always fresh unless cached=True)

    @cacheable_property
    async def exists(self) -> bool:
        """Check if file or directory exists."""
        return await self.implementor.exists(self.full_path)

    @cacheable_property
    async def is_file(self) -> bool:
        """Check if path is a file."""
        return await self.implementor.is_file(self.full_path)

    @cacheable_property
    async def is_dir(self) -> bool:
        """Check if path is a directory."""
        return await self.implementor.is_dir(self.full_path)

    @cacheable_property
    async def size(self) -> int:
        """Get file size in bytes."""
        return await self.implementor.size(self.full_path)

    @cacheable_property
    async def mtime(self) -> float:
        """Get last modification time as Unix timestamp."""
        return await self.implementor.mtime(self.full_path)

    # Path utilities (always computed, never cached)

    @property
    def basename(self) -> str:
        """Filename with extension (e.g., 'file.txt')."""
        return PurePosixPath(self.path).name

    @property
    def stem(self) -> str:
        """Filename without extension (e.g., 'file')."""
        return PurePosixPath(self.path).stem

    @property
    def suffix(self) -> str:
        """File extension including dot (e.g., '.txt')."""
        return PurePosixPath(self.path).suffix

    @property
    def parent(self) -> AsyncStorageNode:
        """Parent directory as AsyncStorageNode."""
        parent_path = str(PurePosixPath(self.path).parent)
        if parent_path == '.':
            parent_path = ''
        return AsyncStorageNode(
            self.manager,
            self.mount_point,
            parent_path,
            must_exist=False,
            autocreate_parents=self.autocreate_parents,
            cached=self._cached
        )

    # METHODS - Actions (all async)

    @resolved()  # Auto must_exist for read
    async def read(self) -> bytes:
        """Read entire file as bytes.

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        return await self.implementor.read_bytes(self.full_path)

    @resolved()  # Auto must_exist for read
    async def read_text(self, encoding: str = 'utf-8') -> str:
        """Read entire file as text.

        Args:
            encoding: Text encoding (default: utf-8)

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        return await self.implementor.read_text(self.full_path, encoding=encoding)

    @resolved(autocreate_parents=True)
    async def write(self, data: bytes, parents: bool = True) -> None:
        """Write bytes to file.

        Args:
            data: Bytes to write
            parents: If True, create parent directories (default: True)

        Examples:
            >>> await node.write(b'Hello World')
            >>> await node.write(b'data', parents=False)  # Fail if parent missing
        """
        await self.implementor.write_bytes(self.full_path, data)
        self.invalidate_cache()

    @resolved(autocreate_parents=True)
    async def write_text(self, text: str, encoding: str = 'utf-8', parents: bool = True) -> None:
        """Write text to file.

        Args:
            text: Text to write
            encoding: Text encoding (default: utf-8)
            parents: If True, create parent directories (default: True)
        """
        await self.implementor.write_text(self.full_path, text, encoding=encoding)
        self.invalidate_cache()

    @resolved()  # Auto must_exist for delete
    async def delete(self, recursive: bool = False) -> None:
        """Delete file or directory.

        Args:
            recursive: If True, delete directories recursively

        Raises:
            FileNotFoundError: If file doesn't exist (if must_exist=True)
        """
        await self.implementor.delete(self.full_path, recursive=recursive)
        self.invalidate_cache()

    @resolved(must_exist=False)
    async def mkdir(self, parents: bool = True, exist_ok: bool = True) -> None:
        """Create directory.

        Args:
            parents: If True, create parent directories
            exist_ok: If True, don't error if directory exists
        """
        await self.implementor.mkdir(self.full_path, parents=parents, exist_ok=exist_ok)
        self.invalidate_cache()

    async def copy(self, dest: AsyncStorageNode) -> None:
        """Copy file to another node.

        Args:
            dest: Destination AsyncStorageNode

        Examples:
            >>> src = storage.node('uploads:file.txt')
            >>> dest = storage.node('backups:file.txt')
            >>> await src.copy(dest)
        """
        if not await self.exists:
            raise FileNotFoundError(f"Source file not found: {self.mount_point}:{self.path}")

        # Create dest parent if needed
        if dest.autocreate_parents:
            parent_path = dest._get_parent_path()
            if parent_path:
                await dest.implementor.mkdir(parent_path, parents=True, exist_ok=True)

        await self.implementor.copy(self.full_path, dest.implementor, dest.full_path)
        dest.invalidate_cache()

    async def list(self) -> list[AsyncStorageNode]:
        """List directory contents as AsyncStorageNodes.

        Returns:
            List of AsyncStorageNode objects for directory contents

        Raises:
            NotADirectoryError: If path is not a directory
        """
        if not await self.is_dir:
            raise NotADirectoryError(f"Not a directory: {self.mount_point}:{self.path}")

        names = await self.implementor.list_dir(self.full_path)

        nodes = []
        for name in names:
            child_path = f"{self.path}/{name}" if self.path else name
            nodes.append(
                AsyncStorageNode(
                    self.manager,
                    self.mount_point,
                    child_path,
                    must_exist=False,
                    autocreate_parents=self.autocreate_parents,
                    cached=self._cached
                )
            )

        return nodes

    async def local_path(self, mode: str = 'r'):
        """Get async context manager for local filesystem path.

        For local storage: returns direct path
        For remote storage: downloads to temp, uploads on exit

        Args:
            mode: Access mode ('r', 'w', 'rw')

        Returns:
            Async context manager yielding local path

        Examples:
            >>> async with node.local_path(mode='r') as local:
            ...     subprocess.run(['ffmpeg', '-i', local, 'output.mp4'])
        """
        return await self.implementor.local_path(self.full_path, mode=mode)

    # Advanced features

    async def get_hash(self) -> str | None:
        """Get MD5 hash from metadata if available.

        Returns:
            MD5 hash string, or None if not available
        """
        return await self.implementor.get_hash(self.full_path)

    async def get_metadata(self) -> dict[str, str]:
        """Get custom metadata.

        Returns:
            Dictionary of metadata key-value pairs
        """
        return await self.implementor.get_metadata(self.full_path)

    async def set_metadata(self, metadata: dict[str, str]) -> None:
        """Set custom metadata.

        Args:
            metadata: Dictionary of metadata to set
        """
        await self.implementor.set_metadata(self.full_path, metadata)

    # Cache management

    def invalidate_cache(self) -> None:
        """Invalidate all cached property values."""
        if self._cached:
            for attr in list(vars(self).keys()):
                if attr.startswith('_cache_'):
                    delattr(self, attr)

    def refresh(self) -> None:
        """Alias for invalidate_cache (more user-friendly)."""
        self.invalidate_cache()

    # Utilities

    def _get_parent_path(self) -> str:
        """Get parent path for this node's full_path."""
        parts = self.full_path.split('/')
        if len(parts) > 1:
            return '/'.join(parts[:-1])
        return ''

    def __repr__(self) -> str:
        """String representation."""
        return f"AsyncStorageNode('{self.mount_point}:{self.path}')"

    def __str__(self) -> str:
        """String representation."""
        return f"{self.mount_point}:{self.path}"
