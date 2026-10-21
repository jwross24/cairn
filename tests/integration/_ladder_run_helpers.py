import copy
import dataclasses
import json
import os
import sys
from pathlib import Path

import pytest

from cairn import allowlist, bundle, claims, ladder, ladderplan
from cairn.skills import bsgs, instance_maker, rho_dp

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _substrate_helpers as helpers

ROOT = Path(__file__).resolve().parents[2]
COMMITTED = json.loads((ROOT / "bundle" / "ladder_plan.json").read_text())
BACKEND = os.path.realpath(sys.executable)
RUN_ID = "run-ladder-e2e"
PATIENCE = 60
MAKER_CEILING = 60
FIT_BITS = 28
HOLD_OUT_BITS = 30


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
    full = ladderplan.LadderPlan.load(obj)
    fit = dataclasses.replace(full.rung(30), bits=FIT_BITS, trials=2)
    hold_out = dataclasses.replace(full.rung(40), bits=HOLD_OUT_BITS, role=ladderplan.ROLE_HOLD_OUT, trials=2)
    return dataclasses.replace(full, rungs=(fit, hold_out), hold_out_m=2, patience_multiplier=PATIENCE)


@pytest.fixture
def hypothesis_object():
    return claims.HypothesisObject(
        target_family="dlp",
        claimed={"model": "c_sqrt_n_ops"},
        method_identity={"interface_version": bsgs.INTERFACE_VERSION, "params": {}},
        declared_parameter_ranges={"bits": [FIT_BITS, HOLD_OUT_BITS]},
        sampling_distribution=None,
    )


def _dispatch_run(
    writer,
    shipped,
    tmp_path,
    plan,
    hypothesis_object,
    run_id,
    *,
    claimant=bsgs,
    backend_paths=None,
    withheld_roots=None,
):
    if withheld_roots is None:
        withheld_roots = allowlist.store_roots(writer.path)
    if claims.get_hypothesis_object(writer, hypothesis_object.hash) is None:
        claims.write_hypothesis_object(writer, hypothesis_object)
    _, nonce = ladder.commit_entropy(writer, hypothesis_hash=hypothesis_object.hash, run_id=run_id)
    for module in (claimant, rho_dp, instance_maker):
        identity = module.identity_bundle()
        digest = writer.put_identity_bundle(identity)
        if not writer.certified(digest):
            writer.put_certificate(digest, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, helpers.SELFTEST_SUMMARY)
    scratch = tmp_path / f"allow-{run_id}"
    scratch.mkdir()
    hypothesis = {
        "target_family": hypothesis_object.target_family,
        "claimed": hypothesis_object.claimed,
        "method_identity": hypothesis_object.method_identity,
        "declared_parameter_ranges": hypothesis_object.declared_parameter_ranges,
        "sampling_distribution": hypothesis_object.sampling_distribution,
    }
    allow = allowlist.instantiate(
        shipped,
        hypothesis=hypothesis,
        counted_object=BACKEND,
        scratch_dir=scratch,
        backend_paths=backend_paths,
        withheld_roots=withheld_roots,
    )
    for arm, module in (
        (ladder.CLAIMANT, claimant),
        (ladder.BASELINE, rho_dp),
        (ladder.BASELINE_AA, rho_dp),
    ):
        ladder.dispatch(
            writer,
            shipped,
            plan=plan,
            plan_hash=ladderplan.plan_digest(shipped) or "dd" * 32,
            hypothesis_hash=hypothesis_object.hash,
            nonce=nonce.nonce,
            run_id=run_id,
            arm=arm,
            skill=module.__name__,
            allow_list=allow,
        )
    return nonce.nonce


@pytest.fixture
def dispatched(writer, shipped, tmp_path, plan, hypothesis_object):
    return _dispatch_run(writer, shipped, tmp_path, plan, hypothesis_object, RUN_ID)


@pytest.fixture
def attest_path(tmp_path):
    path = tmp_path / "attestations.log"
    path.touch()
    return path
