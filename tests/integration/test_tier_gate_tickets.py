import json
import shutil
import sys
from pathlib import Path

import pytest

from cairn import bundle, prefilter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

STATEMENT = "b" * 64
OTHER_STATEMENT = "c" * 64
AT = "2026-09-08T00:00:00.000000+00:00"
LATER = "2026-09-08T00:00:01.000000+00:00"

ALL_QUIET = dict.fromkeys(prefilter.REQUIRED_FILTERS, prefilter.QUIET)


def with_verdict(name, verdict):
    return {**ALL_QUIET, name: verdict}


@pytest.fixture
def gate(tmp_path, pinned_bundle):
    bundle_path, pin_path = pinned_bundle()
    sub = helpers.open_writer(tmp_path)
    yield sub, bundle.GateBundle.open(bundle_path, pin_path)
    sub.close()


def nodes_of_kind(sub, kind):
    return sub.conn.execute("SELECT COUNT(*) FROM nodes WHERE kind = ?", (kind,)).fetchone()[0]


def variant_source(tmp_path):
    """A gate-bundle source that differs from the repository's in one pinned value, so it hashes apart."""
    src = tmp_path / "bundle-variant"
    shutil.copytree(Path(__file__).resolve().parents[2] / "bundle", src)
    auditor = json.loads((src / "auditor.json").read_text())
    auditor["f"] = "0.02"
    (src / "auditor.json").write_text(json.dumps(auditor))
    return src


def test_a_complete_quiet_battery_admits_tier_one_and_round_trips_through_the_substrate(gate):
    sub, gate_bundle = gate
    digest, result = prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert result.passed and result.missing == () and result.rejected == ()
    assert nodes_of_kind(sub, prefilter.KIND) == 1
    assert prefilter.result_for(sub, digest) == result
    assert prefilter.read(sub, gate_bundle, STATEMENT) == result
    assert prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_flagged_but_complete_battery_still_admits_tier_one_and_keeps_the_flag(gate):
    sub, gate_bundle = gate
    _, result = prefilter.record(
        sub,
        gate_bundle,
        statement_hash=STATEMENT,
        verdicts=with_verdict(prefilter.BOUNDED_PROVER, prefilter.FLAG),
        flags=(prefilter.BOUNDED_PROVER,),
        at=AT,
    )
    assert result.flagged == (prefilter.BOUNDED_PROVER,)
    assert result.passed
    assert prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_rejecting_filter_denies_tier_one(gate):
    sub, gate_bundle = gate
    _, result = prefilter.record(
        sub, gate_bundle, statement_hash=STATEMENT, verdicts=with_verdict(prefilter.VACUITY, prefilter.REJECT), at=AT
    )
    assert result.rejected == (prefilter.VACUITY,)
    assert not result.passed
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_an_unrun_filter_denies_tier_one_and_is_not_read_as_a_quiet_one(gate):
    sub, gate_bundle = gate
    partial = {name: prefilter.QUIET for name in prefilter.REQUIRED_FILTERS if name != prefilter.VACUITY}
    _, result = prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=partial, at=AT)
    assert result.missing == (prefilter.VACUITY,)
    assert result.rejected == ()
    assert not result.passed
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_an_absent_record_denies_tier_one(gate):
    sub, gate_bundle = gate
    prefilter.record(sub, gate_bundle, statement_hash=OTHER_STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert prefilter.read(sub, gate_bundle, STATEMENT) is None
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_result_recorded_under_another_bundle_is_not_read_for_this_one(gate, tmp_path, pinned_bundle):
    sub, gate_bundle = gate
    other = bundle.GateBundle.open(*pinned_bundle(name="other", src=variant_source(tmp_path)))
    prefilter.record(sub, other, statement_hash=STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert nodes_of_kind(sub, prefilter.KIND) == 1
    assert prefilter.read(sub, gate_bundle, STATEMENT) is None
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)
    assert prefilter.admits_tier_one(sub, other, STATEMENT)


def test_the_most_recent_result_for_the_statement_is_the_one_read(gate):
    sub, gate_bundle = gate
    prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=ALL_QUIET, at=AT)
    assert prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)
    _, later = prefilter.record(
        sub,
        gate_bundle,
        statement_hash=STATEMENT,
        verdicts=with_verdict(prefilter.EXISTS_IMPLICATION, prefilter.REJECT),
        at=LATER,
    )
    assert prefilter.read(sub, gate_bundle, STATEMENT) == later
    assert not prefilter.admits_tier_one(sub, gate_bundle, STATEMENT)


def test_a_malformed_record_is_refused_and_writes_no_node(gate):
    sub, gate_bundle = gate
    with pytest.raises(prefilter.PrefilterError, match="not one of"):
        prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts=with_verdict(prefilter.VACUITY, "PASS"))
    with pytest.raises(prefilter.PrefilterError, match="not in the battery"):
        prefilter.record(sub, gate_bundle, statement_hash=STATEMENT, verdicts={**ALL_QUIET, "invented": "QUIET"})
    with pytest.raises(prefilter.PrefilterError, match="carry no flag"):
        prefilter.record(
            sub, gate_bundle, statement_hash=STATEMENT, verdicts=with_verdict(prefilter.VACUITY, prefilter.FLAG)
        )
    assert nodes_of_kind(sub, prefilter.KIND) == 0
