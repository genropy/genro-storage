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
    "StorageBackend",
    "LocalStorage",
    "Base64Backend",
    "RelativeMountBackend",
]
