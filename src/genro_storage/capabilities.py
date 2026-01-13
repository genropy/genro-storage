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

"""Backend capability declarations.

This module defines the capabilities that storage backends can support,
allowing feature detection and validation before attempting operations.
"""

from dataclasses import dataclass
from typing import Callable


def capability(*names: str) -> Callable:
    """Decorator to automatically register capabilities on the backend class.

    During class definition, this decorator adds capability names to the class's
    PROTOCOL_CAPABILITIES dictionary. For single-protocol backends, uses the
    _default_protocol attribute; for multi-protocol backends (like FsspecBackend),
    the dictionary must be declared manually.

    Args:
        *names: One or more capability names (e.g., 'read', 'write', 'mkdir')

    Examples:
        >>> class MyBackend(StorageBackend):
        ...     _default_protocol = 'mybackend'
        ...
        ...     @capability('read')
        ...     def read_bytes(self, path):
        ...         pass
        ...
        ...     @capability('write', 'metadata')
        ...     def write_bytes(self, path, data):
        ...         pass
        ...
        ...     # Capabilities are now automatically registered:
        ...     # MyBackend.PROTOCOL_CAPABILITIES == {'mybackend': {'read', 'write', 'metadata'}}
    """

    def decorator(func: Callable) -> Callable:
        # Access the class namespace during class construction
        import sys

        frame = sys._getframe(1)
        namespace = frame.f_locals

        # Get the protocol for this class (default to class name in lowercase)
        protocol = namespace.get("_default_protocol")
        if protocol is None:
            # Try to infer from class name (remove 'Backend' or 'Storage' suffix)
            class_name = namespace.get("__qualname__", "unknown")
            protocol = class_name.lower().replace("backend", "").replace("storage", "") or "unknown"

        # Initialize PROTOCOL_CAPABILITIES dict if needed
        if "PROTOCOL_CAPABILITIES" not in namespace:
            namespace["PROTOCOL_CAPABILITIES"] = {}

        # Initialize capability set for this protocol
        if protocol not in namespace["PROTOCOL_CAPABILITIES"]:
            namespace["PROTOCOL_CAPABILITIES"][protocol] = set()

        # Register these capability names
        namespace["PROTOCOL_CAPABILITIES"][protocol].update(names)

        return func

    return decorator


@dataclass(frozen=True)
class BackendCapabilities:
    """Declares what features a storage backend supports.

    This allows code to check capabilities before attempting operations,
    providing better error messages and enabling conditional features.

    Attributes:
        read: Backend supports read operations
        write: Backend supports write operations
        delete: Backend supports delete operations
        mkdir: Backend supports creating directories
        list_dir: Backend supports listing directory contents
        versioning: Backend supports file versioning (S3, GCS with versioning)
        version_listing: Backend can list all versions of a file
        version_access: Backend can access specific versions
        metadata: Backend supports custom key-value metadata
        presigned_urls: Backend can generate temporary signed URLs
        public_urls: Backend has public HTTP URLs
        atomic_operations: Backend guarantees atomic write operations
        symbolic_links: Backend supports symbolic links (local filesystem)
        copy_optimization: Backend supports native server-side copy
        hash_on_metadata: MD5/ETag available without reading file
        append_mode: Backend supports append mode ('a')
        seek_support: Backend supports seek operations in file handles
        readonly: Backend is read-only (HTTP, read-only mounts)
        temporary: Storage is temporary/ephemeral (memory backend)

    Examples:
        >>> # Check if backend supports versioning
        >>> if node.capabilities.versioning:
        ...     versions = node.versions

        >>> # Check if backend is read-only
        >>> if node.capabilities.readonly:
        ...     print("Cannot write to this storage")
    """

    # Core operations
    read: bool = True
    write: bool = True
    delete: bool = True

    # Directory operations
    mkdir: bool = True
    list_dir: bool = True

    # Versioning support
    versioning: bool = False
    version_listing: bool = False
    version_access: bool = False

    # Metadata support
    metadata: bool = False

    # URL generation
    presigned_urls: bool = False
    public_urls: bool = False

    # Advanced features
    atomic_operations: bool = True
    symbolic_links: bool = False
    copy_optimization: bool = False
    hash_on_metadata: bool = False

    # Performance characteristics
    append_mode: bool = True
    seek_support: bool = True

    # Access patterns
    readonly: bool = False
    temporary: bool = False

    def __str__(self) -> str:
        """Return human-readable list of supported features."""
        features = []
        if self.versioning:
            features.append("versioning")
        if self.metadata:
            features.append("metadata")
        if self.presigned_urls:
            features.append("presigned URLs")
        if self.copy_optimization:
            features.append("server-side copy")
        if self.hash_on_metadata:
            features.append("fast hashing")
        if self.symbolic_links:
            features.append("symbolic links")
        if self.readonly:
            features.append("read-only")
        if self.temporary:
            features.append("temporary storage")

        return ", ".join(features) if features else "basic file operations"
