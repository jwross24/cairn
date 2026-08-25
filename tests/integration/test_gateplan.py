import functools
import json
import shutil
import sys
from pathlib import Path

import pytest

from cairn import attest, bundle, claims, gateplan, kat, keys, log

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers
from mutants import gateplan_mutants, verifier_mutants

ROOT = Path(__file__).resolve().parents[2]
WEAK_ACCEPT = {"rc": 0, "stdout": None, "stderr_empty": False}


@pytest.fixture
def plan_env(tmp_path, pinned_bundle, clear_flags, db_snapshot):
    def make(name="deploy", src=ROOT / "bundle"):
        bundle_path, pin_path = pinned_bundle(name=name, src=src)
        gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
        attest_path = tmp_path / f"{name}-attestations.log"
        clear_flags(attest_path)
        attest.init(attest_path, gate_bundle.waiver_target())
        sub = helpers.open_writer(tmp_path, name=f"{name}-substrate.sqlite")
        return gate_bundle, sub, attest_path

    return make


def _source_copy(tmp_path, name, edit):
    directory = tmp_path / f"src-{name}"
    shutil.copytree(ROOT / "bundle", directory)
    edit(directory)
    return directory


def _run_plan(env, db_snapshot, label, *, src=None, name="deploy"):
    gate_bundle, sub, attest_path = env(name=name) if src is None else env(name=name, src=src)
    result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    db_snapshot(sub.conn, label)
    return result, sub


def test_the_committed_plan_runs_every_step_green_against_the_built_bundle(plan_env, db_snapshot):
    result, sub = _run_plan(plan_env, db_snapshot, "committed-plan")
    assert result.ok
    assert [s.step for s in result.steps] == [
        "canon_kat",
        "verifier_selftest_pass",
        "verifier_selftest_fail_xP_ne_Q",
        "verifier_selftest_crash",
        "verifier_selftest_crash_control",
        "waiver_cannot_advance",
        "tier_gate_selftest_two_above",
    ]
    assert [s.observed for s in result.steps] == [
        "pass",
        "OK",
        "FAIL xP-ne-Q",
        "FAIL backend-crash",
        "OK",
        "no-ticket",
        "TierRefused(tier-two-above)",
    ]
    assert all(s.result == "pass" for s in result.steps)
    assert len({s.run_id for s in result.steps}) == len(result.steps)
    for step in result.steps:
        row = claims.get_gate_run(sub, step.run_id)
        assert row["gate"] == "gate_plan" and row["plan_step"] == step.step and row["result"] == "pass"
        assert row["bundle_hash"] == result.bundle_hash and row["pin_hash"] == result.pin_hash
    sub.close()


def test_a_weakened_accept_predicate_fails_the_crash_step_and_blocks_the_rest(tmp_path, plan_env, db_snapshot):
    def weaken(directory):
        path = directory / "verifier.json"
        obj = json.loads(path.read_text())
        obj["accept"] = WEAK_ACCEPT
        path.write_text(json.dumps(obj))

    src = _source_copy(tmp_path, "weak-accept", weaken)
    result, sub = _run_plan(plan_env, db_snapshot, "weak-accept", src=src, name="weak-accept")
    assert not result.ok
    failed = result.first_failure
    assert failed.step == "verifier_selftest_crash"
    assert failed.observed == "OK" and failed.expected == "FAIL backend-crash"
    assert gateplan.MISMATCH_REASON in failed.reasons
    assert [s.step for s in result.steps if s.result == "blocked"] == [
        "verifier_selftest_crash_control",
        "waiver_cannot_advance",
        "tier_gate_selftest_two_above",
    ]
    for step in result.steps:
        if step.result == "blocked":
            assert step.reasons == (f"{gateplan.BLOCKED_PREFIX}verifier_selftest_crash",)
    assert [s.result for s in result.steps[:3]] == ["pass", "pass", "pass"]
    assert failed.stdout_digest and failed.stderr_digest and failed.stdout_digest != failed.stderr_digest
    assert f"observed:{failed.observed}" in failed.reasons
    assert all(s.stdout_digest is None for s in result.steps if s.result == "blocked")
    sub.close()


def test_a_verifier_script_without_the_xP_eq_Q_check_fails_that_step_and_blocks_the_rest(plan_env, db_snapshot):
    with verifier_mutants.script_without_xP_eq_Q():
        gate_bundle, sub, attest_path = plan_env(name="weak-script")
    result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    db_snapshot(sub.conn, "weak-script")
    assert not result.ok
    failed = result.first_failure
    assert failed.step == "verifier_selftest_fail_xP_ne_Q"
    assert failed.observed == "OK" and failed.expected == "FAIL xP-ne-Q"
    assert [s.step for s in result.steps if s.result == "blocked"] == [
        "verifier_selftest_crash",
        "verifier_selftest_crash_control",
        "waiver_cannot_advance",
        "tier_gate_selftest_two_above",
    ]
    sub.close()


def test_a_bundle_whose_plan_lacks_the_xP_ne_Q_step_is_refused_before_any_step_runs(tmp_path, plan_env, db_snapshot):
    def drop(directory):
        path = directory / "gate_plan.json"
        obj = json.loads(path.read_text())
        obj["steps"] = [s for s in obj["steps"] if s["step"] != "verifier_selftest_fail_xP_ne_Q"]
        path.write_text(json.dumps(obj))

    src = _source_copy(tmp_path, "no-xp-step", drop)
    gate_bundle, sub, _ = plan_env(name="no-xp-step", src=src)
    before = db_snapshot(sub.conn, "no-xp-step-before")
    with pytest.raises(gateplan.PlanInvalid) as info:
        gateplan.GatePlan.from_bundle(gate_bundle)
    assert info.value.reason == "missing-required-selftest:verifier_selftest_fail_xP_ne_Q"
    assert db_snapshot(sub.conn, "no-xp-step-after")["gate_runs"] == before["gate_runs"]
    sub.close()


def test_a_malformed_plan_row_in_the_bundle_fails_closed_with_no_gate_runs(tmp_path, plan_env, db_snapshot):
    def malform(directory):
        path = directory / "gate_plan.json"
        obj = json.loads(path.read_text())
        obj["steps"][1]["expect"] = "definitely-not-in-the-vocabulary"
        path.write_text(json.dumps(obj))

    src = _source_copy(tmp_path, "malformed", malform)
    gate_bundle, sub, _ = plan_env(name="malformed", src=src)
    before = db_snapshot(sub.conn, "malformed-before")
    with pytest.raises(gateplan.PlanInvalid) as info:
        gateplan.GatePlan.from_bundle(gate_bundle)
    assert info.value.reason.startswith("expect-outside-vocabulary:1.")
    assert db_snapshot(sub.conn, "malformed-after")["gate_runs"] == before["gate_runs"]
    sub.close()



def test_the_run_logs_exactly_one_record_per_step(plan_env, db_snapshot, caplog):
    import logging

    caplog.set_level(logging.INFO, logger=log.LOGGER_NAME)
    result, sub = _run_plan(plan_env, db_snapshot, "caplog")
    steps = [r for r in caplog.records if r.name == log.LOGGER_NAME and r.getMessage() == "step"]
    assert [r.fields["step"] for r in steps] == [s.step for s in result.steps]
    assert all("stdout_digest" not in r.fields for r in steps)
    assert all(r.fields["run_id"] and isinstance(r.fields["wall_ms"], int) for r in steps)
    sub.close()


def test_the_waiver_step_fails_when_record_zero_does_not_name_the_fixture_waiver(tmp_path, pinned_bundle, clear_flags, db_snapshot):
    bundle_path, pin_path = pinned_bundle(name="wrong-waiver")
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    attest_path = tmp_path / "wrong-waiver.log"
    clear_flags(attest_path)
    attest.init(attest_path, keys.hypothesis_key(gate_bundle.gate_plan["fixtures"]["admitted_hypothesis"]))
    sub = helpers.open_writer(tmp_path, name="wrong-waiver.sqlite")
    result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    db_snapshot(sub.conn, "wrong-waiver")
    failed = result.first_failure
    assert failed.step == "waiver_cannot_advance" and failed.observed == "waiver-record-absent"
    assert [s.step for s in result.steps if s.result == "blocked"] == ["tier_gate_selftest_two_above"]
    sub.close()


def test_an_invalid_plan_spawns_no_gp_and_the_valid_prefix_mutant_shows_the_refusal_is_load_bearing(tmp_path, plan_env, db_snapshot, popen_spy):
    def drop(directory):
        path = directory / "gate_plan.json"
        obj = json.loads(path.read_text())
        obj["steps"] = [s for s in obj["steps"] if s["step"] != "verifier_selftest_crash_control"]
        path.write_text(json.dumps(obj))

    src = _source_copy(tmp_path, "load-bearing", drop)
    gate_bundle, sub, attest_path = plan_env(name="load-bearing", src=src)
    before = db_snapshot(sub.conn, "load-bearing-before")
    spawns_at_start = len(popen_spy)
    with pytest.raises(gateplan.PlanInvalid, match="missing-required-selftest:verifier_selftest_crash_control"):
        gateplan.GatePlan.from_bundle(gate_bundle)
    assert len(popen_spy) == spawns_at_start
    assert db_snapshot(sub.conn, "load-bearing-refused")["gate_runs"] == before["gate_runs"]
    with gateplan_mutants.loader_runs_valid_prefix():
        gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    assert len(popen_spy) > spawns_at_start
    assert db_snapshot(sub.conn, "load-bearing-mutant")["gate_runs"] > before["gate_runs"]
    sub.close()


def _edit_plan(directory, mutate):
    path = directory / "gate_plan.json"
    obj = json.loads(path.read_text())
    mutate(obj)
    path.write_text(json.dumps(obj))


def test_the_crash_control_half_fails_the_plan_when_it_is_starved_of_stack(tmp_path, plan_env, db_snapshot):
    def starve(obj):
        for step in obj["steps"]:
            if step["step"] == "verifier_selftest_crash_control":
                step["stack"] = "8M"

    src = _source_copy(tmp_path, "starved-control", lambda d: _edit_plan(d, starve))
    result, sub = _run_plan(plan_env, db_snapshot, "starved-control", src=src, name="starved-control")
    failed = result.first_failure
    assert failed.step == "verifier_selftest_crash_control"
    assert failed.expected == "OK" and failed.observed == "FAIL backend-crash"
    assert [s.step for s in result.steps if s.result == "blocked"] == ["waiver_cannot_advance", "tier_gate_selftest_two_above"]
    sub.close()


def test_a_non_empty_waivable_checks_list_fails_the_waiver_step(tmp_path, plan_env, db_snapshot):
    def allow_a_waiver(directory):
        (directory / "waivable_checks.json").write_text(json.dumps(["tier_gate"]))

    src = _source_copy(tmp_path, "waivable", allow_a_waiver)
    result, sub = _run_plan(plan_env, db_snapshot, "waivable", src=src, name="waivable")
    failed = result.first_failure
    assert failed.step == "waiver_cannot_advance" and failed.observed == "waivable-checks-nonempty"
    sub.close()


def test_a_recorded_waiver_hypothesis_removes_ticket_absent_and_fails_the_waiver_step(plan_env, db_snapshot):
    gate_bundle, sub, attest_path = plan_env(name="seeded-waiver")
    claims.write_hypothesis_object(sub, claims.HypothesisObject(**gate_bundle.waiver_hypothesis()))
    result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    db_snapshot(sub.conn, "seeded-waiver")
    failed = result.first_failure
    assert failed.step == "waiver_cannot_advance" and failed.observed == "admitted"
    assert "ticket-absent" not in failed.reasons
    sub.close()


def test_a_corrupted_canonicalizer_vector_fails_the_canon_kat_step_first(tmp_path, plan_env, db_snapshot, monkeypatch):
    vectors = tmp_path / "corrupt_kat.json"
    data = json.loads((ROOT / "tests" / "vectors" / "canon_kat.json").read_text())
    data["vectors"][0]["expected"] = "00" * 32
    vectors.write_text(json.dumps(data))
    monkeypatch.setattr(gateplan.kat, "run", functools.partial(kat.run, vectors))
    result, sub = _run_plan(plan_env, db_snapshot, "corrupt-kat", name="corrupt-kat")
    failed = result.first_failure
    assert failed.step == "canon_kat" and failed.observed == "fail"
    assert any(reason.startswith("kat:") for reason in failed.reasons)
    assert all(s.result == "blocked" for s in result.steps[1:])
    sub.close()


def test_a_tier_gate_refusal_for_another_reason_fails_the_two_above_step(plan_env, db_snapshot):
    gate_bundle, sub, attest_path = plan_env(name="wrong-reason")
    with gateplan_mutants.tier_gate_skips_recording():
        result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    db_snapshot(sub.conn, "wrong-reason")
    failed = result.first_failure
    assert failed.step == "tier_gate_selftest_two_above"
    assert failed.observed.startswith("TierRefused(") and "tier-two-above" not in failed.observed
    assert "ticket-absent" in failed.observed
    sub.close()


def test_an_unrecorded_tier_refusal_fails_the_two_above_step(plan_env, db_snapshot):
    gate_bundle, sub, attest_path = plan_env(name="no-refusal-row")
    with gateplan_mutants.tier_gate_drops_refusal_rows():
        result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    db_snapshot(sub.conn, "no-refusal-row")
    failed = result.first_failure
    assert failed.step == "tier_gate_selftest_two_above" and failed.observed == "refusal-unrecorded"
    sub.close()


def test_failed_and_blocked_steps_each_persist_their_gate_runs_row_with_reasons(tmp_path, plan_env, db_snapshot):
    def weaken(directory):
        path = directory / "verifier.json"
        obj = json.loads(path.read_text())
        obj["accept"] = WEAK_ACCEPT
        path.write_text(json.dumps(obj))

    src = _source_copy(tmp_path, "persisted", weaken)
    result, sub = _run_plan(plan_env, db_snapshot, "persisted", src=src, name="persisted")
    rows = {row["plan_step"]: row for row in (claims.get_gate_run(sub, s.run_id) for s in result.steps)}
    assert len(rows) == len(result.steps)
    for step in result.steps:
        row = rows[step.step]
        assert row["result"] == step.result
        assert json.loads(row["reasons"]) == list(step.reasons)
        if step.result == "blocked":
            assert json.loads(row["reasons"]) == ["blocked-by:verifier_selftest_crash"]
    assert [rows[s.step]["result"] for s in result.steps] == ["pass", "pass", "pass", "fail", "blocked", "blocked", "blocked"]
    sub.close()


def test_a_bundle_with_no_fixtures_block_is_refused_by_name_not_by_key_error(tmp_path, pinned_bundle):
    src = _source_copy(tmp_path, "no-fixtures", lambda d: _edit_plan(d, lambda o: o.pop("fixtures")))
    bundle_path, pin_path = pinned_bundle(name="no-fixtures", src=src)
    gate_bundle = bundle.GateBundle.open(bundle_path, pin_path)
    with pytest.raises(bundle.BundleError, match=r"gate_plan\.fixtures\.waiver_hypothesis"):
        gate_bundle.waiver_target()


def test_a_plan_missing_its_cost_profile_fixture_fails_closed_before_any_step(tmp_path, plan_env, db_snapshot):
    src = _source_copy(tmp_path, "no-profile", lambda d: _edit_plan(d, lambda o: o["fixtures"].pop("cost_profile")))
    gate_bundle, sub, attest_path = plan_env(name="no-profile", src=src)
    plan = gateplan.GatePlan.from_bundle(gate_bundle)
    with pytest.raises(gateplan.FixtureInvalid, match="fixture-absent:cost_profile"):
        plan.run(gate_bundle, sub, attest_path)
    sub.close()


def test_a_corpus_fixture_field_of_the_wrong_type_is_refused_by_name(tmp_path, plan_env, db_snapshot):
    def break_field(obj):
        obj["fixtures"]["corpus_1"]["n"] = 7

    src = _source_copy(tmp_path, "bad-fixture", lambda d: _edit_plan(d, break_field))
    gate_bundle, sub, attest_path = plan_env(name="bad-fixture", src=src)
    with pytest.raises(gateplan.FixtureInvalid, match=r"fixture-field-wrong-type:corpus_1\.n"):
        gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    sub.close()


def test_a_cost_profile_fixture_that_is_not_a_decimal_string_is_refused_by_name(tmp_path, plan_env, db_snapshot):
    def break_profile(obj):
        obj["fixtures"]["cost_profile"]["per_try_s"] = "not-a-number"

    src = _source_copy(tmp_path, "bad-profile", lambda d: _edit_plan(d, break_profile))
    gate_bundle, sub, attest_path = plan_env(name="bad-profile", src=src)
    with pytest.raises(gateplan.FixtureInvalid, match=r"fixture-field-wrong-type:cost_profile\.per_try_s"):
        gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    sub.close()
