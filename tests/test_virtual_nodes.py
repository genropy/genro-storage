"""Tests for virtual nodes (iternode and diffnode)."""

import pytest
import tempfile
import shutil
from genro_storage import StorageManager


@pytest.fixture
def storage():
    """Create a StorageManager with memory storage."""
    mgr = StorageManager()
    mgr.configure([{"name": "mem", "protocol": "memory"}])
    return mgr


@pytest.fixture
def temp_storage():
    """Create a StorageManager with local storage."""
    tmpdir = tempfile.mkdtemp()
    mgr = StorageManager()
    mgr.configure([{"name": "local", "protocol": "local", "path": tmpdir}])
    yield mgr
    shutil.rmtree(tmpdir)


class TestIterNode:
    """Tests for iternode (virtual concatenation node)."""

    def test_create_iternode_with_nodes(self, storage):
        """Can create iternode with multiple nodes."""
        n1 = storage.node("mem:file1.txt")
        n1.write("Hello ")

        n2 = storage.node("mem:file2.txt")
        n2.write("World")

        iternode = storage.iternode(n1, n2)
        assert iternode is not None

    def test_iternode_read_text_concatenates(self, storage):
        """iternode.read() concatenates all sources."""
        n1 = storage.node("mem:f1.txt")
        n1.write("One ")

        n2 = storage.node("mem:f2.txt")
        n2.write("Two ")

        n3 = storage.node("mem:f3.txt")
        n3.write("Three")

        iternode = storage.iternode(n1, n2, n3)
        result = iternode.read()

        assert result == "One Two Three"

    def test_iternode_is_lazy(self, storage):
        """iternode doesn't read until materialized."""
        n1 = storage.node("mem:file1.txt")
        n1.write("original")

        iternode = storage.iternode(n1)

        # Change source after creating iternode
        n1.write("modified")

        # Should read current content (lazy)
        result = iternode.read()
        assert result == "modified"

    def test_iternode_append(self, storage):
        """Can append nodes to iternode after creation."""
        n1 = storage.node("mem:f1.txt")
        n1.write("First ")

        n2 = storage.node("mem:f2.txt")
        n2.write("Second")

        iternode = storage.iternode(n1)
        iternode.append(n2)

        result = iternode.read()
        assert result == "First Second"

    def test_iternode_extend(self, storage):
        """Can extend iternode with multiple nodes."""
        n1 = storage.node("mem:f1.txt")
        n1.write("A ")

        n2 = storage.node("mem:f2.txt")
        n2.write("B ")

        n3 = storage.node("mem:f3.txt")
        n3.write("C")

        iternode = storage.iternode(n1)
        iternode.extend(n2, n3)

        result = iternode.read()
        assert result == "A B C"

    def test_iternode_append_and_extend(self, storage):
        """Can mix append and extend."""
        n1 = storage.node("mem:f1.txt")
        n1.write("1 ")

        n2 = storage.node("mem:f2.txt")
        n2.write("2 ")

        n3 = storage.node("mem:f3.txt")
        n3.write("3 ")

        n4 = storage.node("mem:f4.txt")
        n4.write("4")

        iternode = storage.iternode(n1)
        iternode.append(n2)
        iternode.extend(n3, n4)

        result = iternode.read()
        assert result == "1 2 3 4"

    def test_iternode_copy_to_destination(self, storage):
        """Can copy iternode content to destination."""
        n1 = storage.node("mem:f1.txt")
        n1.write("Part 1 ")

        n2 = storage.node("mem:f2.txt")
        n2.write("Part 2")

        iternode = storage.iternode(n1, n2)

        dest = storage.node("mem:result.txt")
        iternode.copy_to(dest)

        assert dest.exists
        assert dest.read() == "Part 1 Part 2"

    def test_iternode_empty(self, storage):
        """Can create empty iternode."""
        iternode = storage.iternode()

        result = iternode.read()
        assert result == ""

    def test_iternode_exists_is_false(self, storage):
        """iternode.exists returns False (virtual)."""
        n1 = storage.node("mem:f1.txt")
        n1.write("content")

        iternode = storage.iternode(n1)

        assert iternode.exists is False

    def test_iternode_write_raises_error(self, storage):
        """Cannot write to iternode (virtual, no path)."""
        iternode = storage.iternode()

        with pytest.raises(ValueError, match="[Cc]annot write|virtual|no path"):
            iternode.write("content")

    def test_iternode_read_bytes(self, storage):
        """iternode.read(mode='rb') concatenates binary content."""
        n1 = storage.node("mem:f1.bin")
        n1.write(b"Hello ", mode="wb")

        n2 = storage.node("mem:f2.bin")
        n2.write(b"World", mode="wb")

        iternode = storage.iternode(n1, n2)
        result = iternode.read(mode="rb")

        assert result == b"Hello World"


class TestDiffNode:
    """Tests for diffnode (virtual diff node)."""

    def test_create_diffnode(self, storage):
        """Can create diffnode with two nodes."""
        n1 = storage.node("mem:v1.txt")
        n1.write("content 1")

        n2 = storage.node("mem:v2.txt")
        n2.write("content 2")

        diffnode = storage.diffnode(n1, n2)
        assert diffnode is not None

    def test_diffnode_generates_diff(self, storage):
        """diffnode.read() generates unified diff."""
        n1 = storage.node("mem:v1.txt")
        n1.write("line 1\nline 2\nline 3\n")

        n2 = storage.node("mem:v2.txt")
        n2.write("line 1\nline 2 modified\nline 3\n")

        diffnode = storage.diffnode(n1, n2)
        diff = diffnode.read()

        assert isinstance(diff, str)
        assert "line 2" in diff
        assert "modified" in diff
        # Check for unified diff markers
        assert "---" in diff or "+++" in diff or "@@ -" in diff

    def test_diffnode_identical_files(self, storage):
        """Diff of identical files is empty or minimal."""
        n1 = storage.node("mem:f1.txt")
        n1.write("same content\n")

        n2 = storage.node("mem:f2.txt")
        n2.write("same content\n")

        diffnode = storage.diffnode(n1, n2)
        diff = diffnode.read()

        # Empty diff or only header
        assert len(diff) == 0 or diff.count("\n") <= 2

    def test_diffnode_is_lazy(self, storage):
        """diffnode doesn't read until materialized."""
        n1 = storage.node("mem:v1.txt")
        n1.write("original")

        n2 = storage.node("mem:v2.txt")
        n2.write("different")

        diffnode = storage.diffnode(n1, n2)

        # Change source after creating diffnode
        n1.write("modified")

        # Should read current content
        diff = diffnode.read()
        assert "modified" in diff or "different" in diff

    def test_diffnode_copy_to_destination(self, storage):
        """Can copy diff to destination file."""
        n1 = storage.node("mem:v1.txt")
        n1.write("line 1\nline 2\n")

        n2 = storage.node("mem:v2.txt")
        n2.write("line 1\nline 2 changed\n")

        diffnode = storage.diffnode(n1, n2)

        dest = storage.node("mem:changes.diff")
        diffnode.copy_to(dest)

        assert dest.exists
        content = dest.read()
        assert "line 2" in content

    def test_diffnode_exists_is_false(self, storage):
        """diffnode.exists returns False (virtual)."""
        n1 = storage.node("mem:f1.txt")
        n1.write("content 1")

        n2 = storage.node("mem:f2.txt")
        n2.write("content 2")

        diffnode = storage.diffnode(n1, n2)

        assert diffnode.exists is False

    def test_diffnode_write_raises_error(self, storage):
        """Cannot write to diffnode (virtual)."""
        n1 = storage.node("mem:f1.txt")
        n1.write("content")

        n2 = storage.node("mem:f2.txt")
        n2.write("content")

        diffnode = storage.diffnode(n1, n2)

        with pytest.raises(ValueError, match="[Cc]annot write|virtual|no path"):
            diffnode.write("content")

    def test_diffnode_binary_raises_error(self, storage):
        """Diffing binary files raises ValueError."""
        n1 = storage.node("mem:file1.bin")
        n1.write(b"\x00\x01", mode="wb")

        n2 = storage.node("mem:file2.bin")
        n2.write(b"\x02\x03", mode="wb")

        diffnode = storage.diffnode(n1, n2)

        with pytest.raises(ValueError, match="[Cc]annot diff.*binary"):
            diffnode.read()


class TestZipMethod:
    """Tests for zip() method on nodes."""

    def test_zip_single_file(self, temp_storage):
        """zip() of single file creates ZIP with that file."""
        node = temp_storage.node("local:file.txt")
        node.write("content")

        zip_bytes = node.zip()

        assert isinstance(zip_bytes, bytes)
        assert len(zip_bytes) > 0
        # Check ZIP signature
        assert zip_bytes[:2] == b"PK"

    def test_zip_directory_recursive(self, temp_storage):
        """zip() of directory includes all files recursively."""
        dir_node = temp_storage.node("local:mydir")
        dir_node.mkdir()

        dir_node.child("file1.txt").write("content1")
        dir_node.child("file2.txt").write("content2")

        subdir = dir_node.child("subdir")
        subdir.mkdir()
        subdir.child("file3.txt").write("content3")

        zip_bytes = dir_node.zip()

        assert isinstance(zip_bytes, bytes)
        assert zip_bytes[:2] == b"PK"

        # Verify ZIP contains files
        import zipfile
        import io

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert len(names) >= 3
            assert any("file1.txt" in n for n in names)
            assert any("file2.txt" in n for n in names)
            assert any("file3.txt" in n for n in names)

    def test_zip_iternode(self, storage):
        """zip() of iternode creates ZIP with all accumulated files."""
        n1 = storage.node("mem:file1.txt")
        n1.write("content1")

        n2 = storage.node("mem:file2.txt")
        n2.write("content2")

        iternode = storage.iternode(n1, n2)
        zip_bytes = iternode.zip()

        assert isinstance(zip_bytes, bytes)
        assert zip_bytes[:2] == b"PK"

        # Verify contents
        import zipfile
        import io

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert "file1.txt" in names
            assert "file2.txt" in names
            assert zf.read("file1.txt") == b"content1"
            assert zf.read("file2.txt") == b"content2"

    def test_zip_and_write(self, storage):
        """Can write ZIP to another node."""
        n1 = storage.node("mem:f1.txt")
        n1.write("data1")

        n2 = storage.node("mem:f2.txt")
        n2.write("data2")

        iternode = storage.iternode(n1, n2)

        zip_node = storage.node("mem:archive.zip")
        zip_node.write(iternode.zip(), mode="wb")

        assert zip_node.exists
        assert zip_node.read(mode="rb")[:2] == b"PK"

    def test_zip_empty_iternode(self, storage):
        """zip() of empty iternode creates empty ZIP."""
        iternode = storage.iternode()

        zip_bytes = iternode.zip()

        assert isinstance(zip_bytes, bytes)
        assert zip_bytes[:2] == b"PK"

        import zipfile
        import io

        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            assert len(zf.namelist()) == 0


class TestIntegration:
    """Integration tests combining multiple features."""

    def test_iternode_workflow(self, storage):
        """Build document using iternode."""
        header = storage.node("mem:header.txt")
        header.write("# Report\n\n")

        body = storage.node("mem:body.txt")
        body.write("Content here.\n\n")

        footer = storage.node("mem:footer.txt")
        footer.write("End of report.")

        # Build report
        report_builder = storage.iternode(header, body, footer)

        # Write to destination
        report = storage.node("mem:report.txt")
        report_builder.copy_to(report)

        content = report.read()
        assert content == "# Report\n\nContent here.\n\nEnd of report."

    def test_diffnode_workflow(self, storage):
        """Generate diff and save it."""
        v1 = storage.node("mem:config_v1.txt")
        v1.write("setting1=value1\nsetting2=value2\n")

        v2 = storage.node("mem:config_v2.txt")
        v2.write("setting1=value1\nsetting2=new_value\n")

        # Generate diff
        changes = storage.diffnode(v1, v2)

        # Save diff to file
        diff_file = storage.node("mem:changes.diff")
        changes.copy_to(diff_file)

        assert diff_file.exists
        assert "setting2" in diff_file.read()

    def test_zip_iternode_and_save(self, storage):
        """Create ZIP from multiple files and save."""
        files = []
        for i in range(3):
            node = storage.node(f"mem:file{i}.txt")
            node.write(f"Content {i}")
            files.append(node)

        # Create ZIP
        archive_builder = storage.iternode(*files)

        # Save ZIP
        zip_file = storage.node("mem:backup.zip")
        zip_file.write(archive_builder.zip(), mode="wb")

        assert zip_file.exists
        assert zip_file.size > 0

    def test_incremental_build_with_iternode(self, storage):
        """Build content incrementally."""
        builder = storage.iternode()

        # Add sections progressively
        intro = storage.node("mem:intro.txt")
        intro.write("Introduction\n")
        builder.append(intro)

        # Add more sections
        for i in range(1, 4):
            section = storage.node(f"mem:section{i}.txt")
            section.write(f"Section {i}\n")
            builder.append(section)

        # Finalize
        final = storage.node("mem:document.txt")
        builder.copy_to(final)

        content = final.read()
        assert "Introduction" in content
        assert "Section 1" in content
        assert "Section 3" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
