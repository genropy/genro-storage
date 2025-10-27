# genro-storage

[![Python versions](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/genro-storage/badge/?version=latest)](https://genro-storage.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/genropy/genro-storage/workflows/Tests/badge.svg)](https://github.com/genropy/genro-storage/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Universal storage abstraction for Python with pluggable backends**

A modern, elegant Python library that provides a unified interface for accessing files across local filesystems, cloud storage (S3, GCS, Azure), and remote protocols (HTTP). Built on top of **fsspec**, genro-storage adds an intuitive mount-point system and user-friendly API inspired by Unix filesystems.

## Status: Alpha - Ready for Testing

**Current Version:** 0.1.0-alpha  
**Last Updated:** October 2025

✅ Core implementation complete
✅ All backends working (local, S3, GCS, Azure, HTTP, Memory, Base64)
✅ 102+ tests passing
✅ Full documentation on ReadTheDocs
⚠️ Not yet on PyPI - install from source

## Key Features

- **Powered by fsspec** - Leverage 20+ battle-tested storage backends
- **Mount point system** - Organize storage with logical names like `home:`, `uploads:`, `s3:`
- **Intuitive API** - Pathlib-inspired interface that feels natural and Pythonic
- **Content-based comparison** - Compare files by MD5 hash across different backends
- **Efficient hashing** - Uses cloud metadata (S3 ETag) when available, avoiding downloads
- **Flexible configuration** - Load mounts from YAML, JSON, or code
- **Test-friendly** - In-memory backend for fast, isolated testing
- **Base64 data URIs** - Embed small data directly in URIs (no storage needed)
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
import base64
text = "Configuration data"
b64_data = base64.b64encode(text.encode()).decode()
node = storage.node(f'data:{b64_data}')
print(node.read_text())  # "Configuration data"
```

## Installation

### From Source (Current)

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

genro-storage is extracted and modernized from [Genropy](https://github.com/genropy/genropy), a Python web framework with 6+ years of production battle-testing. We're making this powerful storage abstraction available as a standalone library for the wider Python community.

## Development Status

**Phase:** Alpha Testing

- ✅ API Design Complete
- ✅ Core Implementation Complete
- ✅ FsspecBackend (all 6 storage types working)
- ✅ Comprehensive Test Suite (74+ tests, 66% coverage)
- ✅ MD5 hashing and content-based equality
- ✅ Full Documentation on ReadTheDocs
- ✅ MinIO Integration Testing
- ⏳ Additional backends (GCS, Azure) - ready but needs testing
- ⏳ Performance optimization
- ⏳ First PyPI release (v0.1.0)

**Roadmap:**
- v0.1.0 (Q4 2025) - First public release
- v0.2.0 - Async support, additional utilities
- v1.0.0 - Production-ready, stable API

## Contributing

Contributions welcome! The library is in alpha but the API is stabilizing.

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
