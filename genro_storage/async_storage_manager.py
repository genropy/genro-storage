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

"""AsyncStorageManager - Async storage manager with provider architecture.

This is the async base implementation using the provider system.
"""

from __future__ import annotations

from typing import Any
from pydantic import ValidationError

from .async_storage_node import AsyncStorageNode
from .providers.registry import ProviderRegistry


class AsyncStorageManager:
    """Async manager for storage mount points and creates AsyncStorageNodes.

    AsyncStorageManager is the async entry point for genro-storage.
    It manages mount points (named storage backends) and creates
    AsyncStorageNode instances for file operations.

    Architecture:
    - Uses ProviderRegistry to get protocol configurations
    - Each mount point has: async_implementor + base_path
    - Passes full paths (base_path + relative) to async implementor

    Examples:
        >>> # Create async manager
        >>> storage = AsyncStorageManager()
        >>>
        >>> # Configure mount points
        >>> await storage.configure([
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
        >>> await node.write(b'Hello World')
    """

    def __init__(self):
        """Initialize AsyncStorageManager."""
        self._mounts: dict[str, dict[str, Any]] = {}

    async def configure(self, mounts: list[dict[str, Any]]) -> None:
        """Configure mount points.

        Args:
            mounts: List of mount point configurations. Each dict must have:
                - name: Mount point name (e.g., 'uploads')
                - protocol: Protocol name (e.g., 's3_aws', 'local')
                - base_path: Optional base path prefix (default: '')
                - ... other protocol-specific config fields

        Raises:
            ValueError: If protocol not found or configuration invalid
            ValidationError: If Pydantic validation fails

        Examples:
            >>> await storage.configure([
            ...     {
            ...         'name': 'uploads',
            ...         'protocol': 's3_aws',
            ...         'bucket': 'my-bucket',
            ...         'region': 'us-east-1',
            ...         'access_key': 'AKIA...',
            ...         'secret_key': 'secret',
            ...         'base_path': 'production/uploads'
            ...     }
            ... ])
        """
        for mount_config in mounts:
            name = mount_config.pop('name')
            protocol = mount_config.pop('protocol')
            base_path = mount_config.pop('base_path', '')

            # Get protocol configuration from registry
            try:
                protocol_config = ProviderRegistry.get_protocol(protocol)
            except ValueError as e:
                available = ProviderRegistry.list_protocols()
                raise ValueError(
                    f"Unknown protocol '{protocol}'. "
                    f"Available protocols: {available}"
                ) from e

            # Extract Model and Implementor classes
            Model = protocol_config['model']
            Implementor = protocol_config['implementor']
            capabilities = protocol_config['capabilities']

            # Validate configuration with Pydantic
            try:
                validated_config = Model(**mount_config)
            except ValidationError as e:
                raise ValidationError(
                    f"Invalid configuration for mount '{name}' (protocol: {protocol})",
                    e.errors()
                )

            # Create implementor instance
            implementor = Implementor(validated_config)

            # Store in mounts registry
            self._mounts[name] = {
                'implementor': implementor,
                'base_path': base_path,
                'protocol': protocol,
                'capabilities': capabilities,
                'config': validated_config
            }

    def node(
        self,
        path: str,
        must_exist: bool | None = None,
        autocreate_parents: bool = True,
        cached: bool = False
    ) -> AsyncStorageNode:
        """Create an AsyncStorageNode for the given path.

        Args:
            path: Full path with mount point (e.g., 'uploads:documents/file.txt')
            must_exist: If True, operations check file existence
            autocreate_parents: If True, write operations create parent dirs
            cached: If True, node properties are cached

        Returns:
            AsyncStorageNode instance

        Raises:
            ValueError: If path format is invalid or mount point not found

        Examples:
            >>> node = storage.node('uploads:documents/report.pdf')
            >>> node = storage.node('uploads:new/file.txt', autocreate_parents=True)
            >>> node = storage.node('uploads:file.txt', cached=True)
        """
        # Parse path
        if ':' not in path:
            raise ValueError(
                f"Invalid path format: '{path}'. "
                f"Expected format: 'mount_point:relative/path'"
            )

        mount_point, relative_path = path.split(':', 1)

        # Validate mount point exists
        if mount_point not in self._mounts:
            available = list(self._mounts.keys())
            raise ValueError(
                f"Unknown mount point '{mount_point}'. "
                f"Available mount points: {available}"
            )

        # Create and return node
        return AsyncStorageNode(
            manager=self,
            mount_point=mount_point,
            path=relative_path,
            must_exist=must_exist,
            autocreate_parents=autocreate_parents,
            cached=cached
        )

    def get_mount_info(self, mount_point: str) -> dict[str, Any]:
        """Get information about a mount point.

        Args:
            mount_point: Mount point name

        Returns:
            Dictionary with mount point information:
                - implementor: Async implementor instance
                - base_path: Base path prefix
                - protocol: Protocol name
                - capabilities: List of capabilities
                - config: Validated configuration

        Raises:
            ValueError: If mount point not found
        """
        if mount_point not in self._mounts:
            available = list(self._mounts.keys())
            raise ValueError(
                f"Unknown mount point '{mount_point}'. "
                f"Available: {available}"
            )

        return self._mounts[mount_point].copy()

    def list_mounts(self) -> list[str]:
        """List all configured mount points.

        Returns:
            List of mount point names
        """
        return list(self._mounts.keys())

    def has_mount(self, mount_point: str) -> bool:
        """Check if mount point is configured.

        Args:
            mount_point: Mount point name

        Returns:
            True if mount point exists
        """
        return mount_point in self._mounts

    async def remove_mount(self, mount_point: str) -> None:
        """Remove a mount point.

        Args:
            mount_point: Mount point name to remove

        Raises:
            ValueError: If mount point not found
        """
        if mount_point not in self._mounts:
            raise ValueError(f"Mount point '{mount_point}' not found")

        # Close implementor if it has close method
        mount_info = self._mounts[mount_point]
        implementor = mount_info['implementor']
        if hasattr(implementor, 'close'):
            await implementor.close()

        del self._mounts[mount_point]

    async def close_all(self) -> None:
        """Close all mount points and release resources."""
        for mount_point in list(self._mounts.keys()):
            await self.remove_mount(mount_point)

    def __repr__(self) -> str:
        """String representation."""
        mounts_str = ', '.join(f"'{m}'" for m in self._mounts.keys())
        return f"AsyncStorageManager(mounts=[{mounts_str}])"
