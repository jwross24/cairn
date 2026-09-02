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
from skill_contract import CLAUSES, MUST, SUBJECTS, Context  # noqa: E402

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="the harness pins a gate bundle through uappnd, a macOS/BSD chflags bit; the Linux arm is cairn-hcl",
)

FIXTURES = str(ROOT / "tests" / "fixtures")
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
def harness(tmp_path_factory):
    from cairn import bundle, substrate

    root = tmp_path_factory.mktemp("conformance")
    bundle_path, pin_path = root / "gate-bundle.sqlite", root / "gate-bundle.pin"
    bundle.build(ROOT / "bundle", bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    gate = bundle.GateBundle.open(bundle_path, pin_path)
    os.environ["CAIRN_DB"] = str(root / "substrate.sqlite")
    try:
        with substrate.Substrate.open(root / "substrate.sqlite") as sub:
            yield _context(root, sub, gate.verifier_config(), gate.hash)
    finally:
        os.environ.pop("CAIRN_DB", None)
        os.chflags(pin_path, 0)
        pin_path.chmod(0o644)


@pytest.fixture(scope="module")
def sweep(harness):
    handler = _Records()
    logger = logging.getLogger("cairn")
    previous = logger.level
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    try:
        results = {subject.name: skill_contract.run_conformance(subject, harness) for subject in SUBJECTS}
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous)
    conformance_conftest.RESULTS.update(results)
    return results, handler.lines


@pytest.fixture(scope="module")
def verdicts(sweep):
    return sweep[0]


@pytest.mark.parametrize(("subject", "clause"), CASES, ids=IDS)
def test_clause(subject, clause, verdicts):
    verdict = next(v for v in verdicts[subject.name] if v.clause_id == clause.id)
    if clause.level != MUST:
        expected = skill_contract.EXPECTED_SHOULD[subject.name][clause.id]
        assert verdict.status == expected, f"{subject.name} {clause.id}: {verdict.reason}"
        return
    if subject.conforming:
        assert verdict.status == skill_contract.PASS, f"{subject.name} {clause.id}: {verdict.reason}"
        return
    expected = skill_contract.FAIL if clause.id in subject.expected_must_failures else skill_contract.PASS
    assert verdict.status == expected, f"{subject.name} {clause.id}: {verdict.reason}"


@pytest.mark.parametrize("name", [subject.name for subject in skill_contract.CONFORMING])
def test_every_conforming_subject_scores_every_must_clause(name, verdicts):
    passed, total = skill_contract.must_score(verdicts[name])
    assert (passed, total) == (total, len(skill_contract.MUST_IDS))
    assert skill_contract.failures(verdicts[name]) == frozenset()


def test_the_m1_baseline_skills_are_registered_as_conforming_subjects():
    assert {s.name for s in skill_contract.CONFORMING} >= {"toy_curve", "rho_dp", "bsgs", "instance_maker"}


def test_the_planted_fixture_fails_exactly_its_declared_must_clauses(verdicts):
    observed = skill_contract.failures(verdicts["nonconforming"])
    assert observed == skill_contract.NONCONFORMING.expected_must_failures
    assert len(observed) >= 2, "a harness whose checks are stubs cannot fail the planted fixture"


def test_every_must_clause_has_a_negative_witness(verdicts):
    witnessed = set()
    for subject in SUBJECTS:
        if not subject.conforming:
            witnessed |= skill_contract.failures(verdicts[subject.name])
    assert witnessed == set(skill_contract.MUST_IDS)


def test_stubbing_a_must_check_moves_its_witness_verdict_set(harness):
    clause_id = "S2-08"
    subject = skill_contract.WITNESS
    index = next(i for i, c in enumerate(skill_contract.CLAUSES) if c.id == clause_id)
    real = skill_contract.CLAUSES[index]
    skill_contract.CLAUSES[index] = skill_contract.Clause(
        clause_id, MUST, "stub", lambda s, c: skill_contract.Verdict(clause_id, MUST, skill_contract.PASS, "")
    )
    try:
        stubbed = skill_contract.failures(skill_contract.run_conformance(subject, harness))
    finally:
        skill_contract.CLAUSES[index] = real
    assert clause_id in subject.expected_must_failures
    assert clause_id not in stubbed
    assert stubbed != subject.expected_must_failures


def test_every_verdict_is_logged_once_per_subject_and_clause(sweep):
    results, lines = sweep
    logged = [(line["subject"], line["clause_id"]) for line in lines]
    assert sorted(logged) == sorted((name, clause.id) for name in results for clause in CLAUSES)
    assert len(logged) == len(set(logged))


def test_the_json_test_log_carries_a_record_per_clause(harness, json_test_log):
    skill_contract.run_conformance(skill_contract.NONCONFORMING, harness)
    records = [
        json.loads(line)
        for line in json_test_log.read_text().splitlines()
        if line.strip() and json.loads(line).get("step") == skill_contract.LOG_STEP
    ]
    assert [r["clause_id"] for r in records] == [clause.id for clause in CLAUSES]
    assert {r["subject"] for r in records} == {"nonconforming"}


def test_discrepancies_exist_only_for_an_xfail(verdicts):
    xfail = [v for row in verdicts.values() for v in row if v.status == skill_contract.XFAIL]
    assert DISCREPANCIES.exists() == bool(xfail)
