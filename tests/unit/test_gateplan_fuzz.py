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
from mutants import gateplan_mutants

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "tests" / "fuzz_corpus" / "gateplan"
COMMITTED = json.loads((ROOT / "bundle" / "gate_plan.json").read_text())["steps"]

json_values = st.recursive(
    st.none() | st.booleans() | st.integers() | st.text(),
    lambda children: st.lists(children, max_size=3) | st.dictionaries(st.text(), children, max_size=3),
    max_leaves=6,
)
arbitrary_plans = st.lists(st.dictionaries(st.text(), json_values, max_size=4), max_size=6)

PERTURBATIONS = (
    "duplicate_name",
    "bad_expect",
    "bad_kind",
    "extra_field",
    "bad_entry",
    "bad_x",
    "drop_field",
    "wrong_type_fixture",
)


@st.composite
def near_miss_plans(draw):
    rows = [dict(row) for row in COMMITTED]
    mode = draw(st.sampled_from(["intact", "subset", "perturbed"]))
    if mode == "subset":
        keep = draw(st.lists(st.booleans(), min_size=len(rows), max_size=len(rows)))
        return [row for row, flag in zip(rows, keep, strict=True) if flag]
    if mode == "intact":
        return rows
    index = draw(st.integers(min_value=0, max_value=len(rows) - 1))
    how = draw(st.sampled_from(PERTURBATIONS))
    row = rows[index]
    if how == "duplicate_name" and index > 0:
        row["step"] = rows[draw(st.integers(min_value=0, max_value=index - 1))]["step"]
    elif how == "bad_expect":
        row["expect"] = draw(st.none() | st.text() | st.integers())
    elif how == "bad_kind":
        row["kind"] = draw(st.none() | st.text() | st.integers())
    elif how == "extra_field":
        row[draw(st.sampled_from(["scope", "cmd", "note"]))] = draw(json_values)
    elif how == "bad_entry" and row.get("kind") == gateplan.KIND_VERIFIER:
        row["entry"] = draw(st.none() | st.text())
    elif how == "bad_x" and row.get("entry") == gateplan.ENTRY_VERIFY:
        row["x"] = draw(st.none() | st.text() | st.integers())
    elif how == "wrong_type_fixture" and row.get("kind") == gateplan.KIND_VERIFIER:
        row["fixture"] = draw(st.none() | st.integers() | st.lists(st.text(), max_size=2))
    elif how == "drop_field":
        row.pop(draw(st.sampled_from(sorted(row))), None)
    return rows


def _refusal(plan_rows):
    try:
        gateplan.GatePlan.load(plan_rows)
    except gateplan.PlanInvalid as invalid:
        return invalid.reason
    return None


@given(plan_rows=arbitrary_plans)
@settings(max_examples=500)
def test_an_arbitrary_plan_document_raises_nothing_but_plan_invalid(plan_rows):
    reason = _refusal(plan_rows)
    assert reason is None or (isinstance(reason, str) and re.match(r"[a-z-]+(:|$)", reason))


@given(plan_rows=near_miss_plans())
@settings(max_examples=500)
def test_a_near_miss_plan_either_loads_with_every_required_step_or_names_its_first_bad_path(plan_rows):
    reason = _refusal(plan_rows)
    if reason is None:
        loaded = gateplan.GatePlan.load(plan_rows)
        assert [step.step for step in loaded.steps] == [row["step"] for row in plan_rows]
        assert set(gateplan.REQUIRED_STEPS) <= {step.step for step in loaded.steps}
        return
    assert re.match(r"[a-z-]+(:|$)", reason), reason


@pytest.mark.parametrize(
    "plan_rows", [None, 0, "steps", 3.5, True, {}, {"steps": []}], ids=lambda v: type(v).__name__ + str(v)[:8]
)
def test_a_plan_that_is_not_a_list_is_refused_by_type(plan_rows):
    with pytest.raises(gateplan.PlanInvalid, match="plan-not-a-list:"):
        gateplan.GatePlan.load(plan_rows)


def test_an_empty_plan_is_refused():
    with pytest.raises(gateplan.PlanInvalid, match="plan-empty"):
        gateplan.GatePlan.load([])


def test_a_ten_thousand_step_plan_is_refused_on_the_first_duplicate_not_by_running_out_of_memory():
    rows = copy.deepcopy(COMMITTED) * 1429
    assert len(rows) > 10_000
    with pytest.raises(gateplan.PlanInvalid, match=r"duplicate-step-name:7\."):
        gateplan.GatePlan.load(rows)


def test_the_committed_plan_loads_unchanged():
    loaded = gateplan.GatePlan.load(copy.deepcopy(COMMITTED))
    assert [step.step for step in loaded.steps] == [row["step"] for row in COMMITTED]
    assert [step.expect for step in loaded.steps] == [row["expect"] for row in COMMITTED]


MUTATIONS = {
    "drop_required": (
        lambda rows: [r for r in rows if r["step"] != "verifier_selftest_crash"],
        "missing-required-selftest:verifier_selftest_crash",
    ),
    "duplicate_name": (
        lambda rows: [*rows[:2], {**rows[2], "step": rows[1]["step"]}, *rows[3:]],
        "duplicate-step-name:2.verifier_selftest_pass",
    ),
    "rename_expect": (
        lambda rows: [
            {k: v for k, v in r.items() if k != "expect"} | {"expected": r["expect"]} if i == 1 else r
            for i, r in enumerate(rows)
        ],
        "step-missing-field:1.expect",
    ),
    "unknown_field": (
        lambda rows: [{**r, "scope": "selftest"} if i == 0 else r for i, r in enumerate(rows)],
        "unknown-step-field:0.'scope'",
    ),
    "unknown_kind": (
        lambda rows: [{**r, "kind": "handwave"} if i == 0 else r for i, r in enumerate(rows)],
        "unknown-step-kind:0.'handwave'",
    ),
    "expect_outside_vocabulary": (
        lambda rows: [{**r, "expect": "green"} if i == 1 else r for i, r in enumerate(rows)],
        "expect-outside-vocabulary:1.'green'",
    ),
    "step_fixture_name_wrong_type": (
        lambda rows: [{**r, "fixture": 7} if r.get("kind") == gateplan.KIND_VERIFIER else r for r in rows],
        "step-field-wrong-type:1.fixture",
    ),
    "entry_outside_vocabulary": (
        lambda rows: [{**r, "entry": "ellcard"} if r.get("kind") == gateplan.KIND_VERIFIER else r for r in rows],
        "unknown-verifier-entry:1.'ellcard'",
    ),
    "x_not_decimal": (
        lambda rows: [{**r, "x": "three"} if r.get("entry") == gateplan.ENTRY_VERIFY else r for r in rows],
        "step-field-wrong-type:1.x",
    ),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_every_mutation_of_the_committed_plan_is_refused_with_its_exact_named_path(name):
    mutate, expected_reason = MUTATIONS[name]
    mutated = mutate(copy.deepcopy(COMMITTED))
    with pytest.raises(gateplan.PlanInvalid, match=re.escape(expected_reason)):
        gateplan.GatePlan.load(mutated)


@pytest.fixture(scope="module")
def empty_substrate(tmp_path_factory):
    from cairn.substrate import Substrate

    directory = tmp_path_factory.mktemp("gateplan-fuzz")
    Substrate.open(directory / "substrate.sqlite", role="writer").close()
    return directory / "substrate.sqlite"


@given(plan_rows=st.one_of(arbitrary_plans, near_miss_plans()))
@settings(max_examples=500, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_validating_a_plan_spawns_no_subprocess_and_writes_no_gate_runs_row(plan_rows, popen_spy, empty_substrate):
    _refusal(plan_rows)
    assert popen_spy == []
    conn = sqlite3.connect(f"file:{empty_substrate}?mode=ro", uri=True)
    try:
        assert conn.execute("SELECT count(*) FROM gate_runs").fetchone()[0] == 0
    finally:
        conn.close()


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


def test_every_planted_mutant_is_exercised_by_a_kill_test():
    killed = set()
    for path in (
        Path(__file__),
        Path(__file__).with_name("test_gateplan_validation.py"),
        ROOT / "tests" / "integration" / "test_gateplan.py",
    ):
        killed |= {name for name in gateplan_mutants.ALL if f"gateplan_mutants.{name}(" in path.read_text()}
    assert killed == set(gateplan_mutants.ALL), f"unexercised mutants: {sorted(set(gateplan_mutants.ALL) - killed)}"
