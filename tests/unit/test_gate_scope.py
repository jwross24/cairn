import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import gate_scope
from gate_scope import GATES, codespell_skips, for_gate, main, plan

ROOT = Path(__file__).resolve().parents[2]
CHECK_SH = (ROOT / "scripts" / "check.sh").read_text()

SKIPS = ("lean/vendor", "lean/.lake", "tests/goldens")
PATHS = [
    "src/cairn/instances.py",
    "tests/unit/test_gate_scope.py",
    "scripts/gate_scope.py",
    "research/grounding/rmp_repro.py",
    "lean/vendor/formal_conjectures/NOTICE",
    "README.md",
]


def gate_paths(name, paths=None):
    return for_gate(name, paths if paths is not None else PATHS, SKIPS)


def test_the_python_gates_take_only_the_python_files_inside_the_scope_they_are_given_today():
    assert gate_paths("format") == ["src/cairn/instances.py", "tests/unit/test_gate_scope.py", "scripts/gate_scope.py"]
    assert gate_paths("lint") == gate_paths("format")


def test_the_type_gate_stops_at_src_and_tests_as_its_unscoped_form_does():
    assert gate_paths("types") == ["src/cairn/instances.py", "tests/unit/test_gate_scope.py"]


def test_a_python_file_outside_every_gate_scope_reaches_no_python_gate():
    outside = ["research/grounding/rmp_repro.py"]
    assert gate_paths("format", outside) == []
    assert gate_paths("lint", outside) == []
    assert gate_paths("types", outside) == []


def test_the_spelling_gate_drops_a_path_its_skip_list_covers_and_keeps_the_rest():
    spelled = gate_paths("spelling")
    assert "lean/vendor/formal_conjectures/NOTICE" not in spelled
    assert "README.md" in spelled and "src/cairn/instances.py" in spelled


def test_a_directory_whose_name_merely_starts_with_a_skip_entry_is_not_skipped():
    assert for_gate("spelling", ["lean/vendored/keep.md"], SKIPS) == ["lean/vendored/keep.md"]


def test_the_theater_gate_receives_every_path_and_resolves_its_own_globs():
    assert gate_paths("theater") == PATHS


def test_the_skip_list_is_read_from_the_repository_s_own_codespell_configuration():
    skips = codespell_skips(ROOT)
    assert "lean/vendor" in skips
    assert not any(entry.startswith("./") for entry in skips)


def test_a_tree_without_a_pyproject_yields_no_skips_rather_than_raising(tmp_path):
    assert codespell_skips(tmp_path) == ()


def test_the_plan_names_a_gate_once_per_path_it_takes():
    assert plan(["README.md"], SKIPS) == [("spelling", "README.md"), ("theater", "README.md")]


def test_an_empty_path_list_is_refused_rather_than_planning_nothing(capsys):
    assert main(["plan"]) == gate_scope.USAGE_EXIT
    assert "checks nothing" in capsys.readouterr().err


def test_the_staged_mode_takes_no_paths_of_its_own(capsys):
    assert main(["staged", "extra.py"]) == gate_scope.USAGE_EXIT
    assert "no path arguments" in capsys.readouterr().err


@pytest.mark.parametrize("gate", GATES)
def test_every_gate_the_plan_can_name_is_a_gate_check_sh_runs_in_both_of_its_forms(gate):
    scoped = re.findall(r"^\s*scoped_gate (\w+)\s", CHECK_SH, re.MULTILINE)
    unscoped = re.findall(r"^\s*gate (\w+)\s", CHECK_SH, re.MULTILINE)
    assert gate in scoped
    assert gate in unscoped


def test_the_two_forms_of_the_fast_tier_run_the_same_gates():
    scoped = set(re.findall(r"^\s*scoped_gate (\w+)\s", CHECK_SH, re.MULTILINE))
    unscoped = set(re.findall(r"^\s*gate (\w+)\s", CHECK_SH, re.MULTILINE)) - {"unit-tests", "tests"}
    assert scoped == unscoped == set(GATES)
