# Comparison: genro-storage vs genropy storage.py

**Document Version:** 1.0
**Date:** 2025-10-27
**Original genropy storage:** `/Users/fporcari/Development/genropy/gnrpy/gnr/lib/services/storage.py`

---

## Executive Summary

**genro-storage** is a modernized, standalone Python storage library that reimplements the core functionality of genropy's `storage.py` with significant improvements in architecture, testing, and cloud storage support. However, it lacks deep integration with the genropy ecosystem (Bag system, GnrBaseService, WSGI serving).

**Status:**
- ✅ Core file operations: Complete and improved
- ✅ Cloud storage: Enhanced (S3 versioning, presigned URLs, metadata)
- ⚠️ genropy integration: Missing (Bag, Service system, WSGI)
- ❌ Advanced features: Missing (StorageResolver, sync, call, serve)

---

## Architecture Comparison

### genropy storage.py (Original)

**File:** Single monolithic file (957 lines)
**Architecture:** Integrated service within genropy framework
**Base Classes:**
- `GnrBaseService` - Genropy service integration
- `BaseServiceType` - Service factory with `conf_*()` methods

**Key Components:**
1. `ServiceType` - Configuration factory for predefined storage types
2. `StorageService` - Abstract base for storage implementations
3. `BaseLocalService` - Local filesystem implementation
4. `StorageNode` - File/directory representation
5. `StorageResolver` - Directory-to-Bag conversion
6. `XmlStorageResolver` / `TxtStorageResolver` - File content resolvers
7. `ExitStack` - Custom context manager implementation

**Integration Points:**
- `self.parent` - Reference to parent service manager
- `self.site` - Site instance integration
- `external_host` - URL generation for web apps
- Bag system - Directory navigation as Bag structures

### genro-storage (New Implementation)

**Structure:** Modular package (multiple files)
**Architecture:** Standalone library with plugin backends
**Base Classes:**
- `StorageBackend` - Abstract backend interface
- No dependency on genropy framework

**File Structure:**
```
genro_storage/
├── __init__.py              # Public API
├── manager.py               # StorageManager (18.6 KB)
├── node.py                  # StorageNode (27.1 KB)
├── exceptions.py            # Exception hierarchy
└── backends/
    ├── base.py              # Abstract StorageBackend
    ├── local.py             # LocalStorage
    ├── base64.py            # Base64Backend
    └── fsspec.py            # FsspecBackend (S3, GCS, Azure, HTTP)
```

**Key Components:**
1. `StorageManager` - Configuration and mount point management
2. `StorageNode` - Enhanced file/directory operations
3. Backend system - Pluggable storage implementations
4. Exception hierarchy - Dual inheritance with standard Python exceptions

**Integration Points:**
- None - Fully standalone
- Configuration via YAML/JSON/list
- Mount point system (Unix-like paths)

---

## Feature Comparison Matrix

### ✅ Features Present in Both

| Feature | genropy | genro-storage | Notes |
|---------|---------|---------------|-------|
| Local filesystem | ✓ | ✓ | Enhanced in genro-storage |
| File read/write | ✓ | ✓ | Binary and text modes |
| Directory operations | ✓ | ✓ | mkdir, children, listdir |
| File metadata | ✓ | ✓ | size, mtime, exists |
| Copy operations | ✓ | ✓ | Cross-backend support |
| Move operations | ✓ | ✓ | Cross-backend support |
| Delete operations | ✓ | ✓ | Files and directories |
| Open context manager | ✓ | ✓ | Both implement |
| local_path() | ✓ | ✓ | Enhanced in genro-storage |
| URL generation | ✓ | ✓ | Different approaches |
| internal_url() | ✓ | ✓ | genro-storage missing external_host |
| Base64 encoding | ✓ | ✓ | genro-storage has writable Base64Backend |
| File extensions | ✓ | ✓ | Different naming (ext vs suffix) |
| Basename operations | ✓ | ✓ | Similar functionality |
| Path normalization | ✓ | ✓ | genro-storage more robust |

### ❌ Features MISSING in genro-storage

| Feature | Location in genropy | Impact | Priority |
|---------|---------------------|--------|----------|
| **StorageResolver** | Lines 807-928 | 🔴 Critical | HIGH |
| **XmlStorageResolver** | Lines 946-956 | 🔴 Critical | HIGH |
| **TxtStorageResolver** | Lines 936-944 | 🔴 Critical | HIGH |
| **serve() method** | Lines 606-633, 771-797 | 🔴 Critical | HIGH |
| **Symbolic storage** | Lines 162-195 | 🔴 Critical | HIGH |
| **sync_to_service()** | Lines 415-443 | ✅ **Replaced by copy() skip strategies** | N/A |
| **call() method** | Lines 636-666 | 🔴 Critical | HIGH |
| **ServiceType factory** | Lines 150-195 | 🟡 Medium | MEDIUM |
| **GnrBaseService integration** | Throughout | 🟡 Medium | MEDIUM |
| **Tag system** | Line 680 | 🟡 Medium | MEDIUM |
| **ext_attributes property** | Lines 282-283, 709-711 | 🟡 Medium | MEDIUM |
| **symbolic_url()** | Lines 500-501 | 🟢 Low | LOW |
| **ExitStack custom** | Lines 28-138 | 🟢 Low | LOW |
| **NotExistingStorageNode** | Lines 21-22 | ✅ Has equivalent | N/A |

### ✨ Features ONLY in genro-storage (Improvements)

| Feature | Description | Benefit |
|---------|-------------|---------|
| **MD5-based equality** | `node1 == node2` compares content | Content verification |
| **Path operator `/`** | `node / 'child'` navigation | Pythonic API |
| **Copy skip strategies** | `skip='hash'`, `'size'`, `'exists'` | Intelligent incremental backups |
| **Copy callbacks** | `progress`, `on_file`, `on_skip` | Progress tracking & logging |
| **Writable Base64Backend** | Write returns new base64 path | Inline data handling |
| **S3 versioning** | Full version history support | Cloud-native features |
| **Presigned URLs** | S3/GCS temporary URLs | Secure sharing |
| **Callable paths** | Dynamic path resolution | Multi-user support |
| **fill_from_url()** | Download from HTTP URLs | Data ingestion |
| **to_base64()** | Convert files to data URIs | Embedding support |
| **Structured metadata** | get_metadata/set_metadata | Cloud metadata |
| **Mode-aware local_path()** | 'r', 'w', 'rw' modes | Optimized transfers |
| **Streaming (8MB chunks)** | Large file handling | Performance |
| **Exception hierarchy** | Dual inheritance design | Python compatibility |
| **Type hints** | Full type annotations | IDE support |
| **Comprehensive tests** | 160 passing tests | Code quality |
| **fsspec integration** | 20+ storage protocols | Extensibility |

---

## Critical Missing Features (Detailed)

### 1. StorageResolver System

**What it does (genropy):**
```python
# Convert storage directory to navigable Bag
storage_resolver = StorageResolver(
    storageNode('home:/documents'),
    ext='pdf,docx',
    include='*.pdf',
    exclude='draft_*'
)
bag = storage_resolver()  # Returns Bag with filtered files

# Automatically processes files by extension
# - .xml files become XmlStorageResolver (Bag from XML)
# - .txt files become TxtStorageResolver (text content)
# - directories become nested StorageResolver
```

**Why it's critical:**
- Core genropy pattern for file navigation
- Enables directory browsing in UI
- Filter/process files declaratively
- Integration with Bag system (fundamental to genropy)

**genro-storage equivalent:** ❌ None

**Workaround:**
```python
# Manual implementation needed
def list_files_as_dict(node, ext_filter=None):
    result = {}
    for child in node.children():
        if ext_filter and child.suffix not in ext_filter:
            continue
        result[child.basename] = child
    return result
```

---

### 2. serve() Method (WSGI Integration)

**What it does (genropy):**
```python
# In WSGI application
def __call__(self, environ, start_response):
    storage_node = self.storageNode('uploads:/file.pdf')
    return storage_node.serve(
        environ,
        start_response,
        download=True,
        download_name='report.pdf'
    )
```

**Features:**
- ETag support (304 Not Modified responses)
- Cache-Control headers
- Content-Disposition for downloads
- Integration with paste.fileapp
- Efficient file streaming

**genro-storage equivalent:** ❌ None

**Workaround:**
```python
# Manual WSGI implementation needed
from werkzeug.utils import send_file

def serve_file(storage, path):
    node = storage.node(path)
    with node.local_path() as local_path:
        return send_file(local_path)
```

---

### 3. Symbolic Storage Backend

**What it does (genropy):**
```python
# Symbolic storage - virtual mapping without physical path
service_config = {
    'rsrc': {'implementation': 'symbolic'},
    'pkg': {'implementation': 'symbolic'},
    'page': {'implementation': 'symbolic'}
}

# Used for virtual resource resolution
# No actual files, just logical paths
```

**Why it's critical:**
- Genropy uses symbolic storage for resource resolution
- Virtual filesystem paths
- Framework internals depend on it

**genro-storage equivalent:** ❌ None

---

### 4. sync_to_service() Method

**What it does (genropy):**
```python
# Sync entire storage service to another
home_service.sync_to_service(
    dest_service='backup',
    subpath='documents',
    skip_existing=True,
    thermo=progress_bar,
    doneCb=callback_on_complete
)
```

**Features:**
- Recursive directory sync
- Skip existing files
- Skip same-size files (optimization)
- Progress tracking
- Completion callbacks

**genro-storage equivalent:** ❌ None

**Workaround:**
```python
def sync_directories(src_node, dest_node):
    for child in src_node.children():
        dest_child = dest_node / child.basename
        if child.isfile:
            if not dest_child.exists:
                child.copy(dest_child)
        elif child.isdir:
            dest_child.mkdir()
            sync_directories(child, dest_child)
```

---

### 5. call() Method (External Process Integration)

**What it does (genropy):**
```python
# Run external command on storage files
# Automatically manages local_path for cloud files
video = storage.node('s3:/video.mp4')
output = storage.node('s3:/output.mp4')

storage.call(
    args=['ffmpeg', '-i', video, output],
    cb=on_complete,
    run_async=True
)
```

**Features:**
- Automatic local_path management for all arguments
- Async execution with threading
- Callbacks on completion
- Returns subprocess output

**genro-storage equivalent:** ❌ None

**Workaround:**
```python
import subprocess

video = storage.node('s3:/video.mp4')
with video.local_path() as local_video:
    subprocess.run(['ffmpeg', '-i', local_video, 'output.mp4'])
```

---

### 6. ServiceType Factory Pattern

**What it does (genropy):**
```python
class ServiceType(BaseServiceType):
    def conf_home(self):
        return dict(implementation='local', base_path=self.site.site_static_dir)

    def conf_mail(self):
        return dict(implementation='local', base_path='%s/mail' % self.site.site_static_dir)

    def conf_uploads(self):
        return dict(implementation='s3', bucket='my-uploads')
```

**Why it's useful:**
- Predefined storage configurations
- Site-aware paths
- Convention over configuration
- Easy service registration

**genro-storage equivalent:** ❌ None (manual configuration only)

---

## Integration Gaps

### 1. Bag System Integration

**genropy:**
```python
# StorageResolver converts directories to Bag
resolver = StorageResolver(storage_node)
bag = resolver()  # Returns Bag
bag['subdir']['file.xml']  # Navigate as Bag
```

**genro-storage:**
```python
# No Bag integration - manual navigation only
node = storage.node('mount:/path')
children = node.children()  # Returns list of StorageNode
```

**Impact:** Cannot use storage directories in places expecting Bag structures

---

### 2. Site Integration

**genropy:**
```python
# Storage services know about site
service.parent.external_host  # "https://myapp.com"
service.parent.cache_max_age  # Cache settings
self.site.site_static_dir     # Site paths
```

**genro-storage:**
```python
# No site concept - standalone
# Must configure URLs/paths manually
```

**Impact:** Cannot automatically generate correct URLs for web applications

---

### 3. GnrBaseService Integration

**genropy:**
```python
# StorageService inherits from GnrBaseService
class StorageService(GnrBaseService):
    # Lifecycle management
    # Service registration
    # Parent service access
```

**genro-storage:**
```python
# Standalone - not a service
# No lifecycle management
# No parent service concept
```

**Impact:** Cannot be used as drop-in replacement in genropy service system

---

## API Differences

### StorageNode Properties

| Property | genropy | genro-storage | Notes |
|----------|---------|---------------|-------|
| `.ext` | ✓ | ❌ | Use `.suffix` instead |
| `.suffix` | ❌ | ✓ | Returns `.pdf` (with dot) |
| `.basename` | ✓ | ✓ | Same |
| `.cleanbasename` | ✓ | ❌ | Use `.stem` instead |
| `.stem` | ❌ | ✓ | Filename without extension |
| `.dirname` | ✓ | ❌ | Use `.parent.fullpath` |
| `.parent` | ❌ (`.parentStorageNode`) | ✓ | Returns parent node |
| `.fullpath` | ✓ | ✓ | Same concept |
| `.internal_path` | ✓ | ❌ | Backend-specific |
| `.exists` | ✓ | ✓ | Same |
| `.isfile` | ✓ | ✓ | Same |
| `.isdir` | ✓ | ✓ | Same |
| `.size` | ✓ | ✓ | Same |
| `.mtime` | ✓ | ✓ | Same |
| `.md5hash` | ✓ | ✓ | Enhanced in genro-storage |
| `.ext_attributes` | ✓ | ❌ | Returns `(mtime, size, isdir)` |
| `.versions` | ✓ | ✓ | S3 versioning |
| `.mimetype` | ✓ | ❌ | Use `mimetypes.guess_type()` |

### StorageNode Methods

| Method | genropy | genro-storage | Notes |
|--------|---------|---------------|-------|
| `.open(mode)` | ✓ | ✓ | Same |
| `.read_bytes()` | ❌ | ✓ | New convenience method |
| `.read_text()` | ❌ | ✓ | New convenience method |
| `.write_bytes()` | ❌ | ✓ | New convenience method |
| `.write_text()` | ❌ | ✓ | New convenience method |
| `.delete()` | ✓ | ✓ | Same |
| `.copy(dest)` | ✓ | ✓ | Enhanced in genro-storage |
| `.move(dest)` | ✓ | ✓ | Updates source node in place |
| `.mkdir()` | ✓ | ✓ | Same |
| `.children()` | ✓ | ✓ | Same |
| `.listdir()` | ✓ | ❌ | Use `[c.basename for c in children()]` |
| `.child(path)` | ✓ | ✓ | Same |
| `.local_path()` | ✓ | ✓ | Enhanced with mode in genro-storage |
| `.url()` | ✓ | ✓ | Different implementations |
| `.internal_url()` | ✓ | ✓ | Missing external_host in genro-storage |
| `.serve()` | ✓ | ❌ | **MISSING** |
| `.base64()` | ✓ (method) | ❌ | Use `.to_base64()` |
| `.to_base64()` | ❌ | ✓ | New method name |
| `.fill_from_url()` | ✓ | ✓ | Enhanced in genro-storage |
| `.get_metadata()` | ✓ | ✓ | Enhanced in genro-storage |
| `.set_metadata()` | ✓ | ✓ | Enhanced in genro-storage |
| `.open_version()` | ❌ | ✓ | New S3 feature |
| `.splitext()` | ✓ | ❌ | Use `.stem` and `.suffix` |
| `.__truediv__()` | ❌ | ✓ | Supports `node / 'child'` |
| `.__eq__()` | ❌ | ✓ | Content comparison via MD5 |

---

## Configuration Comparison

### genropy Configuration

```python
# Via ServiceType factory methods
class ServiceType(BaseServiceType):
    def conf_home(self):
        return dict(
            implementation='local',
            base_path=self.site.site_static_dir
        )

    def conf_uploads(self):
        return dict(
            implementation='s3',
            bucket='my-uploads',
            region='eu-west-1'
        )

# Automatic registration with service system
# Site-aware paths
# Convention-based naming
```

### genro-storage Configuration

```python
# YAML file
- name: home
  type: local
  path: /var/app/static

- name: uploads
  type: s3
  bucket: my-uploads
  region: eu-west-1

# Or programmatic
storage.configure([
    {'name': 'home', 'type': 'local', 'path': '/var/app/static'},
    {'name': 'uploads', 'type': 's3', 'bucket': 'my-uploads'}
])

# Manual configuration
# No site integration
# Explicit mount names
```

---

## Use Case Compatibility

### ✅ Works in Both (Compatible)

```python
# Basic file operations
node = storage.node('home:/documents/file.pdf')
content = node.read_bytes()
node.write_bytes(b'new content')
node.delete()

# Copy/move
node.copy(storage.node('backup:/file.pdf'))
node.move(storage.node('archive:/file.pdf'))

# Directory operations
for child in node.children():
    print(child.basename)

# Cloud storage
s3_node = storage.node('s3:/uploads/image.jpg')
url = s3_node.url()  # Presigned URL
```

### ❌ Only Works in genropy

```python
# StorageResolver for directory browsing
from gnr.lib.services.storage import StorageResolver
resolver = StorageResolver(storage_node, ext='pdf,docx')
file_bag = resolver()

# WSGI serving
def wsgi_app(environ, start_response):
    node = storage.node('uploads:/file.pdf')
    return node.serve(environ, start_response, download=True)

# Service synchronization
home_service.sync_to_service('backup', skip_existing=True)

# External process integration
storage.call(['ffmpeg', '-i', video_node, output_node], run_async=True)

# Symbolic storage
symbolic_node = storage.node('rsrc:/virtual/path')

# Site-aware URLs
url = node.internal_url(nocache=True)  # Uses site.external_host
```

### ✨ Only Works in genro-storage

```python
# Content comparison
if node1 == node2:
    print("Files have identical content")

# Path operator
config = base_dir / 'config' / 'app.yaml'

# S3 versioning
for version in s3_node.versions:
    with s3_node.open_version(version['version_id']) as f:
        old_content = f.read()

# Callable paths (multi-user)
def get_user_dir():
    return f'/data/users/{current_user_id()}'

storage.configure([
    {'name': 'user', 'type': 'local', 'path': get_user_dir}
])

# Mode-aware local_path
with node.local_path(mode='r') as path:  # Download only
    process_file(path)

with node.local_path(mode='w') as path:  # Upload only
    create_file(path)

# Download from URL
node.fill_from_url('https://example.com/file.pdf', timeout=30)

# Base64 data URIs
data_uri = node.to_base64()  # data:image/png;base64,...
```

---

## Migration Path

### If Migrating FROM genropy TO genro-storage

**Required Changes:**

1. **Replace StorageResolver usage:**
   ```python
   # OLD (genropy)
   resolver = StorageResolver(node, ext='pdf')
   bag = resolver()

   # NEW (genro-storage)
   files = {c.basename: c for c in node.children() if c.suffix == '.pdf'}
   ```

2. **Replace serve() calls:**
   ```python
   # OLD (genropy)
   return node.serve(environ, start_response)

   # NEW (genro-storage)
   from werkzeug.utils import send_file
   with node.local_path() as path:
       return send_file(path)
   ```

3. **Replace property names:**
   ```python
   # OLD (genropy)
   ext = node.ext
   name = node.cleanbasename

   # NEW (genro-storage)
   ext = node.suffix.lstrip('.')
   name = node.stem
   ```

4. **Update configuration:**
   ```python
   # OLD (genropy) - via ServiceType
   # Automatic based on conf_* methods

   # NEW (genro-storage) - explicit
   storage.configure('storage_config.yaml')
   ```

5. **Remove symbolic storage references:**
   ```python
   # No direct replacement - requires architecture change
   ```

### If Adding genro-storage Features TO genropy

**Recommended Additions:**

1. **Add equality comparison:**
   ```python
   def __eq__(self, other):
       if not isinstance(other, StorageNode):
           return False
       return self.md5hash == other.md5hash
   ```

2. **Add path operator:**
   ```python
   def __truediv__(self, other):
       return self.child(other)
   ```

3. **Add convenience methods:**
   ```python
   def read_bytes(self):
       with self.open('rb') as f:
           return f.read()

   def write_bytes(self, data):
       with self.open('wb') as f:
           f.write(data)
   ```

4. **Enhance S3 versioning:**
   ```python
   def open_version(self, version_id, mode='rb'):
       # Implementation using boto3
   ```

5. **Add type hints:**
   ```python
   from typing import Optional, Union, List

   def copy(self, dest: Union[str, 'StorageNode']) -> 'StorageNode':
       ...
   ```

---

## Testing Comparison

### genropy Testing

**Status:** ⚠️ Unknown (tests not found in storage.py)

### genro-storage Testing

**Status:** ✅ Comprehensive (106 passing tests)

**Test Coverage:**
- `test_local_storage.py` - Local filesystem operations
- `test_base64.py` - Base64 backend
- `test_md5_and_equality.py` - Content comparison
- `test_advanced_features.py` - Advanced features (URL, metadata, versioning)
- `test_s3_integration.py` - S3 integration tests

**Test Infrastructure:**
- pytest fixtures
- Temporary directories
- Mock S3 (moto)
- Comprehensive assertions

---

## Performance Considerations

### genropy

- Local-to-local copy uses `shutil.copy2()` ✅
- No streaming for large files ⚠️
- ETag support for HTTP caching ✅
- No chunk-based processing ⚠️

### genro-storage

- Local-to-local copy uses `shutil.copy2()` ✅
- 8MB chunk streaming for large files ✅
- No ETag support (no serve method) ❌
- Efficient cloud metadata retrieval ✅
- Content-based comparison caching ✅

---

## Recommendations

### For New Projects (Starting Fresh)

**Use genro-storage if:**
- ✅ You need modern Python features (type hints, pathlib-style API)
- ✅ You want comprehensive testing
- ✅ You need advanced cloud features (versioning, presigned URLs)
- ✅ You don't need Bag integration
- ✅ You want standalone library (no framework dependency)

**Use genropy storage.py if:**
- ✅ You need Bag integration
- ✅ You need WSGI serving
- ✅ You need symbolic storage
- ✅ You're building within genropy ecosystem
- ✅ You need StorageResolver

### For Existing genropy Projects

**Migration Strategy:**

1. **Phase 1:** Add genro-storage alongside genropy storage
2. **Phase 2:** Use genro-storage for new features
3. **Phase 3:** Implement missing features in genro-storage
4. **Phase 4:** Gradually migrate existing code
5. **Phase 5:** Remove genropy storage dependency

**Critical Features to Implement First:**
1. StorageResolver (for Bag integration)
2. serve() method (for WSGI)
3. ServiceType factory (for configuration)
4. Symbolic storage (for resource resolution)

### For Contributing to genro-storage

**High-Priority Features:**
1. ✅ StorageResolver implementation
2. ✅ serve() method with ETag support
3. ✅ Symbolic backend
4. ✅ sync_to_service() method
5. ✅ call() method for external processes

**Medium-Priority Features:**
1. ServiceType factory pattern
2. Tag system
3. ext_attributes property
4. Better genropy integration hooks

**Low-Priority Features:**
1. symbolic_url() method
2. Custom ExitStack (can use stdlib)

---

## Conclusion

**genro-storage** represents a significant modernization of storage handling with:
- Better architecture (modular, testable)
- Enhanced cloud support (versioning, metadata, presigned URLs)
- Pythonic API (type hints, operators, properties)
- Comprehensive testing (106 tests)

However, it **cannot be a drop-in replacement** for genropy storage.py due to:
- Missing Bag integration (StorageResolver)
- Missing WSGI serving (serve method)
- Missing service system integration
- No symbolic storage support

**Ideal Future State:** genro-storage as the core library with genropy-specific adapters for Bag/Service integration.

---

## Document Maintenance

**To update this document:**

1. Read original genropy storage:
   ```bash
   cat /Users/fporcari/Development/genropy/gnrpy/gnr/lib/services/storage.py
   ```

2. Compare with genro-storage:
   ```bash
   cd /Users/fporcari/Development/genro-ng/genro-storage
   find genro_storage -name "*.py" -type f
   ```

3. Update relevant sections in this document

4. Commit changes:
   ```bash
   git add COMPARISON_WITH_GENROPY.md
   git commit -m "docs: Update comparison document"
   ```

---

**End of Document**
