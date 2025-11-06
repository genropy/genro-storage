"""Tests for serve() method (WSGI file serving)."""

import pytest
from genro_storage import StorageManager


class TestServeMethod:
    """Test serve() method for WSGI integration."""

    @pytest.fixture
    def storage(self, tmp_path):
        """Create storage manager with local mount."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        manager = StorageManager()
        manager.configure(
            [
                {"name": "data", "type": "local", "path": str(data_dir)},
            ]
        )
        return manager

    def test_serve_basic_file(self, storage):
        """Basic file serving."""
        file = storage.node("data:test.txt")
        file.write("Hello World")

        # Mock WSGI environ and start_response
        environ = {}
        response_status = []
        response_headers = []

        def start_response(status, headers):
            response_status.append(status)
            response_headers.extend(headers)

        # Serve file
        body = file.serve(environ, start_response)

        # Check response
        assert response_status[0] == "200 OK"
        assert b"Hello World" in b"".join(body)

        # Check headers
        headers_dict = dict(response_headers)
        assert "ETag" in headers_dict
        assert headers_dict["Content-Type"] == "text/plain"
        assert headers_dict["Content-Length"] == "11"

    def test_serve_with_etag_match(self, storage):
        """ETag match returns 304 Not Modified."""
        file = storage.node("data:test.txt")
        file.write("Hello World")

        # First request to get ETag
        environ1 = {}
        response_headers1 = []

        def start_response1(status, headers):
            response_headers1.extend(headers)

        body1 = file.serve(environ1, start_response1)
        headers_dict1 = dict(response_headers1)
        etag = headers_dict1["ETag"]

        # Second request with ETag
        environ2 = {"HTTP_IF_NONE_MATCH": etag}
        response_status2 = []
        response_headers2 = []

        def start_response2(status, headers):
            response_status2.append(status)
            response_headers2.extend(headers)

        body2 = file.serve(environ2, start_response2)

        # Should return 304
        assert response_status2[0] == "304 Not Modified"
        assert body2 == [b""]

    def test_serve_with_etag_mismatch(self, storage):
        """ETag mismatch returns full file."""
        file = storage.node("data:test.txt")
        file.write("Hello World")

        # Request with wrong ETag
        environ = {"HTTP_IF_NONE_MATCH": '"wrong-etag"'}
        response_status = []

        def start_response(status, headers):
            response_status.append(status)

        body = file.serve(environ, start_response)

        # Should return 200 with full content
        assert response_status[0] == "200 OK"
        assert b"Hello World" in b"".join(body)

    def test_serve_with_download(self, storage):
        """Download mode sets Content-Disposition."""
        file = storage.node("data:report.pdf")
        file.write(b"PDF content", mode="wb")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(environ, start_response, download=True)

        # Check Content-Disposition
        headers_dict = dict(response_headers)
        assert "Content-Disposition" in headers_dict
        assert "attachment" in headers_dict["Content-Disposition"]
        assert "report.pdf" in headers_dict["Content-Disposition"]

    def test_serve_with_custom_download_name(self, storage):
        """Custom download name."""
        file = storage.node("data:file.pdf")
        file.write(b"PDF content", mode="wb")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(environ, start_response, download_name="custom_name.pdf")

        # Check custom name
        headers_dict = dict(response_headers)
        assert "custom_name.pdf" in headers_dict["Content-Disposition"]

    def test_serve_with_cache_control(self, storage):
        """Cache-Control header."""
        file = storage.node("data:test.txt")
        file.write("Hello World")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(environ, start_response, cache_max_age=3600)

        # Check Cache-Control
        headers_dict = dict(response_headers)
        assert headers_dict["Cache-Control"] == "max-age=3600"

    def test_serve_missing_file(self, storage):
        """Missing file returns 404."""
        file = storage.node("data:missing.txt")

        environ = {}
        response_status = []

        def start_response(status, headers):
            response_status.append(status)

        body = file.serve(environ, start_response)

        assert response_status[0] == "404 Not Found"
        assert body == [b"Not Found"]

    def test_serve_binary_file(self, storage):
        """Binary file serving."""
        file = storage.node("data:image.png")
        binary_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100

        file.write(binary_data, mode="wb")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(environ, start_response)

        # Check MIME type
        headers_dict = dict(response_headers)
        assert headers_dict["Content-Type"] == "image/png"

        # Check content
        assert b"".join(body) == binary_data

    def test_serve_large_file(self, storage):
        """Large file is streamed in chunks."""
        file = storage.node("data:large.bin")

        # Create 1MB file
        large_data = b"X" * (1024 * 1024)
        file.write(large_data, mode="wb")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(environ, start_response)

        # Should return multiple chunks
        assert len(body) > 1  # More than one chunk

        # Check total content
        assert b"".join(body) == large_data

        # Check Content-Length
        headers_dict = dict(response_headers)
        assert headers_dict["Content-Length"] == str(len(large_data))

    def test_serve_mimetype_detection(self, storage):
        """Correct MIME type for various formats."""
        test_cases = [
            ("image.jpg", b"JPEG", "image/jpeg"),
            ("video.mp4", b"MP4", "video/mp4"),
            ("doc.pdf", b"PDF", "application/pdf"),
            ("data.json", b"{}", "application/json"),
            ("style.css", b"body{}", "text/css"),
        ]

        for filename, content, expected_mime in test_cases:
            file = storage.node(f"data:{filename}")
            file.write(content, mode="wb")

            environ = {}
            response_headers = []

            def start_response(status, headers):
                response_headers.clear()
                response_headers.extend(headers)

            body = file.serve(environ, start_response)

            headers_dict = dict(response_headers)
            assert headers_dict["Content-Type"] == expected_mime, f"Failed for {filename}"

    def test_serve_empty_file(self, storage):
        """Empty file serving."""
        file = storage.node("data:empty.txt")
        file.write("")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(environ, start_response)

        headers_dict = dict(response_headers)
        assert headers_dict["Content-Length"] == "0"
        assert b"".join(body) == b""

    def test_serve_with_all_options(self, storage):
        """All options combined."""
        file = storage.node("data:report.pdf")
        file.write(b"PDF content", mode="wb")

        environ = {}
        response_headers = []

        def start_response(status, headers):
            response_headers.extend(headers)

        body = file.serve(
            environ,
            start_response,
            download=True,
            download_name="annual_report.pdf",
            cache_max_age=86400,
        )

        headers_dict = dict(response_headers)

        # Check all headers
        assert "ETag" in headers_dict
        assert headers_dict["Content-Type"] == "application/pdf"
        assert "annual_report.pdf" in headers_dict["Content-Disposition"]
        assert headers_dict["Cache-Control"] == "max-age=86400"

    def test_serve_etag_changes_on_modification(self, storage):
        """ETag changes when file is modified."""
        file = storage.node("data:test.txt")
        file.write("Version 1")

        # Get first ETag
        environ1 = {}
        response_headers1 = []

        def start_response1(status, headers):
            response_headers1.extend(headers)

        body1 = file.serve(environ1, start_response1)
        etag1 = dict(response_headers1)["ETag"]

        # Modify file
        import time

        time.sleep(0.01)  # Ensure mtime changes
        file.write("Version 2")

        # Get second ETag
        environ2 = {}
        response_headers2 = []

        def start_response2(status, headers):
            response_headers2.extend(headers)

        body2 = file.serve(environ2, start_response2)
        etag2 = dict(response_headers2)["ETag"]

        # ETags should be different
        assert etag1 != etag2

    def test_serve_with_subdirectory(self, storage):
        """Serve file from subdirectory."""
        file = storage.node("data:subdir/nested/file.txt")
        file.write("Nested content")

        environ = {}
        response_status = []

        def start_response(status, headers):
            response_status.append(status)

        body = file.serve(environ, start_response)

        assert response_status[0] == "200 OK"
        assert b"Nested content" in b"".join(body)
