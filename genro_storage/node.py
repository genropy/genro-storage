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
        # TODO: Implement via backend
        pass
    
    @property
    def isfile(self) -> bool:
        """True if node points to a file.
        
        Returns:
            bool: True if this node is a file, False if directory or doesn't exist
        
        Examples:
            >>> if node.isfile:
            ...     data = node.read_bytes()
        """
        # TODO: Implement via backend
        pass
    
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
        # TODO: Implement via backend
        pass
    
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
        # TODO: Implement via backend
        pass
    
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
        # TODO: Implement via backend
        pass
    
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
    
    # ==================== File I/O Methods ====================
    
    def open(self, mode: str = 'rb') -> BinaryIO | TextIO:
        """Open file and return file-like object.
        
        Args:
            mode: File mode. Supported modes:
                - 'r': Read text
                - 'rb': Read binary (default)
                - 'w': Write text
                - 'wb': Write binary
                - 'a': Append text
                - 'ab': Append binary
        
        Returns:
            BinaryIO | TextIO: File-like object supporting context manager protocol
        
        Raises:
            FileNotFoundError: If file doesn't exist (in read mode)
            StoragePermissionError: If insufficient permissions
        
        Examples:
            >>> # Read binary
            >>> with node.open('rb') as f:
            ...     data = f.read()
            >>> 
            >>> # Write text
            >>> with node.open('w') as f:
            ...     f.write("Hello World")
            >>> 
            >>> # Append
            >>> with node.open('a') as f:
            ...     f.write("\\nAppended line")
        """
        # TODO: Implement via backend
        pass
    
    def read_bytes(self) -> bytes:
        """Read entire file as bytes.
        
        This is a convenience method that reads the entire file content
        into memory. For large files, consider using ``open()`` and reading
        in chunks.
        
        Returns:
            bytes: Complete file contents as bytes
        
        Raises:
            FileNotFoundError: If file doesn't exist
            StoragePermissionError: If insufficient permissions
        
        Examples:
            >>> data = node.read_bytes()
            >>> print(f"Read {len(data)} bytes")
        """
        # TODO: Implement via backend
        pass
    
    def read_text(self, encoding: str = 'utf-8') -> str:
        """Read entire file as string.
        
        This is a convenience method that reads the entire file content
        into memory as a string. For large files, consider using ``open()``
        in text mode and reading in chunks.
        
        Args:
            encoding: Text encoding to use (default: 'utf-8')
        
        Returns:
            str: Complete file contents as string
        
        Raises:
            FileNotFoundError: If file doesn't exist
            StoragePermissionError: If insufficient permissions
            UnicodeDecodeError: If file content is not valid for the specified encoding
        
        Examples:
            >>> content = node.read_text()
            >>> content = node.read_text('latin-1')
            >>> 
            >>> # Process line by line
            >>> for line in content.splitlines():
            ...     print(line)
        """
        # TODO: Implement via backend
        pass
    
    def write_bytes(self, data: bytes) -> None:
        """Write bytes to file.
        
        This will create the file if it doesn't exist, or overwrite it
        if it does exist. Parent directories must exist.
        
        Args:
            data: Bytes to write to the file
        
        Raises:
            StoragePermissionError: If insufficient permissions
            FileNotFoundError: If parent directory doesn't exist
        
        Examples:
            >>> node.write_bytes(b'Hello World')
            >>> node.write_bytes(image_data)
        """
        # TODO: Implement via backend
        pass
    
    def write_text(self, text: str, encoding: str = 'utf-8') -> None:
        """Write string to file.
        
        This will create the file if it doesn't exist, or overwrite it
        if it does exist. Parent directories must exist.
        
        Args:
            text: String to write to the file
            encoding: Text encoding to use (default: 'utf-8')
        
        Raises:
            StoragePermissionError: If insufficient permissions
            FileNotFoundError: If parent directory doesn't exist
        
        Examples:
            >>> node.write_text("Hello World")
            >>> node.write_text("Café", encoding='utf-8')
            >>> 
            >>> # Write multiple lines
            >>> lines = ["Line 1", "Line 2", "Line 3"]
            >>> node.write_text("\\n".join(lines))
        """
        # TODO: Implement via backend
        pass
    
    # ==================== File Operations ====================
    
    def delete(self) -> None:
        """Delete file or directory.
        
        This operation is idempotent - if the file/directory doesn't exist,
        no error is raised.
        
        For directories, this performs a recursive delete (like ``rm -rf``).
        
        Raises:
            StoragePermissionError: If insufficient permissions
        
        Examples:
            >>> # Delete a file
            >>> node.delete()
            >>> 
            >>> # Delete a directory recursively
            >>> dir_node = storage.node('home:temp_data')
            >>> dir_node.delete()  # Removes directory and all contents
        """
        # TODO: Implement via backend
        pass
    
    def copy(self, dest: StorageNode | str) -> StorageNode:
        """Copy file or directory to destination.
        
        This works seamlessly across different storage backends. Large files
        are streamed to avoid loading everything in memory.
        
        Args:
            dest: Destination as StorageNode or path string.
                If destination is a directory, the file will be copied
                inside with the same basename.
        
        Returns:
            StorageNode: The destination node
        
        Raises:
            FileNotFoundError: If source doesn't exist
            StoragePermissionError: If insufficient permissions
        
        Examples:
            >>> # Copy within same storage
            >>> node.copy(storage.node('home:backup/file.txt'))
            >>> 
            >>> # Copy across different storage backends
            >>> node.copy(storage.node('s3:uploads/file.txt'))
            >>> 
            >>> # Copy with string destination
            >>> node.copy('home:backup/file.txt')
            >>> 
            >>> # Copy directory recursively
            >>> dir_node.copy(storage.node('home:backup/my_folder'))
        """
        # TODO: Implement via backend
        pass
    
    def move(self, dest: StorageNode | str) -> StorageNode:
        """Move file or directory to destination.
        
        If source and destination are on the same backend, this will use
        an efficient rename operation. Otherwise, it will copy then delete.
        
        After this operation, the current node will point to the new location.
        
        Args:
            dest: Destination as StorageNode or path string
        
        Returns:
            StorageNode: The destination node (also updates self)
        
        Raises:
            FileNotFoundError: If source doesn't exist
            StoragePermissionError: If insufficient permissions
        
        Examples:
            >>> # Move within same storage (efficient rename)
            >>> node.move(storage.node('home:archive/file.txt'))
            >>> print(node.fullpath)  # Now points to home:archive/file.txt
            >>> 
            >>> # Move across storage backends (copy + delete)
            >>> node.move(storage.node('s3:uploads/file.txt'))
        """
        # TODO: Implement via backend
        pass
    
    # ==================== Directory Operations ====================
    
    def children(self) -> list[StorageNode]:
        """List child nodes (if directory).
        
        Returns:
            list[StorageNode]: List of StorageNode objects for each child
        
        Raises:
            ValueError: If node is not a directory
        
        Examples:
            >>> if node.isdir:
            ...     for child in node.children():
            ...         if child.isfile:
            ...             print(f"{child.basename}: {child.size} bytes")
            ...         else:
            ...             print(f"{child.basename}/")
        """
        # TODO: Implement via backend
        pass
    
    def child(self, name: str) -> StorageNode:
        """Get a child node by name.
        
        This doesn't check if the child exists - it just creates a StorageNode
        pointing to the path. Use ``.exists`` on the result to check existence.
        
        Args:
            name: Child name (filename or subdirectory name)
        
        Returns:
            StorageNode: A node pointing to the child (may not exist)
        
        Examples:
            >>> docs = storage.node('home:documents')
            >>> report = docs.child('report.pdf')
            >>> 
            >>> if report.exists:
            ...     content = report.read_text()
            >>> 
            >>> # Navigate multiple levels
            >>> subdir = docs.child('reports').child('2024')
        """
        child_path = str(self._posix_path / name)
        return StorageNode(self._manager, self._mount_name, child_path)
    
    def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory.
        
        Args:
            parents: If True, create parent directories as needed (like ``mkdir -p``)
            exist_ok: If True, don't raise error if directory already exists
        
        Raises:
            FileExistsError: If directory exists and exist_ok=False
            FileNotFoundError: If parent doesn't exist and parents=False
            StoragePermissionError: If insufficient permissions
        
        Examples:
            >>> # Create single directory (parent must exist)
            >>> node = storage.node('home:new_folder')
            >>> node.mkdir()
            >>> 
            >>> # Create directory and all parents
            >>> node = storage.node('home:a/b/c/d')
            >>> node.mkdir(parents=True)
            >>> 
            >>> # Idempotent creation
            >>> node.mkdir(parents=True, exist_ok=True)
        """
        # TODO: Implement via backend
        pass
    
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
