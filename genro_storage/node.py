"""StorageNode - Represents a file or directory in a storage backend.

This module provides the StorageNode class which is the main interface for
interacting with files and directories across different storage backends.
"""

from __future__ import annotations
from typing import BinaryIO, TextIO, TYPE_CHECKING
from pathlib import PurePosixPath

if TYPE_CHECKING:
    from .manager import StorageManager


class StorageNode:
    """Represents a file or directory in a storage backend.
    
    StorageNode provides a unified interface for file operations across
    different storage backends (local, S3, GCS, Azure, HTTP, etc.).
    
    Note:
        Users should not instantiate StorageNode directly. Use 
        ``StorageManager.node()`` instead.
    
    The node can represent either a file or a directory. Use the properties
    ``isfile`` and ``isdir`` to determine the type.
    
    Examples:
        >>> # Get a node via StorageManager
        >>> node = storage.node('home:documents/report.pdf')
        >>> 
        >>> # Check if it exists
        >>> if node.exists:
        ...     print(f"File size: {node.size} bytes")
        >>> 
        >>> # Read content
        >>> content = node.read_text()
        >>> 
        >>> # Write content
        >>> node.write_text("Hello World")
    
    Attributes:
        fullpath: Full path including mount point (e.g., "home:documents/file.txt")
        exists: True if file or directory exists
        isfile: True if node points to a file
        isdir: True if node points to a directory
        size: File size in bytes
        mtime: Last modification time as Unix timestamp
        basename: Filename with extension
        stem: Filename without extension
        suffix: File extension including dot
        parent: Parent directory as StorageNode
    """
    
    def __init__(self, manager: StorageManager, mount_name: str, path: str):
        """Initialize a StorageNode.
        
        Args:
            manager: The StorageManager instance that owns this node
            mount_name: Name of the mount point (e.g., "home", "uploads")
            path: Relative path within the mount (e.g., "documents/file.txt")
        
        Note:
            This should not be called directly. Use ``StorageManager.node()`` instead.
        """
        self._manager = manager
        self._mount_name = mount_name
        self._path = path
        self._posix_path = PurePosixPath(path) if path else PurePosixPath('.')
        # Get backend from manager
        self._backend = manager._mounts[mount_name]
    
    # ==================== Properties ====================
    
    @property
    def fullpath(self) -> str:
        """Full path including mount point.

        Returns:
            str: Full path in format "mount:path/to/file"

        Examples:
            >>> node = storage.node('home:documents/report.pdf')
            >>> print(node.fullpath)
            'home:documents/report.pdf'
        """
        if self._path:
            return f"{self._mount_name}:{self._path}"
        return f"{self._mount_name}:"

    @property
    def path(self) -> str:
        """Relative path within the mount.

        Returns:
            str: Path relative to mount point (without mount prefix)

        Examples:
            >>> node = storage.node('home:documents/report.pdf')
            >>> print(node.path)
            'documents/report.pdf'

            >>> # For base64 backend, this is the base64-encoded content
            >>> node = storage.node('b64:SGVsbG8=')
            >>> print(node.path)
            'SGVsbG8='
        """
        return self._path

    @property
    def exists(self) -> bool:
        """True if file or directory exists.
        
        Returns:
            bool: True if the file or directory exists on the storage backend
        
        Examples:
            >>> if node.exists:
            ...     print("File exists!")
            ... else:
            ...     print("File not found")
        """
        return self._backend.exists(self._path)
    
    @property
    def isfile(self) -> bool:
        """True if node points to a file.
        
        Returns:
            bool: True if this node is a file, False if directory or doesn't exist
        
        Examples:
            >>> if node.isfile:
            ...     data = node.read_bytes()
        """
        return self._backend.is_file(self._path)
    
    @property
    def isdir(self) -> bool:
        """True if node points to a directory.
        
        Returns:
            bool: True if this node is a directory, False if file or doesn't exist
        
        Examples:
            >>> if node.isdir:
            ...     for child in node.children():
            ...         print(child.basename)
        """
        return self._backend.is_dir(self._path)
    
    @property
    def size(self) -> int:
        """File size in bytes.
        
        Returns:
            int: Size of the file in bytes
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If node is a directory (directories don't have size)
        
        Examples:
            >>> print(f"File size: {node.size} bytes")
            >>> print(f"File size: {node.size / 1024:.1f} KB")
        """
        return self._backend.size(self._path)
    
    @property
    def mtime(self) -> float:
        """Last modification time as Unix timestamp.
        
        Returns:
            float: Unix timestamp of last modification time
        
        Examples:
            >>> from datetime import datetime
            >>> mod_time = datetime.fromtimestamp(node.mtime)
            >>> print(f"Modified: {mod_time}")
        """
        return self._backend.mtime(self._path)
    
    @property
    def basename(self) -> str:
        """Filename with extension.
        
        Returns:
            str: The filename including extension
        
        Examples:
            >>> node = storage.node('home:documents/report.pdf')
            >>> print(node.basename)
            'report.pdf'
        """
        return self._posix_path.name
    
    @property
    def stem(self) -> str:
        """Filename without extension.
        
        Returns:
            str: The filename without extension
        
        Examples:
            >>> node = storage.node('home:documents/report.pdf')
            >>> print(node.stem)
            'report'
        """
        return self._posix_path.stem
    
    @property
    def suffix(self) -> str:
        """File extension including dot.
        
        Returns:
            str: The file extension including the leading dot (e.g., ".pdf")
        
        Examples:
            >>> node = storage.node('home:documents/report.pdf')
            >>> print(node.suffix)
            '.pdf'
        """
        return self._posix_path.suffix
    
    @property
    def parent(self) -> StorageNode:
        """Parent directory as StorageNode.
        
        Returns:
            StorageNode: A new StorageNode pointing to the parent directory
        
        Examples:
            >>> node = storage.node('home:documents/reports/q4.pdf')
            >>> parent = node.parent
            >>> print(parent.fullpath)
            'home:documents/reports'
        """
        parent_path = str(self._posix_path.parent)
        if parent_path == '.':
            parent_path = ''
        return StorageNode(self._manager, self._mount_name, parent_path)
    
    @property
    def md5hash(self) -> str:
        """MD5 hash of file content.

        For cloud storage (S3, GCS, Azure), retrieves hash from metadata (fast).
        For local storage, computes hash by reading file in blocks (slower).

        Returns:
            str: MD5 hash as lowercase hexadecimal string (32 characters)

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If node is a directory

        Examples:
            >>> hash1 = node1.md5hash
            >>> hash2 = node2.md5hash
            >>> if hash1 == hash2:
            ...     print("Files have identical content")
        """
        # Check if exists first
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self.fullpath}")

        # Check if it's a file (not a directory)
        if not self.isfile:
            raise ValueError(f"Cannot compute hash of directory: {self.fullpath}")
        
        # Try to get hash from backend metadata first (S3 ETag, etc.)
        metadata_hash = self._backend.get_hash(self._path)
        if metadata_hash:
            return metadata_hash.lower()
        
        # Fallback: compute MD5 by reading file in blocks
        import hashlib
        hasher = hashlib.md5()
        
        # Use 64KB blocks like Genropy legacy code
        BLOCKSIZE = 65536
        
        with self.open('rb') as f:
            while True:
                chunk = f.read(BLOCKSIZE)
                if not chunk:
                    break
                hasher.update(chunk)
        
        return hasher.hexdigest()
    
    # ==================== File I/O Methods ====================
    
    def open(self, mode: str = 'rb') -> BinaryIO | TextIO:
        """Open file and return file-like object.
        
        Args:
            mode: File mode ('r', 'rb', 'w', 'wb', 'a', 'ab')
        
        Returns:
            BinaryIO | TextIO: File-like object (context manager)
        
        Examples:
            >>> with node.open('rb') as f:
            ...     data = f.read()
        """
        return self._backend.open(self._path, mode)
    
    def read_bytes(self) -> bytes:
        """Read entire file as bytes."""
        return self._backend.read_bytes(self._path)
    
    def read_text(self, encoding: str = 'utf-8') -> str:
        """Read entire file as string."""
        return self._backend.read_text(self._path, encoding)
    
    def write_bytes(self, data: bytes) -> None:
        """Write bytes to file.

        Note:
            For base64 backend, this updates the node's path to the new base64-encoded content.
        """
        result = self._backend.write_bytes(self._path, data)
        # If backend returns a new path (e.g., base64), update it
        if result is not None:
            self._path = result
            self._posix_path = PurePosixPath(result) if result else PurePosixPath('.')
    
    def write_text(self, text: str, encoding: str = 'utf-8') -> None:
        """Write string to file.

        Note:
            For base64 backend, this updates the node's path to the new base64-encoded content.
        """
        result = self._backend.write_text(self._path, text, encoding)
        # If backend returns a new path (e.g., base64), update it
        if result is not None:
            self._path = result
            self._posix_path = PurePosixPath(result) if result else PurePosixPath('.')
    
    # ==================== File Operations ====================
    
    def delete(self) -> None:
        """Delete file or directory."""
        self._backend.delete(self._path, recursive=True)
    
    def copy(self, dest: StorageNode | str) -> StorageNode:
        """Copy file/directory to destination.

        Note:
            If copying to base64 backend, the destination node's path will be
            updated to the new base64-encoded content.
        """
        # Convert string to StorageNode if needed
        if isinstance(dest, str):
            dest = self._manager.node(dest)

        # Copy via backends
        new_path = self._backend.copy(self._path, dest._backend, dest._path)

        # If destination backend returned a new path, update dest
        if new_path is not None:
            dest._path = new_path
            dest._posix_path = PurePosixPath(new_path) if new_path else PurePosixPath('.')

        return dest
    
    def move(self, dest: StorageNode | str) -> StorageNode:
        """Move file/directory to destination."""
        # Convert string to StorageNode if needed
        if isinstance(dest, str):
            dest = self._manager.node(dest)
        
        # Copy then delete
        self.copy(dest)
        self.delete()
        
        # Update self to point to new location
        self._mount_name = dest._mount_name
        self._path = dest._path
        self._posix_path = dest._posix_path
        self._backend = dest._backend
        
        return self
    
    # ==================== Directory Operations ====================
    
    def children(self) -> list[StorageNode]:
        """List child nodes (if directory)."""
        names = self._backend.list_dir(self._path)
        return [self.child(name) for name in names]
    
    def child(self, name: str) -> StorageNode:
        """Get a child node by name."""
        child_path = str(self._posix_path / name)
        return StorageNode(self._manager, self._mount_name, child_path)
    
    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        self._backend.mkdir(self._path, parents=parents, exist_ok=exist_ok)

    # ==================== Advanced Methods ====================

    def local_path(self, mode: str = 'r'):
        """Get local filesystem path for this file.

        Returns a context manager that provides a local filesystem path.
        For local storage, returns the actual path. For remote storage
        (S3, GCS, etc.), downloads to a temporary file, yields the temp path,
        and uploads changes on exit.

        This is essential for integrating with external tools that only
        work with local filesystem paths (ffmpeg, ImageMagick, etc.).

        Args:
            mode: Access mode
                - 'r': Read-only (download, no upload)
                - 'w': Write-only (no download, upload on exit)
                - 'rw': Read-write (download and upload)

        Returns:
            Context manager yielding str (local filesystem path)

        Examples:
            >>> # Process video with ffmpeg
            >>> video = storage.node('s3:videos/input.mp4')
            >>> with video.local_path(mode='r') as path:
            ...     subprocess.run(['ffmpeg', '-i', path, 'output.mp4'])
            >>>
            >>> # Modify image in place
            >>> image = storage.node('s3:photos/pic.jpg')
            >>> with image.local_path(mode='rw') as path:
            ...     subprocess.run(['convert', path, '-resize', '800x600', path])
            >>> # Changes automatically uploaded to S3

        Notes:
            - For local storage, returns the actual path (no copy)
            - For remote storage, uses temporary files
            - Temporary files are automatically cleaned up on exit
            - Large files are streamed in chunks to avoid memory issues
        """
        return self._backend.local_path(self._path, mode=mode)

    def get_metadata(self) -> dict[str, str]:
        """Get custom metadata for this file.

        Returns user-defined metadata attached to the file. Supported for
        cloud storage (S3, GCS, Azure). For local storage, returns empty dict.

        Returns:
            dict[str, str]: Metadata key-value pairs

        Raises:
            FileNotFoundError: If file doesn't exist

        Examples:
            >>> file = storage.node('s3:documents/report.pdf')
            >>> metadata = file.get_metadata()
            >>> print(metadata.get('Author'))
            'John Doe'
        """
        return self._backend.get_metadata(self._path)

    def set_metadata(self, metadata: dict[str, str]) -> None:
        """Set custom metadata for this file.

        Attaches user-defined metadata to the file. Supported for cloud
        storage (S3, GCS, Azure). For local storage, raises PermissionError.

        Args:
            metadata: Metadata key-value pairs to set

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If backend doesn't support metadata
            ValueError: If metadata keys/values are invalid

        Examples:
            >>> file = storage.node('s3:documents/report.pdf')
            >>> file.set_metadata({
            ...     'Author': 'John Doe',
            ...     'Version': '1.0',
            ...     'Department': 'Engineering'
            ... })

        Notes:
            - Keys and values must be strings
            - This typically replaces all existing metadata
            - Cloud providers may have size/format restrictions
        """
        return self._backend.set_metadata(self._path, metadata)

    def url(self, expires_in: int = 3600, **kwargs) -> str | None:
        """Generate public URL for accessing this file.

        Returns a URL that can be used to access the file directly.
        For cloud storage (S3, GCS), generates a presigned/signed URL.
        For HTTP storage, returns the direct URL.
        For local storage, returns None.

        Args:
            expires_in: URL expiration time in seconds (default: 3600 = 1 hour)
            **kwargs: Backend-specific options

        Returns:
            str | None: Public URL or None if not supported

        Examples:
            >>> # S3 presigned URL
            >>> file = storage.node('s3:documents/report.pdf')
            >>> url = file.url()
            >>> print(url)
            'https://bucket.s3.amazonaws.com/documents/report.pdf?X-Amz-...'
            >>>
            >>> # Custom expiration (24 hours)
            >>> url = file.url(expires_in=86400)

        Notes:
            - Cloud storage URLs are temporary and expire
            - Use this for sharing files externally
            - HTTP URLs are direct (no expiration)
        """
        return self._backend.url(self._path, expires_in=expires_in, **kwargs)

    def internal_url(self, nocache: bool = False) -> str | None:
        """Generate internal/relative URL for this file.

        Returns a URL suitable for internal application use.
        Optionally includes cache busting parameters.

        Args:
            nocache: If True, append mtime for cache busting

        Returns:
            str | None: Internal URL or None if not supported

        Examples:
            >>> file = storage.node('home:static/app.js')
            >>> url = file.internal_url(nocache=True)
            >>> print(url)
            '/storage/home/static/app.js?mtime=1234567890'

        Notes:
            - Useful for web applications
            - Cache busting helps with CDN/browser caching
        """
        return self._backend.internal_url(self._path, nocache=nocache)

    @property
    def versions(self) -> list[dict]:
        """Get list of available versions for this file.

        Returns version history for versioned storage (S3 with versioning enabled).
        For non-versioned storage, returns empty list.

        Returns:
            list[dict]: List of version info dicts

        Examples:
            >>> file = storage.node('s3:documents/report.pdf')
            >>> for v in file.versions:
            ...     print(f"Version {v['version_id']}: {v['last_modified']}")

        Notes:
            - Only S3 with versioning enabled returns versions
            - Empty list if versioning not supported
        """
        return self._backend.get_versions(self._path)

    def open_version(self, version_id: str, mode: str = 'rb'):
        """Open a specific version of this file.

        Opens a historical version from versioned storage (S3).
        Only read modes are supported for historical versions.

        Args:
            version_id: Version identifier to open
            mode: Open mode (read modes only, default: 'rb')

        Returns:
            File-like object

        Raises:
            ValueError: If mode is not read-only
            PermissionError: If versioning not supported
            FileNotFoundError: If version doesn't exist

        Examples:
            >>> file = storage.node('s3:documents/report.pdf')
            >>> versions = file.versions
            >>> if versions:
            ...     # Open previous version
            ...     with file.open_version(versions[1]['version_id']) as f:
            ...         old_content = f.read()

        Notes:
            - Only works with S3 versioning enabled
            - Historical versions are read-only
        """
        return self._backend.open_version(self._path, version_id, mode)

    def fill_from_url(self, url: str, timeout: int = 30) -> None:
        """Download content from URL and write to this file.

        Fetches content from the specified URL and writes it to this storage node.
        Useful for downloading files from the internet into storage.

        Args:
            url: URL to download from (http:// or https://)
            timeout: Request timeout in seconds (default: 30)

        Raises:
            ValueError: If URL is invalid
            IOError: If download fails
            PermissionError: If storage is read-only

        Examples:
            >>> # Download image from internet
            >>> img = storage.node('s3:downloads/logo.png')
            >>> img.fill_from_url('https://example.com/logo.png')
            >>>
            >>> # Download with custom timeout
            >>> file = storage.node('local:data.json')
            >>> file.fill_from_url('https://api.example.com/data', timeout=60)

        Notes:
            - Uses urllib for HTTP requests (no external dependencies)
            - Overwrites existing file if present
            - Parent directory must exist or backend must support auto-creation
        """
        import urllib.request
        import urllib.error

        # Validate URL
        if not url or not url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL: {url}. Must start with http:// or https://")

        # Download content
        try:
            with urllib.request.urlopen(url, timeout=timeout) as response:
                data = response.read()
        except urllib.error.URLError as e:
            raise IOError(f"Failed to download from {url}: {e}") from e
        except Exception as e:
            raise IOError(f"Error downloading from {url}: {e}") from e

        # Write to storage
        self.write_bytes(data)

    def to_base64(self, mime: str | None = None, include_uri: bool = True) -> str:
        """Encode file content as base64 string.

        Converts the file content to a base64-encoded string, optionally
        formatted as a data URI for direct embedding in HTML/CSS.

        Args:
            mime: MIME type to include in data URI (auto-detected if None)
            include_uri: If True, format as data URI; if False, return raw base64

        Returns:
            str: Base64-encoded string or data URI

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If node is a directory

        Examples:
            >>> # Data URI with auto-detected MIME type
            >>> img = storage.node('images:logo.png')
            >>> data_uri = img.to_base64()
            >>> print(data_uri)
            'data:image/png;base64,iVBORw0KGgo...'
            >>>
            >>> # Raw base64 without URI wrapper
            >>> b64 = img.to_base64(include_uri=False)
            >>> print(b64)
            'iVBORw0KGgo...'
            >>>
            >>> # Custom MIME type
            >>> data_uri = img.to_base64(mime='image/x-icon')

        Notes:
            - Useful for embedding small images/files in HTML
            - MIME type auto-detection based on file extension
            - Large files will result in very long strings
        """
        import base64
        import mimetypes

        # Check exists and is file
        if not self.exists:
            raise FileNotFoundError(f"File not found: {self.fullpath}")

        if not self.isfile:
            raise ValueError(f"Cannot encode directory as base64: {self.fullpath}")

        # Read file content
        data = self.read_bytes()

        # Encode to base64
        b64_data = base64.b64encode(data).decode('ascii')

        # Return based on format
        if include_uri:
            # Auto-detect MIME type if not provided
            if mime is None:
                mime, _ = mimetypes.guess_type(self.basename)
                if mime is None:
                    mime = 'application/octet-stream'

            return f'data:{mime};base64,{b64_data}'
        else:
            return b64_data

    # ==================== Special Methods ====================
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"StorageNode('{self.fullpath}')"
    
    def __str__(self) -> str:
        """String representation."""
        return self.fullpath
    
    def __truediv__(self, other: str) -> StorageNode:
        """Support path / 'child' syntax.
        
        Examples:
            >>> docs = storage.node('home:documents')
            >>> report = docs / 'reports' / '2024' / 'q4.pdf'
            >>> print(report.fullpath)
            'home:documents/reports/2024/q4.pdf'
        """
        return self.child(other)
    
    def __eq__(self, other: object) -> bool:
        """Compare nodes by content (MD5 hash).
        
        Two nodes are considered equal if they have the same file content,
        regardless of their path or location. Comparison is done via MD5 hash.
        
        Args:
            other: Another StorageNode or object to compare
        
        Returns:
            bool: True if both nodes have identical content
        
        Examples:
            >>> file1 = storage.node('home:original.txt')
            >>> file2 = storage.node('backup:copy.txt')
            >>> if file1 == file2:
            ...     print("Files have identical content")
        
        Notes:
            - Only files can be compared (directories return False)
            - Non-existent files return False
            - Comparing with non-StorageNode returns NotImplemented
        """
        if not isinstance(other, StorageNode):
            return NotImplemented
        
        # If same path, they're equal
        if self.fullpath == other.fullpath:
            return True
        
        # Both must be files to compare content
        if not (self.isfile and other.isfile):
            return False
        
        # Compare via MD5 hash
        try:
            return self.md5hash == other.md5hash
        except (FileNotFoundError, ValueError):
            return False
    
    def __ne__(self, other: object) -> bool:
        """Compare nodes for inequality.
        
        Args:
            other: Another StorageNode or object to compare
        
        Returns:
            bool: True if nodes have different content
        
        Examples:
            >>> if file1 != file2:
            ...     print("Files differ")
        """
        result = self.__eq__(other)
        if result is NotImplemented:
            return NotImplemented
        return not result
