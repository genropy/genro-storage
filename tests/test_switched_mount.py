"""Tests for switched mount pattern with callable path resolvers."""

import pytest
import tempfile
import shutil
from pathlib import Path

from genro_storage import StorageManager
from genro_storage.backends.local import LocalStorage


@pytest.fixture
def temp_dirs():
    """Create multiple temporary directories simulating different packages."""
    base_dir = tempfile.mkdtemp()

    # Create structure like: /tmp/base/sys-package, /tmp/base/adm-package, etc.
    sys_dir = Path(base_dir) / "sys-package"
    adm_dir = Path(base_dir) / "adm-package"
    gnr_dir = Path(base_dir) / "gnr-package"

    sys_dir.mkdir(parents=True)
    adm_dir.mkdir(parents=True)
    gnr_dir.mkdir(parents=True)

    # Create some test files
    (sys_dir / "sys_file.txt").write_text("sys content")
    (adm_dir / "adm_file.txt").write_text("adm content")
    (gnr_dir / "gnr_file.txt").write_text("gnr content")

    # Create nested folders
    (sys_dir / "folder").mkdir()
    (sys_dir / "folder" / "nested.txt").write_text("nested in sys")

    yield {"base": base_dir, "sys": str(sys_dir), "adm": str(adm_dir), "gnr": str(gnr_dir)}

    shutil.rmtree(base_dir)


class TestSwitchedMountDirect:
    """Test switched mount pattern using LocalStorage directly."""

    def test_switched_mount_basic_routing(self, temp_dirs):
        """Test basic routing to different directories based on prefix."""

        # Resolver that switches based on prefix
        def resource_resolver(prefix):
            mapping = {"sys": temp_dirs["sys"], "adm": temp_dirs["adm"], "gnr": temp_dirs["gnr"]}
            return mapping.get(prefix, temp_dirs["base"])

        # Create backend with resolver
        backend = LocalStorage(resource_resolver)

        # Access files from different "packages"
        sys_content = backend.read_text("sys/sys_file.txt")
        adm_content = backend.read_text("adm/adm_file.txt")
        gnr_content = backend.read_text("gnr/gnr_file.txt")

        assert sys_content == "sys content"
        assert adm_content == "adm content"
        assert gnr_content == "gnr content"

    def test_switched_mount_nested_paths(self, temp_dirs):
        """Test routing with nested paths."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        backend = LocalStorage(resource_resolver)

        # Access nested file
        content = backend.read_text("sys/folder/nested.txt")
        assert content == "nested in sys"

    def test_switched_mount_write_operations(self, temp_dirs):
        """Test write operations work correctly with routing."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        backend = LocalStorage(resource_resolver)

        # Write to different packages
        backend.write_text("sys/new_sys_file.txt", "new sys content")
        backend.write_text("adm/new_adm_file.txt", "new adm content")

        # Verify files are in correct directories
        assert (Path(temp_dirs["sys"]) / "new_sys_file.txt").read_text() == "new sys content"
        assert (Path(temp_dirs["adm"]) / "new_adm_file.txt").read_text() == "new adm content"

    def test_switched_mount_exists_check(self, temp_dirs):
        """Test exists() works with routing."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        backend = LocalStorage(resource_resolver)

        assert backend.exists("sys/sys_file.txt") is True
        assert backend.exists("adm/adm_file.txt") is True
        assert backend.exists("sys/nonexistent.txt") is False
        assert backend.exists("gnr/nonexistent.txt") is False

    def test_switched_mount_list_dir(self, temp_dirs):
        """Test list_dir() works with routing."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        backend = LocalStorage(resource_resolver)

        # List root of sys package
        sys_files = backend.list_dir("sys")
        assert "sys_file.txt" in sys_files
        assert "folder" in sys_files


class TestSwitchedMountViaStorageManager:
    """Test switched mount pattern via StorageManager."""

    def test_switched_mount_via_manager(self, temp_dirs):
        """Test switched mount through StorageManager configuration."""

        def resource_resolver(prefix):
            mapping = {"sys": temp_dirs["sys"], "adm": temp_dirs["adm"], "gnr": temp_dirs["gnr"]}
            return mapping.get(prefix, temp_dirs["base"])

        # Configure manager with switched mount
        storage = StorageManager()
        storage.add_mount({"name": "resources", "protocol": "local", "path": resource_resolver})

        # Access through storage manager
        sys_node = storage.node("resources:sys/sys_file.txt")
        adm_node = storage.node("resources:adm/adm_file.txt")

        assert sys_node.read() == "sys content"
        assert adm_node.read() == "adm content"

    def test_switched_mount_node_operations(self, temp_dirs):
        """Test StorageNode operations with switched mount."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        storage = StorageManager()
        storage.add_mount({"name": "pkg", "protocol": "local", "path": resource_resolver})

        # Test various node operations
        sys_root = storage.node("pkg:sys")
        assert sys_root.exists
        assert sys_root.isdir

        # List children
        children = sys_root.children()
        child_names = [c.basename for c in children]
        assert "sys_file.txt" in child_names

        # Navigate to child
        sys_file = sys_root.child("sys_file.txt")
        assert sys_file.exists
        assert sys_file.read() == "sys content"


class TestSwitchedMountBackwardCompatibility:
    """Test that context-based callables (no parameters) still work."""

    def test_context_callable_no_parameters(self, temp_dirs):
        """Test callable without parameters still works (backward compatibility)."""
        current_package = "sys"

        def get_current_package_dir():
            # Context-based callable - no parameters
            return temp_dirs[current_package]

        backend = LocalStorage(get_current_package_dir)

        # Access file
        content = backend.read_text("sys_file.txt")
        assert content == "sys content"

        # Change context and create new backend
        current_package = "adm"
        backend2 = LocalStorage(get_current_package_dir)
        content2 = backend2.read_text("adm_file.txt")
        assert content2 == "adm content"


class TestSwitchedMountEdgeCases:
    """Test edge cases and error conditions."""

    def test_prefix_only_path(self, temp_dirs):
        """Test accessing just the prefix (no subpath)."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        backend = LocalStorage(resource_resolver)

        # Access directory root
        assert backend.exists("sys")
        assert backend.is_dir("sys")

    def test_unknown_prefix(self, temp_dirs):
        """Test accessing unknown prefix."""

        def resource_resolver(prefix):
            mapping = {"sys": temp_dirs["sys"], "adm": temp_dirs["adm"]}
            if prefix not in mapping:
                raise ValueError(f"Unknown package: {prefix}")
            return mapping[prefix]

        backend = LocalStorage(resource_resolver)

        # Valid prefix works
        assert backend.exists("sys/sys_file.txt")

        # Invalid prefix raises error
        with pytest.raises(ValueError, match="Unknown package: unknown"):
            backend.exists("unknown/file.txt")

    def test_security_path_escape_with_routing(self, temp_dirs):
        """Test that path escaping is prevented with routing."""

        def resource_resolver(prefix):
            return temp_dirs.get(prefix, temp_dirs["base"])

        backend = LocalStorage(resource_resolver)

        # Try to escape from sys package directory
        with pytest.raises(ValueError, match="Path escapes base directory"):
            backend.read_text("sys/../../etc/passwd")
