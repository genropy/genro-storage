"""Tests for versioning edge cases on non-versioned backends."""

import pytest
import tempfile
from genro_storage import StorageManager


class TestVersioningOnNonVersionedBackends:
    """Test versioning methods on backends that don't support versioning."""

    def test_versions_on_local_backend_returns_empty(self):
        """versions property returns empty list for local backend."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([{"name": "local", "protocol": "local", "path": tmpdir}])

            node = storage.node("local:test.txt")
            node.write("content", mode="w")

            # Local backend doesn't support versioning
            versions = node.versions
            assert versions == []

    def test_versions_on_memory_backend_returns_empty(self):
        """versions property returns empty list for memory backend."""
        storage = StorageManager()
        storage.configure([{"name": "memory", "protocol": "memory"}])

        node = storage.node("memory:test.txt")
        node.write("content", mode="w")

        # Memory backend doesn't support versioning
        versions = node.versions
        assert versions == []

    def test_version_count_on_non_versioned_backend(self):
        """version_count property returns 0 for non-versioned backends."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = StorageManager()
            storage.configure([{"name": "local", "protocol": "local", "path": tmpdir}])

            node = storage.node("local:test.txt")
            node.write("content", mode="w")

            # Should return 0 (no versioning)
            assert node.version_count == 0
