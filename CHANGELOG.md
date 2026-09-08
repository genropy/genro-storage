# Changelog

## 0.8.1 — 2026-09-08

- Fetch StorageNode attributes through one backend metadata snapshot. On S3,
  uncached file attributes now require one HEAD request instead of four.
- Return no fabricated modification timestamp for implicit S3 directories in
  `ext_attributes`, matching the legacy tuple. The separate `mtime()` method
  keeps its previous behavior.
- Preserve compatibility with other backends through a default implementation,
  and delegate snapshots through relative mounts without losing path scoping.
- Add real legacy/current S3 contract tests, metadata regression tests, a local
  MinIO/remote S3 benchmark harness, and portable HTML comparison reports.
- Make pytest import this checkout's source instead of an installed distribution.

Local exploratory measurements for file attributes improved from 6.70 ms to
1.52 ms; legacy measured 3.27 ms in the final comparison. These measurements
are workload-specific and do not establish production or remote S3 performance.
Copy and move paths are unchanged.

See [previous releases](https://github.com/genropy/genro-storage/releases)
for earlier release notes.
