# genro-storage

> **⚠️ WORK IN PROGRESS**: This library is currently under active development. The API is being designed and implemented. Not yet ready for production use.

[![Python versions](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/genro-storage/badge/?version=latest)](https://genro-storage.readthedocs.io/en/latest/?badge=latest)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**Universal storage abstraction for Python with pluggable backends**

A modern, elegant Python library that provides a unified interface for accessing files across local filesystems, cloud storage (S3, GCS, Azure), and remote protocols (HTTP, SFTP). Built on top of **fsspec**, genro-storage adds an intuitive mount-point system and user-friendly API inspired by Unix filesystems.

## Key Features

- **Powered by fsspec** - Leverage 20+ battle-tested storage backends
- **Mount point system** - Organize storage with logical names like `home:`, `uploads:`, `s3:`
- **Intuitive API** - Pathlib-inspired interface that feels natural and Pythonic
- **Flexible configuration** - Load mounts from YAML, JSON, databases, or code
- **Test-friendly** - In-memory backend for fast, isolated testing
- **Production-ready** - Built on 6+ years of Genropy production experience
- **Lightweight core** - Optional backends installed only when needed
- **Cross-storage operations** - Copy/move files between different storage types seamlessly

## Why genro-storage vs raw fsspec?

While **fsspec** is powerful, genro-storage provides:

- **Mount point abstraction** - Work with logical names instead of full URIs
- **Simpler API** - Less verbose, more intuitive for common operations
- **Configuration management** - Load storage configs from files or databases
- **Enhanced utilities** - Cross-storage copy, unified error handling, helper methods

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
    {'name': 'backups', 'type': 'gcs', 'bucket': 'my-backups'}
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
```

## Installation

> **Note:** Not yet published on PyPI. Installation instructions will be available after first release.

```bash
# Future installation (not yet available)
pip install genro-storage
```

## Documentation

- [API Design Specification](API_DESIGN.md) - Complete API reference
- [ReadTheDocs](https://genro-storage.readthedocs.io/) - Full documentation (in progress)
- Quick Start Guide (coming soon)
- Configuration Guide (coming soon)
- Backend Implementations (coming soon)

## Built With

- [fsspec](https://filesystem-spec.readthedocs.io/) - Pythonic filesystem abstraction (20+ backends)
- Modern Python (3.9+) with full type hints
- Zero dependencies for core functionality (fsspec installed on demand)

## Origins

genro-storage is extracted and modernized from [Genropy](https://github.com/genropy/genropy), a Python web framework with 6+ years of production battle-testing. We're making this powerful storage abstraction available as a standalone library for the wider Python community.

## Development Status

**Current Phase:** Design & Testing

- [x] API Design Document
- [x] ReadTheDocs Setup
- [x] Comprehensive Test Suite (200+ tests)
- [ ] Core Implementation (in progress)
- [ ] Documentation Completion
- [ ] First Public Release

**Timeline:** Aiming for v0.1.0 release in Q1 2025

## Contributing

We welcome contributions! However, please note the library is still in early development. 

For now:
- Review the [API Design Document](API_DESIGN.md)
- Check the [test suite](tests/) to understand expected behavior
- Wait for core implementation before submitting code PRs
- Bug reports and suggestions are welcome via GitHub Issues

## License

MIT License - See [LICENSE](LICENSE) for details

---

**Made with ❤️ by the Genropy team**
