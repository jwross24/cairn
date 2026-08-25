import copy
import json
import re
import sqlite3
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from cairn import gateplan

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers  # noqa: E402
from mutants import gateplan_mutants  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fuzz_corpus" / "gateplan"
COMMITTED = json.loads((ROOT / "bundle" / "gate_plan.json").read_text())["steps"]

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children, max_size=3) | st.dictionaries(st.text(), children, max_size=3),
    max_leaves=6,
)
arbitrary_plans = st.lists(st.dictionaries(st.text(), json_values, max_size=4), max_size=6)


def _refusal(plan_rows):
    try:
        gateplan.GatePlan.load(plan_rows)
    except gateplan.PlanInvalid as invalid:
        return invalid.reason
    return None


def _committed_is_valid(reason):
    return reason is None


@given(plan_rows=arbitrary_plans)
@settings(max_examples=500)
def test_an_arbitrary_plan_document_is_either_refused_by_reason_or_carries_every_required_step(plan_rows):
    reason = _refusal(plan_rows)
    if reason is None:
        loaded = gateplan.GatePlan.load(plan_rows)
        assert set(gateplan.REQUIRED_STEPS) <= {step.step for step in loaded.steps}
        return
    assert isinstance(reason, str) and reason


@pytest.mark.parametrize("plan_rows", [None, 0, "steps", 3.5, True, {}, {"steps": []}], ids=lambda v: type(v).__name__ + str(v)[:8])
def test_a_plan_that_is_not_a_list_is_refused_by_type(plan_rows):
    with pytest.raises(gateplan.PlanInvalid, match="plan-not-a-list:"):
        gateplan.GatePlan.load(plan_rows)


def test_an_empty_plan_is_refused():
    with pytest.raises(gateplan.PlanInvalid, match="plan-empty"):
        gateplan.GatePlan.load([])


def test_a_ten_thousand_step_plan_is_refused_on_the_first_duplicate_not_by_running_out_of_memory():
    rows = copy.deepcopy(COMMITTED) * 1429
    assert len(rows) > 10_000
    with pytest.raises(gateplan.PlanInvalid, match="duplicate-step-name:7."):
        gateplan.GatePlan.load(rows)


def test_the_committed_plan_loads_unchanged():
    loaded = gateplan.GatePlan.load(copy.deepcopy(COMMITTED))
    assert [step.step for step in loaded.steps] == [row["step"] for row in COMMITTED]
    assert [step.expect for step in loaded.steps] == [row["expect"] for row in COMMITTED]
    assert _committed_is_valid(_refusal(copy.deepcopy(COMMITTED)))


MUTATIONS = {
    "drop_required": lambda rows: [r for r in rows if r["step"] != "verifier_selftest_crash"],
    "duplicate_name": lambda rows: rows[:2] + [{**rows[2], "step": rows[1]["step"]}] + rows[3:],
    "rename_expect": lambda rows: [{k: v for k, v in r.items() if k != "expect"} | {"expected": r["expect"]} if i == 1 else r for i, r in enumerate(rows)],
    "unknown_field": lambda rows: [{**r, "scope": "selftest"} if i == 0 else r for i, r in enumerate(rows)],
    "unknown_kind": lambda rows: [{**r, "kind": "handwave"} if i == 0 else r for i, r in enumerate(rows)],
    "expect_outside_vocabulary": lambda rows: [{**r, "expect": "green"} if i == 1 else r for i, r in enumerate(rows)],
    "fixture_field_wrong_type": lambda rows: [{**r, "fixture": 7} if r.get("kind") == gateplan.KIND_VERIFIER else r for r in rows],
    "entry_outside_vocabulary": lambda rows: [{**r, "entry": "ellcard"} if r.get("kind") == gateplan.KIND_VERIFIER else r for r in rows],
    "x_not_decimal": lambda rows: [{**r, "x": "three"} if r.get("entry") == gateplan.ENTRY_VERIFY else r for r in rows],
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_every_mutation_of_the_committed_plan_is_refused_with_a_named_path(name):
    mutated = MUTATIONS[name](copy.deepcopy(COMMITTED))
    reason = _refusal(mutated)
    assert reason is not None, f"{name} loaded when it should have been refused"
    assert re.match(r"[a-z-]+:", reason), reason


@given(plan_rows=arbitrary_plans)
@settings(max_examples=500, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_refusing_a_plan_writes_no_gate_runs_row_and_spawns_no_subprocess(plan_rows, tmp_path_factory, popen_spy):
    directory = tmp_path_factory.mktemp("noside")
    sub = helpers.open_writer(directory)
    sub.close()
    _refusal(plan_rows)
    conn = sqlite3.connect(f"file:{directory / 'substrate.sqlite'}?mode=ro", uri=True)
    try:
        assert conn.execute("SELECT count(*) FROM gate_runs").fetchone()[0] == 0
    finally:
        conn.close()
    assert popen_spy == []


@pytest.mark.parametrize("path", sorted(CORPUS.glob("*.json")), ids=lambda p: p.stem)
def test_fuzz_corpus_replay(path):
    case = json.loads(path.read_text())
    assert case["expect"] == "PlanInvalid"
    with pytest.raises(gateplan.PlanInvalid, match=re.escape(case["match"])):
        gateplan.GatePlan.load(case["steps"])


def _unknown_kind_plan():
    rows = copy.deepcopy(COMMITTED)
    rows.append({"step": "extra", "kind": "handwave", "expect": gateplan.EXPECT_PASS})
    return rows


def test_loader_skips_unknown_steps_mutant_is_killed():
    plan_rows = _unknown_kind_plan()
    assert _refusal(plan_rows) is not None
    with gateplan_mutants.loader_skips_unknown_steps():
        assert _refusal(plan_rows) is None


def test_loader_runs_valid_prefix_mutant_is_killed():
    plan_rows = copy.deepcopy(COMMITTED)
    plan_rows[3] = {"step": "broken", "kind": "handwave", "expect": gateplan.EXPECT_PASS}
    assert _refusal(plan_rows) is not None
    with gateplan_mutants.loader_runs_valid_prefix():
        assert _refusal(plan_rows) is None
