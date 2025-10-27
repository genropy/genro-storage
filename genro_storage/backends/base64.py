"""Base64 backend for inline data storage.

This backend allows embedding content directly in the URI as base64-encoded data.
It's useful for small amounts of data that need to be stored inline, similar to data URIs.

Example:
    storage.configure([{'name': 'b64', 'type': 'base64'}])

    # Read inline base64 data
    node = storage.node('b64:SGVsbG8gV29ybGQ=')  # "Hello World" in base64
    content = node.read_text()  # Returns "Hello World"

    # Also works with binary data
    node = storage.node('b64:iVBORw0KGgo...')  # PNG image in base64
    data = node.read_bytes()

Note:
    This backend is read-only by design. Write operations will raise PermissionError.
    The "path" is the base64-encoded content itself.
"""

import base64
import hashlib
import io
import time
from typing import BinaryIO, TextIO

from .base import StorageBackend
from ..exceptions import StorageError


class Base64Backend(StorageBackend):
    """Storage backend that decodes base64 data from the path/URI.

    This backend treats the path as base64-encoded data and provides read-only
    access to the decoded content. It's useful for embedding small amounts of
    data directly in URIs without requiring actual file storage.

    Attributes:
        _creation_time: Fixed timestamp for mtime() calls
    """

    def __init__(self) -> None:
        """Initialize the Base64 backend."""
        self._creation_time = time.time()

    def _decode(self, path: str) -> bytes:
        """Decode base64 path to bytes.

        Args:
            path: Base64-encoded string

        Returns:
            Decoded bytes

        Raises:
            FileNotFoundError: If path is empty or invalid base64
        """
        if not path:
            raise FileNotFoundError("Base64 path cannot be empty")

        try:
            # Remove whitespace and decode
            clean_path = path.strip().replace(' ', '').replace('\n', '')
            return base64.b64decode(clean_path, validate=True)
        except Exception as e:
            raise FileNotFoundError(f"Invalid base64 data: {e}") from e

    def _is_valid_base64(self, path: str) -> bool:
        """Check if path is valid base64.

        Args:
            path: String to validate

        Returns:
            True if valid base64, False otherwise
        """
        if not path or not path.strip():
            return False

        try:
            clean_path = path.strip().replace(' ', '').replace('\n', '')
            base64.b64decode(clean_path, validate=True)
            return True
        except Exception:
            return False

    def exists(self, path: str) -> bool:
        """Check if the base64 data is valid.

        Args:
            path: Base64-encoded string

        Returns:
            True if valid base64, False otherwise
        """
        return self._is_valid_base64(path)

    def is_file(self, path: str) -> bool:
        """Check if path is a valid base64 file.

        Args:
            path: Base64-encoded string

        Returns:
            True if valid base64 (treated as a file)
        """
        return self._is_valid_base64(path)

    def is_dir(self, path: str) -> bool:
        """Check if path is a directory.

        Args:
            path: Base64-encoded string

        Returns:
            Always False (base64 backend has no directories)
        """
        return False

    def size(self, path: str) -> int:
        """Get size of decoded data in bytes.

        Args:
            path: Base64-encoded string

        Returns:
            Size of decoded data

        Raises:
            FileNotFoundError: If invalid base64
        """
        data = self._decode(path)
        return len(data)

    def mtime(self, path: str) -> float:
        """Get modification time.

        Args:
            path: Base64-encoded string

        Returns:
            Fixed timestamp (base64 data has no modification time)

        Raises:
            FileNotFoundError: If invalid base64
        """
        # Verify it's valid base64
        self._decode(path)
        return self._creation_time

    def open(self, path: str, mode: str = 'rb') -> BinaryIO | TextIO:
        """Open base64 data as file-like object.

        Args:
            path: Base64-encoded string (ignored for write modes)
            mode: Open mode ('rb', 'r', 'wb', 'w', 'ab', 'a')

        Returns:
            File-like object (BytesIO or StringIO)

        Raises:
            FileNotFoundError: If invalid base64 (read modes only)

        Note:
            Write modes return empty BytesIO/StringIO. The caller must handle
            retrieving the content and calling write_bytes/write_text to get
            the new base64 path.
        """
        # Write modes: return empty buffer
        if 'w' in mode or 'a' in mode or '+' in mode:
            if 'b' in mode:
                return io.BytesIO()
            else:
                return io.StringIO()

        # Read modes: decode existing data
        data = self._decode(path)

        if 'b' in mode:
            return io.BytesIO(data)
        else:
            # Text mode
            encoding = 'utf-8'  # Could be made configurable
            text = data.decode(encoding)
            return io.StringIO(text)

    def read_bytes(self, path: str) -> bytes:
        """Read and decode base64 data.

        Args:
            path: Base64-encoded string

        Returns:
            Decoded bytes

        Raises:
            FileNotFoundError: If invalid base64
        """
        return self._decode(path)

    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read and decode base64 data as text.

        Args:
            path: Base64-encoded string
            encoding: Text encoding (default: utf-8)

        Returns:
            Decoded text string

        Raises:
            FileNotFoundError: If invalid base64
            UnicodeDecodeError: If data is not valid text
        """
        data = self._decode(path)
        return data.decode(encoding)

    def write_bytes(self, path: str, data: bytes) -> str:
        """Write bytes to base64 node.

        Creates a new base64-encoded string from the data. The path parameter
        is ignored as the base64 content itself becomes the new path.

        Args:
            path: Ignored (base64 backend is pathless)
            data: Bytes to encode

        Returns:
            str: New base64-encoded path

        Note:
            This operation changes the node's path to the new base64 string.
            The old path becomes invalid.

        Examples:
            >>> new_path = backend.write_bytes("old", b"Hello")
            >>> # new_path is now "SGVsbG8=" (base64 of "Hello")
        """
        return base64.b64encode(data).decode()

    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> str:
        """Write text to base64 node.

        Creates a new base64-encoded string from the text. The path parameter
        is ignored as the base64 content itself becomes the new path.

        Args:
            path: Ignored (base64 backend is pathless)
            text: String to encode
            encoding: Text encoding (default: utf-8)

        Returns:
            str: New base64-encoded path

        Note:
            This operation changes the node's path to the new base64 string.
            The old path becomes invalid.

        Examples:
            >>> new_path = backend.write_text("old", "Hello World")
            >>> # new_path is now "SGVsbG8gV29ybGQ=" (base64 of "Hello World")
        """
        data = text.encode(encoding)
        return base64.b64encode(data).decode()

    def delete(self, path: str, recursive: bool = False) -> None:
        """Delete operation not supported.

        Args:
            path: Unused
            recursive: Unused

        Raises:
            PermissionError: Always (read-only backend)
        """
        raise PermissionError("Base64 backend is read-only")

    def list_dir(self, path: str) -> list[str]:
        """List directory contents.

        Args:
            path: Base64-encoded string

        Returns:
            Empty list

        Raises:
            ValueError: Always (no directories in base64 backend)
        """
        raise ValueError("Base64 backend has no directory structure")

    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory operation not supported.

        Args:
            path: Unused
            parents: Unused
            exist_ok: Unused

        Raises:
            PermissionError: Always (read-only backend)
        """
        raise PermissionError("Base64 backend is read-only")

    def copy(self, src_path: str, dest_backend: 'StorageBackend', dest_path: str) -> str | None:
        """Copy base64 data to another backend.

        This decodes the base64 data and writes it to the destination backend.

        Args:
            src_path: Base64-encoded source data
            dest_backend: Destination backend
            dest_path: Destination path

        Returns:
            str | None: New destination path if destination backend changes it,
                       or None if path unchanged

        Raises:
            FileNotFoundError: If invalid base64
        """
        data = self._decode(src_path)
        result = dest_backend.write_bytes(dest_path, data)
        # Return the result from destination backend's write
        # (base64 returns new path, others return None)
        return result

    def get_hash(self, path: str) -> str | None:
        """Get MD5 hash of decoded data.

        Args:
            path: Base64-encoded string

        Returns:
            MD5 hash of decoded data

        Raises:
            FileNotFoundError: If invalid base64
        """
        data = self._decode(path)
        return hashlib.md5(data).hexdigest()

    def local_path(self, path: str, mode: str = 'r'):
        """Get local filesystem path for base64 data.

        Creates a temporary file with the decoded base64 content.
        Since Base64Backend is read-only, write modes are not supported.

        Args:
            path: Base64-encoded string
            mode: Access mode (only 'r' is supported)

        Returns:
            Context manager yielding str (temp file path)

        Raises:
            PermissionError: If mode is not 'r'
            FileNotFoundError: If invalid base64

        Examples:
            >>> # Use base64 data with external tool
            >>> node = storage.node('b64:SGVsbG8gV29ybGQ=')
            >>> with node.local_path() as path:
            ...     subprocess.run(['cat', path])
        """
        import tempfile
        import os
        from contextlib import contextmanager

        if mode != 'r':
            raise PermissionError(
                f"Base64 backend is read-only. Only mode='r' is supported, got '{mode}'"
            )

        @contextmanager
        def _local_path():
            # Decode data
            data = self._decode(path)

            # Create temp file
            with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name

            try:
                yield tmp_path
            finally:
                # Cleanup
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

        return _local_path()
