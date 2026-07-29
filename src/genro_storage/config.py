# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pythonic storage configuration grammar.

A ``genro-builders`` grammar that describes a storage configuration as a set
of typed, self-documenting method calls instead of a dict/YAML blob. One
``@element`` per protocol: the tag IS the protocol, so there is no ``protocol``
field anywhere — the adapter reads ``node.node_tag``. Each element documents
the mount from its own signature; required fields are the parameters without a
default, validated by the signature machinery (a missing one raises
``ValueError: Validation failed: required attribute ...``). ``permissions`` is a
``Literal`` so an invalid value is rejected by the same signature check.

The required fields mirror exactly those that ``manager.py:_configure_mount``
raises ``StorageConfigError`` on today; legacy aliases (``path``/``prefix``/
``base_url``/``key``/``secret``) are deliberately dropped — one name per field is
the point of the change.

Every mount lives inside the ``mounts`` collection, keyed by ``name``: two
mounts sharing a name raise ``duplicate collection key``. String fields already
accept a ``^pointer`` value (a pointer is a string); fields that must stay
pointer-able but are NOT strings (``port``, ``timeout``, ``anon``,
``verify_ssl``) are typed wide (``int | str | None`` etc.) so the pointer string
survives the signature type check — see the plan Notes for the upstream micro-fix
that will let these tighten.

Example::

    class MyConfig(StorageConfig):
        def main(self, root):
            m = root.mounts()
            m.local(name="home", base_path="/srv/data")
            m.s3(name="uploads", bucket="my-bucket", endpoint_url="^env.s3_url")
            m.relative(name="public", path="home:public", permissions="readonly")
"""

from __future__ import annotations

from typing import Callable, Literal

from genro_builders.builder import BuilderBase, element

#: Permission level accepted by every mount element. Declared once, reused
#: everywhere; the ``Literal`` in the signature IS the validation — never
#: re-checked in Python.
Permissions = Literal["readonly", "readwrite", "delete"]

#: Every protocol tag plus ``relative``, in the order they are declared below.
#: Used as the ``mounts`` container ``sub_tags`` so only these tags are valid
#: children.
_MOUNT_TAGS = (
    "local,memory,s3,gcs,azure,http,smb,sftp,"
    "zip,tar,git,github,webdav,libarchive,base64,relative"
)


class StorageConfig(BuilderBase):
    """Data-only grammar for a storage configuration.

    Subclass it and populate ``mounts`` in ``main`` (or seed pointer data in
    ``setup``); ``page.create()`` builds and resolves it.
    No renderer or compiler: the configuration is consumed by the adapter, not
    rendered.
    """

    _name = "storage_config"

    @element(sub_tags=_MOUNT_TAGS, collection_key="name", node_label="mounts")
    def mounts(self):
        """Collection of named mount points; each child is keyed by its ``name``."""

    # -- local / in-process ----------------------------------------------
    @element(parent_tags="mounts")
    def local(
        self,
        *,
        name: str,
        base_path: str | Callable,
        base_url: str | None = None,
        permissions: Permissions | None = None,
    ):
        """Local filesystem mount; ``base_path`` may be a callable resolved at runtime."""

    @element(parent_tags="mounts")
    def memory(
        self,
        *,
        name: str,
        base_path: str | None = None,
        permissions: Permissions | None = None,
    ):
        """In-memory filesystem, for tests and ephemeral scratch space."""

    @element(parent_tags="mounts")
    def base64(
        self,
        *,
        name: str,
        permissions: Permissions | None = None,
    ):
        """Inline base64 data mount with writable paths; no configuration."""

    # -- cloud object stores ---------------------------------------------
    @element(parent_tags="mounts")
    def s3(
        self,
        *,
        name: str,
        bucket: str,
        base_path: str | None = None,
        region: str | None = None,
        anon: bool | str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        endpoint_url: str | None = None,
        permissions: Permissions | None = None,
    ):
        """S3 or S3-compatible bucket; MinIO and friends via ``endpoint_url``."""

    @element(parent_tags="mounts")
    def gcs(
        self,
        *,
        name: str,
        bucket: str,
        base_path: str | None = None,
        token: str | None = None,
        project: str | None = None,
        endpoint_url: str | None = None,
        permissions: Permissions | None = None,
    ):
        """Google Cloud Storage bucket."""

    @element(parent_tags="mounts")
    def azure(
        self,
        *,
        name: str,
        container: str,
        account_name: str,
        account_key: str | None = None,
        sas_token: str | None = None,
        connection_string: str | None = None,
        permissions: Permissions | None = None,
    ):
        """Azure Blob Storage container; ``account_name`` identifies the account."""

    # -- remote protocols ------------------------------------------------
    @element(parent_tags="mounts")
    def http(
        self,
        *,
        name: str,
        base_path: str,
        permissions: Permissions | None = None,
    ):
        """Read-only HTTP(S) tree rooted at ``base_path``."""

    @element(parent_tags="mounts")
    def smb(
        self,
        *,
        name: str,
        host: str,
        share: str,
        base_path: str | None = None,
        username: str | None = None,
        password: str | None = None,
        domain: str | None = None,
        port: int | str | None = None,
        permissions: Permissions | None = None,
    ):
        """SMB/CIFS network share on ``host``."""

    @element(parent_tags="mounts")
    def sftp(
        self,
        *,
        name: str,
        host: str,
        username: str,
        base_path: str | None = None,
        password: str | None = None,
        port: int | str | None = None,
        key_filename: str | None = None,
        passphrase: str | None = None,
        timeout: int | str | None = None,
        permissions: Permissions | None = None,
    ):
        """SFTP server accessed over SSH on ``host``."""

    @element(parent_tags="mounts")
    def webdav(
        self,
        *,
        name: str,
        url: str,
        username: str | None = None,
        password: str | None = None,
        token: str | None = None,
        cert: str | None = None,
        verify_ssl: bool | str | None = None,
        permissions: Permissions | None = None,
    ):
        """WebDAV server (Nextcloud, ownCloud, SharePoint) at ``url``."""

    # -- archives --------------------------------------------------------
    @element(parent_tags="mounts")
    def zip(
        self,
        *,
        name: str,
        file: str,
        mode: str | None = None,
        target_protocol: str | None = None,
        target_options: dict | None = None,
        permissions: Permissions | None = None,
    ):
        """ZIP archive addressed as a filesystem; ``file`` is the archive path."""

    @element(parent_tags="mounts")
    def tar(
        self,
        *,
        name: str,
        file: str,
        compression: str | None = None,
        target_protocol: str | None = None,
        target_options: dict | None = None,
        permissions: Permissions | None = None,
    ):
        """TAR archive addressed as a filesystem; ``file`` is the archive path."""

    @element(parent_tags="mounts")
    def libarchive(
        self,
        *,
        name: str,
        file: str,
        target_protocol: str | None = None,
        target_options: dict | None = None,
        permissions: Permissions | None = None,
    ):
        """Universal archive (7z, rar, iso, ...) via libarchive; ``file`` is the path."""

    # -- version control -------------------------------------------------
    @element(parent_tags="mounts")
    def git(
        self,
        *,
        name: str,
        base_path: str,
        ref: str | None = None,
        fo: str | None = None,
        permissions: Permissions | None = None,
    ):
        """Local Git repository; ``base_path`` is the repo, ``ref`` a commit/branch/tag."""

    @element(parent_tags="mounts")
    def github(
        self,
        *,
        name: str,
        org: str,
        repo: str,
        sha: str | None = None,
        username: str | None = None,
        token: str | None = None,
        permissions: Permissions | None = None,
    ):
        """Remote GitHub repository via the API (``org``/``repo``)."""

    # -- composition -----------------------------------------------------
    @element(parent_tags="mounts")
    def relative(
        self,
        *,
        name: str,
        path: str,
        permissions: Permissions | None = None,
    ):
        """Child mount of an already-declared parent — ``path`` is 'parent:subpath'."""
