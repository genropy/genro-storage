"""Tests for copy() skip strategies."""

import pytest
from pathlib import Path
from genro_storage import StorageManager, SkipStrategy


class TestCopySkipStrategies:
    """Test copy() with different skip strategies."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage manager with source and dest mounts."""
        src_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        src_dir.mkdir()
        dest_dir.mkdir()

        manager = StorageManager()
        manager.configure([
            {'name': 'src', 'type': 'local', 'path': str(src_dir)},
            {'name': 'dest', 'type': 'local', 'path': str(dest_dir)},
        ])
        return manager

    def test_copy_skip_never_default(self, storage, tmp_path):
        """Default behavior (skip='never') always copies."""
        # Create source file
        src = storage.node('src:file.txt')
        src.write("version 1")

        # First copy
        dest = storage.node('dest:file.txt')
        src.copy_to(dest)
        assert dest.read() == "version 1"

        # Modify source
        src.write("version 2")

        # Copy again (should overwrite)
        src.copy_to(dest)
        assert dest.read() == "version 2"

    def test_copy_skip_exists(self, storage):
        """skip='exists' skips if destination exists."""
        # Create source
        src = storage.node('src:file.txt')
        src.write("version 1")

        # First copy
        dest = storage.node('dest:file.txt')
        src.copy_to(dest, skip='exists')
        assert dest.read() == "version 1"

        # Modify source
        src.write("version 2")

        # Copy again with skip='exists' (should NOT copy)
        src.copy_to(dest, skip='exists')
        assert dest.read() == "version 1"  # Still old version

    def test_copy_skip_exists_string_and_enum(self, storage):
        """skip='exists' works with both string and enum."""
        src = storage.node('src:file.txt')
        src.write("content")
        dest = storage.node('dest:file.txt')

        # Test with string
        src.copy_to(dest, skip='exists')
        assert dest.exists

        # Test with enum
        src2 = storage.node('src:file2.txt')
        src2.write("content")
        dest2 = storage.node('dest:file2.txt')
        src2.copy_to(dest2, skip=SkipStrategy.EXISTS)
        assert dest2.exists

    def test_copy_skip_size(self, storage):
        """skip='size' skips if same size."""
        # Create source
        src = storage.node('src:file.txt')
        src.write("12345")  # 5 bytes

        # First copy
        dest = storage.node('dest:file.txt')
        src.copy_to(dest, skip='size')
        assert dest.read() == "12345"

        # Modify source with SAME SIZE
        src.write("abcde")  # Still 5 bytes

        # Copy with skip='size' (should skip because same size)
        src.copy_to(dest, skip='size')
        assert dest.read() == "12345"  # Still old content

        # Modify source with DIFFERENT SIZE
        src.write("123456")  # 6 bytes

        # Copy with skip='size' (should copy because different size)
        src.copy_to(dest, skip='size')
        assert dest.read() == "123456"  # New content

    def test_copy_skip_hash(self, storage):
        """skip='hash' skips if same content (MD5)."""
        # Create source
        src = storage.node('src:file.txt')
        src.write("content")

        # First copy
        dest = storage.node('dest:file.txt')
        src.copy_to(dest, skip='hash')
        assert dest.read() == "content"

        # Modify source with SAME CONTENT (same MD5)
        src.write("content")

        # Copy with skip='hash' (should skip)
        src.copy_to(dest, skip='hash')
        assert dest.read() == "content"

        # Modify source with DIFFERENT CONTENT
        src.write("new content")

        # Copy with skip='hash' (should copy)
        src.copy_to(dest, skip='hash')
        assert dest.read() == "new content"

    def test_copy_skip_custom(self, storage):
        """skip='custom' uses custom skip function."""
        # Create files with different mtimes
        src = storage.node('src:file.txt')
        src.write("new")

        dest = storage.node('dest:file.txt')
        dest.write("old")

        # Custom function: skip if dest is newer
        def skip_if_dest_newer(src_node, dest_node):
            return dest_node.exists and dest_node.mtime > src_node.mtime

        # Dest is newer, should skip
        import time
        time.sleep(0.01)  # Ensure different mtime
        dest.write("newer")

        src.copy_to(dest, skip='custom', skip_fn=skip_if_dest_newer)
        assert dest.read() == "newer"  # Not copied

    def test_copy_skip_custom_requires_function(self, storage):
        """skip='custom' without skip_fn raises ValueError."""
        src = storage.node('src:file.txt')
        src.write("content")
        dest = storage.node('dest:file.txt')

        with pytest.raises(ValueError, match="skip='custom' requires skip_fn"):
            src.copy_to(dest, skip='custom')

    def test_copy_directory_skip_exists(self, storage):
        """Directory copy with skip='exists'."""
        # Create source directory structure
        (storage.node('src:dir/file1.txt')).write("file1")
        (storage.node('src:dir/file2.txt')).write("file2")
        (storage.node('src:dir/sub/file3.txt')).write("file3")

        # First copy
        src_dir = storage.node('src:dir')
        dest_dir = storage.node('dest:dir')
        src_dir.copy_to(dest_dir, skip='exists')

        assert storage.node('dest:dir/file1.txt').read() == "file1"
        assert storage.node('dest:dir/file2.txt').read() == "file2"
        assert storage.node('dest:dir/sub/file3.txt').read() == "file3"

        # Modify sources
        storage.node('src:dir/file1.txt').write("modified1")
        storage.node('src:dir/file2.txt').write("modified2")

        # Copy again with skip='exists' (should skip existing)
        src_dir.copy_to(dest_dir, skip='exists')

        assert storage.node('dest:dir/file1.txt').read() == "file1"  # Old
        assert storage.node('dest:dir/file2.txt').read() == "file2"  # Old

    def test_copy_directory_skip_hash(self, storage):
        """Directory copy with skip='hash' skips identical files."""
        # Create source structure
        storage.node('src:dir/unchanged.txt').write("same")
        storage.node('src:dir/changed.txt').write("old")

        # First copy
        src_dir = storage.node('src:dir')
        dest_dir = storage.node('dest:dir')
        src_dir.copy_to(dest_dir)

        # Modify only one file
        storage.node('src:dir/changed.txt').write("new")

        # Copy with skip='hash'
        copied = []
        skipped = []

        src_dir.copy_to(dest_dir, skip='hash',
                     on_file=lambda n: copied.append(n.basename),
                     on_skip=lambda n, r: skipped.append(n.basename))

        # Only changed file should be copied
        assert 'changed.txt' in copied
        assert 'unchanged.txt' in skipped
        assert storage.node('dest:dir/changed.txt').read() == "new"

    def test_copy_with_progress_callback(self, storage):
        """Progress callback is called for each file."""
        # Create directory with multiple files
        for i in range(5):
            storage.node(f'src:dir/file{i}.txt').write(f"content{i}")

        progress_calls = []

        def progress(current, total):
            progress_calls.append((current, total))

        src_dir = storage.node('src:dir')
        dest_dir = storage.node('dest:dir')
        src_dir.copy_to(dest_dir, progress=progress)

        # Should have 5 calls (one per file)
        assert len(progress_calls) == 5
        assert progress_calls[0] == (1, 5)
        assert progress_calls[-1] == (5, 5)

    def test_copy_with_on_file_callback(self, storage):
        """on_file callback is called after each copy."""
        storage.node('src:dir/file1.txt').write("a")
        storage.node('src:dir/file2.txt').write("b")

        copied_files = []

        def on_file(node):
            copied_files.append(node.basename)

        src_dir = storage.node('src:dir')
        dest_dir = storage.node('dest:dir')
        src_dir.copy_to(dest_dir, on_file=on_file)

        assert set(copied_files) == {'file1.txt', 'file2.txt'}

    def test_copy_with_on_skip_callback(self, storage):
        """on_skip callback is called when files are skipped."""
        # Create and copy
        storage.node('src:file1.txt').write("a")
        storage.node('src:file2.txt').write("b")

        src = storage.node('src:file1.txt')
        dest = storage.node('dest:file1.txt')
        src.copy_to(dest)

        # Copy again with skip='exists'
        skipped_files = []

        def on_skip(node, reason):
            skipped_files.append((node.basename, reason))

        src.copy_to(dest, skip='exists', on_skip=on_skip)

        assert len(skipped_files) == 1
        assert skipped_files[0][0] == 'file1.txt'
        assert 'exists' in skipped_files[0][1]

    def test_copy_skip_hash_with_directory_tracking(self, storage):
        """Full directory sync with detailed tracking."""
        # Create source structure
        storage.node('src:dir/unchanged1.txt').write("same1")
        storage.node('src:dir/unchanged2.txt').write("same2")
        storage.node('src:dir/changed.txt').write("old")
        storage.node('src:dir/new.txt').write("new")

        # First copy (without new.txt)
        src_dir = storage.node('src:dir')
        dest_dir = storage.node('dest:dir')

        for name in ['unchanged1.txt', 'unchanged2.txt', 'changed.txt']:
            src = storage.node(f'src:dir/{name}')
            dst = storage.node(f'dest:dir/{name}')
            src.copy_to(dst)

        # Modify one file
        storage.node('src:dir/changed.txt').write("new content")

        # Track what happens
        copied = []
        skipped = []

        def on_file(node):
            copied.append(node.basename)

        def on_skip(node, reason):
            skipped.append((node.basename, reason))

        # Sync with skip='hash'
        src_dir.copy_to(dest_dir, skip='hash', on_file=on_file, on_skip=on_skip)

        # Verify results
        assert 'changed.txt' in copied  # Modified file copied
        assert 'new.txt' in copied  # New file copied
        assert len(skipped) == 2  # Two unchanged files skipped
        assert any('unchanged1.txt' == s[0] for s in skipped)
        assert any('unchanged2.txt' == s[0] for s in skipped)

    def test_copy_single_file_with_callbacks(self, storage):
        """Callbacks work with single file copy too."""
        src = storage.node('src:file.txt')
        src.write("content")
        dest = storage.node('dest:file.txt')

        # First copy
        copied = []
        src.copy_to(dest, on_file=lambda n: copied.append(n.path))
        assert len(copied) == 1

        # Second copy with skip
        skipped = []
        src.copy_to(dest, skip='hash', on_skip=lambda n, r: skipped.append(n.path))
        assert len(skipped) == 1

    def test_copy_nonexistent_source_raises_error(self, storage):
        """Copying nonexistent source raises FileNotFoundError."""
        src = storage.node('src:nonexistent.txt')
        dest = storage.node('dest:file.txt')

        with pytest.raises(FileNotFoundError, match="Source not found"):
            src.copy_to(dest)

    def test_backward_compatibility_simple_copy(self, storage):
        """Simple copy without skip still works (backward compatible)."""
        src = storage.node('src:file.txt')
        src.write("content")
        dest = storage.node('dest:file.txt')

        # Old-style copy (no parameters)
        result = src.copy_to(dest)

        assert dest.read() == "content"
        assert result is dest

    def test_skip_strategy_enum_values(self):
        """SkipStrategy enum has correct values."""
        assert SkipStrategy.NEVER == 'never'
        assert SkipStrategy.EXISTS == 'exists'
        assert SkipStrategy.SIZE == 'size'
        assert SkipStrategy.HASH == 'hash'
        assert SkipStrategy.CUSTOM == 'custom'


class TestCopySkipEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage manager."""
        src_dir = tmp_path / "source"
        dest_dir = tmp_path / "dest"
        src_dir.mkdir()
        dest_dir.mkdir()

        manager = StorageManager()
        manager.configure([
            {'name': 'src', 'type': 'local', 'path': str(src_dir)},
            {'name': 'dest', 'type': 'local', 'path': str(dest_dir)},
        ])
        return manager

    def test_skip_size_handles_missing_dest(self, storage):
        """skip='size' doesn't fail if dest doesn't exist."""
        src = storage.node('src:file.txt')
        src.write("content")
        dest = storage.node('dest:file.txt')

        # Should copy (not skip) because dest doesn't exist
        src.copy_to(dest, skip='size')
        assert dest.exists
        assert dest.read() == "content"

    def test_skip_hash_handles_missing_dest(self, storage):
        """skip='hash' doesn't fail if dest doesn't exist."""
        src = storage.node('src:file.txt')
        src.write("content")
        dest = storage.node('dest:file.txt')

        # Should copy because dest doesn't exist
        src.copy_to(dest, skip='hash')
        assert dest.exists

    def test_empty_directory_copy(self, storage):
        """Copying empty directory works."""
        src_dir = storage.node('src:empty_dir')
        src_dir.mkdir()

        dest_dir = storage.node('dest:empty_dir')
        src_dir.copy_to(dest_dir)

        assert dest_dir.exists
        assert dest_dir.isdir
        assert len(dest_dir.children()) == 0

    def test_nested_directory_copy_with_skip(self, storage):
        """Deep nested directories with skip strategies."""
        # Create deep structure
        storage.node('src:a/b/c/d/file.txt').write("deep")

        src = storage.node('src:a')
        dest = storage.node('dest:a')

        src.copy_to(dest, skip='hash')

        assert storage.node('dest:a/b/c/d/file.txt').read() == "deep"
