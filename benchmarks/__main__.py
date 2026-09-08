"""Run with python -m benchmarks. Credentials are read only from the environment."""

import argparse
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit

# Always benchmark this checkout, never a separately installed genro-storage.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from .adapters import ADAPTERS, Target, load_legacy
from .runner import OPERATIONS, run


def positive(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("Must be positive")
    return result


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("minio", "hetzner"), default="minio")
    parser.add_argument("--legacy-root", type=Path, default=os.environ.get("BENCH_LEGACY_ROOT"))
    parser.add_argument("--adapters", nargs="+", choices=ADAPTERS, default=list(ADAPTERS))
    parser.add_argument("--operations", nargs="+", choices=OPERATIONS, default=list(OPERATIONS))
    parser.add_argument("--sizes", nargs="+", type=positive, help="Object sizes in bytes")
    parser.add_argument("--workers", nargs="+", type=positive)
    parser.add_argument("--calls", type=positive, default=1, help="Calls per worker per sample")
    parser.add_argument("--repeats", type=positive)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--list-count", type=positive)
    parser.add_argument("--history", type=positive, default=1, help="Fixture versions per key")
    parser.add_argument("--caches", nargs="+", choices=("cold", "warm"), default=["cold", "warm"])
    parser.add_argument("--seed", type=int, default=8319)
    parser.add_argument("--output", type=Path, default=Path("benchmarks/results"))
    parser.add_argument("--smoke", action="store_true", help="Small, quick end-to-end run")
    parser.add_argument("--create-bucket", action="store_true", help="Create bucket if missing")
    parser.add_argument(
        "--enable-versioning",
        action="store_true",
        help="Enable versioning on the local MinIO benchmark bucket only",
    )
    options = parser.parse_args(argv)
    if options.warmups < 0:
        parser.error("--warmups cannot be negative")
    if "legacy" in options.adapters and not options.legacy_root:
        parser.error("Use --legacy-root or BENCH_LEGACY_ROOT to load the real legacy service")
    if options.enable_versioning and options.target != "minio":
        parser.error("--enable-versioning is restricted to local MinIO")
    options.sizes = list(
        dict.fromkeys(
            options.sizes or ([1024, 65536] if options.smoke else [4096, 1048576, 33554432])
        )
    )
    options.workers = list(dict.fromkeys(options.workers or ([1, 2] if options.smoke else [1, 4])))
    options.repeats = options.repeats or (3 if options.smoke else 7)
    options.list_count = options.list_count or (8 if options.smoke else 64)
    options.adapters = list(dict.fromkeys(options.adapters))
    options.operations = list(dict.fromkeys(options.operations))
    options.caches = list(dict.fromkeys(options.caches))
    local = options.target == "minio"
    defaults = (
        dict(
            ENDPOINT="http://127.0.0.1:29000",
            BUCKET="genro-storage-benchmark",
            REGION="us-east-1",
            ACCESS_KEY="minioadmin",
            SECRET_KEY="minioadmin",
        )
        if local
        else {}
    )
    values = {
        name: os.environ.get("BENCH_S3_" + name, defaults.get(name))
        for name in ("ENDPOINT", "BUCKET", "REGION", "ACCESS_KEY", "SECRET_KEY")
    }
    if not all(values.values()):
        parser.error("Set BENCH_S3_ENDPOINT, BUCKET, REGION, ACCESS_KEY and SECRET_KEY for Hetzner")
    parsed = urlsplit(values["ENDPOINT"])
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in ("", "/")
    ):
        parser.error("Endpoint must be an HTTP(S) origin without credentials, path or query")
    if local and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        parser.error("The minio target requires a loopback endpoint")
    options.endpoint_host = parsed.netloc
    target = Target(
        values["ENDPOINT"],
        values["BUCKET"],
        values["REGION"],
        values["ACCESS_KEY"],
        values["SECRET_KEY"],
        os.environ.get("BENCH_S3_TOKEN"),
    )
    return options, target


def main():
    options, target = parse_args()
    try:
        legacy = load_legacy(options.legacy_root) if "legacy" in options.adapters else None
        client = target.client()
        try:
            from botocore.exceptions import ClientError

            try:
                client.head_bucket(Bucket=target.bucket)
            except ClientError as exc:
                if not options.create_bucket or exc.response["Error"]["Code"] not in (
                    "404",
                    "NoSuchBucket",
                ):
                    raise
                kwargs = (
                    {}
                    if target.region == "us-east-1"
                    else {"CreateBucketConfiguration": {"LocationConstraint": target.region}}
                )
                client.create_bucket(Bucket=target.bucket, **kwargs)
            if options.enable_versioning:
                client.put_bucket_versioning(
                    Bucket=target.bucket, VersioningConfiguration={"Status": "Enabled"}
                )
        finally:
            client.close()
        output, passed = run(target, options, legacy)
        print(f"{'PASS' if passed else 'FAIL'}: {output / 'report.md'}")
        return 0 if passed else 1
    except KeyboardInterrupt:
        print("Benchmark interrupted; see results.json for cleanup status.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(
            f"Benchmark failed: {type(exc).__name__}. Check configuration and results.json "
            "(if created). Exception details are suppressed to avoid exposing credentials.",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
