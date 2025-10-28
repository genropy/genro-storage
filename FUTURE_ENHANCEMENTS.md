# Future Enhancements

This document tracks potential features and enhancements that could be added to genro-storage in the future. These ideas are not currently prioritized but are worth considering based on user needs.

## Version Comparison & Diff

### Text Diff Support
Add built-in text diff capabilities for versioned files:

```python
# Generate unified diff between versions
diff = node.diff_versions_text(v1=-1, v2=-2, format='unified')
print(diff)

# HTML diff for web display
html_diff = node.diff_versions_text(format='html')
```

**Implementation notes:**
- Use stdlib `difflib` (no dependencies)
- Support formats: unified, context, HTML
- Only for text files (raise error for binary)
- Keep `diff_versions()` for raw bytes comparison

**Use cases:**
- Configuration file changes
- Code review for versioned scripts
- Document change tracking
- Audit logs

**Considerations:**
- Should we support semantic diff for structured formats (JSON, XML)?
- Would require additional dependencies (jsondiff, xmldiff)
- Alternative: document how users can do this themselves with `diff_versions()`

## Advanced Version Management

### Time-based Retention Policies
Programmatic lifecycle policies:

```python
# Keep only versions from last 30 days
node.cleanup_versions(keep_days=30)

# Keep last N versions
node.cleanup_versions(keep_last=10)

# Combine: keep last 5 OR anything from last 7 days
node.cleanup_versions(keep_last=5, keep_days=7)
```

### Version Tagging
Mark important versions with labels:

```python
# Tag a version
node.tag_version(-1, "release-v1.0")
node.tag_version(-5, "pre-migration-backup")

# List tagged versions
tags = node.get_version_tags()

# Restore to tagged version
node.rollback(tag="release-v1.0")
```

**Implementation notes:**
- For S3: use object metadata or external mapping
- Requires persistent tag storage
- Consider tag lifecycle (delete with version? keep?)

## Batch Operations

### Bulk Version Operations
Operate on multiple files efficiently:

```python
# Compact versions for all files in a directory
storage.bulk_compact_versions('s3:documents/')

# Snapshot multiple files at once
storage.create_snapshot('s3:config/', tag='pre-deploy')
```

## Integration Features

### Change Notifications
Webhooks or callbacks for version events:

```python
def on_version_created(node, version_info):
    print(f"New version: {version_info['version_id']}")

storage.on('version_created', on_version_created)
```

### Version Metadata
Custom metadata on specific versions:

```python
# Add metadata to current version
node.annotate_version(
    version=-1,
    metadata={'author': 'user@example.com', 'reason': 'bug fix'}
)

# Query versions by metadata
versions = node.find_versions(author='user@example.com')
```

## Format-Specific Diff

### Structured Data Diff
Smart diff for common formats:

```python
# JSON semantic diff
json_diff = node.diff_json_versions(-1, -2)
# Returns: {'added': [...], 'removed': [...], 'changed': [...]}

# CSV diff (row-level)
csv_diff = node.diff_csv_versions(-1, -2)

# Image diff (visual)
image_diff = node.diff_image_versions(-1, -2)
# Returns PIL Image or similarity score
```

**Dependencies needed:**
- JSON: `jsondiff` or `deepdiff`
- CSV: `pandas` (optional)
- Images: `PIL/Pillow`, `imagehash`

**Considerations:**
- Heavy dependencies for optional features
- Could be separate package: `genro-storage-diff`
- Or document how to do this with existing `diff_versions()`

## Storage Optimization

### Deduplication Across Files
Find and deduplicate identical files:

```python
# Find duplicate files by content hash
duplicates = storage.find_duplicates('s3:uploads/')

# Deduplicate using S3 object references
storage.deduplicate('s3:uploads/', strategy='reference')
```

### Compression on Storage
Transparent compression for specific file types:

```python
storage.configure([{
    'name': 's3',
    'type': 's3',
    'bucket': 'my-bucket',
    'compress': ['*.json', '*.txt', '*.log']  # Auto gzip these
}])
```

## Enhanced Capabilities

### Locking/Concurrency
Distributed locks for concurrent access:

```python
with node.lock(timeout=30):
    # Exclusive access
    data = node.read_bytes()
    data = process(data)
    node.write_bytes(data)
```

### Streaming for Large Files
Better support for very large files:

```python
# Stream with progress
with node.stream_download() as stream:
    for chunk in stream:
        progress.update(len(chunk))
        process_chunk(chunk)
```

## Cloud-Specific Features

### S3 Advanced Features
Expose more S3-specific capabilities:

```python
# Object legal hold
node.set_legal_hold(True)

# Object lock (WORM)
node.set_retention(mode='GOVERNANCE', until=datetime(...))

# Storage class transitions
node.set_storage_class('GLACIER')
```

## Testing & Development

### Mock Backend Enhancements
Better testing support:

```python
# Memory backend with simulated latency
backend = MockBackend(latency_ms=100, failure_rate=0.01)

# Record/replay mode for integration tests
storage.record_mode('fixtures/api-calls.json')
```

---

## Decision Criteria

When evaluating these enhancements, consider:

1. **Scope**: Does it fit genro-storage's mission (storage abstraction)?
2. **Dependencies**: Can we avoid heavy dependencies?
3. **Complexity**: Will it complicate the simple API?
4. **Maintenance**: Can we maintain it long-term?
5. **Demand**: Do users actually need this?

Some features might be better as:
- **Separate packages**: `genro-storage-diff`, `genro-storage-admin`
- **Documentation**: "How to do X with genro-storage"
- **Examples**: Code recipes in docs

---

## Contributing Ideas

Have an idea for genro-storage? Please:
1. Check this document first
2. Open a GitHub issue for discussion
3. Provide use cases and examples
4. Consider scope and dependencies

Not all ideas will be implemented, but all are appreciated!
