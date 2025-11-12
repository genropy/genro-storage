# Copyright (c) 2025 Softwell Srl, Milano, Italy
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""StorageManager - Main entry point for configuring and accessing storage.

This module provides the StorageManager class which is the primary interface
for configuring storage backends and creating StorageNode instances.
"""

from __future__ import annotations
from typing import Any, Annotated
import json
from pathlib import Path

# TODO: Replace with genro_core.decorators.api.apiready when available
from .decorators import apiready

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .node import StorageNode
from .exceptions import StorageConfigError, StorageNotFoundError
from .backends import StorageBackend
from .backends.local import LocalStorage
from .backends.fsspec import FsspecBackend
from .backends.base64 import Base64Backend
from .backends.relative import RelativeMountBackend


@apiready(path="/storage")
class StorageManager:
    """Main entry point for configuring and accessing storage.

    StorageManager is responsible for:
    - Configuring mount points that map to storage backends
    - Creating StorageNode instances for file/directory access
    - Managing the lifecycle of storage backend connections

    A mount point is a logical name (e.g., "home", "uploads", "s3") that
    maps to an actual storage backend (local filesystem, S3 bucket, etc.).

    Examples:
        >>> # Create manager
        >>> storage = StorageManager()
        >>>
        >>> # Configure from file
        >>> storage.configure('/etc/app/storage.yaml')
        >>>
        >>> # Configure programmatically
        >>> storage.configure([
        ...     {'name': 'home', 'type': 'local', 'path': '/home/user'},
        ...     {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
        ... ])
        >>>
        >>> # Access files
        >>> node = storage.node('home:documents/report.pdf')
        >>> content = node.read_text()
    """

    def __init__(self):
        """Initialize a new StorageManager with no configured mounts.

        After initialization, you must call ``configure()`` to set up
        mount points before you can access any files.

        Examples:
            >>> from genro_storage import StorageManager
            >>> storage = StorageManager()
        """
        # Dictionary mapping mount names to backend instances
        self._mounts: dict[str, Any] = {}

    def configure(
        self,
        source: Annotated[
            str | list[dict[str, Any]],
            "Configuration source: path to YAML/JSON file or list of mount configurations",
        ],
    ) -> None:
        """Configure mount points from various sources.

        This method can be called multiple times. If a mount with the same
        name already exists, it will be replaced with the new configuration.

        Args:
            source: Configuration source, can be:
                - str: Path to YAML or JSON configuration file
                - list[dict]: List of mount configurations

        Raises:
            FileNotFoundError: If configuration file doesn't exist
            StorageConfigError: If configuration format is invalid
            TypeError: If source is neither str nor list

        Configuration Dictionary Format:
            Each mount configuration dict must have:

            - name (str, required): Mount point name (e.g., "home", "uploads")
            - type (str, required): Backend type ("local", "s3", "gcs", "azure", "http", "memory")
            - Additional fields depend on type (see examples below)

        Examples:
            **Local Storage:**

            >>> storage.configure([{
            ...     'name': 'home',
            ...     'type': 'local',
            ...     'path': '/home/user'  # required: absolute path
            ... }])

            **S3 Storage:**

            >>> storage.configure([{
            ...     'name': 'uploads',
            ...     'type': 's3',
            ...     'bucket': 'my-bucket',    # required
            ...     'prefix': 'uploads/',     # optional, default: ""
            ...     'region': 'eu-west-1',    # optional
            ...     'anon': False             # optional, default: False
            ... }])

            **GCS Storage:**

            >>> storage.configure([{
            ...     'name': 'backups',
            ...     'type': 'gcs',
            ...     'bucket': 'my-backups',   # required
            ...     'prefix': '',             # optional
            ...     'token': 'path/to/service-account.json'  # optional
            ... }])

            **Azure Blob Storage:**

            >>> storage.configure([{
            ...     'name': 'archive',
            ...     'type': 'azure',
            ...     'container': 'archives',      # required
            ...     'account_name': 'myaccount',  # required
            ...     'account_key': '...'          # optional if using managed identity
            ... }])

            **HTTP Storage (read-only):**

            >>> storage.configure([{
            ...     'name': 'cdn',
            ...     'type': 'http',
            ...     'base_url': 'https://cdn.example.com'  # required
            ... }])

            **Memory Storage (for testing):**

            >>> storage.configure([{
            ...     'name': 'test',
            ...     'type': 'memory'
            ... }])

            **From YAML File:**

            .. code-block:: yaml

                # storage.yaml
                - name: home
                  type: local
                  path: /home/user

                - name: uploads
                  type: s3
                  bucket: my-app-uploads
                  region: eu-west-1

            >>> storage.configure('/etc/app/storage.yaml')

            **From JSON File:**

            .. code-block:: json

                [
                  {
                    "name": "home",
                    "type": "local",
                    "path": "/home/user"
                  },
                  {
                    "name": "uploads",
                    "type": "s3",
                    "bucket": "my-app-uploads",
                    "region": "eu-west-1"
                  }
                ]

            >>> storage.configure('./config/storage.json')

            **Multiple Calls (mounts are replaced if same name):**

            >>> storage.configure([{'name': 'home', 'type': 'local', 'path': '/home/user'}])
            >>> storage.configure([{'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}])
            >>> # Now both 'home' and 'uploads' are configured
        """
        # Parse source
        if isinstance(source, str):
            config_list = self._load_config_file(source)
        elif isinstance(source, list):
            config_list = source
        else:
            raise TypeError(
                f"source must be str (file path) or list[dict], got {type(source).__name__}"
            )

        # Validate and configure each mount
        for config in config_list:
            self._configure_mount(config)

    @apiready
    def add_mount(
        self, config: Annotated[dict[str, Any], "Mount configuration dictionary"]
    ) -> None:
        """Add or update a single mount point.

        If a mount with the same name already exists, it will be replaced.

        Args:
            config: Mount configuration dictionary with 'name' and 'type' fields

        Raises:
            StorageConfigError: If configuration is invalid

        Examples:
            >>> storage.add_mount({
            ...     'name': 'uploads',
            ...     'type': 's3',
            ...     'bucket': 'my-bucket'
            ... })
        """
        self._configure_mount(config)

    @apiready
    def delete_mount(self, name: Annotated[str, "Mount point name to delete"]) -> None:
        """Delete a mount point.

        Args:
            name: Name of the mount point to remove

        Raises:
            KeyError: If mount point doesn't exist

        Examples:
            >>> storage.delete_mount('uploads')
        """
        if name not in self._mounts:
            raise KeyError(f"Mount point '{name}' not found")
        del self._mounts[name]

    def _load_config_file(self, filepath: str) -> list[dict[str, Any]]:
        """Load configuration from YAML or JSON file.

        Args:
            filepath: Path to configuration file

        Returns:
            list[dict]: List of mount configurations

        Raises:
            FileNotFoundError: If file doesn't exist
            StorageConfigError: If file format is invalid
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        # Determine format from extension
        suffix = path.suffix.lower()

        try:
            with open(path, "r") as f:
                if suffix in (".yaml", ".yml"):
                    if not HAS_YAML:
                        raise StorageConfigError(
                            "YAML support not available. Install PyYAML: pip install PyYAML"
                        )
                    config = yaml.safe_load(f)
                elif suffix == ".json":
                    config = json.load(f)
                else:
                    raise StorageConfigError(
                        f"Unsupported configuration file format: {suffix}. "
                        f"Use .yaml, .yml, or .json"
                    )
        except Exception as e:
            if HAS_YAML and isinstance(e, yaml.YAMLError):
                raise StorageConfigError(f"Failed to parse YAML file: {e}")
            elif isinstance(e, json.JSONDecodeError):
                raise StorageConfigError(f"Failed to parse JSON file: {e}")
            else:
                raise

        if not isinstance(config, list):
            raise StorageConfigError(
                f"Configuration must be a list of mount configs, got {type(config).__name__}"
            )

        return config

    def _configure_mount(self, config: dict[str, Any]) -> None:
        """Configure a single mount point.

        Args:
            config: Mount configuration dictionary

        Raises:
            StorageConfigError: If configuration is invalid
        """
        # Validate required fields
        if "name" not in config:
            raise StorageConfigError("Mount configuration missing required field: 'name'")

        mount_name = config["name"]

        # Check for relative mount (child mount referencing a parent)
        # Only check if path is a string (not callable)
        if "path" in config and isinstance(config["path"], str) and ":" in config["path"]:
            self._configure_relative_mount(mount_name, config)
            return

        # Accept 'protocol' as standard, 'type' for legacy
        backend_type = config.get("protocol") or config.get("type")
        if not backend_type:
            raise StorageConfigError(
                f"Mount configuration for '{config['name']}' missing required field: 'protocol'"
            )

        # Create appropriate backend
        if backend_type == "local":
            # Accept 'base_path' as standard
            base_path = config.get("base_path") or config.get("path")
            if not base_path:
                raise StorageConfigError(
                    f"Local storage '{mount_name}' missing required field: 'base_path'"
                )
            # LocalStorage supports both string paths and callables
            # Optional base_url for URL generation
            backend = LocalStorage(
                path=base_path,
                base_url=config.get("base_url")
            )

        elif backend_type == "memory":
            backend = FsspecBackend("memory", base_path=config.get("base_path", ""))

        elif backend_type == "s3":
            if "bucket" not in config:
                raise StorageConfigError(
                    f"S3 storage '{mount_name}' missing required field: 'bucket'"
                )
            # Build S3 path: bucket/base_path
            path = config["bucket"]
            # Accept 'base_path' as standard, 'prefix' for legacy
            if config.get("base_path"):
                path = f"{path}/{config['base_path'].strip('/')}"
            elif config.get("prefix"):
                path = f"{path}/{config['prefix'].strip('/')}"

            kwargs = {}
            if "region" in config:
                kwargs["client_kwargs"] = {"region_name": config["region"]}
            if "anon" in config:
                kwargs["anon"] = config["anon"]
            # Accept 'access_key'/'secret_key' as standard, 'key'/'secret' for legacy
            if config.get("access_key"):
                kwargs["key"] = config["access_key"]
            elif config.get("key"):
                kwargs["key"] = config["key"]
            if config.get("secret_key"):
                kwargs["secret"] = config["secret_key"]
            elif config.get("secret"):
                kwargs["secret"] = config["secret"]
            if "endpoint_url" in config:
                kwargs["endpoint_url"] = config["endpoint_url"]

            backend = FsspecBackend("s3", base_path=path, **kwargs)

        elif backend_type == "gcs":
            if "bucket" not in config:
                raise StorageConfigError(
                    f"GCS storage '{mount_name}' missing required field: 'bucket'"
                )
            path = config["bucket"]
            # Accept 'base_path' as standard, 'prefix' for legacy
            if config.get("base_path"):
                path = f"{path}/{config['base_path'].strip('/')}"
            elif config.get("prefix"):
                path = f"{path}/{config['prefix'].strip('/')}"

            kwargs = {}
            if "token" in config:
                kwargs["token"] = config["token"]
            if "project" in config:
                kwargs["project"] = config["project"]
            if "endpoint_url" in config:
                kwargs["endpoint_url"] = config["endpoint_url"]

            backend = FsspecBackend("gcs", base_path=path, **kwargs)

        elif backend_type == "azure":
            if "container" not in config:
                raise StorageConfigError(
                    f"Azure storage '{mount_name}' missing required field: 'container'"
                )
            if "account_name" not in config:
                raise StorageConfigError(
                    f"Azure storage '{mount_name}' missing required field: 'account_name'"
                )

            # Base path is just the container name for Azure
            base_path = config["container"]

            kwargs = {"account_name": config["account_name"]}
            if "account_key" in config:
                kwargs["account_key"] = config["account_key"]
            if "sas_token" in config:
                kwargs["sas_token"] = config["sas_token"]
            if "connection_string" in config:
                kwargs["connection_string"] = config["connection_string"]

            backend = FsspecBackend("az", base_path=base_path, **kwargs)

        elif backend_type == "http":
            # Accept 'base_path' as standard, 'base_url' for legacy
            base_path_value = config.get("base_path") or config.get("base_url")
            if not base_path_value:
                raise StorageConfigError(
                    f"HTTP storage '{mount_name}' missing required field: 'base_path'"
                )
            backend = FsspecBackend("http", base_path=base_path_value)

        elif backend_type == "smb":
            if "host" not in config:
                raise StorageConfigError(
                    f"SMB storage '{mount_name}' missing required field: 'host'"
                )
            if "share" not in config:
                raise StorageConfigError(
                    f"SMB storage '{mount_name}' missing required field: 'share'"
                )

            # Build SMB path: /share/base_path
            path = f"/{config['share']}"
            # Accept 'base_path' as standard, 'path' for legacy
            if config.get("base_path"):
                path = f"{path}/{config['base_path'].strip('/')}"
            elif config.get("path"):
                path = f"{path}/{config['path'].strip('/')}"

            kwargs = {"host": config["host"]}
            if "username" in config:
                kwargs["username"] = config["username"]
            if "password" in config:
                kwargs["password"] = config["password"]
            if "domain" in config:
                kwargs["domain"] = config["domain"]
            if "port" in config:
                kwargs["port"] = config["port"]

            backend = FsspecBackend("smb", base_path=path, **kwargs)

        elif backend_type == "sftp":
            if "host" not in config:
                raise StorageConfigError(
                    f"SFTP storage '{mount_name}' missing required field: 'host'"
                )
            if "username" not in config:
                raise StorageConfigError(
                    f"SFTP storage '{mount_name}' missing required field: 'username'"
                )

            # Build SFTP path: host:/base_path
            # Accept 'base_path' as standard, 'path' for legacy
            path = config.get("base_path") or config.get("path", "/")

            kwargs = {"host": config["host"], "username": config["username"]}
            if "password" in config:
                kwargs["password"] = config["password"]
            if "port" in config:
                kwargs["port"] = config["port"]
            if "key_filename" in config:
                kwargs["key_filename"] = config["key_filename"]
            if "passphrase" in config:
                kwargs["passphrase"] = config["passphrase"]
            if "timeout" in config:
                kwargs["timeout"] = config["timeout"]

            backend = FsspecBackend("sftp", base_path=path, **kwargs)

        elif backend_type == "zip":
            if "file" not in config:
                raise StorageConfigError(
                    f"ZIP storage '{mount_name}' missing required field: 'file'"
                )

            # ZIP archives use 'fo' parameter for file path
            kwargs = {"fo": config["file"]}
            if "mode" in config:
                kwargs["mode"] = config["mode"]
            if "target_protocol" in config:
                kwargs["target_protocol"] = config["target_protocol"]
            if "target_options" in config:
                kwargs["target_options"] = config["target_options"]

            backend = FsspecBackend("zip", base_path="", **kwargs)

        elif backend_type == "tar":
            if "file" not in config:
                raise StorageConfigError(
                    f"TAR storage '{mount_name}' missing required field: 'file'"
                )

            # TAR archives use 'fo' parameter for file path
            kwargs = {"fo": config["file"]}
            if "compression" in config:
                kwargs["compression"] = config["compression"]
            if "target_protocol" in config:
                kwargs["target_protocol"] = config["target_protocol"]
            if "target_options" in config:
                kwargs["target_options"] = config["target_options"]

            backend = FsspecBackend("tar", base_path="", **kwargs)

        elif backend_type == "git":
            # Accept 'base_path' as standard, 'path' for legacy
            git_path = config.get("base_path") or config.get("path")
            if not git_path:
                raise StorageConfigError(
                    f"Git storage '{mount_name}' missing required field: 'base_path'"
                )

            # Git backend accesses local Git repositories
            kwargs = {"path": git_path}
            if "ref" in config:
                kwargs["ref"] = config["ref"]  # commit, tag, or branch
            if "fo" in config:
                kwargs["fo"] = config["fo"]

            backend = FsspecBackend("git", base_path="", **kwargs)

        elif backend_type == "github":
            if "org" not in config:
                raise StorageConfigError(
                    f"GitHub storage '{mount_name}' missing required field: 'org'"
                )
            if "repo" not in config:
                raise StorageConfigError(
                    f"GitHub storage '{mount_name}' missing required field: 'repo'"
                )

            # GitHub backend accesses remote repositories via API
            kwargs = {"org": config["org"], "repo": config["repo"]}
            if "sha" in config:
                kwargs["sha"] = config["sha"]  # commit, branch, or tag
            if "username" in config:
                kwargs["username"] = config["username"]  # GitHub username for auth
            if "token" in config:
                kwargs["token"] = config["token"]  # GitHub personal access token

            backend = FsspecBackend("github", base_path="", **kwargs)

        elif backend_type == "webdav":
            if "url" not in config:
                raise StorageConfigError(
                    f"WebDAV storage '{mount_name}' missing required field: 'url'"
                )

            # WebDAV backend for Nextcloud, ownCloud, SharePoint, etc.
            kwargs = {"base_url": config["url"]}
            if "username" in config and "password" in config:
                kwargs["auth"] = (config["username"], config["password"])
            if "token" in config:
                kwargs["token"] = config["token"]
            if "cert" in config:
                kwargs["cert"] = config["cert"]
            if "verify_ssl" in config:
                kwargs["verify_ssl"] = config["verify_ssl"]

            backend = FsspecBackend("webdav", base_path="", **kwargs)

        elif backend_type == "libarchive":
            if "file" not in config:
                raise StorageConfigError(
                    f"LibArchive storage '{mount_name}' missing required field: 'file'"
                )

            # LibArchive backend for universal archive support (7z, rar, iso, etc.)
            kwargs = {"fo": config["file"]}
            if "target_protocol" in config:
                kwargs["target_protocol"] = config["target_protocol"]
            if "target_options" in config:
                kwargs["target_options"] = config["target_options"]

            backend = FsspecBackend("libarchive", base_path="", **kwargs)

        elif backend_type == "base64":
            # Base64 backend has no configuration parameters
            backend = Base64Backend()

        else:
            raise StorageConfigError(
                f"Unknown storage type '{backend_type}' for mount '{mount_name}'. "
                f"Supported types: local, s3, gcs, azure, http, memory, base64, smb, sftp, zip, tar, "
                f"git, github, webdav, libarchive"
            )

        # Apply permission restrictions if specified
        if "permissions" in config:
            backend = self._apply_permissions(mount_name, backend, config["permissions"])

        self._mounts[mount_name] = backend

    def _configure_relative_mount(self, mount_name: str, config: dict[str, Any]) -> None:
        """Configure a relative mount point that references a parent mount.

        A relative mount is a child mount that inherits the backend type and
        configuration from a parent mount, but adds a relative path prefix
        and optional permission restrictions.

        Args:
            mount_name: Name for the new child mount
            config: Configuration dict with 'path' and optional 'permissions'

        Raises:
            StorageConfigError: If path format is invalid or parent mount not found

        Examples:
            >>> # After configuring parent:
            >>> # {'name': 'data', 'type': 's3', 'bucket': 'my-bucket'}
            >>> # Configure child with permissions:
            >>> # {'name': 'public', 'path': 'data:public', 'permissions': 'readonly'}
            >>> # Now 'public:file.txt' can only read from 'data:public/file.txt'
        """
        mount_path = config["path"]

        # Parse parent mount and relative path
        if ":" not in mount_path:
            raise StorageConfigError(
                f"Relative mount path must contain ':' separator (got '{mount_path}')"
            )

        parent_mount_name, relative_path = mount_path.split(":", 1)

        # Validate parent mount exists
        if parent_mount_name not in self._mounts:
            available = ", ".join(f"'{m}'" for m in self._mounts.keys()) if self._mounts else "none"
            raise StorageConfigError(
                f"Parent mount '{parent_mount_name}' not found for relative mount '{mount_name}'. "
                f"Available mounts: {available}"
            )

        # Get parent backend and create relative wrapper
        parent_backend = self._mounts[parent_mount_name]

        # Get permissions (default: 'delete' = full access)
        permissions = config.get("permissions", "delete")

        # Validate permissions value
        valid_permissions = ("readonly", "readwrite", "delete")
        if permissions not in valid_permissions:
            raise StorageConfigError(
                f"Invalid permissions '{permissions}' for mount '{mount_name}'. "
                f"Valid values: {', '.join(valid_permissions)}"
            )

        relative_backend = RelativeMountBackend(parent_backend, relative_path, permissions)

        self._mounts[mount_name] = relative_backend

    def _apply_permissions(
        self, mount_name: str, backend: StorageBackend, permissions: str
    ) -> StorageBackend:
        """Apply permission restrictions to a backend by wrapping with RelativeMountBackend.

        Validates that requested permissions are compatible with backend capabilities.
        For example, cannot request 'readwrite' on a read-only backend like HTTP.

        Args:
            mount_name: Name of the mount (for error messages)
            backend: The backend to wrap
            permissions: Permission level ('readonly', 'readwrite', 'delete')

        Returns:
            StorageBackend: Original backend wrapped with permission layer

        Raises:
            StorageConfigError: If permissions are invalid or incompatible with backend
        """
        # Validate permissions value
        valid_permissions = ("readonly", "readwrite", "delete")
        if permissions not in valid_permissions:
            raise StorageConfigError(
                f"Invalid permissions '{permissions}' for mount '{mount_name}'. "
                f"Valid values: {', '.join(valid_permissions)}"
            )

        # Check compatibility with backend capabilities
        caps = backend.capabilities

        # If backend is readonly, can only request 'readonly' permission
        if caps.readonly and permissions in ("readwrite", "delete"):
            raise StorageConfigError(
                f"Cannot configure mount '{mount_name}' with '{permissions}' permission. "
                f"Backend type is read-only (supports only 'readonly' permission)"
            )

        # If backend doesn't support write, cannot request write/delete
        if not caps.write and permissions in ("readwrite", "delete"):
            raise StorageConfigError(
                f"Cannot configure mount '{mount_name}' with '{permissions}' permission. "
                f"Backend does not support write operations"
            )

        # If backend doesn't support delete, cannot request delete permission
        if not caps.delete and permissions == "delete":
            raise StorageConfigError(
                f"Cannot configure mount '{mount_name}' with 'delete' permission. "
                f"Backend does not support delete operations"
            )

        # Wrap backend with permission layer (empty relative path = no prefix)
        return RelativeMountBackend(backend, relative_path="", permissions=permissions)

    @apiready
    def node(
        self,
        mount_or_path: Annotated[
            str | None, "Mount name or full path (mount:path format), or None for dummy node"
        ] = None,
        *path_parts: str,
        version: Annotated[
            int | str | None, "Optional version: int for index (-1=latest), str for version_id"
        ] = None,
    ) -> StorageNode:
        """Create a StorageNode pointing to a file or directory.

        This is the primary way to access files and directories. The path
        uses a mount:path format where the mount name refers to a configured
        storage backend.

        When called without arguments, creates a dummy/accumulator node that
        can be used to build content from multiple sources.

        Args:
            mount_or_path: Either:
                - Full path with mount: "mount:path/to/file"
                - Just mount name: "mount"
                - None: creates a dummy accumulator node (no storage backend)
            *path_parts: Additional path components to join
            version: Optional version specifier for versioned storage (S3, GCS).
                If specified, creates a read-only snapshot node of that version.
                Can be int (index: -1=latest, -2=previous) or str (version_id).

        Returns:
            StorageNode: A new StorageNode instance

        Raises:
            KeyError: If mount point doesn't exist (wrapped as StorageNotFoundError)
            ValueError: If path format is invalid

        Path Normalization:
            - Multiple slashes collapsed: "a//b" → "a/b"
            - Leading/trailing slashes stripped
            - No support for ".." (parent directory) - raises ValueError

        Examples:
            **Full path in one string:**

            >>> node = storage.node('home:documents/report.pdf')

            **Mount + path parts:**

            >>> node = storage.node('home', 'documents', 'report.pdf')

            **Mix styles:**

            >>> node = storage.node('home:documents', 'reports', 'q4.pdf')

            **Dynamic composition:**

            >>> user_id = '123'
            >>> year = '2024'
            >>> node = storage.node('uploads', 'users', user_id, year, 'avatar.jpg')
            >>> # Result: uploads:users/123/2024/avatar.jpg

            **Just mount (root of storage):**

            >>> node = storage.node('home')
            >>> # Result: home:

            **Path with special characters:**

            >>> # Spaces and unicode are OK
            >>> node = storage.node('home:My Documents/Café Menu.pdf')

            **Invalid paths (will raise ValueError):**

            >>> # Parent directory traversal not allowed
            >>> node = storage.node('home:documents/../etc/passwd')  # ValueError

            **Dummy node (accumulator):**

            >>> dummy = storage.node()  # No parameters
            >>> dummy.append(node1)
            >>> dummy.extend(node2, node3)
            >>> dummy.read_text()  # Concatenates all sources
        """
        # Create dummy node if no mount specified
        if mount_or_path is None:
            return StorageNode(self, None, None, version=version)

        # Parse mount and path
        if ":" in mount_or_path:
            # Format: "mount:path"
            mount_name, initial_path = mount_or_path.split(":", 1)
            path_components = [initial_path] if initial_path else []
        else:
            # Just mount name
            mount_name = mount_or_path
            path_components = []

        # Add additional path parts
        path_components.extend(path_parts)

        # Check if mount exists
        if mount_name not in self._mounts:
            raise StorageNotFoundError(
                f"Mount point '{mount_name}' not found. "
                f"Available mounts: {', '.join(self._mounts.keys())}"
            )

        # Join and normalize path
        path = "/".join(path_components)
        path = self._normalize_path(path)

        # Create and return node
        return StorageNode(self, mount_name, path, version=version)

    def iternode(self, *nodes) -> StorageNode:
        """Create a virtual node that concatenates multiple nodes lazily.

        This creates a virtual node (no physical storage) that accumulates
        references to other nodes. Content is only read when materialized
        via read_text(), read_bytes(), copy(), or zip().

        Args:
            *nodes: StorageNode instances to concatenate

        Returns:
            StorageNode: Virtual node with concatenation capability

        Examples:
            >>> # Create from existing nodes
            >>> n1 = storage.node('mem:part1.txt')
            >>> n2 = storage.node('mem:part2.txt')
            >>> combined = storage.iternode(n1, n2)
            >>>
            >>> # Read concatenated content
            >>> content = combined.read_text()
            >>>
            >>> # Add more nodes
            >>> n3 = storage.node('mem:part3.txt')
            >>> combined.append(n3)
            >>>
            >>> # Save to file
            >>> result = storage.node('mem:result.txt')
            >>> combined.copy(result)
            >>>
            >>> # Create ZIP
            >>> zip_bytes = combined.zip()
        """
        from .node import StorageNode

        node = StorageNode(self, None, None, version=None)
        node._is_virtual = True
        node._virtual_type = "iter"
        node._sources = list(nodes)
        return node

    def diffnode(self, node1: StorageNode, node2: StorageNode) -> StorageNode:
        """Create a virtual node that generates a diff between two nodes.

        This creates a virtual node that generates a unified diff between
        two text files. The diff is only computed when materialized via
        read_text() or copy().

        Args:
            node1: First node (old version)
            node2: Second node (new version)

        Returns:
            StorageNode: Virtual node with diff capability

        Raises:
            ValueError: If nodes contain binary data

        Examples:
            >>> # Compare two versions
            >>> v1 = storage.node('mem:config_v1.txt')
            >>> v2 = storage.node('mem:config_v2.txt')
            >>> diff = storage.diffnode(v1, v2)
            >>>
            >>> # Read diff
            >>> changes = diff.read_text()
            >>>
            >>> # Save diff to file
            >>> diff_file = storage.node('mem:changes.diff')
            >>> diff.copy(diff_file)
        """
        from .node import StorageNode

        node = StorageNode(self, None, None, version=None)
        node._is_virtual = True
        node._virtual_type = "diff"
        node._sources = [node1, node2]
        return node

    def _normalize_path(self, path: str) -> str:
        """Normalize a path.

        Args:
            path: Path to normalize

        Returns:
            str: Normalized path

        Raises:
            ValueError: If path contains invalid components (e.g., "..")
        """
        if not path:
            return ""

        # Check for parent directory traversal
        if ".." in path.split("/"):
            raise ValueError("Parent directory traversal (..) is not supported")

        # Normalize: strip leading/trailing slashes, collapse multiple slashes
        parts = [p for p in path.split("/") if p]
        return "/".join(parts)

    @apiready
    def get_mount_names(self) -> Annotated[list[str], "List of configured mount point names"]:
        """Get list of configured mount names.

        Returns:
            list[str]: List of mount point names

        Examples:
            >>> storage.configure([
            ...     {'name': 'home', 'type': 'local', 'path': '/home/user'},
            ...     {'name': 'uploads', 'type': 's3', 'bucket': 'my-bucket'}
            ... ])
            >>> print(storage.get_mount_names())
            ['home', 'uploads']
        """
        return list(self._mounts.keys())

    @apiready
    def has_mount(
        self, name: Annotated[str, "Mount point name to check"]
    ) -> Annotated[bool, "True if mount exists"]:
        """Check if a mount point is configured.

        Args:
            name: Mount point name to check

        Returns:
            bool: True if mount exists

        Examples:
            >>> if storage.has_mount('uploads'):
            ...     node = storage.node('uploads:file.txt')
            ... else:
            ...     print("Uploads storage not configured")
        """
        return name in self._mounts

    def __repr__(self) -> str:
        """String representation for debugging."""
        mount_names = ", ".join(self._mounts.keys()) if self._mounts else "none"
        return f"StorageManager(mounts=[{mount_names}])"
