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

"""Base classes for async provider system.

This module defines:
- AsyncProvider: Factory class that registers protocols via @protocol decorator
- AsyncImplementor: Async adapter class that implements the storage API
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncIterator, Type, Callable
from pydantic import BaseModel

if TYPE_CHECKING:
    from ..capabilities import BackendCapabilities


class AsyncProvider(ABC):
    """Base class for async storage providers.

    A Provider is a factory that:
    1. Defines available protocols via @protocol decorator
    2. Returns (Model, Implementor, capabilities) for each protocol
    3. Auto-registers protocols in the global registry

    Example:
        >>> class FsspecProvider(AsyncProvider):
        ...     @protocol('s3_aws')
        ...     def protocol_s3_aws(self):
        ...         class Model(BaseModel):
        ...             bucket: str
        ...             region: str
        ...
        ...         class Implementor(AsyncFsspecImplementor):
        ...             def __init__(self, config: Model):
        ...                 super().__init__(config)
        ...
        ...         return {
        ...             'model': Model,
        ...             'implementor': Implementor,
        ...             'capabilities': ['read', 'write', 'metadata']
        ...         }
    """

    _protocols: dict[str, Callable] = {}

    @classmethod
    def protocol(cls, name: str) -> Callable:
        """Decorator to register a protocol.

        Args:
            name: Protocol name (e.g., 's3_aws', 's3_minio', 'gcs')

        Returns:
            Decorator function

        Example:
            >>> @protocol('s3_aws')
            ... def protocol_s3_aws(self):
            ...     # Return model, implementor, capabilities
            ...     pass
        """

        def decorator(func: Callable) -> Callable:
            # Store protocol method
            if not hasattr(cls, "_protocols"):
                cls._protocols = {}
            cls._protocols[name] = func

            # Auto-register in global registry when decorated
            from .registry import ProviderRegistry

            ProviderRegistry.register(name, cls, func)

            return func

        return decorator

    @classmethod
    def get_protocol(cls, name: str) -> dict[str, Any]:
        """Get protocol configuration.

        Args:
            name: Protocol name

        Returns:
            dict: Dictionary with 'model', 'implementor', 'capabilities'

        Raises:
            ValueError: If protocol not found
        """
        if name not in cls._protocols:
            raise ValueError(
                f"Protocol '{name}' not found in {cls.__name__}. "
                f"Available: {list(cls._protocols.keys())}"
            )

        # Call protocol method to get config
        instance = cls()
        protocol_method = cls._protocols[name]
        return protocol_method(instance)

    @classmethod
    def list_protocols(cls) -> list[str]:
        """List all available protocols.

        Returns:
            list[str]: Protocol names
        """
        return list(cls._protocols.keys())


class AsyncImplementor(ABC):
    """Base class for async storage implementors.

    An AsyncImplementor is an adapter that:
    1. Receives validated configuration (Pydantic model)
    2. Creates/manages the underlying async provider client (fsspec async, aioboto3, etc.)
    3. Implements the async storage API methods
    4. Translates between our API and provider API

    All methods are async coroutines for true concurrent I/O.

    Example:
        >>> class AsyncFsspecImplementor(AsyncImplementor):
        ...     def __init__(self, config: BaseModel):
        ...         self.config = config
        ...         self.fs = fsspec.filesystem('s3', asynchronous=True, **config.dict())
        ...
        ...     async def read_bytes(self, path: str) -> bytes:
        ...         return await self.fs._cat(path)
    """

    def __init__(self, config: BaseModel) -> None:
        """Initialize implementor with validated configuration.

        Args:
            config: Pydantic model instance with validated configuration
        """
        self.config = config

    # Core file operations (all async)

    @abstractmethod
    async def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        pass

    @abstractmethod
    async def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        pass

    @abstractmethod
    async def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        pass

    @abstractmethod
    async def size(self, path: str) -> int:
        """Get file size in bytes."""
        pass

    @abstractmethod
    async def mtime(self, path: str) -> float:
        """Get last modification time."""
        pass

    @abstractmethod
    async def read_bytes(self, path: str) -> bytes:
        """Read entire file as bytes."""
        pass

    @abstractmethod
    async def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read entire file as text."""
        pass

    @abstractmethod
    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        pass

    @abstractmethod
    async def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        pass

    @abstractmethod
    async def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        pass

    @abstractmethod
    async def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        pass

    @abstractmethod
    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        pass

    @abstractmethod
    async def copy(
        self, src_path: str, dest_implementor: "AsyncImplementor", dest_path: str
    ) -> str | None:
        """Copy file to another implementor."""
        pass

    # Async iteration support

    async def open_read(self, path: str) -> AsyncIterator[bytes]:
        """Open file for streaming read.

        Yields:
            bytes: Chunks of file data

        Example:
            >>> async for chunk in implementor.open_read('file.txt'):
            ...     process(chunk)
        """
        data = await self.read_bytes(path)
        yield data

    async def open_write(self, path: str) -> "AsyncFileWriter":
        """Open file for streaming write.

        Returns:
            AsyncFileWriter: Context manager for writing

        Example:
            >>> async with implementor.open_write('file.txt') as writer:
            ...     await writer.write(b'data')
        """
        raise NotImplementedError(f"{self.__class__.__name__} does not support streaming write")

    # Optional advanced features

    async def get_hash(self, path: str) -> str | None:
        """Get MD5 hash from metadata if available.

        Default: Returns None (must compute manually)
        """
        return None

    async def get_metadata(self, path: str) -> dict[str, str]:
        """Get custom metadata for file.

        Default: Returns empty dict (no metadata support)
        """
        return {}

    async def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set custom metadata for file.

        Default: Raises PermissionError (no metadata support)
        """
        raise PermissionError(f"{self.__class__.__name__} does not support metadata operations")

    async def get_versions(self, path: str) -> list[dict]:
        """Get list of file versions.

        Default: Returns empty list (no versioning)
        """
        return []

    async def read_version(self, path: str, version_id: str) -> bytes:
        """Read specific version of file.

        Default: Raises PermissionError (no versioning)
        """
        raise PermissionError(f"{self.__class__.__name__} does not support versioning")

    async def delete_version(self, path: str, version_id: str) -> None:
        """Delete specific version of file.

        Default: Raises PermissionError (no versioning)
        """
        raise PermissionError(f"{self.__class__.__name__} does not support version deletion")

    async def url(self, path: str, expires_in: int = 3600, **kwargs) -> str | None:
        """Generate public URL for file.

        Default: Returns None (no URL generation)
        """
        return None

    async def internal_url(self, path: str, nocache: bool = False) -> str | None:
        """Generate internal URL for file.

        Default: Returns None (no internal URL)
        """
        return None

    def local_path(self, path: str, mode: str = "r"):
        """Get async context manager for local filesystem path.

        For local storage: returns direct path
        For remote storage: downloads to temp, uploads on exit

        Default: Raises NotImplementedError (must override)
        """
        raise NotImplementedError(f"{self.__class__.__name__} must implement local_path")

    async def close(self) -> None:
        """Close resources.

        Default: Does nothing
        """
        pass
