import copy
import dataclasses
import shutil
import sys
from pathlib import Path

import pytest

from cairn import ladder, ladderplan, laddertable

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import _substrate_helpers as helpers
from test_ladder_run import (
    MAKER_CEILING,
    RUN_ID,
    _dispatch_run,
)

from tests.fixtures.skills import ladder_model_miss, ladder_wrong_answer


def run_wrong_answer(writer, shipped, tmp_path, plan, hypothesis_object, attest_path):
    nonce = _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, RUN_ID, claimant=ladder_wrong_answer)
    scratch = tmp_path / "runs"
    scratch.mkdir()
    return ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped),
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        attest_path=attest_path,
    )


def run_measured_floor(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, ops_kind):
    measured_plan = _measured_floor_plan(plan)
    nonce = _dispatch_run(writer, shipped, tmp_path, measured_plan, hypothesis_object, RUN_ID)
    scratch = tmp_path / "measured-runs"
    scratch.mkdir()

    def observe(trial):
        assert trial.reported_ops is not None
        return laddertable.OpsObservation(ops_kind, trial.reported_ops)

    return ladder.run(
        writer,
        shipped,
        plan=measured_plan,
        plan_hash=ladderplan.plan_digest(shipped),
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        ops_counter=observe,
        attest_path=attest_path,
    )


def run_model_miss(writer, shipped, tmp_path, plan, hypothesis_object, attest_path, bits):
    nonce = _dispatch_run(
        writer,
        shipped,
        tmp_path,
        plan,
        hypothesis_object,
        RUN_ID,
        claimant=ladder_model_miss,
    )
    scratch = tmp_path / f"model-miss-{bits}"
    scratch.mkdir()

    def observe(trial):
        if trial.arm == ladder.CLAIMANT and trial.bits == bits:
            assert trial.reported_ops is not None
            return laddertable.OpsObservation(laddertable.OPS_EXACT, trial.reported_ops)
        return laddertable.OpsObservation(laddertable.OPS_UNKNOWN, None)

    return ladder.run(
        writer,
        shipped,
        plan=plan,
        plan_hash=ladderplan.plan_digest(shipped),
        run_id=RUN_ID,
        hypothesis_hash=hypothesis_object.hash,
        nonce=nonce,
        scratch_root=scratch,
        budget_remaining=10_000.0,
        ceiling_multiplier=MAKER_CEILING,
        ops_counter=observe,
        attest_path=attest_path,
    )


_RAN = {}


@pytest.fixture
def replayed_run(tmp_path, tmp_path_factory, shipped, plan, hypothesis_object):
    opened = []

    def replay(key, run):
        if key not in _RAN:
            home = tmp_path_factory.mktemp("ladder-run")
            built = helpers.open_writer(home)
            try:
                log = home / "attestations.log"
                log.touch()
                result = run(built, home, log)
            finally:
                built.close()
            _RAN[key] = (home, result)
        home, result = _RAN[key]
        shutil.copy2(home / "substrate.sqlite", tmp_path / "substrate.sqlite")
        shutil.copy2(home / "attestations.log", tmp_path / "attestations.log")
        sub = helpers.open_writer(tmp_path)
        opened.append(sub)
        return sub, tmp_path / "attestations.log", copy.deepcopy(result)

    yield replay
    for sub in opened:
        sub.close()


def _measured_floor_plan(plan):
    floor = dataclasses.replace(plan.rungs[0].refutation_floor, group_ops=1)
    floor_rung = dataclasses.replace(
        plan.rungs[0], floor_binds=True, memory_cap_bytes=floor.memory_bytes, refutation_floor=floor
    )
    return dataclasses.replace(plan, rungs=(floor_rung, *plan.rungs[1:]))
