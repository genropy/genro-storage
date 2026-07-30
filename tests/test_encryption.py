# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for at-rest encryption on a mount.

A mount declared ``encrypted`` stores ciphertext while its nodes read and write
plaintext: the tests assert both halves of that claim at once — the value comes
back unchanged AND the bytes on disk are not the value. Key material is one or
more comma-separated Fernet keys with ``MultiFernet`` semantics (the FIRST key
encrypts, ALL keys decrypt), so rotation is asserted by writing with one key set
and reading with another that merely still contains the old key.

The contract has no silent degradation, and each of its edges gets a test: an
encrypted mount with no installed key is dormant (runtime error), key material
that resolves empty is a configuration error, and declaring an encrypted mount
without the ``cryptography`` package installed is a configuration error too.
That last one is exercised by faking the package away — it IS installed here,
since the whole suite needs it.
"""

from __future__ import annotations

import pytest
from cryptography.fernet import Fernet, InvalidToken
from genro_bag.resolver import BagCbResolver

from genro_storage import StorageManager
from genro_storage import manager as manager_module
from genro_storage.storage_grammar import StorageConfig
from genro_storage.exceptions import StorageConfigError, StorageError


@pytest.fixture
def key():
    """A single fresh Fernet key, as the configuration carries it: a str."""
    return Fernet.generate_key().decode()


@pytest.fixture
def storage(tmp_path, key):
    """A manager with one encrypted and one plain local mount on ``tmp_path``."""
    storage = StorageManager()
    storage.configure(
        [
            {"name": "secure", "protocol": "local", "base_path": str(tmp_path), "encrypted": True},
            {"name": "plain", "protocol": "local", "base_path": str(tmp_path)},
        ],
        storage_key=key,
    )
    return storage


def _config_class(main):
    """A throwaway ``StorageConfig`` subclass with an injected ``main``."""
    return type("_TestConfig", (StorageConfig,), {"main": lambda self, root: main(root)})


# ---------------------------------------------------------------------------
# Roundtrip: plaintext to the caller, ciphertext on the medium
# ---------------------------------------------------------------------------


def test_text_roundtrip_leaves_no_plaintext_on_disk(storage, tmp_path):
    """``write_text``/``read_text`` are transparent; the file itself is not the text."""
    node = storage.node("secure:secret.txt")
    node.write_text("attack at dawn")

    assert node.read_text() == "attack at dawn"
    on_disk = (tmp_path / "secret.txt").read_bytes()
    assert b"attack at dawn" not in on_disk
    assert on_disk.startswith(b"gAAAAA")  # Fernet token prefix


def test_bytes_roundtrip_leaves_no_plaintext_on_disk(storage, tmp_path):
    """``write_bytes``/``read_bytes`` are transparent on the same terms."""
    node = storage.node("secure:secret.bin")
    node.write_bytes(b"\x00\x01payload\x02")

    assert node.read_bytes() == b"\x00\x01payload\x02"
    assert b"payload" not in (tmp_path / "secret.bin").read_bytes()


def test_read_write_generic_forms_are_transparent_too(storage):
    """``read()``/``write()`` route through the same layer as the convenience pair."""
    node = storage.node("secure:generic.txt")
    node.write("hello", mode="w")

    assert node.read() == "hello"
    assert node.read(mode="rb") == b"hello"


def test_ciphertext_differs_between_writes_of_the_same_content(storage, tmp_path):
    """Fernet is non-deterministic: identical plaintext, different bytes at rest."""
    node = storage.node("secure:a.txt")
    node.write_text("same")
    first = (tmp_path / "a.txt").read_bytes()
    node.write_text("same")
    second = (tmp_path / "a.txt").read_bytes()

    assert first != second
    assert node.read_text() == "same"


def test_plain_mount_alongside_is_untouched(storage, tmp_path):
    """Encryption is per mount: the plain one still writes the bytes it is given."""
    storage.node("plain:visible.txt").write_text("in the clear")

    assert (tmp_path / "visible.txt").read_bytes() == b"in the clear"
    assert storage.mount_is_encrypted("secure") is True
    assert storage.mount_is_encrypted("plain") is False


def test_skip_if_unchanged_compares_plaintext(storage):
    """The skip check sees decrypted content, so re-writing the same text skips."""
    node = storage.node("secure:skip.txt")

    assert node.write_text("stable", skip_if_unchanged=True) is True
    assert node.write_text("stable", skip_if_unchanged=True) is False
    assert node.write_text("changed", skip_if_unchanged=True) is True


# ---------------------------------------------------------------------------
# Relative mounts: the flag follows the stored bytes
# ---------------------------------------------------------------------------


@pytest.fixture
def storage_with_child(tmp_path, key):
    """``storage`` plus a relative mount inside the encrypted one."""
    storage = StorageManager()
    storage.configure(
        [
            {"name": "secure", "protocol": "local", "base_path": str(tmp_path), "encrypted": True},
            {"name": "child", "path": "secure:inner"},
        ],
        storage_key=key,
    )
    return storage


def test_relative_mount_inherits_the_parent_flag(storage_with_child):
    """A relative mount over an encrypted parent is itself encrypted."""
    assert storage_with_child.mount_is_encrypted("child") is True


def test_relative_mount_over_plain_parent_stays_plain(storage, tmp_path):
    """The inheritance is of the parent's actual flag, not unconditional."""
    storage.configure([{"name": "sub", "path": "plain:inner"}])

    assert storage.mount_is_encrypted("sub") is False


def test_read_through_the_child_sees_plaintext(storage_with_child, tmp_path):
    """Bytes written by the parent read back as plaintext through the child."""
    storage_with_child.node("secure:inner/f.txt").write_text("SECRET-MARKER")

    assert storage_with_child.node("child:f.txt").read_text() == "SECRET-MARKER"
    on_disk = (tmp_path / "inner" / "f.txt").read_bytes()
    assert b"SECRET-MARKER" not in on_disk


def test_write_through_the_child_lands_ciphertext(storage_with_child, tmp_path):
    """Bytes written through the child are ciphertext the parent can read."""
    storage_with_child.node("child:g.txt").write_text("WRITTEN-VIA-CHILD")

    assert storage_with_child.node("secure:inner/g.txt").read_text() == "WRITTEN-VIA-CHILD"
    on_disk = (tmp_path / "inner" / "g.txt").read_bytes()
    assert b"WRITTEN-VIA-CHILD" not in on_disk
    assert on_disk.startswith(b"gAAAAA")


# ---------------------------------------------------------------------------
# Key rotation: the first key encrypts, all keys decrypt
# ---------------------------------------------------------------------------


def test_rotation_reads_with_the_old_key_and_writes_with_the_new(storage, tmp_path, key):
    """After rotation the old content still reads; new content uses the new key."""
    storage.node("secure:rotated.txt").write_text("written with the old key")

    new_key = Fernet.generate_key().decode()
    storage.set_encryption_keys(f"{new_key},{key}")

    node = storage.node("secure:rotated.txt")
    assert node.read_text() == "written with the old key"

    node.write_text("written with the new key")
    # The new key alone suffices for what was just written; the old one does not.
    assert Fernet(new_key).decrypt((tmp_path / "rotated.txt").read_bytes()) == (
        b"written with the new key"
    )
    with pytest.raises(InvalidToken):
        Fernet(key).decrypt((tmp_path / "rotated.txt").read_bytes())


def test_a_key_no_longer_installed_cannot_read_its_content(storage):
    """Dropping a key from the material is what makes its content unreadable."""
    storage.node("secure:orphan.txt").write_text("only the old key knows")
    storage.set_encryption_keys(Fernet.generate_key().decode())

    with pytest.raises(InvalidToken):
        storage.node("secure:orphan.txt").read_text()


def test_keys_are_whitespace_tolerant(tmp_path, key):
    """A comma-separated list may be spaced out; the keys are stripped."""
    storage = StorageManager()
    storage.configure(
        [{"name": "secure", "protocol": "local", "base_path": str(tmp_path), "encrypted": True}],
        storage_key=f"  {key} , {Fernet.generate_key().decode()}  ",
    )
    storage.node("secure:spaced.txt").write_text("fine")

    assert storage.node("secure:spaced.txt").read_text() == "fine"


# ---------------------------------------------------------------------------
# Configuration paths: recipe, dict list, precedence
# ---------------------------------------------------------------------------


def test_recipe_declares_the_key_and_the_encrypted_mount(tmp_path, key):
    """The grammar carries ``storage_key`` on ``mounts`` and ``encrypted`` on the mount."""

    def rec(root):
        m = root.mounts(storage_key=BagCbResolver(lambda: key))
        m.local(name="secure", base_path=str(tmp_path), encrypted=True)
        m.local(name="plain", base_path=str(tmp_path))

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert storage.encryption_active is True
    assert storage.mount_is_encrypted("secure") is True
    assert storage.mount_is_encrypted("plain") is False

    storage.node("secure:from_recipe.txt").write_text("recipe")
    assert storage.node("secure:from_recipe.txt").read_text() == "recipe"
    assert b"recipe" not in (tmp_path / "from_recipe.txt").read_bytes()


def test_recipe_without_storage_key_leaves_encryption_inactive(tmp_path):
    """No key declared, no cipher built: encryption stays opt-in."""

    def rec(root):
        root.mounts().local(name="home", base_path=str(tmp_path))

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert storage.encryption_active is False


def test_recipe_key_wins_over_the_configure_argument(tmp_path, key):
    """The recipe is the more specific source: its key is the one installed."""
    recipe_key = Fernet.generate_key().decode()

    def rec(root):
        m = root.mounts(storage_key=recipe_key)
        m.local(name="secure", base_path=str(tmp_path), encrypted=True)

    storage = StorageManager()
    storage.configure(_config_class(rec), storage_key=key)

    storage.node("secure:whose.txt").write_text("recipe key")
    assert Fernet(recipe_key).decrypt((tmp_path / "whose.txt").read_bytes()) == b"recipe key"


def test_reconfiguring_a_mount_without_encrypted_drops_the_flag(storage, tmp_path):
    """The flag follows the mount configuration; it is not sticky."""
    storage.add_mount({"name": "secure", "protocol": "local", "base_path": str(tmp_path)})

    assert storage.mount_is_encrypted("secure") is False


def test_deleting_a_mount_drops_the_flag(storage):
    """A deleted mount leaves no encrypted-name behind."""
    storage.delete_mount("secure")

    assert storage.mount_is_encrypted("secure") is False


def test_key_material_is_never_exposed(storage):
    """``encryption_active`` reports installation; nothing hands the keys back."""
    assert storage.encryption_active is True
    assert not [name for name in dir(storage) if "key" in name and name != "set_encryption_keys"]


# ---------------------------------------------------------------------------
# No silent degradation
# ---------------------------------------------------------------------------


def test_dormant_mount_raises_on_write(tmp_path):
    """Encrypted mount, no key installed: writing is a runtime error."""
    storage = StorageManager()
    storage.configure(
        [{"name": "secure", "protocol": "local", "base_path": str(tmp_path), "encrypted": True}]
    )

    assert storage.encryption_active is False
    with pytest.raises(StorageError, match="requires installed key material"):
        storage.node("secure:nope.txt").write_text("data")


def test_dormant_mount_raises_on_read(tmp_path, key):
    """Encrypted mount, no key installed: reading existing content is a runtime error."""
    written = StorageManager()
    written.configure(
        [{"name": "secure", "protocol": "local", "base_path": str(tmp_path), "encrypted": True}],
        storage_key=key,
    )
    written.node("secure:dormant.txt").write_text("data")

    dormant = StorageManager()
    dormant.configure(
        [{"name": "secure", "protocol": "local", "base_path": str(tmp_path), "encrypted": True}]
    )
    with pytest.raises(StorageError, match="requires installed key material"):
        dormant.node("secure:dormant.txt").read_text()


def test_empty_key_material_is_a_configuration_error(tmp_path):
    """A key that resolves empty is rejected at configuration time, not ignored."""
    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="at least one key is required"):
        storage.configure(
            [{"name": "secure", "protocol": "local", "base_path": str(tmp_path)}],
            storage_key="   ",
        )


def test_empty_key_material_from_a_recipe_is_a_configuration_error(tmp_path):
    """Same verdict when the empty value arrives from a resolver."""

    def rec(root):
        m = root.mounts(storage_key=BagCbResolver(lambda: ""))
        m.local(name="secure", base_path=str(tmp_path), encrypted=True)

    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="at least one key is required"):
        storage.configure(_config_class(rec))


def test_plaintext_payload_on_an_encrypted_mount_raises(storage, tmp_path):
    """Content no installed key can decrypt is an error, never a plaintext fallback."""
    (tmp_path / "smuggled.txt").write_bytes(b"not a fernet token")

    with pytest.raises(InvalidToken):
        storage.node("secure:smuggled.txt").read_text()


def test_encrypted_mount_without_the_package_is_a_configuration_error(tmp_path, monkeypatch):
    """Declaring an encrypted mount with no ``cryptography`` installed fails loudly."""
    monkeypatch.setattr(manager_module, "HAS_CRYPTOGRAPHY", False)
    storage = StorageManager()

    with pytest.raises(StorageConfigError, match="cryptography"):
        storage.configure(
            [
                {
                    "name": "secure",
                    "protocol": "local",
                    "base_path": str(tmp_path),
                    "encrypted": True,
                }
            ]
        )


def test_installing_keys_without_the_package_is_a_configuration_error(monkeypatch):
    """The same verdict when the key material arrives first."""
    monkeypatch.setattr(manager_module, "HAS_CRYPTOGRAPHY", False)
    storage = StorageManager()

    with pytest.raises(StorageConfigError, match="cryptography"):
        storage.set_encryption_keys(Fernet.generate_key().decode())


def test_a_plain_mount_needs_nothing_from_the_package(tmp_path, monkeypatch):
    """Encryption is opt-in: with no encrypted mount the package is never required."""
    monkeypatch.setattr(manager_module, "HAS_CRYPTOGRAPHY", False)
    storage = StorageManager()
    storage.configure([{"name": "home", "protocol": "local", "base_path": str(tmp_path)}])
    storage.node("home:ok.txt").write_text("fine")

    assert storage.node("home:ok.txt").read_text() == "fine"
