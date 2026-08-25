import json
import os
from dataclasses import dataclass

import blake3

from cairn import bundle, canon, claims, cli, exits, gateplan, keys, log, pari, runner, substrate, tiergate, verifier
from cairn.canon import BOOL, INT, NON_EMPTY_STR, Field, List, Map, Optional, STR, Struct
from cairn.errors import CliError
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
        "method_identity": {"interface_version": "toy_curve/1", "params": {}},
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
    lg.info("verifier_arm", arm=arm, accepted=result.accepted, reason=result.reason, gate_result=result.gate_result, node=node_hash, gate_run=run.hash)
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
    lg.info("verifier_refused", arm=arm, reasons=list(result.reasons), gate_run=run.hash, spawned=result.rc is not None)
    return run.hash


def run_slice(sub, gate_bundle, attest_path, *, bits, seed, scratch_root, skip_cache_lookup=False):
    lg.info("step", step=1, name="gate_plan", bundle_hash=gate_bundle.hash, pin_hash=gate_bundle.pin_hash)
    plan_result = gateplan.GatePlan.from_bundle(gate_bundle).run(gate_bundle, sub, attest_path)
    if not plan_result.ok:
        failed = plan_result.first_failure
        raise SliceRefused(f"gate-plan-failed:{failed.step}", NEXT_GATE_SELFTEST)

    identity = toy_curve.skill_identity_hash()
    certificate = sub.get_certificate(identity)
    lg.info("step", step=2, name="certified", skill_identity_hash=identity, certified=sub.certified(identity))
    if not sub.certified(identity):
        raise SliceRefused(REASON_UNCERTIFIED, NEXT_CERTIFY)

    hypothesis = _hypothesis(bits)
    hypothesis_key = keys.hypothesis_key(hypothesis)
    if claims.get_hypothesis_object(sub, hypothesis_key) is None:
        claims.write_hypothesis_object(sub, claims.HypothesisObject(**hypothesis))
    evaluation = toy_curve.COST_PROFILE.evaluate(bits)
    launch = tiergate.Launch(
        cost_profile=toy_curve.COST_PROFILE,
        inputs=bits,
        budget_remaining=BUDGET_CORE_S,
        hypothesis_key=hypothesis_key,
        method_identity=hypothesis["method_identity"],
        skill_identity_hash=identity,
        declared_tier=0,
    )
    decision = tiergate.TierGate(sub, gate_bundle).admit(launch)
    lg.info("step", step=3, name="tier_gate", result=type(decision).__name__, reasons=list(decision.reasons), gate_run=decision.gate_run_hash)
    if isinstance(decision, tiergate.TierRefused):
        raise SliceRefused(f"tier-refused:{','.join(decision.reasons)}", NEXT_CERTIFY)

    bundle_identity = toy_curve.identity_bundle()
    stdin_document = {"bits": bits, "seed": seed}
    payload = json.dumps(stdin_document, sort_keys=True, separators=(",", ":")).encode()
    recipe = {
        "skill_identity_hash": identity,
        "inputs": {"input.json": (sub.put_blob(payload), len(payload))},
        "seed": seed,
        "tool_versions": {"cypari2": bundle_identity["tool_digests"]["cypari2"]},
        "container_digest": bundle_identity["container_digest"],
        "salt": "",
    }
    attempt = runner.launch(
        sub,
        "cairn.skills.toy_curve",
        recipe,
        stdin_document=stdin_document,
        bundle_hash=gate_bundle.hash,
        evaluation=evaluation,
        ceiling_multiplier=gate_bundle.tiers["ceiling_multiplier"],
        tool_digests=bundle_identity["tool_digests"],
        scratch_root=scratch_root,
        budget_remaining=BUDGET_CORE_S,
        skip_cache_lookup=skip_cache_lookup,
    )
    lg.info("step", step=4, name="generator", attempt=attempt.attempt_id, status=attempt.status, cached=attempt.served_from_cache, manifest=attempt.output_manifest_hash)
    if attempt.status == "FAIL":
        raise SliceBackend(f"attempt-{attempt.status}")
    if attempt.status != "OK":
        raise SliceRefused(f"attempt-{attempt.status}", NEXT_DEBUG)

    document = attempt.parsed.document if attempt.parsed is not None else _served_document(sub, attempt)
    node_a = sub.put_node(
        KIND_GENERATOR,
        canon.encode(
            GENERATOR_NODE,
            {
                "skill_identity_hash": identity,
                "output_manifest_hash": attempt.output_manifest_hash,
                "certificate_hash": certificate["cert_hash"],
                "cost_tag": "tier0",
                "bits": bits,
                "seed": seed,
            },
        ),
    )

    n = int(document["n"])
    x = _draw(bytes.fromhex(node_a), n - 1, DERIVE_LABEL)
    curve = pari.pari.ellinit([int(document["a"]), int(document["b"])], int(document["p"]))
    Q = _point(pari.pari.ellmul(curve, [int(document["P"][0]), int(document["P"][1])], x))
    fields = _instance_fields(document, Q)
    instance = _instance(fields)
    statement = claims.ClaimStatement(
        claim_id=CLAIM_ID,
        version=1,
        informal=f"the {bits}-bit toy-curve slice instance and its derived Q = xP",
        scope={
            "target_family": TARGET_FAMILY,
            "size_interval": [bits, bits],
            "param_ranges": {"bits": [bits, bits]},
            "assumption_set": set(),
        },
        quantities={"units": fields, "cost_model": None},
    )
    claims.write_claim_statement(sub, statement)
    node_b = sub.put_node(
        KIND_DERIVATION,
        canon.encode(
            DERIVATION_NODE,
            {
                "instance_hash": instance.instance_hash,
                "x_commit": blake3.blake3(str(x).encode()).hexdigest(),
                "Q": [str(Q[0]), str(Q[1])],
                "source_node": node_a,
            },
        ),
        replay_grade=GRADE_VERIFIABLE,
    )
    sub.add_lineage(node_b, node_a, "derives")
    lg.info("step", step=5, name="derivation", instance_hash=instance.instance_hash, statement=statement.hash, node=node_b)

    engine = verifier.Verifier(gate_bundle.verifier_config())
    gate_read = _instance(_statement_units(sub, statement.hash))
    positive = engine.run(gate_read, x)
    lg.info("step", step=6, name="verify", accepted=positive.accepted, reason=positive.reason, instance_hash=positive.instance_hash)
    if not positive.accepted:
        raise SliceRefused(f"verifier-{positive.reason}", NEXT_DEBUG)
    node_c, node_d = _record_verifier_run(sub, gate_bundle, positive, arm="slice_positive")
    arms = [_arm("slice_positive", positive, node_c, node_d)]
    lg.info("step", step=7, name="gate_run", gate_run=node_d)

    negatives = []
    wrong_coordinate = _instance({**fields, "Qy": str((int(fields["Qy"]) + 1) % int(fields["p"]))})
    negatives.append(("negative_coordinate", engine.run(wrong_coordinate, x)))
    negatives.append(("negative_scalar", engine.run(gate_read, x % (n - 1) + 1 if x != 1 else 2)))
    negative_nodes = []
    for arm, result in negatives:
        if result.accepted:
            raise SliceRefused(f"negative-accepted:{arm}", NEXT_DEBUG)
        node, run_hash = _record_verifier_run(sub, gate_bundle, result, arm=arm)
        negative_nodes.append(node)
        arms.append(_arm(arm, result, node, run_hash))

    named = engine.run(gate_read, verifier.Submission(x, P=gate_read.P, Q=gate_read.Q))
    if named.reason != "submitter-named-instance" or named.rc is not None:
        raise SliceRefused("submitter-named-not-refused", NEXT_DEBUG)
    refused_run = _refuse_verifier_run(sub, gate_bundle, named, arm="submitter_named")
    arms.append(_arm("submitter_named", named, None, refused_run))
    lg.info("step", step=8, name="negatives", negatives=negative_nodes, refused=refused_run)

    certificate_ref = certificate["cert_hash"]
    nodes = (
        SliceNode("A", KIND_GENERATOR, node_a, _grade_of(sub, node_a), "tier0", certificate_ref),
        SliceNode("B", KIND_DERIVATION, node_b, _grade_of(sub, node_b), "tier0", certificate_ref),
        SliceNode("C", KIND_VERIFIER_RESULT, node_c, _grade_of(sub, node_c), "tier0", certificate_ref),
        SliceNode("D", "gate_run", node_d, GRADE_REPLAYABLE, "tier0", certificate_ref),
    )
    lg.info("step", step=9, name="summary", nodes=[n.hash for n in nodes], attempt=attempt.attempt_id)
    return SliceResult(nodes, tuple(arms), tuple(negative_nodes), refused_run, attempt.attempt_id, attempt.served_from_cache, gate_bundle.hash, attempt.receipt_hash, statement.hash, instance.instance_hash)


def _arm(name, result, node, gate_run):
    return Arm(name, result.accepted, result.reason, tuple(result.reasons), result.gate_result, node, gate_run, result.rc is not None, result.instance_hash, result.stdout_digest, result.stderr_digest, result.rc)


def _grade_of(sub, node_hash):
    row = sub.get_node(node_hash)
    if row is None:
        raise SliceRefused(f"node-absent:{node_hash}", NEXT_DEBUG)
    return row["replay_grade"]


def _served_document(sub, attempt):
    blobs = [
        row["child_hash"]
        for row in sub.conn.execute(
            "SELECT child_hash FROM lineage WHERE parent_hash = ? AND edge_kind = ? ORDER BY child_hash",
            (attempt.output_manifest_hash, substrate.EDGE_MEMBER),
        ).fetchall()
    ]
    if len(blobs) != 1:
        raise SliceRefused(f"cached-manifest-carries-{len(blobs)}-artifacts", NEXT_DEBUG)
    payload = sub.get_blob(blobs[0])
    if payload is None:
        raise SliceRefused("cached-artifact-blob-absent", NEXT_DEBUG)
    return json.loads(payload)


def _statement_units(sub, statement_hash):
    row = claims.get_claim_statement(sub, statement_hash)
    if row is None:
        raise SliceRefused("statement-absent", NEXT_DEBUG)
    return json.loads(row["quantities"])["units"]


def _next_command(ns, step):
    paths = f"--db {ns.db} --bundle {ns.bundle} --pin {ns.pin}"
    if step == NEXT_CERTIFY:
        return f"cairn selftest toy-curve {paths}"
    if step == NEXT_GATE_SELFTEST:
        return f"cairn gate selftest --json {paths} --attest {ns.attest}"
    return f"cairn m0-run --bits {ns.bits} --seed {ns.seed} --json --log DEBUG {paths} --attest {ns.attest}"


def _configure(parser):
    sizes = toy_curve.COST_PROFILE.declared_sizes()
    parser.add_argument("--bits", type=int, default=40, choices=sizes, help=f"curve size the slice generates and verifies; the cost profile declares {', '.join(str(b) for b in sizes)}")
    parser.add_argument("--seed", type=int, default=1, help="generator seed; the same seed replays to the same node A")
    parser.add_argument("--skip-cache-lookup", action="store_true", help="record a fresh attempt even when the recipe is already cached")


def _run(ns):
    if not os.path.exists(ns.attest):
        raise CliError(
            exits.ENVIRONMENT,
            f"the attestation file {ns.attest} does not exist; the gate plan's waiver step reads its record 0",
            where=str(ns.attest),
            next_command=f"cairn attest init --attest {ns.attest} --bundle {ns.bundle} --pin {ns.pin}",
        )
    gate_bundle = bundle.open_or_refuse(ns, command="cairn m0-run")
    scratch_root = os.path.join(os.path.dirname(os.path.abspath(ns.db)) or ".", "m0-runs")
    try:
        with substrate.Substrate.open(ns.db) as sub:
            result = run_slice(
                sub,
                gate_bundle,
                ns.attest,
                bits=ns.bits,
                seed=ns.seed,
                scratch_root=scratch_root,
                skip_cache_lookup=getattr(ns, "skip_cache_lookup", False),
            )
    except substrate.WriterAlreadyOpen as exc:
        raise CliError(exits.CONFLICT, f"another writer already holds {ns.db}: {exc}", where=str(ns.db), next_command=f"cairn m0-run --db {ns.db}") from None
    except gateplan.PlanInvalid as invalid:
        raise CliError(exits.GATE_REFUSED, f"the gate plan in bundle {gate_bundle.hash} is invalid ({invalid.reason}); no step ran", where=str(ns.bundle), next_command=bundle.repin_sequence(ns.bundle, ns.pin)) from None
    except SliceBackend as backend:
        raise CliError(exits.BACKEND, f"the M0 slice could not complete: {backend.reason}", where=str(ns.db), next_command=_next_command(ns, NEXT_DEBUG)) from None
    except SliceRefused as refused:
        raise CliError(exits.GATE_REFUSED, f"the M0 slice refused: {refused.reason}", where=str(ns.db), next_command=_next_command(ns, refused.next_step)) from None
    payload = {
        "arms": [
            {"arm": a.arm, "accepted": a.accepted, "reason": a.reason, "reasons": list(a.reasons), "gate_result": a.gate_result, "node": a.node, "gate_run": a.gate_run, "spawned": a.spawned, "instance_hash": a.instance_hash, "stdout_digest": a.stdout_digest, "stderr_digest": a.stderr_digest, "rc": a.rc}
            for a in result.arms
        ],
        "statement_hash": result.statement_hash,
        "instance_hash": result.instance_hash,
        "nodes": [
            {"label": node.label, "kind": node.kind, "hash": node.hash, "replay_grade": node.replay_grade, "cost_tag": node.cost_tag, "selftest_ref": node.selftest_ref}
            for node in result.nodes
        ],
        "negatives": list(result.negatives),
        "refused_submission": result.refused_submission,
        "attempt_id": result.attempt_id,
        "served_from_cache": result.served_from_cache,
        "receipt_hash": result.receipt_hash,
        "bundle_hash": result.bundle_hash,
        "exit_code": exits.OK,
    }
    if getattr(ns, "json", False):
        cli.emit_json("m0-run", payload)
    else:
        for node in result.nodes:
            print(f"{node.label} {node.kind} {node.hash} {node.replay_grade} {node.cost_tag}")
        for arm in result.arms:
            if arm.arm == "slice_positive":
                continue
            verdict = "refused" if arm.node is None else f"FAIL {arm.reason}"
            print(f"- {verdict} {arm.arm} {arm.node or arm.gate_run}")
    return exits.OK


cli.register(
    "m0-run",
    _configure,
    _run,
    summary="run the M0 slice end to end: gate self-tests, a certified 40-bit generator, a derived instance, and a gate-read verification with its negatives",
    read_only=False,
    json=True,
    aliases=("run",),
)
