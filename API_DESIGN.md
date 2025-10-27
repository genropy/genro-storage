# genro-storage - API Design Document

**Version:** 1.0  
**Date:** 2025-10-26  
**Status:** Draft for Approval

---

## 1. Overview

`genro-storage` provides a unified interface for accessing files across different storage backends (local, S3, GCS, Azure, HTTP, etc.) using a mount-point abstraction inspired by Unix filesystems.

**Core Concepts:**
- **Mount Point**: A logical name (e.g., `home`, `uploads`, `s3`) that maps to a storage backend
- **Storage Path**: Format `mount:relative/path/to/file` (e.g., `home:documents/report.pdf`)
- **Backend**: Implementation that handles actual I/O (powered by fsspec)

---

## 2. Public API

### 2.1 StorageManager

Main entry point for configuring and accessing storage.

#### Constructor

```python
StorageManager()
```

Creates a new storage manager instance with no configured mounts.

**Parameters:** None

**Returns:** `StorageManager` instance

**Example:**
```python
from genro_storage import StorageManager

storage = StorageManager()
```

---

#### Method: `configure(source)`

Configures mount points from various sources.

**Signature:**
```python
def configure(self, source: str | list[dict[str, Any]]) -> None
```

**Parameters:**
- `source`: Configuration source, can be:
  - `str`: Path to YAML or JSON file
  - `list[dict]`: List of mount configurations

**Returns:** `None`

**Raises:**
- `FileNotFoundError`: If file path doesn't exist
- `ValueError`: If configuration format is invalid
- `TypeError`: If source is neither str nor list

**Configuration Format (dict):**

Each mount configuration must have:
- `name` (str, required): Mount point name (e.g., "home", "uploads")
- `type` (str, required): Backend type (e.g., "local", "s3", "gcs", "azure", "http")
- Additional fields depend on `type`:

**Local storage:**
```python
{
    "name": "home",
    "type": "local",
    "path": "/home/user"  # required: absolute path
}
```

**S3 storage:**
```python
{
    "name": "uploads",
    "type": "s3",
    "bucket": "my-bucket",  # required
    "prefix": "uploads/",   # optional, default: ""
    "region": "eu-west-1",  # optional
    "anon": False           # optional, default: False
}
```

**GCS storage:**
```python
{
    "name": "backups",
    "type": "gcs",
    "bucket": "my-backups",  # required
    "prefix": "",            # optional
    "token": "path/to/service-account.json"  # optional
}
```

**Azure Blob storage:**
```python
{
    "name": "archive",
    "type": "azure",
    "container": "archives",     # required
    "account_name": "myaccount", # required
    "account_key": "..."         # optional if using managed identity
}
```

**HTTP storage (read-only):**
```python
{
    "name": "cdn",
    "type": "http",
    "base_url": "https://cdn.example.com"  # required
}
```

**Memory storage (for testing):**
```python
{
    "name": "test",
    "type": "memory"
}
```

**YAML File Format:**
```yaml
# storage.yaml
- name: home
  type: local
  path: /home/user

- name: uploads
  type: s3
  bucket: my-app-uploads
  region: eu-west-1

- name: cache
  type: memory
```

**JSON File Format:**
```json
[
  {
    "name": "home",
    "type": "local",
    "path": "/home/user"
  },
  {
    "name": "uploads",
    "type": "s3",
    "bucket": "my-app-uploads",
    "region": "eu-west-1"
  }
]
```

**Examples:**

```python
# From file
storage.configure('/etc/app/storage.yaml')
storage.configure('./config/storage.json')

# From list
storage.configure([
    {'name': 'home', 'type': 'local', 'path': '/home/user'},
    {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
])

# Multiple calls append mounts (last wins if same name)
storage.configure([{'name': 'home', 'type': 'local', 'path': '/home/user'}])
storage.configure([{'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}])
```

**Behavior:**
- If a mount with the same name already exists, it is replaced
- Invalid configurations raise exceptions immediately
- File paths are resolved relative to current working directory

---

#### Method: `node(mount_or_path, *path_parts)`

Creates a StorageNode pointing to a file or directory.

**Signature:**
```python
def node(self, mount_or_path: str, *path_parts: str) -> StorageNode
```

**Parameters:**
- `mount_or_path`: Either:
  - Full path with mount: `"mount:path/to/file"`
  - Just mount name: `"mount"`
- `*path_parts`: Additional path components to join

**Returns:** `StorageNode` instance

**Raises:**
- `KeyError`: If mount point doesn't exist
- `ValueError`: If path format is invalid

**Examples:**

```python
# Full path in one string
node = storage.node('home:documents/report.pdf')

# Mount + path parts
node = storage.node('home', 'documents', 'report.pdf')

# Mix styles
node = storage.node('home:documents', 'reports', 'q4.pdf')

# Dynamic composition
user_id = '123'
year = '2024'
node = storage.node('uploads', 'users', user_id, year, 'avatar.jpg')
# → uploads:users/123/2024/avatar.jpg

# Just mount (root of storage)
node = storage.node('home')
# → home:
```

**Path Normalization:**
- Multiple slashes collapsed: `a//b` → `a/b`
- Leading/trailing slashes stripped
- No support for `..` (parent directory) - raises ValueError

---

### 2.2 StorageNode

Represents a file or directory in a storage backend.

**Note:** Users don't instantiate StorageNode directly - only via `storage.node()`

#### Properties

##### `fullpath: str`
Full path including mount point.

```python
node = storage.node('home:documents/file.txt')
print(node.fullpath)  # "home:documents/file.txt"
```

##### `exists: bool`
True if file/directory exists.

```python
if node.exists:
    print("File exists!")
```

##### `isfile: bool`
True if node points to a file.

```python
if node.isfile:
    data = node.read_bytes()
```

##### `isdir: bool`
True if node points to a directory.

```python
if node.isdir:
    for child in node.children():
        print(child.basename)
```

##### `size: int`
File size in bytes. Raises exception if not a file.

```python
print(f"File size: {node.size} bytes")
```

##### `mtime: float`
Last modification time as Unix timestamp.

```python
from datetime import datetime
mod_time = datetime.fromtimestamp(node.mtime)
print(f"Modified: {mod_time}")
```

##### `basename: str`
Filename with extension.

```python
node = storage.node('home:documents/report.pdf')
print(node.basename)  # "report.pdf"
```

##### `stem: str`
Filename without extension.

```python
node = storage.node('home:documents/report.pdf')
print(node.stem)  # "report"
```

##### `suffix: str`
File extension including dot.

```python
node = storage.node('home:documents/report.pdf')
print(node.suffix)  # ".pdf"
```

##### `parent: StorageNode`
Parent directory as StorageNode.

```python
node = storage.node('home:documents/reports/q4.pdf')
parent = node.parent
print(parent.fullpath)  # "home:documents/reports"
```

##### `md5hash: str`
MD5 hash of file content (efficient for cloud storage).

For cloud storage (S3, GCS, Azure), retrieves hash from backend metadata (fast, no download).
For local storage, computes hash by reading file in 64KB blocks.

```python
# Get MD5 hash
hash1 = node1.md5hash
hash2 = node2.md5hash

# Compare file contents
if hash1 == hash2:
    print("Files have identical content")
```

**Raises:**
- `FileNotFoundError`: If file doesn't exist
- `ValueError`: If node is a directory

**Performance Notes:**
- S3/MinIO/GCS: Uses ETag metadata (instant, no download)
- Azure: Uses content_md5 metadata
- Local/memory: Computes by reading file (slower for large files)

---

#### Methods

##### `open(mode: str = 'rb')`
Opens file and returns file-like object.

**Signature:**
```python
def open(self, mode: str = 'rb') -> BinaryIO | TextIO
```

**Parameters:**
- `mode`: File mode ('r', 'rb', 'w', 'wb', 'a', 'ab')

**Returns:** File-like object (context manager)

**Example:**
```python
with node.open('rb') as f:
    data = f.read()

with node.open('w') as f:
    f.write("Hello World")
```

---

##### `read_bytes()`
Reads entire file as bytes.

**Signature:**
```python
def read_bytes(self) -> bytes
```

**Returns:** `bytes`

**Raises:** `FileNotFoundError` if file doesn't exist

**Example:**
```python
data = node.read_bytes()
```

---

##### `read_text(encoding: str = 'utf-8')`
Reads entire file as string.

**Signature:**
```python
def read_text(self, encoding: str = 'utf-8') -> str
```

**Parameters:**
- `encoding`: Text encoding (default: 'utf-8')

**Returns:** `str`

**Example:**
```python
content = node.read_text()
content = node.read_text('latin-1')
```

---

##### `write_bytes(data: bytes)`
Writes bytes to file.

**Signature:**
```python
def write_bytes(self, data: bytes) -> None
```

**Parameters:**
- `data`: Bytes to write

**Returns:** `None`

**Example:**
```python
node.write_bytes(b'Hello World')
```

---

##### `write_text(text: str, encoding: str = 'utf-8')`
Writes string to file.

**Signature:**
```python
def write_text(self, text: str, encoding: str = 'utf-8') -> None
```

**Parameters:**
- `text`: String to write
- `encoding`: Text encoding (default: 'utf-8')

**Returns:** `None`

**Example:**
```python
node.write_text("Hello World")
node.write_text("Café", encoding='utf-8')
```

---

##### `delete()`
Deletes file or directory.

**Signature:**
```python
def delete(self) -> None
```

**Returns:** `None`

**Behavior:**
- For files: deletes the file
- For directories: deletes recursively (like `rm -rf`)
- If doesn't exist: no error (idempotent)

**Example:**
```python
node.delete()
```

---

##### `copy(dest: StorageNode | str)`
Copies file/directory to destination.

**Signature:**
```python
def copy(self, dest: StorageNode | str) -> StorageNode
```

**Parameters:**
- `dest`: Destination as StorageNode or path string

**Returns:** Destination `StorageNode`

**Behavior:**
- Works across different storage backends
- If dest is directory, creates file with same basename inside
- Overwrites existing files
- For directories: copies recursively

**Example:**
```python
# Same storage
node.copy(storage.node('home:backup/file.txt'))

# Cross-storage
node.copy(storage.node('s3:uploads/file.txt'))

# String destination
node.copy('home:backup/file.txt')
```

---

##### `move(dest: StorageNode | str)`
Moves file/directory to destination.

**Signature:**
```python
def move(self, dest: StorageNode | str) -> StorageNode
```

**Parameters:**
- `dest`: Destination as StorageNode or path string

**Returns:** Destination `StorageNode`

**Behavior:**
- If same backend: efficient rename
- If different backend: copy + delete
- Updates current node to point to new location

**Example:**
```python
node.move(storage.node('home:archive/file.txt'))
# node now points to home:archive/file.txt
```

---

##### `children()`
Lists child nodes (if directory).

**Signature:**
```python
def children(self) -> list[StorageNode]
```

**Returns:** List of `StorageNode` objects

**Raises:** Exception if not a directory

**Example:**
```python
if node.isdir:
    for child in node.children():
        print(f"{child.basename}: {child.size} bytes")
```

---

##### `child(name: str)`
Gets a child node by name.

**Signature:**
```python
def child(self, name: str) -> StorageNode
```

**Parameters:**
- `name`: Child name (filename or subdirectory)

**Returns:** `StorageNode` (may not exist)

**Example:**
```python
docs = storage.node('home:documents')
report = docs.child('report.pdf')
```

---

##### `mkdir(parents: bool = False, exist_ok: bool = False)`
Creates directory.

**Signature:**
```python
def mkdir(self, parents: bool = False, exist_ok: bool = False) -> None
```

**Parameters:**
- `parents`: If True, create parent directories as needed
- `exist_ok`: If True, don't raise error if already exists

**Returns:** `None`

**Raises:**
- `FileExistsError`: If exists and `exist_ok=False`
- `FileNotFoundError`: If parent doesn't exist and `parents=False`

**Example:**
```python
node.mkdir()
node.mkdir(parents=True, exist_ok=True)
```

---

#### Operators

##### `__eq__` and `__ne__`
Content-based equality comparison using MD5 hash.

Two nodes are considered equal if they have the same file content (MD5 hash), regardless of their path or storage backend.

**Signature:**
```python
def __eq__(self, other: object) -> bool
def __ne__(self, other: object) -> bool
```

**Parameters:**
- `other`: Another StorageNode or object to compare

**Returns:** `bool`
- `True` if both nodes have identical content (same MD5 hash)
- `False` otherwise
- Returns `NotImplemented` when comparing with non-StorageNode objects

**Notes:**
- Only files can be compared (directories return `False`)
- Non-existent files return `False`
- Comparison works across different backends and paths

**Examples:**
```python
# Compare files on same backend
file1 = storage.node('home:original.txt')
file2 = storage.node('home:copy.txt')
if file1 == file2:
    print("Files have identical content")

# Compare across backends (S3 vs local)
s3_file = storage.node('uploads:data.json')
local_file = storage.node('home:backup/data.json')
if s3_file == local_file:
    print("Backup is up to date")
else:
    print("Files differ, update needed")

# Check inequality
if file1 != file2:
    print("Files have different content")
```

---

## 3. Exceptions

All exceptions inherit from `StorageError` base class.

```python
from genro_storage import (
    StorageError,           # Base exception
    StorageNotFoundError,   # File/mount not found
    StoragePermissionError, # Permission denied
    StorageConfigError,     # Invalid configuration
)
```

**Exception Hierarchy:**
```
StorageError (base)
├── StorageNotFoundError (inherits from FileNotFoundError)
├── StoragePermissionError (inherits from PermissionError)
└── StorageConfigError (inherits from ValueError)
```

---

## 4. Complete Usage Examples

### Example 1: Basic File Operations

```python
from genro_storage import StorageManager

# Setup
storage = StorageManager()
storage.configure([
    {'name': 'home', 'type': 'local', 'path': '/home/user'}
])

# Write
node = storage.node('home:documents/report.txt')
node.write_text("# Quarterly Report\n\nSales increased by 15%")

# Read
content = node.read_text()
print(content)

# Check properties
print(f"Size: {node.size} bytes")
print(f"Exists: {node.exists}")

# Delete
node.delete()
```

---

### Example 2: Cross-Storage Copy

```python
storage = StorageManager()
storage.configure([
    {'name': 'local', 'type': 'local', 'path': '/tmp'},
    {'name': 's3', 'type': 's3', 'bucket': 'my-bucket'}
])

# Process locally then upload
local = storage.node('local:processing/image.jpg')
local.write_bytes(processed_image_data)

# Upload to S3
s3_dest = storage.node('s3:uploads/2024/image.jpg')
local.copy(s3_dest)

# Cleanup local
local.delete()
```

---

### Example 3: Directory Iteration

```python
# List all files in directory
uploads = storage.node('s3:uploads/2024')

if uploads.isdir:
    for file in uploads.children():
        if file.isfile:
            print(f"{file.basename}: {file.size / 1024:.1f} KB")
```

---

### Example 4: Dynamic Path Building

```python
def save_user_avatar(user_id: int, image_data: bytes):
    node = storage.node('uploads', 'users', str(user_id), 'avatar.jpg')
    node.parent.mkdir(parents=True, exist_ok=True)
    node.write_bytes(image_data)
    return node.fullpath

# Usage
path = save_user_avatar(123, avatar_bytes)
print(f"Saved to: {path}")  # "uploads:users/123/avatar.jpg"
```

---

### Example 5: Configuration from YAML

```yaml
# config/storage.yaml
- name: home
  type: local
  path: /home/user

- name: uploads
  type: s3
  bucket: prod-uploads
  region: eu-west-1

- name: cache
  type: memory
```

```python
storage = StorageManager()
storage.configure('config/storage.yaml')

# Ready to use
node = storage.node('uploads:file.txt')
```

---

## 5. Type Hints

All public APIs have complete type hints:

```python
from typing import BinaryIO, TextIO

class StorageManager:
    def __init__(self) -> None: ...
    def configure(self, source: str | list[dict[str, Any]]) -> None: ...
    def node(self, mount_or_path: str, *path_parts: str) -> StorageNode: ...

class StorageNode:
    @property
    def fullpath(self) -> str: ...
    @property
    def exists(self) -> bool: ...
    @property
    def size(self) -> int: ...
    
    def open(self, mode: str = 'rb') -> BinaryIO | TextIO: ...
    def read_bytes(self) -> bytes: ...
    def read_text(self, encoding: str = 'utf-8') -> str: ...
    def write_bytes(self, data: bytes) -> None: ...
    def copy(self, dest: StorageNode | str) -> StorageNode: ...
    # ...
```

---

## 6. Behavior Specifications

### 6.1 Path Normalization

- Paths are always normalized to forward slashes `/`
- Multiple consecutive slashes are collapsed: `a//b` → `a/b`
- Leading and trailing slashes are stripped
- Empty path components are removed
- **No parent directory traversal**: `..` raises `ValueError`

### 6.2 Error Handling

- Missing mounts raise `KeyError` with clear message
- File not found raises `StorageNotFoundError` (subclass of `FileNotFoundError`)
- Permission errors raise `StoragePermissionError` (subclass of `PermissionError`)
- Configuration errors raise `StorageConfigError` with detailed message

### 6.3 Cross-Storage Operations

- `copy()` and `move()` work seamlessly across different backends
- Implementation uses streaming for large files (no full load in memory)
- Progress/errors are raised as they occur

### 6.4 Idempotency

- `delete()` doesn't error if file doesn't exist
- `mkdir(exist_ok=True)` doesn't error if directory exists
- Configuration can be called multiple times (mounts are replaced)

---

## 7. What's NOT in Public API

These are intentionally NOT exposed:

- ❌ `.mount()`, `.mount_local()`, `.mount_s3()` - use `.configure()` instead
- ❌ Direct StorageNode instantiation - use `storage.node()` instead
- ❌ Backend classes - implementation detail
- ❌ Internal fsspec filesystem objects - abstracted away

---

## 8. Python Version & Dependencies

**Minimum Python:** 3.9

**Core Dependencies:**
- `fsspec >= 2023.1.0`

**Optional Dependencies:**
- `s3fs >= 2023.1.0` - for S3 support
- `gcsfs >= 2023.1.0` - for Google Cloud Storage
- `adlfs >= 2023.1.0` - for Azure Blob Storage
- `aiohttp >= 3.8.0` - for HTTP support
- `PyYAML >= 6.0` - for YAML config files

---

## 9. Open Questions / Decisions Needed

1. **Async support**: Should we add `async` methods (e.g., `async def read_bytes_async()`)?
   - Decision: Start without, add in v0.2 if needed

2. **Glob/pattern matching**: Should StorageNode support `.glob('*.txt')`?
   - Decision: Not in v1.0, can add later

3. **Metadata**: Should we expose file metadata (content-type, custom headers)?
   - Decision: Not in v1.0 - fsspec handles this internally

4. **Streaming**: Should we add `.iter_chunks()` for large files?
   - Decision: Not in v1.0 - users can use `.open()` + manual reading

---

## 10. Approval Checklist

Before implementation, confirm:

- [ ] API surface is complete and correct
- [ ] Configuration format is clear
- [ ] Examples cover main use cases
- [ ] No ambiguities in behavior
- [ ] Type hints are accurate
- [ ] Nothing is missing from public API

---

**Status:** ⏳ Awaiting Approval

**Next Step:** Write test suite based on this specification
