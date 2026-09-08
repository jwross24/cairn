from decimal import Decimal
from pathlib import Path

import pytest

from cairn import keys, runner, substrate
from cairn.profile import Evaluation
from cairn.skills import toy_curve

FIXTURES = str(Path(__file__).resolve().parent.parent / "fixtures")
BUNDLE_HASH = "ab" * 32
IDENTITY = toy_curve.identity_bundle()
TOOL_DIGESTS = IDENTITY["tool_digests"]
BURNER_BUDGET = Evaluation(expected_wall_s=30.0, expected_core_s=30.0, expected_verification_core_s=0.0)
TIGHT = Evaluation(expected_wall_s=0.75, expected_core_s=30.0, expected_verification_core_s=0.0)


def _recipe(seed):
    return {
        "skill_identity_hash": keys.identity_bundle_hash(IDENTITY),
        "inputs": {},
        "seed": seed,
        "tool_versions": {"cypari2": TOOL_DIGESTS["cypari2"]},
        "container_digest": IDENTITY["container_digest"],
        "salt": "",
    }


def _launch(sub, tmp_path, module, seed, evaluation, env_extra=None, **overrides):
    return runner.launch(
        sub,
        module,
        _recipe(seed),
        stdin_document={"n": 1},
        bundle_hash=BUNDLE_HASH,
        evaluation=evaluation,
        ceiling_multiplier=4,
        tool_digests=TOOL_DIGESTS,
        scratch_root=tmp_path / "runs",
        env_extra={"PYTHONPATH": FIXTURES, **(env_extra or {})},
        **overrides,
    )


@pytest.fixture(scope="module")
def arms(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("arms")
    with substrate.Substrate.open(tmp_path / "substrate.sqlite") as sub:
        reaping = _launch(sub, tmp_path, "skills.cpu_burner", 21, BURNER_BUDGET, env_extra={"FIXTURE_GRANDCHILD": "1"})
        orphaning = _launch(sub, tmp_path, "skills.orphans_a_burner", 22, BURNER_BUDGET)
        killed = _launch(
            sub,
            tmp_path,
            "skills.orphans_a_burner",
            23,
            TIGHT,
            env_extra={"FIXTURE_OUTLIVE": "1"},
            wall_cap_multiplier=1.0,
            wall_cap_floor_s=0.0,
        )
        alone = runner.launch(
            sub,
            "cairn.skills.toy_curve",
            _recipe(41),
            stdin_document={"bits": 40, "seed": 1},
            bundle_hash=BUNDLE_HASH,
            evaluation=toy_curve.COST_PROFILE.evaluate(40),
            ceiling_multiplier=4,
            tool_digests=TOOL_DIGESTS,
            scratch_root=tmp_path / "runs",
        )
        yield {
            "reaping": (reaping, sub.get_receipt(reaping.receipt_hash)),
            "orphaning": (orphaning, sub.get_receipt(orphaning.receipt_hash)),
            "killed": (killed, sub.get_receipt(killed.receipt_hash)),
            "alone": (alone, sub.get_receipt(alone.receipt_hash)),
        }


def test_a_child_that_reaps_its_grandchild_records_the_reaped_scope(arms):
    attempt, receipt = arms["reaping"]
    assert attempt.status == "OK"
    assert receipt["measurement_scope"] == runner.SCOPE_REAPED_DESCENDANTS


def test_a_child_that_orphans_its_grandchild_records_a_truncated_scope(arms):
    attempt, receipt = arms["orphaning"]
    assert attempt.status == "OK"
    assert receipt["measurement_scope"] == runner.SCOPE_TRUNCATED


def test_a_child_killed_at_its_wall_cap_records_a_truncated_scope(arms):
    _, receipt = arms["killed"]
    assert receipt["measurement_scope"] == runner.SCOPE_TRUNCATED


def test_no_arm_that_leaves_a_descendant_claims_a_verified_complete_figure(arms):
    for name in ("reaping", "orphaning", "killed"):
        _, receipt = arms[name]
        assert not runner.scope_is_verified_complete(receipt["measurement_scope"]), name


def test_a_reader_keyed_on_cpu_alone_cannot_separate_the_orphan_from_the_reaper(arms):
    reaped = Decimal(str(arms["reaping"][1]["cpu_user_s"]))
    orphaned = Decimal(str(arms["orphaning"][1]["cpu_user_s"]))
    assert orphaned * 2 < reaped, (orphaned, reaped)
    assert arms["reaping"][1]["measurement_scope"] != arms["orphaning"][1]["measurement_scope"]


def test_a_launch_with_no_descendant_at_all_records_a_tree_figure(arms):
    attempt, receipt = arms["alone"]
    assert attempt.status == "OK"
    assert receipt["measurement_scope"] == runner.SCOPE_TREE
    assert runner.scope_is_verified_complete(receipt["measurement_scope"])
