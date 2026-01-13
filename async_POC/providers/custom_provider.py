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

"""Async custom provider for non-fsspec backends.

This module provides async custom storage backends that don't use fsspec:
- base64: Inline base64-encoded data
- (future) cache: Caching layer wrapper
- (future) encrypted: Encrypted storage wrapper
"""

from __future__ import annotations

import base64
from typing import Any
from pydantic import BaseModel

from .base import AsyncProvider, AsyncImplementor


class CustomProvider(AsyncProvider):
    """Async provider for custom (non-fsspec) backends.

    This provider hosts backends with custom logic that don't
    fit the standard filesystem abstraction:
    - base64: Data embedded in path as base64
    - Future: cache, encrypted, etc.
    """

    @AsyncProvider.protocol("base64")
    def protocol_base64(self) -> dict[str, Any]:
        """Base64 inline encoding backend.

        This backend encodes data directly in the path using base64.
        The path itself IS the data.

        Special behavior:
        - write() returns new path with encoded data
        - No directories or listing
        - Useful for embedding data in URLs/configs

        Example:
            >>> node = storage.node('b64:')
            >>> new_path = await node.write(b'Hello World')
            >>> # new_path is 'b64:SGVsbG8gV29ybGQ='
            >>> decoded = await storage.node(new_path).read()
            >>> # decoded is b'Hello World'
        """

        class Base64Model(BaseModel):
            """Configuration for base64 backend."""

            # Base64 has no configuration, just needs to exist
            pass

        class Base64Implementor(AsyncImplementor):
            """Async implementor for base64 inline encoding.

            Unlike filesystem backends, base64 stores data IN the path.
            Path format: 'encoded_data' where encoded_data is base64.

            Special notes:
            - exists() checks if path contains valid base64
            - write() modifies the path (returns new encoded path)
            - No directory operations
            """

            def __init__(self, config: Base64Model):
                super().__init__(config)

            def _decode_path(self, path: str) -> bytes:
                """Decode base64 path to bytes.

                Args:
                    path: Base64 encoded string

                Returns:
                    Decoded bytes

                Raises:
                    ValueError: If path is not valid base64
                """
                if not path:
                    return b""

                try:
                    return base64.b64decode(path, validate=True)
                except Exception as e:
                    raise ValueError(f"Invalid base64 path: {path}") from e

            def _encode_data(self, data: bytes) -> str:
                """Encode bytes to base64 path.

                Args:
                    data: Bytes to encode

                Returns:
                    Base64 encoded string
                """
                return base64.b64encode(data).decode("ascii")

            # Core async operations

            async def exists(self, path: str) -> bool:
                """Check if path contains valid base64 data."""
                if not path:
                    return False

                try:
                    self._decode_path(path)
                    return True
                except ValueError:
                    return False

            async def is_file(self, path: str) -> bool:
                """Base64 paths are always files (if valid)."""
                return await self.exists(path)

            async def is_dir(self, path: str) -> bool:
                """Base64 has no directories."""
                return False

            async def size(self, path: str) -> int:
                """Get decoded data size."""
                data = self._decode_path(path)
                return len(data)

            async def mtime(self, path: str) -> float:
                """Base64 has no modification time (return 0)."""
                return 0.0

            async def read_bytes(self, path: str) -> bytes:
                """Read (decode) base64 data."""
                return self._decode_path(path)

            async def read_text(self, path: str, encoding: str = "utf-8") -> str:
                """Read (decode) base64 data as text."""
                data = self._decode_path(path)
                return data.decode(encoding)

            async def write_bytes(self, path: str, data: bytes) -> None:
                """Write (encode) data to base64.

                Note: This modifies the path! The caller should handle
                the new path returned by the node.

                Args:
                    path: Ignored (new path is generated)
                    data: Bytes to encode
                """
                # Encoding happens, but path update is handled by StorageNode
                # The implementor just validates/stores the concept
                pass

            async def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
                """Write (encode) text to base64."""
                await self.write_bytes(path, text.encode(encoding))

            async def delete(self, path: str, recursive: bool = False) -> None:
                """Delete in base64 means clearing the path.

                Since data IS the path, delete doesn't make sense.
                Just don't use the path anymore.
                """
                # No-op for base64 (path is immutable data)
                pass

            async def list_dir(self, path: str) -> list[str]:
                """Base64 has no directories."""
                raise NotImplementedError("Base64 backend doesn't support directories")

            async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
                """Base64 has no directories."""
                raise NotImplementedError("Base64 backend doesn't support directories")

            async def copy(
                self, src_path: str, dest_implementor: AsyncImplementor, dest_path: str
            ) -> str | None:
                """Copy base64 data to another implementor.

                Args:
                    src_path: Source base64 path
                    dest_implementor: Destination implementor
                    dest_path: Destination path

                Returns:
                    New destination path (if dest is also base64)
                """
                # Decode source data
                data = self._decode_path(src_path)

                # Write to destination
                await dest_implementor.write_bytes(dest_path, data)

                # If dest is also base64, return encoded path
                if isinstance(dest_implementor, Base64Implementor):
                    return self._encode_data(data)

                return None

            async def local_path(self, path: str, mode: str = "r"):
                """Base64 doesn't support local_path (data is inline)."""
                raise NotImplementedError(
                    "Base64 backend doesn't support local_path(). "
                    "Data is inline, use read_bytes() instead."
                )

        return {
            "model": Base64Model,
            "implementor": Base64Implementor,
            "capabilities": [
                "read",
                "write",
                # NO: delete, mkdir, list_dir (not a filesystem)
            ],
        }


# Future protocols for CustomProvider:

# @AsyncProvider.protocol('cache')
# def protocol_cache(self) -> dict[str, Any]:
#     """Caching layer wrapper around another backend."""
#     pass

# @AsyncProvider.protocol('encrypted')
# def protocol_encrypted(self) -> dict[str, Any]:
#     """Encrypted storage wrapper."""
#     pass

# @AsyncProvider.protocol('compressed')
# def protocol_compressed(self) -> dict[str, Any]:
#     """Transparent compression wrapper."""
#     pass
