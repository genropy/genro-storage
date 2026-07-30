At-Rest Encryption
==================

Encryption is a property of the **file**, not of the mount. A write declares
``encrypted=``; what lands on the medium is a self-describing envelope, and a
read needs no declaration — the file says what it is. Encrypted and plain files
coexist in the same directory, and an encrypted file that is copied elsewhere
stays readable through the library.

Installation
------------

Encryption relies on the ``cryptography`` package, shipped as an optional
extra:

.. code-block:: bash

   pip install genro-storage[encryption]

Nothing else changes for installations that do not use encryption: with no key
material no cipher is ever built and the package is never imported. Declaring
a ``default_encrypted`` mount or a ``storage_key`` *without* the package raises
a ``StorageConfigError`` with the install hint.

The envelope
------------

An encrypted payload is a first line naming the format and the encoding domain,
then the `Fernet <https://cryptography.io/en/latest/fernet/>`_ token:

.. code-block:: text

   #GNRE1:acmespa
   gAAAAABo...token...

The whole file stays ASCII. The default (unnamed) domain renders ``#GNRE1:``
with nothing after the colon. Header parsing is bounded — first line only, at
most 128 bytes — so a file that does not start with one is simply not
encrypted, at no measurable cost.

Two caveats about the header, both by design:

- it is **not authenticated**: Fernet's HMAC covers the token, not the line
  above it. Tampering with the domain misroutes the key lookup and decryption
  fails loudly; it cannot yield wrong plaintext;
- the domain travels **in cleartext**. It is routing metadata, never a security
  boundary — do not put a secret in a domain name.

Encoding domains
----------------

A domain groups the keys that encrypt and decrypt one class of content — one
tenant, one partner, one category of secret. Names use ``[a-z0-9_-]``, up to 64
characters; anything else is a ``StorageConfigError``. The empty name is the
default domain, which is what the pre-0.8 unqualified syntax produces.

What domains buy: content encrypted for one tenant cannot be read by another
tenant's keys even inside the same mount, and keys rotate per domain rather
than for the whole installation.

Key material and rotation
-------------------------

The key material is one or more comma-separated Fernet keys, each optionally
prefixed with ``<domain>:``:

.. code-block:: text

   acmespa:<key-1>,acmespa:<key-2>,partner:<key-3>

The split is on the **first** colon, which is unambiguous: Fernet keys are
base64url and never contain one. An unprefixed key belongs to the default
domain, so today's plain ``"<key>"`` and ``"<new>,<old>"`` forms keep working.
The domain of the **first** entry overall becomes the default write domain —
what ``encrypted=True`` uses.

Keys of one domain are wrapped in a single ``MultiFernet``: the **first** key of
a domain encrypts, **all** of them decrypt. Rotation is therefore per domain and
is a configuration change:

1. prepend the new key: ``"acme:<new>,acme:<old>"`` — new content is written
   with the new key, old content still reads with the old one;
2. re-write the content you want migrated (a read/write pass);
3. drop the old key once nothing depends on it.

Generate a key with:

.. code-block:: python

   from cryptography.fernet import Fernet
   Fernet.generate_key().decode()

The manager never exposes the installed keys: ``encryption_active`` reports
whether any are installed, ``encryption_domains`` lists the configured domain
names.

Writing
-------

``write_bytes``, ``write_text`` and the generic ``write()`` take ``encrypted``:

.. code-block:: python

   import os

   from genro_storage import StorageManager

   storage = StorageManager()
   storage.configure(
       [{'name': 'secure', 'protocol': 'local', 'base_path': '/srv/secure'}],
       storage_key=os.environ['STORAGE_KEY'],
   )

   node = storage.node('secure:token.json')
   node.write_text(payload, encrypted=True)        # default domain
   node.write_text(payload, encrypted='acmespa')   # explicit domain
   node.write_text(payload)                        # plain, unless the mount defaults otherwise

   node.read_text()                                # plaintext, no declaration needed

- ``encrypted=True`` — encrypt for the default write domain;
- ``encrypted='<domain>'`` — encrypt for that domain;
- ``encrypted=False`` — write plaintext, whatever the mount's default;
- omitted — the mount's ``default_encrypted``, and ``False`` when it has none.

Mount defaults
--------------

A mount can declare ``default_encrypted`` — exactly what its name says, the
default of the write parameter on that mount:

.. code-block:: python

   storage.configure(
       [
           {'name': 'home', 'protocol': 'local', 'base_path': '/srv/data'},
           {'name': 'secure', 'protocol': 'local', 'base_path': '/srv/secure',
            'default_encrypted': True},
           {'name': 'inbox', 'path': 'secure:inbox'},   # inherits the default
       ],
       storage_key=os.environ['STORAGE_KEY'],
   )

   storage.node('secure:a.json').write_text(payload)                   # encrypted
   storage.node('secure:b.json').write_text(payload, encrypted=False)  # plain

It takes the same values as the write parameter, so ``default_encrypted='acmespa'``
defaults that mount's writes to the ``acmespa`` domain. The default belongs to
the mount named in the write and to it alone: a ``relative`` mount has one only
if it declares one — the parent's does not leak through. Files written through
different mounts onto the same directory stay individually readable either way:
the header answers per file. ``StorageManager.mount_default_encrypted(name)``
reports the declared value.

The same in a builder recipe (see :doc:`configuration` for the grammar):

.. code-block:: python

   import os

   from genro_bag.resolver import BagCbResolver
   from genro_storage import StorageConfig

   class MyConfig(StorageConfig):
       def main(self, root):
           m = root.mounts(storage_key=BagCbResolver(lambda: os.environ['STORAGE_KEY']))
           m.local(name='home', base_path='/srv/data')
           m.local(name='secure', base_path='/srv/secure', default_encrypted=True)

Keys never live in the recipe: ``storage_key`` accepts a ``BagResolver``, so
the recipe states *where the key comes from* and the value is read from the
environment at configuration time. Key material can also be installed later
with ``StorageManager.set_encryption_keys(key_material)``.

Reading
-------

Reads are deterministic and have two cases only:

- the stored bytes **start with a header** → decrypt through that domain's
  keyring;
- they **do not** → return them untouched.

There is no content sniffing and no legacy bare-token path: content written by
0.7.x, which carried no header, reads back as ciphertext bytes. Re-write it
through 0.8 to bring it into the envelope.

Failure behaviour
-----------------

There is no silent degradation:

- encrypting or decrypting for a domain with **no installed keys** raises
  ``StorageError`` naming that domain — a mount with ``default_encrypted`` and
  no key configured is *dormant*: configuration succeeds, the write fails;
- key material that **resolves empty** is a ``StorageConfigError`` at
  configuration time;
- an invalid domain, on key material or on a write, is a ``StorageConfigError``;
- a payload **no installed key can decrypt** raises
  ``cryptography.fernet.InvalidToken`` rather than returning ciphertext.

Coverage boundary
-----------------

Encryption covers the node read/write surface: ``read_bytes`` /
``write_bytes`` and the text wrappers. Paths that hand out the stored bytes
directly deliver the envelope as it is:

- ``open()`` — returns the backend's file handle;
- ``local_path()`` — and ``call()`` / ``serve()``, which are built on it;
- ``copy_to()`` / ``move_to()`` — relocate the stored bytes verbatim, so the
  envelope travels with the file. A copy to any mount stays readable through
  the library, and copying a plain file onto a ``default_encrypted`` mount
  leaves it plain and readable;
- **versioned reads** — ``open()`` / ``read_bytes()`` with a ``version`` go
  through the backend snapshot and return the envelope, not the plaintext;
- ``size()`` and ``md5hash()`` — report on the stored envelope, not on the
  content inside it.

Fernet is a whole-payload scheme: content is encrypted and decrypted in
memory, which is the right trade-off for configuration files, tokens and
documents. Very large encrypted files pay that memory cost.
