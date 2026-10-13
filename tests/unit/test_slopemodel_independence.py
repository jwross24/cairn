import ast
import importlib.util
import sys
from pathlib import Path

import pytest

from cairn import slopemodel

SOURCE_ROOT = Path(slopemodel.__file__).resolve().parents[2]
A_ROOTS = ("cairn.slopemodel.slopemodel_a", "cairn.slopemodel.slope_hunt_executor")
B_ROOTS = ("cairn.slopemodel.slopemodel_b", "cairn.slopemodel.slope_hunt_verifier")


def module_path(source_root, name):
    path = source_root.joinpath(*name.split("."))
    if path.with_suffix(".py").is_file():
        return path.with_suffix(".py")
    initializer = path / "__init__.py"
    return initializer if initializer.is_file() else None


def imported_modules(tree, package, source_root):
    result = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = importlib.util.resolve_name("." * node.level + base, package)
            result.add(base)
            for alias in node.names:
                candidate = f"{base}.{alias.name}"
                if module_path(source_root, candidate) is not None:
                    result.add(candidate)
    return result


def nonstdlib_closure(source_root, roots):
    visited = set()
    result = set()
    pending = list(roots)
    while pending:
        name = pending.pop()
        if name in visited or name.split(".")[0] in sys.stdlib_module_names:
            continue
        visited.add(name)
        path = module_path(source_root, name)
        if path is None:
            result.add(name.split(".")[0])
            continue
        tree = ast.parse(path.read_text())
        if tree.body:
            result.add(name)
        parts = name.split(".")
        pending.extend(".".join(parts[:index]) for index in range(1, len(parts)))
        package = name if path.name == "__init__.py" else name.rpartition(".")[0]
        pending.extend(imported_modules(tree, package, source_root))
    return result


def assert_independent(source_root, a_roots=A_ROOTS, b_roots=B_ROOTS):
    overlap = nonstdlib_closure(source_root, a_roots) & nonstdlib_closure(source_root, b_roots)
    assert not overlap, f"nonstandard-library import overlap: {sorted(overlap)}"


def test_executor_and_verifier_import_graphs_are_independent():
    assert_independent(SOURCE_ROOT)


@pytest.mark.parametrize("bridge", ["import left", "from left import helper", "from intermediary import helper"])
def test_import_graph_refuses_direct_and_transitive_overlap(tmp_path, bridge):
    (tmp_path / "left.py").write_text("import shared_dependency\n")
    (tmp_path / "right.py").write_text(bridge + "\n")
    (tmp_path / "intermediary.py").write_text("from left import helper\n")
    with pytest.raises(AssertionError, match="import overlap"):
        assert_independent(tmp_path, ("left",), ("right",))


def test_import_graph_refuses_shared_package_initializer(tmp_path):
    package = tmp_path / "engines"
    package.mkdir()
    (package / "__init__.py").write_text("import shared_dependency\n")
    (package / "left.py").write_text("value = 1\n")
    (package / "right.py").write_text("value = 2\n")
    with pytest.raises(AssertionError, match="engines"):
        assert_independent(tmp_path, ("engines.left",), ("engines.right",))
