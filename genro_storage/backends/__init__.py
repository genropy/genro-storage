"""Backend implementations for genro-storage.

This package contains all storage backend implementations:
- Local: Local filesystem
- S3: Amazon S3
- GCS: Google Cloud Storage
- Azure: Azure Blob Storage
- HTTP: Read-only HTTP access
- Memory: In-memory storage for testing
- Base64: Inline base64-encoded data (data URI style)
- Relative: Hierarchical mount wrapper with permissions
"""

from .base import StorageBackend
from .local import LocalStorage
from .base64 import Base64Backend
from .relative import RelativeMountBackend

__all__ = [
    'StorageBackend',
    'LocalStorage',
    'Base64Backend',
    'RelativeMountBackend',
]
