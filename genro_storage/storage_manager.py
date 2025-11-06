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

"""StorageManager - Sync wrapper around AsyncStorageManager.

This provides a synchronous API by wrapping async operations with asyncio.run().
"""

from __future__ import annotations

import asyncio
from typing import Any

from .async_storage_manager import AsyncStorageManager
from .storage_node import StorageNode


class StorageManager:
    """Sync wrapper for AsyncStorageManager.

    Provides synchronous API by wrapping all async operations with asyncio.run().

    Examples:
        >>> # Create manager
        >>> storage = StorageManager()
        >>>
        >>> # Configure mount points
        >>> storage.configure([
        ...     {
        ...         'name': 'uploads',
        ...         'protocol': 's3_aws',
        ...         'bucket': 'my-bucket',
        ...         'region': 'us-east-1',
        ...         'base_path': 'production/uploads'
        ...     },
        ...     {
        ...         'name': 'local',
        ...         'protocol': 'local',
        ...         'root_path': '/home/user/storage'
        ...     }
        ... ])
        >>>
        >>> # Create nodes
        >>> node = storage.node('uploads:documents/file.txt')
        >>> node.write(b'Hello World')
    """

    def __init__(self):
        """Initialize StorageManager with async backend."""
        self._async_manager = AsyncStorageManager()

    def configure(self, mounts: list[dict[str, Any]]) -> None:
        """Configure mount points (sync wrapper).

        Args:
            mounts: List of mount point configurations

        Raises:
            ValueError: If protocol not found or configuration invalid
            ValidationError: If Pydantic validation fails
        """
        asyncio.run(self._async_manager.configure(mounts))

    def node(
        self,
        path: str,
        must_exist: bool | None = None,
        autocreate_parents: bool = True,
        cached: bool = False
    ) -> StorageNode:
        """Create a StorageNode for the given path (sync wrapper).

        Args:
            path: Full path with mount point (e.g., 'uploads:documents/file.txt')
            must_exist: If True, operations check file existence
            autocreate_parents: If True, write operations create parent dirs
            cached: If True, node properties are cached

        Returns:
            StorageNode instance

        Raises:
            ValueError: If path format is invalid or mount point not found
        """
        # Create async node
        async_node = self._async_manager.node(
            path,
            must_exist=must_exist,
            autocreate_parents=autocreate_parents,
            cached=cached
        )

        # Wrap in sync node
        return StorageNode(async_node)

    def get_mount_info(self, mount_point: str) -> dict[str, Any]:
        """Get information about a mount point.

        Args:
            mount_point: Mount point name

        Returns:
            Dictionary with mount point information

        Raises:
            ValueError: If mount point not found
        """
        return self._async_manager.get_mount_info(mount_point)

    def list_mounts(self) -> list[str]:
        """List all configured mount points.

        Returns:
            List of mount point names
        """
        return self._async_manager.list_mounts()

    def has_mount(self, mount_point: str) -> bool:
        """Check if mount point is configured.

        Args:
            mount_point: Mount point name

        Returns:
            True if mount point exists
        """
        return self._async_manager.has_mount(mount_point)

    def remove_mount(self, mount_point: str) -> None:
        """Remove a mount point (sync wrapper).

        Args:
            mount_point: Mount point name to remove

        Raises:
            ValueError: If mount point not found
        """
        asyncio.run(self._async_manager.remove_mount(mount_point))

    def close_all(self) -> None:
        """Close all mount points and release resources (sync wrapper)."""
        asyncio.run(self._async_manager.close_all())

    def __repr__(self) -> str:
        """String representation."""
        return repr(self._async_manager)
