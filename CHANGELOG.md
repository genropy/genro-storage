# Changelog

All notable changes to genro-storage will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure
- Core StorageManager and StorageNode implementation
- FsspecBackend generic wrapper for all storage backends
- Support for 6 storage backends: local, S3, GCS, Azure, HTTP, Memory
- Comprehensive test suite (54+ tests)
- MinIO integration for S3 testing
- Full documentation on ReadTheDocs
- GitHub Actions CI/CD pipelines
- Docker Compose setup for local testing

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- N/A (initial release)

## [0.1.0-alpha] - 2025-10-27

### Added
- Initial alpha release
- Core API implementation
- Local filesystem backend (via fsspec)
- S3 backend (tested with MinIO)
- Memory backend for testing
- 54+ tests with 81% coverage
- Complete documentation
- CI/CD with GitHub Actions

### Known Issues
- GCS and Azure backends not yet tested in CI
- HTTP backend needs integration tests
- Coverage could be improved to 90%+
- No async support yet

### Breaking Changes
- N/A (initial release)

---

## Release Types

- **Major version** (1.0.0): Breaking API changes
- **Minor version** (0.1.0): New features, backwards compatible
- **Patch version** (0.1.1): Bug fixes, backwards compatible
- **Pre-release** (0.1.0-alpha, 0.1.0-beta, 0.1.0-rc1): Development versions

## Links

- [PyPI](https://pypi.org/project/genro-storage/) (coming soon)
- [Documentation](https://genro-storage.readthedocs.io/)
- [Repository](https://github.com/genropy/genro-storage)
- [Issue Tracker](https://github.com/genropy/genro-storage/issues)

[Unreleased]: https://github.com/genropy/genro-storage/compare/v0.1.0-alpha...HEAD
[0.1.0-alpha]: https://github.com/genropy/genro-storage/releases/tag/v0.1.0-alpha
