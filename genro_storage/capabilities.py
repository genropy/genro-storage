"""Backend capability declarations.

This module defines the capabilities that storage backends can support,
allowing feature detection and validation before attempting operations.
"""

from dataclasses import dataclass


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
