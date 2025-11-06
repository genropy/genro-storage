# Refactoring Snapshot - Integrazione Smartswitch
**Data**: 2025-11-06
**Branch**: `new-architecture-async`
**Stato**: In corso - Registry refactorato, Provider da completare

## Obiettivo

Integrare smartswitch in genro-storage per sostituire le catene if/elif (250 linee) con dispatch intelligente basato su provider pattern.

## Architettura Concordata

### 1. Provider Pattern

Ogni provider è un modulo in `genro_storage/providers/` con:
- **Classe `Provider`** (stesso nome in tutti i moduli)
- **Attributo di classe `proto`**: `proto = Switcher(prefix='protocol_')`
- **Metodi `protocol_*`**: Decorati con `@proto`, auto-registrati

Esempio:
```python
# genro_storage/providers/fsspec.py
from smartswitch import Switcher

class Provider:
    proto = Switcher(prefix='protocol_')  # Attributo di classe

    @proto  # Auto-registered as 's3_aws' (rimuove 'protocol_')
    def protocol_s3_aws(self, protocol_name: str) -> dict[str, Any]:
        """Amazon S3 protocol."""
        return {
            "model": S3AwsModel,
            "implementor": S3AwsImplementor,
            "capabilities": {...}
        }
```

### 2. ProviderRegistry

**Oggetto secondario** istanziato da StorageManager.

Classe che:
1. **`__init__`**: Chiama `load_providers()`
2. **`load_providers()`**: Scansiona `providers/`, importa moduli, istanzia `Provider` classes
3. **`add_provider(name, instance)`**: Aggiunge provider a `self.providers = {}`
4. **`del_provider(name)`**: Rimuove provider
5. **`get_protocol(protocol_name)`**: Cerca in tutti i provider e chiama `provider.proto(protocol_name)`
6. **`list_protocols()`**: Lista tutti i protocolli da tutti i provider

**Caratteristiche chiave:**
- `self.providers = {}` - dizionario `nome_modulo -> istanza Provider`
- Ogni modulo in `providers/` deve avere una classe `Provider` (stesso nome per tutti)
- No confusione nomi perché sono moduli diversi (`fsspec.Provider`, `custom.Provider`, etc.)
- Auto-discovery: carica automaticamente tutti i moduli provider all'init

Uso:
```python
registry = ProviderRegistry()  # Auto-loads all providers

# Access provider
fsspec = registry.providers['fsspec']

# List protocols from fsspec
protocols = fsspec.proto._spells.keys()

# Get protocol config
config = registry.get_protocol('s3_aws')
# oppure direttamente:
config = fsspec.proto('s3_aws')
```

### 3. StorageManager - Oggetto Primario

**StorageManager è l'oggetto primario** che coordina tutto.

**Responsabilità:**
- Istanzia `ProviderRegistry` nel suo `__init__`
- Usa il registry per ottenere configurazioni di protocollo
- Sostituisce le catene if/elif con chiamate al registry

**Flusso:**
1. User crea: `storage = StorageManager()`
2. StorageManager `__init__`:
   ```python
   def __init__(self):
       self.registry = ProviderRegistry()  # Istanzia e carica tutti i provider
       self._mounts = {}
   ```
3. Registry auto-carica tutti i provider (fsspec, custom, etc.)
4. Ogni Provider registra i suoi protocolli nello switcher
5. Quando user fa `storage.configure([...])`, il manager usa `registry.get_protocol()`

**Gerarchia degli oggetti:**
```
StorageManager (oggetto primario)
  └── ProviderRegistry (istanziato da StorageManager)
       ├── providers['fsspec'] → istanza di fsspec.Provider
       │    └── proto = Switcher()  (attributo di classe)
       │         ├── protocol_s3_aws
       │         ├── protocol_gcs
       │         └── ...
       ├── providers['custom'] → istanza di custom.Provider
       │    └── proto = Switcher()
       │         └── protocol_custom1
       └── ...
```

### 4. Integration nel Manager

Nel `manager.py`, sostituire 250 linee if/elif con:
```python
def _configure_standard_mount(self, mount_name: str, config: dict):
    backend_type = config["type"]

    # Get protocol config via registry
    protocol_config = self.registry.get_protocol(backend_type)

    Model = protocol_config['model']
    Implementor = protocol_config['implementor']

    # Validate with Pydantic
    validated = Model(**config)

    # Create backend
    backend = Implementor(validated)

    # Apply permissions
    if "permissions" in config:
        backend = self._apply_permissions(mount_name, backend, config["permissions"])

    self._mounts[mount_name] = backend
```

## Progressi Completati

### ✅ 1. Dependencies
- Aggiunto `smartswitch>=0.1.0` a `pyproject.toml`

### ✅ 2. ProviderRegistry Refactorato
File: `genro_storage/providers/registry.py`

Completamente riscritto con:
- `__init__()` chiama `load_providers()`
- `load_providers()` scansiona e carica tutti i provider
- `add_provider()`, `del_provider()`, `get_protocol()`, `list_protocols()`
- Auto-discovery dei moduli provider

### ✅ 3. File Rinominato
- `fsspec_provider.py` → `fsspec.py` (convenzione: nome modulo = nome provider)

## TODO - Prossimi Passi

### 🔄 4. Refactorare Provider Class (IN CORSO)

File: `genro_storage/providers/fsspec.py`

**Modifiche necessarie:**

1. **Rinominare classe**: `FsspecProvider` → `Provider`
2. **Aggiungere attributo di classe**:
   ```python
   class Provider:
       proto = Switcher(prefix='protocol_')
   ```
3. **Cambiare decoratori**: `@AsyncProvider.protocol("s3_aws")` → `@proto`
4. **Rimuovere registrazione manuale** nel vecchio registry

**Pattern da seguire:**
```python
# PRIMA (vecchio)
class FsspecProvider(AsyncProvider):
    @AsyncProvider.protocol("s3_aws")
    def protocol_s3_aws(self) -> dict[str, Any]:
        class S3AwsModel(BaseModel):
            ...
        return {"model": S3AwsModel, "implementor": S3AwsImplementor}

# DOPO (nuovo)
class Provider:
    proto = Switcher(prefix='protocol_')

    @proto
    def protocol_s3_aws(self, protocol_name: str) -> dict[str, Any]:
        class S3AwsModel(BaseModel):
            ...
        return {"model": S3AwsModel, "implementor": S3AwsImplementor}
```

### ⏳ 5. Refactorare Altri Provider

File: `genro_storage/providers/custom_provider.py`

Stesso processo:
- Rinominare a `custom.py`
- Classe → `Provider`
- Attributo di classe `proto = Switcher(prefix='protocol_')`
- Decoratori `@proto`

### ⏳ 6. Connettere manager.py

File: `genro_storage/manager.py`

**Modifiche:**
1. Importare `ProviderRegistry`
2. Nell'`__init__`: `self.registry = ProviderRegistry()`
3. Sostituire catene if/elif (linee 349-600) con chiamate a `self.registry.get_protocol()`

### ⏳ 7. Testing

1. Test caricamento provider: `registry.providers` contiene 'fsspec', 'custom', etc.
2. Test listing protocolli: `registry.list_protocols()` ritorna tutti i protocolli
3. Test get_protocol: `registry.get_protocol('s3_aws')` ritorna dict corretto
4. Test manager integration: mount configuration funziona
5. Run full test suite

### ⏳ 8. Commit

Commit message:
```
refactor: Integrate smartswitch for provider dispatch

Replace 250-line if/elif chains with smartswitch-based provider pattern.

- Add smartswitch dependency
- Refactor ProviderRegistry with auto-loading
- Update Provider classes to use @proto decorator
- Connect manager.py to use registry

Benefits:
- Cleaner code (250 lines → ~50 lines in manager)
- Plugin system (external packages can add providers)
- Auto-discovery of protocols
- Better testability

Resolves #53
Related to #50 (long functions), #51 (complexity)
```

## File Modificati Finora

```
M pyproject.toml                          # Added smartswitch dependency
M genro_storage/providers/registry.py     # Completely refactored
R genro_storage/providers/fsspec_provider.py → fsspec.py  # Renamed (da completare refactor)
```

## Branch e Git Status

**Branch corrente**: `new-architecture-async`

**Modifiche staged/unstaged da prima**:
- `genro_storage/__init__.py` - async native imports
- `pyproject.toml` - asyncer rimosso + smartswitch aggiunto
- `genro_storage/asyncer_wrapper.py` - deleted
- `tests/test_asyncer_wrapper.py` - deleted

**Note**: Queste modifiche async erano state fatte su main, portate su new-architecture-async con checkout.

## Issue GitHub Correlati

- **#53** - Add smartswitch integration (questo refactoring)
- **#50** - Refactor long functions (risolto parzialmente da #53)
- **#51** - Reduce cyclomatic complexity (risolto parzialmente da #53)
- **#52** - Reduce sync/async duplication
- **#54** - Thread safety

## Principi Genro-Libs

- **"Eat Your Own Dog Food"**: Usiamo smartswitch (nostro tool) in genro-storage
- **Dependencies tra tool**: È OK dipendere da smartswitch (stessa famiglia)
- **Feedback loop**: Problemi trovati migliorano smartswitch

## Naming Convention Smartswitch

**Con `prefix='protocol_'`**:

```python
proto = Switcher(prefix='protocol_')

@proto  # No parametri!
def protocol_s3_aws(...):
    pass

# Smartswitch fa automaticamente:
# 1. Vede nome funzione: protocol_s3_aws
# 2. Rimuove prefix: protocol_
# 3. Registra come: s3_aws

# Chiamata:
result = proto('s3_aws')  # Trova e chiama protocol_s3_aws
```

## Test Rapidi

```python
# Test 1: Registry loads providers
from genro_storage.providers.registry import ProviderRegistry
registry = ProviderRegistry()
print(registry.providers.keys())  # Should show: dict_keys(['fsspec', 'custom', ...])

# Test 2: List protocols
print(registry.list_protocols())  # Should show all protocols

# Test 3: Get specific protocol
config = registry.get_protocol('s3_aws')
print(config.keys())  # Should show: dict_keys(['model', 'implementor', ...])

# Test 4: Direct provider access
fsspec = registry.providers['fsspec']
print(fsspec.proto._spells.keys())  # Show fsspec protocols
```

## Note Importanti

1. **Non fare refactoring a pioggia**: Completare un file alla volta
2. **Testing incrementale**: Testare dopo ogni modifica importante
3. **Manteneresi allineati**: Verificare architettura prima di continuare
4. **File Provider**: Ogni modulo deve avere classe `Provider` (stesso nome)
5. **Attributo di classe**: `proto` deve essere attributo di classe, non di istanza

## Prossima Azione

Continuare il refactoring di `genro_storage/providers/fsspec.py`:
1. Classe `FsspecProvider` → `Provider`
2. Aggiungere `proto = Switcher(prefix='protocol_')` come attributo di classe
3. Cambiare tutti i decoratori `@AsyncProvider.protocol(...)` → `@proto`
4. Testare che i protocolli si registrino correttamente

---
**Per riprendere**: Leggi questo file, verifica lo stato del branch, continua dal punto 4 (Refactorare Provider Class).
