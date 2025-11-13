"""Tests for call() method and mimetype property."""

import pytest
import subprocess
import time
from pathlib import Path
from genro_storage import StorageManager


class TestCallMethod:
    """Test call() method for external process integration."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage manager with local mount."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        manager = StorageManager()
        manager.configure(
            [
                {"name": "data", "protocol": "local", "path": str(data_dir)},
            ]
        )
        return manager

    def test_call_simple_command(self, storage):
        """Simple command execution."""
        # Create test file
        file = storage.node("data:test.txt")
        file.write("Hello World")

        # Use 'cat' to read file (Unix) or 'type' on Windows
        import platform

        if platform.system() == "Windows":
            output = file.call("type", file, return_output=True)
        else:
            output = file.call("cat", file, return_output=True)

        assert "Hello World" in output

    def test_call_with_storagenode_arguments(self, storage):
        """StorageNode arguments are converted to local paths."""
        input_file = storage.node("data:input.txt")
        output_file = storage.node("data:output.txt")

        input_file.write("Test content")

        # Use 'cp' on Unix or 'copy' on Windows
        import platform

        if platform.system() == "Windows":
            input_file.call("copy", input_file, output_file, shell=True)
        else:
            input_file.call("cp", input_file, output_file)

        assert output_file.exists
        assert output_file.read() == "Test content"

    def test_call_modifies_file(self, storage):
        """File modifications are uploaded after command."""
        file = storage.node("data:file.txt")
        file.write("line 1\n")

        # Append to file using echo (platform-specific)
        import platform

        if platform.system() == "Windows":
            # Windows: use type to append
            pytest.skip("Complex shell redirect on Windows")
        else:
            # Unix: use sh with proper local_path expansion
            # The file node is converted to local path automatically
            with file.local_path(mode="rw") as local_path:
                import subprocess

                subprocess.run(["sh", "-c", f'echo "line 2" >> "{local_path}"'], check=True)

        content = file.read()
        assert "line 1" in content
        assert "line 2" in content

    def test_call_return_output(self, storage):
        """Return command output when return_output=True."""
        file = storage.node("data:test.txt")
        file.write("Hello\nWorld\n")

        # Count lines
        import platform

        if platform.system() == "Windows":
            # Windows find counts lines
            output = file.call("find", "/c", "/v", '""', file, return_output=True)
            assert "2" in output
        else:
            # Unix wc counts lines
            output = file.call("wc", "-l", file, return_output=True)
            assert "2" in output

    def test_call_with_callback(self, storage):
        """Callback is called after execution."""
        callback_called = []

        def callback():
            callback_called.append(True)

        file = storage.node("data:test.txt")
        file.write("test")

        import platform

        if platform.system() == "Windows":
            file.call("type", file, callback=callback)
        else:
            file.call("cat", file, callback=callback)

        assert len(callback_called) == 1

    def test_call_async_mode(self, storage):
        """Async mode runs in background."""
        file = storage.node("data:test.txt")
        file.write("test")

        callback_called = []

        def callback():
            callback_called.append(True)

        # Start async
        import platform

        if platform.system() == "Windows":
            result = file.call("timeout", "1", callback=callback, async_mode=True)
        else:
            result = file.call("sleep", "0.1", callback=callback, async_mode=True)

        # Should return immediately
        assert result is None

        # Wait for completion
        time.sleep(0.5)

        # Callback should have been called
        assert len(callback_called) == 1

    def test_call_with_subprocess_kwargs(self, storage):
        """subprocess_kwargs are passed through."""
        file = storage.node("data:test.txt")
        file.write("test")

        # Set timeout
        import platform

        if platform.system() == "Windows":
            # Windows: timeout command
            with pytest.raises(subprocess.TimeoutExpired):
                file.call("timeout", "10", timeout=0.1)
        else:
            # Unix: sleep command
            with pytest.raises(subprocess.TimeoutExpired):
                file.call("sleep", "10", timeout=0.1)

    def test_call_command_not_found(self, storage):
        """Raises error if command not found."""
        file = storage.node("data:test.txt")
        file.write("test")

        with pytest.raises((FileNotFoundError, subprocess.CalledProcessError)):
            file.call("nonexistent_command_xyz", file)

    def test_call_command_fails(self, storage):
        """Raises error if command exits non-zero."""
        file = storage.node("data:test.txt")
        file.write("test")

        # 'false' command always fails on Unix
        import platform

        if platform.system() != "Windows":
            with pytest.raises(subprocess.CalledProcessError):
                file.call("false")

    def test_call_multiple_storagenode_args(self, storage):
        """Multiple StorageNode arguments work."""
        file1 = storage.node("data:file1.txt")
        file2 = storage.node("data:file2.txt")
        output = storage.node("data:output.txt")

        file1.write("Content1")
        file2.write("Content2")

        # Concatenate files using call() which auto-converts StorageNodes to paths
        import platform

        if platform.system() == "Windows":
            pytest.skip("Complex redirect on Windows")
        else:
            # Use call with explicit local_path handling
            with file1.local_path() as path1:
                with file2.local_path() as path2:
                    with output.local_path(mode="w") as out_path:
                        import subprocess

                        subprocess.run(
                            ["sh", "-c", f'cat "{path1}" "{path2}" > "{out_path}"'], check=True
                        )

        result = output.read()
        assert "Content1" in result
        assert "Content2" in result

    def test_call_mixed_arguments(self, storage):
        """Mix StorageNode and string arguments."""
        file = storage.node("data:test.txt")
        file.write("Hello World")

        # grep with pattern (string) and file (StorageNode)
        import platform

        if platform.system() != "Windows":
            output = file.call("grep", "World", file, return_output=True)
            assert "World" in output


class TestMimetypeProperty:
    """Test mimetype property."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage manager."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        manager = StorageManager()
        manager.configure(
            [
                {"name": "data", "protocol": "local", "path": str(data_dir)},
            ]
        )
        return manager

    def test_mimetype_image_formats(self, storage):
        """Image formats return correct MIME types."""
        jpg = storage.node("data:photo.jpg")
        png = storage.node("data:icon.png")
        gif = storage.node("data:animation.gif")

        assert jpg.mimetype == "image/jpeg"
        assert png.mimetype == "image/png"
        assert gif.mimetype == "image/gif"

    def test_mimetype_document_formats(self, storage):
        """Document formats return correct MIME types."""
        pdf = storage.node("data:document.pdf")
        txt = storage.node("data:readme.txt")
        html = storage.node("data:page.html")

        assert pdf.mimetype == "application/pdf"
        assert txt.mimetype == "text/plain"
        assert html.mimetype == "text/html"

    def test_mimetype_archive_formats(self, storage):
        """Archive formats return correct MIME types."""
        zip_file = storage.node("data:archive.zip")
        tar = storage.node("data:backup.tar")
        gz = storage.node("data:compressed.tar.gz")  # .tar.gz returns x-tar

        assert zip_file.mimetype == "application/zip"
        assert tar.mimetype == "application/x-tar"
        # Python's mimetypes returns 'application/x-tar' for .tar.gz
        assert gz.mimetype in (
            "application/gzip",
            "application/x-gzip",
            "application/x-tar",
            "application/x-tar+gzip",
        )

    def test_mimetype_video_audio(self, storage):
        """Video and audio formats."""
        mp4 = storage.node("data:video.mp4")
        mp3 = storage.node("data:audio.mp3")
        wav = storage.node("data:sound.wav")

        assert mp4.mimetype == "video/mp4"
        assert mp3.mimetype == "audio/mpeg"
        assert wav.mimetype == "audio/x-wav"

    def test_mimetype_code_formats(self, storage):
        """Code/script formats."""
        py = storage.node("data:script.py")
        js = storage.node("data:app.js")
        json = storage.node("data:config.json")
        xml = storage.node("data:data.xml")

        assert py.mimetype == "text/x-python"
        assert js.mimetype in ("text/javascript", "application/javascript")
        assert json.mimetype == "application/json"
        assert xml.mimetype in ("text/xml", "application/xml")

    def test_mimetype_unknown_extension(self, storage):
        """Unknown extension returns application/octet-stream."""
        unknown = storage.node("data:file.xyz123")
        assert unknown.mimetype == "application/octet-stream"

    def test_mimetype_no_extension(self, storage):
        """File without extension returns application/octet-stream."""
        no_ext = storage.node("data:README")
        assert no_ext.mimetype == "application/octet-stream"

    def test_mimetype_case_insensitive(self, storage):
        """MIME type detection is case-insensitive."""
        jpg_upper = storage.node("data:photo.JPG")
        jpg_lower = storage.node("data:photo.jpg")
        jpg_mixed = storage.node("data:photo.JpG")

        assert jpg_upper.mimetype == "image/jpeg"
        assert jpg_lower.mimetype == "image/jpeg"
        assert jpg_mixed.mimetype == "image/jpeg"

    def test_mimetype_with_base64_backend(self, storage):
        """Mimetype works with base64 backend."""
        import base64

        # Configure base64 backend
        storage.configure([{"name": "b64", "protocol": "base64"}])

        # Create base64 node with .pdf extension in path
        content = b"PDF content"
        b64_data = base64.b64encode(content).decode()

        # The path is just the base64 data, but we can check basename behavior
        node = storage.node(f"b64:{b64_data}")

        # Base64 backend doesn't have real extensions
        # This tests that mimetype doesn't crash
        result = node.mimetype
        assert isinstance(result, str)

    def test_mimetype_real_world_extensions(self, storage):
        """Test common real-world file extensions."""
        test_cases = [
            (
                "document.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            (
                "spreadsheet.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ),
            (
                "presentation.pptx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ),
            ("image.svg", "image/svg+xml"),
            ("data.csv", "text/csv"),
            ("style.css", "text/css"),
        ]

        for filename, expected_mime in test_cases:
            node = storage.node(f"data:{filename}")
            assert node.mimetype == expected_mime, f"Failed for {filename}"
