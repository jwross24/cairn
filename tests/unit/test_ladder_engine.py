import copy
import dataclasses
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from cairn import allowlist, bundle, claims, instances, keys, ladder, ladderplan, laddertable, runner
from cairn.skills import bsgs, rho_dp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

BACKEND = os.path.realpath(sys.executable)
ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
RUN_ID = "run-ladder-1"


def _hypothesis_object():
    return claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": [28, 30]},
        sampling_distribution=None,
    )


@pytest.fixture
def shipped(pinned_bundle):
    return bundle.GateBundle.open(*pinned_bundle())


@pytest.fixture
def writer(tmp_path):
    sub = helpers.open_writer(tmp_path)
    yield sub
    sub.close()


@pytest.fixture
def plan():
    obj = copy.deepcopy(COMMITTED)
    obj["baseline"]["implementation_revision"] = rho_dp.implementation_revision()
    return ladderplan.LadderPlan.load(obj)


def _certify(sub, module):
    identity = module.identity_bundle()
    digest = sub.put_identity_bundle(identity)
    sub.put_certificate(digest, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    return identity, digest


def _allow_list(shipped, tmp_path, hypothesis):
    scratch = tmp_path / "scratch"
    scratch.mkdir(exist_ok=True)
    return allowlist.instantiate(shipped, hypothesis=hypothesis, counted_object=BACKEND, scratch_dir=scratch)


@pytest.fixture
def seeded(writer, shipped, tmp_path, plan):
    obj = _hypothesis_object()
    claims.write_hypothesis_object(writer, obj)
    commitment, nonce = ladder.commit_entropy(writer, hypothesis_hash=obj.hash, run_id=RUN_ID)
    for module in (bsgs, rho_dp):
        _certify(writer, module)
    hypothesis = {
        "target_family": obj.target_family,
        "claimed": obj.claimed,
        "method_identity": obj.method_identity,
        "declared_parameter_ranges": obj.declared_parameter_ranges,
        "sampling_distribution": obj.sampling_distribution,
    }
    value = allow = _allow_list(shipped, tmp_path, hypothesis)
    return {
        "hypothesis": obj,
        "commitment": commitment,
        "nonce": nonce.nonce,
        "allow_list": allow,
        "plan": plan,
        "bundle": shipped,
        "value": value,
    }


def _dispatch(seeded, arm=ladder.CLAIMANT, module=bsgs, **overrides):
    identity = module.identity_bundle()
    fields = {
        "run_id": RUN_ID,
        "arm": arm,
        "nonce": seeded["nonce"],
        "hypothesis_hash": seeded["hypothesis"].hash,
        "method_identity": ladder.expected_identity(
            seeded["plan"], arm, {"method_identity": seeded["hypothesis"].method_identity}
        ),
        "skill": module.__name__,
        "implementation_revision": identity["implementation_revision"],
        "identity_bundle": identity,
        "identity_bundle_hash": keys.identity_bundle_hash(identity),
        "allow_list": seeded["allow_list"].as_dict(),
        "allow_list_hash": seeded["allow_list"].hash,
        "gate_bundle_hash": seeded["bundle"].hash,
        "plan_hash": "dd" * 32,
        "at": "2026-09-08T00:00:00Z",
    }
    fields.update(overrides)
    return ladder.Dispatch(**fields)


def _refuse_hypothesis_after_entropy(writer, seeded, shipped):
    later = dataclasses.replace(seeded["hypothesis"], claimed={"model": "c_sqrt_n_ops", "note": "late"})
    _, nonce = ladder.commit_entropy(writer, hypothesis_hash=later.hash, run_id="run-ladder-late")
    claims.write_hypothesis_object(writer, later)
    return _dispatch(seeded, hypothesis_hash=later.hash, nonce=nonce.nonce, method_identity=later.method_identity)


def _refuse_method_identity(writer, seeded, shipped):
    return _dispatch(seeded, method_identity={"interface_version": "other/1", "params": {}})


def _refuse_baseline_revision(writer, seeded, shipped):
    return _dispatch(seeded, arm=ladder.BASELINE, module=rho_dp, implementation_revision="ab" * 32)


def _refuse_uncertified(writer, seeded, shipped):
    identity = {**bsgs.identity_bundle(), "container_digest": "cd" * 32}
    return _dispatch(
        seeded,
        identity_bundle=identity,
        identity_bundle_hash=keys.identity_bundle_hash(identity),
    )


def _refuse_yanked(writer, seeded, shipped):
    value = _dispatch(seeded)
    writer.add_yank_record(
        "yank-1",
        value.identity_bundle_hash,
        "recipe",
        kind="human_path",
        ruling_ref="ruling-1",
        record_digest="ab" * 32,
        file_offset=0,
    )
    return value


def _refuse_commitment_absent(writer, seeded, shipped):
    other = instances.draw_nonce(writer, seeded["hypothesis"].hash, "run-ladder-2")
    return _dispatch(seeded, nonce=other.nonce)


def _refuse_nonce_published(writer, seeded, shipped):
    instances.publish_nonce(writer, seeded["nonce"])
    return _dispatch(seeded)


def _refuse_nonce_foreign(writer, seeded, shipped):
    other = dataclasses.replace(seeded["hypothesis"], target_family="other")
    claims.write_hypothesis_object(writer, other)
    ladder.commit_entropy(writer, hypothesis_hash=other.hash, run_id="run-ladder-3")
    foreign = instances.nonces_for(writer, other.hash)[0].nonce
    return _dispatch(seeded, nonce=foreign)


def _refuse_allow_list(writer, seeded, shipped):
    unbound = {**seeded["allow_list"].as_dict(), "bundle_hash": "ee" * 32}
    return _dispatch(seeded, allow_list=unbound)


REFUSALS = [
    ("hypothesis-after-entropy", _refuse_hypothesis_after_entropy, ladder.HYPOTHESIS_AFTER_ENTROPY),
    ("method-identity-mismatch", _refuse_method_identity, ladder.METHOD_IDENTITY_MISMATCH),
    ("baseline-revision-mismatch", _refuse_baseline_revision, ladder.BASELINE_REVISION_MISMATCH),
    ("uncertified-revision", _refuse_uncertified, ladder.UNCERTIFIED_REVISION),
    ("yanked-revision", _refuse_yanked, ladder.YANKED_REVISION),
    ("entropy-commitment-absent", _refuse_commitment_absent, ladder.COMMITMENT_ABSENT),
    ("nonce-published", _refuse_nonce_published, ladder.NONCE_PUBLISHED),
    ("nonce-foreign", _refuse_nonce_foreign, ladder.NONCE_FOREIGN),
    ("allow-list-unbound", _refuse_allow_list, ladder.ALLOW_LIST_UNBOUND),
]


@pytest.mark.parametrize(("label", "build", "expected"), REFUSALS, ids=[r[0] for r in REFUSALS])
def test_pre_spawn_refusal_table(writer, shipped, seeded, popen_spy, label, build, expected):
    value = build(writer, seeded, shipped)
    with pytest.raises(ladder.RunRefused) as raised:
        ladder.check_dispatch(writer, shipped, value, seeded["plan"])
    assert raised.value.reason == expected
    assert popen_spy == []
    assert writer.conn.execute(f"SELECT count(*) FROM {ladder.TABLE}").fetchone()[0] == 0


def test_every_refusal_reason_is_the_pre_spawn_vocabulary():
    assert {r[2] for r in REFUSALS} <= set(ladder.PRE_SPAWN_REASONS)


def test_an_unknown_arm_is_refused_before_the_plan_is_read(seeded):
    with pytest.raises(ladder.RunRefused) as raised:
        ladder.expected_identity(seeded["plan"], "control", {"method_identity": {}})
    assert raised.value.reason == ladder.ARM_UNKNOWN


def test_the_dispatch_record_carries_the_full_dispatched_identity(writer, shipped, seeded, popen_spy):
    value = ladder.dispatch(
        writer,
        shipped,
        plan=seeded["plan"],
        plan_hash="dd" * 32,
        hypothesis_hash=seeded["hypothesis"].hash,
        nonce=seeded["nonce"],
        run_id=RUN_ID,
        arm=ladder.CLAIMANT,
        skill=bsgs.__name__,
        allow_list=seeded["allow_list"],
    )
    identity = bsgs.identity_bundle()
    assert value.hypothesis_hash == seeded["hypothesis"].hash
    assert value.method_identity == seeded["hypothesis"].method_identity
    assert value.implementation_revision == identity["implementation_revision"]
    assert value.identity_bundle == identity
    assert value.allow_list_hash == seeded["allow_list"].hash
    assert value.gate_bundle_hash == shipped.hash
    row = writer.conn.execute(f"SELECT * FROM {ladder.TABLE}").fetchone()
    assert (row["run_id"], row["arm"], row["record_hash"]) == (RUN_ID, ladder.CLAIMANT, value.hash)
    assert ladder.dispatches_for(writer, RUN_ID)[ladder.CLAIMANT] == value
    assert popen_spy == []


def test_the_trial_recipe_key_is_built_from_the_dispatched_identity(seeded):
    value = _dispatch(seeded)
    recipe = ladder._recipe(value, 7, "ladder/x")
    assert recipe["skill_identity_hash"] == value.identity_bundle_hash
    assert recipe["container_digest"] == value.identity_bundle["container_digest"]
    assert recipe["tool_versions"] == value.identity_bundle["tool_digests"]
    changed = {**value.identity_bundle, "implementation_revision": "ff" * 32}
    other = dataclasses.replace(value, identity_bundle=changed, identity_bundle_hash=keys.identity_bundle_hash(changed))
    assert keys.recipe_key(recipe) != keys.recipe_key(ladder._recipe(other, 7, "ladder/x"))


def test_each_arm_draws_its_own_seed_from_the_run_nonce(seeded):
    seeds = {arm: ladder.method_seed(seeded["nonce"], seeded["hypothesis"].hash, arm, 28, 0) for arm in ladderplan.ARMS}
    assert len(set(seeds.values())) == len(ladderplan.ARMS)
    assert seeds[ladder.CLAIMANT] == ladder.method_seed(
        seeded["nonce"], seeded["hypothesis"].hash, ladder.CLAIMANT, 28, 0
    )
    assert seeds[ladder.CLAIMANT] != ladder.method_seed(
        seeded["nonce"], seeded["hypothesis"].hash, ladder.CLAIMANT, 28, 1
    )
    assert seeds[ladder.CLAIMANT] != instances.trial_seed(seeded["nonce"], seeded["hypothesis"].hash, 28, 0)


def test_the_hold_out_rung_runs_the_claimant_alone(plan):
    assert ladder.arms_for(plan.hold_out_rung) == (ladder.CLAIMANT,)
    assert ladder.arms_for(plan.fit_rungs[0]) == tuple(ladderplan.ARMS)


def _arm_trial(arm, bits, trial, ops, **overrides):
    fields = {
        "arm": arm,
        "bits": bits,
        "trial": trial,
        "seed": 1,
        "status": runner.STATUS_OK,
        "ops": ops,
        "recovered": True,
        "completed": True,
        "cpu_seconds": "0.010000",
        "wall_seconds": "0.010000",
        "peak_rss_bytes": 1000,
        "scratch_bytes": 0,
        "reported_memory_bytes": 1000,
        "replay_grade": "Replayable",
        "measurement_scope": runner.SCOPE_TREE,
        "attempt_id": "attempt-1",
        "instance_hash": "aa" * 32,
    }
    fields.update(overrides)
    return ladder.ArmTrial(**fields)


def _rung_of(plan, bits):
    return plan.rung(bits)


def test_a_trial_at_the_patience_ceiling_is_a_success_rate_failure_and_no_rung_keeps(plan):
    rung = _rung_of(plan, 30)
    mean = bsgs.COST_PROFILE.production.per_size[30].mean_tries
    ceiling = ladder._ceiling_ops(bsgs, 30, plan.patience_multiplier)
    claim = [
        _arm_trial(ladder.CLAIMANT, 30, 0, int(mean)),
        _arm_trial(
            ladder.CLAIMANT,
            30,
            1,
            ceiling,
            completed=False,
            recovered=False,
            status=runner.STATUS_BUDGET_EXCEEDED,
        ),
    ]
    base = [_arm_trial(ladder.BASELINE, 30, i, int(mean) * 4) for i in (0, 1)]
    row = ladder._rung_row(plan, rung, bsgs, claim, {ladder.BASELINE: base})
    assert Decimal(row.success_rate) == Decimal("0.5")
    assert Decimal(row.mean_ops) > Decimal(str(mean))
    assert ceiling > int(mean)
    table = laddertable.ResultTable(
        run_id=RUN_ID,
        nonce="n",
        hypothesis_hash="aa" * 32,
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        implementation_revision="bb" * 32,
        gate_bundle_hash="cc" * 32,
        plan_hash="dd" * 32,
        uncounted_backend=None,
        rungs=(row,),
        trials=tuple(ladder._trial_row(t) for t in claim),
    )
    with pytest.raises(laddertable.LadderTableError):
        laddertable.verdict(table, plan)
    single = dataclasses.replace(plan, rungs=(rung, plan.hold_out_rung), comparison=plan.comparison)
    found = laddertable.verdict(table, single)
    assert (found.kind, found.predicate) != (laddertable.KEEP, laddertable.ALL_RUNGS_PASS)


def test_an_uncounted_run_names_its_backend_and_cannot_keep(plan):
    rung = _rung_of(plan, 30)
    mean = int(bsgs.COST_PROFILE.production.per_size[30].mean_tries)
    claim = [_arm_trial(ladder.CLAIMANT, 30, i, mean) for i in (0, 1)]
    base = [_arm_trial(ladder.BASELINE, 30, i, mean * 4) for i in (0, 1)]
    row = ladder._rung_row(plan, rung, bsgs, claim, {ladder.BASELINE: base})
    table = laddertable.ResultTable(
        run_id=RUN_ID,
        nonce="n",
        hypothesis_hash="aa" * 32,
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        implementation_revision="bb" * 32,
        gate_bundle_hash="cc" * 32,
        plan_hash="dd" * 32,
        uncounted_backend=BACKEND,
        rungs=(row,),
        trials=tuple(ladder._trial_row(t) for t in claim),
    )
    single = dataclasses.replace(plan, rungs=(rung, plan.hold_out_rung))
    found = laddertable.verdict(table, single)
    assert (found.kind, found.predicate) == (laddertable.INCONCLUSIVE, laddertable.UNCOUNTED_BACKEND)
    assert Decimal(row.claim_ci_low) > 0
