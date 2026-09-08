# Comparative storage benchmarks

This first suite measures **S3-compatible object storage**, using local MinIO or
an existing Hetzner bucket. It compares the actual legacy implementation with
this checkout and direct clients. SFTP/WebDAV are not implemented yet; the
adapter boundary separates client operations from measurement and reporting.

No production storage implementation is modified by the benchmark.

## Setup

Run commands from the genro-storage repository root, preferably in a dedicated
virtual environment:

```bash
python -m pip install -e '.[benchmark,dev]'
export BENCH_LEGACY_ROOT=/path/to/Genropy/genropy
python -m pip install -e "$BENCH_LEGACY_ROOT/gnrpy"
```

The real legacy S3 module is loaded from `BENCH_LEGACY_ROOT`; its installed
runtime dependencies must be available. The CLI always imports genro-storage
from this checkout's `src/` directory, not a previously installed wheel.

## Local MinIO

```bash
docker compose -p genro-storage-bench -f benchmarks/compose.yaml up -d --wait
python -m benchmarks --smoke --create-bucket
```

MinIO is bound to localhost only: API port 29000, console port 29001. Local
credentials are `minioadmin` / `minioadmin`; the default bucket is
`genro-storage-benchmark`. Its volume and Compose project are separate from the
integration-test services. Override ports with `BENCH_MINIO_PORT` and
`BENCH_MINIO_CONSOLE_PORT`; when overriding the API port, set `BENCH_S3_ENDPOINT`
to the matching URL as well.

The smoke preset uses 1 KiB/64 KiB files, eight listing entries, concurrency 1/2,
one warmup and three measured rounds. A broader run uses 4 KiB/1 MiB/32 MiB
files, 64 listing entries, concurrency 1/4 and seven measured rounds:

```bash
python -m benchmarks
```

The full matrix can take several minutes and transfer many gigabytes even
though the fixture objects are relatively small. Start with smoke, especially
on a remote service. All sizes are exact bytes; `--sizes`, `--workers`,
`--repeats`, `--list-count`, `--calls`, `--operations`, `--adapters`,
`--warmups` and `--caches` override the defaults. For example:

```bash
python -m benchmarks --sizes 4096 --operations attrs listing tree_attrs \
  --workers 1 4 --repeats 10 --caches cold warm
```

For a focused version-awareness experiment on local MinIO:

```bash
python -m benchmarks --smoke --enable-versioning --history 5 \
  --adapters legacy genro genro-unversioned s3fs \
  --operations attrs listing tree_attrs --workers 1
```

`--enable-versioning` is explicitly restricted to the loopback MinIO target.
The suite never changes versioning on Hetzner. `--history > 1` requires an
already version-enabled bucket. Repeated fixture uploads create real versions;
cleanup removes both versions and delete markers from this run's prefix.

## Hetzner

Use a dedicated, existing benchmark bucket. Supply settings through the
environment or your local secret manager; the tool does not read `.env` files
automatically. Do not commit credential values.

```bash
export BENCH_S3_ENDPOINT='https://<your-object-storage-endpoint>'
export BENCH_S3_BUCKET='<dedicated-benchmark-bucket>'
export BENCH_S3_REGION='<bucket-region>'
# Set BENCH_S3_ACCESS_KEY and BENCH_S3_SECRET_KEY securely in the environment.
# BENCH_S3_TOKEN is optional when the provider uses session credentials.
python -m benchmarks --target hetzner --smoke
```

There are no remote credential, endpoint or bucket defaults. Creation of a
missing bucket requires `--create-bucket`; a bucket is never deleted. The
credential must permit object read/write/copy/delete, listing and reading
bucket-versioning status, plus version listing/deletion for versioned buckets.
Multipart upload permissions are needed by clients that use multipart writes.

Each invocation owns only `genro-storage-bench/<new-UUID>/`. Setup and validation
use a separate boto3 client. Cleanup runs after successful or failed runs and
on Ctrl-C, removing only objects under the generated prefix. If cleanup fails,
the report records the prefix for manual recovery. A forcibly killed process
or an interrupted multipart upload may require manual cleanup of that prefix
or its multipart uploads. No remote Hetzner run is part of local verification.

## Compared clients

| Name | Implementation |
|---|---|
| `legacy` | Real legacy `StorageNode` and `aws_s3.Service`; minimal site configuration only |
| `genro` | Public StorageManager/StorageNode API from this checkout |
| `genro-unversioned` | Same code, with the created s3fs client's `version_aware=False` for diagnosis |
| `backend` | Direct `FsspecBackend`, excluding manager/node operations |
| `s3fs` | Direct S3FileSystem; version awareness enabled to match the current genro default |
| `boto3` | Direct object requests and managed download for `local_path` |
| `smart-open` | Direct smart_open reads/writes; boto3 for the remaining operations |

The legacy adapter does **not** emulate S3 calls, load a database, or boot a web
site. It invokes the real service methods. The comparison isolates storage
operations, excluding the site's storage handler and service lookup overhead.
An instrumentation subclass observes the legacy `_client` accessor so HTTP
counting continues when the service renews its client and session after two
minutes; storage operations and renewal policy are unchanged.
Imports are completed before timing. All clients receive the same endpoint,
bucket, region, credentials and deterministic payloads. Each s3fs-based adapter
owns a fresh client instance; its normal defaults and effective configuration
are recorded. The diagnostic variant does not alter production source.

## What is measured

- `client_start_and_exists`: client construction/connection and the first
  existence check. One observation per adapter, separate from steady state.
- `exists`, `missing`: checks for a known object and a nonexistent key.
- `attrs`: `(mtime, size, is_directory)` for a known file.
- `listing`: complete names in a flat directory.
- `tree_attrs`: complete names and attributes for every file in that directory.
- `read`, `write`: consume all bytes or complete the upload before stopping.
- `copy`, `move`: same-bucket copies and moves of individual objects.
- `local_path`: obtain a local file and read its full contents, including cleanup.

SHA-256 checks, destination reads, move-source checks and listing/attribute
validation run **outside** timing. A wrong result invalidates the sample. For
example, legacy `children()` currently uses one listing page; a test exceeding
its page capacity must fail, rather than present an incomplete list as faster.

Cold means **client metadata cache invalidated before each batch**. It does not
mean a new connection, cold server caches, or cold OS caches. Warm means caches
are retained between calls, not guaranteed hits. Files are reopened on each
read. Multiple calls in one cold batch may populate and reuse cache entries.
All adapters and cases are shuffled with a recorded seed each round. Warmups
are retained in raw JSON but omitted from summaries.

Concurrency is a fixed-size **thread pool invoking synchronous APIs**, not a
comparison of native asyncio throughput. The pool is reused outside timing;
per-call latency starts inside its worker, while batch throughput includes
scheduling and joining. Different clients intentionally use their real
algorithms: equal output does not imply equal API-call sequences. Node creation
is included for legacy and genro operations.

HTTP accounting uses botocore/aiobotocore `before-send.s3.*` events, including
retry attempts. Counts are grouped by S3 operation and include only measured
client work; fixture writes and correctness checks are excluded. URL, headers,
keys and secret values are not captured. Credential-provider requests outside
S3 are not counted. For copy/move, MiB/s describes **logical object bytes**, not
bytes transferred over the network.

## Reports and interpretation

Each run creates an ignored `benchmarks/results/<UUID>/` directory containing:

- `results.json`: raw timings, warmups, HTTP operations, failures, parameters,
  Python/package versions, source path/revision/hash and effective client settings.
- `summary.csv`: medians, nearest-rank p95, operations/s, logical MiB/s,
  HTTP attempts per operation and failed-sample counts.
- `report.md`: readable comparison table, with sample counts and limitations.

Few repetitions do not establish a stable p95. Initialization has only one
observation. Run several complete invocations on an otherwise idle machine and
compare matching operation, size, concurrency, cache and version-history cases.
Capture Docker resource limits and server configuration alongside results if
comparing machines. Client metadata records versions; the MinIO image is pinned
in Compose. Results identify the endpoint host and bucket but exclude credentials.

MinIO over loopback helps expose client costs; Hetzner adds real network and
service behavior. Differences between those environments are not attributable
to latency alone: server implementation, TLS and available bandwidth also change.
Controlled latency injection is a future extension; it is not simulated by a
sleep around client calls.

## Verification and shutdown

```bash
python -m pytest benchmarks/tests -q -o addopts=''
python -m ruff check benchmarks
python -m benchmarks --smoke

# Opt in to real isolation, client-refresh and pagination-gate tests:
BENCH_TEST_ENDPOINT=http://127.0.0.1:29000 \
  python -m pytest benchmarks/tests -q -o addopts=''

docker compose -p genro-storage-bench -f benchmarks/compose.yaml stop
```

The unit tests cover statistics, correctness gates, cleanup scope and credential
handling. Actual client behavior is verified by the real MinIO run. A failed
sample or failed cleanup makes the CLI exit nonzero. Exceptions are recorded by
type, not raw text, to avoid leaking credentials from third-party errors.

## Portable HTML report

The recorded local comparison is available in
[reports/storage-benchmark.html](reports/storage-benchmark.html). It is a single,
mobile-friendly offline document with charts, filters, test evidence and CSV/JSON
exports. No server or external JavaScript libraries are needed.

To rebuild this snapshot when its five recorded result directories are present:

```bash
python -m benchmarks.html_report
```

The generator verifies completion, cleanup and summary medians against raw
samples. Test evidence is recorded separately in
`report_assets/verification.json`; generating the document does not rerun tests.

## First optimization and differential contracts

[The first optimization report](reports/optimization-round-1.html) compares the
original and modified checkout on the same local workload. It includes the
complete before/after matrix; raw observations are preserved in the companion
JSON. Regenerate it with `python -m benchmarks.optimization_report`.

`tests/test_attribute_snapshot.py` covers backend fallback, relative mount
scoping, virtual nodes, updates and permission errors. The opt-in
`benchmarks/tests/test_legacy_contract.py` compares real legacy and current S3
nodes for empty/binary files, Unicode paths, metadata, reads, temporary files,
overwrite, copy, move and delete, with and without bucket versioning.
It also enforces one HTTP HEAD for uncached file attributes.

The same differential suite has 10 passes and 4 failures on the original source:
directory timestamps differ and file metadata takes four HEADs. All 14 pass on
the modified checkout. Final combined verification: 584 passed, 14 skipped.
This is a bounded S3 contract, not proof of compatibility with every legacy API.
Recursive copies, existing destination directories, key/prefix collisions and
error semantics need explicit differential coverage before copy/move changes.
