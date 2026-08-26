import inspect
import json
import logging
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests" / "conformance"))

import conftest as conformance_conftest  # noqa: E402
import skill_contract  # noqa: E402
from skill_contract import CLAUSES, MUST, SUBJECTS, Context, SkillSubject  # noqa: E402

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="the harness pins a gate bundle through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

FIXTURES = str(ROOT / "tests" / "fixtures")
COVERAGE = Path(__file__).resolve().parent / "COVERAGE.md"
DISCREPANCIES = Path(__file__).resolve().parent / "DISCREPANCIES.md"
CASES = [(subject, clause) for subject in SUBJECTS for clause in CLAUSES]
IDS = [f"{subject.name}-{clause.id}" for subject, clause in CASES]


class _Records(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.DEBUG)
        self.lines = []

    def emit(self, record):
        if getattr(record, "step", None) == skill_contract.LOG_STEP and record.getMessage() == "verdict":
            self.lines.append(dict(record.fields))


def _context(root, sub, config, bundle_hash):
    return Context(
        sub=sub,
        config=config,
        bundle_hash=bundle_hash,
        scratch_root=root / "runs",
        fixtures_path=FIXTURES,
        repo_root=ROOT,
        workspace=root / "workspace",
    )


@pytest.fixture(scope="module")
def sweep(tmp_path_factory):
    from cairn import bundle, substrate

    root = tmp_path_factory.mktemp("conformance")
    bundle_path, pin_path = root / "gate-bundle.sqlite", root / "gate-bundle.pin"
    bundle.build(ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    handler = _Records()
    logger = logging.getLogger("cairn")
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    os.environ["CAIRN_DB"] = str(root / "substrate.sqlite")
    try:
        with substrate.Substrate.open(root / "substrate.sqlite") as sub:
            ctx = _context(root, sub, gate.verifier_config(), gate.hash)
            results = {subject.name: skill_contract.run_conformance(subject, ctx) for subject in SUBJECTS}
    finally:
        os.environ.pop("CAIRN_DB", None)
        logger.removeHandler(handler)
        logger.setLevel(previous)
        os.chflags(pin_path, 0)
        os.chmod(pin_path, 0o644)
    conformance_conftest.RESULTS.update(results)
    return results, handler.lines


@pytest.fixture(scope="module")
def verdicts(sweep):
    return sweep[0]


@pytest.mark.parametrize(("subject", "clause"), CASES, ids=IDS)
def test_clause(subject, clause, verdicts):
    verdict = next(v for v in verdicts[subject.name] if v.clause_id == clause.id)
    if clause.level != MUST:
        assert verdict.status in skill_contract.STATUSES, verdict
        return
    if subject.conforming:
        assert verdict.status == skill_contract.PASS, f"{subject.name} {clause.id}: {verdict.reason}"
        return
    expected = skill_contract.FAIL if clause.id in subject.expected_must_failures else skill_contract.PASS
    assert verdict.status == expected, f"{subject.name} {clause.id}: {verdict.reason}"


def test_the_conforming_subject_scores_every_must_clause(verdicts):
    passed, total = skill_contract.must_score(verdicts["toy_curve"])
    assert (passed, total) == (total, len(skill_contract.MUST_IDS))
    assert skill_contract.failures(verdicts["toy_curve"]) == frozenset()


def test_the_planted_fixture_fails_exactly_its_declared_must_clauses(verdicts):
    observed = skill_contract.failures(verdicts["nonconforming"])
    assert observed == skill_contract.NONCONFORMING.expected_must_failures
    assert len(observed) >= 2, "a harness whose checks are stubs cannot fail the planted fixture"


def test_a_stubbed_must_check_is_caught_by_the_fixture(tmp_path_factory):
    from cairn import bundle, substrate

    stubbed = skill_contract.Clause(
        "S2-01", MUST, "stub", lambda subject, ctx: skill_contract.Verdict("S2-01", MUST, skill_contract.PASS, "stub")
    )
    root = tmp_path_factory.mktemp("stub")
    bundle_path, pin_path = root / "gate-bundle.sqlite", root / "gate-bundle.pin"
    bundle.build(ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    try:
        with substrate.Substrate.open(root / "substrate.sqlite") as sub:
            ctx = _context(root, sub, gate.verifier_config(), gate.hash)
            real = skill_contract.CLAUSES[0]
            skill_contract.CLAUSES[0] = stubbed
            try:
                observed = skill_contract.failures(skill_contract.run_conformance(skill_contract.NONCONFORMING, ctx))
            finally:
                skill_contract.CLAUSES[0] = real
    finally:
        os.chflags(pin_path, 0)
        os.chmod(pin_path, 0o644)
    assert "S2-01" not in observed
    assert observed != skill_contract.NONCONFORMING.expected_must_failures


def test_every_verdict_is_logged_once_per_subject_and_clause(sweep):
    results, lines = sweep
    logged = [(line["subject"], line["clause_id"]) for line in lines]
    assert sorted(logged) == sorted((name, clause.id) for name in results for clause in CLAUSES)
    assert len(logged) == len(set(logged))


def test_the_json_test_log_carries_a_record_per_clause(tmp_path, json_test_log):
    from cairn import bundle, substrate

    bundle_path, pin_path = tmp_path / "gate-bundle.sqlite", tmp_path / "gate-bundle.pin"
    bundle.build(ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    try:
        with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
            ctx = _context(tmp_path, sub, gate.verifier_config(), gate.hash)
            skill_contract.run_conformance(skill_contract.NONCONFORMING, ctx)
    finally:
        os.chflags(pin_path, 0)
        os.chmod(pin_path, 0o644)
    records = [
        json.loads(line)
        for line in json_test_log.read_text().splitlines()
        if line.strip() and json.loads(line).get("step") == skill_contract.LOG_STEP
    ]
    assert [r["clause_id"] for r in records] == [clause.id for clause in CLAUSES]
    assert {r["subject"] for r in records} == {"nonconforming"}


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


def test_discrepancies_exist_only_for_an_xfail(verdicts):
    xfail = [v for row in verdicts.values() for v in row if v.status == skill_contract.XFAIL]
    assert DISCREPANCIES.exists() == bool(xfail)


def _coverage_rows():
    rows = []
    for line in COVERAGE.read_text().splitlines():
        if not line.startswith("| S2-"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        rows.append((cells[0], cells[1], cells[2], cells[-1].replace("`", "")))
    return rows


def test_every_registered_subject_is_a_skill_subject():
    assert all(isinstance(subject, SkillSubject) for subject in SUBJECTS)
    assert len({subject.name for subject in SUBJECTS}) == len(SUBJECTS)
    assert [subject.conforming for subject in SUBJECTS] == [True, False]
