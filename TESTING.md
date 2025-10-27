# Testing with MinIO

This guide explains how to run integration tests using MinIO as a local S3-compatible storage.

## Quick Start

### 1. Start MinIO

```bash
# Start MinIO in Docker
docker-compose up -d

# Check it's running
docker-compose ps

# View MinIO console at http://localhost:9001
# Login: minioadmin / minioadmin
```

### 2. Run Integration Tests

```bash
# Install test dependencies
pip install pytest pytest-cov boto3

# Run all tests including S3 integration tests
pytest tests/ -v -m integration

# Or run only S3 tests
pytest tests/test_s3_integration.py -v

# Run with coverage
pytest tests/ -v --cov=genro_storage
```

### 3. Stop MinIO

```bash
docker-compose down

# Or keep data and just stop
docker-compose stop
```

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures (MinIO setup)
├── test_local_storage.py          # Unit tests (no dependencies)
├── test_s3_integration.py         # Integration tests (requires MinIO)
└── test_memory_storage.py         # Memory backend tests
```

## Running Tests Without MinIO

```bash
# Skip integration tests
pytest tests/ -v -m "not integration"

# Or just run unit tests
pytest tests/test_local_storage.py -v
```

## MinIO Configuration

MinIO is configured via `docker-compose.yml`:

- **API Port**: 9000
- **Console Port**: 9001
- **User**: minioadmin
- **Password**: minioadmin

You can override these via environment variables:

```bash
export MINIO_ENDPOINT=http://localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin

pytest tests/test_s3_integration.py -v
```

## Debugging

### View MinIO Console

Open http://localhost:9001 in your browser to:
- See created buckets
- Browse uploaded files
- Check logs
- Monitor metrics

### Check MinIO Logs

```bash
docker-compose logs -f minio
```

### Clean Up Test Data

```bash
# Remove all MinIO data
docker-compose down -v

# Restart fresh
docker-compose up -d
```

## CI/CD Integration

For GitHub Actions, add this to your workflow:

```yaml
services:
  minio:
    image: minio/minio:latest
    ports:
      - 9000:9000
    env:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    options: >-
      --health-cmd "curl -f http://localhost:9000/minio/health/live"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 5
```

## Troubleshooting

### MinIO not starting

```bash
# Check Docker is running
docker ps

# Check logs
docker-compose logs minio

# Try rebuilding
docker-compose down -v
docker-compose up -d --build
```

### Tests failing with connection errors

```bash
# Verify MinIO is accessible
curl http://localhost:9000/minio/health/live

# Should return: OK
```

### Port already in use

```bash
# Change ports in docker-compose.yml
ports:
  - "19000:9000"  # Change 9000 to 19000
  - "19001:9001"  # Change 9001 to 19001

# Update MINIO_ENDPOINT
export MINIO_ENDPOINT=http://localhost:19000
```

## Testing Other Cloud Providers

The same pattern works for:

- **LocalStack** (AWS services): `docker-compose-localstack.yml`
- **Azurite** (Azure Blob): `docker-compose-azurite.yml`
- **fake-gcs-server** (GCS): `docker-compose-gcs.yml`

See respective files for setup instructions.
