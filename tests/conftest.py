"""Shared test fixtures and configuration."""

import os
import tempfile
import shutil
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing.
    
    Yields the path to the temp directory and cleans it up after the test.
    """
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def storage_manager():
    """Create a fresh StorageManager instance for testing."""
    from genro_storage import StorageManager
    return StorageManager()


@pytest.fixture
def configured_storage(temp_dir):
    """Create a StorageManager with a local mount configured.
    
    Provides a storage manager with 'test' mount pointing to a temp directory.
    """
    from genro_storage import StorageManager
    
    storage = StorageManager()
    storage.configure([
        {'name': 'test', 'type': 'local', 'path': temp_dir}
    ])
    return storage


@pytest.fixture
def multi_storage(temp_dir):
    """Create a StorageManager with multiple mounts configured.
    
    Provides:
    - 'local1': temp_dir/mount1
    - 'local2': temp_dir/mount2
    - 'memory': in-memory storage
    """
    from genro_storage import StorageManager
    
    mount1 = os.path.join(temp_dir, 'mount1')
    mount2 = os.path.join(temp_dir, 'mount2')
    os.makedirs(mount1)
    os.makedirs(mount2)
    
    storage = StorageManager()
    storage.configure([
        {'name': 'local1', 'type': 'local', 'path': mount1},
        {'name': 'local2', 'type': 'local', 'path': mount2},
        {'name': 'memory', 'type': 'memory'}
    ])
    return storage


@pytest.fixture
def sample_file(temp_dir):
    """Create a sample file with known content.
    
    Returns tuple of (file_path, content_bytes).
    """
    content = b"Sample file content\nLine 2\nLine 3"
    file_path = os.path.join(temp_dir, 'sample.txt')
    
    with open(file_path, 'wb') as f:
        f.write(content)
    
    return file_path, content


@pytest.fixture
def sample_text_file(temp_dir):
    """Create a sample text file with UTF-8 content.
    
    Returns tuple of (file_path, content_str).
    """
    content = "Hello World\nCafé ☕\nLine 3"
    file_path = os.path.join(temp_dir, 'sample_text.txt')
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return file_path, content


@pytest.fixture
def sample_directory(temp_dir):
    """Create a sample directory structure.
    
    Structure:
    sample_dir/
    ├── file1.txt
    ├── file2.txt
    └── subdir/
        └── file3.txt
    
    Returns the path to sample_dir.
    """
    sample_dir = os.path.join(temp_dir, 'sample_dir')
    subdir = os.path.join(sample_dir, 'subdir')
    
    os.makedirs(subdir)
    
    # Create files
    with open(os.path.join(sample_dir, 'file1.txt'), 'w') as f:
        f.write('Content 1')
    with open(os.path.join(sample_dir, 'file2.txt'), 'w') as f:
        f.write('Content 2')
    with open(os.path.join(subdir, 'file3.txt'), 'w') as f:
        f.write('Content 3')
    
    return sample_dir
