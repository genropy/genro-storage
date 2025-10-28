# genro-storage

[![Python versions](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/genro-storage/badge/?version=latest)](https://genro-storage.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/genropy/genro-storage/workflows/Tests/badge.svg)](https://github.com/genropy/genro-storage/actions)
[![Coverage](https://raw.githubusercontent.com/genropy/genro-storage/main/.github/badges/coverage.svg)](https://github.com/genropy/genro-storage/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Universal storage abstraction for Python with pluggable backends**

A modern, elegant Python library that provides a unified interface for accessing files across local filesystems, cloud storage (S3, GCS, Azure), and remote protocols (HTTP). Built on top of **fsspec**, genro-storage adds an intuitive mount-point system and user-friendly API inspired by Unix filesystems.

## Status: Beta - Ready for Production Testing

**Current Version:** 0.1.0-beta
**Last Updated:** October 2025

✅ Core implementation complete
✅ All backends working (local, S3, GCS, Azure, HTTP, Memory, Base64)
✅ 195 tests passing on Python 3.9-3.12
✅ Full documentation on ReadTheDocs
✅ Battle-tested code from Genropy (19+ years in production, storage abstraction since 2018)
✅ Available on PyPI

## Key Features

- **Powered by fsspec** - Leverage 20+ battle-tested storage backends
- **Mount point system** - Organize storage with logical names like `home:`, `uploads:`, `s3:`
- **Intuitive API** - Pathlib-inspired interface that feels natural and Pythonic
- **Intelligent copy strategies** - Skip files by existence, size, or hash for efficient incremental backups
- **Progress tracking** - Built-in callbacks for progress bars and logging during copy operations
- **Content-based comparison** - Compare files by MD5 hash across different backends
- **Efficient hashing** - Uses cloud metadata (S3 ETag) when available, avoiding downloads
- **External tool integration** - `call()` method for seamless integration with ffmpeg, imagemagick, pandoc, etc.
- **WSGI file serving** - `serve()` method for web frameworks (Flask, Django, Pyramid) with ETag caching
- **MIME type detection** - Automatic content-type detection from file extensions
- **Flexible configuration** - Load mounts from YAML, JSON, or code
- **Dynamic paths** - Support for callable paths that resolve at runtime (perfect for user-specific directories)
- **Cloud metadata** - Get/set custom metadata on S3, GCS, Azure files
- **URL generation** - Generate presigned URLs for S3, public URLs for sharing
- **Base64 utilities** - Encode files to data URIs, download from URLs
- **S3 versioning** - Access historical file versions (when S3 versioning enabled)
- **Test-friendly** - In-memory backend for fast, isolated testing
- **Base64 data URIs** - Embed data inline with automatic encoding (writable with mutable paths)
- **Production-ready backends** - Built on 6+ years of Genropy production experience
- **Lightweight core** - Optional backends installed only when needed
- **Cross-storage operations** - Copy/move files between different storage types seamlessly

## Why genro-storage vs raw fsspec?

While **fsspec** is powerful, genro-storage provides:

- **Mount point abstraction** - Work with logical names instead of full URIs
- **Simpler API** - Less verbose, more intuitive for common operations
- **Configuration management** - Load storage configs from files
- **Enhanced utilities** - Cross-storage copy, unified error handling

Think of it as **"requests" is to "urllib"** - a friendlier interface to an excellent foundation.

## Perfect For

- **Multi-cloud applications** that need storage abstraction
- **Data pipelines** processing files from various sources
- **Web applications** managing uploads across environments
- **CLI tools** that work with local and remote files
- **Testing scenarios** requiring storage mocking

## Quick Example

```python
from genro_storage import StorageManager

# Configure storage backends
storage = StorageManager()
storage.configure([
    {'name': 'home', 'type': 'local', 'path': '/home/user'},
    {'name': 'uploads', 'type': 's3', 'bucket': 'my-app-uploads'},
    {'name': 'backups', 'type': 'gcs', 'bucket': 'my-backups'},
    {'name': 'data', 'type': 'base64'}  # Inline base64 data
])

# Work with files using a unified API
node = storage.node('uploads:users/123/avatar.jpg')
if node.exists:
    # Copy from S3 to local
    node.copy(storage.node('home:cache/avatar.jpg'))

    # Read and process
    data = node.read_bytes()

    # Backup to GCS
    node.copy(storage.node('backups:avatars/user_123.jpg'))

# Base64 backend: embed data directly in URIs (data URI style)
# Read inline data
import base64
text = "Configuration data"
b64_data = base64.b64encode(text.encode()).decode()
node = storage.node(f'data:{b64_data}')
print(node.read_text())  # "Configuration data"

# Or write to create base64 (path updates automatically)
node = storage.node('data:')
node.write_text("New content")
print(node.path)  # "TmV3IGNvbnRlbnQ=" (base64 of "New content")

# Copy from S3 to base64 for inline use
s3_image = storage.node('uploads:photo.jpg')
b64_image = storage.node('data:')
s3_image.copy(b64_image)
data_uri = f"data:image/jpeg;base64,{b64_image.path}"

# Advanced features
# 1. Intelligent incremental backups (NEW!)
docs = storage.node('home:documents')
s3_backup = storage.node('uploads:backup/documents')

# Skip files that already exist (fastest)
docs.copy(s3_backup, skip='exists')

# Skip files with same size (fast, good accuracy)
docs.copy(s3_backup, skip='size')

# Skip files with same content (accurate, uses S3 ETag - fast!)
docs.copy(s3_backup, skip='hash')

# With progress tracking
from tqdm import tqdm
pbar = tqdm(desc="Backing up", unit="file")
docs.copy(s3_backup, skip='hash',
          progress=lambda cur, tot: pbar.update(1))
pbar.close()

# 2. Work with external tools using call() (ffmpeg, imagemagick, etc.)
video = storage.node('uploads:video.mp4')
thumbnail = storage.node('uploads:thumb.jpg')

# Automatically handles cloud download/upload
video.call('ffmpeg', '-i', video, '-vf', 'thumbnail', '-frames:v', '1', thumbnail)

# Or use local_path() for more control
with video.local_path(mode='r') as local_path:
    import subprocess
    subprocess.run(['ffmpeg', '-i', local_path, 'output.mp4'])

# 3. Serve files via WSGI (Flask, Django, Pyramid)
from flask import Flask, request
app = Flask(__name__)

@app.route('/files/<path:filepath>')
def serve_file(filepath):
    node = storage.node(f'uploads:{filepath}')
    # ETag caching, streaming, MIME types - all automatic!
    return node.serve(request.environ, lambda s, h: None, cache_max_age=3600)

# 4. Check MIME types
doc = storage.node('uploads:report.pdf')
print(doc.mimetype)  # 'application/pdf'

# 5. Dynamic paths for multi-user apps
def get_user_storage():
    user_id = get_current_user()
    return f'/data/users/{user_id}'

storage.configure([
    {'name': 'user', 'type': 'local', 'path': get_user_storage}
])
# Path resolves differently per user!

# 6. Cloud metadata
file = storage.node('uploads:document.pdf')
file.set_metadata({
    'Author': 'John Doe',
    'Department': 'Engineering'
})

# 7. Generate shareable URLs
url = file.url(expires_in=3600)  # S3 presigned URL

# 8. Encode to data URI
img = storage.node('home:logo.png')
data_uri = img.to_base64()  # data:image/png;base64,...

# 9. Download from internet
remote = storage.node('uploads:downloaded.pdf')
remote.fill_from_url('https://example.com/file.pdf')
```

## Installation

### From GitHub (Recommended)

Install directly from GitHub without cloning:

```bash
# Base package
pip install git+https://github.com/genropy/genro-storage.git

# With S3 support
pip install "genro-storage[s3] @ git+https://github.com/genropy/genro-storage.git"

# With all backends
pip install "genro-storage[all] @ git+https://github.com/genropy/genro-storage.git"
```

### From Source (Development)

Clone and install in editable mode:

```bash
# Clone repository
git clone https://github.com/genropy/genro-storage.git
cd genro-storage

# Install base package
pip install -e .

# Install with S3 support
pip install -e ".[s3]"

# Install with all backends
pip install -e ".[all]"

# Install for development
pip install -e ".[all,dev]"
```

### Supported Backends

Install optional dependencies for specific backends:

```bash
pip install genro-storage[s3]      # Amazon S3
pip install genro-storage[gcs]     # Google Cloud Storage
pip install genro-storage[azure]   # Azure Blob Storage
pip install genro-storage[http]    # HTTP/HTTPS
pip install genro-storage[all]     # All backends
```

## Testing

```bash
# Unit tests (fast, no external dependencies)
pytest tests/test_local_storage.py -v

# Integration tests (requires Docker + MinIO)
docker-compose up -d
pytest tests/test_s3_integration.py -v

# All tests
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=genro_storage
```

See [TESTING.md](TESTING.md) for detailed testing instructions with MinIO.

## Documentation

- **[Full Documentation](https://genro-storage.readthedocs.io/)** - Complete API reference and guides
- **[API Design](API_DESIGN.md)** - Detailed design specification
- **[Testing Guide](TESTING.md)** - How to run tests with MinIO

## Built With

- [fsspec](https://filesystem-spec.readthedocs.io/) - Pythonic filesystem abstraction
- Modern Python (3.9+) with full type hints
- Optional backends: s3fs, gcsfs, adlfs, aiohttp

## Origins

genro-storage is extracted and modernized from [Genropy](https://github.com/genropy/genropy), a Python web framework in production since 2006 (19+ years). The storage abstraction layer was introduced in 2018 and has been battle-tested in production for 6+ years. We're making this powerful storage abstraction available as a standalone library for the wider Python community.

## Development Status

**Phase:** Beta - Production Testing

- ✅ API Design Complete and Stable
- ✅ Core Implementation Complete
- ✅ FsspecBackend (all 7 storage types working: local, S3, GCS, Azure, HTTP, Memory, Base64)
- ✅ Comprehensive Test Suite (195 tests, 79% coverage)
- ✅ CI/CD with Python 3.9, 3.10, 3.11, 3.12
- ✅ MD5 hashing and content-based equality
- ✅ Base64 backend with writable mutable paths
- ✅ Intelligent copy skip strategies (exists, size, hash, custom)
- ✅ call() method for external tool integration (ffmpeg, imagemagick, etc.)
- ✅ serve() method for WSGI file serving (Flask, Django, Pyramid)
- ✅ mimetype property for automatic content-type detection
- ✅ local_path() context manager for external tools
- ✅ Callable path support for dynamic directories
- ✅ Cloud metadata get/set (S3, GCS, Azure)
- ✅ URL generation (presigned URLs, data URIs)
- ✅ S3 versioning support
- ✅ Full Documentation on ReadTheDocs
- ✅ MinIO Integration Testing
- 🎯 Ready for early adopters and production testing
- ⏳ First PyPI release (v0.1.0)
- ⏳ Extended GCS/Azure integration testing

**Roadmap:**
- v0.1.0 (Q4 2025) - First PyPI release (Beta)
- v0.2.0 (Q1 2026) - Async support, performance optimizations
- v1.0.0 (2026) - Production-ready, stable API guarantee

## Contributing

Contributions welcome! The library is in beta with a stable API.

**How to contribute:**
1. Review the [API Design Document](API_DESIGN.md)
2. Check existing [tests](tests/) to understand behavior
3. Open an issue to discuss major changes
4. Submit PRs with tests

**Testing contributions:**
- Add tests for GCS and Azure backends
- Improve test coverage (target: 90%+)
- Add integration tests for edge cases

## License

MIT License - See [LICENSE](LICENSE) for details

---

**Made with ❤️ by the Genropy team**
