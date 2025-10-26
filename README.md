# genro-storage

[![Python versions](https://img.shields.io/badge/python-3.9%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation Status](https://readthedocs.org/projects/genro-storage/badge/?version=latest)](https://genro-storage.readthedocs.io/en/latest/?badge=latest)
[![Tests](https://github.com/genropy/genro-storage/workflows/tests/badge.svg)](https://github.com/genropy/genro-storage/actions)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![PyPI version](https://badge.fury.io/py/genro-storage.svg)](https://badge.fury.io/py/genro-storage)

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

```bash
# Basic installation (local storage only)
pip install genro-storage

# With cloud storage support
pip install genro-storage[s3]      # Amazon S3
pip install genro-storage[gcs]     # Google Cloud Storage
pip install genro-storage[azure]   # Azure Blob Storage
pip install genro-storage[full]    # All backends
```

## Documentation

- [API Design Specification](API_DESIGN.md) - Complete API reference
- [ReadTheDocs](https://genro-storage.readthedocs.io/) - Full documentation
- Quick Start Guide
- Configuration Guide
- Backend Implementations

## Built With

- [fsspec](https://filesystem-spec.readthedocs.io/) - Pythonic filesystem abstraction (20+ backends)
- Modern Python (3.9+) with full type hints
- Zero dependencies for core functionality (fsspec installed on demand)

## Origins

genro-storage is extracted and modernized from [Genropy](https://github.com/genropy/genropy), a Python web framework with 6+ years of production battle-testing. We're making this powerful storage abstraction available as a standalone library for the wider Python community.

## Development Status

**Current Status:** Design & Testing Phase

- [x] API Design Document
- [x] ReadTheDocs Setup
- [x] Test Suite (200+ tests)
- [ ] Core Implementation
- [ ] Documentation Completion
- [ ] First Release

## License

MIT License - See [LICENSE](LICENSE) for details

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

**Made with ❤️ by the Genropy team**
