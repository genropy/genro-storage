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

"""Provider system for genro-storage.

This module contains the new provider architecture with:
- Provider classes (fsspec, boto3, filesystem)
- Pydantic models for configuration validation
- Implementor classes as adapters between our API and provider APIs
"""

from .base import AsyncProvider, AsyncImplementor
from .registry import ProviderRegistry
from .fsspec_provider import FsspecProvider
from .custom_provider import CustomProvider

__all__ = [
    "AsyncProvider",
    "AsyncImplementor",
    "ProviderRegistry",
    "FsspecProvider",
    "CustomProvider",
]
