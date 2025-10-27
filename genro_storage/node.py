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
