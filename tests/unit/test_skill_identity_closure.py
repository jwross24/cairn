import ast
import importlib
import json
import shutil
import subprocess
import sys

import pytest

from cairn import bundle

ROOT = bundle.REPO_ROOT
SRC = ROOT / "src"
SKILLS = ("toy_curve", "rho_dp", "bsgs", "instance_maker")
INITIALIZERS = ("src/cairn/__init__.py", "src/cairn/skills/__init__.py")


def _module_file(dotted):
    base = SRC.joinpath(*dotted.split("."))
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


def _imported(tree, lazy):
    stack = list(ast.iter_child_nodes(tree))
    while stack:
        node = stack.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if lazy:
                stack.extend(ast.iter_child_nodes(node))
            continue
        stack.extend(ast.iter_child_nodes(node))
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.module
            yield from (f"{node.module}.{alias.name}" for alias in node.names)


def _with_initializers(dotted):
    parts = dotted.split(".")
    return [".".join(parts[:i]) for i in range(1, len(parts) + 1)]


def _module_closure(roots):
    seen, pending = set(), list(roots)
    while pending:
        dotted = pending.pop()
        if dotted in seen or not dotted.startswith("cairn"):
            continue
        for name in _with_initializers(dotted):
            path = _module_file(name)
            if path is None:
                continue
            seen.add(name)
            tree = ast.parse(path.read_text())
            pending.extend(_imported(tree, lazy=False))
    return seen


def static_closure(skill):
    dotted = f"cairn.skills.{skill}"
    tree = ast.parse(_module_file(dotted).read_text())
    lazy_targets = {name for name in _imported(tree, lazy=True) if name.startswith("cairn")}
    modules = _module_closure([dotted, *lazy_targets])
    return {str(_module_file(name).relative_to(ROOT)) for name in modules}


def uncovered(closure, sources):
    return sorted(set(closure) - set(sources))


def _sources(skill):
    return importlib.import_module(f"cairn.skills.{skill}").IDENTITY_SOURCES


@pytest.mark.parametrize("skill", SKILLS)
def test_the_declared_sources_cover_the_static_import_closure(skill):
    assert not uncovered(static_closure(skill), _sources(skill))


@pytest.mark.parametrize("skill", SKILLS)
def test_a_fresh_process_loads_no_repository_file_outside_the_declared_sources(skill):
    probe = (
        "import importlib, json, os, sys\n"
        f"sys.path.insert(0, {str(SRC)!r})\n"
        f"importlib.import_module('cairn.skills.{skill}')\n"
        f"root = {str(ROOT)!r}\n"
        "print(json.dumps(sorted(os.path.relpath(m.__file__, root) for m in sys.modules.values()"
        " if getattr(m, '__file__', None) and os.path.abspath(m.__file__).startswith(os.path.join(root, 'src')))))\n"
    )
    done = subprocess.run([sys.executable, "-I", "-c", probe], capture_output=True, text=True, check=True)
    loaded = json.loads(done.stdout)
    assert set(INITIALIZERS) <= set(loaded)
    assert not uncovered(loaded, _sources(skill))


@pytest.mark.parametrize("skill", SKILLS)
def test_the_package_initializers_are_declared(skill):
    assert set(INITIALIZERS) <= set(_sources(skill))


@pytest.mark.parametrize("skill", SKILLS)
def test_the_closure_gate_refuses_a_dropped_member(skill):
    closure = static_closure(skill)
    for dropped in sorted(closure):
        kept = [path for path in _sources(skill) if path != dropped]
        assert uncovered(closure, kept) == [dropped]


@pytest.mark.parametrize("skill", SKILLS)
@pytest.mark.parametrize("target", [*INITIALIZERS, "src/cairn/canon.py"])
def test_a_changed_closure_member_moves_the_implementation_revision(skill, target, tmp_path):
    shutil.copytree(SRC, tmp_path / "src", ignore=shutil.ignore_patterns("__pycache__"))
    module = importlib.import_module(f"cairn.skills.{skill}")
    before = module.implementation_revision(tmp_path)
    path = tmp_path / target
    path.write_bytes(path.read_bytes() + b"\nPLANTED = 1\n")
    assert module.implementation_revision(tmp_path) != before
