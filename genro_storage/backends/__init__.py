"""Backend implementations for genro-storage.

This package contains all storage backend implementations:
- Local: Local filesystem
- S3: Amazon S3
- GCS: Google Cloud Storage
- Azure: Azure Blob Storage
- HTTP: Read-only HTTP access
- Memory: In-memory storage for testing
"""

from .base import StorageBackend
from .local import LocalStorage

__all__ = [
    'StorageBackend',
    'LocalStorage',
]
