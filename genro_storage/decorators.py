# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Decorators for genro-storage.

Contains:
- @apiready: Placeholder for future genro_core integration
- @smartsync: Unified sync/async API decorator
- SmartSync: Base class for sync/async mode control
"""

import asyncio
import functools
from typing import Callable, TypeVar, Any, Optional

T = TypeVar('T')


def apiready(obj_or_path=None, **kwargs):
    """No-op decorator placeholder for @apiready from genro_core.

    This is a temporary implementation that does nothing. It will be replaced
    by the actual decorator from genro_core.decorators.api when available.

    Usage:
        @apiready
        def method(self):
            pass

        @apiready(path="/storage")
        class MyClass:
            pass
    """

    def decorator(obj):
        return obj

    # If called without arguments (@apiready), obj_or_path is the decorated object
    if callable(obj_or_path):
        return obj_or_path

    # If called with arguments (@apiready(path="...")), return the decorator
    return decorator


class SmartSync:
    """Base class for unified sync/async API.

    Provides a single slot '_sync_mode' that controls whether async methods
    are wrapped with asyncio.run() or return coroutines.

    This is part of the 'smart' family of utilities (smartswitch, smartsync)
    that provide intelligent runtime behavior adaptation.

    Features:
    - Works with regular classes and __slots__
    - No global registry, no weakref, no cleanup needed
    - Minimal memory overhead (one slot per instance)
    - Clean inheritance pattern

    Usage:
        from genro_storage.decorators import SmartSync, smartsync

        class MyClass(SmartSync):
            def __init__(self, _sync: bool = False):
                SmartSync.__init__(self, _sync)

            @smartsync
            async def my_method(self):
                await asyncio.sleep(0.1)
                return "result"

        # Sync mode
        obj_sync = MyClass(_sync=True)
        result = obj_sync.my_method()  # No await needed!

        # Async mode
        obj_async = MyClass(_sync=False)
        result = await obj_async.my_method()  # Await required

    With __slots__:
        class MyClass(SmartSync):
            __slots__ = ('data',)  # NO __weakref__ needed!

            def __init__(self, _sync: bool = False):
                SmartSync.__init__(self, _sync)
                self.data = []

            @smartsync
            async def process(self):
                ...
    """
    __slots__ = ('_sync_mode',)

    def __init__(self, _sync: bool = False):
        """Initialize sync mode.

        Args:
            _sync: If True, async methods decorated with @smartsync
                   are wrapped with asyncio.run() and can be called
                   without await. If False (default), methods return
                   coroutines that must be awaited.
        """
        self._sync_mode = _sync


def smartsync(method):
    """Decorator for methods that work in both sync and async contexts.

    Part of the 'smart' family of utilities that provide intelligent
    runtime behavior adaptation. Automatically detects whether the code
    is running in an async or sync context and adapts accordingly.

    Features:
    - Auto-detection of sync/async context using asyncio.get_running_loop()
    - Asymmetric caching: caches True (async), always checks False (sync)
    - Enhanced error handling with clear messages
    - Works with both async and sync methods (sync methods are passed through)
    - No configuration needed - just apply the decorator

    How it works:
    - At import time: Checks if method is async using asyncio.iscoroutinefunction()
    - At runtime: Detects if running in async context (checks for event loop)
    - Asymmetric cache: Once async context is detected (True), it's cached forever
    - Sync context (False) is never cached, always re-checked
    - This allows transitioning from sync → async, but not async → sync (which is correct)

    Args:
        method: Method to decorate (async or sync)

    Returns:
        Wrapped function that works in both sync and async contexts

    Example:
        class StorageManager:
            @smartsync
            async def configure(self, mounts: list) -> None:
                # Implementation uses await
                await self._setup_mounts(mounts)

        # Sync usage - auto-detected
        manager = StorageManager()
        manager.configure([...])  # No await needed!

        # Async usage - auto-detected
        async def main():
            manager = StorageManager()
            await manager.configure([...])  # Await required
    """
    # Import time: Detect if method is async
    if asyncio.iscoroutinefunction(method):
        # Asymmetric cache: only cache True (async context found)
        _cached_has_loop = False

        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            nonlocal _cached_has_loop

            coro = method(self, *args, **kwargs)

            # If cache says True, use it (we're in async context)
            if _cached_has_loop:
                return coro

            # Otherwise, check current context
            try:
                asyncio.get_running_loop()
                # Found event loop! Cache it forever
                _cached_has_loop = True
                return coro
            except RuntimeError:
                # No event loop - sync context, execute with asyncio.run()
                # Don't cache False, always re-check next time
                try:
                    return asyncio.run(coro)
                except RuntimeError as e:
                    if "cannot be called from a running event loop" in str(e):
                        raise RuntimeError(
                            f"Cannot call {method.__name__}() synchronously from within "
                            f"an async context. Use 'await {method.__name__}()' instead."
                        ) from e
                    raise

        # Add cache reset method for testing
        def reset_cache():
            nonlocal _cached_has_loop
            _cached_has_loop = False

        wrapper._smartsync_reset_cache = reset_cache

        return wrapper
    else:
        # Sync method - no wrapping needed
        return method
