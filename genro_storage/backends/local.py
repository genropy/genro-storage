"""Local filesystem backend for genro-storage.

This module implements the local filesystem storage backend using
Python's standard pathlib and file operations.
"""

from pathlib import Path
from typing import BinaryIO, TextIO
import shutil

from .base import StorageBackend


class LocalStorage(StorageBackend):
    """Local filesystem storage backend.
    
    This backend provides access to files on the local filesystem.
    All paths are relative to a configured base directory.
    
    Args:
        base_path: Absolute path to the base directory for this storage
    
    Raises:
        ValueError: If base_path is not absolute
        FileNotFoundError: If base_path doesn't exist
    
    Examples:
        >>> # Typically created via StorageManager configuration
        >>> backend = LocalStorage('/home/user')
        >>> 
        >>> # Access files relative to base
        >>> data = backend.read_bytes('documents/report.pdf')
    """
    
    def __init__(self, base_path: str):
        """Initialize LocalStorage backend.
        
        Args:
            base_path: Absolute path to base directory
        
        Raises:
            ValueError: If base_path is not absolute
            FileNotFoundError: If base_path doesn't exist
        """
        self.base_path = Path(base_path)
        
        if not self.base_path.is_absolute():
            raise ValueError(f"base_path must be absolute, got: {base_path}")
        
        if not self.base_path.exists():
            raise FileNotFoundError(f"Base path does not exist: {base_path}")
        
        if not self.base_path.is_dir():
            raise ValueError(f"Base path must be a directory: {base_path}")
    
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
    
    def __repr__(self) -> str:
        """String representation."""
        return f"LocalStorage('{self.base_path}')"
