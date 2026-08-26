import ast
from pathlib import Path

import pytest

DOCTOR_PACKAGE = Path(__file__).resolve().parents[2] / "src" / "cairn" / "doctor"
WRITE_ALLOWED = {"mutate.py", "artifacts.py"}
RMDIR_ALLOWED = {"mutate.py"}

WRITE_ATTRS = {
    "chmod",
    "chflags",
    "replace",
    "rename",
    "mkdir",
    "makedirs",
    "symlink",
    "symlink_to",
    "write_text",
    "write_bytes",
    "touch",
    "copy",
    "copy2",
    "copytree",
    "copyfile",
    "copystat",
    "move",
    "ftruncate",
}
DELETE_ATTRS = {"remove", "unlink", "rmtree", "removedirs"}
# os.write and os.truncate name a descriptor, not a path, so they are only a write
# when qualified by the os module; a bare .write is sys.stdout's just as often.
OS_WRITE_ATTRS = {"open", "write", "truncate"}
WRITE_MODES = set("wax+")


def _open_is_write(call, *, position=1):
    mode = None
    if len(call.args) > position and isinstance(call.args[position], ast.Constant):
        mode = call.args[position].value
    for kw in call.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            mode = kw.value.value
    return isinstance(mode, str) and bool(WRITE_MODES & set(mode))


def _aliases(tree):
    modules, names = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules[alias.asname or alias.name.split(".")[0]] = alias.name
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names[alias.asname or alias.name] = alias.name
    return modules, names


def _is_os(func, modules):
    return isinstance(func.value, ast.Name) and modules.get(func.value.id, func.value.id) == "os"


def scan_source(name, text):
    tree = ast.parse(text)
    modules, imported = _aliases(tree)
    violations = []

    def report(attr):
        if attr in DELETE_ATTRS:
            violations.append(f"{name}: {attr} — the doctor deletes nothing")
        elif attr == "rmdir" and name not in RMDIR_ALLOWED:
            violations.append(f"{name}: rmdir outside mutate.py")
        elif attr in WRITE_ATTRS and name not in WRITE_ALLOWED:
            violations.append(f"{name}: {attr} outside mutate.py/artifacts.py")

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            resolved = imported.get(func.id, func.id)
            if resolved == "open" and _open_is_write(node):
                if name not in WRITE_ALLOWED:
                    violations.append(f"{name}: open(..., write mode) outside mutate.py/artifacts.py")
                continue
            report(resolved)
            continue
        if not isinstance(func, ast.Attribute):
            continue
        if _is_os(func, modules) and func.attr in OS_WRITE_ATTRS:
            if name not in WRITE_ALLOWED:
                violations.append(f"{name}: os.{func.attr} outside mutate.py/artifacts.py")
            continue
        if func.attr == "open" and _open_is_write(node, position=0):
            if name not in WRITE_ALLOWED:
                violations.append(f"{name}: .open(..., write mode) outside mutate.py/artifacts.py")
            continue
        report(func.attr)
    return violations


def _sources():
    return sorted(p for p in DOCTOR_PACKAGE.rglob("*.py") if "__pycache__" not in p.parts)


def test_no_doctor_module_writes_outside_the_mutate_chokepoint():
    violations = []
    for path in _sources():
        violations += scan_source(path.name, path.read_text())
    assert violations == []


def test_the_package_actually_has_the_modules_the_scan_polices():
    names = {p.name for p in _sources()}
    assert {"mutate.py", "artifacts.py", "detectors.py", "fixers.py", "__init__.py"} <= names


@pytest.mark.parametrize(
    ("source", "needle"),
    [
        ("import os\ndef f(p):\n    with open(p, 'w') as fh:\n        fh.write('x')\n", "open"),
        ("import os\ndef f(p):\n    os.chmod(p, 0o644)\n", "chmod"),
        ("import os\ndef f(p):\n    os.chflags(p, 0)\n", "chflags"),
        ("import os\ndef f(p):\n    os.replace(p, p)\n", "replace"),
        ("import os\ndef f(p):\n    os.rmdir(p)\n", "rmdir"),
        ("import shutil\ndef f(p):\n    shutil.copy2(p, p)\n", "copy2"),
        ("from pathlib import Path\ndef f(p):\n    Path(p).write_text('x')\n", "write_text"),
        ("import os\ndef f(p):\n    return os.open(p, os.O_WRONLY | os.O_CREAT)\n", "os.open"),
        ("import os\ndef f(fd, b):\n    os.write(fd, b)\n", "os.write"),
        ("import os\ndef f(p):\n    os.truncate(p, 0)\n", "os.truncate"),
        ("from pathlib import Path\ndef f(p):\n    Path(p).open('w').write('x')\n", ".open"),
        ("from os import unlink as _u\ndef f(p):\n    _u(p)\n", "unlink"),
        ("from shutil import rmtree\ndef f(p):\n    rmtree(p)\n", "rmtree"),
        ("from os import remove as _r\ndef f(p):\n    _r(p)\n", "remove"),
    ],
    ids=[
        "open-w",
        "chmod",
        "chflags",
        "replace",
        "rmdir",
        "shutil",
        "write_text",
        "os-open",
        "os-write",
        "os-truncate",
        "path-open-write-mode",
        "aliased-unlink",
        "imported-rmtree",
        "aliased-remove",
    ],
)
def test_a_planted_writer_module_is_caught(source, needle):
    violations = scan_source("detectors.py", source)
    assert violations and needle in violations[0]


@pytest.mark.parametrize(
    "source",
    [
        "import os\ndef f(p):\n    os.remove(p)\n",
        "import os\ndef f(p):\n    os.unlink(p)\n",
        "import shutil\ndef f(p):\n    shutil.rmtree(p)\n",
    ],
    ids=["remove", "unlink", "rmtree"],
)
def test_a_planted_deleter_is_caught_even_in_the_chokepoint(source):
    assert scan_source("mutate.py", source)


def test_rmdir_is_allowed_only_in_the_chokepoint():
    source = "import os\ndef f(p):\n    os.rmdir(p)\n"
    assert scan_source("mutate.py", source) == []
    assert scan_source("fixers.py", source)


def test_a_clean_module_scans_clean():
    assert scan_source("detectors.py", "import os\ndef f(p):\n    return os.stat(p).st_mode\n") == []
