"""Unit checks for benchmark accounting and correctness gates.

Actual client compatibility is verified by the MinIO smoke run, not mocks.
"""

import uuid

import pytest

from benchmarks.__main__ import parse_args
from benchmarks.adapters import Requests, Target
from benchmarks.runner import Fixtures, percentile, save_report, summarize


def sample(**changes):
    row = dict(
        adapter="boto3",
        operation="read",
        size_bytes=1024,
        workers=1,
        cache="cold",
        warmup=False,
        elapsed_s=0.02,
        latencies_s=[0.01, 0.02],
        requests={"GetObject": 2},
        errors=[],
        calls=2,
    )
    return dict(row, **changes)


def test_summary_excludes_warmups_and_failed_samples():
    result = summarize(
        [
            sample(),
            sample(warmup=True, elapsed_s=99),
            sample(errors=["AssertionError"], elapsed_s=0.00001),
        ]
    )[0]
    assert result["samples"] == 2
    assert result["failed_samples"] == 1
    assert result["median_ms"] == 15
    assert result["p95_ms"] == 20
    assert result["ops_s"] == 100
    assert result["http_per_op"] == 1
    assert percentile(list(range(1, 101)), 0.95) == 95


def test_all_failed_has_no_speed_claim():
    row = summarize([sample(errors=["AssertionError"])])[0]
    assert row["failed_samples"] == 1
    assert "median_ms" not in row
    assert "ops_s" not in row


def test_http_attempt_counter_counts_retries_and_resets():
    counter = Requests()
    counter.sent("before-send.s3.GetObject", request="never retained")
    counter.sent("before-send.s3.GetObject")
    counter.sent("before-send.s3.HeadObject")
    assert counter.snapshot() == {"GetObject": 2, "HeadObject": 1}
    counter.reset()
    assert counter.snapshot() == {}


def test_incomplete_listing_is_not_accepted():
    fixtures = object.__new__(Fixtures)
    with pytest.raises(AssertionError, match="listing"):
        fixtures.check("listing", ["000000.bin"], "", "", 1, 2)
    fixtures.check("listing", ["000000.bin", "000001.bin"], "", "", 1, 2)


def test_read_corruption_is_not_accepted():
    from benchmarks.runner import digest

    fixtures = object.__new__(Fixtures)
    fixtures.hashes = {3: digest(b"abc")}
    with pytest.raises(AssertionError, match="mismatch"):
        fixtures.check("read", b"abd", "", "", 3, 1)
    fixtures.check("read", b"abc", "", "", 3, 1)


@pytest.mark.parametrize(
    "prefix",
    [
        "",
        "/",
        "other/",
        "genro-storage-bench/",
        "genro-storage-bench/not-a-uuid/",
        "genro-storage-bench/" + str(uuid.uuid4()) + "/extra",
    ],
)
def test_cleanup_rejects_unscoped_paths_before_any_network_call(prefix):
    fixtures = object.__new__(Fixtures)
    fixtures.prefix = prefix
    with pytest.raises(ValueError):
        fixtures.cleanup()


def test_report_keeps_raw_attempts_and_no_speed_for_failed_sample(tmp_path):
    save_report(tmp_path, dict(run_id="test", status="failed"), [sample(errors=["AssertionError"])])
    assert "GetObject" in (tmp_path / "results.json").read_text()
    assert "1 / 1" in (tmp_path / "report.md").read_text()
    assert "http_per_op" in (tmp_path / "summary.csv").read_text()


def test_remote_requires_explicit_settings(monkeypatch):
    for name in ("ENDPOINT", "BUCKET", "REGION", "ACCESS_KEY", "SECRET_KEY"):
        monkeypatch.delenv("BENCH_S3_" + name, raising=False)
    with pytest.raises(SystemExit):
        parse_args(["--target", "hetzner", "--adapters", "boto3"])


def test_minio_cannot_point_at_remote_with_default_credentials(monkeypatch):
    monkeypatch.setenv("BENCH_S3_ENDPOINT", "https://remote.example")
    with pytest.raises(SystemExit):
        parse_args(["--adapters", "boto3"])


def test_credentials_not_in_target_repr():
    target = Target(
        "http://localhost", "bucket", "region", "private-key", "private-secret", "private-token"
    )
    assert "private-" not in repr(target)
