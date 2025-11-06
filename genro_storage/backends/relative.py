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

"""Relative mount backend for hierarchical storage organization.

This module provides RelativeMountBackend, a wrapper that creates child
mounts referencing a parent mount with a relative path prefix and optional
permission restrictions.
"""

from __future__ import annotations

from typing import BinaryIO, TextIO, Literal

from .base import StorageBackend
from ..capabilities import BackendCapabilities
from ..exceptions import StoragePermissionError


PermissionLevel = Literal["readonly", "readwrite", "delete"]


class RelativeMountBackend(StorageBackend):
    """Backend wrapper for relative mounts with permission control.

    A relative mount creates a logical child mount that inherits the backend
    type and configuration from a parent mount, but operates on a subdirectory
    with optional permission restrictions.

    Permission levels:
        - readonly: Can read files, list directories, check existence
        - readwrite: Can read and write files, create directories, copy files
        - delete: Can perform all operations including deletion

    Args:
        parent_backend: The parent backend to wrap
        relative_path: Path prefix to prepend to all operations
        permissions: Permission level (default: 'delete' = full access)

    Examples:
        >>> # Parent mount for S3 bucket
        >>> parent = FsspecBackend('s3', base_path='my-bucket')
        >>>
        >>> # Child mount for uploads with read-write only
        >>> child = RelativeMountBackend(parent, 'uploads', permissions='readwrite')
        >>>
        >>> # Operations on child are prefixed
        >>> child.write_bytes('file.txt', b'data')  # writes to my-bucket/uploads/file.txt
        >>> child.delete('file.txt')  # raises PermissionError (no delete permission)
    """

    def __init__(
        self,
        parent_backend: StorageBackend,
        relative_path: str,
        permissions: PermissionLevel = "delete",
    ):
        """Initialize relative mount backend.

        Args:
            parent_backend: Parent backend to wrap
            relative_path: Path prefix for all operations
            permissions: Permission level ('readonly', 'readwrite', 'delete')
        """
        self.parent = parent_backend
        self.relative_path = relative_path.rstrip("/")
        self.permissions = permissions

    def _full_path(self, path: str) -> str:
        """Combine relative_path with operation path.

        Args:
            path: Path relative to this mount

        Returns:
            str: Full path including relative_path prefix
        """
        if not path:
            return self.relative_path

        # Normalize and combine paths
        clean_path = path.lstrip("/")
        if self.relative_path:
            return f"{self.relative_path}/{clean_path}"
        return clean_path

    def _check_write_permission(self) -> None:
        """Check if write operations are allowed.

        Raises:
            StoragePermissionError: If mount is read-only
        """
        if self.permissions == "readonly":
            raise StoragePermissionError(f"Mount is read-only. Write operations are not permitted.")

    def _check_delete_permission(self) -> None:
        """Check if delete operations are allowed.

        Raises:
            StoragePermissionError: If mount doesn't have delete permission
        """
        if self.permissions in ("readonly", "readwrite"):
            raise StoragePermissionError(
                f"Mount does not have delete permission (current: {self.permissions})"
            )

    @property
    def capabilities(self) -> BackendCapabilities:
        """Return parent backend capabilities.

        Returns:
            BackendCapabilities: Capabilities inherited from parent
        """
        return self.parent.capabilities

    # Read operations (allowed for all permission levels)

    def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        return self.parent.exists(self._full_path(path))

    def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        return self.parent.is_file(self._full_path(path))

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        return self.parent.is_dir(self._full_path(path))

    def size(self, path: str) -> int:
        """Get file size in bytes."""
        return self.parent.size(self._full_path(path))

    def mtime(self, path: str) -> float:
        """Get last modification time."""
        return self.parent.mtime(self._full_path(path))

    def open(self, path: str, mode: str = "rb") -> BinaryIO | TextIO:
        """Open file with permission check for write modes."""
        if mode in ("w", "wb", "a", "ab", "r+", "rb+", "w+", "wb+", "a+", "ab+"):
            self._check_write_permission()
        return self.parent.open(self._full_path(path), mode)

    def read_bytes(self, path: str) -> bytes:
        """Read entire file as bytes."""
        return self.parent.read_bytes(self._full_path(path))

    def read_text(self, path: str, encoding: str = "utf-8") -> str:
        """Read entire file as text."""
        return self.parent.read_text(self._full_path(path), encoding)

    def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        return self.parent.list_dir(self._full_path(path))

    def get_hash(self, path: str) -> str | None:
        """Get MD5 hash from filesystem metadata."""
        return self.parent.get_hash(self._full_path(path))

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get custom metadata for file."""
        return self.parent.get_metadata(self._full_path(path))

    def get_versions(self, path: str) -> list[dict]:
        """Get list of available versions."""
        return self.parent.get_versions(self._full_path(path))

    def open_version(self, path: str, version_id: str, mode: str = "rb"):
        """Open specific version of file."""
        return self.parent.open_version(self._full_path(path), version_id, mode)

    def url(self, path: str, expires_in: int = 3600, **kwargs) -> str | None:
        """Generate public URL for file access."""
        return self.parent.url(self._full_path(path), expires_in, **kwargs)

    def internal_url(self, path: str, nocache: bool = False) -> str | None:
        """Generate internal URL for file access."""
        return self.parent.internal_url(self._full_path(path), nocache)

    def local_path(self, path: str, mode: str = "r"):
        """Get local filesystem path with permission check for write modes."""
        if mode in ("w", "rw"):
            self._check_write_permission()
        return self.parent.local_path(self._full_path(path), mode)

    # Write operations (require readwrite or delete permission)

    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        self._check_write_permission()
        self.parent.write_bytes(self._full_path(path), data)

    def write_text(self, path: str, text: str, encoding: str = "utf-8") -> None:
        """Write text to file."""
        self._check_write_permission()
        self.parent.write_text(self._full_path(path), text, encoding)

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        self._check_write_permission()
        self.parent.mkdir(self._full_path(path), parents, exist_ok)

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set custom metadata for file."""
        self._check_write_permission()
        self.parent.set_metadata(self._full_path(path), metadata)

    def copy(self, src_path: str, dest_backend: "StorageBackend", dest_path: str) -> str | None:
        """Copy file to another backend."""
        # Source read is always allowed
        # Destination write is checked by dest_backend
        return self.parent.copy(self._full_path(src_path), dest_backend, dest_path)

    # Delete operations (require delete permission)

    def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        self._check_delete_permission()
        self.parent.delete(self._full_path(path), recursive)

    def delete_version(self, path: str, version_id: str) -> None:
        """Delete specific version of file."""
        self._check_delete_permission()
        self.parent.delete_version(self._full_path(path), version_id)

    def close(self) -> None:
        """Close backend - delegates to parent."""
        # Don't close parent as other mounts may use it
        pass
