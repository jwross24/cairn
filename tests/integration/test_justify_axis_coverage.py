import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from cairn import claims, justify, selftest, substrate

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import factories
from mutants import justify_mutants

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def axis_writer(tmp_path, monkeypatch):
    monkeypatch.syspath_prepend(str(FIXTURES))
    module = importlib.import_module("skills.multi_axis")
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        certificate = module.certify(sub)
        yield sub, certificate, tmp_path / "attestations.log"


def _invoke(bits):
    process = subprocess.run(
        [sys.executable, "-m", "skills.multi_axis"],
        input=json.dumps({"bits": bits, "seed": 1}),
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
        env={**os.environ, "PYTHONPATH": str(FIXTURES)},
    )
    return json.loads(process.stdout)


def _derive(axis_writer, bits):
    sub, certificate, attest_path = axis_writer
    statement = factories.claim_statement(size=(bits, bits), assumptions=frozenset(), seed=bits)
    claims.write_claim_statement(sub, statement)
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        statement.scope,
        frozenset(),
        producer=(certificate["identity_bundle_hash"], "skill"),
    )
    claims.write_evidence_node(sub, node)
    row = claims.evidence_for(sub, statement.hash)[0]
    ctx = justify.context_for(sub, row, claims.get_claim_statement(sub, statement.hash), attest_path)
    stored = json.loads(sub.get_certificate(certificate["identity_bundle_hash"])["selftest_summary"])
    assert ctx.producer_summary == stored
    assert ctx.attempt_inputs == {"bits": [bits, bits]}
    return justify.derive_tag(sub, statement.hash, attest_path)


@pytest.mark.parametrize(("bits", "axis"), [(20, "algorithm"), (40, "implementation")])
def test_real_plural_certificate_attribution_reaches_history_and_cli(axis_writer, bits, axis):
    output = _invoke(bits)
    records = {record["axis"]: record for record in output["cross_check"]}
    assert records[axis]["result"] == "agree"
    assert all(record["result"] == "untested" for name, record in records.items() if name != axis)
    derivation = _derive(axis_writer, bits)
    coverage = {
        "covered": True,
        "dimensions": {"bits": True},
        "contributions": {"bits": {axis: [bits, bits]}},
    }
    assert derivation.tag == justify.STRONG_EMPIRICAL
    assert derivation.results[0][1].cross_check_coverage.record() == coverage
    sub, _, _ = axis_writer
    history = claims.tag_history_for(sub, derivation.statement_hash)
    assert json.loads(history[-1]["justification"])["cross_check_coverage"] == coverage
    assert justify._payload(derivation)["evidence"][0]["cross_check_coverage"] == coverage


def test_real_plural_fixture_gap_preserves_the_producer_cap(axis_writer):
    output = _invoke(25)
    assert all(record["result"] == "untested" for record in output["cross_check"])
    derivation = _derive(axis_writer, 25)
    assert derivation.tag == justify.CONJECTURE
    coverage = {
        "covered": False,
        "dimensions": {"bits": False},
        "contributions": {"bits": {}},
    }
    assert justify._payload(derivation)["evidence"][0]["cross_check_coverage"] == coverage


def test_unconditional_coverage_is_refused_by_the_real_gap_test(axis_writer):
    with justify_mutants.producer_rule_ignores_range(), pytest.raises(AssertionError):
        test_real_plural_fixture_gap_preserves_the_producer_cap(axis_writer)


def test_real_plural_certificate_matches_the_shared_summary_builder(axis_writer, monkeypatch):
    sub, certificate, _ = axis_writer
    monkeypatch.syspath_prepend(str(FIXTURES))
    module = importlib.import_module("skills.multi_axis")
    stored = json.loads(sub.get_certificate(certificate["identity_bundle_hash"])["selftest_summary"])
    assert stored["cross_check"] == selftest.cross_check_summary(module)
