"""Tests for copy filtering functionality (include/exclude/filter)."""

import pytest
import tempfile
from datetime import datetime, timedelta
from genro_storage import StorageManager


class TestCopyIncludePatterns:
    """Tests for include pattern filtering."""

    def test_include_single_extension(self):
        """Include only files with specific extension."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create test files
        storage.node('src:file1.py').write_text('python')
        storage.node('src:file2.txt').write_text('text')
        storage.node('src:file3.py').write_text('python')
        storage.node('src:readme.md').write_text('markdown')

        # Copy only Python files
        storage.node('src:').copy_to(storage.node('dest:'), include='*.py')

        # Check results
        assert storage.node('dest:file1.py').exists
        assert storage.node('dest:file3.py').exists
        assert not storage.node('dest:file2.txt').exists
        assert not storage.node('dest:readme.md').exists

    def test_include_multiple_patterns(self):
        """Include files matching any of multiple patterns."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create test files
        storage.node('src:script.py').write_text('python')
        storage.node('src:data.json').write_text('json')
        storage.node('src:config.yaml').write_text('yaml')
        storage.node('src:readme.txt').write_text('text')

        # Copy only Python and JSON files
        storage.node('src:').copy_to(
            storage.node('dest:'),
            include=['*.py', '*.json']
        )

        # Check results
        assert storage.node('dest:script.py').exists
        assert storage.node('dest:data.json').exists
        assert not storage.node('dest:config.yaml').exists
        assert not storage.node('dest:readme.txt').exists

    def test_include_with_subdirectories(self):
        """Include patterns match paths in subdirectories."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create nested structure
        storage.node('src:dir1/file1.py').write_text('python')
        storage.node('src:dir1/file2.txt').write_text('text')
        storage.node('src:dir2/file3.py').write_text('python')

        # Copy only Python files
        storage.node('src:').copy_to(storage.node('dest:'), include='*.py')

        # Check results - should match basename
        assert storage.node('dest:dir1/file1.py').exists
        assert not storage.node('dest:dir1/file2.txt').exists
        assert storage.node('dest:dir2/file3.py').exists


class TestCopyExcludePatterns:
    """Tests for exclude pattern filtering."""

    def test_exclude_single_pattern(self):
        """Exclude files matching pattern."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create test files
        storage.node('src:app.py').write_text('code')
        storage.node('src:app.log').write_text('log')
        storage.node('src:data.txt').write_text('text')

        # Copy all except logs
        storage.node('src:').copy_to(storage.node('dest:'), exclude='*.log')

        # Check results
        assert storage.node('dest:app.py').exists
        assert storage.node('dest:data.txt').exists
        assert not storage.node('dest:app.log').exists

    def test_exclude_multiple_patterns(self):
        """Exclude files matching any of multiple patterns."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create test files
        storage.node('src:app.py').write_text('code')
        storage.node('src:debug.log').write_text('log')
        storage.node('src:cache.tmp').write_text('temp')
        storage.node('src:data.txt').write_text('text')

        # Exclude logs and temp files
        storage.node('src:').copy_to(
            storage.node('dest:'),
            exclude=['*.log', '*.tmp']
        )

        # Check results
        assert storage.node('dest:app.py').exists
        assert storage.node('dest:data.txt').exists
        assert not storage.node('dest:debug.log').exists
        assert not storage.node('dest:cache.tmp').exists

    def test_exclude_directory_pattern(self):
        """Exclude files in specific directories."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create nested structure
        storage.node('src:src/main.py').write_text('code')
        storage.node('src:__pycache__/main.pyc').write_text('cached')
        storage.node('src:tests/test.py').write_text('test')

        # Exclude cache directory
        storage.node('src:').copy_to(
            storage.node('dest:'),
            exclude='__pycache__/*'
        )

        # Check results
        assert storage.node('dest:src/main.py').exists
        assert storage.node('dest:tests/test.py').exists
        assert not storage.node('dest:__pycache__/main.pyc').exists


class TestCopyIncludeAndExclude:
    """Tests for combining include and exclude patterns."""

    def test_include_then_exclude(self):
        """Include filters first, then exclude."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create test files
        storage.node('src:main.py').write_text('code')
        storage.node('src:test_main.py').write_text('test')
        storage.node('src:utils.py').write_text('code')
        storage.node('src:readme.txt').write_text('text')

        # Include Python files but exclude tests
        storage.node('src:').copy_to(
            storage.node('dest:'),
            include='*.py',
            exclude='test_*.py'
        )

        # Check results
        assert storage.node('dest:main.py').exists
        assert storage.node('dest:utils.py').exists
        assert not storage.node('dest:test_main.py').exists
        assert not storage.node('dest:readme.txt').exists  # Not included


class TestCopyCustomFilter:
    """Tests for custom filter function."""

    def test_filter_by_size(self):
        """Filter files by size."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create files of different sizes
        storage.node('src:small.txt').write_text('a')  # 1 byte
        storage.node('src:medium.txt').write_text('a' * 100)  # 100 bytes
        storage.node('src:large.txt').write_text('a' * 10000)  # 10KB

        # Copy only files smaller than 1KB
        storage.node('src:').copy_to(
            storage.node('dest:'),
            filter=lambda node, path: node.size < 1000
        )

        # Check results
        assert storage.node('dest:small.txt').exists
        assert storage.node('dest:medium.txt').exists
        assert not storage.node('dest:large.txt').exists

    def test_filter_by_modification_time(self):
        """Filter files by modification time."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create files
        storage.node('src:old.txt').write_text('old')
        storage.node('src:new.txt').write_text('new')

        # Get current time and create cutoff
        cutoff = datetime.now() - timedelta(hours=1)
        cutoff_ts = cutoff.timestamp()

        # Copy only files modified recently (all should be recent in this test)
        storage.node('src:').copy_to(
            storage.node('dest:'),
            filter=lambda node, path: node.mtime > cutoff_ts
        )

        # Both should exist (were just created)
        assert storage.node('dest:old.txt').exists
        assert storage.node('dest:new.txt').exists

    def test_filter_by_path(self):
        """Filter files based on relative path."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create nested structure
        storage.node('src:src/main.py').write_text('code')
        storage.node('src:tests/test.py').write_text('test')
        storage.node('src:docs/readme.md').write_text('docs')

        # Copy only files NOT in tests directory
        storage.node('src:').copy_to(
            storage.node('dest:'),
            filter=lambda node, relpath: 'tests/' not in relpath
        )

        # Check results
        assert storage.node('dest:src/main.py').exists
        assert storage.node('dest:docs/readme.md').exists
        assert not storage.node('dest:tests/test.py').exists


class TestCopyCombinedFiltering:
    """Tests for combining all filtering methods."""

    def test_all_filters_together(self):
        """Combine include, exclude, and custom filter."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create diverse file structure
        storage.node('src:main.py').write_text('a' * 10)  # Small Python
        storage.node('src:large.py').write_text('a' * 10000)  # Large Python
        storage.node('src:test_main.py').write_text('a' * 10)  # Test Python
        storage.node('src:data.json').write_text('a' * 10)  # JSON
        storage.node('src:debug.log').write_text('a' * 10)  # Log

        # Copy:
        # - Include: only .py and .json
        # - Exclude: no test files
        # - Filter: only files < 1KB
        storage.node('src:').copy_to(
            storage.node('dest:'),
            include=['*.py', '*.json'],
            exclude='test_*.py',
            filter=lambda node, path: node.size < 1000
        )

        # Check results
        assert storage.node('dest:main.py').exists  # Passes all filters
        assert storage.node('dest:data.json').exists  # Passes all filters
        assert not storage.node('dest:large.py').exists  # Too large
        assert not storage.node('dest:test_main.py').exists  # Excluded
        assert not storage.node('dest:debug.log').exists  # Not included

    def test_filter_with_callbacks(self):
        """Filtering works with skip callbacks."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create files
        storage.node('src:file1.py').write_text('code')
        storage.node('src:file2.txt').write_text('text')
        storage.node('src:file3.log').write_text('log')

        # Track skipped files
        skipped = []

        # Copy with filtering and callbacks
        storage.node('src:').copy_to(
            storage.node('dest:'),
            include='*.py',
            on_skip=lambda node, reason: skipped.append((node.basename, reason))
        )

        # Check that filtered files were reported as skipped
        assert len(skipped) == 2  # file2.txt and file3.log
        basenames = [name for name, reason in skipped]
        assert 'file2.txt' in basenames
        assert 'file3.log' in basenames


class TestCopyFilteringEdgeCases:
    """Tests for edge cases in filtering."""

    def test_empty_directory_with_filters(self):
        """Copy empty directory with filters doesn't error."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create empty directory
        storage.node('src:empty').mkdir()

        # Copy with filters - should not error
        storage.node('src:').copy_to(storage.node('dest:'), include='*.py')

        # Destination should exist
        assert storage.node('dest:empty').exists
        assert storage.node('dest:empty').isdir

    def test_filter_exception_skips_file(self):
        """If filter function raises exception, file is skipped."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create files
        storage.node('src:file1.txt').write_text('content1')
        storage.node('src:file2.txt').write_text('content2')

        # Filter that raises exception for specific file
        def bad_filter(node, relpath):
            if 'file1' in relpath:
                raise ValueError("Test error")
            return True

        # Track skipped files
        skipped = []

        # Copy with bad filter
        storage.node('src:').copy_to(
            storage.node('dest:'),
            filter=bad_filter,
            on_skip=lambda node, reason: skipped.append((node.basename, reason))
        )

        # file1 should be skipped due to exception
        assert not storage.node('dest:file1.txt').exists
        assert storage.node('dest:file2.txt').exists

        # Check skipped was called for file1
        basenames = [name for name, reason in skipped]
        assert 'file1.txt' in basenames

    def test_no_files_match_filters(self):
        """Copy when no files match filters doesn't error."""
        storage = StorageManager()
        temp_src = tempfile.mkdtemp()
        temp_dest = tempfile.mkdtemp()
        storage.configure([
            {'name': 'src', 'type': 'local', 'path': temp_src},
            {'name': 'dest', 'type': 'local', 'path': temp_dest}
        ])

        # Create files that won't match
        storage.node('src:file1.txt').write_text('text')
        storage.node('src:file2.md').write_text('markdown')

        # Copy with filter that matches nothing
        storage.node('src:').copy_to(
            storage.node('dest:'),
            include='*.py'  # No Python files exist
        )

        # Destination directory should exist but be empty
        assert storage.node('dest:').exists
        children = storage.node('dest:').children()
        assert len(children) == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
