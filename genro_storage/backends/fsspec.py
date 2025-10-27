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
    
    def copy(self, src_path: str, dest_backend: StorageBackend, dest_path: str) -> None:
        """Copy file/directory to another backend."""
        src_full = self._full_path(src_path)
        
        # Check if both are fsspec backends
        if isinstance(dest_backend, FsspecBackend):
            dest_full = dest_backend._full_path(dest_path)
            
            # Use fsspec's copy if same filesystem
            if self.fs == dest_backend.fs:
                self.fs.copy(src_full, dest_full, recursive=True)
                return
        
        # Fallback: copy via read/write
        info = self.fs.info(src_full)
        
        if info['type'] == 'file':
            # Copy single file
            data = self.read_bytes(src_path)
            dest_backend.write_bytes(dest_path, data)
        
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
    
    def close(self) -> None:
        """Close filesystem connection if needed."""
        # Most fsspec filesystems don't need explicit closing
        # but S3 and others might have session cleanup
        if hasattr(self.fs, 'close'):
            self.fs.close()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"FsspecBackend(protocol='{self.protocol}', base_path='{self.base_path}')"
