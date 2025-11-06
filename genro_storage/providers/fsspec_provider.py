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

"""Async fsspec-based provider for genro-storage.

This module provides async storage backends using the fsspec library,
supporting multiple protocols including S3 (AWS and MinIO), GCS,
Azure, HTTP, and many more.

Architecture:
- AsyncProvider: Factory that defines protocols and returns (Model, Implementor, capabilities)
- Model: Pydantic model for configuration validation
- AsyncImplementor: Async adapter that wraps fsspec async filesystem
- StorageManager passes full paths to Implementor (no base_path inside Implementor)
"""

from __future__ import annotations

import tempfile
import os
import asyncio
from pathlib import PurePosixPath
from typing import Any, TYPE_CHECKING

import fsspec
from pydantic import BaseModel, Field, field_validator

from .base import AsyncProvider, AsyncImplementor

if TYPE_CHECKING:
    pass


class FsspecProvider(AsyncProvider):
    """Async provider for fsspec-based storage backends.

    Supports multiple protocols:
    - s3_aws: Amazon S3 with AWS configuration
    - s3_minio: MinIO (S3-compatible, no region)
    - gcs: Google Cloud Storage
    - local: Local filesystem
    - memory: In-memory filesystem (testing)
    """

    @AsyncProvider.protocol('s3_aws')
    def protocol_s3_aws(self) -> dict[str, Any]:
        """Amazon S3 protocol with AWS-specific configuration."""

        class S3AwsModel(BaseModel):
            """Configuration for Amazon S3."""
            bucket: str = Field(..., description="S3 bucket name")
            region: str = Field(..., description="AWS region (e.g., 'us-east-1')")
            access_key: str | None = Field(None, description="AWS access key ID")
            secret_key: str | None = Field(None, description="AWS secret access key")
            session_token: str | None = Field(None, description="AWS session token")
            endpoint_url: str | None = Field(None, description="Custom S3 endpoint URL")
            anon: bool = Field(False, description="Anonymous access (public buckets)")
            version_aware: bool = Field(True, description="Enable versioning support")

            @field_validator('bucket')
            @classmethod
            def validate_bucket(cls, v: str) -> str:
                if not v or not v.strip():
                    raise ValueError("Bucket name cannot be empty")
                return v.strip()

        class S3AwsImplementor(AsyncFsspecImplementor):
            """Async implementor for Amazon S3."""

            def __init__(self, config: S3AwsModel):
                fs_kwargs = {
                    'version_aware': config.version_aware,
                    'anon': config.anon,
                    'asynchronous': True,  # IMPORTANT: Enable async mode
                }

                if config.access_key:
                    fs_kwargs['key'] = config.access_key
                if config.secret_key:
                    fs_kwargs['secret'] = config.secret_key
                if config.session_token:
                    fs_kwargs['token'] = config.session_token
                if config.endpoint_url:
                    fs_kwargs['endpoint_url'] = config.endpoint_url
                if config.region:
                    fs_kwargs['region_name'] = config.region

                super().__init__(
                    config=config,
                    protocol='s3',
                    root_path=config.bucket,
                    **fs_kwargs
                )

        return {
            'model': S3AwsModel,
            'implementor': S3AwsImplementor,
            'capabilities': [
                'read', 'write', 'delete', 'list',
                'metadata', 'versioning', 'hash'
            ]
        }

    @AsyncProvider.protocol('s3_minio')
    def protocol_s3_minio(self) -> dict[str, Any]:
        """MinIO protocol (S3-compatible, no region required)."""

        class S3MinioModel(BaseModel):
            """Configuration for MinIO."""
            bucket: str = Field(..., description="Bucket name")
            endpoint_url: str = Field(..., description="MinIO endpoint URL")
            access_key: str = Field(..., description="MinIO access key")
            secret_key: str = Field(..., description="MinIO secret key")
            anon: bool = Field(False, description="Anonymous access")
            version_aware: bool = Field(False, description="Enable versioning")

            @field_validator('bucket')
            @classmethod
            def validate_bucket(cls, v: str) -> str:
                if not v or not v.strip():
                    raise ValueError("Bucket name cannot be empty")
                return v.strip()

        class S3MinioImplementor(AsyncFsspecImplementor):
            """Async implementor for MinIO."""

            def __init__(self, config: S3MinioModel):
                fs_kwargs = {
                    'key': config.access_key,
                    'secret': config.secret_key,
                    'endpoint_url': config.endpoint_url,
                    'version_aware': config.version_aware,
                    'anon': config.anon,
                    'asynchronous': True,
                }

                super().__init__(
                    config=config,
                    protocol='s3',
                    root_path=config.bucket,
                    **fs_kwargs
                )

        return {
            'model': S3MinioModel,
            'implementor': S3MinioImplementor,
            'capabilities': [
                'read', 'write', 'delete', 'list',
                'metadata', 'versioning', 'hash'
            ]
        }

    @AsyncProvider.protocol('gcs')
    def protocol_gcs(self) -> dict[str, Any]:
        """Google Cloud Storage protocol."""

        class GcsModel(BaseModel):
            """Configuration for Google Cloud Storage."""
            bucket: str = Field(..., description="GCS bucket name")
            project: str | None = Field(None, description="GCP project ID")
            token: str | None = Field(None, description="Path to service account JSON")
            consistency: str = Field('md5', description="Consistency check method")

            @field_validator('bucket')
            @classmethod
            def validate_bucket(cls, v: str) -> str:
                if not v or not v.strip():
                    raise ValueError("Bucket name cannot be empty")
                return v.strip()

        class GcsImplementor(AsyncFsspecImplementor):
            """Async implementor for Google Cloud Storage."""

            def __init__(self, config: GcsModel):
                fs_kwargs = {
                    'consistency': config.consistency,
                    'asynchronous': True,
                }

                if config.project:
                    fs_kwargs['project'] = config.project
                if config.token:
                    fs_kwargs['token'] = config.token

                super().__init__(
                    config=config,
                    protocol='gcs',
                    root_path=config.bucket,
                    **fs_kwargs
                )

        return {
            'model': GcsModel,
            'implementor': GcsImplementor,
            'capabilities': [
                'read', 'write', 'delete', 'list',
                'metadata', 'hash'
            ]
        }

    @AsyncProvider.protocol('local')
    def protocol_local(self) -> dict[str, Any]:
        """Local filesystem protocol."""

        class LocalModel(BaseModel):
            """Configuration for local filesystem."""
            root_path: str = Field(..., description="Root directory path")

            @field_validator('root_path')
            @classmethod
            def validate_root_path(cls, v: str) -> str:
                if not v or not v.strip():
                    raise ValueError("Root path cannot be empty")
                path = os.path.expanduser(v.strip())
                if not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                return path

        class LocalImplementor(AsyncFsspecImplementor):
            """Async implementor for local filesystem."""

            def __init__(self, config: LocalModel):
                super().__init__(
                    config=config,
                    protocol='file',
                    root_path=config.root_path,
                    asynchronous=True,
                    auto_mkdir=True
                )

        return {
            'model': LocalModel,
            'implementor': LocalImplementor,
            'capabilities': [
                'read', 'write', 'delete', 'list'
            ]
        }

    @AsyncProvider.protocol('memory')
    def protocol_memory(self) -> dict[str, Any]:
        """In-memory filesystem protocol (for testing)."""

        class MemoryModel(BaseModel):
            """Configuration for in-memory filesystem."""
            pass  # No configuration needed

        class MemoryImplementor(AsyncFsspecImplementor):
            """Async implementor for in-memory filesystem."""

            def __init__(self, config: MemoryModel):
                super().__init__(
                    config=config,
                    protocol='memory',
                    root_path='',
                    asynchronous=True
                )

        return {
            'model': MemoryModel,
            'implementor': MemoryImplementor,
            'capabilities': [
                'read', 'write', 'delete', 'list'
            ]
        }


class AsyncLocalPathContext:
    """Async context manager for local filesystem path access.

    For local storage: returns direct path
    For remote storage: downloads to temp, uploads on exit
    """

    def __init__(self, implementor: AsyncFsspecImplementor, path: str, mode: str):
        """Initialize context manager.

        Args:
            implementor: AsyncFsspecImplementor instance
            path: Full path (from _make_path)
            mode: Access mode ('r', 'w', 'rw')
        """
        self.implementor = implementor
        self.path = path
        self.mode = mode
        self.fs_path = implementor._make_path(path)
        self.tmp_path = None
        self.is_local = implementor.protocol == 'file'

    async def __aenter__(self) -> str:
        """Enter context: setup local path."""
        if self.is_local:
            # Local filesystem: return direct path
            return self.fs_path

        # Remote filesystem: use temp file
        self.tmp_path = self._create_temp_file()

        # Download if reading
        if 'r' in self.mode:
            await self._download_if_exists()

        return self.tmp_path

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context: cleanup and upload if needed."""
        if exc_type is not None:
            self._cleanup_temp()
            return False

        # Upload if writing
        if 'w' in self.mode and self.tmp_path:
            await self._upload_if_exists()

        self._cleanup_temp()
        return False

    def _create_temp_file(self) -> str:
        """Create temporary file with same extension."""
        suffix = os.path.splitext(self.path)[1]
        tmp = tempfile.NamedTemporaryFile(mode='w+b', suffix=suffix, delete=False)
        tmp.close()
        return tmp.name

    async def _download_if_exists(self) -> None:
        """Download remote file to temp if it exists."""
        exists = await self.implementor.fs._exists(self.fs_path)
        if not exists:
            return

        data = await self.implementor.fs._cat(self.fs_path)
        with open(self.tmp_path, 'wb') as f:
            f.write(data)

    async def _upload_if_exists(self) -> None:
        """Upload temp file to remote if it exists."""
        if not os.path.exists(self.tmp_path):
            return

        # Ensure parent directory exists
        parent = str(PurePosixPath(self.fs_path).parent)
        if parent and parent != '.':
            await self.implementor.fs._makedirs(parent, exist_ok=True)

        with open(self.tmp_path, 'rb') as f:
            data = f.read()
        await self.implementor.fs._pipe(self.fs_path, data)

    def _cleanup_temp(self) -> None:
        """Remove temp file if it exists."""
        if self.tmp_path and os.path.exists(self.tmp_path):
            os.unlink(self.tmp_path)


class AsyncFsspecImplementor(AsyncImplementor):
    """Base async implementor for fsspec-based storage.

    This is a pure async protocol wrapper:
    - Receives full paths from StorageManager
    - No path manipulation (StorageManager handles base_path)
    - Wraps fsspec async filesystem operations
    """

    def __init__(
        self,
        config: BaseModel,
        protocol: str,
        root_path: str,
        **fs_kwargs: Any
    ):
        """Initialize async fsspec implementor.

        Args:
            config: Validated Pydantic configuration model
            protocol: Fsspec protocol name (e.g., 's3', 'gcs', 'file')
            root_path: Root path (bucket name, directory, etc.)
            **fs_kwargs: Additional arguments for fsspec.filesystem()
        """
        super().__init__(config)
        self.protocol = protocol
        self.root_path = root_path
        self.fs_kwargs = fs_kwargs

        # Create async fsspec filesystem instance
        # IMPORTANT: asynchronous=True must be in fs_kwargs
        self.fs = fsspec.filesystem(protocol, **fs_kwargs)

    def _make_path(self, path: str) -> str:
        """Combine root_path with path from StorageManager.

        Args:
            path: Path from StorageManager (already includes base_path)

        Returns:
            Full path for fsspec
        """
        if not path:
            return self.root_path

        clean = path.lstrip('/')

        if self.root_path:
            return f"{self.root_path}/{clean}"

        return clean

    # Core async operations

    async def exists(self, path: str) -> bool:
        """Check if file or directory exists."""
        fs_path = self._make_path(path)
        return await self.fs._exists(fs_path)

    async def is_file(self, path: str) -> bool:
        """Check if path is a file."""
        fs_path = self._make_path(path)
        try:
            info = await self.fs._info(fs_path)
            return info['type'] == 'file'
        except FileNotFoundError:
            return False

    async def is_dir(self, path: str) -> bool:
        """Check if path is a directory."""
        fs_path = self._make_path(path)
        try:
            info = await self.fs._info(fs_path)
            return info['type'] == 'directory'
        except FileNotFoundError:
            return False

    async def size(self, path: str) -> int:
        """Get file size in bytes."""
        fs_path = self._make_path(path)
        info = await self.fs._info(fs_path)

        if info['type'] != 'file':
            raise ValueError(f"Path is a directory, not a file: {path}")

        return info.get('size', 0)

    async def mtime(self, path: str) -> float:
        """Get last modification time."""
        fs_path = self._make_path(path)
        info = await self.fs._info(fs_path)

        if 'mtime' in info:
            return info['mtime']
        elif 'LastModified' in info:
            import datetime
            dt = info['LastModified']
            if isinstance(dt, datetime.datetime):
                return dt.timestamp()

        import time
        return time.time()

    async def read_bytes(self, path: str) -> bytes:
        """Read entire file as bytes."""
        fs_path = self._make_path(path)
        return await self.fs._cat(fs_path)

    async def read_text(self, path: str, encoding: str = 'utf-8') -> str:
        """Read entire file as text."""
        data = await self.read_bytes(path)
        return data.decode(encoding)

    async def write_bytes(self, path: str, data: bytes) -> None:
        """Write bytes to file."""
        fs_path = self._make_path(path)
        await self.fs._pipe(fs_path, data)

    async def write_text(self, path: str, text: str, encoding: str = 'utf-8') -> None:
        """Write text to file."""
        data = text.encode(encoding)
        await self.write_bytes(path, data)

    async def delete(self, path: str, recursive: bool = False) -> None:
        """Delete file or directory."""
        fs_path = self._make_path(path)

        is_dir = await self.is_dir(path)
        if is_dir:
            if not recursive:
                raise ValueError(f"Path is a directory, use recursive=True: {path}")
            await self.fs._rm(fs_path, recursive=True)
        else:
            await self.fs._rm(fs_path)

    async def list_dir(self, path: str) -> list[str]:
        """List directory contents."""
        fs_path = self._make_path(path)

        entries = await self.fs._ls(fs_path, detail=False)

        # Extract basenames
        result = []
        for entry in entries:
            # Remove root_path prefix if present
            if self.root_path and entry.startswith(self.root_path + '/'):
                entry = entry[len(self.root_path) + 1:]

            # Remove path prefix
            if path and entry.startswith(path + '/'):
                entry = entry[len(path) + 1:]

            # Get basename only
            basename = entry.split('/')[-1]
            if basename:
                result.append(basename)

        return result

    async def mkdir(self, path: str, parents: bool = False, exist_ok: bool = False) -> None:
        """Create directory."""
        fs_path = self._make_path(path)
        await self.fs._makedirs(fs_path, exist_ok=exist_ok)

    async def copy(
        self,
        src_path: str,
        dest_implementor: AsyncImplementor,
        dest_path: str
    ) -> str | None:
        """Copy file to another implementor."""
        # Read from source
        data = await self.read_bytes(src_path)

        # Write to destination
        await dest_implementor.write_bytes(dest_path, data)

        return None

    async def local_path(self, path: str, mode: str = 'r'):
        """Get async context manager for local filesystem path.

        Args:
            path: Full path (from StorageManager)
            mode: Access mode ('r', 'w', 'rw')

        Returns:
            AsyncLocalPathContext: Async context manager yielding local path
        """
        return AsyncLocalPathContext(self, path, mode)

    async def close(self) -> None:
        """Close filesystem resources."""
        if hasattr(self.fs, 'close'):
            await self.fs.close()
