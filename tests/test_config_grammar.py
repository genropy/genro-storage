# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the ``StorageConfig`` grammar (``genro_storage.config``).

The grammar is a data-only ``genro-builders`` dialect: one ``@element`` per
protocol, each mount living inside the ``mounts`` collection keyed by ``name``.
These tests exercise the grammar in isolation (no ``StorageManager``), through
the same ``_build`` idiom the genro-builders tests use
(``tests/test_collection_key.py:42``): a throw-away subclass whose ``main``
recipe is supplied per test, mounted on a fresh ``BuilderHandler``.

Validation is the signature's own: a required field (a parameter without a
default) missing raises ``Validation failed: required attribute ...``; a
``permissions`` value outside the ``Literal`` raises ``Validation failed``; two
mounts with the same ``name`` clash on the collection key; a mount element
placed outside ``mounts`` violates its ``parent_tags``.
"""

from __future__ import annotations

import pytest
from genro_builders.builder import BuilderHandler

from genro_storage.config import StorageConfig


def _build(main):
    """Build a ``StorageConfig`` whose ``mounts`` are populated by ``main(root)``.

    Mirrors ``genro-builders`` ``tests/test_collection_key.py:_build``: a fresh
    subclass gets ``main`` injected, then ``add_builder`` runs ``create()`` which
    calls it. A grammar error inside the recipe propagates out of ``add_builder``.
    """

    class _H(StorageConfig):
        pass

    _H.main = lambda self, root: main(root)
    page = _H()
    BuilderHandler().add_builder(page)
    return page


def _mounts(page):
    """The ``mounts`` collection bag of a built page."""
    return page.source.get_node("mounts").value


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_mounts_keyed_by_name_and_tagged_by_protocol():
    """Each mount is labelled by its ``name`` and carries its protocol as node_tag."""

    def rec(root):
        m = root.mounts()
        m.local(name="home", base_path="/srv/data")
        m.s3(name="uploads", bucket="my-bucket", endpoint_url="http://minio:9000")
        m.memory(name="scratch")

    mounts = _mounts(_build(rec))
    assert [n.label for n in mounts] == ["home", "uploads", "scratch"]
    assert mounts.get_node("home").node_tag == "local"
    assert mounts.get_node("uploads").node_tag == "s3"
    assert mounts.get_node("scratch").node_tag == "memory"


def test_only_provided_fields_are_captured_as_attributes():
    """Unset optional fields are dropped; the set ones survive as node attributes."""
    mounts = _mounts(_build(lambda root: root.mounts().s3(name="uploads", bucket="b")))
    attrs = dict(mounts.get_node("uploads").attr)
    assert attrs == {"name": "uploads", "bucket": "b"}


def test_relative_mount_builds():
    """``relative(name=..., path='parent:sub')`` builds with its permissions."""

    def rec(root):
        m = root.mounts()
        m.local(name="home", base_path="/srv/data")
        m.relative(name="public", path="home:public", permissions="readonly")

    node = _mounts(_build(rec)).get_node("public")
    assert node.node_tag == "relative"
    assert node.attr.get("path") == "home:public"
    assert node.attr.get("permissions") == "readonly"


@pytest.mark.parametrize("value", ["readonly", "readwrite", "delete"])
def test_valid_permissions_accepted(value):
    """Every permission in the ``Literal`` is accepted."""
    mounts = _mounts(_build(lambda root: root.mounts().memory(name="m", permissions=value)))
    assert mounts.get_node("m").attr.get("permissions") == value


# ---------------------------------------------------------------------------
# Pointer-able wide fields (see the plan Notes: pointers are strings, so
# non-string fields are typed wide to let a ``^pointer`` through the type check)
# ---------------------------------------------------------------------------


def test_pointer_string_accepted_on_wide_typed_field():
    """A ``^pointer`` on the wide-typed ``port`` passes the signature type check."""
    mounts = _mounts(
        _build(
            lambda root: root.mounts().smb(name="share", host="h", share="s", port="^env.smb_port")
        )
    )
    assert mounts.get_node("share").attr.get("port") == "^env.smb_port"


def test_native_int_still_accepted_on_wide_typed_field():
    """The wide type keeps the native value valid too."""
    mounts = _mounts(
        _build(lambda root: root.mounts().smb(name="share", host="h", share="s", port=445))
    )
    assert mounts.get_node("share").attr.get("port") == 445


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_missing_required_field_raises():
    """A required field (``s3.bucket``) missing raises on ``required attribute``."""
    with pytest.raises(ValueError, match="required attribute"):
        _build(lambda root: root.mounts().s3(name="uploads"))


def test_missing_name_raises():
    """``name`` is required on every mount element."""
    with pytest.raises(ValueError, match="required attribute"):
        _build(lambda root: root.mounts().memory())


def test_invalid_permissions_raises():
    """A ``permissions`` value outside the ``Literal`` raises ``Validation failed``."""
    with pytest.raises(ValueError, match="Validation failed"):
        _build(lambda root: root.mounts().local(name="home", base_path="/srv", permissions="bogus"))


def test_duplicate_name_raises():
    """Two mounts resolving to the same ``name`` clash on the collection key."""

    def rec(root):
        m = root.mounts()
        m.memory(name="dup")
        m.memory(name="dup")

    with pytest.raises(ValueError, match="duplicate collection key"):
        _build(rec)


def test_mount_outside_mounts_raises():
    """A mount element placed on the root, outside ``mounts``, violates parent_tags."""
    with pytest.raises(ValueError):
        _build(lambda root: root.s3(name="x", bucket="b"))
