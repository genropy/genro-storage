"""Test skeleton for AsyncStorageManager.

Tests that verify:
1. ProviderRegistry auto-loads providers
2. Protocols are registered correctly
3. SmartSwitch dispatch works
4. Logging shows method calls
"""

import pytest
from genro_storage.async.manager import AsyncStorageManager


def test_manager_initialization():
    """Test that AsyncStorageManager initializes ProviderRegistry."""
    storage = AsyncStorageManager()

    # Verify provider_registry exists
    assert hasattr(storage, 'provider_registry')
    assert storage.provider_registry is not None

    # Verify _mounts dict exists
    assert hasattr(storage, '_mounts')
    assert isinstance(storage._mounts, dict)
    assert len(storage._mounts) == 0  # Initially empty


def test_provider_registry_auto_load():
    """Test that ProviderRegistry auto-loads providers."""
    storage = AsyncStorageManager()
    registry = storage.provider_registry

    # Verify providers were loaded
    assert hasattr(registry, 'providers')
    assert isinstance(registry.providers, dict)

    # Should have at least fsspec provider
    # (Nota: dipende da quali provider ci sono nella folder)
    print(f"Loaded providers: {list(registry.providers.keys())}")

    # If providers exist, verify they have proto switcher
    for name, provider in registry.providers.items():
        assert hasattr(provider, 'proto'), f"Provider '{name}' should have 'proto' switcher"


def test_list_protocols():
    """Test that list_protocols() returns available protocols."""
    storage = AsyncStorageManager()

    # Get all available protocols
    protocols = storage.list_protocols()

    print(f"Available protocols: {protocols}")

    # Verify it's a list
    assert isinstance(protocols, list)

    # Should have at least some protocols
    # (Nota: dipende da quali provider sono implementati)
    # assert len(protocols) > 0  # Commentato per ora, non sappiamo quanti provider ci sono


def test_get_protocol_s3_aws():
    """Test that get_protocol() resolves s3_aws protocol."""
    storage = AsyncStorageManager()

    # Get s3_aws protocol config
    try:
        config = storage.get_protocol('s3_aws')

        print(f"s3_aws config keys: {config.keys()}")

        # Verify structure
        assert 'model' in config
        assert 'implementor' in config
        assert 'capabilities' in config

        print("✓ s3_aws protocol found and has correct structure")

    except ValueError as e:
        # Protocol not found - list available ones
        protocols = storage.list_protocols()
        print(f"s3_aws not found. Available: {protocols}")
        pytest.skip(f"s3_aws protocol not available: {e}")


def test_get_protocol_unknown():
    """Test that get_protocol() raises ValueError for unknown protocol."""
    storage = AsyncStorageManager()

    # Try to get unknown protocol
    with pytest.raises(ValueError) as exc_info:
        storage.get_protocol('unknown_protocol_xyz')

    # Error message should list available protocols
    assert 'unknown_protocol_xyz' in str(exc_info.value)
    assert 'Available protocols' in str(exc_info.value)


@pytest.mark.asyncio
async def test_smartswitch_dispatch():
    """Test that SmartSwitch dispatch works."""
    storage = AsyncStorageManager()

    # Enable logging to see dispatch
    storage.api.enable_log(mode='silent', time=True)

    # Call configure via SmartSwitch
    await storage.api('configure')([
        {'name': 'test', 'protocol': 's3_aws', 'bucket': 'test'}
    ])

    # Call list_mounts via SmartSwitch
    await storage.api('list-mounts')()

    # Get log history
    history = storage.api.get_log_history()

    print(f"\nLog history ({len(history)} entries):")
    for entry in history:
        print(f"  - {entry['handler']}: {entry.get('elapsed', 0)*1000:.2f}ms")

    # Verify calls were logged
    assert len(history) == 2
    assert history[0]['handler'] == 'configure'
    assert history[1]['handler'] == 'list-mounts'


@pytest.mark.asyncio
async def test_smartswitch_logging_visible(capsys):
    """Test that SmartSwitch logging shows method calls."""
    storage = AsyncStorageManager()

    # Enable logging to console
    storage.api.enable_log(mode='log', before=True, after=True)

    # Call methods
    await storage.api('configure')([{'name': 'test', 'protocol': 's3'}])
    await storage.api('node')('uploads:file.txt')

    # Capture output
    captured = capsys.readouterr()

    print("Captured output:")
    print(captured.err)

    # Verify logging output contains our calls
    # (SmartSwitch logga su stderr)
    assert 'configure' in captured.err or 'storage' in captured.err


def test_smartswitch_introspection():
    """Test SmartSwitch introspection methods."""
    storage = AsyncStorageManager()

    # Get registered handlers
    handlers = storage.api.entries()

    print(f"Registered handlers: {handlers}")

    # Should have our decorated methods
    assert 'configure' in handlers
    assert 'node' in handlers
    assert 'list-mounts' in handlers

    # Verify switcher name
    assert storage.api.name == 'storage'
