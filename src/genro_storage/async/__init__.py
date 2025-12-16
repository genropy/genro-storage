"""Async-first implementation of genro-storage (skeleton).

This module contains the skeleton async-native implementation:
- AsyncStorageManager: Storage configuration with SmartSwitch dispatch
- ProviderRegistry integration
- Methods with pass (no real implementation yet)
"""

from .manager import AsyncStorageManager

__all__ = [
    "AsyncStorageManager",
]
