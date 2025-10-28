# genro-storage - Claude Code Context

## Project Overview

**genro-storage** is a universal storage abstraction library for Python that provides a unified interface for accessing files across local filesystems, cloud storage (S3, GCS, Azure), and remote protocols (HTTP). Built on top of fsspec, it adds an intuitive mount-point system inspired by Unix filesystems.

## Current Status

- **Version:** 0.1.0-beta
- **Development Phase:** Beta - Ready for Production Testing
- **Python Support:** 3.9, 3.10, 3.11, 3.12
- **Test Coverage:** 195 tests passing, 79% coverage
- **License:** MIT

## Project Structure

```
genro-storage/
├── genro_storage/          # Main package
│   ├── __init__.py        # Public API exports
│   ├── manager.py         # StorageManager - main entry point
│   ├── node.py            # StorageNode - file/directory abstraction
│   ├── config.py          # Configuration and mount point management
│   └── backends/          # Storage backend implementations
│       ├── __init__.py
│       ├── base.py        # Abstract backend interface
│       └── fsspec_backend.py  # Unified fsspec-based backend
├── tests/                 # Test suite
│   ├── test_local_storage.py
│   ├── test_s3_integration.py
│   ├── test_copy_strategies.py
│   ├── test_call_serve_mimetype.py
│   └── ...
├── docs/                  # Documentation (ReadTheDocs)
├── API_DESIGN.md         # Detailed API specification
├── TESTING.md            # Testing instructions
└── pyproject.toml        # Build configuration
```

## Key Components

### StorageManager (`manager.py`)
- Main entry point for the library
- Manages mount points (named storage backends)
- Factory for creating StorageNode instances
- Configuration loading from YAML/JSON/dict

### StorageNode (`node.py`)
- Represents a file or directory
- Unified API for all storage backends
- Key methods: `read()`, `write()`, `copy()`, `exists`, `list()`, `call()`, `serve()`
- Supports intelligent copy strategies: exists, size, hash

### FsspecBackend (`backends/fsspec_backend.py`)
- Unified backend implementation using fsspec
- Supports: local, S3, GCS, Azure, HTTP, memory, base64
- Handles all low-level filesystem operations

## Important Features

1. **Mount Point System**: Logical names like `home:`, `uploads:`, `s3:` instead of full URIs
2. **Intelligent Copy**: Skip strategies (exists/size/hash) for efficient backups
3. **External Tool Integration**: `call()` method for ffmpeg, imagemagick, etc.
4. **WSGI Serving**: `serve()` method for Flask, Django, Pyramid
5. **Base64 Backend**: Embed data inline with writable paths
6. **Cloud Metadata**: Get/set custom metadata on cloud files
7. **Callable Paths**: Dynamic path resolution at runtime

## Architecture Notes

- Built on fsspec for battle-tested storage backends
- Originated from Genropy framework (19+ years in production, storage since 2018)
- Type-hinted codebase with mypy support
- Async support planned for v0.2.0

## Testing Approach

- Unit tests: Fast, no external dependencies (tests/test_local_storage.py)
- Integration tests: Require Docker + MinIO (tests/test_s3_integration.py)
- CI/CD: GitHub Actions with Python 3.9-3.12 matrix
- Use pytest with coverage reporting

## Git and Commit Policies

**IMPORTANT**: When creating commits:
- **DO NOT** include Claude Code attribution in commit messages
- **DO NOT** add "Co-Authored-By: Claude" footer
- **DO NOT** add "Generated with Claude Code" messages
- Keep commit messages clean and professional
- Follow the repository's existing commit message style

## Code Language Policy

**IMPORTANT**: All code and documentation must be in English:
- **ALL code** must be written in English (variables, functions, classes, etc.)
- **ALL comments** must be in English
- **ALL docstrings** must be in English
- **ALL commit messages** must be in English
- No exceptions - this is a strict requirement for consistency and international collaboration

## Development Phase Policy

**IMPORTANT**: The project is in active construction (Beta phase):
- **DO NOT** worry about backward compatibility - breaking changes are acceptable
- **DO NOT** maintain extensive change history in documentation - focus on current state
- **DO NOT** preserve deprecated code or legacy patterns
- **DO** refactor freely to improve design and architecture
- **DO** focus on getting the API right, even if it means breaking changes
- **DO** keep documentation focused on the current version, not historical versions
- Once we reach v1.0.0, backward compatibility will become a priority

## Configuration Examples

```python
storage = StorageManager()
storage.configure([
    {'name': 'home', 'type': 'local', 'path': '/home/user'},
    {'name': 'uploads', 'type': 's3', 'bucket': 'my-app-uploads'},
    {'name': 'backups', 'type': 'gcs', 'bucket': 'my-backups'},
])
```

## Common Development Tasks

### Running Tests
```bash
# Unit tests only
pytest tests/test_local_storage.py -v

# With MinIO integration
docker-compose up -d
pytest tests/test_s3_integration.py -v

# All tests with coverage
pytest tests/ -v --cov=genro_storage
```

### Code Quality
```bash
# Format code
black genro_storage/ tests/

# Lint
ruff check genro_storage/ tests/

# Type check
mypy genro_storage/
```

### Documentation
```bash
cd docs/
make html
# Output in docs/_build/html/
```

## Key Design Decisions

1. **Single Backend Implementation**: FsspecBackend handles all storage types instead of separate backend classes
2. **Mutable Path for Base64**: Base64 backend updates node.path after write operations
3. **Skip Strategies**: Intelligent copy with exists/size/hash comparison
4. **Context Manager Pattern**: `local_path()` for safe temporary file handling
5. **WSGI Integration**: `serve()` returns WSGI-compatible iterables

## Important Files to Review

- `API_DESIGN.md`: Complete API specification
- `COPY_SKIP_STRATEGIES.md`: Copy strategy implementation details
- `IMPLEMENTATION_SUMMARY.md`: Core implementation notes
- `IMPLEMENTATION_SUMMARY_CALL_SERVE_MIMETYPE.md`: External tool integration details
- `COMPARISON_WITH_GENROPY.md`: Differences from original Genropy implementation

## Dependencies

**Core:**
- fsspec >= 2023.1.0
- PyYAML >= 6.0

**Optional (backends):**
- s3fs >= 2023.1.0 (S3)
- gcsfs >= 2023.1.0 (GCS)
- adlfs >= 2023.1.0 (Azure)
- aiohttp >= 3.8.0 (HTTP)

**Development:**
- pytest >= 7.0
- pytest-cov >= 4.0
- black >= 23.0
- ruff >= 0.1.0
- mypy >= 1.0
- boto3 >= 1.26.0 (MinIO testing)

## Gotchas and Special Cases

1. **Base64 Backend**: Paths are mutable after write operations
2. **S3 ETag**: Used for efficient hash comparison (avoids downloads)
3. **Callable Paths**: Resolve at access time, not configuration time
4. **HTTP Backend**: Read-only, no write support
5. **Memory Backend**: For testing, data lost when process exits

## Future Roadmap

- v0.1.0 (Q4 2025): First PyPI release (Beta)
- v0.2.0 (Q1 2026): Async support, performance optimizations
- v1.0.0 (2026): Production-ready, stable API guarantee

## Links

- **GitHub**: https://github.com/genropy/genro-storage
- **Documentation**: https://genro-storage.readthedocs.io
- **Issues**: https://github.com/genropy/genro-storage/issues
- **PyPI**: https://pypi.org/project/genro-storage/ (coming soon)
