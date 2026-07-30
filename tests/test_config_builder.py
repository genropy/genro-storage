# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the builder->mounts adapter (``StorageManager.configure`` accepting
a ``StorageConfig``).

``configure()`` gains two source forms on top of the untouched ``str`` /
``list[dict]`` path: a ``StorageConfig`` SUBCLASS (instantiated and built on a
fresh handler) and a ``StorageConfig`` INSTANCE (used as already built). Both are
flattened by ``_mounts_from_builder`` — walking the ``mounts`` collection in
declaration order, resolving ``BagResolver`` values through ``runtime_values``,
tagging the protocol from ``node_tag`` — into the ``list[dict]`` the existing
``_configure_mount`` consumes unchanged.

Local mounts use ``tmp_path``: ``LocalStorage`` validates a string ``base_path``
eagerly (the directory must exist), so the tests point it at a real directory.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from genro_bag.resolver import BagCbResolver

from genro_storage import StorageManager
from genro_storage.backends.local import LocalStorage
from genro_storage.backends.relative import RelativeMountBackend
from genro_storage.storage_grammar import StorageConfig
from genro_storage.exceptions import StorageConfigError


def _config_class(main):
    """A throwaway ``StorageConfig`` subclass with an injected ``main``.

    Mirrors the ``_build`` idiom of ``test_config_grammar`` but keeps the class
    (not just an instance) so it can be handed to ``configure()`` both as a
    subclass and, once built, as an instance.
    """
    return type("_TestConfig", (StorageConfig,), {"main": lambda self, root: main(root)})


def _mount_types(storage):
    """Backend class name per mount — a comparable, side-effect-free snapshot."""
    return {name: type(backend).__name__ for name, backend in storage._mounts.items()}


# ---------------------------------------------------------------------------
# Subclass vs instance equivalence
# ---------------------------------------------------------------------------


def test_subclass_and_instance_produce_the_same_mounts(tmp_path):
    """``configure(SubClass)`` and ``configure(instance)`` yield identical mounts."""

    def rec(root):
        m = root.mounts()
        m.local(name="home", base_path=str(tmp_path))
        m.memory(name="scratch")
        m.s3(name="uploads", bucket="my-bucket", endpoint_url="http://minio:9000")

    Config = _config_class(rec)

    from_subclass = StorageManager()
    from_subclass.configure(Config)

    page = Config()
    page.create()
    from_instance = StorageManager()
    from_instance.configure(page)

    # Declaration order is preserved (bag order == configuration order).
    assert list(from_subclass._mounts) == ["home", "scratch", "uploads"]
    assert _mount_types(from_subclass) == _mount_types(from_instance)


def test_protocol_comes_from_node_tag(tmp_path):
    """Each mount's backend is chosen from its element tag, not a ``protocol`` field."""

    def rec(root):
        m = root.mounts()
        m.local(name="home", base_path=str(tmp_path))
        m.s3(name="uploads", bucket="my-bucket", endpoint_url="http://minio:9000")

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert isinstance(storage._mounts["home"], LocalStorage)
    assert type(storage._mounts["uploads"]).__name__ == "FsspecBackend"


# ---------------------------------------------------------------------------
# Resolver resolution (read once, at configuration time)
# ---------------------------------------------------------------------------


def test_resolver_is_read_at_configuration_time(tmp_path):
    """A ``BagResolver`` placed in the recipe reaches the backend as its resolved value."""
    deploy_root = str(tmp_path)
    calls = []

    def read_root():
        calls.append(1)
        return deploy_root

    def rec(root):
        root.mounts().local(name="home", base_path=BagCbResolver(read_root))

    storage = StorageManager()
    storage.configure(_config_class(rec))

    backend = storage._mounts["home"]
    assert isinstance(backend, LocalStorage)
    # The resolved value, not the resolver object.
    assert str(backend.base_path) == str(Path(deploy_root).resolve())
    # ``configure()`` consumes each value once, so the resolver is read once.
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# Relative mounts (routed on the ':' in ``path``, no ``protocol`` key)
# ---------------------------------------------------------------------------


def test_relative_mount_after_parent_resolves_and_enforces_permissions():
    """A relative mount declared after its parent builds and keeps its permissions."""

    def rec(root):
        m = root.mounts()
        m.memory(name="data", base_path="/data")
        m.relative(name="public", path="data:public", permissions="readonly")

    storage = StorageManager()
    storage.configure(_config_class(rec))

    backend = storage._mounts["public"]
    assert isinstance(backend, RelativeMountBackend)
    assert backend.relative_path == "public"
    assert backend.permissions == "readonly"


def test_relative_mount_before_parent_raises():
    """Declaring a relative mount before its parent fails, as with the dict path."""

    def rec(root):
        m = root.mounts()
        m.relative(name="public", path="data:public")
        m.memory(name="data")

    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="Parent mount 'data' not found"):
        storage.configure(_config_class(rec))


# ---------------------------------------------------------------------------
# Empty and unbuilt edge cases
# ---------------------------------------------------------------------------


def test_built_but_empty_config_mounts_nothing():
    """A built config declaring an empty ``mounts`` collection configures zero mounts.

    Zero mounts is legitimate — a bare ``StorageManager()`` already has none — so
    the empty collection (``value is None``, not an empty Bag) must not raise.
    """

    def rec(root):
        root.mounts()

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert storage.get_mount_names() == []


def test_unbuilt_instance_raises():
    """``configure(StorageConfig())`` on a never-built instance is misuse, not empty.

    An instance never built has an empty source, and an instance is used as
    ALREADY BUILT, so this raises instead of silently doing nothing.
    """
    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="has not been built"):
        storage.configure(StorageConfig())
