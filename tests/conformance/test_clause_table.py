import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "conformance"))
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))

import skill_contract  # noqa: E402
from skill_contract import CLAUSES, SUBJECTS  # noqa: E402

COVERAGE = Path(__file__).resolve().parent / "COVERAGE.md"


def test_clause_ids_are_unique_and_ordered():
    ids = [clause.id for clause in CLAUSES]
    assert len(ids) == len(set(ids))
    assert ids == sorted(ids)
    assert all(clause.level in skill_contract.LEVELS for clause in CLAUSES)


def test_no_must_clause_carries_a_stub_check():
    for clause in CLAUSES:
        source = inspect.getsource(clause.check)
        assert getattr(clause.check, "__module__", "") == "skill_contract", clause.id
        assert len(source.splitlines()) > 3, f"{clause.id} check is a one-liner, so it cannot discriminate"
        assert clause.id in source, f"{clause.id} check does not name its own clause id"


def test_coverage_table_matches_clauses():
    rows = _coverage_rows()
    assert [row[0] for row in rows] == [clause.id for clause in CLAUSES]
    for row, clause in zip(rows, CLAUSES, strict=True):
        assert row[1] == clause.level, clause.id
        assert row[3] == getattr(clause.check, "__name__", ""), clause.id


def test_every_registered_subject_is_a_skill_subject():
    assert len({subject.name for subject in SUBJECTS}) == len(SUBJECTS)
    assert any(subject.conforming for subject in SUBJECTS)
    assert any(not subject.conforming for subject in SUBJECTS)
    assert set(skill_contract.EXPECTED_SHOULD) == {subject.name for subject in SUBJECTS}


def _coverage_rows():
    rows = []
    for line in COVERAGE.read_text().splitlines():
        if not line.startswith("| S2-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append((cells[0], cells[1], cells[2], cells[-1].replace("`", "")))
    return rows
