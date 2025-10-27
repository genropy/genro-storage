"""Base backend interface for genro-storage.

This module defines the abstract base class that all storage backends
must implement. It provides the contract for file operations across
different storage systems.
"""

from abc import ABC, abstractmethod
from typing import BinaryIO, TextIO


class StorageBackend(ABC):
    """Abstract base class for storage backends.
    
    All storage backend implementations (Local, S3, GCS, Azure, HTTP, etc.)
    must inherit from this class and implement all abstract methods.
    
    This ensures a consistent interface across all storage types and makes
    it easy to add new backends in the future.
    
    Note:
        Backend implementations should not be instantiated directly by users.
        They are created internally by StorageManager based on configuration.
    """
    
    @abstractmethod
    def exists(self, path: str) -> bool:
        """Check if a file or directory exists.
        
        Args:
            path: Relative path within this storage backend
        
        Returns:
            bool: True if file or directory exists
        
        Examples:
            >>> exists = backend.exists('documents/report.pdf')
        """
        pass
    
    @abstractmethod
    def is_file(self, path: str) -> bool:
        """Check if path points to a file.
        
        Args:
            path: Relative path within this storage backend
        
        Returns:
            bool: True if path is a file, False otherwise
        
        Examples:
            >>> if backend.is_file('documents/report.pdf'):
            ...     print("It's a file")
        """
        pass
    
    @abstractmethod
    def is_dir(self, path: str) -> bool:
        """Check if path points to a directory.
        
        Args:
            path: Relative path within this storage backend
        
        Returns:
            bool: True if path is a directory, False otherwise
        
        Examples:
            >>> if backend.is_dir('documents'):
            ...     print("It's a directory")
        """
        pass
    
    @abstractmethod
    def size(self, path: str) -> int:
        """Get file size in bytes.
        
        Args:
            path: Relative path to file
        
        Returns:
            int: File size in bytes
        
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If path is a directory
        
        Examples:
            >>> size = backend.size('documents/report.pdf')
            >>> print(f"File is {size} bytes")
        """
        pass
    
    @abstractmethod
    def mtime(self, path: str) -> float:
        """Get last modification time.
        
        Args:
            path: Relative path to file or directory
        
        Returns:
            float: Unix timestamp of last modification
        
        Raises:
            FileNotFoundError: If path doesn't exist
        
        Examples:
            >>> from datetime import datetime
            >>> timestamp = backend.mtime('documents/report.pdf')
            >>> mod_time = datetime.fromtimestamp(timestamp)
        """
        pass
    
    @abstractmethod
    def open(self, path: str, mode: str = 'rb') -> BinaryIO | TextIO:
        """Open a file and return file-like object.
        
        Args:
            path: Relative path to file
            mode: File mode ('r', 'rb', 'w', 'wb', 'a', 'ab')
        
        Returns:
            BinaryIO | TextIO: File-like object supporting context manager
        
        Raises:
            FileNotFoundError: If file doesn't exist (in read mode)
            PermissionError: If insufficient permissions
        
        Examples:
            >>> with backend.open('file.txt', 'rb') as f:
            ...     data = f.read()
        """
        pass
    
    @abstractmethod
    def read_bytes(self, path: str) -> bytes:
        """Read entire file as bytes.
        
        Args:
            path: Relative path to file
        
        Returns:
            bytes: Complete file contents
        
        Raises:
            FileNotFoundError: If file doesn't exist
        
        Examples:
            >>> data = backend.read_bytes('image.jpg')
        """
        pass
    
    @abstractmethod
    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read entire file as text.
        
        Args:
            path: Relative path to file
            encoding: Text encoding
        
        Returns:
            str: Complete file contents as string
        
        Raises:
            FileNotFoundError: If file doesn't exist
            UnicodeDecodeError: If encoding is incorrect
        
        Examples:
            >>> content = backend.read_text('document.txt')
        """
        pass
    
    @abstractmethod
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file.
        
        Args:
            path: Relative path to file
            data: Bytes to write
        
        Raises:
            PermissionError: If insufficient permissions
            FileNotFoundError: If parent directory doesn't exist
        
        Examples:
            >>> backend.write_bytes('file.bin', b'Hello')
        """
        pass
    
    @abstractmethod
    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        """Write text to file.
        
        Args:
            path: Relative path to file
            text: String to write
            encoding: Text encoding
        
        Raises:
            PermissionError: If insufficient permissions
            FileNotFoundError: If parent directory doesn't exist
        
        Examples:
            >>> backend.write_text('file.txt', 'Hello World')
        """
        pass
    
    @abstractmethod
    def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory.
        
        Args:
            path: Relative path to delete
            recursive: If True, delete directories recursively
        
        Raises:
            FileNotFoundError: If path doesn't exist (implementation may choose to be idempotent)
            ValueError: If path is non-empty directory and recursive=False
        
        Examples:
            >>> backend.delete('file.txt')
            >>> backend.delete('folder', recursive=True)
        """
        pass
    
    @abstractmethod
    def list_dir(self, path: str) -> list[str]:
        """List directory contents.
        
        Args:
            path: Relative path to directory
        
        Returns:
            list[str]: List of names (not full paths) in the directory
        
        Raises:
            FileNotFoundError: If directory doesn't exist
            ValueError: If path is not a directory
        
        Examples:
            >>> names = backend.list_dir('documents')
            >>> for name in names:
            ...     print(name)  # Just 'report.pdf', not 'documents/report.pdf'
        """
        pass
    
    @abstractmethod
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory.
        
        Args:
            path: Relative path to create
            parents: If True, create parent directories as needed
            exist_ok: If True, don't error if directory exists
        
        Raises:
            FileExistsError: If exists and exist_ok=False
            FileNotFoundError: If parent doesn't exist and parents=False
        
        Examples:
            >>> backend.mkdir('new_folder')
            >>> backend.mkdir('a/b/c', parents=True)
        """
        pass
    
    @abstractmethod
    def copy(self, src_path: str, dest_backend: 'StorageBackend', dest_path: str) -> None:
        """Copy file/directory to another backend.
        
        This method handles cross-backend copying efficiently, streaming
        data when possible to avoid loading large files in memory.
        
        Args:
            src_path: Source path in this backend
            dest_backend: Destination backend (may be different type)
            dest_path: Destination path in dest_backend
        
        Raises:
            FileNotFoundError: If source doesn't exist
            PermissionError: If insufficient permissions
        
        Examples:
            >>> # Copy within same backend
            >>> backend.copy('file.txt', backend, 'backup/file.txt')
            >>> 
            >>> # Copy to different backend
            >>> backend.copy('file.txt', other_backend, 'file.txt')
        """
        pass
    
    def get_hash(self, path: str) -> str | None:
        """Get MD5 hash from filesystem metadata if available.
        
        This method attempts to retrieve the MD5 hash from the storage
        backend's metadata without reading the file content. For cloud
        storage like S3, this uses the ETag. For local storage, this
        returns None and the hash must be computed by reading the file.
        
        Args:
            path: Relative path to file
        
        Returns:
            str | None: MD5 hash as hexadecimal string, or None if not available
        
        Examples:
            >>> hash_value = backend.get_hash('file.txt')
            >>> if hash_value:
            ...     print(f"MD5: {hash_value}")
        """
        return None  # Default: no metadata hash available
    
    def close(self) -> None:
        """Close backend and release resources.
        
        This method is called when the backend is no longer needed.
        Implementations should close any open connections, file handles, etc.
        
        The default implementation does nothing. Backends that manage
        resources should override this method.
        
        Examples:
            >>> backend.close()
        """
        pass
