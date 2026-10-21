from pathlib import Path

import pytest
from _ladder_allowlist_helpers import BACKEND, _hypothesis
from _ladder_allowlist_helpers import instance as instance
from _ladder_allowlist_helpers import scratch as scratch
from _ladder_allowlist_helpers import shipped as shipped

from cairn import allowlist


@pytest.mark.parametrize(
    ("exit_status", "stderr", "expected"),
    [
        (0, b"Operation not permitted", None),
        (9, b"", None),
        (9, b"Traceback\nValueError: unrelated\n", None),
        (9, b"CHILD_ERR PermissionError: [Errno 1] Operation not permitted\n", "network_egress"),
        (
            1,
            b'  File "subprocess.py", line 1970, in _execute_child\n'
            b"PermissionError: [Errno 1] Operation not permitted: '/bin/echo'\n",
            "undeclared_exec",
        ),
        (71, b"sandbox-exec: execvp() of '/bin/echo' failed: Operation not permitted\n", "undeclared_exec"),
        (1, b"Failed to exec /bin/bash as variant for /bin/sh (1: Operation not permitted).\n", "undeclared_exec"),
        (1, b"PermissionError: [Errno 1] Operation not permitted: '/etc/planted.txt'\n", "outside_write"),
        (1, b"PermissionError: [Errno 1] Operation not permitted: '/etc'\n", "outside_write"),
        (1, b"PermissionError: [Errno 1] Operation not permitted: '/usr/bin/true'\n", "outside_write"),
        (
            1,
            b"python3.14: posix_spawn: /opt/homebrew/Cellar/python@3.14/3.14.7/Frameworks/"
            b"Python.framework/Versions/3.14/Resources/Python.app/Contents/MacOS/Python: "
            b"Undefined error: 0\n",
            "undeclared_exec",
        ),
    ],
)
def test_a_named_violation_is_read_from_the_child_report(instance, exit_status, stderr, expected):
    assert allowlist.detect_violation(exit_status, stderr, instance) == expected


def test_a_denied_write_to_a_permitted_executable_is_named_rather_than_dropped(instance):
    stderr = f"PermissionError: [Errno 1] Operation not permitted: '{instance.counted_object}'\n".encode()
    assert allowlist.detect_violation(1, stderr, instance) == "outside_write"


@pytest.mark.parametrize("suffix", ["", "/out.json"])
def test_a_denial_naming_only_the_writable_root_is_unclassified_and_not_dropped(instance, suffix):
    stderr = f"Operation not permitted: '{instance.writable_root}{suffix}'".encode()
    assert allowlist.detect_violation(9, stderr, instance) == allowlist.UNCLASSIFIED


def test_the_class_does_not_turn_on_whether_the_denied_path_exists_here(instance, tmp_path):
    absent = tmp_path / "never-created.txt"
    present = tmp_path / "created.txt"
    present.write_text("x")
    named = [
        allowlist.detect_violation(1, f"Operation not permitted: '{p}'\n".encode(), instance)
        for p in (absent, present, Path("/etc"))
    ]
    assert named == ["outside_write"] * 3


@pytest.fixture
def withholding(shipped, scratch, tmp_path):
    store = tmp_path / "store"
    store.mkdir()
    value = allowlist.instantiate(
        shipped, hypothesis=_hypothesis(), counted_object=BACKEND, scratch_dir=scratch, withheld_roots=[store]
    )
    return value, Path(value.withheld_roots[0])


def _denied(path):
    return f"PermissionError: [Errno 1] Operation not permitted: '{path}'\n".encode()


@pytest.mark.parametrize("leaf", ["", "/substrate.sqlite", "/nested/never-created.db"])
def test_a_denied_path_within_a_withheld_root_is_named_a_withheld_read(withholding, leaf):
    value, store = withholding
    assert allowlist.detect_violation(1, _denied(f"{store}{leaf}"), value) == "withheld_read"


def test_a_symlink_into_a_withheld_root_is_named_by_where_it_leads(withholding, tmp_path):
    value, store = withholding
    alias = tmp_path / "alias"
    alias.symlink_to(store)
    assert allowlist.detect_violation(1, _denied(alias / "substrate.sqlite"), value) == "withheld_read"


def test_a_withheld_root_names_only_paths_within_it(withholding):
    value, store = withholding
    assert allowlist.detect_violation(1, _denied(f"{store}-sibling/x"), value) == "outside_write"
    assert allowlist.detect_violation(1, _denied(store.parent), value) == "outside_write"


def test_a_withheld_read_outranks_an_outside_write_in_one_report(withholding):
    value, store = withholding
    stderr = _denied("/etc/planted.txt") + _denied(store / "substrate.sqlite")
    assert allowlist.detect_violation(1, stderr, value) == "withheld_read"


def test_without_withheld_roots_no_denied_path_is_a_withheld_read(instance, tmp_path):
    assert instance.withheld_roots == ()
    assert allowlist.detect_violation(1, _denied(tmp_path / "store" / "substrate.sqlite"), instance) == "outside_write"
