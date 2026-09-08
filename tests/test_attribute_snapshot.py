"""Attribute snapshots preserve node contracts without caching stale file data."""

from datetime import datetime, timezone

import pytest

from genro_storage import StorageManager
from genro_storage.backends.fsspec import FsspecBackend


@pytest.mark.parametrize("protocol", ["memory", "local"])
def test_attributes_follow_create_overwrite_delete(tmp_path, protocol):
    manager = StorageManager()
    config = dict(name="test", protocol=protocol, base_path=str(tmp_path))
    manager.configure([config])
    node = manager.node("test:entry")
    assert node.ext_attributes == (None, None, False)
    node.write_bytes(b"first")
    assert node.ext_attributes[1:] == (5, False)
    node.write_bytes(b"x")
    assert node.ext_attributes[1:] == (1, False)
    node.delete()
    assert node.ext_attributes == (None, None, False)
    assert manager.iternode(node).ext_attributes == (None, None, False)


def test_metadata_permission_failure_is_not_reported_as_absence(monkeypatch):
    backend = FsspecBackend("memory")

    def denied(path):
        raise PermissionError("denied")

    monkeypatch.setattr(backend.fs, "info", denied)
    with pytest.raises(PermissionError):
        backend.ext_attributes("private")


@pytest.mark.parametrize(
    "metadata,expected",
    [
        (
            {"type": "file", "size": 0, "LastModified": datetime(2020, 1, 1, tzinfo=timezone.utc)},
            (1577836800.0, 0, False),
        ),
        ({"type": "directory", "size": 0}, (None, None, True)),
    ],
)
def test_s3_metadata_without_fabricated_directory_timestamp(monkeypatch, metadata, expected):
    backend = FsspecBackend("memory")
    # Only the external filesystem metadata response is substituted.
    backend.protocol = "s3"
    monkeypatch.setattr(backend.fs, "info", lambda path: metadata)
    assert backend.ext_attributes("entry") == expected


def test_relative_mount_keeps_parent_snapshot_and_scope(tmp_path):
    from genro_storage.backends.relative import RelativeMountBackend

    parent = FsspecBackend("memory", base_path=str(tmp_path))
    parent.write_bytes("nested/entry", b"scoped")
    parent.write_bytes("entry", b"outside")
    child = RelativeMountBackend(parent, "nested", permissions="readonly")
    assert child.ext_attributes("entry")[1:] == (6, False)
    assert child.ext_attributes("missing") == (None, None, False)
