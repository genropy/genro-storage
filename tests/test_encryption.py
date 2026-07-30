# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for at-rest encryption.

Encryption is per file and declared at the write site: ``encrypted=True`` for
the default domain, ``encrypted='<domain>'`` for an explicit one, nothing at
all for plain content. What lands on the medium is self-describing — an
envelope whose first line is ``#GNRE1:<domain>``, then the Fernet token — so
the tests assert both halves of the claim at once: the value comes back
unchanged AND the bytes on disk are an envelope, not the value.

Reads declare nothing, which is what lets encrypted and plain files share a
directory: a header means decrypt through that domain's keyring, no header
means passthrough. Key material is one or more comma-separated Fernet keys,
each optionally ``<domain>:`` prefixed; keys of one domain form a single
``MultiFernet`` (the FIRST key encrypts, ALL decrypt), so rotation is asserted
by writing with one key set and reading with another that merely still contains
the old key.

The contract has no silent degradation, and each of its edges gets a test:
encrypting or decrypting for a domain with no installed key is a runtime error
naming the domain, key material that resolves empty is a configuration error, an
invalid domain is a configuration error, and declaring a ``default_encrypted``
mount without the ``cryptography`` package installed is a configuration error
too. A mount may carry ``default_encrypted`` as the default of that write
parameter — overridable at every write site in both directions — and a relative
mount inherits its parent's.
That last one is exercised by faking the package away — it IS installed here,
since the whole suite needs it. Content with no header is never sniffed: it
passes through untouched.
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
    """A manager with key material installed and two local mounts.

    Nothing about the mounts is encrypted: the write site decides, so ``files``
    and ``other`` differ only by the directory they point at.
    """
    (tmp_path / "other").mkdir()
    storage = StorageManager()
    storage.configure(
        [
            {"name": "files", "protocol": "local", "base_path": str(tmp_path)},
            {"name": "other", "protocol": "local", "base_path": str(tmp_path / "other")},
        ],
        storage_key=key,
    )
    return storage


def _config_class(main):
    """A throwaway ``StorageConfig`` subclass with an injected ``main``."""
    return type("_TestConfig", (StorageConfig,), {"main": lambda self, root: main(root)})


def _token(data):
    """The Fernet token of an envelope, i.e. everything past the header line."""
    return data.split(b"\n", 1)[1]


# ---------------------------------------------------------------------------
# The envelope: build, parse, bounds
# ---------------------------------------------------------------------------


def test_envelope_roundtrip_through_the_manager(storage):
    """``encrypt`` emits the envelope, ``decrypt`` reads it back."""
    enveloped = storage.encrypt(b"payload")

    assert enveloped.startswith(b"#GNRE1:\n")
    assert storage.decrypt(enveloped) == b"payload"


def test_build_and_parse_are_inverse(storage):
    """The header carries the domain verbatim, the payload comes back untouched."""
    built = storage._build_envelope("acmespa", b"TOKEN")

    assert built == b"#GNRE1:acmespa\nTOKEN"
    assert storage._parse_envelope(built) == ("acmespa", b"TOKEN")


def test_empty_domain_renders_a_bare_header(storage):
    """The default domain is the empty string, and it still gets a header."""
    assert storage._build_envelope("", b"TOKEN") == b"#GNRE1:\nTOKEN"
    assert storage._parse_envelope(b"#GNRE1:\nTOKEN") == ("", b"TOKEN")


@pytest.mark.parametrize(
    "data",
    [
        b"plain content",
        b"#GNRE1 no colon\ntoken",
        b"#GNRE1:UPPER\ntoken",  # domain outside the charset: not a header
        b"#GNRE1:nonewline",
        b"#GNRE1:" + b"x" * 200 + b"\ntoken",  # first line past the 128-byte bound
    ],
)
def test_content_without_a_valid_header_parses_as_unenveloped(storage, data):
    """Anything that is not exactly the envelope is passthrough, byte for byte."""
    assert storage._parse_envelope(data) == (None, data)
    assert storage.decrypt(data) == data


# ---------------------------------------------------------------------------
# Domain-aware key material
# ---------------------------------------------------------------------------


def test_unprefixed_keys_land_in_the_default_domain(storage):
    """Today's syntax keeps working: no prefix means the empty domain."""
    assert storage.encryption_domains == [""]
    assert storage.encrypt(b"x").startswith(b"#GNRE1:\n")


def test_prefixed_keys_group_one_cipher_per_domain():
    """Each domain gets its own keyring, in declaration order."""
    keys = [Fernet.generate_key().decode() for _ in range(3)]
    storage = StorageManager()
    storage.set_encryption_keys(f"acmespa:{keys[0]},acmespa:{keys[1]},partner:{keys[2]}")

    assert storage.encryption_domains == ["acmespa", "partner"]
    assert Fernet(keys[0]).decrypt(_token(storage.encrypt(b"a", domain="acmespa"))) == b"a"
    assert Fernet(keys[2]).decrypt(_token(storage.encrypt(b"p", domain="partner"))) == b"p"


def test_the_first_configured_key_sets_the_default_domain():
    """An unqualified encryption uses the domain of the first key overall."""
    storage = StorageManager()
    storage.set_encryption_keys(
        f"partner:{Fernet.generate_key().decode()},acmespa:{Fernet.generate_key().decode()}"
    )

    assert storage.encrypt(b"x").startswith(b"#GNRE1:partner\n")


def test_rotation_is_per_domain():
    """Within a domain the first key encrypts and all of them decrypt."""
    old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    storage = StorageManager()
    storage.set_encryption_keys(f"acmespa:{old}")
    written = storage.encrypt(b"before rotation", domain="acmespa")

    storage.set_encryption_keys(f"acmespa:{new},acmespa:{old}")

    assert storage.decrypt(written) == b"before rotation"
    assert Fernet(new).decrypt(_token(storage.encrypt(b"after", domain="acmespa"))) == b"after"


def test_a_domain_with_no_keys_raises_naming_it(storage):
    """The error names the domain — encrypting and decrypting alike."""
    with pytest.raises(StorageError, match="'partner'"):
        storage.encrypt(b"x", domain="partner")
    with pytest.raises(StorageError, match="'partner'"):
        storage.decrypt(b"#GNRE1:partner\nTOKEN")


@pytest.mark.parametrize("domain", ["ACME", "acme spa", "acme.spa", "x" * 65])
def test_an_invalid_domain_is_a_configuration_error(storage, domain):
    """The charset is checked on the key material and on the write parameter."""
    with pytest.raises(StorageConfigError, match="Invalid encryption domain"):
        storage.encrypt(b"x", domain=domain)
    with pytest.raises(StorageConfigError, match="Invalid encryption domain"):
        storage.set_encryption_keys(f"{domain}:{Fernet.generate_key().decode()}")


# ---------------------------------------------------------------------------
# Per-node writes: plaintext to the caller, an envelope on the medium
# ---------------------------------------------------------------------------


def test_text_roundtrip_leaves_no_plaintext_on_disk(storage, tmp_path):
    """``write_text(encrypted=True)`` is transparent; the file is not the text."""
    node = storage.node("files:secret.txt")
    node.write_text("attack at dawn", encrypted=True)

    assert node.read_text() == "attack at dawn"
    on_disk = (tmp_path / "secret.txt").read_bytes()
    assert b"attack at dawn" not in on_disk
    assert on_disk.startswith(b"#GNRE1:\n")  # default domain, then the token
    assert _token(on_disk).startswith(b"gAAAAA")  # Fernet token prefix


def test_bytes_roundtrip_leaves_no_plaintext_on_disk(storage, tmp_path):
    """``write_bytes``/``read_bytes`` are transparent on the same terms."""
    node = storage.node("files:secret.bin")
    node.write_bytes(b"\x00\x01payload\x02", encrypted=True)

    assert node.read_bytes() == b"\x00\x01payload\x02"
    assert b"payload" not in (tmp_path / "secret.bin").read_bytes()


def test_read_write_generic_forms_are_transparent_too(storage, tmp_path):
    """``read()``/``write()`` route through the same layer as the convenience pair."""
    node = storage.node("files:generic.txt")
    node.write("hello", mode="w", encrypted=True)

    assert node.read() == "hello"
    assert node.read(mode="rb") == b"hello"
    assert (tmp_path / "generic.txt").read_bytes().startswith(b"#GNRE1:\n")


def test_binary_generic_write_takes_the_parameter_too(storage, tmp_path):
    """``write(mode='wb', encrypted=...)`` forwards to the same write path."""
    storage.node("files:generic.bin").write(b"\x00raw", mode="wb", encrypted=True)

    assert storage.node("files:generic.bin").read(mode="rb") == b"\x00raw"
    assert (tmp_path / "generic.bin").read_bytes().startswith(b"#GNRE1:\n")


def test_an_explicit_domain_writes_through_that_keyring(tmp_path):
    """``encrypted='<domain>'`` picks the domain, whatever the default one is."""
    default_key, acme_key = Fernet.generate_key().decode(), Fernet.generate_key().decode()
    storage = StorageManager()
    storage.configure(
        [{"name": "files", "protocol": "local", "base_path": str(tmp_path)}],
        storage_key=f"{default_key},acmespa:{acme_key}",
    )
    storage.node("files:tenant.txt").write_text("tenant data", encrypted="acmespa")

    on_disk = (tmp_path / "tenant.txt").read_bytes()
    assert on_disk.startswith(b"#GNRE1:acmespa\n")
    assert Fernet(acme_key).decrypt(_token(on_disk)) == b"tenant data"
    assert storage.node("files:tenant.txt").read_text() == "tenant data"


def test_a_write_without_the_parameter_stays_plain(storage, tmp_path):
    """Encryption is declared, never inherited: the default write is plaintext."""
    storage.node("files:visible.txt").write_text("in the clear")

    assert (tmp_path / "visible.txt").read_bytes() == b"in the clear"


def test_encrypted_and_plain_files_coexist_in_one_directory(storage, tmp_path):
    """The header travels with the file, so the same directory holds both."""
    storage.node("files:mixed_secret.txt").write_text("hidden", encrypted=True)
    storage.node("files:mixed_public.txt").write_text("shown")

    assert storage.node("files:mixed_secret.txt").read_text() == "hidden"
    assert storage.node("files:mixed_public.txt").read_text() == "shown"
    assert (tmp_path / "mixed_secret.txt").read_bytes().startswith(b"#GNRE1:\n")
    assert (tmp_path / "mixed_public.txt").read_bytes() == b"shown"


def test_an_explicit_false_writes_plain_over_encrypted_content(storage, tmp_path):
    """The parameter decides every write: rewriting plain leaves no envelope behind."""
    node = storage.node("files:downgraded.txt")
    node.write_text("secret", encrypted=True)
    node.write_text("public")

    assert (tmp_path / "downgraded.txt").read_bytes() == b"public"
    assert node.read_text() == "public"


def test_ciphertext_differs_between_writes_of_the_same_content(storage, tmp_path):
    """Fernet is non-deterministic: identical plaintext, different bytes at rest."""
    node = storage.node("files:a.txt")
    node.write_text("same", encrypted=True)
    first = (tmp_path / "a.txt").read_bytes()
    node.write_text("same", encrypted=True)
    second = (tmp_path / "a.txt").read_bytes()

    assert first != second
    assert node.read_text() == "same"


def test_skip_if_unchanged_compares_plaintext(storage):
    """The skip check sees decrypted content, so re-writing the same text skips."""
    node = storage.node("files:skip.txt")

    assert node.write_text("stable", skip_if_unchanged=True, encrypted=True) is True
    assert node.write_text("stable", skip_if_unchanged=True, encrypted=True) is False
    assert node.write_text("changed", skip_if_unchanged=True, encrypted=True) is True


# ---------------------------------------------------------------------------
# Copy and move: the envelope travels verbatim
# ---------------------------------------------------------------------------


def test_copy_to_a_plain_mount_keeps_the_file_readable(storage, tmp_path):
    """The 0.7.x encrypted → plain case: the copy is an envelope, and it reads back."""
    storage.node("files:travelling.txt").write_text("carried across", encrypted=True)
    storage.node("files:travelling.txt").copy_to("other:travelling.txt")

    copied = (tmp_path / "other" / "travelling.txt").read_bytes()
    assert copied.startswith(b"#GNRE1:\n")  # identifiable wherever it lands
    assert b"carried across" not in copied
    assert storage.node("other:travelling.txt").read_text() == "carried across"


def test_copy_of_plain_content_reads_back_in_passthrough(storage, tmp_path):
    """The 0.7.x plain → encrypted-mount case: no header, so nothing to decrypt."""
    storage.node("files:public.txt").write_text("nothing to hide")
    storage.node("files:public.txt").copy_to("other:public.txt")

    assert (tmp_path / "other" / "public.txt").read_bytes() == b"nothing to hide"
    assert storage.node("other:public.txt").read_text() == "nothing to hide"


# ---------------------------------------------------------------------------
# Relative mounts: the stored bytes are the parent's, envelope included
# ---------------------------------------------------------------------------


@pytest.fixture
def storage_with_child(tmp_path, key):
    """A local mount plus a relative mount inside it."""
    storage = StorageManager()
    storage.configure(
        [
            {"name": "files", "protocol": "local", "base_path": str(tmp_path)},
            {"name": "child", "path": "files:inner"},
        ],
        storage_key=key,
    )
    return storage


def test_read_through_the_child_sees_plaintext(storage_with_child, tmp_path):
    """Bytes written by the parent read back as plaintext through the child."""
    storage_with_child.node("files:inner/f.txt").write_text("SECRET-MARKER", encrypted=True)

    assert storage_with_child.node("child:f.txt").read_text() == "SECRET-MARKER"
    on_disk = (tmp_path / "inner" / "f.txt").read_bytes()
    assert b"SECRET-MARKER" not in on_disk


def test_write_through_the_child_lands_ciphertext(storage_with_child, tmp_path):
    """Bytes written through the child are an envelope the parent can read."""
    storage_with_child.node("child:g.txt").write_text("WRITTEN-VIA-CHILD", encrypted=True)

    assert storage_with_child.node("files:inner/g.txt").read_text() == "WRITTEN-VIA-CHILD"
    on_disk = (tmp_path / "inner" / "g.txt").read_bytes()
    assert b"WRITTEN-VIA-CHILD" not in on_disk
    assert on_disk.startswith(b"#GNRE1:\n")


# ---------------------------------------------------------------------------
# The mount default: default_encrypted
# ---------------------------------------------------------------------------


@pytest.fixture
def storage_with_default(tmp_path, key):
    """Two local mounts sharing the key material, one defaulting to encrypted writes."""
    (tmp_path / "vault").mkdir()
    storage = StorageManager()
    storage.configure(
        [
            {"name": "files", "protocol": "local", "base_path": str(tmp_path)},
            {
                "name": "vault",
                "protocol": "local",
                "base_path": str(tmp_path / "vault"),
                "default_encrypted": True,
            },
        ],
        storage_key=key,
    )
    return storage


def test_an_undeclared_write_takes_the_mount_default(storage_with_default, tmp_path):
    """No ``encrypted=`` at the write site: the mount's default decides."""
    storage_with_default.node("vault:a.txt").write_text("kept")

    on_disk = (tmp_path / "vault" / "a.txt").read_bytes()
    assert on_disk.startswith(b"#GNRE1:\n")
    assert b"kept" not in on_disk
    assert storage_with_default.node("vault:a.txt").read_text() == "kept"


def test_the_mount_default_also_covers_bytes_and_the_generic_write(storage_with_default, tmp_path):
    """Every write path resolves the same default, not just ``write_text``."""
    storage_with_default.node("vault:b.bin").write_bytes(b"\x00raw")
    storage_with_default.node("vault:c.txt").write("generic")

    assert (tmp_path / "vault" / "b.bin").read_bytes().startswith(b"#GNRE1:\n")
    assert (tmp_path / "vault" / "c.txt").read_bytes().startswith(b"#GNRE1:\n")
    assert storage_with_default.node("vault:b.bin").read_bytes() == b"\x00raw"


def test_an_explicit_false_overrides_the_mount_default(storage_with_default, tmp_path):
    """The write site wins in BOTH directions: plain on a default_encrypted mount."""
    storage_with_default.node("vault:plain.txt").write_text("in the clear", encrypted=False)

    assert (tmp_path / "vault" / "plain.txt").read_bytes() == b"in the clear"
    assert storage_with_default.node("vault:plain.txt").read_text() == "in the clear"


def test_a_mount_without_the_default_stays_plain(storage_with_default, tmp_path):
    """The default belongs to its mount alone; the sibling is untouched."""
    storage_with_default.node("files:open.txt").write_text("nothing to hide")

    assert (tmp_path / "open.txt").read_bytes() == b"nothing to hide"


def test_a_string_default_names_the_domain(tmp_path):
    """``default_encrypted='<domain>'`` defaults the writes to that domain."""
    domain_key = Fernet.generate_key().decode()
    storage = StorageManager()
    storage.configure(
        [
            {
                "name": "files",
                "protocol": "local",
                "base_path": str(tmp_path),
                "default_encrypted": "acmespa",
            }
        ],
        storage_key=f"acmespa:{domain_key}",
    )
    storage.node("files:tenant.txt").write_text("tenant data")

    on_disk = (tmp_path / "tenant.txt").read_bytes()
    assert on_disk.startswith(b"#GNRE1:acmespa\n")
    assert Fernet(domain_key).decrypt(_token(on_disk)) == b"tenant data"


def test_an_explicit_domain_overrides_a_string_default(tmp_path):
    """A named domain at the write site beats the mount's named default."""
    keys = [Fernet.generate_key().decode() for _ in range(2)]
    storage = StorageManager()
    storage.configure(
        [
            {
                "name": "files",
                "protocol": "local",
                "base_path": str(tmp_path),
                "default_encrypted": "acmespa",
            }
        ],
        storage_key=f"acmespa:{keys[0]},partner:{keys[1]}",
    )
    storage.node("files:other.txt").write_text("partner data", encrypted="partner")

    assert (tmp_path / "other.txt").read_bytes().startswith(b"#GNRE1:partner\n")


def test_the_manager_reports_the_mount_default(storage_with_default):
    """The mount holds a default, and that is exactly what the manager reports."""
    assert storage_with_default.mount_default_encrypted("vault") is True
    assert storage_with_default.mount_default_encrypted("files") is False
    assert storage_with_default.mount_default_encrypted("unknown") is False


def test_reconfiguring_a_mount_replaces_its_default(storage_with_default, tmp_path):
    """The default is not sticky: reconfiguring without it goes back to plain."""
    storage_with_default.add_mount(
        {"name": "vault", "protocol": "local", "base_path": str(tmp_path / "vault")}
    )

    assert storage_with_default.mount_default_encrypted("vault") is False
    storage_with_default.node("vault:after.txt").write_text("plain again")
    assert (tmp_path / "vault" / "after.txt").read_bytes() == b"plain again"


def test_deleting_a_mount_forgets_its_default(storage_with_default):
    """Nothing survives the mount it belonged to."""
    storage_with_default.delete_mount("vault")

    assert storage_with_default.mount_default_encrypted("vault") is False


def test_a_relative_mount_does_not_inherit_the_parent_default(tmp_path, key):
    """The default belongs to the mount named in the write, and to it alone."""
    storage = StorageManager()
    storage.configure(
        [
            {
                "name": "vault",
                "protocol": "local",
                "base_path": str(tmp_path),
                "default_encrypted": True,
            },
            {"name": "child", "path": "vault:inner"},
        ],
        storage_key=key,
    )

    assert storage.mount_default_encrypted("child") is False
    storage.node("child:f.txt").write_text("plain via the child")
    assert (tmp_path / "inner" / "f.txt").read_bytes() == b"plain via the child"
    # The same directory through the parent still defaults to encrypted, and
    # the mixed content reads fine either way: the header answers per file.
    storage.node("vault:inner/g.txt").write_text("enveloped via the parent")
    assert (tmp_path / "inner" / "g.txt").read_bytes().startswith(b"#GNRE1:\n")
    assert storage.node("child:g.txt").read_text() == "enveloped via the parent"


def test_a_relative_mount_may_declare_its_own_default(tmp_path, key):
    """A relative mount encrypts by default only if IT declares so."""
    storage = StorageManager()
    storage.configure(
        [
            {"name": "files", "protocol": "local", "base_path": str(tmp_path)},
            {"name": "inbox", "path": "files:inbox", "default_encrypted": "acmespa"},
        ],
        storage_key=f"acmespa:{key}",
    )

    assert storage.mount_default_encrypted("inbox") == "acmespa"
    storage.node("inbox:f.txt").write_text("own default")
    assert (tmp_path / "inbox" / "f.txt").read_bytes().startswith(b"#GNRE1:acmespa\n")


def test_the_recipe_declares_the_mount_default(tmp_path, key):
    """The grammar carries ``default_encrypted`` on ``local``."""

    def rec(root):
        root.mounts(storage_key=BagCbResolver(lambda: key)).local(
            name="vault", base_path=str(tmp_path), default_encrypted=True
        )

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert storage.mount_default_encrypted("vault") is True
    storage.node("vault:recipe.txt").write_text("from the recipe")
    assert (tmp_path / "recipe.txt").read_bytes().startswith(b"#GNRE1:\n")


def test_every_protocol_element_accepts_default_encrypted(key):
    """The grammar mirrors the dict path: the option exists on every mount element.

    The envelope sits above the backend, so ``default_encrypted`` is
    protocol-independent — a closed signature rejecting it on one element
    would make the grammar diverge from an equivalent dict/YAML entry.
    """

    def rec(root):
        m = root.mounts(storage_key=BagCbResolver(lambda: key))
        m.memory(name="cache", default_encrypted=True)
        m.s3(name="uploads", bucket="b", default_encrypted="acmespa")
        m.http(name="cdn", base_path="https://cdn.example.com", default_encrypted=False)

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert storage.mount_default_encrypted("cache") is True
    assert storage.mount_default_encrypted("uploads") == "acmespa"
    assert storage.mount_default_encrypted("cdn") is False
    storage.node("cache:x.bin").write_bytes(b"payload")
    assert storage.node("cache:x.bin").read_bytes() == b"payload"


def test_an_invalid_default_domain_is_a_configuration_error(tmp_path, key):
    """The charset is checked where the mount is declared, not at the first write."""
    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="Invalid encryption domain"):
        storage.configure(
            [
                {
                    "name": "files",
                    "protocol": "local",
                    "base_path": str(tmp_path),
                    "default_encrypted": "ACME",
                }
            ],
            storage_key=key,
        )


def test_a_default_encrypted_mount_with_no_key_fails_at_the_write(tmp_path):
    """Dormancy is per write: configuration succeeds, the write is the error."""
    storage = StorageManager()
    storage.configure(
        [
            {
                "name": "vault",
                "protocol": "local",
                "base_path": str(tmp_path),
                "default_encrypted": True,
            }
        ]
    )

    assert storage.mount_default_encrypted("vault") is True
    with pytest.raises(StorageError, match="requires installed key material"):
        storage.node("vault:nope.txt").write_text("data")


# ---------------------------------------------------------------------------
# Key rotation: the first key encrypts, all keys decrypt
# ---------------------------------------------------------------------------


def test_rotation_reads_with_the_old_key_and_writes_with_the_new(storage, tmp_path, key):
    """After rotation the old content still reads; new content uses the new key."""
    storage.node("files:rotated.txt").write_text("written with the old key", encrypted=True)

    new_key = Fernet.generate_key().decode()
    storage.set_encryption_keys(f"{new_key},{key}")

    node = storage.node("files:rotated.txt")
    assert node.read_text() == "written with the old key"

    node.write_text("written with the new key", encrypted=True)
    # The new key alone suffices for what was just written; the old one does not.
    token = _token((tmp_path / "rotated.txt").read_bytes())
    assert Fernet(new_key).decrypt(token) == b"written with the new key"
    with pytest.raises(InvalidToken):
        Fernet(key).decrypt(token)


def test_a_key_no_longer_installed_cannot_read_its_content(storage):
    """Dropping a key from the material is what makes its content unreadable."""
    storage.node("files:orphan.txt").write_text("only the old key knows", encrypted=True)
    storage.set_encryption_keys(Fernet.generate_key().decode())

    with pytest.raises(InvalidToken):
        storage.node("files:orphan.txt").read_text()


def test_keys_are_whitespace_tolerant(tmp_path, key):
    """A comma-separated list may be spaced out; the keys are stripped."""
    storage = StorageManager()
    storage.configure(
        [{"name": "files", "protocol": "local", "base_path": str(tmp_path)}],
        storage_key=f"  {key} , {Fernet.generate_key().decode()}  ",
    )
    storage.node("files:spaced.txt").write_text("fine", encrypted=True)

    assert storage.node("files:spaced.txt").read_text() == "fine"


# ---------------------------------------------------------------------------
# Configuration paths: recipe, dict list, precedence
# ---------------------------------------------------------------------------


def test_recipe_declares_the_key(tmp_path, key):
    """The grammar carries ``storage_key`` on ``mounts``; the write site does the rest."""

    def rec(root):
        root.mounts(storage_key=BagCbResolver(lambda: key)).local(
            name="files", base_path=str(tmp_path)
        )

    storage = StorageManager()
    storage.configure(_config_class(rec))

    assert storage.encryption_active is True

    storage.node("files:from_recipe.txt").write_text("recipe", encrypted=True)
    assert storage.node("files:from_recipe.txt").read_text() == "recipe"
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
        root.mounts(storage_key=recipe_key).local(name="files", base_path=str(tmp_path))

    storage = StorageManager()
    storage.configure(_config_class(rec), storage_key=key)

    storage.node("files:whose.txt").write_text("recipe key", encrypted=True)
    assert (
        Fernet(recipe_key).decrypt(_token((tmp_path / "whose.txt").read_bytes())) == b"recipe key"
    )


def test_key_material_is_never_exposed(storage):
    """``encryption_active`` reports installation; nothing hands the keys back."""
    assert storage.encryption_active is True
    assert not [name for name in dir(storage) if "key" in name and name != "set_encryption_keys"]


# ---------------------------------------------------------------------------
# No silent degradation
# ---------------------------------------------------------------------------


def test_an_encrypted_write_with_no_key_installed_raises(tmp_path):
    """The parameter is honoured or it fails: never a silent plaintext write."""
    storage = StorageManager()
    storage.configure([{"name": "files", "protocol": "local", "base_path": str(tmp_path)}])

    assert storage.encryption_active is False
    with pytest.raises(StorageError, match="requires installed key material"):
        storage.node("files:nope.txt").write_text("data", encrypted=True)


def test_reading_an_envelope_with_no_key_installed_raises(tmp_path, key):
    """The header names a domain that is not installed: a runtime error, loudly."""
    written = StorageManager()
    written.configure(
        [{"name": "files", "protocol": "local", "base_path": str(tmp_path)}], storage_key=key
    )
    written.node("files:dormant.txt").write_text("data", encrypted=True)

    dormant = StorageManager()
    dormant.configure([{"name": "files", "protocol": "local", "base_path": str(tmp_path)}])
    with pytest.raises(StorageError, match="requires installed key material"):
        dormant.node("files:dormant.txt").read_text()


def test_writing_to_an_unknown_domain_raises_naming_it(storage):
    """A domain with no keys is dormant, and using it at the write site says so."""
    with pytest.raises(StorageError, match="'partner'"):
        storage.node("files:tenant.txt").write_text("data", encrypted="partner")


def test_empty_key_material_is_a_configuration_error(tmp_path):
    """A key that resolves empty is rejected at configuration time, not ignored."""
    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="at least one key is required"):
        storage.configure(
            [{"name": "files", "protocol": "local", "base_path": str(tmp_path)}],
            storage_key="   ",
        )


def test_empty_key_material_from_a_recipe_is_a_configuration_error(tmp_path):
    """Same verdict when the empty value arrives from a resolver."""

    def rec(root):
        root.mounts(storage_key=BagCbResolver(lambda: "")).local(
            name="files", base_path=str(tmp_path)
        )

    storage = StorageManager()
    with pytest.raises(StorageConfigError, match="at least one key is required"):
        storage.configure(_config_class(rec))


def test_unenveloped_content_passes_through(storage, tmp_path):
    """No header, no decryption: the read is deterministic, never content sniffing."""
    (tmp_path / "smuggled.txt").write_bytes(b"not a fernet token")

    assert storage.node("files:smuggled.txt").read_text() == "not a fernet token"


def test_enveloped_content_no_key_can_decrypt_raises(storage, tmp_path):
    """A header the keys cannot honour is an error, never a plaintext fallback."""
    (tmp_path / "broken.txt").write_bytes(b"#GNRE1:\nnot a fernet token")

    with pytest.raises(InvalidToken):
        storage.node("files:broken.txt").read_text()


def test_default_encrypted_mount_without_the_package_is_a_configuration_error(
    tmp_path, monkeypatch
):
    """Declaring ``default_encrypted`` with no ``cryptography`` installed fails loudly."""
    monkeypatch.setattr(manager_module, "HAS_CRYPTOGRAPHY", False)
    storage = StorageManager()

    with pytest.raises(StorageConfigError, match="cryptography"):
        storage.configure(
            [
                {
                    "name": "files",
                    "protocol": "local",
                    "base_path": str(tmp_path),
                    "default_encrypted": True,
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
    """Encryption is opt-in: with no encrypted write the package is never required."""
    monkeypatch.setattr(manager_module, "HAS_CRYPTOGRAPHY", False)
    storage = StorageManager()
    storage.configure([{"name": "home", "protocol": "local", "base_path": str(tmp_path)}])
    storage.node("home:ok.txt").write_text("fine")

    assert storage.node("home:ok.txt").read_text() == "fine"
