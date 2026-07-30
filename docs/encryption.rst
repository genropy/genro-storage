At-Rest Encryption
==================

A mount can be declared ``encrypted``: bytes are encrypted before they reach
the backend and decrypted on the way back, so the files on the medium are
ciphertext while callers keep reading and writing plaintext through the
normal node API.

Installation
------------

Encryption relies on the ``cryptography`` package, shipped as an optional
extra:

.. code-block:: bash

   pip install genro-storage[encryption]

Nothing else changes for installations that do not use encryption: with no
encrypted mount the cipher is never built and the package is never imported.
Declaring an encrypted mount *without* the package raises a
``StorageConfigError`` with the install hint.

Enabling encryption
-------------------

Two ingredients: the ``encrypted`` flag on the mount, and the key material
(``storage_key``) on the manager.

.. code-block:: python

   import os

   from genro_storage import StorageManager

   storage = StorageManager()
   storage.configure(
       [
           {'name': 'home', 'protocol': 'local', 'base_path': '/srv/data'},
           {'name': 'secure', 'protocol': 'local', 'base_path': '/srv/secure',
            'encrypted': True},
       ],
       storage_key=os.environ['STORAGE_KEY'],
   )

   node = storage.node('secure:token.json')
   node.write_text(payload)          # ciphertext on disk
   node.read_text()                  # plaintext to the caller

The same two ingredients in a builder recipe (see :doc:`configuration` for
the grammar):

.. code-block:: python

   import os

   from genro_bag.resolver import BagCbResolver
   from genro_storage import StorageConfig

   class MyConfig(StorageConfig):
       def main(self, root):
           m = root.mounts(storage_key=BagCbResolver(lambda: os.environ['STORAGE_KEY']))
           m.local(name='home', base_path='/srv/data')
           m.local(name='secure', base_path='/srv/secure', encrypted=True)

Keys never live in the recipe: ``storage_key`` accepts a ``BagResolver``, so
the recipe states *where the key comes from* and the value is read from the
environment at configuration time. Key material can also be installed later
with ``StorageManager.set_encryption_keys(key_material)``.

Key material and rotation
-------------------------

The key material is one or more comma-separated `Fernet
<https://cryptography.io/en/latest/fernet/>`_ keys, wrapped in a
``MultiFernet``: the **first** key encrypts, **all** keys decrypt. Rotation is
therefore a configuration change:

1. prepend the new key: ``"<new-key>,<old-key>"`` — new content is written
   with the new key, old content still reads with the old one;
2. re-write the content you want migrated (a read/write pass);
3. drop the old key once nothing depends on it.

Generate a key with:

.. code-block:: python

   from cryptography.fernet import Fernet
   Fernet.generate_key().decode()

The manager never exposes the installed keys; ``encryption_active`` reports
whether key material is installed, ``mount_is_encrypted(name)`` whether a
given mount encrypts at rest.

Relative mounts
---------------

A ``relative`` mount inherits the flag from its parent: the stored bytes are
the parent's, so reads and writes through the child are transparent on the
same terms.

.. code-block:: python

   storage.configure([
       {'name': 'secure', 'protocol': 'local', 'base_path': '/srv/secure',
        'encrypted': True},
       {'name': 'inbox', 'path': 'secure:inbox'},     # encrypted too
   ], storage_key=key)

Failure behaviour
-----------------

There is no silent degradation:

- an encrypted mount with **no key installed** is *dormant* — reading or
  writing it raises ``StorageError`` at runtime, while configuration
  succeeds;
- key material that **resolves empty** is a ``StorageConfigError`` at
  configuration time;
- a payload **no installed key can decrypt** raises
  ``cryptography.fernet.InvalidToken`` rather than returning ciphertext.

Coverage boundary
-----------------

Encryption covers the node read/write surface: ``read_bytes`` /
``write_bytes`` and the text wrappers. Paths that hand out the stored bytes
directly bypass the cipher and carry the at-rest bytes untouched:

- ``open()`` — returns the backend's file handle;
- ``local_path()`` — and ``call()`` / ``serve()``, which are built on it;
- ``copy_to()`` / ``move_to()`` — relocate the stored bytes as they are, so
  a copy or move is valid across **same-encryption** mounts only: encrypted
  → plain delivers ciphertext, plain → encrypted stores bytes the mount
  cannot decrypt.

Fernet is a whole-payload scheme: content is encrypted and decrypted in
memory, which is the right trade-off for configuration files, tokens and
documents. Very large files on encrypted mounts pay that memory cost.
