Using genro-storage From Async Code
====================================

The API is synchronous. This page explains what that means for an async caller,
and how to do it well.

.. contents:: Table of Contents
   :local:
   :depth: 2

The Contract
------------

Every I/O method on ``StorageNode`` and ``StorageManager`` is **synchronous and
blocking**: it performs the operation and returns the value. There is no dual
mode, no context detection, and no method whose return type depends on its
caller.

.. code-block:: python

    node = storage.node('home:file.txt')

    if node.exists():           # returns bool
        content = node.read()   # returns str

That holds identically inside an event loop — which is exactly the point. A call
from a coroutine **blocks the loop** until the I/O finishes, so an async caller
has to offload it.

Offloading to a Thread
----------------------

Use :func:`asyncio.to_thread`. Storage work is I/O-bound, so threads are the
right tool and the GIL is not a bottleneck:

.. code-block:: python

    import asyncio

    async def load_report():
        node = storage.node('uploads:reports/q4.pdf')
        return await asyncio.to_thread(node.read_bytes)

Arguments are passed straight through, so a write is just as direct:

.. code-block:: python

    await asyncio.to_thread(node.write_bytes, payload)
    await asyncio.to_thread(source.copy_to, destination)

Where you want to control the pool yourself, use an explicit executor:

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor

    pool = ThreadPoolExecutor(max_workers=8)
    data = await asyncio.get_running_loop().run_in_executor(pool, node.read_bytes)

Running Operations in Parallel
------------------------------

Because each call is an ordinary function, ``asyncio.gather`` composes them
without any special support from this library:

.. code-block:: python

    async def read_all(nodes):
        return await asyncio.gather(
            *(asyncio.to_thread(node.read_bytes) for node in nodes)
        )

For a large batch, bound the concurrency rather than launching one thread per
file:

.. code-block:: python

    async def read_all(nodes, limit=8):
        semaphore = asyncio.Semaphore(limit)

        async def read_one(node):
            async with semaphore:
                return await asyncio.to_thread(node.read_bytes)

        return await asyncio.gather(*(read_one(node) for node in nodes))

Web Frameworks
--------------

In FastAPI and Starlette, a handler declared with ``def`` (not ``async def``) is
already run in a threadpool by the framework. Storage calls inside it need no
wrapping:

.. code-block:: python

    from fastapi import FastAPI, HTTPException
    from genro_storage import StorageManager

    app = FastAPI()

    storage = StorageManager()
    storage.configure([
        {'name': 'uploads', 'protocol': 's3', 'bucket': 'my-bucket'}
    ])

    @app.get("/files/{filepath:path}")
    def get_file(filepath: str):          # note: def, not async def
        node = storage.node(f'uploads:{filepath}')

        if not node.exists():
            raise HTTPException(status_code=404, detail="File not found")

        return {"data": node.read_bytes(), "size": node.size()}

Inside an ``async def`` handler, offload as shown above.

Why the API Is Not Async
------------------------

A library that changes behaviour based on its calling context takes away the
application's ability to decide *where* blocking work runs — and in a server,
that decision belongs to the server. Making it explicit costs one
``asyncio.to_thread`` and hands the caller back the choice of executor, pool
size and back-pressure.

This is also the contract genro-asgi ratified for storage (its
``SPECIFICATION.md``, D22), and the direction recorded for this package in
issue #67.

Migrating From Earlier Versions
-------------------------------

Up to 0.7, I/O methods carried a ``@smartasync`` decorator: awaiting them inside
an event loop worked, and calling them without ``await`` worked too. The
decorator is gone. If your code awaited a node method, wrap the call instead:

.. code-block:: python

    # before
    data = await node.read_bytes()

    # after
    data = await asyncio.to_thread(node.read_bytes)

Synchronous call sites are unaffected — they were already doing the right thing.
``AsyncStorageManager``, removed earlier, has no replacement: there is one
manager, and it is this one.

``call(..., async_mode=True)`` is unrelated and unchanged: it is an explicit
opt-in that runs an external tool in a background thread, not a behaviour that
varies with the caller.

Next Steps
----------

* See :doc:`/quickstart` for basic usage
* Check :doc:`/backends` for storage configuration
* Read :doc:`copy-strategies` for efficient sync
* Explore :doc:`/examples` for more patterns
