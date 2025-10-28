# Async Support Roadmap for genro-storage v0.2.0

## Executive Summary

**Goal:** Add async support using hybrid approach (native async + thread wrapper fallback)

**Timeline:** 3-4 weeks
**Effort:** ~20-25 days full-time equivalent
**Target Release:** v0.2.0 (Q1 2026)
**Approach:** Hybrid - native async where available, transparent thread wrapper fallback

## Design Philosophy

Hybrid approach inspired by psycopg3 but pragmatically optimized:

1. **Performance where it matters:** Native async for I/O-bound backends (aiofiles, aiohttp, aioboto3)
2. **Compatibility everywhere:** Thread wrapper fallback via `asyncio.to_thread()` for sync-only backends
3. **Transparent to users:** Auto-detection of backend capabilities, no manual configuration
4. **Backward compatible:** Existing sync API unchanged, lives side-by-side with async
5. **Incremental migration:** Backends can be migrated to native async over time
6. **AST generation optional:** Can generate sync from async OR keep current sync code
7. **Clear separation:** `AsyncStorageManager` / `StorageManager`

## Architecture

```
genro_storage/
├── async_/                       # Async implementation
│   ├── manager.py               # AsyncStorageManager
│   ├── node.py                  # AsyncStorageNode
│   └── backends/
│       ├── base.py              # AsyncStorageBackend (with _supports_native_async)
│       ├── local.py             # NATIVE: aiofiles
│       ├── http.py              # NATIVE: aiohttp
│       ├── s3.py                # NATIVE: aioboto3 or s3fs async
│       ├── azure.py             # NATIVE: adlfs async
│       ├── fsspec.py            # WRAPPER: auto-detect + thread fallback
│       ├── memory.py            # WRAPPER: thread (fast anyway)
│       └── base64.py            # WRAPPER: thread (CPU-bound)
│
├── backends/                     # Current sync implementation (KEEP AS-IS)
│   ├── base.py                  # StorageBackend
│   ├── local.py                 # LocalStorage
│   ├── fsspec.py                # FsspecBackend
│   └── base64.py                # Base64Backend
│
├── _shared/                      # Shared utilities
│   ├── exceptions.py            # Same for both
│   └── async_utils.py           # Helpers (to_thread wrapper, detection)
│
├── _codegen/                     # OPTIONAL (can defer to v0.3.0)
│   ├── async_to_sync.py         # AST transformation (if we want to generate sync)
│   └── markers.py               # Markers for conditional code
│
├── manager.py                    # StorageManager (current, unchanged)
├── node.py                       # StorageNode (current, unchanged)
└── __init__.py                   # Export both sync (default) and async
```

**Backend Status Matrix:**

| Backend | Async Type | Library | Performance Impact |
|---------|-----------|---------|-------------------|
| Local   | ✅ Native | aiofiles | High - lots of disk I/O |
| S3      | ✅ Native | aioboto3/s3fs | High - network I/O |
| HTTP    | ✅ Native | aiohttp | High - network I/O |
| Azure   | ✅ Native | adlfs | High - network I/O |
| GCS     | ⚠️ Hybrid | gcsfs + thread | Medium - partial async |
| Memory  | 🔄 Thread | asyncio.to_thread | Low - already fast |
| Base64  | 🔄 Thread | asyncio.to_thread | Low - CPU-bound |

## Implementation Example

### Hybrid Backend Pattern

```python
from abc import ABC, abstractmethod
import asyncio
import inspect

class AsyncStorageBackend(ABC):
    """Base class for async backends with hybrid support."""

    # Subclasses set this to indicate native async support
    _supports_native_async: bool = False

    @abstractmethod
    async def read_bytes(self, path: str) -> bytes:
        """Read file bytes. Must be implemented by subclasses."""
        pass

# NATIVE ASYNC: Local storage with aiofiles
class AsyncLocalStorage(AsyncStorageBackend):
    _supports_native_async = True

    async def read_bytes(self, path: str) -> bytes:
        """Native async using aiofiles."""
        import aiofiles
        async with aiofiles.open(path, 'rb') as f:
            return await f.read()

# WRAPPER: Base64 with thread pool
class AsyncBase64Backend(AsyncStorageBackend):
    _supports_native_async = False

    def __init__(self):
        from genro_storage.backends.base64 import Base64Backend
        self._sync_backend = Base64Backend()

    async def read_bytes(self, path: str) -> bytes:
        """Wrapped sync operation in thread."""
        return await asyncio.to_thread(
            self._sync_backend.read_bytes, path
        )

# HYBRID: fsspec with auto-detection
class AsyncFsspecBackend(AsyncStorageBackend):
    def __init__(self, fs):
        self.fs = fs
        # Auto-detect async support
        self._supports_native_async = (
            hasattr(fs, '_cat_file') and
            inspect.iscoroutinefunction(fs._cat_file)
        )

    async def read_bytes(self, path: str) -> bytes:
        """Use native async if available, else thread wrapper."""
        if self._supports_native_async:
            # Native async (e.g., s3fs)
            return await self.fs._cat_file(path)
        else:
            # Thread wrapper fallback
            return await asyncio.to_thread(self.fs.cat_file, path)
```

### User Experience (Transparent)

```python
# Users don't need to know which backends are native vs wrapper!
from genro_storage.async_ import AsyncStorageManager

async def backup_files():
    storage = AsyncStorageManager()
    storage.configure([
        {'name': 'local', 'type': 'local', 'path': '/data'},     # Native async
        {'name': 's3', 'type': 's3', 'bucket': 'mybucket'},      # Native async
        {'name': 'data', 'type': 'base64'}                       # Thread wrapper
    ])

    # All operations work the same way, regardless of backend type
    local = storage.node('local:file.txt')
    s3 = storage.node('s3:file.txt')
    b64 = storage.node('data:base64string')

    # All await the same, performance optimized automatically
    content1 = await local.read_bytes()  # aiofiles (native)
    content2 = await s3.read_bytes()     # aioboto3 (native)
    content3 = await b64.read_bytes()    # thread pool (wrapped)
```

## Phases

### Phase 0: Preparation (Week 1)

**Goal:** Setup infrastructure for async development

**Tasks:**
- [ ] Setup pytest-asyncio for async testing
- [ ] Add async dependencies: aiofiles, aiohttp, aioboto3
- [ ] Create `_shared/async_utils.py` with thread wrapper helpers
- [ ] Create async test fixtures (async StorageManager)
- [ ] Update CI to run async tests
- [ ] Prototype auto-detection of backend async support

**Deliverables:**
- Async testing infrastructure
- Helper utilities for thread wrapping
- CI pipeline updated
- Proof of concept for hybrid backend

**Risks:**
- Thread wrapper may have unexpected edge cases
- Mitigation: Comprehensive testing, start with simple backends

**Estimated effort:** 3 days


### Phase 1: Core Async Implementation (Week 1-2)

**Goal:** Implement async backends (native + wrapper)

**Tasks:**

1. **AsyncStorageBackend interface** (`async_/backends/base.py`)
   - [ ] Define async abstract methods (all 25 methods)
   - [ ] Add `_supports_native_async` flag
   - [ ] Add type hints

2. **AsyncLocalStorage - NATIVE** (`async_/backends/local.py`)
   - [ ] async read_bytes/read_text using aiofiles
   - [ ] async write_bytes/write_text
   - [ ] async exists/size/mtime
   - [ ] async mkdir/delete
   - [ ] async children (directory listing)

3. **AsyncHttpBackend - NATIVE** (`async_/backends/http.py`)
   - [ ] async read_bytes using aiohttp
   - [ ] async exists (HEAD request)

4. **AsyncBase64Backend - WRAPPER** (`async_/backends/base64.py`)
   - [ ] Use thread wrapper for encode/decode
   - [ ] Set `_supports_native_async = False`

5. **AsyncMemoryBackend - WRAPPER** (`async_/backends/memory.py`)
   - [ ] Thread wrapper around sync dict operations

**Deliverables:**
- 5 async backend implementations (2 native, 3 wrapper)
- 60+ async tests
- Proof that hybrid approach works

**Test criteria:**
- All async tests pass
- Performance benchmarks show native async is faster

**Estimated effort:** 6 days


### Phase 2: AsyncStorageNode Core I/O (Week 2)

**Goal:** Implement async version of StorageNode with core I/O

**Tasks:**

1. **Basic I/O** (`async_/node.py`)
   - [ ] async read_bytes()
   - [ ] async read_text()
   - [ ] async write_bytes()
   - [ ] async write_text()
   - [ ] async open() → async context manager
   - [ ] async exists property → async exists()
   - [ ] async size property → async size()
   - [ ] async mtime property → async mtime()

2. **Properties vs Methods:**
   - Async can't use `@property` (can't await)
   - Convert properties to async methods:
     ```python
     # Sync (current)
     if node.exists:
         size = node.size

     # Async (new)
     if await node.exists():
         size = await node.size()
     ```

3. **Directory operations:**
   - [ ] async mkdir()
   - [ ] async children() → async iterator
   - [ ] async child()

**Deliverables:**
- AsyncStorageNode with core I/O
- 80+ async tests
- Documentation updates

**API Design Decision:**

```python
# Option A: Methods (chosen - consistent with async patterns)
exists = await node.exists()
size = await node.size()

# Option B: Properties (rejected - weird syntax)
exists = await node.exists
size = await node.size
```

**Estimated effort:** 5 days


### Phase 3: Copy/Move Operations (Week 2-3)

**Goal:** Implement async cross-storage operations

**Tasks:**

1. **AsyncStorageNode copy/move**
   - [ ] async copy() with streaming
   - [ ] async move()
   - [ ] async skip_if strategies (auto-detect sync vs async)
   - [ ] Handle mixed native/wrapper backends (transparent)

2. **Skip strategies with auto-wrapping:**
   ```python
   # Sync skip function - auto-wrapped in thread
   def skip_if_exists(src, dst):
       return dst.exists

   # Async skip function - used natively
   async def skip_if_hash(src, dst):
       if not await dst.exists():
           return False
       return await src.md5hash() == await dst.md5hash()

   # Both work!
   await src.copy(dst, skip_if=skip_if_exists)
   await src.copy(dst, skip_if=skip_if_hash)
   ```

3. **Optimization:**
   - [ ] Async streaming copy (chunk-based)
   - [ ] Progress callbacks (async + sync auto-wrapped)

**Deliverables:**
- Async copy/move operations
- Async skip strategies with backward compat
- 30+ tests

**Estimated effort:** 4 days


### Phase 4: S3/Cloud Backends (Week 3)

**Goal:** Add native async for S3 and Azure

**Tasks:**

1. **AsyncS3Backend** (`async_/backends/s3.py`)
   - [ ] Choose: aioboto3 (native) vs s3fs async
   - [ ] Implement async read/write/exists/delete
   - [ ] async get_metadata() / set_metadata()
   - [ ] async versions() for versioning support

2. **AsyncAzureBackend** (`async_/backends/azure.py`)
   - [ ] Use adlfs async capabilities
   - [ ] Implement core operations
   - [ ] async metadata support

3. **AsyncFsspecBackend - HYBRID** (`async_/backends/fsspec.py`)
   - [ ] Auto-detect if fsspec filesystem has async methods
   - [ ] Use native async if available
   - [ ] Fallback to thread wrapper
   - [ ] Support GCS (partial async via gcsfs)

**Deliverables:**
- Native async for S3 and Azure
- Hybrid fsspec backend for other cloud providers
- 40+ cloud integration tests

**Estimated effort:** 5 days


### Phase 5: Advanced Features (Week 3-4)

**Goal:** Implement remaining async features

**Tasks:**

1. **File properties**
   - [ ] async md5hash()
   - [x] mimetype (sync OK - just string lookup)
   - [x] url() (sync OK - no I/O)

2. **Download from URL**
   - [ ] async fill_from_url() using aiohttp

3. **Versioning** (S3-specific)
   - [ ] async versions()
   - [ ] async open_version()

**Deferred to v0.3.0:**
- `call()` - subprocess async is complex
- `serve()` - ASGI vs WSGI different paradigm
- `local_path()` - requires sync I/O anyway

**Deliverables:**
- Async advanced features
- 20+ tests

**Estimated effort:** 2 days


### Phase 6: AsyncStorageManager (Week 4)

**Goal:** Implement async storage manager

**Tasks:**

1. **AsyncStorageManager** (`async_/manager.py`)
   - [ ] configure() - can stay sync (no I/O)
   - [ ] node() - returns AsyncStorageNode
   - [ ] Async context manager support
   ```python
   async with AsyncStorageManager() as storage:
       data = await storage.node('s3:file').read_bytes()
   ```

2. **Backend registration:**
   - [ ] register_backend_type() for async backends
   - [ ] Auto-detect sync vs async backends via inspection

**Deliverables:**
- AsyncStorageManager
- 15+ tests
- Integration tests

**Estimated effort:** 2 days


### Phase 7: Testing & Documentation (Week 4)

**Goal:** Comprehensive testing and documentation

**Tasks:**

1. **Testing:**
   - [ ] Port all 195 sync tests to async
   - [ ] Integration tests (native vs wrapper backends)
   - [ ] Performance benchmarks (async vs sync, native vs thread)
   - [ ] Edge cases (errors, timeouts, cancellation)
   - [ ] MinIO async integration tests

2. **Documentation:**
   - [ ] Update README with async examples
   - [ ] New docs/async.rst guide
   - [ ] Backend performance comparison table
   - [ ] Migration guide (sync → async)
   - [ ] API reference for AsyncStorageManager/Node
   - [ ] Document hybrid approach and when backends use threads

3. **Examples:**
   ```python
   # Sync (existing)
   storage = StorageManager()
   data = storage.node('s3:file').read_bytes()

   # Async (new)
   async with AsyncStorageManager() as storage:
       data = await storage.node('s3:file').read_bytes()
   ```

**Deliverables:**
- 195+ async tests passing
- Complete async documentation
- Migration guide
- Performance benchmarks published

**Estimated effort:** 3 days


## Timeline Summary

| Phase | Focus | Duration | Cumulative |
|-------|-------|----------|------------|
| 0 | Preparation & Infrastructure | 3 days | 3 days |
| 1 | Core Backends (Native + Wrapper) | 6 days | 9 days |
| 2 | AsyncStorageNode I/O | 5 days | 14 days |
| 3 | Copy/Move Operations | 4 days | 18 days |
| 4 | S3/Cloud Backends | 5 days | 23 days |
| 5 | Advanced Features | 2 days | 25 days |
| 6 | AsyncStorageManager | 2 days | 27 days |
| 7 | Testing & Docs | 3 days | 30 days |

**Total:** 30 days (6 weeks) @ 100% dedication

**With experience from v0.1.0:** Could be as fast as 20-25 days (3-4 weeks)

**Part-time (50%):** ~1.5-2 months
**Part-time (25%):** ~3 months


## Success Criteria

### Must Have (v0.2.0)

- [ ] AsyncStorageManager / AsyncStorageNode working
- [ ] Native async backends: Local (aiofiles), S3 (aioboto3), HTTP (aiohttp), Azure (adlfs)
- [ ] Thread wrapper backends: Memory, Base64, GCS (partial)
- [ ] Core I/O: read, write, copy, move, exists, size, mtime
- [ ] Async tests: 195+ passing
- [ ] Transparent backend detection (users don't need to know which is native vs wrapper)
- [ ] Documentation: Complete async guide with hybrid approach explained
- [ ] Backward compatibility: Sync API unchanged, lives side-by-side

### Nice to Have (v0.2.0)

- [ ] Performance benchmarks: native async vs thread wrapper vs sync
- [ ] Async metadata operations (S3, Azure)
- [ ] Async versioning (S3)
- [ ] AST code generation (optional, can keep both codebases)
- [ ] Auto-wrapping of sync skip_if functions

### Deferred (v0.3.0)

- [ ] `call()` async (subprocess integration with asyncio.create_subprocess_exec)
- [ ] `serve()` async (ASGI support)
- [ ] Full native async for all fsspec backends
- [ ] Async progress callbacks with cancellation
- [ ] Connection pooling for cloud backends


## Risks & Mitigations

### Medium Risk

**Risk:** Thread wrapper performance not good enough for some use cases
**Impact:** Medium - users may need native async for all backends
**Mitigation:**
- Benchmark early to quantify overhead
- Prioritize native async for high-traffic backends (Local, S3, HTTP)
- Document clearly which backends are native vs wrapper
- Thread wrapper good enough for most cases (I/O-bound work)

**Risk:** Auto-detection of backend async support is fragile
**Impact:** Medium - may break with fsspec updates
**Mitigation:**
- Use inspection and duck-typing carefully
- Test with multiple fsspec versions
- Allow manual override if needed
- Fallback is always safe (thread wrapper)

### Low Risk

**Risk:** Properties vs methods creates awkward API
**Impact:** Low - just API style difference
**Mitigation:**
- Follow asyncio conventions (methods, not properties)
- Consistent with aiofiles, httpx, etc.

**Risk:** Mixing sync/async in same codebase increases complexity
**Impact:** Low - but manageable
**Mitigation:**
- Clear separation: `genro_storage.async_` vs `genro_storage`
- Good documentation
- Examples showing both patterns


## Dependencies

### Required

- Python 3.9+ (async/await, asyncio.to_thread, type hints)
- aiofiles (async local I/O)
- aiohttp (async HTTP)
- pytest-asyncio (testing)

### Backend-Specific

- aioboto3 or s3fs (async S3 - choose based on Phase 4 evaluation)
- adlfs (async Azure)
- gcsfs (partial async GCS)
- fsspec (fallback for other backends)

### Optional (v0.3.0)

- ast-comments (if we implement AST sync code generation)
- asyncio-compat (for older Python compatibility)


## Breaking Changes

**None!** Backward compatibility maintained:

```python
# Old code (v0.1.x) - still works in v0.2.0
from genro_storage import StorageManager
storage = StorageManager()
data = storage.node('s3:file').read_bytes()

# New code (v0.2.0+)
from genro_storage.async_ import AsyncStorageManager
async with AsyncStorageManager() as storage:
    data = await storage.node('s3:file').read_bytes()
```


## Post-v0.2.0 Roadmap

### v0.3.0 (Q2 2026) - Advanced Async

- Async `call()` for external tools
- Async `serve()` with ASGI support
- Native async for GCS/Azure (bypass fsspec)
- Cancellation support
- Progress callbacks

### v0.4.0 (Q3 2026) - Performance

- Connection pooling (async)
- Parallel operations
- Streaming optimizations
- Benchmarking suite


## Resource Requirements

**Development:**
- 1 developer @ 50% = 3-4 months
- 1 developer @ 100% = 1.5-2 months

**Code review:**
- Senior Python dev with async experience
- ~5-10 hours total

**Testing:**
- MinIO for S3 testing (already have)
- GCS emulator (optional)
- CI/CD time increases ~50% (async tests)


## Open Questions

1. **Which S3 library: aioboto3 vs s3fs async?**
   - aioboto3: More control, official AWS SDK base, better maintained
   - s3fs: Already using fsspec, simpler integration, but less mature async
   - **Decision in Phase 4:** Benchmark both, choose based on performance + maturity

2. **Auto-wrap sync skip_if or require async?**
   ```python
   # Option A: Auto-detect and wrap sync functions
   def skip_exists(src, dst):  # sync
       return dst.exists
   await node.copy(dst, skip_if=skip_exists)  # works!

   # Option B: Require async functions only
   async def skip_exists(src, dst):  # must be async
       return await dst.exists()
   ```
   - **Recommendation:** Option A (auto-wrap) for better backward compat

3. **Async context managers optional or required?**
   ```python
   # Option A: Optional (simpler)
   storage = AsyncStorageManager()
   data = await storage.node('file').read_bytes()

   # Option B: Required (explicit resource management)
   async with AsyncStorageManager() as storage:
       data = await storage.node('file').read_bytes()
   ```
   - **Recommendation:** Option A by default, Option B available for cleanup


## Conclusion

The **hybrid approach** (native async + thread wrapper) is **ideal for genro-storage**:

✅ **Best performance** - Native async for critical backends (Local, S3, HTTP)
✅ **100% compatibility** - Thread wrapper ensures everything works
✅ **Transparent** - Users don't need to know implementation details
✅ **Pragmatic** - Focus effort where it matters most
✅ **Incremental** - Can migrate more backends to native async over time
✅ **Faster development** - ~40% time saved vs full async rewrite (30 days vs 52 days)
✅ **Lower risk** - Thread wrapper is proven, no AST complexity
✅ **Leverages experience** - Apply lessons from v0.1.0 implementation

**Timeline:** 20-30 days @ 100% (3-6 weeks)
**Realistic part-time:** 1.5-2 months @ 50%
**Target release:** v0.2.0 in Q1 2026
**Confidence level:** High (hybrid approach well-proven, e.g., Django ORM)

### Why Hybrid > Pure Async?

| Aspect | Pure Async | Hybrid | Winner |
|--------|-----------|--------|--------|
| Performance | 100% | ~95% (native where it matters) | Tie |
| Development Time | 52 days | 30 days | ✅ Hybrid |
| Complexity | High (AST) | Medium (detection) | ✅ Hybrid |
| Risk | Medium-High | Low | ✅ Hybrid |
| Compatibility | Depends on libs | 100% (thread fallback) | ✅ Hybrid |
| Maintenance | Single codebase | Dual codebase | Pure Async |

**The hybrid approach wins on pragmatism: 95% of the performance, 60% of the effort, 50% of the risk.**

---

**Next Steps:**

1. Get stakeholder buy-in on hybrid approach
2. Allocate 3-4 weeks development time
3. Start Phase 0 (preparation) to build infrastructure
4. Benchmark native async vs thread wrapper in Phase 1
5. Ship v0.2.0 in Q1 2026
