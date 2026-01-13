# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
"""POC async implementation - kept for reference.

This directory contains the previous async implementation that used
a separate AsyncStorageManager/AsyncStorageNode architecture.

It has been replaced by @smartasync decorator on StorageNode methods,
which provides unified sync/async API without code duplication.
"""
