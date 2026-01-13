# Release Notes v0.2.0

**Release Date:** October 28, 2025

## 🎉 Major Features

### Virtual Nodes
- **iternode**: Lazy concatenation of multiple nodes
- **diffnode**: Unified diff generation between two nodes
- **zip()**: Create ZIP archives from files, directories, or iternodes

### Interactive Tutorials
- 8 comprehensive Jupyter notebooks covering beginner to advanced topics
- Hands-on examples with executable code
- Available via Binder for zero-setup learning

## 📚 Documentation Improvements

### Comprehensive Documentation Overhaul
- Complete API reference with all methods and parameters
- Enhanced copy() documentation with filter, skip_fn, progress callbacks
- Fixed all code examples to use correct API signatures
- Added missing methods to API reference (path property, zip() examples)
- Fixed versioning.rst to remove non-existent methods

### Tutorial Access
- Added Binder badge for one-click notebook execution
- Clear instructions for both online and local usage
- Documented that variables persist between notebook cells

### Technical Improvements
- Corrected historical timeline (Genropy since 2006, storage abstraction since 2018)
- Fixed RST heading interpretation issues in documentation
- Added Codecov badge with interactive coverage dashboard

## 🐛 Bug Fixes

- Fixed call() method examples in documentation (template string → *args pattern)
- Fixed MinIO startup in Code Quality workflow
- Simplified coverage generation in CI

## 🔧 API Changes

### New Methods
- `StorageNode.zip()` - Create ZIP archives
- `StorageManager.iternode(*nodes)` - Virtual concatenation node
- `StorageManager.diffnode(node1, node2)` - Virtual diff node

### Enhanced copy() Method
Now supports:
- `filter` parameter for custom filtering
- `skip_fn` parameter for custom skip logic
- `progress` callback for progress tracking
- `on_file` callback for per-file processing
- `on_skip` callback for skipped files

## 📊 Test Coverage

- 195 tests passing on Python 3.9-3.12
- Coverage: 79%
- Codecov integration enabled

## 🔗 Links

- **Documentation**: https://genro-storage.readthedocs.io/
- **Jupyter Tutorials**: [notebooks/](notebooks/)
- **Try Online**: [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/genropy/genro-storage/main?filepath=notebooks)
- **GitHub**: https://github.com/genropy/genro-storage

## 📦 Installation

```bash
# From PyPI
pip install genro-storage==0.2.0

# With cloud backends
pip install genro-storage[s3]==0.2.0
pip install genro-storage[gcs]==0.2.0
pip install genro-storage[azure]==0.2.0
pip install genro-storage[all]==0.2.0
```

## ⚠️ Breaking Changes

None - This release maintains full backward compatibility with v0.1.0.

## 🙏 Contributors

Thanks to everyone who contributed to this release!

---

**Full Changelog**: https://github.com/genropy/genro-storage/compare/v0.1.0-beta...v0.2.0
