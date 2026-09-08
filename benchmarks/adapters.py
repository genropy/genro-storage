"""Real S3 clients behind a small benchmark protocol. No storage mocks."""

from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
import importlib.util
from pathlib import Path
from threading import Lock
from types import SimpleNamespace
import sys
import tempfile

import boto3
from botocore.exceptions import ClientError
import s3fs
from smart_open import open as smart_open

from genro_storage import StorageManager
from genro_storage.backends.fsspec import FsspecBackend


@dataclass
class Target:
    endpoint: str
    bucket: str
    region: str
    access_key: str = field(repr=False)
    secret_key: str = field(repr=False)
    token: str | None = field(default=None, repr=False)

    def client(self):
        return boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            region_name=self.region,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            aws_session_token=self.token,
        )


class Requests:
    """Count HTTP send attempts, including retries; never record URLs or headers."""

    def __init__(self):
        self.lock = Lock()
        self.counts = Counter()

    def sent(self, event_name, **kwargs):
        with self.lock:
            self.counts[event_name.rsplit(".", 1)[-1]] += 1

    def attach(self, client):
        client.meta.events.register("before-send.s3.*", self.sent)

    def reset(self):
        with self.lock:
            self.counts.clear()

    def snapshot(self):
        with self.lock:
            return dict(self.counts)


class BotoAdapter:
    always_http = True

    def __init__(self, target, prefix):
        self.target, self.prefix = target, prefix
        self.requests = Requests()
        self.client = target.client()
        self.requests.attach(self.client)

    def key(self, path):
        return self.prefix + path

    def invalidate(self):
        pass

    def exists(self, path):
        try:
            self.client.head_object(Bucket=self.target.bucket, Key=self.key(path))
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise

    def attrs(self, path):
        info = self.client.head_object(Bucket=self.target.bucket, Key=self.key(path))
        return info["LastModified"].timestamp(), info["ContentLength"], False

    def listing(self, path):
        prefix = self.key(path).rstrip("/") + "/"
        pages = self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.target.bucket, Prefix=prefix, Delimiter="/"
        )
        return sorted(
            item["Key"][len(prefix) :] for page in pages for item in page.get("Contents", [])
        )

    def read(self, path):
        response = self.client.get_object(Bucket=self.target.bucket, Key=self.key(path))
        with response["Body"] as body:
            return body.read()

    def write(self, path, data):
        self.client.put_object(Bucket=self.target.bucket, Key=self.key(path), Body=data)

    def copy(self, source, dest):
        self.client.copy_object(
            Bucket=self.target.bucket,
            Key=self.key(dest),
            CopySource={"Bucket": self.target.bucket, "Key": self.key(source)},
        )

    def move(self, source, dest):
        self.copy(source, dest)
        self.client.delete_object(Bucket=self.target.bucket, Key=self.key(source))

    @contextmanager
    def local_path(self, path):
        with tempfile.TemporaryDirectory() as directory:
            local = str(Path(directory) / "data.bin")
            self.client.download_file(self.target.bucket, self.key(path), local)
            yield local

    def close(self):
        self.client.close()


class SmartOpenAdapter(BotoAdapter):
    """Direct smart_open transfer baseline; metadata/copy use boto3."""

    def read(self, path):
        with smart_open(
            f"s3://{self.target.bucket}/{self.key(path)}",
            "rb",
            transport_params={"client": self.client},
        ) as stream:
            return stream.read()

    def write(self, path, data):
        with smart_open(
            f"s3://{self.target.bucket}/{self.key(path)}",
            "wb",
            transport_params={"client": self.client},
        ) as stream:
            stream.write(data)


class FsspecAdapter:
    always_http = False

    def __init__(self, target, prefix, layer="s3fs", version_aware=True):
        self.prefix = f"{target.bucket}/{prefix}"
        self.requests = Requests()
        # The manager does not expose skip_instance_cache. Clear the registry
        # BEFORE construction so each adapter owns a distinct real client.
        s3fs.S3FileSystem.clear_instance_cache()
        options = dict(
            key=target.access_key,
            secret=target.secret_key,
            endpoint_url=target.endpoint,
            client_kwargs={"region_name": target.region},
        )
        if layer == "genro":
            self.manager = StorageManager()
            self.manager.configure(
                [
                    dict(
                        name="bench",
                        protocol="s3",
                        bucket=target.bucket,
                        base_path=prefix.rstrip("/"),
                        access_key=target.access_key,
                        secret_key=target.secret_key,
                        endpoint_url=target.endpoint,
                        region=target.region,
                    )
                ]
            )
            self.backend = self.manager._mounts["bench"]
            self.fs = self.backend.fs
            # Diagnostic-only configuration; production code is left untouched.
            self.fs.version_aware = version_aware
        elif layer == "backend":
            self.backend = FsspecBackend(
                "s3", base_path=self.prefix.rstrip("/"), version_aware=version_aware, **options
            )
            self.fs = self.backend.fs
        else:
            self.fs = s3fs.S3FileSystem(version_aware=version_aware, **options)
        if target.token:
            self.fs.token = target.token
        self.layer = layer
        self.requests.attach(self.fs.connect())

    def node(self, path):
        return self.manager.node("bench:" + path)

    def invalidate(self):
        self.fs.invalidate_cache()

    def exists(self, path):
        if self.layer == "genro":
            return self.node(path).exists()
        if self.layer == "backend":
            return self.backend.exists(path)
        return self.fs.exists(self.prefix + path)

    def attrs(self, path):
        if self.layer == "genro":
            return self.node(path).ext_attributes
        if self.layer == "backend":
            return self.backend.mtime(path), self.backend.size(path), self.backend.is_dir(path)
        info = self.fs.info(self.prefix + path)
        return info["LastModified"].timestamp(), info["size"], info["type"] == "directory"

    def listing(self, path):
        if self.layer == "genro":
            return sorted(node.basename for node in self.node(path).children())
        if self.layer == "backend":
            return sorted(self.backend.list_dir(path))
        return sorted(
            item.rsplit("/", 1)[-1] for item in self.fs.ls(self.prefix + path, detail=False)
        )

    def read(self, path):
        if self.layer == "genro":
            return self.node(path).read_bytes()
        if self.layer == "backend":
            return self.backend.read_bytes(path)
        with self.fs.open(self.prefix + path, "rb") as stream:
            return stream.read()

    def write(self, path, data):
        if self.layer == "genro":
            return self.node(path).write_bytes(data)
        if self.layer == "backend":
            return self.backend.write_bytes(path, data)
        with self.fs.open(self.prefix + path, "wb") as stream:
            stream.write(data)

    def copy(self, source, dest):
        if self.layer == "genro":
            return self.node(source).copy_to(self.node(dest))
        if self.layer == "backend":
            return self.backend.copy(source, self.backend, dest)
        return self.fs.copy(self.prefix + source, self.prefix + dest)

    def move(self, source, dest):
        if self.layer == "genro":
            return self.node(source).move_to(self.node(dest))
        self.copy(source, dest)
        self.fs.rm(self.prefix + source)

    @contextmanager
    def local_path(self, path):
        if self.layer == "genro":
            with self.node(path).local_path(mode="r") as local:
                yield local
        elif self.layer == "backend":
            with self.backend.local_path(path, mode="r") as local:
                yield local
        else:
            with tempfile.TemporaryDirectory() as directory:
                local = str(Path(directory) / "data.bin")
                self.fs.get_file(self.prefix + path, local)
                yield local

    def close(self):
        s3fs.S3FileSystem.close_session(self.fs.loop, self.fs._s3creator)


def load_legacy(root):
    """Import the real legacy module once, before any timing starts."""
    root = Path(root).resolve()
    sys.path.insert(0, str(root / "gnrpy"))
    from gnr.lib.services.storage import StorageNode
    import gnr.lib.services.storage as storage_module

    if not Path(storage_module.__file__).resolve().is_relative_to(root):
        raise ValueError("Imported legacy package is outside --legacy-root")
    path = root / "projects/gnrcore/packages/sys/resources/services/storage/aws_s3.py"
    spec = importlib.util.spec_from_file_location("benchmark_legacy_s3", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Service, StorageNode


class LegacyAdapter:
    always_http = True

    def __init__(self, target, prefix, classes):
        service_cls, node_cls = classes
        self.node_cls = node_cls
        self.requests = Requests()
        requests = self.requests
        self.clients = []
        clients = self.clients
        instrumentation_lock = Lock()

        class ObservedService(service_cls):
            @property
            def _client(self):
                client = super()._client
                # The real service periodically recreates its boto3 client and
                # session. Observe every replacement without changing its I/O.
                with instrumentation_lock:
                    if client not in clients:
                        requests.attach(client)
                        clients.append(client)
                return client

        # Only site configuration plumbing is supplied here. All file operations
        # execute the unmodified StorageNode and aws_s3.Service implementations.
        parent = SimpleNamespace(gnrapp=SimpleNamespace(config={"packages": {}}))
        self.service = ObservedService(
            parent=parent,
            bucket=target.bucket,
            base_path=prefix,
            aws_access_key_id=target.access_key,
            aws_secret_access_key=target.secret_key,
            aws_session_token=target.token,
            region_name=target.region,
            custom_endpoint=True,
            endpoint_url=target.endpoint,
            versioned=True,
        )
        self.service.service_name = "bench"
        self.service.service_implementation = "aws_s3"
        self.service._client  # Initialize before worker threads share the client.

    def node(self, path):
        return self.node_cls(parent=self.service.parent, path=path, service=self.service)

    def invalidate(self):
        pass

    def exists(self, path):
        return self.node(path).exists

    def attrs(self, path):
        return self.node(path).ext_attributes

    def listing(self, path):
        return sorted(node.basename for node in self.node(path).children() or [])

    def read(self, path):
        with self.node(path).open("rb") as stream:
            return stream.read()

    def write(self, path, data):
        with self.node(path).open("wb") as stream:
            stream.write(data)

    def copy(self, source, dest):
        self.node(source).copy(self.node(dest))

    def move(self, source, dest):
        self.node(source).move(self.node(dest))

    def local_path(self, path):
        return self.node(path).local_path(mode="r")

    def close(self):
        for client in self.clients:
            client.close()


ADAPTERS = ("legacy", "genro", "genro-unversioned", "backend", "s3fs", "boto3", "smart-open")


def build_adapter(name, target, prefix, legacy=None):
    if name == "legacy":
        return LegacyAdapter(target, prefix, legacy)
    if name == "boto3":
        return BotoAdapter(target, prefix)
    if name == "smart-open":
        return SmartOpenAdapter(target, prefix)
    return FsspecAdapter(
        target,
        prefix,
        layer="genro" if name.startswith("genro") else name,
        version_aware=name != "genro-unversioned",
    )
