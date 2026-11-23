import json
import shutil

import factories
import pytest
from _substrate_helpers import ENV_MANIFEST_HASH, IDENTITY_A, SELFTEST_SUMMARY, TRANSCRIPT_HASH, recipe

from cairn import bundle, canon, claims, hunt, runner, substrate
from cairn.profile import Evaluation


def _seed_hunt(writer, statement, identity_hash, gate):
    root = writer.path.parent / "hunt-programs"
    root.mkdir(exist_ok=True)
    (root / "scoped_hunt_survival.py").write_text(
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "d.update(status='OK', candidate=False)\n"
        "print(json.dumps(d, sort_keys=True))\n"
    )
    distribution = hunt.Distribution({"bits": (30, 30)})
    method = {"interface_version": "scoped_fixture/1", "params": {}}
    hypothesis = claims.HypothesisObject(
        statement.scope["target_family"],
        {"fixture": "survival"},
        method,
        {"bits": [30, 30]},
        distribution.hash,
        statement.hash,
    )
    claims.write_hypothesis_object(writer, hypothesis)
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        1,
        {"bits": (30, 30)},
        method_identity=method,
        target_family=statement.scope["target_family"],
        assumption_set=statement.scope["assumption_set"],
        executor_identity=identity_hash,
        verifier_identity="v" * 64,
    )

    def executor(context):
        return runner.launch(
            writer,
            "scoped_hunt_survival",
            {
                "skill_identity_hash": identity_hash,
                "inputs": {"hunt_input": (context.input_blob_hash, context.input_blob_size)},
                "seed": context.seed,
                "tool_versions": IDENTITY_A["tool_digests"],
                "container_digest": IDENTITY_A["container_digest"],
                "salt": context.run_id,
            },
            bundle_hash=gate.hash,
            evaluation=Evaluation(0.1, 0.1, 0.1),
            ceiling_multiplier=4,
            tool_digests=IDENTITY_A["tool_digests"],
            scratch_root=root / "runs",
            skip_cache_lookup=True,
            do_not_cache=True,
            env_extra={"PYTHONPATH": str(root)},
            stdin_document={
                "statement_hash": context.plan.statement_hash,
                "plan_hash": context.plan.hash,
                "run_id": context.run_id,
                "trial": context.trial,
                "point": dict(context.point),
                "seed": context.seed,
                "input_blob_hash": context.input_blob_hash,
            },
        )

    result = hunt.run_hunt(writer, plan, executor, lambda *args: pytest.fail("survived hunt called verifier"))
    assert result.verdict == "SURVIVED"
    node = claims.EvidenceNode(**canon.decode(claims.EVIDENCE_NODE, writer.get_node(result.evidence_hash)["canonical"]))
    assert node.hash == result.evidence_hash
    return node


def _seed(writer, gate, *, statement_seed=31, include_lean=True):
    statement = factories.claim_statement(seed=statement_seed)
    claims.write_claim_statement(writer, statement)
    identity_hash = writer.put_identity_bundle(IDENTITY_A)
    certificate_hash = writer.put_certificate(identity_hash, TRANSCRIPT_HASH, ENV_MANIFEST_HASH, SELFTEST_SUMMARY)
    solution_blob = writer.put_blob(b"solution secret")
    recipe_key = writer.put_recipe(
        recipe(seed=statement_seed, skill_identity_hash=identity_hash, inputs={"solution": (solution_blob, 15)})
    )
    attempt_id = writer.start_attempt(recipe_key, skip_cache_lookup=True)
    writer.close_attempt(attempt_id, "OK")
    repro = factories.repro_record(attempt_id)
    claims.write_repro_record(writer, repro)
    evidence = {}
    for offset, kind in enumerate(("ladder_table", "repro_node"), 1):
        node = factories.evidence_node(
            kind,
            statement.hash,
            statement.scope,
            statement.scope["assumption_set"],
            verdict="KEEP",
            repro=repro,
            producer=(identity_hash, "skill"),
            seed=statement_seed + offset,
            attempt_id=attempt_id,
        )
        claims.write_evidence_node(writer, node)
        evidence[kind] = node
    evidence[hunt.KIND] = _seed_hunt(writer, statement, identity_hash, gate)
    lean = None
    gate_run = None
    lean_recipe = None
    if include_lean:
        lean_recipe = writer.put_recipe(recipe(seed=statement_seed + 500, inputs={"solution": (solution_blob, 15)}))
        lean_attempt = writer.start_attempt(lean_recipe, skip_cache_lookup=True)
        writer.close_attempt(lean_attempt, "OK")
        gate_run = factories.gate_run(
            gate="challenge_render",
            result="pass",
            seed=statement_seed + 20,
            bundle_hash=gate.hash,
            pin_hash=gate.pin_hash,
            statement_hash=statement.hash,
            formal_statement_hash="f" * 64,
            renderer_hash="a" * 64,
            prelude_hash="b" * 64,
            arm="dev-macos-fake-landrun",
        )
        claims.write_gate_run(writer, gate_run)
        lean = factories.evidence_node(
            "lean_artifact",
            statement.hash,
            statement.scope,
            statement.scope["assumption_set"],
            verdict="KEEP",
            producer=(identity_hash, "gate"),
            seed=statement_seed + 21,
            attempt_id=lean_attempt,
            repro=None,
        )
        claims.write_evidence_node(writer, lean)
        writer.add_lineage(lean.hash, gate_run.hash, substrate.EDGE_INPUT)
        evidence["lean_artifact"] = lean
    other_statement = factories.claim_statement(seed=statement_seed + 100)
    claims.write_claim_statement(writer, other_statement)
    other_evidence = factories.evidence_node(
        "ladder_table",
        other_statement.hash,
        other_statement.scope,
        other_statement.scope["assumption_set"],
        verdict="KEEP",
        producer=(identity_hash, "skill"),
        seed=statement_seed + 101,
        attempt_id=attempt_id,
    )
    claims.write_evidence_node(writer, other_evidence)
    transcript_node = writer.put_node("prover_transcript", b"prover proof text")
    return {
        "statement": statement,
        "identity_hash": identity_hash,
        "certificate_hash": certificate_hash,
        "recipe_key": recipe_key,
        "attempt_id": attempt_id,
        "repro": repro,
        "evidence": evidence,
        "other_statement": other_statement,
        "other_evidence": other_evidence,
        "solution_blob": solution_blob,
        "transcript_node": transcript_node,
        "gate_run": gate_run,
        "lean_recipe": lean_recipe,
    }


def _make_skeptic_bundle(tmp_path, clear_flags, name, kinds, *, tools=None):
    source = tmp_path / f"{name}-source"
    shutil.copytree(bundle.REPO_ROOT / "bundle", source)
    (source / "skeptic_scope.json").write_text(json.dumps({"evidence_kinds": kinds}))
    if tools is not None:
        (source / "worker_roles.json").write_text(
            json.dumps(
                {
                    "skeptic": {
                        "template": "scoped_read_probe",
                        "tools": tools,
                        "model": "claude-haiku-4-5-20251001",
                        "max_turns": 4,
                        "timeout_s": 120,
                    }
                }
            )
        )
        templates = json.loads((source / "role_templates.json").read_text())
        templates["scoped_read_probe"] = (
            "Call read_node with the first handed node's hash. "
            "Return exactly the informal field from that tool result, without surrounding text."
        )
        (source / "role_templates.json").write_text(json.dumps(templates))
    bundle_path = tmp_path / f"{name}.sqlite"
    pin_path = tmp_path / f"{name}.pin"
    bundle.build(source, bundle_path)
    bundle.write_pin(bundle_path, pin_path)
    clear_flags(pin_path)
    return bundle_path, pin_path
