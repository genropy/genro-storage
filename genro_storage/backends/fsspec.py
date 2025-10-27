"""Fsspec-based backend for genro-storage.

This module provides a generic backend that wraps fsspec filesystems,
allowing access to local, S3, GCS, Azure, HTTP, and other storage systems
through a unified interface.
"""

from typing import BinaryIO, TextIO
from pathlib import PurePosixPath
import fsspec

from .base import StorageBackend


class FsspecBackend(StorageBackend):
    """Generic backend that wraps any fsspec filesystem.
    
    This backend provides a unified interface to any fsspec-compatible
    filesystem, including:
    - Local filesystem (file://)
    - Amazon S3 (s3://)
    - Google Cloud Storage (gcs://)
    - Azure Blob Storage (az://)
    - HTTP/HTTPS (http://, https://)
    - In-memory (memory://)
    - And many more...
    
    Args:
        protocol: Fsspec protocol (e.g., 'file', 's3', 'gcs', 'memory')
        base_path: Base path within the filesystem (optional)
        **kwargs: Additional arguments passed to fsspec.filesystem()
    
    Examples:
        >>> # Local filesystem
        >>> backend = FsspecBackend('file', base_path='/home/user')
        >>> 
        >>> # S3
        >>> backend = FsspecBackend('s3', base_path='my-bucket/uploads',
        ...                         anon=False, region='eu-west-1')
        >>> 
        >>> # Memory (for testing)
        >>> backend = FsspecBackend('memory', base_path='/test')
    """
    
    def __init__(self, protocol: str, base_path: str = '', **kwargs):
        """Initialize FsspecBackend.
        
        Args:
            protocol: Fsspec protocol name
            base_path: Base path prefix for all operations
            **kwargs: Additional arguments for fsspec.filesystem()
        """
        self.protocol = protocol
        self.base_path = base_path.rstrip('/')
        self.fs_kwargs = kwargs
        
        # Create fsspec filesystem instance
        self.fs = fsspec.filesystem(protocol, **kwargs)
    
    def _full_path(self, path: str) -> str:
        """Combine base_path with relative path.
        
        Args:
            path: Relative path
        
        Returns:
            str: Full path including base_path
        """
        if not path:
            return self.base_path or '/'
        
        if self.base_path:
            # Normalize path separators
            clean_path = path.lstrip('/')
            return f"{self.base_path}/{clean_path}"
        
        return path
    
    def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        full_path = self._full_path(path)
        return self.fs.exists(full_path)
    
    def is_file(self, path: str) -> bool:
        """Check if path points to a file."""
        full_path = self._full_path(path)
        try:
            info = self.fs.info(full_path)
            return info['type'] == 'file'
        except FileNotFoundError:
            return False
    
    def is_dir(self, path: str) -> bool:
        """Check if path points to a directory."""
        full_path = self._full_path(path)
        try:
            info = self.fs.info(full_path)
            return info['type'] == 'directory'
        except FileNotFoundError:
            return False
    
    def size(self, path: str) -> int:
        """Get file size in bytes."""
        full_path = self._full_path(path)
        
        info = self.fs.info(full_path)
        
        if info['type'] != 'file':
            raise ValueError(f"Path is a directory, not a file: {path}")
        
        return info.get('size', 0)
    
    def mtime(self, path: str) -> float:
        """Get last modification time."""
        full_path = self._full_path(path)
        
        info = self.fs.info(full_path)
        
        # fsspec may return 'mtime' or 'LastModified' depending on backend
        if 'mtime' in info:
            return info['mtime']
        elif 'LastModified' in info:
            # S3-style timestamp
            import datetime
            dt = info['LastModified']
            if isinstance(dt, datetime.datetime):
                return dt.timestamp()
        
        # Fallback: return current time
        import time
        return time.time()
    
    def open(self, path: str, mode: str = 'rb') -> BinaryIO | TextIO:
        """Open file and return file-like object."""
        full_path = self._full_path(path)
        return self.fs.open(full_path, mode)
    
    def read_bytes(self, path: str) -> bytes:
        """Read entire file as bytes."""
        full_path = self._full_path(path)
        
        with self.fs.open(full_path, 'rb') as f:
            return f.read()
    
    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read entire file as text."""
        full_path = self._full_path(path)
        
        with self.fs.open(full_path, 'r', encoding=encoding) as f:
            return f.read()
    
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        full_path = self._full_path(path)
        
        with self.fs.open(full_path, 'wb') as f:
            f.write(data)
    
    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        """Write text to file."""
        full_path = self._full_path(path)
        
        with self.fs.open(full_path, 'w', encoding=encoding) as f:
            f.write(text)
    
    def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        full_path = self._full_path(path)
        
        if not self.fs.exists(full_path):
            # Idempotent
            return
        
        # fsspec's rm handles both files and directories
        self.fs.rm(full_path, recursive=recursive)
    
    def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        full_path = self._full_path(path)
        
        # Get all items in directory
        items = self.fs.ls(full_path, detail=False)
        
        # Extract just the names (not full paths)
        base = full_path.rstrip('/') + '/'
        names = []
        for item in items:
            if item.startswith(base):
                name = item[len(base):]
                # Only direct children (no nested paths)
                if '/' not in name:
                    names.append(name)
            else:
                # Fallback: use basename
                names.append(item.split('/')[-1])
        
        return names
    
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        full_path = self._full_path(path)
        
        if self.fs.exists(full_path):
            if not exist_ok:
                raise FileExistsError(f"Directory already exists: {path}")
            return
        
        # fsspec's makedirs handles parent creation
        if parents:
            self.fs.makedirs(full_path, exist_ok=True)
        else:
            # Check parent exists
            parent = str(PurePosixPath(full_path).parent)
            if parent and not self.fs.exists(parent):
                raise FileNotFoundError(f"Parent directory does not exist: {parent}")
            
            self.fs.mkdir(full_path)
    
    def copy(self, src_path: str, dest_backend: StorageBackend, dest_path: str) -> str | None:
        """Copy file/directory to another backend."""
        src_full = self._full_path(src_path)

        # Check if both are fsspec backends
        if isinstance(dest_backend, FsspecBackend):
            dest_full = dest_backend._full_path(dest_path)

            # Use fsspec's copy if same filesystem
            if self.fs == dest_backend.fs:
                self.fs.copy(src_full, dest_full, recursive=True)
                return None

        # Fallback: copy via read/write
        info = self.fs.info(src_full)

        if info['type'] == 'file':
            # Copy single file
            data = self.read_bytes(src_path)
            result = dest_backend.write_bytes(dest_path, data)
            return result  # Return new path if dest backend changed it
        
        elif info['type'] == 'directory':
            # Copy directory recursively
            dest_backend.mkdir(dest_path, parents=True, exist_ok=True)
            
            for item in self.fs.ls(src_full, detail=True):
                item_name = item['name'].split('/')[-1]
                
                if item['type'] == 'file':
                    src_item = f"{src_path}/{item_name}" if src_path else item_name
                    dest_item = f"{dest_path}/{item_name}" if dest_path else item_name
                    self.copy(src_item, dest_backend, dest_item)
                elif item['type'] == 'directory':
                    src_item = f"{src_path}/{item_name}" if src_path else item_name
                    dest_item = f"{dest_path}/{item_name}" if dest_path else item_name
                    self.copy(src_item, dest_backend, dest_item)
    
    def get_versions(self, path: str) -> list[dict]:
        """Get list of available versions for a file.

        Returns version history for versioned storage (S3 with versioning enabled).
        For non-versioned storage, returns empty list.

        Args:
            path: Relative path to file

        Returns:
            list[dict]: List of version info dicts with keys:
                - version_id: Version identifier
                - is_latest: True if this is the current version
                - last_modified: Modification timestamp
                - size: File size in bytes

        Examples:
            >>> versions = backend.get_versions('document.pdf')
            >>> for v in versions:
            ...     print(f"Version {v['version_id']}: {v['last_modified']}")

        Notes:
            - Only S3 with versioning enabled returns versions
            - GCS and Azure have different versioning models
            - Empty list if versioning not enabled or not supported
        """
        full_path = self._full_path(path)

        # S3: Get version history
        if self.protocol == 's3':
            if hasattr(self.fs, 'object_version_info'):
                try:
                    versions_info = self.fs.object_version_info(full_path)
                    # Convert to normalized format
                    return [
                        {
                            'version_id': v.get('VersionId'),
                            'is_latest': v.get('IsLatest', False),
                            'last_modified': v.get('LastModified'),
                            'size': v.get('Size', 0)
                        }
                        for v in versions_info
                    ]
                except Exception:
                    # Versioning not enabled or error
                    return []
            else:
                return []

        # Other protocols: no versioning
        return []

    def open_version(self, path: str, version_id: str, mode: str = 'rb'):
        """Open a specific version of a file.

        Opens a historical version of a file from versioned storage.
        Only works with S3 when versioning is enabled.

        Args:
            path: Relative path to file
            version_id: Version identifier to open
            mode: Open mode (read modes only)

        Returns:
            File-like object

        Raises:
            ValueError: If mode is not read-only
            PermissionError: If versioning not supported
            FileNotFoundError: If version doesn't exist

        Examples:
            >>> # Open specific version
            >>> with backend.open_version('file.txt', 'xyz123') as f:
            ...     old_content = f.read()
        """
        if 'w' in mode or 'a' in mode or '+' in mode:
            raise ValueError("Cannot write to historical versions (read-only)")

        full_path = self._full_path(path)

        # S3: Open specific version
        if self.protocol == 's3':
            if hasattr(self.fs, 'open'):
                return self.fs.open(full_path, mode, version_id=version_id)
            else:
                raise PermissionError("S3 versioning not available")

        # Other protocols: not supported
        raise PermissionError(
            f"{self.protocol} backend does not support versioning"
        )

    def get_hash(self, path: str) -> str | None:
        """Get MD5 hash from filesystem metadata if available.

        For S3/MinIO: Uses ETag which is the MD5 hash
        For GCS: Also uses ETag
        For Azure: Uses content_md5
        For local/memory: Returns None (must compute)

        Args:
            path: Relative path to file

        Returns:
            str | None: MD5 hash as hexadecimal string, or None if not in metadata
        """
        full_path = self._full_path(path)

        try:
            info = self.fs.info(full_path)
        except FileNotFoundError:
            return None

        # S3/MinIO/GCS: ETag is MD5 (wrapped in quotes)
        if 'ETag' in info:
            return info['ETag'].strip('"')

        # Azure Blob Storage: content_md5
        if 'content_md5' in info:
            return info['content_md5']

        # No hash available in metadata
        return None

    def get_metadata(self, path: str) -> dict[str, str]:
        """Get custom metadata for a file.

        Retrieves user-defined metadata from cloud storage. Different storage
        backends store metadata in different ways:
        - S3: Uses 'Metadata' field
        - GCS: Uses 'metadata' field
        - Azure: Uses 'metadata' field

        Args:
            path: Relative path to file

        Returns:
            dict[str, str]: Metadata key-value pairs

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self._full_path(path)

        try:
            info = self.fs.info(full_path)
        except FileNotFoundError:
            raise FileNotFoundError(f"File not found: {path}")

        # Extract metadata based on protocol
        if self.protocol == 's3':
            # S3: metadata in 'Metadata' field (case-sensitive)
            return info.get('Metadata', {})
        elif self.protocol in ('gcs', 'gs'):
            # GCS: metadata in 'metadata' field
            return info.get('metadata', {})
        elif self.protocol in ('azure', 'az', 'adl'):
            # Azure: metadata in 'metadata' field
            return info.get('metadata', {})
        else:
            # Other protocols: no metadata support
            return {}

    def set_metadata(self, path: str, metadata: dict[str, str]) -> None:
        """Set custom metadata for a file.

        Stores user-defined metadata with the file in cloud storage.

        Args:
            path: Relative path to file
            metadata: Metadata key-value pairs to set

        Raises:
            FileNotFoundError: If file doesn't exist
            PermissionError: If backend doesn't support metadata
            ValueError: If metadata keys/values are invalid

        Notes:
            - For S3: Replaces all existing metadata
            - For GCS/Azure: Similar behavior
            - Some backends have key/value restrictions
        """
        full_path = self._full_path(path)

        # Check file exists
        if not self.fs.exists(full_path):
            raise FileNotFoundError(f"File not found: {path}")

        # Validate metadata
        if not isinstance(metadata, dict):
            raise ValueError("Metadata must be a dictionary")

        for key, value in metadata.items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ValueError("Metadata keys and values must be strings")

        # Set metadata based on protocol
        if self.protocol == 's3':
            # S3: Use setxattr or update_metadata if available
            if hasattr(self.fs, 'setxattr'):
                for key, value in metadata.items():
                    self.fs.setxattr(full_path, key, value)
            else:
                raise PermissionError(
                    "S3 metadata update not available in this fsspec version. "
                    "Consider using boto3 directly for metadata operations."
                )

        elif self.protocol in ('gcs', 'gs'):
            # GCS: Use setxattr if available
            if hasattr(self.fs, 'setxattr'):
                for key, value in metadata.items():
                    self.fs.setxattr(full_path, key, value)
            else:
                raise PermissionError("GCS metadata update not available")

        elif self.protocol in ('azure', 'az', 'adl'):
            # Azure: Use setxattr if available
            if hasattr(self.fs, 'setxattr'):
                for key, value in metadata.items():
                    self.fs.setxattr(full_path, key, value)
            else:
                raise PermissionError("Azure metadata update not available")

        else:
            # Other protocols don't support metadata
            raise PermissionError(
                f"{self.protocol} backend does not support metadata operations"
            )

    def url(self, path: str, expires_in: int = 3600, **kwargs) -> str | None:
        """Generate public URL for file access.

        For S3: Generates presigned URL
        For GCS: Generates signed URL
        For HTTP: Returns direct URL
        For others: Returns None

        Args:
            path: Relative path to file
            expires_in: URL expiration time in seconds
            **kwargs: Backend-specific options

        Returns:
            str | None: Public URL or None if not supported
        """
        full_path = self._full_path(path)

        # S3: Generate presigned URL
        if self.protocol == 's3':
            if hasattr(self.fs, 'sign'):
                # s3fs supports signing
                return self.fs.sign(full_path, expiration=expires_in)
            else:
                # Fallback: no presigned URL support
                return None

        # HTTP: Return direct URL
        elif self.protocol in ('http', 'https'):
            # For HTTP, the path IS the URL
            return full_path

        # GCS: Generate signed URL
        elif self.protocol in ('gcs', 'gs'):
            if hasattr(self.fs, 'sign'):
                return self.fs.sign(full_path, expiration=expires_in)
            else:
                return None

        # Other protocols: no URL support
        else:
            return None

    def internal_url(self, path: str, nocache: bool = False) -> str | None:
        """Generate internal/relative URL for file access.

        This is a simplified version that returns a path-based URL.
        Applications should override this with their own URL generation logic.

        Args:
            path: Relative path to file
            nocache: If True, append mtime as query parameter

        Returns:
            str | None: Internal URL or None
        """
        # For cloud storage, we don't have an "internal" URL concept
        # Applications would typically use their own URL routing
        # Return None by default
        return None

    def local_path(self, path: str, mode: str = 'r'):
        """Get local filesystem path for remote file.

        Downloads the file to a temporary location, yields the local path,
        and uploads changes back on exit if the file was modified.

        This allows external tools (ffmpeg, imagemagick, etc.) to work
        with remote files transparently.

        Args:
            path: Relative path to file
            mode: Access mode - 'r' (read), 'w' (write), 'rw' (read-write)

        Returns:
            Context manager yielding str (local temp file path)

        Examples:
            >>> # Process remote S3 file with ffmpeg
            >>> with backend.local_path('video.mp4', mode='r') as local_path:
            ...     subprocess.run(['ffmpeg', '-i', local_path, 'output.mp4'])
            >>>
            >>> # Modify remote file in place
            >>> with backend.local_path('image.jpg', mode='rw') as local_path:
            ...     subprocess.run(['convert', local_path, '-resize', '800', local_path])
            >>> # Changes uploaded automatically
        """
        import tempfile
        import os
        from contextlib import contextmanager

        @contextmanager
        def _local_path():
            full_path = self._full_path(path)

            # Create temporary file
            suffix = os.path.splitext(path)[1]  # Preserve extension
            with tempfile.NamedTemporaryFile(mode='w+b', suffix=suffix, delete=False) as tmp:
                tmp_path = tmp.name

            try:
                # Download file if reading
                if mode in ('r', 'rw'):
                    if self.fs.exists(full_path):
                        # Download from remote to temp
                        with self.fs.open(full_path, 'rb') as remote_file:
                            with open(tmp_path, 'wb') as local_file:
                                # Stream in chunks to handle large files
                                chunk_size = 8 * 1024 * 1024  # 8MB chunks
                                while True:
                                    chunk = remote_file.read(chunk_size)
                                    if not chunk:
                                        break
                                    local_file.write(chunk)
                    elif mode == 'rw':
                        # File doesn't exist but mode is rw - create empty
                        pass

                # Yield temp path for user to work with
                yield tmp_path

                # Upload file if writing
                if mode in ('w', 'rw'):
                    # Upload from temp to remote
                    if os.path.exists(tmp_path):
                        # Ensure parent directory exists
                        parent = str(PurePosixPath(full_path).parent)
                        if parent and parent != '.':
                            self.fs.makedirs(parent, exist_ok=True)

                        # Upload
                        with open(tmp_path, 'rb') as local_file:
                            with self.fs.open(full_path, 'wb') as remote_file:
                                # Stream in chunks
                                chunk_size = 8 * 1024 * 1024  # 8MB chunks
                                while True:
                                    chunk = local_file.read(chunk_size)
                                    if not chunk:
                                        break
                                    remote_file.write(chunk)

            finally:
                # Always cleanup temp file
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return _local_path()

    def close(self) -> None:
        """Close filesystem connection if needed."""
        # Most fsspec filesystems don't need explicit closing
        # but S3 and others might have session cleanup
        if hasattr(self.fs, 'close'):
            self.fs.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"FsspecBackend(protocol='{self.protocol}', base_path='{self.base_path}')"
