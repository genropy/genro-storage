# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0

"""AsyncStorageManager - Async storage manager with SmartSwitch dispatch.

This is the skeleton implementation with:
- SmartSwitch for method dispatch
- ProviderRegistry integration
- Methods with pass (no real implementation yet)
- Logging via SmartSwitch
"""

from __future__ import annotations
from typing import Any
from smartswitch import Switcher

from ..providers.registry import ProviderRegistry


class AsyncStorageManager:
    """Async storage manager with SmartSwitch dispatch.

    Skeleton implementation that:
    1. Initializes ProviderRegistry (auto-loads providers)
    2. Uses SmartSwitch for method dispatch
    3. Methods do nothing (pass) but log via SmartSwitch

    Examples:
        >>> storage = AsyncStorageManager()
        >>> # Enable logging to see dispatch
        >>> storage.api.enable_log(mode='log')
        >>>
        >>> # Configure (does nothing, just logs)
        >>> await storage.api('configure')([{'name': 'test', 'protocol': 's3'}])
        >>>
        >>> # List available protocols
        >>> protocols = storage.list_protocols()
    """

    # SmartSwitch for method dispatch
    api = Switcher(name='storage', prefix='storage_')

    def __init__(self):
        """Initialize storage manager and provider registry.

        - Creates ProviderRegistry instance
        - Auto-loads all providers from providers/ folder
        - Each provider registers its protocols
        """
        self.provider_registry = ProviderRegistry()
        self._mounts: dict[str, dict[str, Any]] = {}

    @api
    async def storage_configure(self, mounts: list[dict[str, Any]]) -> None:
        """Configure mount points (skeleton - just pass).

        Args:
            mounts: List of mount configurations with:
                - name: Mount point name
                - protocol: Protocol name (e.g., 's3_aws', 'local')
                - ... protocol-specific config

        Note:
            This is a skeleton method - does nothing except logging.
        """
        # Skeleton: solo pass, SmartSwitch logga la chiamata
        pass

    @api
    async def storage_node(self, path: str) -> Any:
        """Get storage node for path (skeleton - just pass).

        Args:
            path: Path with mount point prefix (e.g., 'uploads:file.txt')

        Returns:
            None (skeleton method)

        Note:
            This is a skeleton method - does nothing except logging.
        """
        # Skeleton: solo pass
        pass

    @api
    async def storage_list_mounts(self) -> list[str]:
        """List configured mount points (skeleton - just pass).

        Returns:
            Empty list (skeleton method)

        Note:
            This is a skeleton method - does nothing except logging.
        """
        # Skeleton: solo pass
        pass

    # Non-API method: utility per vedere protocolli disponibili
    def list_protocols(self) -> list[str]:
        """List all available protocols from registry.

        This is NOT an API method (no @api decorator).
        Direct call to ProviderRegistry.

        Returns:
            list[str]: All available protocol names
        """
        return self.provider_registry.list_protocols()

    def get_protocol(self, protocol_name: str) -> dict[str, Any]:
        """Get protocol configuration from registry.

        This is NOT an API method (no @api decorator).
        Direct call to ProviderRegistry.

        Args:
            protocol_name: Protocol name (e.g., 's3_aws', 'local')

        Returns:
            dict: Protocol configuration with model, implementor, capabilities

        Raises:
            ValueError: If protocol not found
        """
        return self.provider_registry.get_protocol(protocol_name)
