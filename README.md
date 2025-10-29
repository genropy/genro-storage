# genro-storage

[![Python versions](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/genro-storage/badge/?version=latest)](https://genro-storage.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/genropy/genro-storage/workflows/Tests/badge.svg)](https://github.com/genropy/genro-storage/actions)
[![codecov](https://codecov.io/gh/genropy/genro-storage/branch/main/graph/badge.svg)](https://codecov.io/gh/genropy/genro-storage)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Universal storage abstraction for Python with pluggable backends**

A modern, elegant Python library that provides a unified interface for accessing files across local filesystems, cloud storage (S3, GCS, Azure), and remote protocols (HTTP). Built on top of **fsspec**, genro-storage adds an intuitive mount-point system and user-friendly API inspired by Unix filesystems.

## Status: Beta - Ready for Production Testing

**Current Version:** 0.4.2
**Last Updated:** October 2025

✅ Core implementation complete
✅ 15 storage backends working (local, S3, GCS, Azure, HTTP, Memory, Base64, SMB, SFTP, ZIP, TAR, Git, GitHub, WebDAV, LibArchive)
✅ **NEW in v0.4.2:** Git, GitHub, WebDAV, and LibArchive backends
✅ **NEW in v0.4.1:** SMB, SFTP, ZIP, and TAR backends
✅ **NEW in v0.3.0:** Async/await support for FastAPI, asyncio applications (asyncer-based)
✅ 293 tests passing on Python 3.9-3.12
✅ Full documentation on ReadTheDocs
✅ Battle-tested code from Genropy (19+ years in production, storage abstraction since 2018)
✅ Available on PyPI

## Key Features

- **Async/await support** - Use in FastAPI, asyncio apps with AsyncStorageManager (NEW in v0.3.0!)
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

### Synchronous Usage

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
    node.copy_to(storage.node('home:cache/avatar.jpg'))

    # Read and process
    data = node.read_bytes()

    # Backup to GCS
    node.copy_to(storage.node('backups:avatars/user_123.jpg'))

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
s3_image.copy_to(b64_image)
data_uri = f"data:image/jpeg;base64,{b64_image.path}"

# Advanced features
# 1. Intelligent incremental backups (NEW!)
docs = storage.node('home:documents')
s3_backup = storage.node('uploads:backup/documents')

# Skip files that already exist (fastest)
docs.copy_to(s3_backup, skip='exists')

# Skip files with same size (fast, good accuracy)
docs.copy_to(s3_backup, skip='size')

# Skip files with same content (accurate, uses S3 ETag - fast!)
docs.copy_to(s3_backup, skip='hash')

# With progress tracking
from tqdm import tqdm
pbar = tqdm(desc="Backing up", unit="file")
docs.copy_to(s3_backup, skip='hash',
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

### Async Usage (NEW in v0.3.0!)

Built on [asyncer](https://github.com/tiangolo/asyncer) by Sebastián Ramírez (FastAPI author) for automatic sync→async conversion with no event loop blocking.

```python
from genro_storage import AsyncStorageManager

# Initialize async storage manager
storage = AsyncStorageManager()

# Configure (sync - call at startup)
storage.configure([
    {'name': 'uploads', 'type': 's3', 'bucket': 'my-app-uploads'},
    {'name': 'cache', 'type': 'local', 'path': '/tmp/cache'}
])

# Use in async context (FastAPI, asyncio, etc.)
async def process_file(file_path: str):
    node = storage.node(f'uploads:{file_path}')

    # All I/O operations are async
    if await node.exists():
        data = await node.read_bytes()

        # Process and cache
        processed = process_data(data)
        cache_node = storage.node('cache:processed.dat')
        await cache_node.write_bytes(processed)

        return processed

    raise FileNotFoundError(file_path)

# FastAPI example
from fastapi import FastAPI, HTTPException

app = FastAPI()

@app.get("/files/{filepath:path}")
async def get_file(filepath: str):
    """Serve file from S3 storage."""
    node = storage.node(f'uploads:{filepath}')

    if not await node.exists():
        raise HTTPException(status_code=404, detail="File not found")

    return {
        "data": await node.read_bytes(),
        "size": await node.size(),
        "mime_type": node.mimetype  # Sync property
    }

# Concurrent operations
import asyncio

async def backup_files(file_list):
    """Backup multiple files concurrently."""
    async def backup_one(filepath):
        source = storage.node(f'uploads:{filepath}')
        target = storage.node(f'backups:{filepath}')
        data = await source.read_bytes()
        await target.write_bytes(data)

    # Process all files in parallel
    await asyncio.gather(*[backup_one(f) for f in file_list])
```

## Learning with Interactive Tutorials

The best way to learn genro-storage is through our **hands-on Jupyter notebooks** in the [`notebooks/`](notebooks/) directory.

### Run Online (No Installation Required)

[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/genropy/genro-storage/main?filepath=notebooks)

Click the badge above to launch an interactive Jupyter environment in your browser. Ready in ~2 minutes!

### Run Locally

```bash
# 1. Install Jupyter
pip install jupyter notebook

# 2. Navigate to notebooks directory
cd notebooks

# 3. Launch Jupyter
jupyter notebook

# 4. Open 01_quickstart.ipynb and start learning!
```

**Note:** Jupyter will open in your browser automatically. Execute cells sequentially with `Shift+Enter`.

### Tutorial Contents

| Notebook | Topic | Duration | Level |
|----------|-------|----------|-------|
| 01 - Quickstart | Basic concepts and first steps | 15 min | Beginner |
| 02 - Backends | Storage backends and configuration | 20 min | Beginner |
| 03 - File Operations | Read, write, copy, directories | 25 min | Beginner |
| 04 - Virtual Nodes | iternode, diffnode, zip archives | 30 min | Intermediate |
| 05 - Copy Strategies | Smart copying and filtering | 25 min | Intermediate |
| 06 - Versioning | S3 version history and rollback | 30 min | Intermediate |
| 07 - Advanced Features | External tools, WSGI, metadata | 35 min | Advanced |
| 08 - Real World Examples | Complete use cases | 40 min | Advanced |

**Total time:** ~3.5 hours • **Start here:** [01_quickstart.ipynb](notebooks/01_quickstart.ipynb)

See [notebooks/README.md](notebooks/README.md) for the complete learning guide.

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
# Cloud storage
pip install genro-storage[s3]          # Amazon S3
pip install genro-storage[gcs]         # Google Cloud Storage
pip install genro-storage[azure]       # Azure Blob Storage

# Network protocols
pip install genro-storage[http]        # HTTP/HTTPS
pip install genro-storage[smb]         # SMB/CIFS (Windows/Samba shares)
pip install genro-storage[sftp]        # SFTP (SSH File Transfer)
pip install genro-storage[webdav]      # WebDAV (Nextcloud, ownCloud, SharePoint)

# Archive formats
pip install genro-storage[libarchive]  # RAR, 7z, ISO, and 20+ formats

# Version control
# Git and GitHub are built-in to fsspec (no extra install needed)

# Other
pip install genro-storage[async]       # Async support
pip install genro-storage[all]         # All backends + async
```

**Built-in backends** (no extra dependencies):
- Local filesystem
- Memory (in-memory storage for testing)
- Base64 (inline data URIs)
- ZIP archives
- TAR archives (with gzip, bzip2, xz compression)
- Git repositories (requires system `pygit2`)
- GitHub repositories

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
- [asyncer](https://github.com/tiangolo/asyncer) - Async wrapper (v0.3.0+)
- Modern Python (3.9+) with full type hints
- Optional backends: s3fs, gcsfs, adlfs, aiohttp, smbprotocol, paramiko, webdav4, libarchive-c

## Origins

genro-storage is extracted and modernized from [Genropy](https://github.com/genropy/genropy), a Python web framework in production since 2006 (19+ years). The storage abstraction layer was introduced in 2018 and has been battle-tested in production for 6+ years. We're making this powerful storage abstraction available as a standalone library for the wider Python community.

## Development Status

**Phase:** Beta - Production Testing

- ✅ API Design Complete and Stable
- ✅ Core Implementation Complete
- ✅ FsspecBackend (15 storage backends: local, S3, GCS, Azure, HTTP, Memory, Base64, SMB, SFTP, ZIP, TAR, Git, GitHub, WebDAV, LibArchive)
- ✅ Comprehensive Test Suite (293 tests, 81% coverage)
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
- ✅ Async/await support (AsyncStorageManager, AsyncStorageNode) - v0.3.0 released
- 🎯 Ready for early adopters and production testing
- ⏳ Extended GCS/Azure integration testing

**Recent Releases:**
- v0.4.2 (October 2025) - Git, GitHub, WebDAV, LibArchive backends ✅
- v0.4.1 (October 2025) - SMB, SFTP, ZIP, TAR backends ✅
- v0.4.0 (October 2025) - Relative mounts with permissions, unified read/write API ✅
- v0.3.0 (October 2025) - Async support via asyncer wrapper ✅
- v0.2.0 (October 2025) - Virtual nodes, tutorials, enhanced testing ✅

## Contributing

Contributions are welcome! We follow a **Git Flow** workflow with protected branches for code quality.

**Quick Start:**
1. Read our [Contributing Guide](CONTRIBUTING.md) for detailed workflow and guidelines
2. Fork the repository and create a feature branch from `develop`
3. Make your changes with tests and documentation
4. Submit a Pull Request to the `develop` branch

**Branch Structure:**
- `main` - Production releases (protected, requires PR review)
- `develop` - Integration branch (protected, requires PR review)
- `feature/*` - Feature development branches
- `bugfix/*` - Bug fixes
- `hotfix/*` - Critical production fixes

See [CONTRIBUTING.md](CONTRIBUTING.md) for complete workflow documentation.

**Areas for contribution:**
- Add integration tests for GCS and Azure backends
- Improve test coverage (target: 90%+)
- Add integration tests for new backends (SMB, SFTP, WebDAV, etc.)
- Performance optimizations
- Additional backend implementations

## License

MIT License - See [LICENSE](LICENSE) for details

---

**Made with ❤️ by the Genropy team**
