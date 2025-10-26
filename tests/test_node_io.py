"""Tests for StorageNode I/O operations."""

import os
import pytest


class TestStorageNodeOpen:
    """Test StorageNode.open() method."""
    
    def test_open_read_binary_mode(self, configured_storage, temp_dir):
        """open('rb') returns readable binary file object."""
        content = b'Binary content'
        file_path = os.path.join(temp_dir, 'file.bin')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.bin')
        with node.open('rb') as f:
            data = f.read()
        
        assert data == content
    
    def test_open_read_text_mode(self, configured_storage, temp_dir):
        """open('r') returns readable text file object."""
        content = 'Text content\nLine 2'
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        with node.open('r') as f:
            data = f.read()
        
        assert data == content
    
    def test_open_write_binary_mode(self, configured_storage, temp_dir):
        """open('wb') returns writable binary file object."""
        content = b'New binary content'
        
        node = configured_storage.node('test:output.bin')
        with node.open('wb') as f:
            f.write(content)
        
        # Verify file was written
        file_path = os.path.join(temp_dir, 'output.bin')
        with open(file_path, 'rb') as f:
            data = f.read()
        
        assert data == content
    
    def test_open_write_text_mode(self, configured_storage, temp_dir):
        """open('w') returns writable text file object."""
        content = 'New text content\nLine 2'
        
        node = configured_storage.node('test:output.txt')
        with node.open('w') as f:
            f.write(content)
        
        # Verify file was written
        file_path = os.path.join(temp_dir, 'output.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        assert data == content
    
    def test_open_append_mode(self, configured_storage, temp_dir):
        """open('a') appends to existing file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('Original')
        
        node = configured_storage.node('test:file.txt')
        with node.open('a') as f:
            f.write('\nAppended')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        assert content == 'Original\nAppended'
    
    def test_open_default_mode_is_rb(self, configured_storage, temp_dir):
        """open() without mode defaults to 'rb'."""
        content = b'Default mode test'
        file_path = os.path.join(temp_dir, 'file.bin')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.bin')
        with node.open() as f:
            data = f.read()
        
        assert data == content
    
    def test_open_context_manager_closes_file(self, configured_storage, temp_dir):
        """open() context manager properly closes file."""
        content = b'Content'
        file_path = os.path.join(temp_dir, 'file.bin')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.bin')
        with node.open('rb') as f:
            file_obj = f
            assert not f.closed
        
        assert file_obj.closed
    
    def test_open_raises_for_nonexistent_file_in_read_mode(self, configured_storage):
        """open('r') raises FileNotFoundError for nonexistent file."""
        node = configured_storage.node('test:nonexistent.txt')
        with pytest.raises(FileNotFoundError):
            with node.open('r') as f:
                pass
    
    def test_open_creates_file_in_write_mode(self, configured_storage, temp_dir):
        """open('w') creates file if it doesn't exist."""
        node = configured_storage.node('test:new_file.txt')
        
        with node.open('w') as f:
            f.write('Content')
        
        file_path = os.path.join(temp_dir, 'new_file.txt')
        assert os.path.exists(file_path)
    
    def test_open_truncates_existing_file_in_write_mode(self, configured_storage, temp_dir):
        """open('w') truncates existing file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('Original long content')
        
        node = configured_storage.node('test:file.txt')
        with node.open('w') as f:
            f.write('Short')
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        assert content == 'Short'


class TestStorageNodeReadBytes:
    """Test StorageNode.read_bytes() method."""
    
    def test_read_bytes_returns_file_content(self, configured_storage, temp_dir):
        """read_bytes() returns complete file content as bytes."""
        content = b'Hello World\x00\xFF'
        file_path = os.path.join(temp_dir, 'file.bin')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.bin')
        data = node.read_bytes()
        
        assert data == content
    
    def test_read_bytes_returns_empty_for_empty_file(self, configured_storage, temp_dir):
        """read_bytes() returns empty bytes for empty file."""
        file_path = os.path.join(temp_dir, 'empty.bin')
        open(file_path, 'wb').close()
        
        node = configured_storage.node('test:empty.bin')
        data = node.read_bytes()
        
        assert data == b''
    
    def test_read_bytes_handles_large_files(self, configured_storage, temp_dir):
        """read_bytes() handles large files."""
        content = b'X' * 100000  # 100KB
        file_path = os.path.join(temp_dir, 'large.bin')
        with open(file_path, 'wb') as f:
            f.write(content)
        
        node = configured_storage.node('test:large.bin')
        data = node.read_bytes()
        
        assert len(data) == 100000
        assert data == content
    
    def test_read_bytes_raises_for_nonexistent_file(self, configured_storage):
        """read_bytes() raises FileNotFoundError for nonexistent file."""
        node = configured_storage.node('test:nonexistent.bin')
        
        with pytest.raises(FileNotFoundError):
            node.read_bytes()
    
    def test_read_bytes_raises_for_directory(self, configured_storage, temp_dir):
        """read_bytes() raises exception for directory."""
        dir_path = os.path.join(temp_dir, 'mydir')
        os.makedirs(dir_path)
        
        node = configured_storage.node('test:mydir')
        
        with pytest.raises(Exception):
            node.read_bytes()


class TestStorageNodeReadText:
    """Test StorageNode.read_text() method."""
    
    def test_read_text_returns_string_content(self, configured_storage, temp_dir):
        """read_text() returns file content as string."""
        content = 'Hello World\nLine 2'
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        data = node.read_text()
        
        assert data == content
        assert isinstance(data, str)
    
    def test_read_text_default_encoding_is_utf8(self, configured_storage, temp_dir):
        """read_text() uses UTF-8 encoding by default."""
        content = 'Café ☕ 日本語'
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        data = node.read_text()
        
        assert data == content
    
    def test_read_text_custom_encoding(self, configured_storage, temp_dir):
        """read_text() accepts custom encoding."""
        content = 'Café'
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w', encoding='latin-1') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        data = node.read_text(encoding='latin-1')
        
        assert data == content
    
    def test_read_text_empty_file(self, configured_storage, temp_dir):
        """read_text() returns empty string for empty file."""
        file_path = os.path.join(temp_dir, 'empty.txt')
        open(file_path, 'w').close()
        
        node = configured_storage.node('test:empty.txt')
        data = node.read_text()
        
        assert data == ''
    
    def test_read_text_preserves_newlines(self, configured_storage, temp_dir):
        """read_text() preserves newline characters."""
        content = 'Line 1\nLine 2\r\nLine 3\n'
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w', encoding='utf-8', newline='') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        data = node.read_text()
        
        assert '\n' in data
    
    def test_read_text_raises_for_nonexistent_file(self, configured_storage):
        """read_text() raises FileNotFoundError for nonexistent file."""
        node = configured_storage.node('test:nonexistent.txt')
        
        with pytest.raises(FileNotFoundError):
            node.read_text()
    
    def test_read_text_raises_for_invalid_encoding(self, configured_storage, temp_dir):
        """read_text() raises UnicodeDecodeError for wrong encoding."""
        # Write UTF-8 content
        content = 'Café ☕'
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        node = configured_storage.node('test:file.txt')
        
        # Try to read with ASCII encoding
        with pytest.raises(UnicodeDecodeError):
            node.read_text(encoding='ascii')


class TestStorageNodeWriteBytes:
    """Test StorageNode.write_bytes() method."""
    
    def test_write_bytes_creates_file(self, configured_storage, temp_dir):
        """write_bytes() creates new file."""
        content = b'New content'
        
        node = configured_storage.node('test:new_file.bin')
        node.write_bytes(content)
        
        file_path = os.path.join(temp_dir, 'new_file.bin')
        with open(file_path, 'rb') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_bytes_overwrites_existing_file(self, configured_storage, temp_dir):
        """write_bytes() overwrites existing file."""
        file_path = os.path.join(temp_dir, 'file.bin')
        with open(file_path, 'wb') as f:
            f.write(b'Original')
        
        node = configured_storage.node('test:file.bin')
        node.write_bytes(b'New')
        
        with open(file_path, 'rb') as f:
            data = f.read()
        
        assert data == b'New'
    
    def test_write_bytes_handles_empty_content(self, configured_storage, temp_dir):
        """write_bytes() can write empty content."""
        node = configured_storage.node('test:empty.bin')
        node.write_bytes(b'')
        
        file_path = os.path.join(temp_dir, 'empty.bin')
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) == 0
    
    def test_write_bytes_handles_binary_data(self, configured_storage, temp_dir):
        """write_bytes() handles arbitrary binary data."""
        content = bytes(range(256))  # All byte values
        
        node = configured_storage.node('test:binary.bin')
        node.write_bytes(content)
        
        file_path = os.path.join(temp_dir, 'binary.bin')
        with open(file_path, 'rb') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_bytes_handles_large_data(self, configured_storage, temp_dir):
        """write_bytes() handles large binary data."""
        content = b'X' * 1000000  # 1MB
        
        node = configured_storage.node('test:large.bin')
        node.write_bytes(content)
        
        file_path = os.path.join(temp_dir, 'large.bin')
        assert os.path.getsize(file_path) == 1000000
    
    def test_write_bytes_creates_parent_directory(self, configured_storage, temp_dir):
        """write_bytes() creates parent directories if needed."""
        node = configured_storage.node('test:subdir/nested/file.bin')
        node.write_bytes(b'Content')
        
        file_path = os.path.join(temp_dir, 'subdir', 'nested', 'file.bin')
        assert os.path.exists(file_path)
    
    def test_write_bytes_returns_none(self, configured_storage, temp_dir):
        """write_bytes() returns None."""
        node = configured_storage.node('test:file.bin')
        result = node.write_bytes(b'Content')
        
        assert result is None


class TestStorageNodeWriteText:
    """Test StorageNode.write_text() method."""
    
    def test_write_text_creates_file(self, configured_storage, temp_dir):
        """write_text() creates new file."""
        content = 'Hello World'
        
        node = configured_storage.node('test:new_file.txt')
        node.write_text(content)
        
        file_path = os.path.join(temp_dir, 'new_file.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_text_default_encoding_is_utf8(self, configured_storage, temp_dir):
        """write_text() uses UTF-8 encoding by default."""
        content = 'Café ☕ 日本語'
        
        node = configured_storage.node('test:file.txt')
        node.write_text(content)
        
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_text_custom_encoding(self, configured_storage, temp_dir):
        """write_text() accepts custom encoding."""
        content = 'Café'
        
        node = configured_storage.node('test:file.txt')
        node.write_text(content, encoding='latin-1')
        
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'r', encoding='latin-1') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_text_overwrites_existing_file(self, configured_storage, temp_dir):
        """write_text() overwrites existing file."""
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'w') as f:
            f.write('Original content')
        
        node = configured_storage.node('test:file.txt')
        node.write_text('New')
        
        with open(file_path, 'r') as f:
            data = f.read()
        
        assert data == 'New'
    
    def test_write_text_handles_empty_string(self, configured_storage, temp_dir):
        """write_text() can write empty string."""
        node = configured_storage.node('test:empty.txt')
        node.write_text('')
        
        file_path = os.path.join(temp_dir, 'empty.txt')
        assert os.path.exists(file_path)
        assert os.path.getsize(file_path) == 0
    
    def test_write_text_preserves_newlines(self, configured_storage, temp_dir):
        """write_text() preserves newline characters."""
        content = 'Line 1\nLine 2\nLine 3'
        
        node = configured_storage.node('test:file.txt')
        node.write_text(content)
        
        file_path = os.path.join(temp_dir, 'file.txt')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_text_handles_multiline_string(self, configured_storage, temp_dir):
        """write_text() handles multi-line strings."""
        content = """First line
Second line
Third line"""
        
        node = configured_storage.node('test:multiline.txt')
        node.write_text(content)
        
        file_path = os.path.join(temp_dir, 'multiline.txt')
        with open(file_path, 'r') as f:
            data = f.read()
        
        assert data == content
    
    def test_write_text_returns_none(self, configured_storage, temp_dir):
        """write_text() returns None."""
        node = configured_storage.node('test:file.txt')
        result = node.write_text('Content')
        
        assert result is None
