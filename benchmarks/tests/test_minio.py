"""Real cleanup isolation test; opt in with BENCH_TEST_ENDPOINT."""

import os
import uuid

import pytest

from benchmarks.adapters import Target
from benchmarks.runner import Fixtures


@pytest.fixture(scope="module", autouse=True)
def benchmark_bucket():
    """Allow integration checks to run against a newly started MinIO."""
    from botocore.exceptions import ClientError

    endpoint = os.environ.get("BENCH_TEST_ENDPOINT")
    if not endpoint:
        return
    target = Target(endpoint, "genro-storage-benchmark", "us-east-1", "minioadmin", "minioadmin")
    client = target.client()
    try:
        try:
            client.head_bucket(Bucket=target.bucket)
        except ClientError as exc:
            if exc.response["Error"]["Code"] not in ("404", "NoSuchBucket", "NotFound"):
                raise
            client.create_bucket(Bucket=target.bucket)
    finally:
        client.close()


@pytest.mark.integration
def test_cleanup_preserves_other_runs():
    endpoint = os.environ.get("BENCH_TEST_ENDPOINT")
    if not endpoint:
        pytest.skip("Set BENCH_TEST_ENDPOINT to the dedicated local MinIO")
    target = Target(endpoint, "genro-storage-benchmark", "us-east-1", "minioadmin", "minioadmin")
    own = Fixtures(target, str(uuid.uuid4()))
    other = Fixtures(target, str(uuid.uuid4()))
    try:
        own.prepare([16], 2, 1)
        other.prepare([16], 2, 1)
        own.cleanup()
        assert other.read("files/16.bin") == other.payloads[16]
        assert (
            own.client.list_objects_v2(Bucket=target.bucket, Prefix=own.prefix).get("KeyCount") == 0
        )
    finally:
        own.cleanup()
        other.cleanup()
        own.client.close()
        other.client.close()


@pytest.mark.integration
def test_legacy_request_counter_survives_real_client_refresh():
    from datetime import datetime, timedelta
    from benchmarks.adapters import LegacyAdapter, load_legacy

    endpoint = os.environ.get("BENCH_TEST_ENDPOINT")
    root = os.environ.get("BENCH_LEGACY_ROOT")
    if not endpoint or not root:
        pytest.skip("Set BENCH_TEST_ENDPOINT and BENCH_LEGACY_ROOT")
    target = Target(endpoint, "genro-storage-benchmark", "us-east-1", "minioadmin", "minioadmin")
    fixture = Fixtures(target, str(uuid.uuid4()))
    adapter = None
    try:
        fixture.prepare([16], 1, 1)
        adapter = LegacyAdapter(target, fixture.prefix, load_legacy(root))
        assert adapter.exists("files/16.bin")
        assert adapter.requests.snapshot() == {"HeadObject": 1}
        expired = datetime.now() - timedelta(seconds=121)
        adapter.service._boto_client_ts = expired
        adapter.service._boto_session_ts = expired
        adapter.requests.reset()
        assert adapter.exists("files/16.bin")
        assert adapter.requests.snapshot() == {"HeadObject": 1}
        assert len(adapter.clients) == 2
    finally:
        fixture.cleanup()
        fixture.client.close()
        if adapter:
            adapter.close()


@pytest.mark.integration
def test_real_legacy_pagination_limit_fails_correctness_gate():
    from benchmarks.adapters import FsspecAdapter, LegacyAdapter, load_legacy

    endpoint = os.environ.get("BENCH_TEST_ENDPOINT")
    root = os.environ.get("BENCH_LEGACY_ROOT")
    if not endpoint or not root:
        pytest.skip("Set BENCH_TEST_ENDPOINT and BENCH_LEGACY_ROOT")
    target = Target(endpoint, "genro-storage-benchmark", "us-east-1", "minioadmin", "minioadmin")
    fixture = Fixtures(target, str(uuid.uuid4()))
    adapters = []
    try:
        fixture.prepare([16], 1001, 1)
        legacy = LegacyAdapter(target, fixture.prefix, load_legacy(root))
        adapters.append(legacy)
        current = FsspecAdapter(target, fixture.prefix, layer="genro")
        adapters.append(current)
        with pytest.raises(AssertionError, match="listing"):
            fixture.check("listing", legacy.listing("listing"), "", "", 16, 1001)
        fixture.check("listing", current.listing("listing"), "", "", 16, 1001)
    finally:
        fixture.cleanup()
        fixture.client.close()
        for adapter in adapters:
            adapter.close()
