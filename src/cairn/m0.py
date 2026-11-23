import json
import os
from pathlib import Path

import blake3

from cairn import bundle, canon, claims, cli, exits, gateplan, keys, log, pari, runner, substrate, tiergate, verifier
from cairn.errors import CliError
from cairn.m0_nodes import BUDGET_CORE_S as BUDGET_CORE_S
from cairn.m0_nodes import CLAIM_ID as CLAIM_ID
from cairn.m0_nodes import DERIVATION_NODE as DERIVATION_NODE
from cairn.m0_nodes import DERIVE_LABEL as DERIVE_LABEL
from cairn.m0_nodes import GENERATOR_NODE as GENERATOR_NODE
from cairn.m0_nodes import GRADE_REPLAYABLE as GRADE_REPLAYABLE
from cairn.m0_nodes import GRADE_VERIFIABLE as GRADE_VERIFIABLE
from cairn.m0_nodes import KIND_DERIVATION as KIND_DERIVATION
from cairn.m0_nodes import KIND_GENERATOR as KIND_GENERATOR
from cairn.m0_nodes import KIND_VERIFIER_RESULT as KIND_VERIFIER_RESULT
from cairn.m0_nodes import NEXT_CERTIFY as NEXT_CERTIFY
from cairn.m0_nodes import NEXT_DEBUG as NEXT_DEBUG
from cairn.m0_nodes import NEXT_GATE_SELFTEST as NEXT_GATE_SELFTEST
from cairn.m0_nodes import REASON_UNCERTIFIED as REASON_UNCERTIFIED
from cairn.m0_nodes import TARGET_FAMILY as TARGET_FAMILY
from cairn.m0_nodes import VERIFIER_RESULT_NODE as VERIFIER_RESULT_NODE
from cairn.m0_nodes import AdmissionSummary as AdmissionSummary
from cairn.m0_nodes import Arm as Arm
from cairn.m0_nodes import SliceBackend as SliceBackend
from cairn.m0_nodes import SliceNode as SliceNode
from cairn.m0_nodes import SliceRefused as SliceRefused
from cairn.m0_nodes import SliceResult as SliceResult
from cairn.m0_nodes import _draw as _draw
from cairn.m0_nodes import _hypothesis as _hypothesis
from cairn.m0_nodes import _instance as _instance
from cairn.m0_nodes import _instance_fields as _instance_fields
from cairn.m0_nodes import _point as _point
from cairn.m0_nodes import _record_verifier_run as _record_verifier_run
from cairn.m0_nodes import _refuse_verifier_run as _refuse_verifier_run
from cairn.skills import toy_curve

lg = log.get("m0")


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
    decision = tiergate.TierGate(sub, gate_bundle, attest_path=attest_path).admit(launch)
    lg.info(
        "step",
        step=3,
        name="tier_gate",
        result=type(decision).__name__,
        reasons=list(decision.reasons),
        gate_run=decision.gate_run_hash,
    )
    if isinstance(decision, tiergate.TierRefused):
        raise SliceRefused(f"tier-refused:{','.join(decision.reasons)}", NEXT_CERTIFY)
    admission = AdmissionSummary(decision.gate_run_hash, launch.declared_tier, decision.cost_tier)
    cost_tag = f"tier{admission.cost_tier}"

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
        wall_cap_multiplier=gate_bundle.tiers["wall_cap_multiplier"],
        wall_cap_floor_s=gate_bundle.tiers["wall_cap_floor_s"],
        subprocess_startup_ms=gate_bundle.tiers["subprocess_startup_ms"],
        tool_digests=bundle_identity["tool_digests"],
        scratch_root=scratch_root,
        budget_remaining=BUDGET_CORE_S,
        skip_cache_lookup=skip_cache_lookup,
        attest_path=attest_path,
    )
    lg.info(
        "step",
        step=4,
        name="generator",
        attempt=attempt.attempt_id,
        status=attempt.status,
        cached=attempt.served_from_cache,
        manifest=attempt.output_manifest_hash,
    )
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
                "cost_tag": cost_tag,
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
    lg.info(
        "step", step=5, name="derivation", instance_hash=instance.instance_hash, statement=statement.hash, node=node_b
    )

    engine = verifier.Verifier(gate_bundle.verifier_config())
    gate_read = _instance(_statement_units(sub, statement.hash))
    positive = engine.run(gate_read, x)
    lg.info(
        "step",
        step=6,
        name="verify",
        accepted=positive.accepted,
        reason=positive.reason,
        instance_hash=positive.instance_hash,
    )
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
    if named.reason != "submitter-named-instance" or named.spawned:
        raise SliceRefused("submitter-named-not-refused", NEXT_DEBUG)
    refused_run = _refuse_verifier_run(sub, gate_bundle, named, arm="submitter_named")
    arms.append(_arm("submitter_named", named, None, refused_run))
    lg.info("step", step=8, name="negatives", negatives=negative_nodes, refused=refused_run)

    certificate_ref = certificate["cert_hash"]
    nodes = (
        SliceNode("A", KIND_GENERATOR, node_a, _grade_of(sub, node_a), cost_tag, certificate_ref),
        SliceNode("B", KIND_DERIVATION, node_b, _grade_of(sub, node_b), cost_tag, certificate_ref),
        SliceNode("C", KIND_VERIFIER_RESULT, node_c, _grade_of(sub, node_c), cost_tag, certificate_ref),
        SliceNode("D", "gate_run", node_d, GRADE_REPLAYABLE, cost_tag, certificate_ref),
    )
    lg.info("step", step=9, name="summary", nodes=[n.hash for n in nodes], attempt=attempt.attempt_id)
    return SliceResult(
        nodes,
        tuple(arms),
        tuple(negative_nodes),
        refused_run,
        attempt.attempt_id,
        attempt.served_from_cache,
        gate_bundle.hash,
        attempt.receipt_hash,
        statement.hash,
        instance.instance_hash,
        admission,
    )


def _arm(name, result, node, gate_run):
    return Arm(
        name,
        result.accepted,
        result.reason,
        tuple(result.reasons),
        result.gate_result,
        node,
        gate_run,
        result.spawned,
        result.instance_hash,
        result.stdout_digest,
        result.stderr_digest,
        result.rc,
    )


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
    parser.add_argument(
        "--bits",
        type=int,
        default=40,
        choices=sizes,
        help=f"curve size the slice generates and verifies; the cost profile declares {', '.join(str(b) for b in sizes)}",
    )
    parser.add_argument("--seed", type=int, default=1, help="generator seed; the same seed replays to the same node A")
    parser.add_argument(
        "--skip-cache-lookup", action="store_true", help="record a fresh attempt even when the recipe is already cached"
    )


def _run(ns):
    if not Path(ns.attest).exists():
        raise CliError(
            exits.ENVIRONMENT,
            f"the attestation file {ns.attest} does not exist; the gate plan's waiver step reads its record 0",
            where=str(ns.attest),
            next_command=f"cairn attest init --attest {ns.attest} --bundle {ns.bundle} --pin {ns.pin}",
        )
    gate_bundle = bundle.open_or_refuse(ns, command="cairn m0-run")
    # Path.resolve() would follow the /var symlink and move the scratch tree off the db's own directory
    scratch_root = Path(os.path.abspath(ns.db)).parent / "m0-runs"  # noqa: PTH100
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
        raise CliError(
            exits.CONFLICT,
            f"another writer already holds {ns.db}: {exc}",
            where=str(ns.db),
            next_command=f"cairn m0-run --db {ns.db}",
        ) from None
    except gateplan.PlanInvalid as invalid:
        raise CliError(
            exits.GATE_REFUSED,
            f"the gate plan in bundle {gate_bundle.hash} is invalid ({invalid.reason}); no step ran",
            where=str(ns.bundle),
            next_command=bundle.repin_sequence(ns.bundle, ns.pin),
        ) from None
    except SliceBackend as backend:
        raise CliError(
            exits.BACKEND,
            f"the M0 slice could not complete: {backend.reason}",
            where=str(ns.db),
            next_command=_next_command(ns, NEXT_DEBUG),
        ) from None
    except SliceRefused as refused:
        raise CliError(
            exits.GATE_REFUSED,
            f"the M0 slice refused: {refused.reason}",
            where=str(ns.db),
            next_command=_next_command(ns, refused.next_step),
        ) from None
    payload = {
        "arms": [
            {
                "arm": a.arm,
                "accepted": a.accepted,
                "reason": a.reason,
                "reasons": list(a.reasons),
                "gate_result": a.gate_result,
                "node": a.node,
                "gate_run": a.gate_run,
                "spawned": a.spawned,
                "instance_hash": a.instance_hash,
                "stdout_digest": a.stdout_digest,
                "stderr_digest": a.stderr_digest,
                "rc": a.rc,
            }
            for a in result.arms
        ],
        "statement_hash": result.statement_hash,
        "instance_hash": result.instance_hash,
        "nodes": [
            {
                "label": node.label,
                "kind": node.kind,
                "hash": node.hash,
                "replay_grade": node.replay_grade,
                "cost_tag": node.cost_tag,
                "selftest_ref": node.selftest_ref,
            }
            for node in result.nodes
        ],
        "negatives": list(result.negatives),
        "refused_submission": result.refused_submission,
        "attempt_id": result.attempt_id,
        "served_from_cache": result.served_from_cache,
        "receipt_hash": result.receipt_hash,
        "bundle_hash": result.bundle_hash,
        "admission": {
            "gate_run_hash": result.admission.gate_run_hash,
            "declared_tier": result.admission.declared_tier,
            "cost_tier": result.admission.cost_tier,
        },
        "exit_code": exits.OK,
    }
    if getattr(ns, "json", False):
        cli.emit_json("m0-run", payload)
    else:
        print(
            f"admission {result.admission.gate_run_hash} declared_tier={result.admission.declared_tier} "
            f"cost_tier={result.admission.cost_tier}"
        )
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
