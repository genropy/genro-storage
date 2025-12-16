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

"""Decorators for StorageNode (async and sync).

These decorators are candidates for extraction to genro-commons.
See temp/PATTERNS_FOR_COMMONS.md for details.
"""

import asyncio
import inspect
from functools import wraps
from typing import Callable, Any


def cacheable_property(func: Callable) -> property:
    """Property decorator with conditional caching (supports async).

    The property caches its value only if self._cached is True.
    Cache can be invalidated by deleting the cache attribute.
    Supports both sync and async properties.

    Usage:
        class MyClass:
            def __init__(self, cached=False):
                self._cached = cached

            @cacheable_property
            async def expensive_value(self):  # Async property
                return await expensive_computation()

            def invalidate_cache(self):
                for attr in list(vars(self).keys()):
                    if attr.startswith('_cache_'):
                        delattr(self, attr)

    NOTE: Candidate for genro-commons!
    """
    cache_attr = f"_cache_{func.__name__}"
    is_async = inspect.iscoroutinefunction(func)

    if is_async:

        @wraps(func)
        async def async_wrapper(self: Any) -> Any:
            # If caching is enabled and value is cached, return it
            if getattr(self, "_cached", False) and hasattr(self, cache_attr):
                return getattr(self, cache_attr)

            # Compute the value (await async function)
            value = await func(self)

            # If caching is enabled, save to cache
            if getattr(self, "_cached", False):
                setattr(self, cache_attr, value)

            return value

        return property(async_wrapper)
    else:

        @wraps(func)
        def sync_wrapper(self: Any) -> Any:
            # If caching is enabled and value is cached, return it
            if getattr(self, "_cached", False) and hasattr(self, cache_attr):
                return getattr(self, cache_attr)

            # Compute the value
            value = func(self)

            # If caching is enabled, save to cache
            if getattr(self, "_cached", False):
                setattr(self, cache_attr, value)

            return value

        return property(sync_wrapper)


def resolved(must_exist: bool | None = None, autocreate: bool = False) -> Callable:
    """Decorator for storage node methods with preconditions (supports async).

    This decorator handles:
    1. Checking file existence (must_exist)
    2. Auto-creating parent directories (autocreate)

    Supports both sync and async methods.

    Args:
        must_exist:
            - True: Always check file exists, raise FileNotFoundError if not
            - False: Never check existence
            - None: Auto-detect based on method name (read methods must exist)

        autocreate:
            - True: Create parent directories before write operations
            - False: Don't create parents (may fail if parent missing)

    The decorator can also read configuration from the instance:
        - self.must_exist: Default value for must_exist (if not overridden)
        - self.autocreate: Default value for autocreate
        - kwargs['parents']: Runtime override for autocreate

    Usage:
        class AsyncStorageNode:
            @resolved()  # Auto must_exist for read
            async def read(self):
                return await self.implementor.read_bytes(self.full_path)

            @resolved(autocreate=True)
            async def write(self, data, parents=True):
                return await self.implementor.write_bytes(self.full_path, data)

    NOTE: Candidate for genro-commons (generalized version)!
    """
    # Methods that typically require file to exist
    READ_METHODS = {
        "read",
        "read_bytes",
        "read_text",
        "open",
        "size",
        "mtime",
        "get_hash",
        "get_metadata",
    }

    # Methods that write/create files
    WRITE_METHODS = {"write", "write_bytes", "write_text"}

    def decorator(method: Callable) -> Callable:
        is_async = inspect.iscoroutinefunction(method)

        if is_async:

            @wraps(method)
            async def async_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                # 1. Determine if we should check existence
                should_check_exist = must_exist

                if should_check_exist is None:
                    # Auto-detect: read methods need file to exist
                    method_name = method.__name__
                    if method_name in READ_METHODS:
                        should_check_exist = True
                    else:
                        # Check instance attribute if available
                        should_check_exist = getattr(self, "must_exist", False)

                # Check existence if required (await async property)
                if should_check_exist:
                    exists = await self.exists
                    if not exists:
                        raise FileNotFoundError(f"File not found: {self.mount_point}:{self.path}")

                # 2. Determine if we should create parent directories
                # For write methods: check kwargs['parents'] > self.autocreate > decorator autocreate
                method_name = method.__name__
                if method_name in WRITE_METHODS:
                    # Priority: kwargs > instance attribute > decorator parameter
                    should_create = kwargs.get("parents")
                    if should_create is None:
                        should_create = getattr(self, "autocreate", autocreate)

                    parent_path = self._get_parent_path()
                    if parent_path:
                        if should_create:
                            # Create parent directory (await async)
                            await self.implementor.mkdir(parent_path, parents=True, exist_ok=True)
                        else:
                            # Verify parent exists (some backends like memory auto-create)
                            parent_exists = await self.implementor.exists(parent_path)
                            if not parent_exists:
                                raise FileNotFoundError(
                                    f"Parent directory not found: {parent_path}"
                                )

                # 3. Execute the method (await async)
                return await method(self, *args, **kwargs)

            return async_wrapper
        else:

            @wraps(method)
            def sync_wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
                # 1. Determine if we should check existence
                should_check_exist = must_exist

                if should_check_exist is None:
                    # Auto-detect: read methods need file to exist
                    method_name = method.__name__
                    if method_name in READ_METHODS:
                        should_check_exist = True
                    else:
                        # Check instance attribute if available
                        should_check_exist = getattr(self, "must_exist", False)

                # Check existence if required (sync property)
                if should_check_exist:
                    if not self.exists:
                        raise FileNotFoundError(f"File not found: {self.mount_point}:{self.path}")

                # 2. Determine if we should create parent directories
                # For write methods: check kwargs['parents'] > self.autocreate > decorator autocreate
                method_name = method.__name__
                if method_name in WRITE_METHODS:
                    # Priority: kwargs > instance attribute > decorator parameter
                    should_create = kwargs.get("parents")
                    if should_create is None:
                        should_create = getattr(self, "autocreate", autocreate)

                    parent_path = self._get_parent_path()
                    if parent_path:
                        if should_create:
                            # Create parent directory (sync)
                            self.implementor.mkdir(parent_path, parents=True, exist_ok=True)
                        else:
                            # Verify parent exists (some backends like memory auto-create)
                            if not self.implementor.exists(parent_path):
                                raise FileNotFoundError(
                                    f"Parent directory not found: {parent_path}"
                                )

                # 3. Execute the method (sync)
                return method(self, *args, **kwargs)

            return sync_wrapper

    return decorator
