# Claude Code Instructions - genro-storage

**Parent Document**: This project follows all policies from the central [genro-next-generation CLAUDE.md](https://github.com/genropy/genro-next-generation/blob/main/CLAUDE.md)

Read the parent document first for:
- Language policy (English only)
- Git commit authorship rules (no Claude co-author)
- Development status lifecycle (Pre-Alpha → Alpha → Beta)
- Temporary files policy (use temp/ directories)
- Standardization requirements
- All general project policies

## Project-Specific Context

### Current Status
- **Development Status**: Beta
- **Has Implementation Code**: Yes
- **Version**: 0.4.3
- **Python Support**: 3.9, 3.10, 3.11, 3.12
- **Test Coverage**: 85% (411 tests: 401 passing, 10 skipped)
- **GitHub**: https://github.com/genropy/genro-storage

### Project Purpose

Universal storage abstraction for Python with pluggable backends. Provides unified interface for accessing files across local filesystems, cloud storage (S3, GCS, Azure), and remote protocols (HTTP). Built on top of fsspec with an intuitive mount-point system.

### Project Structure

```
genro-storage/
├── genro_storage/          # Main package
│   ├── __init__.py        # Public API exports
│   ├── manager.py         # StorageManager - main entry point
│   ├── node.py            # StorageNode - file/directory abstraction
│   ├── capabilities.py    # Backend capability system
│   ├── exceptions.py      # Custom exceptions
│   ├── asyncer_wrapper.py # Async support wrapper
│   └── backends/          # Storage backend implementations
│       ├── base.py        # Abstract backend interface
│       └── fsspec_backend.py  # Unified fsspec-based backend
├── tests/                 # Comprehensive test suite
├── docs/                  # ReadTheDocs documentation
├── API_DESIGN.md         # Detailed API specification
└── TESTING.md            # Testing instructions with MinIO
```

### Key Components

**StorageManager** (`manager.py`):
- Main entry point for the library
- Manages mount points (named storage backends)
- Factory for creating StorageNode instances
- Configuration loading from YAML/JSON/dict

**StorageNode** (`node.py`):
- Represents a file or directory
- Unified API: `read()`, `write()`, `copy()`, `exists`, `list()`, `call()`, `serve()`
- Intelligent copy strategies: exists, size, hash

**Supported Backends** (15 total):
- Local filesystem, S3, GCS, Azure, HTTP
- Memory, Base64, SMB, SFTP
- ZIP, TAR, Git, GitHub, WebDAV, LibArchive

### Important Features

1. **Mount Point System**: Logical names (`home:`, `uploads:`, `s3:`) instead of full URIs
2. **Intelligent Copy**: Skip strategies for efficient backups
3. **External Tool Integration**: `call()` method for ffmpeg, imagemagick, pandoc
4. **WSGI Serving**: `serve()` method for Flask, Django, Pyramid with ETag caching
5. **Base64 Backend**: Embed data inline with writable paths
6. **Cloud Metadata**: Get/set custom metadata on S3, GCS, Azure
7. **Callable Paths**: Dynamic path resolution at runtime
8. **Async Support**: AsyncStorageManager available

### Architecture Notes

- Built on fsspec for battle-tested storage backends
- Originated from Genropy framework (19+ years in production, storage since 2018)
- Type-hinted codebase with full mypy support
- Available on PyPI

### Testing Approach

**Unit Tests**: Fast, no external dependencies
```bash
pytest tests/test_local_storage.py -v
```

**Integration Tests**: Require Docker + MinIO (S3-compatible)
```bash
docker-compose up -d
pytest tests/test_s3_integration.py -v
```

**Full Test Suite**:
```bash
pytest tests/ -v --cov=genro_storage
```

### Configuration Examples

```python
from genro_storage import StorageManager

storage = StorageManager()
storage.configure([
    {'name': 'home', 'type': 'local', 'path': '/home/user'},
    {'name': 'uploads', 'type': 's3', 'bucket': 'my-app-uploads'},
    {'name': 'backups', 'type': 'gcs', 'bucket': 'my-backups'},
])

# Use mount points
node = storage.node('uploads:documents/file.pdf')
content = node.read()
```

### Development Guidelines

**Code Quality**:
```bash
# Format
black genro_storage/ tests/

# Lint
ruff check genro_storage/ tests/

# Type check
mypy genro_storage/
```

**Documentation**:
- Keep API_DESIGN.md updated for major API changes
- Update docstrings for all public methods
- ReadTheDocs auto-builds from main branch

**Performance**:
- Use cloud metadata (S3 ETag) when available for hashing
- Implement efficient copy strategies
- Test with large files in integration tests

### Dependencies

- `fsspec>=2023.1.0` - Core backend support
- `PyYAML>=6.0` - Configuration file support
- Optional: `s3fs`, `gcsfs`, `adlfs`, `aiohttp`, `smbprotocol`, `paramiko`, `webdav4`, `libarchive-c`, `asyncer`

### Related Documentation

- [API Design](https://github.com/genropy/genro-storage/blob/main/API_DESIGN.md)
- [Testing Guide](https://github.com/genropy/genro-storage/blob/main/TESTING.md)
- [ReadTheDocs](https://genro-storage.readthedocs.io)
- [Jupyter Notebooks](https://github.com/genropy/genro-storage/tree/main/notebooks)

---

**All general policies are inherited from the parent document: `/Users/gporcari/Sviluppo/genro_ng/CLAUDE.md`**

**Last Updated**: 2025-10-30
