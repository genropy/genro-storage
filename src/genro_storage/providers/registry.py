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

"""Global provider registry using smartswitch.

This module manages loading and registration of storage providers.
Each provider module must have a `Provider` class with protocol methods
decorated with its own `proto` switcher.

Architecture:
    - ProviderRegistry: Loads provider modules, instantiates Provider classes
    - Provider classes: Have `proto = Switcher(prefix='protocol_')` as class attribute
    - Protocol methods: Decorated with @proto, auto-registered with naming convention
"""

from __future__ import annotations

import importlib
import pkgutil
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


class ProviderRegistry:
    """Registry that loads and manages storage providers.

    At initialization, scans the providers/ directory, imports each module,
    and instantiates its `Provider` class. Each provider registers its
    protocols using smartswitch.

    Example:
        >>> registry = ProviderRegistry()
        >>> # Auto-loaded providers: fsspec, custom, etc.
        >>>
        >>> # Get fsspec provider
        >>> fsspec = registry.providers['fsspec']
        >>>
        >>> # List protocols from fsspec
        >>> protocols = fsspec.proto.list()
        >>>
        >>> # Call a protocol
        >>> config = fsspec.proto('s3_aws')
    """

    def __init__(self):
        """Initialize registry and load all providers."""
        self.providers = {}  # module_name -> Provider instance
        self.load_providers()

    def load_providers(self) -> None:
        """Scan providers/ directory and load all provider modules.

        For each .py file (except __init__.py, base.py, registry.py):
        1. Import the module
        2. Get the `Provider` class
        3. Instantiate it
        4. Add to self.providers
        """
        # Get path to providers directory
        providers_dir = Path(__file__).parent

        # Scan for .py files
        for module_info in pkgutil.iter_modules([str(providers_dir)]):
            module_name = module_info.name

            # Skip special files
            if module_name in ('__init__', 'base', 'registry'):
                continue

            try:
                # Import module
                module = importlib.import_module(f'.{module_name}', package='genro_storage.providers')

                # Get Provider class
                if not hasattr(module, 'Provider'):
                    continue  # Skip if no Provider class

                provider_class = getattr(module, 'Provider')

                # Instantiate and add
                provider_instance = provider_class()
                self.add_provider(module_name, provider_instance)

            except Exception as e:
                # Log error but continue loading other providers
                import warnings
                warnings.warn(f"Failed to load provider '{module_name}': {e}")
                continue

    def add_provider(self, name: str, provider_instance: Any) -> None:
        """Add a provider to the registry.

        Args:
            name: Provider name (usually module name)
            provider_instance: Instantiated Provider class
        """
        self.providers[name] = provider_instance

    def del_provider(self, name: str) -> None:
        """Remove a provider from the registry.

        Args:
            name: Provider name to remove
        """
        if name in self.providers:
            del self.providers[name]

    def get_protocol(self, protocol_name: str) -> dict[str, Any]:
        """Get protocol configuration by searching all providers.

        Args:
            protocol_name: Protocol name (e.g., 's3_aws', 'gcs')

        Returns:
            dict: Protocol configuration with 'model', 'implementor', etc.

        Raises:
            ValueError: If protocol not found in any provider
        """
        # Try each provider's proto switcher
        for provider_name, provider in self.providers.items():
            if hasattr(provider, 'proto'):
                try:
                    return provider.proto(protocol_name)
                except:
                    continue  # Try next provider

        # Not found in any provider
        available = self.list_protocols()
        raise ValueError(
            f"Protocol '{protocol_name}' not found. "
            f"Available protocols: {available}"
        )

    def list_protocols(self) -> list[str]:
        """List all available protocols from all providers.

        Returns:
            list[str]: All protocol names across all providers
        """
        protocols = []
        for provider in self.providers.values():
            if hasattr(provider, 'proto') and hasattr(provider.proto, '_spells'):
                protocols.extend(provider.proto._spells.keys())
        return sorted(set(protocols))

    def clear(self) -> None:
        """Clear all providers (useful for testing)."""
        self.providers.clear()
