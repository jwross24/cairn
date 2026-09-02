"""The harness's own family: three entries that exercise the rollup and count toward nothing.

The must-FAIL entry produces a curve with a cold toy_curve launch, plants Q = P and submits x = 2,
which the real verifier rejects. The control plants a ladder_table evidence node whose verdict is
INCONCLUSIVE on the cold attempt and reads it back through the substrate; control (k)'s own entry,
the one a real null arm lands, is bead C2's. The third entry is the must-FAIL artifact registered
as a control, and EXPECTED_ESCAPES names it so the rollup's catch is what the family asserts.
"""

import functools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import factories
from _corpus import INCONCLUSIVE, MUST_FAIL, MUST_PASS, SELF_CHECK, Entry

from cairn import claims, keys, verifier
from cairn.skills import toy_curve

OWNER = "cairn-m1-cqt.3.1"
BITS = 30
SEED = 1
WRONG_X = 2
VERIFIER_FAIL = "fail"
VERIFIER_PASS = "pass"
KEEP = "KEEP"
WRONG_X_ID = "self_check/wrong_x_fails_the_verifier"
NULL_ARM_ID = "self_check/planted_ladder_verdict_reads_back"
MIS_REGISTERED_ID = "self_check/wrong_x_registered_as_a_control"


def _recipe(sub, document):
    identity = toy_curve.identity_bundle()
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode()
    return {
        "skill_identity_hash": keys.identity_bundle_hash(identity),
        "inputs": {"input.json": (sub.put_blob(payload), len(payload))},
        "seed": document["seed"],
        "tool_versions": {"cypari2": identity["tool_digests"]["cypari2"]},
        "container_digest": identity["container_digest"],
        "salt": "",
    }


def produce_curve(cold, seed=SEED):
    document = {"bits": BITS, "seed": seed}
    attempt = cold.launch(
        "cairn.skills.toy_curve",
        _recipe(cold.sub, document),
        stdin_document=document,
        evaluation=toy_curve.COST_PROFILE.evaluate(BITS),
        ceiling_multiplier=4,
        tool_digests=toy_curve.identity_bundle()["tool_digests"],
    )
    if attempt.status != "OK":
        raise RuntimeError(f"toy_curve landed {attempt.status}")
    out = attempt.parsed.document
    point = tuple(int(coordinate) for coordinate in out["P"])
    return attempt, verifier.Instance(
        p=int(out["p"]), a=int(out["a"]), b=int(out["b"]), n=int(out["n"]), P=point, Q=point
    )


def wrong_x_run(cold):
    _, instance = produce_curve(cold)
    return verifier.Verifier().run(instance, WRONG_X).gate_result


def null_arm_run(cold, verdict=INCONCLUSIVE):
    attempt, _ = produce_curve(cold)
    statement = factories.claim_statement(seed=SEED)
    claims.write_claim_statement(cold.sub, statement)
    node = factories.evidence_node(
        "ladder_table",
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        verdict=verdict,
        attempt_id=attempt.attempt_id,
        in_sample_sizes=(BITS,),
    )
    claims.write_evidence_node(cold.sub, node)
    rows = claims.evidence_for(cold.sub, statement.hash)
    return rows[-1]["verdict"]


ENTRIES = (
    Entry(WRONG_X_ID, SELF_CHECK, MUST_FAIL, VERIFIER_FAIL, OWNER, wrong_x_run),
    Entry(NULL_ARM_ID, SELF_CHECK, MUST_PASS, INCONCLUSIVE, OWNER, null_arm_run),
    Entry(MIS_REGISTERED_ID, SELF_CHECK, MUST_PASS, VERIFIER_PASS, OWNER, wrong_x_run),
)
EXPECTED_ESCAPES = (MIS_REGISTERED_ID,)
null_arm_driven_to_keep = functools.partial(null_arm_run, verdict=KEEP)
