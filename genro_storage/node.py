"""StorageNode - Represents a file or directory in a storage backend.

This module provides the StorageNode class which is the main interface for
interacting with files and directories across different storage backends.
"""

from __future__ import annotations
from typing import BinaryIO, TextIO, TYPE_CHECKING, Callable, Literal
from pathlib import PurePosixPath
from enum import Enum
from datetime import datetime

if TYPE_CHECKING:
    from .manager import StorageManager


class SkipStrategy(str, Enum):
    """Strategy for skipping files during copy operations.

    Attributes:
        NEVER: Always copy (overwrite existing files)
        EXISTS: Skip if destination file exists (fastest)
        SIZE: Skip if destination exists and has same size (fast)
        HASH: Skip if destination exists and has same content/MD5 (accurate)
        CUSTOM: Use custom skip function provided by user
    """
    NEVER = 'never'
    EXISTS = 'exists'
    SIZE = 'size'
    HASH = 'hash'
    CUSTOM = 'custom'


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
    
    def __init__(self, manager: StorageManager, mount_name: str | None, path: str | None, version: int | str | None = None):
        """Initialize a StorageNode.

        Args:
            manager: The StorageManager instance that owns this node
            mount_name: Name of the mount point (e.g., "home", "uploads"), or None for dummy node
            path: Relative path within the mount (e.g., "documents/file.txt"), or None for dummy node
            version: Optional version specifier for versioned storage.
                If set, the node becomes a read-only snapshot of that version.

        Note:
            This should not be called directly. Use ``StorageManager.node()`` instead.
        """
        self._manager = manager
        self._mount_name = mount_name
        self._path = path
        self._version = version  # None = current version, int/str = specific version
        self._posix_path = PurePosixPath(path) if path else PurePosixPath('.')

        # Virtual node support (set by iternode()/diffnode())
        self._is_virtual = False
        self._virtual_type = None  # 'iter' or 'diff'
        self._sources: list[StorageNode] = []  # For virtual nodes

        # Get backend from manager (None for virtual nodes)
        self._backend = manager._mounts[mount_name] if mount_name else None
    
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
            bool: True if the file or directory exists on the storage backend.
                  Virtual nodes always return False.

        Examples:
            >>> if node.exists:
            ...     print("File exists!")
            ... else:
            ...     print("File not found")
        """
        # Virtual nodes don't have physical storage
        if self._is_virtual:
            return False
        return self._backend.exists(self._path)
    
    @property
    def isfile(self) -> bool:
        """True if node points to a file.
        
        Returns:
            bool: True if this node is a file, False if directory or doesn't exist
        
        Examples:
            >>> if node.isfile:
            ...     data = node._read_bytes()
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

    @property
    def mimetype(self) -> str:
        """Get MIME type from file extension.

        Uses Python's mimetypes module to guess the MIME type based on
        the file extension. Returns 'application/octet-stream' if type
        cannot be determined.

        Returns:
            str: MIME type string (e.g., 'image/png', 'application/pdf')

        Examples:
            >>> jpg = storage.node('photos:image.jpg')
            >>> jpg.mimetype
            'image/jpeg'
            >>>
            >>> pdf = storage.node('documents:report.pdf')
            >>> pdf.mimetype
            'application/pdf'
            >>>
            >>> # Use for HTTP responses
            >>> response.headers['Content-Type'] = node.mimetype
        """
        import mimetypes
        mime, _ = mimetypes.guess_type(self.path)
        return mime or 'application/octet-stream'

    @property
    def capabilities(self):
        """Get capabilities of underlying backend.

        Returns backend capabilities which describe what features are supported,
        such as versioning, metadata, presigned URLs, etc.

        If this node is a versioned snapshot (created with version parameter),
        the versioning capabilities are disabled since the node is read-only.

        Returns:
            BackendCapabilities: Object describing supported features

        Examples:
            >>> if node.capabilities.versioning:
            ...     versions = node.versions
            >>> if node.capabilities.presigned_urls:
            ...     url = node.get_presigned_url()
        """
        caps = self._backend.capabilities

        # If node has a fixed version, it's a snapshot and loses versioning capabilities
        if self._version is not None:
            from dataclasses import replace
            caps = replace(caps,
                           versioning=False,
                           version_listing=False,
                           version_access=False)

        return caps

    # ==================== File I/O Methods ====================

    def open(self,
             mode: str = 'r',
             version: int | str | None = None,
             as_of: datetime | None = None) -> BinaryIO | TextIO:
        """Open file with optional version control support.

        Args:
            mode: File mode ('r', 'rb', 'w', 'wb', 'a', 'ab')
            version: Version to open:
                - None: Latest version (default)
                - str: Specific version_id (e.g., 'abc123...')
                - int: Version index with negative indexing support:
                    - -1: Latest version
                    - -2: Previous version
                    - 0: Oldest version
                    - 1: Second oldest version
            as_of: Open file as it was at this datetime

        Returns:
            BinaryIO | TextIO: File-like object (context manager)

        Raises:
            ValueError: If both version and as_of provided, or invalid mode for historical versions
            IndexError: If version index out of range
            FileNotFoundError: If no version found for as_of date
            PermissionError: If backend doesn't support versioning

        Examples:
            >>> # Latest version
            >>> with node.open() as f:
            ...     data = f.read()

            >>> # Previous version (pythonic!)
            >>> with node.open(version=-2) as f:
            ...     previous = f.read()

            >>> # Specific version by ID
            >>> with node.open(version='abc123xyz') as f:
            ...     old_content = f.read()

            >>> # Version at date
            >>> from datetime import datetime
            >>> with node.open(as_of=datetime(2024, 1, 15)) as f:
            ...     historical = f.read()
        """
        # If node has a fixed version, cannot specify another version
        if self._version is not None and (version is not None or as_of is not None):
            raise ValueError(
                "This node is a versioned snapshot. "
                "Cannot specify version parameter on an already-versioned node."
            )

        # If node has a fixed version, it's read-only
        if self._version is not None and mode in ('w', 'wb', 'a', 'ab'):
            raise ValueError(
                "Cannot write to versioned snapshot. "
                "Create a new node without version parameter to write."
            )

        # Use node's version if set, otherwise use parameter
        effective_version = self._version if self._version is not None else version

        # Validazione parametri
        if version is not None and as_of is not None:
            raise ValueError(
                "Cannot specify both version and as_of. "
                "Use version for ID/index or as_of for date-based access."
            )

        # Check versioning capability FIRST
        if effective_version is not None or as_of is not None:
            # Check backend capabilities (not node capabilities, since we might be using self._version)
            if not self._backend.capabilities.versioning:
                raise PermissionError(
                    f"{self._mount_name} backend does not support versioning. "
                    f"Supported features: {self._list_supported_features()}"
                )

        # Accesso per data
        if as_of is not None:
            if 'w' in mode or 'a' in mode or '+' in mode:
                raise ValueError("Cannot write to historical versions (read-only)")

            version_id = self._resolve_version_at_date(as_of)
            if not version_id:
                raise FileNotFoundError(
                    f"No version found before {as_of} for {self.fullpath}"
                )
            return self._backend.open_version(self._path, version_id, mode)

        # Accesso per version
        if effective_version is not None:
            if 'w' in mode or 'a' in mode or '+' in mode:
                raise ValueError("Cannot write to historical versions (read-only)")

            # Se è un intero, risolvi l'indice
            if isinstance(effective_version, int):
                version_id = self._resolve_version_index(effective_version)
            else:
                # È già un version_id stringa
                version_id = effective_version

            return self._backend.open_version(self._path, version_id, mode)

        # Accesso normale (latest)
        return self._backend.open(self._path, mode)

    def _read_bytes(self) -> bytes:
        """Internal method: Read entire file as bytes.

        If node has a fixed version, reads that version.
        For virtual nodes, materializes content.
        """
        # Virtual node: materialize content
        if self._is_virtual:
            if self._virtual_type == 'iter':
                # Concatenate all sources as bytes
                return b''.join(node._read_bytes() for node in self._sources)
            elif self._virtual_type == 'diff':
                # Diff as bytes (encode UTF-8)
                return self._read_text().encode('utf-8')
            else:
                raise ValueError(f"Unknown virtual type: {self._virtual_type}")

        # Versioned node
        if self._version is not None:
            with self.open(mode='rb') as f:
                return f.read()

        # Normal node
        return self._backend.read_bytes(self._path)

    def _read_text(self, encoding: str = 'utf-8') -> str:
        """Internal method: Read entire file as string.

        If node has a fixed version, reads that version.
        For virtual nodes, materializes content.
        """
        # Virtual node: materialize content
        if self._is_virtual:
            if self._virtual_type == 'iter':
                # Concatenate all sources as text
                return ''.join(node._read_text(encoding) for node in self._sources)
            elif self._virtual_type == 'diff':
                # Generate unified diff
                if len(self._sources) != 2:
                    raise ValueError("diffnode requires exactly 2 nodes")

                node1, node2 = self._sources

                # Check if binary by reading bytes first
                bytes1 = node1._read_bytes()
                bytes2 = node2._read_bytes()

                # Check for null bytes (binary indicator)
                if b'\x00' in bytes1 or b'\x00' in bytes2:
                    raise ValueError("Cannot diff binary files")

                # Try to decode
                try:
                    text1 = bytes1.decode(encoding)
                    text2 = bytes2.decode(encoding)
                except UnicodeDecodeError:
                    raise ValueError("Cannot diff binary files")

                # Generate unified diff
                import difflib
                lines1 = text1.splitlines(keepends=True)
                lines2 = text2.splitlines(keepends=True)
                diff_lines = difflib.unified_diff(
                    lines1, lines2,
                    fromfile=node1.fullpath or 'file1',
                    tofile=node2.fullpath or 'file2'
                )
                return ''.join(diff_lines)
            else:
                raise ValueError(f"Unknown virtual type: {self._virtual_type}")

        # Versioned node
        if self._version is not None:
            with self.open(mode='r') as f:
                content = f.read()
            # If we got bytes, decode them
            if isinstance(content, bytes):
                return content.decode(encoding)
            return content

        # Normal node
        return self._backend.read_text(self._path, encoding)

    def read(self, mode: str = 'r', encoding: str = 'utf-8') -> str | bytes:
        """Read file content in text or binary mode.

        Args:
            mode: Read mode - 'r' for text (default), 'rb' for binary
            encoding: Text encoding (used only for text mode)

        Returns:
            str | bytes: File content as text or bytes depending on mode

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If mode is invalid

        Examples:
            >>> # Read as text (default)
            >>> content = node.read()
            >>> content = node.read(mode='r')
            >>>
            >>> # Read as binary
            >>> data = node.read(mode='rb')
        """
        if mode == 'r':
            return self._read_text(encoding)
        elif mode == 'rb':
            return self._read_bytes()
        else:
            raise ValueError(f"Invalid read mode '{mode}'. Use 'r' for text or 'rb' for binary")

    def _write_bytes(self, data: bytes, skip_if_unchanged: bool = False) -> bool:
        """Internal method: Write bytes to file.

        Args:
            data: Bytes to write
            skip_if_unchanged: If True, skip writing if content identical to current version.
                Uses MD5 hash comparison with existing file's ETag (S3) or computed hash.

        Returns:
            bool: True if written, False if skipped (only when skip_if_unchanged=True)

        Raises:
            ValueError: If node is a versioned snapshot (read-only)

        Note:
            For base64 backend, this updates the node's path to the new base64-encoded content.

        Examples:
            >>> # Simple write
            >>> node.write_bytes(b'Hello World')
            True

            >>> # Skip if unchanged (efficient for versioned storage)
            >>> written = node.write_bytes(data, skip_if_unchanged=True)
            >>> if written:
            ...     print("File updated")
            ... else:
            ...     print("Content unchanged, skipped")
        """
        # Cannot write to virtual nodes
        if self._is_virtual:
            raise ValueError(
                "Cannot write to virtual node (no path). "
                "Virtual nodes are read-only."
            )

        # Cannot write to versioned snapshots
        if self._version is not None:
            raise ValueError(
                "Cannot write to versioned snapshot. "
                "Create a new node without version parameter to write."
            )
        # Check if we should skip
        if skip_if_unchanged:
            import hashlib

            # Try to compare with existing content
            if self.capabilities.versioning and self.exists:
                # Calculate MD5 of new content
                new_md5 = hashlib.md5(data).hexdigest()

                # Get latest version ETag
                versions = self.versions
                if versions:
                    # Find latest version
                    latest = next((v for v in versions if v.get('is_latest')), versions[0])
                    current_etag = latest.get('etag', '')

                    # Compare (S3 ETag is MD5 for simple uploads)
                    if current_etag and new_md5 == current_etag:
                        return False  # Skip: content identical
            elif self.exists:
                # Non-versioned backend: compare with current content
                try:
                    current_data = self._read_bytes()
                    if current_data == data:
                        return False  # Skip: content identical
                except Exception:
                    pass  # If we can't read, write anyway

        # Write the data
        result = self._backend.write_bytes(self._path, data)
        # If backend returns a new path (e.g., base64), update it
        if result is not None:
            self._path = result
            self._posix_path = PurePosixPath(result) if result else PurePosixPath('.')

        return True

    def _write_text(self, text: str, encoding: str = 'utf-8', skip_if_unchanged: bool = False) -> bool:
        """Internal method: Write string to file.

        Args:
            text: String to write
            encoding: Text encoding (default: 'utf-8')
            skip_if_unchanged: If True, skip writing if content identical to current version.
                Uses MD5 hash comparison with existing file's ETag (S3) or computed hash.

        Returns:
            bool: True if written, False if skipped (only when skip_if_unchanged=True)

        Note:
            For base64 backend, this updates the node's path to the new base64-encoded content.

        Examples:
            >>> # Simple write
            >>> node.write_text('Hello World')
            True

            >>> # Skip if unchanged
            >>> written = node.write_text(content, skip_if_unchanged=True)
            >>> if not written:
            ...     print("Content unchanged, skipped")
        """
        return self._write_bytes(text.encode(encoding), skip_if_unchanged=skip_if_unchanged)

    def write(self, data: str | bytes, mode: str = 'w', encoding: str = 'utf-8', skip_if_unchanged: bool = False) -> bool:
        """Write data to file in text or binary mode.

        Args:
            data: Data to write (str for text mode, bytes for binary mode)
            mode: Write mode - 'w' for text (default), 'wb' for binary
            encoding: Text encoding (used only for text mode)
            skip_if_unchanged: If True, skip writing if content identical

        Returns:
            bool: True if written, False if skipped

        Raises:
            TypeError: If data type doesn't match mode
            ValueError: If mode is invalid

        Examples:
            >>> # Write text (default)
            >>> node.write('Hello World')
            >>> node.write('Hello', mode='w')
            >>>
            >>> # Write binary
            >>> node.write(b'binary data', mode='wb')
            >>>
            >>> # Skip if unchanged
            >>> written = node.write('content', skip_if_unchanged=True)
        """
        if mode == 'w':
            if not isinstance(data, str):
                raise TypeError(f"Text mode 'w' requires str, got {type(data).__name__}")
            return self._write_text(data, encoding, skip_if_unchanged)
        elif mode == 'wb':
            if not isinstance(data, bytes):
                raise TypeError(f"Binary mode 'wb' requires bytes, got {type(data).__name__}")
            return self._write_bytes(data, skip_if_unchanged)
        else:
            raise ValueError(f"Invalid write mode '{mode}'. Use 'w' for text or 'wb' for binary")

    # ==================== File Operations ====================

    def delete(self) -> None:
        """Delete file or directory."""
        self._backend.delete(self._path, recursive=True)

    def _should_skip_file(self, dest: StorageNode,
                          skip: SkipStrategy | str,
                          skip_fn: Callable[[StorageNode, StorageNode], bool] | None) -> tuple[bool, str]:
        """Determine if file should be skipped during copy.

        Args:
            dest: Destination node
            skip: Skip strategy to use
            skip_fn: Custom skip function (required if skip='custom')

        Returns:
            Tuple of (should_skip: bool, reason: str)
        """
        # Never skip if destination doesn't exist
        if not dest.exists:
            return (False, '')

        # Check skip strategy
        if skip == 'never' or skip == SkipStrategy.NEVER:
            return (False, '')

        elif skip == 'exists' or skip == SkipStrategy.EXISTS:
            return (True, 'destination exists')

        elif skip == 'size' or skip == SkipStrategy.SIZE:
            try:
                if self.size == dest.size:
                    return (True, f'same size ({self.size} bytes)')
                else:
                    return (False, '')
            except Exception:
                # If size comparison fails, don't skip
                return (False, '')

        elif skip == 'hash' or skip == SkipStrategy.HASH:
            try:
                # Use MD5 hash comparison (with cloud metadata optimization)
                if self.md5hash == dest.md5hash:
                    return (True, f'same content (MD5: {self.md5hash[:8]}...)')
                else:
                    return (False, '')
            except Exception:
                # If hash comparison fails, don't skip
                return (False, '')

        elif skip == 'custom' or skip == SkipStrategy.CUSTOM:
            try:
                if skip_fn and skip_fn(self, dest):
                    return (True, 'custom function returned True')
                else:
                    return (False, '')
            except Exception as e:
                # If custom function fails, don't skip
                return (False, '')

        return (False, '')

    def _copy_file_with_skip(self, dest: StorageNode,
                             skip: SkipStrategy | str,
                             skip_fn: Callable[[StorageNode, StorageNode], bool] | None,
                             on_file: Callable[[StorageNode], None] | None,
                             on_skip: Callable[[StorageNode, str], None] | None) -> StorageNode:
        """Copy single file with skip logic.

        Args:
            dest: Destination node
            skip: Skip strategy
            skip_fn: Custom skip function
            on_file: Callback after file copied
            on_skip: Callback when file skipped

        Returns:
            Destination node
        """
        # Check if we should skip
        should_skip, reason = self._should_skip_file(dest, skip, skip_fn)

        if should_skip:
            if on_skip:
                on_skip(self, reason)
            return dest

        # Perform actual copy
        new_path = self._backend.copy(self._path, dest._backend, dest._path)

        # Update destination path if backend returned new path
        if new_path is not None:
            dest._path = new_path
            dest._posix_path = PurePosixPath(new_path) if new_path else PurePosixPath('.')

        # Call on_file callback
        if on_file:
            on_file(self)

        return dest

    def _copy_dir_with_skip(self, dest: StorageNode,
                            skip: SkipStrategy | str,
                            skip_fn: Callable[[StorageNode, StorageNode], bool] | None,
                            progress: Callable[[int, int], None] | None,
                            on_file: Callable[[StorageNode], None] | None,
                            on_skip: Callable[[StorageNode, str], None] | None,
                            include_patterns: list[str] | None = None,
                            exclude_patterns: list[str] | None = None,
                            filter_fn: Callable[[StorageNode, str], bool] | None = None) -> StorageNode:
        """Copy directory recursively with filtering, skip logic and progress tracking.

        Args:
            dest: Destination node
            skip: Skip strategy
            skip_fn: Custom skip function
            progress: Progress callback(current, total)
            on_file: Callback after each file copied
            on_skip: Callback when file skipped
            include_patterns: Glob patterns for files to include
            exclude_patterns: Glob patterns for files to exclude
            filter_fn: Custom filter function(node, relpath) -> bool

        Returns:
            Destination node
        """
        # Create destination directory if needed
        if not dest.exists:
            dest.mkdir(parents=True, exist_ok=True)

        # Collect all files to process (with filtering)
        files_to_process = []

        def matches_filters(node: StorageNode, relpath: str) -> tuple[bool, str]:
            """Check if file matches include/exclude/filter criteria.

            Returns:
                tuple[bool, str]: (should_include, reason_if_excluded)
            """
            from fnmatch import fnmatch

            # If include patterns specified, file must match at least one (whitelist mode)
            if include_patterns:
                matched = False
                for pattern in include_patterns:
                    if fnmatch(relpath, pattern):
                        matched = True
                        break
                if not matched:
                    return False, f"not matching include patterns"

            # Check exclude patterns (blacklist)
            if exclude_patterns:
                for pattern in exclude_patterns:
                    if fnmatch(relpath, pattern):
                        return False, f"matching exclude pattern '{pattern}'"

            # Apply custom filter function
            if filter_fn:
                try:
                    if not filter_fn(node, relpath):
                        return False, "filtered by custom function"
                except Exception as e:
                    # If filter raises exception, skip the file
                    return False, f"filter error: {e}"

            return True, ""

        def collect_files(src_node: StorageNode, dest_node: StorageNode, relpath: str = ""):
            """Recursively collect all files that match filters."""
            if src_node.isfile:
                # Apply filtering
                should_include, reason = matches_filters(src_node, relpath)
                if should_include:
                    files_to_process.append((src_node, dest_node, relpath))
                elif on_skip:
                    # Notify about filtered files
                    on_skip(src_node, reason)

            elif src_node.isdir:
                # Ensure destination dir exists
                if not dest_node.exists:
                    dest_node.mkdir(parents=True, exist_ok=True)

                # Recurse into children
                for child in src_node.children():
                    child_relpath = f"{relpath}/{child.basename}" if relpath else child.basename
                    collect_files(child, dest_node.child(child.basename), child_relpath)

        collect_files(self, dest)

        # Process files with progress tracking
        total = len(files_to_process)

        for idx, (src, dst, relpath) in enumerate(files_to_process, 1):
            # Check skip condition (skip logic is destination-based)
            should_skip, reason = src._should_skip_file(dst, skip, skip_fn)

            if should_skip:
                if on_skip:
                    on_skip(src, reason)
            else:
                # Copy file
                new_path = src._backend.copy(src._path, dst._backend, dst._path)

                # Update destination path if backend returned new path
                if new_path is not None:
                    dst._path = new_path
                    dst._posix_path = PurePosixPath(new_path) if new_path else PurePosixPath('.')

                if on_file:
                    on_file(src)

            # Progress callback
            if progress:
                progress(idx, total)

        return dest

    def copy_to(self, dest: StorageNode | str,
             # Filtering (source-based)
             include: str | list[str] | None = None,
             exclude: str | list[str] | None = None,
             filter: Callable[[StorageNode, str], bool] | None = None,
             # Skip logic (destination-based)
             skip: SkipStrategy | Literal['never', 'exists', 'size', 'hash', 'custom'] = 'never',
             skip_fn: Callable[[StorageNode, StorageNode], bool] | None = None,
             # Callbacks
             progress: Callable[[int, int], None] | None = None,
             on_file: Callable[[StorageNode], None] | None = None,
             on_skip: Callable[[StorageNode, str], None] | None = None) -> StorageNode:
        """Copy file or directory to destination with filtering and skip logic.

        Supports filtering which files to copy (source-based) and skipping
        existing files (destination-based) for efficient incremental backups.

        Filtering (applied to source files):
            - 'include': Glob patterns for files to include (whitelist)
            - 'exclude': Glob patterns for files to exclude (blacklist)
            - 'filter': Custom function(node, relpath) -> bool

        Skip strategies (applied to destination files):
            - 'never': Always copy (overwrite existing files) - default
            - 'exists': Skip if destination file exists (fastest)
            - 'size': Skip if destination exists and has same size (fast)
            - 'hash': Skip if destination exists and has same content/MD5 (accurate)
            - 'custom': Use custom skip function

        Args:
            dest: Destination node or path string
            include: Glob pattern(s) for files to include. If specified, only matching
                    files are copied (whitelist mode). Can be string or list of strings.
            exclude: Glob pattern(s) for files to exclude. Applied after include.
                    Can be string or list of strings.
            filter: Custom filter function(node, relative_path) -> bool.
                   Return True to include file, False to exclude.
                   Applied after include/exclude patterns.
            skip: Skip strategy (default: 'never' = always copy)
            skip_fn: Custom skip function(src, dest) -> bool (required if skip='custom')
            progress: Callback(current, total) called after each file
            on_file: Callback(src_node) called after each file copied
            on_skip: Callback(src_node, reason) called when file is skipped

        Returns:
            Destination StorageNode

        Raises:
            FileNotFoundError: If source doesn't exist
            ValueError: If skip='custom' but no skip_fn provided

        Examples:
            >>> # Simple copy (overwrite) - default behavior
            >>> src.copy(dest)
            >>>
            >>> # Copy only Python files
            >>> src.copy(dest, include='*.py')
            >>>
            >>> # Copy all except logs and temp files
            >>> src.copy(dest, exclude=['*.log', '*.tmp', '__pycache__/**'])
            >>>
            >>> # Combine include and exclude
            >>> src.copy(dest, include='*.py', exclude='test_*.py')
            >>>
            >>> # Custom filter: only files smaller than 10MB
            >>> src.copy(dest, filter=lambda node, path: node.size < 10_000_000)
            >>>
            >>> # Filter by modification time
            >>> from datetime import datetime, timedelta
            >>> cutoff = datetime.now() - timedelta(days=7)
            >>> src.copy(dest, filter=lambda n, p: n.mtime > cutoff.timestamp())
            >>>
            >>> # Combine filtering and skip strategy
            >>> src.copy(dest,
            ...          include=['*.py', '*.json'],
            ...          exclude='__pycache__/**',
            ...          skip='hash')  # Skip if content identical
            >>>
            >>> # Full-featured backup with tracking
            >>> src.copy(dest,
            ...          exclude=['*.log', '*.tmp', 'node_modules/**'],
            ...          filter=lambda n, p: n.size < 100_000_000,
            ...          skip='hash',
            ...          progress=lambda c, t: print(f"{c}/{t}"))

        Performance Notes:
            - Filtering is applied before copying (saves bandwidth)
            - skip='exists': ~1-2ms per file (only existence check)
            - skip='size': ~2-5ms per file (existence + size read)
            - skip='hash':
              * S3/GCS: ~5-10ms per file (ETag from metadata, fast)
              * Local: ~100ms per MB (must read file to compute MD5)

            For cloud storage, 'hash' is efficient due to ETag metadata.
            For local storage, 'size' is usually sufficient.

        Note:
            - Include/exclude patterns match against relative paths from source
            - If copying to base64 backend, destination path will be updated
            - Filtering is source-based (which files to copy)
            - Skip logic is destination-based (whether to overwrite)
        """
        # Convert string to StorageNode if needed
        if isinstance(dest, str):
            dest = self._manager.node(dest)

        # Virtual node: copy materialized content
        if self._is_virtual:
            # Read content and write to destination
            content = self._read_bytes()
            dest._write_bytes(content)
            return dest

        if not self.exists:
            raise FileNotFoundError(f"Source not found: {self.fullpath}")

        # Validate skip strategy
        if skip == 'custom' and skip_fn is None:
            raise ValueError("skip='custom' requires skip_fn parameter")

        # Normalize include/exclude patterns to lists
        include_patterns = []
        if include is not None:
            include_patterns = [include] if isinstance(include, str) else list(include)

        exclude_patterns = []
        if exclude is not None:
            exclude_patterns = [exclude] if isinstance(exclude, str) else list(exclude)

        # Check if we need enhanced copy (with skip/filter/callbacks)
        has_filters = bool(include_patterns or exclude_patterns or filter)
        needs_enhanced = skip != 'never' or progress or on_file or on_skip or has_filters

        if needs_enhanced:
            # Single file copy
            if self.isfile:
                # For single files, filters don't apply (no relative path context)
                return self._copy_file_with_skip(dest, skip, skip_fn, on_file, on_skip)

            # Directory copy (recursive with filtering)
            elif self.isdir:
                return self._copy_dir_with_skip(
                    dest, skip, skip_fn, progress, on_file, on_skip,
                    include_patterns, exclude_patterns, filter
                )

        # Simple copy without skip logic (backward compatible)
        else:
            # Copy via backends
            new_path = self._backend.copy(self._path, dest._backend, dest._path)

            # If destination backend returned a new path, update dest
            if new_path is not None:
                dest._path = new_path
                dest._posix_path = PurePosixPath(new_path) if new_path else PurePosixPath('.')

        return dest
    
    def move_to(self, dest: StorageNode | str) -> StorageNode:
        """Move file/directory to destination."""
        # Convert string to StorageNode if needed
        if isinstance(dest, str):
            dest = self._manager.node(dest)
        
        # Copy then delete
        self.copy_to(dest)
        self.delete()
        
        # Update self to point to new location
        self._mount_name = dest._mount_name
        self._path = dest._path
        self._posix_path = dest._posix_path
        self._backend = dest._backend
        
        return self

    # ==================== Virtual Node Methods ====================

    def append(self, node: StorageNode) -> None:
        """Append a node to this virtual node (iternode only).

        This method is only available for virtual nodes created with
        storage.iternode(). It adds a node reference to the accumulation list.
        Content is read lazily when materialized.

        Args:
            node: StorageNode to append

        Raises:
            ValueError: If not a virtual iternode

        Examples:
            >>> iternode = storage.iternode()
            >>> n1 = storage.node('mem:part1.txt')
            >>> iternode.append(n1)
            >>> content = iternode.read_text()  # Materializes here
        """
        if not self._is_virtual or self._virtual_type != 'iter':
            raise ValueError("append() is only available for iternode virtual nodes")
        self._sources.append(node)

    def extend(self, *nodes: StorageNode) -> None:
        """Extend this virtual node with multiple nodes (iternode only).

        This method is only available for virtual nodes created with
        storage.iternode(). It adds multiple node references to the accumulation list.
        Content is read lazily when materialized.

        Args:
            *nodes: StorageNodes to append

        Raises:
            ValueError: If not a virtual iternode

        Examples:
            >>> iternode = storage.iternode(n1)
            >>> iternode.extend(n2, n3, n4)
            >>> content = iternode.read_text()  # Materializes all
        """
        if not self._is_virtual or self._virtual_type != 'iter':
            raise ValueError("extend() is only available for iternode virtual nodes")
        self._sources.extend(nodes)

    def zip(self) -> bytes:
        """Create ZIP archive from node content.

        Behavior depends on node type:
        - Regular file: Creates ZIP containing that file
        - Regular directory: Creates ZIP with all files recursively
        - Virtual iternode: Creates ZIP with all accumulated nodes as separate files

        Returns:
            bytes: ZIP archive as bytes

        Raises:
            ValueError: If node doesn't exist (for regular nodes)

        Examples:
            >>> # ZIP a directory
            >>> docs = storage.node('home:documents')
            >>> zip_bytes = docs.zip()
            >>>
            >>> # ZIP accumulated files
            >>> iternode = storage.iternode(n1, n2, n3)
            >>> zip_bytes = iternode.zip()
            >>>
            >>> # Save ZIP
            >>> archive = storage.node('backup.zip')
            >>> archive.write_bytes(zip_bytes)
        """
        import zipfile
        import io

        buffer = io.BytesIO()

        with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            if self._is_virtual and self._virtual_type == 'iter':
                # Virtual iternode: add each source node as separate file
                for node in self._sources:
                    # Use basename as filename in ZIP
                    filename = node.basename if node.basename else 'file'
                    zf.writestr(filename, node._read_bytes())

            elif self.isfile:
                # Single file: add to ZIP
                zf.writestr(self.basename, self._read_bytes())

            elif self.isdir:
                # Directory: recursively add all files
                self._zip_directory(zf, self, '')

            else:
                raise ValueError(f"Cannot create ZIP: node doesn't exist or is invalid type")

        return buffer.getvalue()

    def _zip_directory(self, zf: 'zipfile.ZipFile', dir_node: StorageNode, arc_prefix: str) -> None:
        """Recursively add directory contents to ZIP.

        Args:
            zf: ZipFile object to write to
            dir_node: Directory node to process
            arc_prefix: Archive path prefix for this directory
        """
        for child in dir_node.children():
            # Build archive path
            arc_path = f"{arc_prefix}/{child.basename}" if arc_prefix else child.basename

            if child.isfile:
                # Add file to ZIP
                zf.writestr(arc_path, child._read_bytes())
            elif child.isdir:
                # Recurse into subdirectory
                self._zip_directory(zf, child, arc_path)

    # ==================== Directory Operations ====================
    
    def children(self) -> list[StorageNode]:
        """List child nodes (if directory)."""
        names = self._backend.list_dir(self._path)
        return [self.child(name) for name in names]
    
    def child(self, *parts: str) -> StorageNode:
        """Get a child node by path components.

        Args:
            *parts: Path components to append. Can be:
                - Single string with path separators: 'aaa/bbb/ccc'
                - Multiple strings: 'aaa', 'bbb', 'ccc'

        Returns:
            StorageNode: Child node with combined path

        Examples:
            >>> docs = storage.node('home:documents')
            >>>
            >>> # Single path string
            >>> report = docs.child('2024/reports/q4.pdf')
            >>>
            >>> # Multiple components
            >>> report = docs.child('2024', 'reports', 'q4.pdf')
            >>>
            >>> # Both produce: 'home:documents/2024/reports/q4.pdf'
        """
        # Join all parts into a single path
        child_path = '/'.join(parts)
        # Combine with current path
        full_child_path = str(self._posix_path / child_path)
        return StorageNode(self._manager, self._mount_name, full_child_path)
    
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

    def call(self, *args,
             callback: Callable[[], None] | None = None,
             async_mode: bool = False,
             return_output: bool = False,
             **subprocess_kwargs) -> str | None:
        """Execute external command with automatic local_path management.

        Automatically manages local filesystem paths for StorageNode arguments,
        downloading from cloud storage as needed and uploading changes after
        execution. Perfect for integrating with external tools like ffmpeg,
        imagemagick, pandoc, etc.

        Args:
            *args: Command arguments (str or StorageNode)
                   StorageNode arguments are automatically converted to local paths
            callback: Function to call on completion (async mode only)
            async_mode: Run in background thread (default: False)
            return_output: Return subprocess output as string (default: False)
            **subprocess_kwargs: Additional arguments passed to subprocess.run()
                                (e.g., cwd, env, timeout, shell, etc.)

        Returns:
            str | None: Command output if return_output=True, None otherwise
                       In async mode, returns immediately (None)

        Raises:
            subprocess.CalledProcessError: If command exits with non-zero status
            FileNotFoundError: If command executable not found

        Examples:
            >>> # Video conversion (cloud storage)
            >>> input_video = storage.node('s3:videos/input.mp4')
            >>> output_video = storage.node('s3:videos/output.mp4')
            >>> input_video.call('ffmpeg', '-i', input_video, '-vcodec', 'h264', output_video)
            >>> # Automatically downloads input, uploads output

            >>> # Image resize (local storage)
            >>> image = storage.node('home:photos/photo.jpg')
            >>> image.call('convert', image, '-resize', '800x600', image)

            >>> # With callback (async)
            >>> def on_complete():
            ...     print("Processing complete!")
            >>> video.call('ffmpeg', '-i', video, 'output.mp4',
            ...           callback=on_complete, async_mode=True)
            >>> # Returns immediately, callback called when done

            >>> # Capture output
            >>> pdf = storage.node('documents:report.pdf')
            >>> info = pdf.call('pdfinfo', pdf, return_output=True)
            >>> print(info)

            >>> # With subprocess options
            >>> script = storage.node('scripts:process.py')
            >>> script.call('python', script, 'arg1', 'arg2',
            ...            cwd='/tmp', timeout=60, env={'DEBUG': '1'})

        Notes:
            - StorageNode arguments use local_path(mode='rw') automatically
            - Files are downloaded before command execution
            - Modified files are uploaded after command execution
            - In async mode, cleanup happens in background thread
            - Use return_output=False for commands with large output
            - For shell commands, use shell=True in subprocess_kwargs
        """
        from contextlib import ExitStack
        import subprocess
        import threading

        def _execute():
            with ExitStack() as stack:
                cmd_args = []
                for arg in args:
                    if isinstance(arg, StorageNode):
                        # Automatically get local path for StorageNode
                        local_path = stack.enter_context(arg.local_path(mode='rw'))
                        cmd_args.append(local_path)
                    else:
                        cmd_args.append(str(arg))

                # Execute command
                if return_output:
                    result = subprocess.check_output(cmd_args, **subprocess_kwargs)
                    output = result.decode('utf-8') if isinstance(result, bytes) else result
                else:
                    subprocess.check_call(cmd_args, **subprocess_kwargs)
                    output = None

                # Call callback if provided
                if callback:
                    callback()

                return output

        if async_mode:
            # Run in background thread
            thread = threading.Thread(target=_execute)
            thread.daemon = True
            thread.start()
            return None
        else:
            # Run synchronously
            return _execute()

    def serve(self,
              environ: dict,
              start_response: callable,
              download: bool = False,
              download_name: str | None = None,
              cache_max_age: int | None = None) -> list[bytes]:
        """Serve file via WSGI interface with caching support.

        Serves the file through a WSGI application with:
        - ETag support for caching (304 Not Modified responses)
        - Content-Disposition headers for downloads
        - Cache-Control headers
        - Efficient streaming for large files

        Perfect for integrating storage with web frameworks like Flask, Django,
        Pyramid, or any WSGI application.

        Args:
            environ: WSGI environment dict (contains HTTP headers, request info)
            start_response: WSGI start_response callable
            download: If True, force download with Content-Disposition: attachment
            download_name: Custom filename for downloads (default: basename of file)
            cache_max_age: Cache-Control max-age in seconds (default: no caching)

        Returns:
            list[bytes]: Response body as list of byte chunks (WSGI response)

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageError: If file cannot be read

        Examples:
            >>> # Flask integration
            >>> from flask import Flask, request
            >>> app = Flask(__name__)
            >>>
            >>> @app.route('/files/<path:filepath>')
            >>> def serve_file(filepath):
            >>>     node = storage.node(f'uploads:{filepath}')
            >>>     return node.serve(request.environ, lambda s, h: None,
            >>>                       cache_max_age=3600)
            >>>
            >>> # Download endpoint
            >>> @app.route('/download/<path:filepath>')
            >>> def download_file(filepath):
            >>>     node = storage.node(f'uploads:{filepath}')
            >>>     return node.serve(request.environ, lambda s, h: None,
            >>>                       download=True,
            >>>                       download_name='report.pdf')
            >>>
            >>> # Plain WSGI application
            >>> def application(environ, start_response):
            >>>     path = environ['PATH_INFO']
            >>>     node = storage.node(f'static:{path}')
            >>>     if not node.exists:
            >>>         start_response('404 Not Found', [('Content-Type', 'text/plain')])
            >>>         return [b'Not Found']
            >>>     return node.serve(environ, start_response, cache_max_age=86400)

        Notes:
            - ETag is computed as "{mtime}-{size}" for efficient caching
            - Returns 304 Not Modified when client ETag matches
            - Uses local_path() for efficient cloud storage serving
            - Streams large files in chunks (doesn't load entire file in memory)
        """
        if not self.exists:
            start_response('404 Not Found', [('Content-Type', 'text/plain')])
            return [b'Not Found']

        # Check ETag for 304 Not Modified
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        if if_none_match:
            # Remove quotes from ETag
            if_none_match = if_none_match.replace('"', '')

            # Compute our ETag (mtime-size)
            mtime = self.mtime
            size = self.size
            our_etag = f"{mtime}-{size}"

            if our_etag == if_none_match:
                # Client has current version, return 304
                headers = [('ETag', f'"{our_etag}"')]
                start_response('304 Not Modified', headers)
                return [b'']

        # Build response headers
        headers = []

        # ETag for caching
        mtime = self.mtime
        size = self.size
        etag = f"{mtime}-{size}"
        headers.append(('ETag', f'"{etag}"'))

        # Content-Type
        headers.append(('Content-Type', self.mimetype))

        # Content-Length
        headers.append(('Content-Length', str(size)))

        # Content-Disposition (download)
        if download or download_name:
            filename = download_name or self.basename
            headers.append(('Content-Disposition', f'attachment; filename="{filename}"'))

        # Cache-Control
        if cache_max_age is not None:
            headers.append(('Cache-Control', f'max-age={cache_max_age}'))

        # Start response
        start_response('200 OK', headers)

        # Stream file content
        # Use local_path for efficient serving (downloads from cloud if needed)
        with self.local_path(mode='r') as local_path:
            # Read and stream in chunks
            chunk_size = 64 * 1024  # 64KB chunks
            chunks = []
            with open(local_path, 'rb') as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    chunks.append(chunk)
            return chunks

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

    def _resolve_version_index(self, index: int) -> str:
        """Resolve version index to version_id.

        Supports negative indexing like Python lists.

        Args:
            index: Version index
                -1 = latest (most recent)
                -2 = previous version
                0 = oldest version
                1 = second oldest

        Returns:
            version_id string

        Raises:
            IndexError: If index out of range
        """
        versions = self.versions

        if not versions:
            raise IndexError(f"No versions available for {self.fullpath}")

        try:
            # Python gestisce automaticamente indici negativi
            version_info = versions[index]
            return version_info['version_id']
        except IndexError:
            total = len(versions)
            raise IndexError(
                f"Version index {index} out of range. "
                f"Available versions: 0 to {total-1} or -1 to -{total}"
            )

    def _resolve_version_at_date(self, target_date: datetime) -> str | None:
        """Find version_id closest to (but not after) target_date.

        Args:
            target_date: Target datetime

        Returns:
            version_id or None if no version found before date
        """
        from datetime import timezone

        versions = self.versions

        # Normalize target_date to UTC if naive
        if target_date.tzinfo is None:
            target_date = target_date.replace(tzinfo=timezone.utc)

        # Filter versions up to target date
        valid_versions = [
            v for v in versions
            if v['last_modified'] <= target_date
        ]

        if not valid_versions:
            return None

        # Get the most recent version before target date
        target_version = max(
            valid_versions,
            key=lambda v: v['last_modified']
        )

        return target_version['version_id']

    def _list_supported_features(self) -> str:
        """Helper to list what this backend supports.

        Returns:
            Human-readable string of supported features
        """
        return str(self.capabilities)

    @property
    def version_count(self) -> int:
        """Get total number of versions available.

        Returns:
            int: Number of versions, or 0 if versioning not supported

        Examples:
            >>> print(f"File has {node.version_count} versions")
        """
        return len(self.versions)

    def compact_versions(self, dry_run: bool = False) -> int:
        """Compact version history by removing consecutive duplicates.

        Scans version history and removes versions that have identical content
        to the immediately preceding version. This cleans up unnecessary versions
        created by repeated writes of the same content, reducing storage costs.

        The rule: For each pair of consecutive versions with the same ETag,
        delete the second (more recent) one, keeping the first (older) one.

        Non-consecutive duplicates are preserved to maintain history
        (e.g., reverting to an earlier state).

        Args:
            dry_run: If True, only report what would be deleted without actually deleting

        Returns:
            int: Number of versions removed (or would be removed if dry_run=True)

        Raises:
            PermissionError: If versioning not supported

        Examples:
            >>> # Check what would be removed
            >>> count = node.compact_versions(dry_run=True)
            >>> print(f"Would remove {count} duplicate versions")

            >>> # Actually compact the history
            >>> removed = node.compact_versions()
            >>> print(f"Removed {removed} redundant versions")

        Notes:
            - Only works with backends that support versioning
            - Requires backend to support version deletion (S3)
            - Preserves the oldest of each duplicate pair
            - History of changes is maintained (non-consecutive duplicates kept)
            - Useful for reducing storage costs on versioned buckets

        Example scenario:
            v1: content A (etag: xxx)
            v2: content A (etag: xxx) ← REMOVED (consecutive duplicate)
            v3: content B (etag: yyy)
            v4: content B (etag: yyy) ← REMOVED (consecutive duplicate)
            v5: content A (etag: xxx) ← KEPT (not consecutive to v1, shows revert)
        """
        if not self.capabilities.versioning:
            raise PermissionError(
                f"{self._mount_name} backend does not support versioning"
            )

        versions = self.versions
        if len(versions) < 2:
            return 0  # Nothing to clean up

        # Sort by date (oldest first) to process chronologically
        sorted_versions = sorted(versions, key=lambda v: v['last_modified'])

        to_delete = []

        # Compare consecutive pairs
        for i in range(len(sorted_versions) - 1):
            current = sorted_versions[i]
            next_version = sorted_versions[i + 1]

            current_etag = current.get('etag', '')
            next_etag = next_version.get('etag', '')

            # If consecutive versions have same content, mark the newer one for deletion
            if current_etag and next_etag and current_etag == next_etag:
                to_delete.append(next_version['version_id'])

        if dry_run:
            return len(to_delete)

        # Delete marked versions
        deleted_count = 0
        for version_id in to_delete:
            try:
                self._backend.delete_version(self._path, version_id)
                deleted_count += 1
            except Exception as e:
                # Log but continue with other deletions
                import warnings
                warnings.warn(
                    f"Failed to delete version {version_id}: {e}",
                    RuntimeWarning
                )

        return deleted_count

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
        self._write_bytes(data)

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
        data = self._read_bytes()

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
