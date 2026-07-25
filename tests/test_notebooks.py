"""Execute the shipped notebooks, so the documented API cannot rot unnoticed.

Every notebook in ``notebooks/`` is run cell by cell in a throwaway working
directory. This is not a Jupyter kernel: cells are compiled and exec'd in a
single namespace, so cells relying on IPython magics or shell escapes are
skipped rather than executed.

Marked ``integration`` because two notebooks read from raw.githubusercontent.com.
"""

import json
import pathlib

import pytest
from fsspec.implementations.memory import MemoryFileSystem

NOTEBOOK_DIR = pathlib.Path(__file__).parent.parent / "notebooks"
NOTEBOOKS = sorted(NOTEBOOK_DIR.glob("*.ipynb"))


@pytest.fixture
def empty_memory_filesystem():
    """Give a notebook the empty memory backend a fresh kernel would have.

    fsspec keeps the memory store on the class, so it is shared by everything in
    the process: without this, a notebook creating 'mem:data' fails when an
    earlier test in the same run already created it.
    """
    MemoryFileSystem.store.clear()
    MemoryFileSystem.pseudo_dirs[:] = [""]
    yield
    MemoryFileSystem.store.clear()
    MemoryFileSystem.pseudo_dirs[:] = [""]


def code_cells(notebook_path):
    """Yield (index, source) for every non-empty code cell of a notebook."""
    notebook = json.loads(notebook_path.read_text())
    for index, cell in enumerate(notebook["cells"]):
        source = "".join(cell["source"])
        if cell["cell_type"] == "code" and source.strip():
            yield index, source


def needs_ipython(source):
    """True if the cell uses a magic or a shell escape, which exec cannot run."""
    return any(line.lstrip().startswith(("%", "!")) for line in source.splitlines())


@pytest.mark.integration
@pytest.mark.parametrize("notebook_path", NOTEBOOKS, ids=lambda path: path.stem)
def test_notebook_executes(notebook_path, tmp_path, monkeypatch, empty_memory_filesystem):
    """Test that every cell of a shipped notebook still runs."""
    monkeypatch.chdir(tmp_path)
    namespace = {"__name__": "__main__"}

    for index, source in code_cells(notebook_path):
        if needs_ipython(source):
            continue
        code = compile(source, f"{notebook_path.name}[cell {index}]", "exec")
        try:
            # exec is the point: a notebook cell is arbitrary code by definition.
            exec(code, namespace)  # noqa: S102
        except Exception as error:  # noqa: BLE001 - any failure is a failing notebook
            pytest.fail(f"cell {index} raised {type(error).__name__}: {error}")


def test_notebooks_are_present():
    """Test that the notebook suite is discovered at all."""
    assert len(NOTEBOOKS) == 8
