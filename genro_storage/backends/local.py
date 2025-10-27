"""Local filesystem backend for genro-storage.

This module implements the local filesystem storage backend using
Python's standard pathlib and file operations.
"""

from __future__ import annotations

from pathlib import Path
from typing import BinaryIO, TextIO, Callable, Union
import shutil

from .base import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem storage backend.

    This backend provides access to files on the local filesystem.
    All paths are relative to a configured base directory.

    The base_path can be either a string or a callable that returns a string.
    When a callable is provided, it will be evaluated each time the base_path
    property is accessed, allowing for dynamic paths (e.g., user-specific directories).

    Args:
        path: Absolute path to the base directory, or callable returning path

    Raises:
        ValueError: If resolved path is not absolute or not a directory
        FileNotFoundError: If resolved path doesn't exist

    Examples:
        >>> # Static path
        >>> backend = LocalStorage('/home/user')
        >>>
        >>> # Dynamic path with callable
        >>> def get_user_dir():
        ...     user_id = get_current_user()
        ...     return f'/data/users/{user_id}'
        >>> backend = LocalStorage(get_user_dir)
        >>>
        >>> # Access files relative to base
        >>> data = backend.read_bytes('documents/report.pdf')
    """

    def __init__(self, path: Union[str, Callable[[], str]]):
        """Initialize LocalStorage backend.

        Args:
            path: Absolute path or callable returning absolute path

        Raises:
            ValueError: If path (string only) is not absolute or not a directory
            FileNotFoundError: If path (string only) doesn't exist

        Note:
            When path is a callable, validation is deferred until first access.
            This allows configuration before the context (e.g., current user) is available.
        """
        self._path_or_callable = path

        # Validate immediately only if path is a string (not callable)
        if not callable(path):
            resolved = Path(path).resolve()
            if not Path(path).is_absolute():
                raise ValueError(f"base_path must be absolute, got: {path}")

            if not resolved.exists():
                raise FileNotFoundError(f"Base path does not exist: {path}")

            if not resolved.is_dir():
                raise ValueError(f"Base path must be a directory: {path}")

    def _resolve_base_path(self) -> Path:
        """Resolve base path (evaluating callable if necessary).

        Returns:
            Resolved base path as Path object
        """
        if callable(self._path_or_callable):
            path_str = self._path_or_callable()
        else:
            path_str = self._path_or_callable

        return Path(path_str).resolve()

    @property
    def base_path(self) -> Path:
        """Get current base path (evaluates callable if needed).

        Returns:
            Current base path as Path object
        """
        return self._resolve_base_path()
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a relative path to absolute filesystem path.
        
        Args:
            path: Relative path within this storage
        
        Returns:
            Path: Absolute filesystem path
        
        Raises:
            ValueError: If path tries to escape base_path
        """
        if not path:
            return self.base_path
        
        full_path = (self.base_path / path).resolve()
        
        # Security check: ensure path doesn't escape base_path
        try:
            full_path.relative_to(self.base_path)
        except ValueError:
            raise ValueError(
                f"Path escapes base directory: {path} "
                f"(resolved to {full_path}, base is {self.base_path})"
            )
        
        return full_path
    
    def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        return self._resolve_path(path).exists()
    
    def is_file(self, path: str) -> bool:
        """Check if path points to a file."""
        return self._resolve_path(path).is_file()
    
    def is_dir(self, path: str) -> bool:
        """Check if path points to a directory."""
        return self._resolve_path(path).is_dir()
    
    def size(self, path: str) -> int:
        """Get file size in bytes."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        if full_path.is_dir():
            raise ValueError(f"Path is a directory, not a file: {path}")
        
        return full_path.stat().st_size
    
    def mtime(self, path: str) -> float:
        """Get last modification time."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"Path not found: {path}")
        
        return full_path.stat().st_mtime
    
    def open(self, path: str, mode: str = 'rb') -> BinaryIO | TextIO:
        """Open file and return file-like object."""
        full_path = self._resolve_path(path)
        
        # Ensure parent directory exists for write modes
        if any(m in mode for m in ['w', 'a', 'x']):
            full_path.parent.mkdir(parents=True, exist_ok=True)
        
        return open(full_path, mode)
    
    def read_bytes(self, path: str) -> bytes:
        """Read entire file as bytes."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        return full_path.read_bytes()
    
    def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read entire file as text."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {path}")
        
        return full_path.read_text(encoding=encoding)
    
    def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        full_path = self._resolve_path(path)
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        full_path.write_bytes(data)
    
    def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        """Write text to file."""
        full_path = self._resolve_path(path)
        
        # Ensure parent directory exists
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        full_path.write_text(text, encoding=encoding)
    
    def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            # Idempotent - no error if doesn't exist
            return
        
        if full_path.is_file():
            full_path.unlink()
        elif full_path.is_dir():
            if recursive:
                shutil.rmtree(full_path)
            else:
                # Check if directory is empty
                if any(full_path.iterdir()):
                    raise ValueError(
                        f"Directory is not empty: {path}. "
                        f"Use recursive=True to delete recursively."
                    )
                full_path.rmdir()
    
    def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        full_path = self._resolve_path(path)
        
        if not full_path.exists():
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not full_path.is_dir():
            raise ValueError(f"Path is not a directory: {path}")
        
        return [item.name for item in full_path.iterdir()]
    
    def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        full_path = self._resolve_path(path)
        
        if full_path.exists() and not exist_ok:
            raise FileExistsError(f"Directory already exists: {path}")
        
        full_path.mkdir(parents=parents, exist_ok=exist_ok)
    
    def copy(self, src_path: str, dest_backend: StorageBackend, dest_path: str) -> None:
        """Copy file/directory to another backend.

        For local-to-local copies, uses efficient filesystem operations.
        For copies to other backends, streams the data.
        """
        src_full = self._resolve_path(src_path)

        if not src_full.exists():
            raise FileNotFoundError(f"Source not found: {src_path}")

        if src_full.is_file():
            # Copy single file
            if isinstance(dest_backend, LocalStorage):
                # Local-to-local: use shutil for efficiency
                dest_full = dest_backend._resolve_path(dest_path)
                dest_full.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_full, dest_full)
            else:
                # To other backend: stream via read/write
                data = self.read_bytes(src_path)
                dest_backend.write_bytes(dest_path, data)

        elif src_full.is_dir():
            # Copy directory recursively
            dest_backend.mkdir(dest_path, parents=True, exist_ok=True)

            for item in src_full.iterdir():
                item_rel_path = f"{src_path}/{item.name}" if src_path else item.name
                dest_item_path = f"{dest_path}/{item.name}" if dest_path else item.name
                self.copy(item_rel_path, dest_backend, dest_item_path)

    def local_path(self, path: str, mode: str = 'r'):
        """Get local filesystem path (returns the actual path).

        For local storage, this simply returns the actual filesystem path
        since the file is already local. No temporary copy is needed.

        Args:
            path: Relative path to file
            mode: Access mode (ignored for local storage)

        Returns:
            Context manager yielding str (the actual filesystem path)

        Examples:
            >>> with backend.local_path('video.mp4') as local_path:
            ...     subprocess.run(['ffmpeg', '-i', local_path, 'out.mp4'])
        """
        from contextlib import contextmanager

        @contextmanager
        def _local_path():
            full_path = self._resolve_path(path)
            yield str(full_path)

        return _local_path()
    
    def __repr__(self) -> str:
        """String representation."""
        return f"LocalStorage('{self.base_path}')"
