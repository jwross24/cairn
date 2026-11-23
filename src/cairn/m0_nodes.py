from dataclasses import dataclass

import blake3

from cairn import canon, claims, cli, log, verifier
from cairn.canon import BOOL, INT, NON_EMPTY_STR, STR, Field, List, Optional, Struct
from cairn.skills import toy_curve

lg = log.get("m0")

BUDGET_CORE_S = 3600.0
DERIVE_LABEL = "derive"
TARGET_FAMILY = "toy_curve"
CLAIM_ID = "m0-slice"
KIND_GENERATOR = "m0_generator"
KIND_DERIVATION = "m0_derivation"
KIND_VERIFIER_RESULT = "verifier_result"
GRADE_REPLAYABLE = "Replayable"
GRADE_VERIFIABLE = "Verifiable"
REASON_UNCERTIFIED = "uncertified-revision"

GENERATOR_NODE = Struct(
    "m0_generator",
    [
        Field("skill_identity_hash", NON_EMPTY_STR),
        Field("output_manifest_hash", NON_EMPTY_STR),
        Field("certificate_hash", NON_EMPTY_STR),
        Field("cost_tag", NON_EMPTY_STR),
        Field("bits", INT),
        Field("seed", INT),
    ],
)

DERIVATION_NODE = Struct(
    "m0_derivation",
    [
        Field("instance_hash", NON_EMPTY_STR),
        Field("x_commit", NON_EMPTY_STR),
        Field("Q", List(STR)),
        Field("source_node", NON_EMPTY_STR),
    ],
)

VERIFIER_RESULT_NODE = Struct(
    "verifier_result",
    [
        Field("instance_hash", NON_EMPTY_STR),
        Field("accepted", BOOL),
        Field("reason", Optional(STR)),
        Field("reasons", List(STR)),
        Field("stdout_digest", Optional(STR)),
        Field("stderr_digest", Optional(STR)),
        Field("rc", Optional(INT)),
        Field("spawned", BOOL),
        Field("arm", NON_EMPTY_STR),
    ],
)


@dataclass(frozen=True)
class SliceNode:
    label: str
    kind: str
    hash: str
    replay_grade: str
    cost_tag: str
    selftest_ref: str | None = None


@dataclass(frozen=True)
class Arm:
    arm: str
    accepted: bool
    reason: str | None
    reasons: tuple
    gate_result: str
    node: str | None
    gate_run: str
    spawned: bool
    instance_hash: str | None
    stdout_digest: str | None
    stderr_digest: str | None
    rc: int | None


@dataclass(frozen=True)
class AdmissionSummary:
    gate_run_hash: str
    declared_tier: int
    cost_tier: int


@dataclass(frozen=True)
class SliceResult:
    nodes: tuple
    arms: tuple
    negatives: tuple
    refused_submission: str
    attempt_id: str
    served_from_cache: bool
    bundle_hash: str
    receipt_hash: str | None
    statement_hash: str
    instance_hash: str
    admission: AdmissionSummary


NEXT_CERTIFY = "certify"
NEXT_GATE_SELFTEST = "gate-selftest"
NEXT_DEBUG = "debug"


class SliceBackend(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class SliceRefused(Exception):
    def __init__(self, reason, next_step):
        super().__init__(reason)
        self.reason = reason
        self.next_step = next_step


def _draw(seed_bytes, bound, label):
    counter = 0
    while True:
        material = canon.length_prefix(seed_bytes) + canon.length_prefix(label.encode()) + counter.to_bytes(8, "little")
        value = int.from_bytes(blake3.blake3(material).digest(), "big") % bound
        if value:
            return value
        counter += 1


def _instance_fields(out, Q):
    return {
        "p": str(out["p"]),
        "a": str(out["a"]),
        "b": str(out["b"]),
        "n": str(out["n"]),
        "Px": str(out["P"][0]),
        "Py": str(out["P"][1]),
        "Qx": str(Q[0]),
        "Qy": str(Q[1]),
    }


def _instance(fields):
    return verifier.Instance(
        p=int(fields["p"]),
        a=int(fields["a"]),
        b=int(fields["b"]),
        n=int(fields["n"]),
        P=(int(fields["Px"]), int(fields["Py"])),
        Q=(int(fields["Qx"]), int(fields["Qy"])),
    )


def _point(raw):
    return tuple(int(coordinate.lift()) for coordinate in raw)


def _hypothesis(bits):
    return {
        "target_family": TARGET_FAMILY,
        "claimed": {"model": "c_ln_p_tries"},
        "method_identity": {"interface_version": toy_curve.INTERFACE_VERSION, "params": {}},
        "declared_parameter_ranges": {"bits": [bits, bits]},
        "sampling_distribution": None,
    }


def _record_verifier_run(sub, gate_bundle, result, *, arm):
    node_hash = sub.put_node(
        KIND_VERIFIER_RESULT,
        canon.encode(
            VERIFIER_RESULT_NODE,
            {
                "instance_hash": result.instance_hash,
                "accepted": result.accepted,
                "reason": result.reason,
                "reasons": list(result.reasons),
                "stdout_digest": result.stdout_digest,
                "stderr_digest": result.stderr_digest,
                "rc": result.rc,
                "spawned": result.spawned,
                "arm": arm,
            },
        ),
        replay_grade=GRADE_VERIFIABLE,
    )
    run = claims.GateRun(
        gate="verifier",
        bundle_hash=gate_bundle.hash,
        pin_hash=gate_bundle.pin_hash,
        plan_step=arm,
        instance_hash=result.instance_hash,
        result=result.gate_result,
        reasons=tuple(result.reasons),
        at=cli.now_iso(),
    )
    claims.write_gate_run(sub, run)
    lg.info(
        "verifier_arm",
        arm=arm,
        accepted=result.accepted,
        reason=result.reason,
        gate_result=result.gate_result,
        spawned=result.spawned,
        node=node_hash,
        gate_run=run.hash,
    )
    return node_hash, run.hash


def _refuse_verifier_run(sub, gate_bundle, result, *, arm):
    run = claims.GateRun(
        gate="verifier",
        bundle_hash=gate_bundle.hash,
        pin_hash=gate_bundle.pin_hash,
        plan_step=arm,
        instance_hash=result.instance_hash,
        result=result.gate_result,
        reasons=tuple(result.reasons),
        at=cli.now_iso(),
    )
    claims.write_gate_run(sub, run)
    lg.info("verifier_refused", arm=arm, reasons=list(result.reasons), gate_run=run.hash, spawned=result.spawned)
    return run.hash
