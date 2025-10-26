"""StorageManager - Main entry point for configuring and accessing storage.

This module provides the StorageManager class which is the primary interface
for configuring storage backends and creating StorageNode instances.
"""

from __future__ import annotations
from typing import Any
import json
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from .node import StorageNode
from .exceptions import StorageConfigError, StorageNotFoundError
from .backends import StorageBackend, LocalStorage


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
    
    def configure(self, source: str | list[dict[str, Any]]) -> None:
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
            with open(path, 'r') as f:
                if suffix in ('.yaml', '.yml'):
                    if not HAS_YAML:
                        raise StorageConfigError(
                            "YAML support not available. Install PyYAML: pip install PyYAML"
                        )
                    config = yaml.safe_load(f)
                elif suffix == '.json':
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
        if 'name' not in config:
            raise StorageConfigError("Mount configuration missing required field: 'name'")
        
        if 'type' not in config:
            raise StorageConfigError(
                f"Mount configuration for '{config['name']}' missing required field: 'type'"
            )
        
        mount_name = config['name']
        backend_type = config['type']
        
        # Create appropriate backend based on type
        if backend_type == 'local':
            if 'path' not in config:
                raise StorageConfigError(
                    f"Local storage '{mount_name}' missing required field: 'path'"
                )
            backend = LocalStorage(config['path'])
        elif backend_type == 'memory':
            raise StorageConfigError(
                f"Memory storage not yet implemented for mount '{mount_name}'"
            )
        elif backend_type == 's3':
            raise StorageConfigError(
                f"S3 storage not yet implemented for mount '{mount_name}'"
            )
        elif backend_type == 'gcs':
            raise StorageConfigError(
                f"GCS storage not yet implemented for mount '{mount_name}'"
            )
        elif backend_type == 'azure':
            raise StorageConfigError(
                f"Azure storage not yet implemented for mount '{mount_name}'"
            )
        elif backend_type == 'http':
            raise StorageConfigError(
                f"HTTP storage not yet implemented for mount '{mount_name}'"
            )
        else:
            raise StorageConfigError(
                f"Unknown storage type '{backend_type}' for mount '{mount_name}'. "
                f"Supported types: local, s3, gcs, azure, http, memory"
            )
        
        self._mounts[mount_name] = backend
    
    def node(self, mount_or_path: str, *path_parts: str) -> StorageNode:
        """Create a StorageNode pointing to a file or directory.
        
        This is the primary way to access files and directories. The path
        uses a mount:path format where the mount name refers to a configured
        storage backend.
        
        Args:
            mount_or_path: Either:
                - Full path with mount: "mount:path/to/file"
                - Just mount name: "mount"
            *path_parts: Additional path components to join
        
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
        """
        # Parse mount and path
        if ':' in mount_or_path:
            # Format: "mount:path"
            mount_name, initial_path = mount_or_path.split(':', 1)
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
        path = '/'.join(path_components)
        path = self._normalize_path(path)
        
        # Create and return node
        return StorageNode(self, mount_name, path)
    
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
            return ''
        
        # Check for parent directory traversal
        if '..' in path.split('/'):
            raise ValueError("Parent directory traversal (..) is not supported")
        
        # Normalize: strip leading/trailing slashes, collapse multiple slashes
        parts = [p for p in path.split('/') if p]
        return '/'.join(parts)
    
    def get_mount_names(self) -> list[str]:
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
    
    def has_mount(self, name: str) -> bool:
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
        mount_names = ', '.join(self._mounts.keys()) if self._mounts else 'none'
        return f"StorageManager(mounts=[{mount_names}])"
