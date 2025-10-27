Advanced Features
=================

This guide covers advanced features of genro-storage that go beyond basic file operations.

External Tool Integration
--------------------------

The Problem
~~~~~~~~~~~

Many workflows require external tools (ffmpeg, imagemagick, pandoc, etc.) that:

1. Only work with local filesystem paths
2. Require temporary file management
3. Need upload after processing

**Naive approach:**

.. code-block:: python

    # ❌ Lots of boilerplate
    import tempfile
    import subprocess

    # Download from S3
    s3_node = storage.node('s3:video.mp4')
    local_temp = tempfile.mktemp(suffix='.mp4')
    with open(local_temp, 'wb') as f:
        f.write(s3_node.read_bytes())

    # Process
    output_temp = tempfile.mktemp(suffix='.mp4')
    subprocess.run(['ffmpeg', '-i', local_temp, output_temp])

    # Upload back
    output_node = storage.node('s3:processed.mp4')
    with open(output_temp, 'rb') as f:
        output_node.write_bytes(f.read())

    # Cleanup
    os.unlink(local_temp)
    os.unlink(output_temp)

The ``call()`` Method
~~~~~~~~~~~~~~~~~~~~~~

``call()`` handles all temporary file management automatically:

.. code-block:: python

    # ✅ Clean and automatic
    video = storage.node('s3:video.mp4')
    output = storage.node('s3:processed.mp4')

    video.call(
        'ffmpeg -i {input} -vcodec h264 -crf 28 {output}',
        input=video,
        output=output
    )

**How it works:**

1. Downloads ``input`` file(s) to temporary local paths
2. Substitutes ``{input}`` and ``{output}`` with temp paths
3. Runs the command via subprocess
4. Uploads ``output`` file(s) back to original storage
5. Cleans up temporary files automatically

**Method signature:**

.. code-block:: python

    def call(
        self,
        command: str | list[str],
        *,
        shell: bool = False,
        check: bool = True,
        timeout: int | None = None,
        **path_kwargs: StorageNode | str
    ) -> subprocess.CompletedProcess

**Parameters:**

- ``command``: Command string with ``{placeholders}`` or list of args
- ``shell``: If True, run command through shell (security risk!)
- ``check``: If True, raise exception on non-zero exit code
- ``timeout``: Maximum seconds to wait
- ``**path_kwargs``: StorageNode or string paths to substitute

Advanced call() Examples
~~~~~~~~~~~~~~~~~~~~~~~~~

**Multiple inputs/outputs:**

.. code-block:: python

    # Merge videos
    video1 = storage.node('s3:part1.mp4')
    video2 = storage.node('s3:part2.mp4')
    merged = storage.node('s3:full.mp4')

    video1.call(
        'ffmpeg -i {v1} -i {v2} -filter_complex "[0:v][1:v]concat=n=2:v=1[v]" '
        '-map "[v]" {out}',
        v1=video1,
        v2=video2,
        out=merged
    )

**Image processing:**

.. code-block:: python

    # Create thumbnail with ImageMagick
    photo = storage.node('uploads:photo.jpg')
    thumb = storage.node('uploads:thumb.jpg')

    photo.call(
        ['convert', '{input}', '-resize', '200x200', '-quality', '85', '{output}'],
        input=photo,
        output=thumb
    )

**Document conversion:**

.. code-block:: python

    # Convert markdown to PDF with pandoc
    doc = storage.node('docs:report.md')
    pdf = storage.node('docs:report.pdf')

    doc.call(
        'pandoc {input} -o {output} --pdf-engine=xelatex',
        input=doc,
        output=pdf,
        timeout=60  # 60 seconds max
    )

**Error handling:**

.. code-block:: python

    try:
        result = video.call(
            'ffmpeg -i {input} {output}',
            input=video,
            output=output,
            check=True  # Raises on failure
        )
        print(f"Success! Exit code: {result.returncode}")
    except subprocess.CalledProcessError as e:
        print(f"Command failed: {e.stderr}")

The ``local_path()`` Context Manager
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For more complex tool integration, use ``local_path()`` directly:

.. code-block:: python

    video = storage.node('s3:video.mp4')

    # Read mode: download for processing
    with video.local_path(mode='r') as input_path:
        # input_path is a local Path object
        subprocess.run(['ffprobe', input_path])

    # Write mode: upload after creation
    output = storage.node('s3:output.mp4')
    with output.local_path(mode='w') as output_path:
        subprocess.run(['ffmpeg', ..., output_path])
        # Automatically uploaded on context exit

    # Read-write mode: download, modify, re-upload
    with video.local_path(mode='rw') as path:
        # Modify file in place
        subprocess.run(['some-tool', path])
        # Changes uploaded automatically

**Mode options:**

- ``'r'``: Read-only (downloads file, read-only temp)
- ``'w'``: Write-only (creates temp, uploads on exit)
- ``'rw'``: Read-write (downloads, allows modification, re-uploads)

**When to use local_path() vs call():**

- Use ``call()`` for simple command substitution
- Use ``local_path()`` when you need:
  - Multiple commands on same file
  - Python code between commands
  - Complex control flow
  - Access to Path object for inspection

Web Framework Integration
--------------------------

The Problem
~~~~~~~~~~~

Serving files from cloud storage through web apps typically requires:

1. Generating signed URLs (S3 presigned, etc.)
2. HTTP redirects
3. Bandwidth costs (direct from cloud)

Or:

1. Download file to app server
2. Stream through app
3. Memory management

The ``serve()`` Method
~~~~~~~~~~~~~~~~~~~~~~

``serve()`` efficiently streams files through WSGI-compatible frameworks:

.. code-block:: python

    # Flask example
    from flask import Flask
    app = Flask(__name__)

    @app.route('/documents/<path:filename>')
    def serve_document(filename):
        doc = storage.node(f'docs:{filename}')
        return doc.serve(
            mimetype='auto',  # Auto-detect from extension
            as_attachment=False,  # True for download, False for inline
            attachment_filename=doc.basename  # Custom filename
        )

**How it works:**

1. Opens file in streaming mode (low memory)
2. Detects MIME type automatically or uses provided
3. Sets proper HTTP headers (Content-Type, Content-Disposition)
4. Streams file in chunks (default 8KB)
5. Works with Flask, Django, Pyramid, Bottle, etc.

**Method signature:**

.. code-block:: python

    def serve(
        self,
        mimetype: str = 'auto',
        as_attachment: bool = False,
        attachment_filename: str | None = None,
        cache_timeout: int | None = None,
        add_etags: bool = True,
        conditional: bool = True
    ) -> Response

**Parameters:**

- ``mimetype``: MIME type or 'auto' for automatic detection
- ``as_attachment``: True = force download, False = display inline
- ``attachment_filename``: Custom filename for downloads
- ``cache_timeout``: Seconds for Cache-Control header
- ``add_etags``: Include ETag header for caching
- ``conditional``: Support If-Modified-Since, If-None-Match

Framework-Specific Examples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Flask:**

.. code-block:: python

    from flask import Flask

    @app.route('/images/<path:image>')
    def serve_image(image):
        return storage.node(f's3:{image}').serve()

    @app.route('/download/<path:file>')
    def download_file(file):
        return storage.node(f'docs:{file}').serve(
            as_attachment=True,
            attachment_filename='report.pdf'
        )

**Django:**

.. code-block:: python

    from django.http import HttpResponse

    def serve_file(request, path):
        node = storage.node(f's3:{path}')
        response = node.serve(
            mimetype='application/pdf',
            cache_timeout=3600  # 1 hour
        )
        return response

**Pyramid:**

.. code-block:: python

    from pyramid.view import view_config

    @view_config(route_name='serve_file')
    def serve_file_view(request):
        filename = request.matchdict['filename']
        node = storage.node(f'uploads:{filename}')
        return node.serve()

**Performance considerations:**

- Streaming: O(1) memory usage (vs O(n) for read_bytes())
- Chunk size: Default 8KB, configurable
- Caching: ETags and Last-Modified headers reduce bandwidth
- For very large files (>1GB), consider CDN or signed URLs

File Properties and Metadata
-----------------------------

The ``mimetype`` Property
~~~~~~~~~~~~~~~~~~~~~~~~~

Automatic MIME type detection based on file extension:

.. code-block:: python

    image = storage.node('uploads:photo.jpg')
    print(image.mimetype)  # 'image/jpeg'

    video = storage.node('videos:movie.mp4')
    print(video.mimetype)  # 'video/mp4'

    doc = storage.node('docs:report.pdf')
    print(doc.mimetype)  # 'application/pdf'

    # Unknown extensions return generic
    unknown = storage.node('file.xyz')
    print(unknown.mimetype)  # 'application/octet-stream'

**How it works:**

Uses Python's ``mimetypes`` module to map extensions to MIME types. Supports:

- Standard types (image/*, video/*, application/*, text/*)
- Common web formats (HTML, CSS, JS, JSON, XML)
- Document formats (PDF, DOCX, XLSX)
- Archive formats (ZIP, TAR, GZ)

**Use cases:**

- Setting Content-Type headers for web serving
- Validating file uploads
- Content-based processing pipelines

.. code-block:: python

    # Validate upload type
    upload = storage.node('uploads:avatar.jpg')
    if not upload.mimetype.startswith('image/'):
        raise ValueError("Only images allowed")

    # Content-based routing
    file = storage.node('files:document')
    if file.mimetype == 'application/pdf':
        process_pdf(file)
    elif file.mimetype.startswith('image/'):
        process_image(file)

The ``md5hash`` Property
~~~~~~~~~~~~~~~~~~~~~~~~~

Compute MD5 hash of file contents:

.. code-block:: python

    file = storage.node('data:file.txt')
    print(file.md5hash)  # 'a1b2c3d4e5f6...'

    # Compare files
    file1 = storage.node('v1:data.json')
    file2 = storage.node('v2:data.json')

    if file1.md5hash == file2.md5hash:
        print("Files are identical")
    else:
        print("Files differ")

**How it works:**

- Computes MD5 hash by reading file in chunks (memory-efficient)
- Returns lowercase hex digest (32 characters)
- Uses streaming to handle large files
- Result is cached per StorageNode instance

**Use cases:**

.. code-block:: python

    # Content-based equality check
    if original.md5hash == backup.md5hash:
        print("Backup verified")

    # Deduplication
    seen_hashes = set()
    for file in directory.children():
        hash = file.md5hash
        if hash in seen_hashes:
            print(f"Duplicate: {file.basename}")
        seen_hashes.add(hash)

    # Change detection
    old_hash = file.md5hash
    # ... time passes ...
    if file.md5hash != old_hash:
        print("File was modified")

**Performance note:** MD5 computation requires reading entire file. For large files, consider using ``size`` and ``mtime`` for quicker comparisons.

Smart Copy Strategies
----------------------

The Problem
~~~~~~~~~~~

Copying files can be expensive (time, bandwidth, cost). Often you want to:

- Skip if destination already exists
- Skip if sizes match (assume identical)
- Skip if MD5 hashes match (verify identical)
- Custom logic

The ``skip_if`` Parameter
~~~~~~~~~~~~~~~~~~~~~~~~~

All copy/move operations support ``skip_if`` to control when to skip:

.. code-block:: python

    source.copy(destination, skip_if='exists')

**Built-in strategies:**

1. ``'exists'`` - Skip if destination exists (fastest)
2. ``'size'`` - Skip if destination exists AND size matches
3. ``'hash'`` - Skip if destination exists AND MD5 hash matches (slowest but safest)
4. ``'never'`` - Always copy (default)
5. ``callable`` - Custom function

Strategy Details
~~~~~~~~~~~~~~~~

**'exists' strategy:**

.. code-block:: python

    # Skip if file exists, regardless of content
    source.copy(dest, skip_if='exists')

    # Use case: first-time sync
    for file in source_dir.children():
        target = dest_dir.child(file.basename)
        file.copy(target, skip_if='exists')
        # Only copies files that don't exist yet

**Performance:** Fastest. Just checks ``dest.exists``.

**'size' strategy:**

.. code-block:: python

    # Skip if exists AND size matches
    source.copy(dest, skip_if='size')

    # Use case: incremental backups
    for file in source_dir.children():
        target = backup_dir.child(file.basename)
        file.copy(target, skip_if='size')
        # Only copies if missing or size changed

**Performance:** Fast. Checks ``exists`` + ``size`` (no file reads).

**'hash' strategy:**

.. code-block:: python

    # Skip if exists AND MD5 hash matches (content-identical)
    source.copy(dest, skip_if='hash')

    # Use case: verify backups
    for file in source_dir.children():
        target = backup_dir.child(file.basename)
        file.copy(target, skip_if='hash')
        # Guarantees destination content matches source

**Performance:** Slow. Reads both files to compute MD5. Use for verification.

**'never' strategy (default):**

.. code-block:: python

    # Always copy, overwrite if exists
    source.copy(dest, skip_if='never')  # or just source.copy(dest)

Custom Skip Functions
~~~~~~~~~~~~~~~~~~~~~

Provide a callable for custom logic:

.. code-block:: python

    def skip_if_recent(source: StorageNode, dest: StorageNode) -> bool:
        """Skip if destination modified in last 24 hours."""
        if not dest.exists:
            return False  # Don't skip, destination missing

        import time
        age_seconds = time.time() - dest.mtime
        return age_seconds < 86400  # Skip if < 24 hours old

    source.copy(dest, skip_if=skip_if_recent)

**Function signature:**

.. code-block:: python

    def skip_function(source: StorageNode, dest: StorageNode) -> bool:
        """
        Args:
            source: Source node (guaranteed to exist)
            dest: Destination node (may not exist)

        Returns:
            True to skip copy, False to proceed
        """
        pass

**More examples:**

.. code-block:: python

    # Skip if destination is newer
    def skip_if_newer(src, dst):
        return dst.exists and dst.mtime > src.mtime

    # Skip based on size threshold
    def skip_if_too_large(src, dst):
        return src.size > 100 * 1024 * 1024  # > 100MB

    # Skip based on filename pattern
    def skip_temp_files(src, dst):
        return src.basename.startswith('.')

    # Combine conditions
    def smart_skip(src, dst):
        if not dst.exists:
            return False
        if dst.size != src.size:
            return False
        # Only compute expensive hash if sizes match
        return dst.md5hash == src.md5hash

Batch Operations with Skip Strategies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Efficient directory sync:**

.. code-block:: python

    def sync_directory(source_dir, dest_dir, strategy='size'):
        """Sync directory with smart skipping."""
        for file in source_dir.children():
            if file.isfile:
                dest_file = dest_dir.child(file.basename)
                file.copy(dest_file, skip_if=strategy)
                print(f"Synced: {file.basename}")

    # Usage
    source = storage.node('s3:source/')
    dest = storage.node('backup:dest/')
    sync_directory(source, dest, strategy='size')

**Incremental backups with statistics:**

.. code-block:: python

    def incremental_backup(source_dir, backup_dir):
        """Backup with statistics."""
        stats = {'copied': 0, 'skipped': 0, 'bytes': 0}

        for file in source_dir.children():
            if not file.isfile:
                continue

            backup_file = backup_dir.child(file.basename)

            # Custom skip with counting
            if backup_file.exists and backup_file.md5hash == file.md5hash:
                stats['skipped'] += 1
                continue

            file.copy(backup_file)
            stats['copied'] += 1
            stats['bytes'] += file.size

        return stats

    # Usage
    stats = incremental_backup(
        storage.node('data:'),
        storage.node('backups:')
    )
    print(f"Copied {stats['copied']}, skipped {stats['skipped']}")
    print(f"Total: {stats['bytes'] / 1024 / 1024:.2f} MB")

Performance Comparison
~~~~~~~~~~~~~~~~~~~~~~

For 1000 files (1MB each) where 900 are identical:

.. code-block:: text

    Strategy     Time       Network      Notes
    ──────────────────────────────────────────────────────────────
    never        ~180s      1000MB       Always copies everything
    exists       ~5s        100MB        Fast check, copies changed
    size         ~8s        100MB        Slightly slower check
    hash         ~45s       100MB        Reads all for verification

**Recommendation:**

- **Development:** Use ``'exists'`` (fast, simple)
- **Production sync:** Use ``'size'`` (good balance)
- **Critical backups:** Use ``'hash'`` (guaranteed correctness)
- **Custom needs:** Write your own function

Best Practices
--------------

Tool Integration
~~~~~~~~~~~~~~~~

.. code-block:: python

    # ✅ Good: Handle errors
    try:
        video.call('ffmpeg -i {input} {output}', input=video, output=result)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg failed: {e.stderr}")
        # Clean up or retry

    # ✅ Good: Set timeouts
    doc.call('pandoc {in} -o {out}', in=doc, out=pdf, timeout=60)

    # ❌ Bad: shell=True with user input (security risk!)
    filename = user_input  # DANGEROUS!
    node.call(f'convert {filename} output.jpg', shell=True)

    # ✅ Good: Use argument list with shell=False
    node.call(['convert', filename, 'output.jpg'], shell=False)

Web Serving
~~~~~~~~~~~

.. code-block:: python

    # ✅ Good: Let serve() handle MIME types
    return node.serve(mimetype='auto')

    # ✅ Good: Enable caching for static assets
    return node.serve(cache_timeout=3600, add_etags=True)

    # ✅ Good: Force download for sensitive files
    return node.serve(as_attachment=True, attachment_filename='secure.pdf')

    # ❌ Bad: Loading entire file into memory
    data = node.read_bytes()  # Could be GBs!
    return Response(data, mimetype='video/mp4')

    # ✅ Good: Use streaming
    return node.serve()

Copy Strategies
~~~~~~~~~~~~~~~

.. code-block:: python

    # ✅ Good: Use appropriate strategy for use case
    source.copy(dest, skip_if='size')  # Fast incremental sync

    # ✅ Good: Verify critical backups
    source.copy(dest, skip_if='hash')  # Slower but guaranteed

    # ❌ Bad: No skip strategy for repeated syncs
    for file in directory.children():
        file.copy(backup_dir.child(file.basename))
        # Wastes time/bandwidth re-copying unchanged files

    # ✅ Good: Monitor what was skipped
    def sync_with_logging(src, dst):
        if dst.exists and dst.md5hash == src.md5hash:
            logger.info(f"Skipped (unchanged): {src.basename}")
            return True
        logger.info(f"Copying: {src.basename}")
        return False

    source.copy(dest, skip_if=sync_with_logging)

See Also
--------

- :doc:`examples` - Practical examples
- :doc:`api` - Complete API reference
- :doc:`overview` - Technical overview and comparisons
