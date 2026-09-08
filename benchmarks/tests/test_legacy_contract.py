"""Differential contracts against the unmodified legacy S3 service on real MinIO."""

import os
import uuid

import pytest

from benchmarks.adapters import FsspecAdapter, LegacyAdapter, Target, load_legacy
from benchmarks.runner import Fixtures


@pytest.fixture(params=[False, True], ids=["unversioned", "versioned"])
def pair(request):
    endpoint = os.environ.get("BENCH_TEST_ENDPOINT")
    root = os.environ.get("BENCH_LEGACY_ROOT")
    if not endpoint or not root:
        pytest.skip("Set BENCH_TEST_ENDPOINT and BENCH_LEGACY_ROOT")
    target = Target(
        endpoint, "storage-contract-" + uuid.uuid4().hex, "us-east-1", "minioadmin", "minioadmin"
    )
    fixture = Fixtures(target, str(uuid.uuid4()))
    adapters = []
    fixture.client.create_bucket(Bucket=target.bucket)
    try:
        if request.param:
            fixture.client.put_bucket_versioning(
                Bucket=target.bucket, VersioningConfiguration={"Status": "Enabled"}
            )
        fixture.prepare([16], 2, 1)
        adapters.append(LegacyAdapter(target, fixture.prefix, load_legacy(root)))
        adapters.append(FsspecAdapter(target, fixture.prefix, layer="genro"))
        yield fixture, *adapters
    finally:
        fixture.cleanup()
        fixture.client.delete_bucket(Bucket=target.bucket)
        fixture.client.close()
        for adapter in adapters:
            adapter.close()


@pytest.mark.parametrize(
    "payload", [b"", b"hello\x00\xff", b"x" * 65536], ids=["empty", "binary", "64k"]
)
def test_file_metadata_and_reads_match(pair, payload):
    fixture, legacy, current = pair
    key = "nested/Caffè con spazi.bin"
    fixture.put(key, payload)
    assert legacy.attrs(key) == current.attrs(key)
    for adapter in (legacy, current):
        assert adapter.exists(key)
        assert adapter.read(key) == payload
        with adapter.local_path(key) as local:
            from pathlib import Path

            assert Path(local).read_bytes() == payload


def test_absence_and_implicit_directory_contract(pair):
    _, legacy, current = pair
    for adapter in (legacy, current):
        assert adapter.attrs("absent") == (None, None, False)
        assert not adapter.exists("absent")
        assert adapter.exists("listing")
        assert adapter.attrs("listing")[1:] == (None, True)
        assert adapter.listing("listing") == ["000000.bin", "000001.bin"]
    assert legacy.attrs("listing") == current.attrs("listing") == (None, None, True)


def test_write_overwrite_copy_move_and_delete_match(pair):
    fixture, legacy, current = pair
    for index, adapter in enumerate((legacy, current)):
        source, copied, moved = [f"workflow-{index}/{name}" for name in ("source", "copy", "move")]
        adapter.write(source, b"old")
        adapter.write(source, b"new content")
        adapter.invalidate()
        assert adapter.read(source) == b"new content"
        adapter.copy(source, copied)
        assert fixture.read(copied) == b"new content"
        assert adapter.exists(source)
        adapter.move(copied, moved)
        adapter.invalidate()
        assert not adapter.exists(copied)
        assert fixture.read(moved) == b"new content"
        adapter.node(moved).delete()
        adapter.invalidate()
        assert not adapter.exists(moved)


def test_metadata_observes_overwrite_after_invalidation(pair):
    fixture, legacy, current = pair
    path = "files/16.bin"
    assert legacy.attrs(path) == current.attrs(path)
    fixture.put(path, b"changed")
    current.invalidate()
    assert legacy.attrs(path) == current.attrs(path)
    assert current.attrs(path)[1] == 7


def test_current_file_attributes_use_one_remote_metadata_request(pair):
    _, _, current = pair
    current.invalidate()
    current.requests.reset()
    assert current.attrs("files/16.bin")[1:] == (16, False)
    assert current.requests.snapshot() == {"HeadObject": 1}
