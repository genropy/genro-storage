API Reference
=============

This page provides the complete API documentation for genro-storage.

StorageManager
--------------

.. autoclass:: genro_storage.StorageManager
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __repr__

StorageNode
-----------

.. autoclass:: genro_storage.StorageNode
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __repr__, __str__, __truediv__

Exceptions
----------

.. automodule:: genro_storage.exceptions
   :members:
   :undoc-members:
   :show-inheritance:

Backend Classes
---------------

Base Backend
~~~~~~~~~~~~

.. autoclass:: genro_storage.backends.StorageBackend
   :members:
   :undoc-members:
   :show-inheritance:

Local Storage
~~~~~~~~~~~~~

.. autoclass:: genro_storage.backends.LocalStorage
   :members:
   :undoc-members:
   :show-inheritance:
   :special-members: __init__, __repr__
