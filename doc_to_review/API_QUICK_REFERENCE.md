# genro-storage - API Quick Reference

Quick reference guide for StorageManager and StorageNode APIs with signatures, descriptions, and required capabilities.

---

## StorageManager API

### Initialization & Configuration

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `__init__()` | `StorageManager()` | Create new storage manager | - |
| `configure()` | `configure(source: str \| list[dict])` | Configure mount points from file or dict list | - |
| `node()` | `node(path: str) -> StorageNode` | Get a node for the given path (format: `mount:path`) | - |

---

## StorageNode API

### File I/O Operations

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `open()` | `open(mode='r', version=None, as_of=None) -> BinaryIO \| TextIO` | Open file with optional version support | `versioning` (for version/as_of) |
| `read_bytes()` | `read_bytes() -> bytes` | Read entire file as bytes | `read` |
| `read_text()` | `read_text(encoding='utf-8') -> str` | Read entire file as string | `read` |
| `write_bytes()` | `write_bytes(data: bytes)` | Write bytes to file | `write` |
| `write_text()` | `write_text(text: str, encoding='utf-8')` | Write string to file | `write` |
| `write_bytes_if_changed()` | `write_bytes_if_changed(data: bytes) -> bool` | Write only if content differs (uses hash) | `write`, `hash_on_metadata` (optimal) |
| `write_text_if_changed()` | `write_text_if_changed(text: str, encoding='utf-8') -> bool` | Write text only if content differs | `write`, `hash_on_metadata` (optimal) |
| `delete()` | `delete(recursive=False)` | Delete file or directory | `delete` |

### Directory Operations

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `mkdir()` | `mkdir(parents=False, exist_ok=False)` | Create directory | `mkdir` |
| `list()` | `list() -> list[StorageNode]` | List directory contents | `list_dir` |
| `child()` | `child(name: str) -> StorageNode` | Get child node by name | - |
| `__truediv__()` | `node / "subpath" -> StorageNode` | Path concatenation operator | - |

### File Properties

| Property | Type | Description | Capabilities |
|----------|------|-------------|--------------|
| `exists` | `bool` | True if file/directory exists | - |
| `is_file` | `bool` | True if this is a file | - |
| `is_dir` | `bool` | True if this is a directory | - |
| `size` | `int` | File size in bytes | - |
| `mtime` | `float` | Modification time (Unix timestamp) | - |
| `md5hash` | `str` | MD5 hash (hex string) | `hash_on_metadata` (efficient) |
| `mimetype` | `str` | MIME type based on extension | - |
| `fullpath` | `str` | Full path with mount prefix | - |
| `path` | `str` | Path without mount prefix | - |
| `name` | `str` | File/directory name | - |
| `parent` | `StorageNode` | Parent directory node | - |
| `posix_path` | `PurePosixPath` | POSIX path object | - |

### Copy & Move

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `copy()` | `copy(dest, skip=SkipStrategy.NEVER, include=None, exclude=None, filter_fn=None, on_file=None, on_skip=None, progress_callback=None)` | Copy file/directory with advanced filtering | `read` (source), `write` (dest) |
| `move()` | `move(dest: StorageNode \| str) -> StorageNode` | Move file/directory and update self | `read`, `write`, `delete` |

**Copy Skip Strategies:**
- `SkipStrategy.NEVER` (default): Always copy
- `SkipStrategy.EXISTS`: Skip if destination exists
- `SkipStrategy.SIZE`: Skip if size matches
- `SkipStrategy.HASH`: Skip if MD5 hash matches
- `SkipStrategy.CUSTOM`: Use custom filter function

### Versioning Operations

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `versions` | `Property -> list[dict]` | List all versions with metadata | `versioning`, `version_listing` |
| `version_count` | `Property -> int` | Total number of versions | `versioning` |
| `open_version()` | `open_version(version_id: str, mode='r')` | Open specific version by ID | `versioning`, `version_access` |
| `diff_versions()` | `diff_versions(v1=-1, v2=-2) -> tuple[bytes, bytes]` | Get content from two versions | `versioning`, `version_access` |
| `rollback()` | `rollback(to_version=-2)` | Rollback to previous version (creates new version) | `versioning`, `version_access`, `write` |
| `compact_versions()` | `compact_versions(dry_run=False) -> int` | Remove consecutive duplicate versions | `versioning`, `version_listing` |

**Version List Format:**
```python
[
    {
        'version_id': str,      # Unique version identifier
        'is_latest': bool,      # True if this is the current version
        'last_modified': datetime,  # Timestamp
        'size': int,            # Size in bytes
        'etag': str             # ETag/hash for deduplication
    },
    ...
]
```

**Version Access:**
- By index: `open(version=-1)` (latest), `open(version=-2)` (previous), `open(version=0)` (oldest)
- By ID: `open(version='abc123xyz')`
- By datetime: `open(as_of=datetime(2024, 1, 15))`

### Metadata Operations

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `metadata` | `Property -> dict[str, str]` | Get custom metadata | `metadata` |
| `set_metadata()` | `set_metadata(metadata: dict[str, str])` | Set custom key-value metadata | `metadata`, `write` |

### URL Generation

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `url` | `Property -> str \| None` | Get public URL if available | `public_urls` |
| `get_presigned_url()` | `get_presigned_url(expires_in=3600, download=False, download_name=None) -> str` | Generate temporary signed URL | `presigned_urls` |
| `internal_url()` | `internal_url(nocache=False) -> str \| None` | Get internal URL for frameworks | `public_urls` or `presigned_urls` |

### Advanced Features

| Method | Signature | Description | Capabilities |
|--------|-----------|-------------|--------------|
| `call()` | `call(command: list, return_output=False, async_mode=False, callback=None, **kwargs) -> str \| None` | Execute external command on file | `read` (if needed by command) |
| `serve()` | `serve(mimetype=None, cache_control=None, etag=None, download=False, download_name=None) -> tuple` | Serve file for WSGI (Flask, Django, etc.) | `read` |
| `local_path()` | `local_path(mode='r') -> ContextManager[Path]` | Get local filesystem path (downloads if needed) | `read` |
| `fill_from_url()` | `fill_from_url(url: str, timeout=30)` | Download from HTTP URL | `write` |
| `to_base64()` | `to_base64(data_uri=True, mime_type=None) -> str` | Encode as base64 string | `read` |

### Comparison & Capabilities

| Method/Property | Signature | Description | Capabilities |
|-----------------|-----------|-------------|--------------|
| `__eq__()` | `node1 == node2` | Compare by MD5 hash | - |
| `capabilities` | `Property -> BackendCapabilities` | Get backend capabilities | - |

---

## Backend Capabilities

Capability attributes available on `node.capabilities`:

### Core Operations
- `read`: Supports read operations
- `write`: Supports write operations
- `delete`: Supports delete operations

### Directory Operations
- `mkdir`: Can create directories
- `list_dir`: Can list directory contents

### Versioning Support
- `versioning`: Has versioning support (S3 with versioning enabled)
- `version_listing`: Can list all versions
- `version_access`: Can access specific versions

### Metadata & URLs
- `metadata`: Supports custom key-value metadata
- `presigned_urls`: Can generate temporary signed URLs
- `public_urls`: Has public HTTP URLs

### Advanced Features
- `atomic_operations`: Guarantees atomic write operations
- `symbolic_links`: Supports symbolic links (local only)
- `copy_optimization`: Native server-side copy
- `hash_on_metadata`: MD5/ETag available without reading file
- `append_mode`: Supports append mode ('a')
- `seek_support`: File handles support seek operations

### Access Patterns
- `readonly`: Backend is read-only (HTTP)
- `temporary`: Storage is ephemeral (memory backend)

### Example Usage

```python
# Check capabilities before using features
if node.capabilities.versioning:
    versions = node.versions
    node.rollback()

if node.capabilities.metadata:
    node.set_metadata({'author': 'John', 'project': 'acme'})

if node.capabilities.presigned_urls:
    url = node.get_presigned_url(expires_in=3600)

if not node.capabilities.write:
    print("Read-only storage")
```

---

## Backend Capability Matrix

| Backend | Versioning | Metadata | Presigned URLs | Hash on Metadata | Server-side Copy |
|---------|------------|----------|----------------|------------------|------------------|
| **Local** | ✗ | ✗ | ✗ | ✗ | ✗ |
| **S3** | ✓ (if enabled) | ✓ | ✓ | ✓ (ETag) | ✓ |
| **GCS** | ✓ (if enabled) | ✓ | ✓ | ✓ (ETag) | ✓ |
| **Azure** | ✗ | ✓ | ✓ | ✓ (MD5) | ✓ |
| **HTTP** | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Memory** | ✗ | ✗ | ✗ | ✗ | ✗ |
| **Base64** | ✗ | ✗ | ✗ | ✗ | ✗ |

---

## Common Patterns

### Check and Use Features
```python
# Versioning
if node.capabilities.versioning:
    print(f"File has {node.version_count} versions")
    if node.version_count > 1:
        node.rollback()  # Undo last change

# Metadata
if node.capabilities.metadata:
    node.set_metadata({'uploaded_by': 'user123', 'project': 'alpha'})
    meta = node.metadata
```

### Efficient Copy with Skip Strategies
```python
from genro_storage import SkipStrategy

# Incremental backup - skip unchanged files
source.copy(backup, skip=SkipStrategy.HASH)

# With progress tracking
def on_file(src, dest):
    print(f"Copying {src.name}...")

def on_skip(src, dest, reason):
    print(f"Skipped {src.name}: {reason}")

source.copy(
    backup,
    skip=SkipStrategy.HASH,
    on_file=on_file,
    on_skip=on_skip
)
```

### Versioning Workflow
```python
# Enable S3 versioning first in AWS console or boto3
storage.configure([{
    'name': 's3',
    'type': 's3',
    'bucket': 'my-versioned-bucket'
}])

doc = storage.node('s3:important.txt')

# Write changes
doc.write_text('v1')
doc.write_text('v2')
doc.write_text('v3')

# View history
for v in doc.versions:
    print(f"{v['version_id']}: {v['last_modified']} - {v['size']} bytes")

# Access old version
with doc.open(version=-2) as f:  # Second-to-last version
    old_content = f.read()

# Compare versions
current, previous = doc.diff_versions(-1, -2)

# Rollback
doc.rollback()  # Restore previous version

# Clean up duplicates
removed = doc.compact_versions()
print(f"Removed {removed} redundant versions")
```

### External Tool Integration
```python
# Image optimization
image = storage.node('uploads:photo.jpg')
image.call(['convert', image, '-resize', '800x600', image])

# Video transcoding
video = storage.node('media:input.mp4')
output = storage.node('media:output.webm')
video.call(['ffmpeg', '-i', video, output])

# With async callback
def on_complete(returncode):
    print(f"Finished with code {returncode}")

video.call(['ffmpeg', '-i', video, output],
          async_mode=True,
          callback=on_complete)
```

### WSGI Serving
```python
# Flask example
from flask import Response

@app.route('/download/<path:filename>')
def download_file(filename):
    node = storage.node(f'uploads:{filename}')
    status, headers, body_iter = node.serve(
        download=True,
        cache_control='public, max-age=3600'
    )
    return Response(body_iter, status=status, headers=headers)
```

---

## Error Handling

All operations may raise:
- `FileNotFoundError`: File/directory doesn't exist
- `PermissionError`: Operation not allowed (e.g., write to read-only backend, versioning on non-versioned backend)
- `IsADirectoryError`: Operation requires file but got directory
- `NotADirectoryError`: Operation requires directory but got file
- `StorageConfigError`: Invalid configuration
- `StorageNotFoundError`: Mount point doesn't exist

Always check capabilities before using advanced features to avoid `PermissionError`.
