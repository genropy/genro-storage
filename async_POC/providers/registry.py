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

"""Global provider registry.

This module maintains a global registry of all available protocols
and their provider classes. Protocols are auto-registered when
decorated with @protocol decorator.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Type, Callable

if TYPE_CHECKING:
    from .base import AsyncProvider


class ProviderRegistry:
    """Global registry for storage providers and protocols.

    This class maintains a mapping of protocol names to their provider
    classes and protocol methods. Protocols are auto-registered when
    decorated with @Provider.protocol decorator.

    Example:
        >>> # Protocols are auto-registered via decorator
        >>> class FsspecProvider(AsyncProvider):
        ...     @protocol('s3_aws')
        ...     def protocol_s3_aws(self):
        ...         pass  # Auto-registered
        ...
        >>> # Later, retrieve protocol
        >>> config = ProviderRegistry.get_protocol('s3_aws')
        >>> Model = config['model']
        >>> instance = Model(bucket='my-bucket', region='us-east-1')
    """

    # Registry: protocol_name -> (AsyncProvider class, protocol method)
    _registry: dict[str, tuple[Type[AsyncProvider], Callable]] = {}

    @classmethod
    def register(
        cls, protocol_name: str, provider_class: Type[AsyncProvider], protocol_method: Callable
    ) -> None:
        """Register a protocol (called automatically by @protocol decorator).

        Args:
            protocol_name: Protocol name (e.g., 's3_aws')
            provider_class: Provider class
            protocol_method: Protocol method that returns config dict
        """
        cls._registry[protocol_name] = (provider_class, protocol_method)

    @classmethod
    def get_protocol(cls, protocol_name: str) -> dict[str, Any]:
        """Get protocol configuration.

        Args:
            protocol_name: Protocol name

        Returns:
            dict: Dictionary with 'model', 'implementor', 'capabilities'

        Raises:
            ValueError: If protocol not registered

        Example:
            >>> config = ProviderRegistry.get_protocol('s3_aws')
            >>> Model = config['model']
            >>> Implementor = config['implementor']
            >>> capabilities = config['capabilities']
        """
        if protocol_name not in cls._registry:
            available = list(cls._registry.keys())
            raise ValueError(
                f"Protocol '{protocol_name}' not found. " f"Available protocols: {available}"
            )

        provider_class, protocol_method = cls._registry[protocol_name]

        # Create provider instance and call protocol method
        provider_instance = provider_class()
        return protocol_method(provider_instance)

    @classmethod
    def list_protocols(cls) -> list[str]:
        """List all registered protocols.

        Returns:
            list[str]: Protocol names
        """
        return list(cls._registry.keys())

    @classmethod
    def list_providers(cls) -> dict[str, list[str]]:
        """List all providers and their protocols.

        Returns:
            dict: Provider name -> list of protocol names
        """
        result: dict[str, list[str]] = {}

        for protocol_name, (provider_class, _) in cls._registry.items():
            provider_name = provider_class.__name__
            if provider_name not in result:
                result[provider_name] = []
            result[provider_name].append(protocol_name)

        return result

    @classmethod
    def clear(cls) -> None:
        """Clear registry (useful for testing)."""
        cls._registry.clear()
