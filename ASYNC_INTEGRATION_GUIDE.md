# genro-storage Async Wrapper - Integration Guide

## Quick Start (DONE Tonight!)

✅ **Async wrapper is ready and tested!**
- 21 tests passing
- 96% coverage on wrapper
- Ready for genro-mail-proxy integration

## Installation

```bash
# In genro-storage (already done)
pip install asyncer

# In genro-mail-proxy (tomorrow)
pip install genro-storage[async]
# or if installing from local:
cd ../genro-storage
pip install -e ".[async]"
```

## Usage Example

```python
from genro_storage.asyncer_wrapper import AsyncStorageManager

# Initialize
storage = AsyncStorageManager()

# Configure (sync - do at startup)
storage.configure([{
    'name': 'attachments',
    'type': 's3',
    'bucket': 'mail-attachments',
    'region': 'eu-west-1',
    'endpoint_url': 'http://localhost:9000'  # For MinIO
}])

# Use in async context
async def read_attachment(path: str) -> bytes:
    node = storage.node(path)
    if await node.exists():
        return await node.read_bytes()
    raise FileNotFoundError(path)

# Example: read attachment for email
data = await read_attachment('attachments:received/msg123/invoice.pdf')
```

## genro-mail-proxy Integration Plan (Tomorrow Morning)

### Step 1: Install dependency (5 min)

```bash
cd genro-mail-proxy
pip install -e "../genro-storage[async]"

# Update requirements.txt
echo "genro-storage[async]>=0.2.0" >> requirements.txt
```

### Step 2: Create storage client wrapper (15 min)

```python
# async_mail_service/storage_client.py (NEW FILE)

from genro_storage.asyncer_wrapper import AsyncStorageManager
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AttachmentStorage:
    """Wrapper around AsyncStorageManager for genro-mail-proxy."""

    def __init__(self):
        self.storage = AsyncStorageManager()
        self._configured = False

    def configure_from_db(self, volumes: List[Dict[str, Any]]):
        """Load volumes from database (sync - call at startup)."""
        for vol in volumes:
            try:
                self.storage.add_mount(vol)
                logger.info(f"Configured storage volume: {vol['name']}")
            except Exception as e:
                logger.error(f"Failed to configure volume {vol.get('name')}: {e}")

        self._configured = True

    def add_volume(self, config: Dict[str, Any]):
        """Add volume at runtime (sync)."""
        self.storage.add_mount(config)
        logger.info(f"Added storage volume: {config['name']}")

    async def read_attachment(self, path: str) -> bytes:
        """Read attachment for email sending (async).

        Args:
            path: Storage path (format: "volume:path/to/file")

        Returns:
            bytes: Attachment data

        Raises:
            FileNotFoundError: If attachment doesn't exist
        """
        node = self.storage.node(path)

        if not await node.exists():
            raise FileNotFoundError(f"Attachment not found: {path}")

        return await node.read_bytes()

    async def store_attachment(self, path: str, data: bytes):
        """Store attachment (if needed for IMAP receive)."""
        node = self.storage.node(path)
        await node.write_bytes(data)

    async def delete_attachment(self, path: str):
        """Delete attachment."""
        node = self.storage.node(path)
        if await node.exists():
            await node.delete()

    async def attachment_exists(self, path: str) -> bool:
        """Check if attachment exists."""
        node = self.storage.node(path)
        return await node.exists()

    async def get_attachment_size(self, path: str) -> int:
        """Get attachment size in bytes."""
        node = self.storage.node(path)
        return await node.size()
```

### Step 3: Update core.py to use new storage (30 min)

```python
# In async_mail_service/core.py

# OLD (remove)
# from .s3_attachment_storage import S3AttachmentStorage

# NEW (add)
from .storage_client import AttachmentStorage

class AsyncMailCore:
    def __init__(self, ...):
        # OLD
        # self.s3_storage = S3AttachmentStorage(...)

        # NEW
        self.attachment_storage = AttachmentStorage()

    async def start(self):
        """Load volumes from database on startup."""
        # Load volumes from DB
        volumes = await self.persistence.get_all_volumes()
        self.attachment_storage.configure_from_db(volumes)

        # ... rest of startup

    async def _fetch_attachment(self, attachment_ref: Dict) -> bytes:
        """Fetch attachment for email sending.

        OLD: attachment_ref = {
            "s3": {
                "bucket": "...",
                "key": "...",
                "region": "..."
            }
        }

        NEW: attachment_ref = {
            "path": "attachments:received/msg123/file.pdf"
        }
        """
        # NEW - simple path-based lookup
        path = attachment_ref.get('path')
        if not path:
            raise ValueError("Missing attachment path")

        return await self.attachment_storage.read_attachment(path)
```

### Step 4: Add database table for volumes (15 min)

```sql
-- In persistence.py or migration script

CREATE TABLE IF NOT EXISTS storage_volumes (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    type TEXT NOT NULL,
    config TEXT NOT NULL,  -- JSON
    created_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Example data
INSERT INTO storage_volumes (id, name, type, config) VALUES (
    'vol1',
    'attachments',
    's3',
    '{"bucket": "mail-attachments", "region": "eu-west-1", "endpoint_url": "http://localhost:9000"}'
);
```

```python
# In persistence.py

async def get_all_volumes(self) -> List[Dict[str, Any]]:
    """Load all storage volumes from database."""
    async with self._lock:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT name, type, config FROM storage_volumes"
            ) as cursor:
                rows = await cursor.fetchall()
                volumes = []
                for row in rows:
                    config = json.loads(row['config'])
                    volumes.append({
                        'name': row['name'],
                        'type': row['type'],
                        **config
                    })
                return volumes

async def save_volume(self, volume: Dict[str, Any]):
    """Save storage volume to database."""
    async with self._lock:
        async with aiosqlite.connect(self.db_path) as db:
            config = {k: v for k, v in volume.items() if k not in ('name', 'type')}
            await db.execute(
                """INSERT OR REPLACE INTO storage_volumes (id, name, type, config)
                   VALUES (?, ?, ?, ?)""",
                (volume['name'], volume['name'], volume['type'], json.dumps(config))
            )
            await db.commit()
```

### Step 5: Add API endpoint for volume management (20 min)

```python
# In async_mail_service/api.py

from pydantic import BaseModel

class VolumeConfig(BaseModel):
    name: str
    type: str  # 's3', 'local', 'gcs', 'azure'
    bucket: Optional[str] = None  # For S3/GCS
    region: Optional[str] = None  # For S3
    endpoint_url: Optional[str] = None  # For MinIO
    path: Optional[str] = None  # For local
    # Add other fields as needed

@app.post("/api/volumes")
async def add_volume(volume: VolumeConfig):
    """Add storage volume dynamically."""
    try:
        # Add to genro-storage
        service.attachment_storage.add_volume(volume.dict())

        # Save to DB for persistence
        await service.persistence.save_volume(volume.dict())

        return {"ok": True, "volume": volume.name}
    except Exception as e:
        return {"ok": False, "error": str(e)}

@app.get("/api/volumes")
async def list_volumes():
    """List all configured volumes."""
    volumes = await service.persistence.get_all_volumes()
    return {"volumes": volumes}
```

### Step 6: Remove old S3 storage code (5 min)

```bash
# Remove old implementation
rm async_mail_service/s3_attachment_storage.py

# Update any imports that reference it
grep -r "s3_attachment_storage" async_mail_service/
# Fix any remaining references
```

### Step 7: Test (15 min)

```python
# Test manually
curl -X POST http://localhost:8000/api/volumes \
  -H "Content-Type: application/json" \
  -d '{
    "name": "attachments",
    "type": "s3",
    "bucket": "mail-attachments",
    "region": "eu-west-1",
    "endpoint_url": "http://localhost:9000"
  }'

# Send test email with attachment
curl -X POST http://localhost:8000/commands/add-messages \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{
      "id": "test1",
      "from": "sender@example.com",
      "to": "recipient@example.com",
      "subject": "Test with attachment",
      "body": "See attached",
      "attachments": [{
        "path": "attachments:test/invoice.pdf",
        "filename": "invoice.pdf"
      }]
    }]
  }'
```

## Benefits

### Code Reduction
- **Before**: ~192 lines (s3_attachment_storage.py)
- **After**: ~50 lines (storage_client.py wrapper)
- **Saved**: ~140 lines + maintenance

### Database Efficiency
```python
# Before (verbose)
attachment = {
    "s3": {
        "bucket": "mail-attachments",
        "region": "eu-west-1",
        "key": "received/msg123/invoice.pdf",
        "endpoint_url": "http://localhost:9000"
    }
}  # 120 bytes

# After (compact)
attachment = {
    "path": "attachments:received/msg123/invoice.pdf"
}  # 52 bytes

# 58% size reduction!
```

### Multi-Cloud Support
```python
# Client can choose backend via API
POST /api/volumes {"name": "aws", "type": "s3", ...}
POST /api/volumes {"name": "gcp", "type": "gcs", ...}
POST /api/volumes {"name": "local", "type": "local", ...}

# Same code works for all!
data = await storage.read_attachment('aws:file.pdf')
data = await storage.read_attachment('gcp:file.pdf')
data = await storage.read_attachment('local:file.pdf')
```

## Timeline Tomorrow

```
09:00-09:05  Install genro-storage dependency
09:05-09:20  Create storage_client.py
09:20-09:50  Update core.py to use new storage
09:50-10:05  Add database table + queries
10:05-10:25  Add API endpoints
10:25-10:30  Remove old S3 code
10:30-10:45  Test manually
10:45-11:00  Fix any bugs

TOTAL: ~2 hours
```

## Testing Checklist

- [ ] Volume configuration via API works
- [ ] Volumes persist across restarts
- [ ] Can read attachments using path format
- [ ] Email sending with attachments works
- [ ] Multiple volumes work correctly
- [ ] S3 MinIO integration works
- [ ] Local storage works (for dev)

## Troubleshooting

### Import Error
```
ImportError: cannot import name 'AsyncStorageManager' from 'genro_storage.asyncer_wrapper'
```
**Solution**: Make sure asyncer is installed: `pip install asyncer`

### Mount Not Found
```
StorageNotFoundError: Mount point 'attachments' not found
```
**Solution**: Check volume was configured correctly at startup or via API

### File Not Found
```
FileNotFoundError: Attachment not found: attachments:file.pdf
```
**Solution**: Verify path exists in storage, check mount name and path

## Notes

- genro-storage sync API is already production-ready (81% coverage, 274 tests)
- Async wrapper is minimal (96% coverage, 21 tests)
- Only READ operations are needed for sending emails
- WRITE operations available if needed for IMAP receiving
- Performance is good (ThreadPoolExecutor for I/O-bound ops)
- No event loop blocking

## Next Steps (Future)

- Full async API (native async, not wrapper) - v0.3.0
- Runtime mount add/remove without restart - v0.3.0
- Mount persistence to file - v0.3.0
- Enhanced error handling - v0.3.0

But for now, this wrapper is **production-ready** for genro-mail-proxy! 🚀
