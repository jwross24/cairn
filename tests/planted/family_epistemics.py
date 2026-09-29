import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import _substrate_helpers as helpers
import factories
from _corpus import MUST_FAIL, MUST_PASS, Entry

from cairn import (
    attest,
    bundle,
    canon,
    claims,
    foundations,
    human_authority,
    hunt,
    justify,
    keys,
    ledger,
    repro,
    selftest,
    tiergate,
)
from cairn.profile import Evaluation
from cairn.skills import toy_curve
from cairn.substrate import EDGE_INPUT, blob_hash

OWNER = "cairn-m1-cqt.3.4"
REJECT = "REJECT"
ADMIT = "ADMIT"
ATTEST_PATH = "unused-attestation-file"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
HUNT_EXECUTOR = "e" * 64
HUNT_VERIFIER = "v" * 64
HUNT_TOOLS = {"fixture": "f" * 64}
BITS = 30
SEED = 1

E_ID = "epistemics/e-small-n-killed"
F_ID = "epistemics/f-strong-without-repro"
G_ID = "epistemics/g-statistical-offered-proven"
H_ID = "epistemics/h-weaker-premise-depth-three"
I_ID = "epistemics/i-divergent-cold-rerun"
M_ADMIT_ID = "epistemics/m-tier-one-admitted"
M_COST_STAT_ID = "epistemics/m-cost-statistical-cap"
M_COST_REPRO_ID = "epistemics/m-cost-repro-cap"
M_AUTHOR_ID = "epistemics/m-author-only-cap"
M_AUDIT_ID = "epistemics/m-audit-only-refusal"


def _emit(test_id, **values):
    print(json.dumps({"entry": test_id, **values}, sort_keys=True))


def _claim(scope, informal, *, cost_model=None, claim_id):
    return claims.ClaimStatement(
        claim_id,
        1,
        informal,
        scope,
        {"units": {"size": "bits"}, "cost_model": cost_model},
    )


def _population(bits, seed=SEED):
    return {
        "target_family": "toy_curve",
        "size_interval": [bits, bits],
        "param_ranges": {"bits": [bits, bits], "seed": [seed, seed]},
        "assumption_set": [],
    }


def _cost_model():
    return {"exponent": "1/2", "constant": "0.886", "crossover": BITS}


def _cost_statement(seed):
    return factories.claim_statement(
        family="toy_curve",
        size=(BITS, BITS),
        assumptions=(),
        param_ranges={"bits": [BITS, BITS]},
        cost_model=_cost_model(),
        seed=seed,
    )


def _record_statistical_node(cold, statement, seed):
    node = factories.evidence_node(
        "statistical",
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        producer=("gate:statistical", "gate"),
        attempt_id=None,
        repro=None,
        seed=seed,
    )
    claims.write_evidence_node(cold.sub, node)
    return node


def _write_hunt_programs(root):
    root.mkdir(parents=True, exist_ok=True)
    (root / "hunt_evaluator.py").write_text(
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "def composite(n):\n"
        "    value = n * n + n + 41\n"
        "    divisor = 2\n"
        "    while divisor * divisor <= value and value % divisor:\n"
        "        divisor += 1\n"
        "    return divisor * divisor <= value\n"
        "n = d['point']['n']\n"
        "value = n * n + n + 41\n"
        "candidate = composite(n)\n"
        "small_samples = [{'n': sample, 'value': sample * sample + sample + 41, 'prime': not composite(sample)} for sample in range(40)]\n"
        "print(json.dumps({'status': 'OK', 'statement_hash': d['statement_hash'], "
        "'plan_hash': d['plan_hash'], 'run_id': d['run_id'], 'trial': d['trial'], "
        "'point': d['point'], 'seed': d['seed'], 'input_blob_hash': d['input_blob_hash'], "
        "'candidate': candidate, 'value': value, 'small_samples': small_samples}, sort_keys=True))\n"
    )
    (root / "hunt_verifier.py").write_text(
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "n = d['point']['n']\n"
        "value = n * n + n + 41\n"
        "divisor = 2\n"
        "while divisor * divisor <= value and value % divisor:\n"
        "    divisor += 1\n"
        "valid = divisor * divisor <= value and d.get('accept', True)\n"
        "print(json.dumps({'status': 'OK', 'statement_hash': d['statement_hash'], "
        "'plan_hash': d['plan_hash'], 'run_id': d['run_id'], 'trial': d['trial'], "
        "'point': d['point'], 'seed': d['seed'], 'input_blob_hash': d['input_blob_hash'], "
        "'executor_output_digest': d['executor_output_digest'], 'counterexample_valid': valid, "
        "'value': value}, sort_keys=True))\n"
    )


def small_n_hunt_killed(cold):
    programs = cold.scratch_root / "hunt-programs"
    _write_hunt_programs(programs)
    scope = {
        "target_family": "euler",
        "size_interval": [0, 41],
        "param_ranges": {"n": [0, 41]},
        "assumption_set": [],
    }
    statement = _claim(scope, "n*n+n+41 is prime", claim_id="euler-small-n-prime")
    claims.write_claim_statement(cold.sub, statement)
    distribution = hunt.Distribution({"n": (41, 41)})
    method_identity = {"interface_version": "counterexample_hunt/1", "params": {}}
    hypothesis = claims.HypothesisObject(
        "euler",
        {"claim": "prime"},
        method_identity,
        {"n": [41, 41]},
        distribution.hash,
        statement.hash,
    )
    claims.write_hypothesis_object(cold.sub, hypothesis)
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        1,
        {"n": (41, 41)},
        target_family="euler",
        executor_identity=HUNT_EXECUTOR,
        verifier_identity=HUNT_VERIFIER,
    )

    def launch(context, identity, module, inputs, document):
        return cold.launch(
            module,
            {
                "skill_identity_hash": identity,
                "inputs": inputs,
                "seed": context.seed,
                "tool_versions": HUNT_TOOLS,
                "container_digest": "c" * 64,
                "salt": f"hunt/{context.run_id}/{context.trial}/{module}",
            },
            evaluation=Evaluation(0.05, 0.05, 0.05),
            ceiling_multiplier=4,
            tool_digests=HUNT_TOOLS,
            do_not_cache=True,
            env_extra={"PYTHONPATH": str(programs)},
            stdin_document=document,
        )

    def executor(context):
        document = {
            "statement_hash": context.plan.statement_hash,
            "plan_hash": context.plan.hash,
            "run_id": context.run_id,
            "trial": context.trial,
            "point": dict(context.point),
            "seed": context.seed,
            "input_blob_hash": context.input_blob_hash,
        }
        return launch(
            context,
            HUNT_EXECUTOR,
            "hunt_evaluator",
            {"hunt_input": (context.input_blob_hash, context.input_blob_size)},
            document,
        )

    def verifier(context, execution):
        document = {
            "statement_hash": context.plan.statement_hash,
            "plan_hash": context.plan.hash,
            "run_id": context.run_id,
            "trial": context.trial,
            "point": dict(context.point),
            "seed": context.seed,
            "input_blob_hash": context.input_blob_hash,
            "executor_output_digest": execution.output_json_hash,
            "accept": True,
        }
        return launch(
            context,
            HUNT_VERIFIER,
            "hunt_verifier",
            {
                "hunt_input": (context.input_blob_hash, context.input_blob_size),
                "executor_output": (execution.output_json_hash, len(cold.sub.get_blob(execution.output_json_hash))),
            },
            document,
        )

    result = hunt.run_hunt(cold.sub, plan, executor, verifier, attest_path=ATTEST_PATH)
    entry = ledger.get_entry(cold.sub, result.ledger_hash)
    evidence = claims.get_evidence_node(cold.sub, result.evidence_hash)
    attempts = tuple(cold.sub.get_attempt(trial.attempt_id) for trial in result.record.trials)
    assert result.verdict == "KILLED" and result.standing is False, result
    assert result.record.trials[0].outcome == "COUNTEREXAMPLE", result.record.trials[0]
    assert entry["decision"] == "REFUTED" and entry["evidence_node"] == result.evidence_hash, entry
    assert cold.sub.is_root("ledger_row", result.ledger_hash)
    assert evidence["kind"] == "counterexample_hunt_record" and evidence["verdict"] == "KILLED", evidence
    assert claims.get_claim_statement(cold.sub, statement.hash)["status"] == "refuted"
    assert len(result.record.trials) == 1
    trial = result.record.trials[0]
    for attempt_id in (trial.attempt_id, trial.verifier_attempt_id):
        row = cold.sub.get_attempt(attempt_id)
        assert row["status"] == "OK" and row["skip_cache_lookup"] == 1, row
        assert cold.sub.get_receipt(row["receipt_hash"])["exit_status"] == 0
    assert attempts[0]["attempt_id"] == trial.attempt_id
    executor_receipt = cold.sub.get_receipt(attempts[0]["receipt_hash"])
    executor_output = json.loads(cold.sub.get_blob(executor_receipt["stdout_digest"]))
    small_samples = executor_output["small_samples"]
    assert [sample["n"] for sample in small_samples] == list(range(40)), small_samples
    assert all(sample["value"] == sample["n"] ** 2 + sample["n"] + 41 for sample in small_samples)
    assert all(sample["prime"] for sample in small_samples), small_samples
    assert executor_output["point"] == {"n": 41} and executor_output["value"] == 1763
    _emit(
        E_ID,
        hunt=result.run_hash,
        evidence=result.evidence_hash,
        ledger=result.ledger_hash,
        point=trial.point,
        small_sample_attempt=trial.attempt_id,
        small_sample_count=len(small_samples),
        small_sample_bounds=[small_samples[0]["n"], small_samples[-1]["n"]],
    )
    return REJECT


def strong_without_repro_capped(cold):
    identity = toy_curve.skill_identity_hash()
    attempt, output, _ = _toy_attempt(cold)
    statement = _computed_statement(output)
    claims.write_claim_statement(cold.sub, statement)
    node = factories.evidence_node(
        "ladder_table",
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        verdict="KEEP",
        producer=(identity, "skill"),
        attempt_id=attempt.attempt_id,
        repro=None,
        in_sample_sizes=(output.bits,),
        seed=612,
    )
    claims.write_evidence_node(cold.sub, node)
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    assert derived.tag == justify.CONJECTURE and derived.justified_by == node.hash, derived
    assert isinstance(result, justify.Justification)
    assert result.cls == justify.CONJECTURE and result.reason == "ladder-keep-no-repro", result
    assert derived.deferred == ()
    assert claims.get_evidence_node(cold.sub, node.hash)["repro_record_hash"] is None
    assert claims.repro_records_for_attempt(cold.sub, attempt.attempt_id) == []
    _emit(
        F_ID,
        statement=statement.hash,
        evidence=node.hash,
        attempt=attempt.attempt_id,
        order=output.n,
        class_name=derived.tag,
        reason=result.reason,
    )
    return REJECT


def statistical_proven_refused(cold):
    statement = factories.claim_statement(assumptions=(), cost_model=None, seed=621)
    claims.write_claim_statement(cold.sub, statement)
    node = _record_statistical_node(cold, statement, 622)
    row = claims.get_evidence_node(cold.sub, node.hash)
    result = justify.justify(
        row,
        {"hash": statement.hash, "scope": statement.scope},
        justify.context_for(
            cold.sub,
            row,
            {"hash": statement.hash, **statement.__dict__},
            ATTEST_PATH,
            offered_class=justify.PROVEN,
        ),
    )
    assert isinstance(result, justify.LatticeViolation), result
    assert result.reason == "statistical-cannot-justify-PROVEN", result
    _emit(G_ID, statement=statement.hash, evidence=node.hash, refusal=result.reason)
    return REJECT


def weak_foundation_at_depth_three(cold):
    statements = tuple(factories.claim_statement(assumptions=(), seed=631 + i) for i in range(4))
    for statement in statements:
        claims.write_claim_statement(cold.sub, statement)
    root, first, second, weak = statements
    for statement, tag in (
        (root, justify.PROVEN),
        (first, justify.PROVEN),
        (second, justify.PROVEN),
        (weak, justify.CONJECTURE),
    ):
        claims.append_tag_history(cold.sub, statement.hash, None, tag, None, '{"planted":true}', "test")
    foundations.add_premise(cold.sub, root.hash, first.hash)
    foundations.add_premise(cold.sub, first.hash, second.hash)
    foundations.add_premise(cold.sub, second.hash, weak.hash)
    found = foundations.violations(cold.sub, root.hash)
    assert len(found) == 1 and found[0].path == tuple(statement.hash for statement in statements), found
    assert (found[0].dependent_tag, found[0].premise_tag, found[0].depth) == (
        justify.PROVEN,
        justify.CONJECTURE,
        3,
    ), found[0]
    assert foundations.closure(cold.sub, root.hash) == [
        (root.hash, first.hash),
        (root.hash, first.hash, second.hash),
        (root.hash, first.hash, second.hash, weak.hash),
    ]
    _emit(H_ID, path=[statement.hash for statement in statements], depth=found[0].depth)
    return REJECT


def _toy_recipe(sub, identity, document):
    identity_bundle = toy_curve.identity_bundle()
    payload = json.dumps(document, sort_keys=True, separators=(",", ":")).encode("utf-8")
    input_hash = sub.put_blob(payload)
    recipe = {
        "skill_identity_hash": identity,
        "inputs": {"input.json": (input_hash, len(payload))},
        "seed": document["seed"],
        "tool_versions": {"cypari2": identity_bundle["tool_digests"]["cypari2"]},
        "container_digest": identity_bundle["container_digest"],
        "salt": "",
    }
    return recipe, input_hash, payload


def _toy_attempt(cold, *, bits=BITS, seed=SEED, gate_bundle=None, replay="Replayable"):
    identity_bundle = toy_curve.identity_bundle()
    identity = cold.sub.put_identity_bundle(identity_bundle)
    assert identity == toy_curve.skill_identity_hash()
    document = {"bits": bits, "seed": seed}
    recipe, input_hash, payload = _toy_recipe(cold.sub, identity, document)
    result = cold.launch(
        "cairn.skills.toy_curve",
        recipe,
        bundle_hash=gate_bundle.hash if gate_bundle is not None else cold.bundle_hash,
        evaluation=toy_curve.COST_PROFILE.evaluate(bits),
        ceiling_multiplier=4,
        tool_digests=identity_bundle["tool_digests"],
        replay=replay,
        env_extra={"PYTHONPATH": str(FIXTURES)},
        stdin_document=document,
    )
    row = cold.sub.get_attempt(result.attempt_id)
    receipt = cold.sub.get_receipt(result.receipt_hash)
    stdout = cold.sub.get_blob(receipt["stdout_digest"])
    output = toy_curve.ToyCurveOutput.from_json(stdout.decode("utf-8"))
    stored_recipe = canon.decode(keys.RECIPE, cold.sub.get_node(result.recipe_key)["canonical"])
    members = {
        item["child_hash"]
        for item in cold.sub.conn.execute(
            "SELECT child_hash FROM lineage WHERE parent_hash = ? AND edge_kind = 'member'",
            (result.output_manifest_hash,),
        )
    }
    input_edges = {
        item["parent_hash"]
        for item in cold.sub.lineage_of(result.output_manifest_hash)
        if item["edge_kind"] == EDGE_INPUT
    }
    assert row["status"] == "OK" and row["skip_cache_lookup"] == 1, row
    assert receipt["exit_status"] == 0 and output.status == "OK", (receipt, output)
    assert output.bits == bits and output.seed == seed, output
    assert blob_hash(stdout) in members, members
    assert receipt["stdout_digest"] == blob_hash(stdout)
    assert stored_recipe["inputs"]["input.json"] == (input_hash, len(payload)), stored_recipe
    assert stored_recipe["seed"] == seed and cold.sub.get_blob(input_hash) == payload
    assert input_hash in input_edges
    assert json.loads(stdout) == result.parsed.document
    return result, output, input_hash


def _toy_pair(cold, *, gate_bundle=None):
    identity = toy_curve.skill_identity_hash()
    first, output, first_input = _toy_attempt(cold, gate_bundle=gate_bundle)
    second, rerun_output, second_input = _toy_attempt(cold, gate_bundle=gate_bundle)
    assert first.status == second.status == "OK", (first.status, second.status)
    assert first.recipe_key == second.recipe_key
    assert first.output_manifest_hash == second.output_manifest_hash
    assert first_input == second_input
    assert output.to_dict() == rerun_output.to_dict()
    record, marked = repro.record_rerun(cold.sub, first.attempt_id, second.attempt_id, attest_path=ATTEST_PATH)
    assert record.passed and not marked, (record, marked)
    return identity, first, second, output, record


def _write_repro_node(cold, statement, identity, attempt, record, *, seed, replay_grade="Replayable"):
    node = factories.evidence_node(
        "repro_node",
        statement.hash,
        statement.scope,
        statement.scope["assumption_set"],
        producer=(identity, "skill"),
        attempt_id=attempt.attempt_id,
        repro=record,
        seed=seed,
    )
    claims.write_evidence_node(cold.sub, node, replay_grade=replay_grade)
    assert cold.sub.get_attempt(attempt.attempt_id)["output_manifest_hash"] is not None
    return node


def _build_gate_bundle(cold):
    path = cold.scratch_root / "epistemics-gate.sqlite"
    pin = cold.scratch_root / "epistemics-gate.pin"
    bundle.build(bundle.REPO_ROOT / "bundle", path)
    bundle.write_pin(path, pin)
    if hasattr(os, "chflags"):
        os.chflags(pin, 0)
    return bundle.GateBundle.open(path, pin)


def _computed_statement(output, *, cost_model=None, seed=SEED):
    scope = _population(output.bits, seed)
    if cost_model is None:
        informal = f"toy_curve computes curve order {output.n} for bits={output.bits} and seed={seed}"
        claim_id = f"toy-curve-order-{output.bits}-{seed}"
        quantities = {"units": {"size": "bits", "order": "curve_order"}, "cost_model": None}
    else:
        informal = (
            f"toy_curve computes curve order {output.n} for bits={output.bits} and seed={seed}; "
            "its runtime follows the typed cost model"
        )
        claim_id = f"toy-curve-cost-order-{output.bits}-{seed}"
        quantities = {
            "units": {"size": "bits", "order": "curve_order", "cost": "core_s"},
            "cost_model": cost_model,
        }
    return claims.ClaimStatement(claim_id, 1, informal, scope, quantities)


def tier_one_fact_admitted(cold):
    gate_bundle = _build_gate_bundle(cold)
    certification = selftest.certify(cold.sub, gate_bundle.verifier_config())
    discovery, discovered, discovery_input = _toy_attempt(cold, gate_bundle=gate_bundle)
    identity = toy_curve.skill_identity_hash()
    assert certification["identity_bundle_hash"] == identity
    assert cold.sub.certified(identity)
    statement = _computed_statement(discovered)
    claims.write_claim_statement(cold.sub, statement)
    method_identity = {"interface_version": toy_curve.INTERFACE_VERSION, "params": {}}
    hypothesis = claims.HypothesisObject(
        "toy_curve",
        {"computed_order": str(discovered.n), "bits": str(BITS), "seed": str(SEED)},
        method_identity,
        {"bits": [BITS, BITS], "seed": [SEED, SEED]},
        claim_statement_hash=statement.hash,
    )
    claims.write_hypothesis_object(cold.sub, hypothesis)
    attest_path = cold.scratch_root / "epistemics.attest"
    attest.init(str(attest_path), gate_bundle.waiver_target())
    human_authority.append(
        cold.sub,
        str(attest_path),
        human_authority.STATEMENT_RATIFICATION,
        {"statement_hash": statement.hash, "issued_by": "fixture-operator", "at": datetime.now(UTC).isoformat()},
        gate_bundle_hash=gate_bundle.hash,
    )
    decision = tiergate.TierGate(cold.sub, gate_bundle, attest_path=str(attest_path)).admit(
        tiergate.Launch(
            cost_profile=toy_curve.COST_PROFILE,
            inputs=BITS,
            budget_remaining=1000.0,
            hypothesis_key=hypothesis.hash,
            method_identity=method_identity,
            skill_identity_hash=identity,
            declared_tier=1,
            statement_hash=statement.hash,
        )
    )
    assert isinstance(decision, tiergate.Admitted), decision
    assert decision.launch.declared_tier == 1 and decision.ticket_tier == 0, decision
    ticket = claims.get_ticket(cold.sub, decision.ticket_hash)
    assert ticket["bundle_hash"] == gate_bundle.hash and ticket["statement_hash"] == statement.hash, ticket
    assert claims.get_gate_run(cold.sub, decision.gate_run_hash)["result"] == "admitted"
    first, output, first_input = _toy_attempt(cold, gate_bundle=gate_bundle)
    second, rerun_output, second_input = _toy_attempt(cold, gate_bundle=gate_bundle)
    assert first.recipe_key == second.recipe_key and first.output_manifest_hash == second.output_manifest_hash
    assert first_input == second_input == discovery_input
    assert output.to_dict() == rerun_output.to_dict() == discovered.to_dict()
    record, marked = repro.record_rerun(
        cold.sub,
        first.attempt_id,
        second.attempt_id,
        attest_path=ATTEST_PATH,
    )
    assert record.passed and not marked
    node = _write_repro_node(cold, statement, identity, first, record, seed=641)
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    assert derived.tag == justify.STRONG_EMPIRICAL and derived.justified_by == node.hash, derived
    assert isinstance(result, justify.Justification) and result.reason == "repro_node-population", result
    assert record.attempt_id == first.attempt_id and record.passed
    _emit(
        M_ADMIT_ID,
        statement=statement.hash,
        evidence=node.hash,
        order=output.n,
        discovery_attempt=discovery.attempt_id,
        first_attempt=first.attempt_id,
        rerun_attempt=second.attempt_id,
        repro=record.hash,
        gate_run=decision.gate_run_hash,
        ticket=decision.ticket_hash,
        declared_tier=decision.launch.declared_tier,
        ticket_tier=decision.ticket_tier,
        class_name=derived.tag,
    )
    return ADMIT


def cost_statistical_capped(cold):
    statement = _cost_statement(651)
    claims.write_claim_statement(cold.sub, statement)
    node = _record_statistical_node(cold, statement, 652)
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    assert derived.tag == justify.CONJECTURE and derived.justified_by == node.hash, derived
    assert isinstance(result, justify.Justification)
    assert result.reason == "cost-model-statement", result
    _emit(M_COST_STAT_ID, statement=statement.hash, evidence=node.hash, class_name=derived.tag, reason=result.reason)
    return REJECT


def cost_repro_capped(cold):
    identity, first, second, output, record = _toy_pair(cold)
    statement = _computed_statement(output, cost_model=_cost_model())
    claims.write_claim_statement(cold.sub, statement)
    node = _write_repro_node(cold, statement, identity, first, record, seed=661)
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    assert record.passed and first.recipe_key == second.recipe_key
    assert derived.tag == justify.CONJECTURE and derived.justified_by == node.hash, derived
    assert isinstance(result, justify.Justification) and result.reason == "cost-model-statement", result
    _emit(
        M_COST_REPRO_ID,
        statement=statement.hash,
        evidence=node.hash,
        order=output.n,
        attempts=[first.attempt_id, second.attempt_id],
        repro=record.hash,
        class_name=derived.tag,
        reason=result.reason,
    )
    return REJECT


def author_only_fact_capped(cold):
    identity, first, second, output, record = _toy_pair(cold)
    statement = _computed_statement(output)
    claims.write_claim_statement(cold.sub, statement)
    corpus = selftest.load_corpus()
    origins = {case["id"]: dict.fromkeys(case["fields"], justify.AUTHOR_SUPPLIED) for case in corpus["cases"]}
    certificate = {
        "corpus_origins": origins,
        "randomized_arm": False,
        "cross_check": None,
        "pass": 0,
        "floor": 0,
        "must_fail_witnesses": 0,
    }
    cold.sub.put_certificate(identity, helpers.TRANSCRIPT_HASH, helpers.ENV_MANIFEST_HASH, certificate)
    node = _write_repro_node(cold, statement, identity, first, record, seed=671)
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    inputs = {"bits": [output.bits, output.bits]}
    assert justify.producer_capped(certificate, inputs)
    assert derived.tag == justify.CONJECTURE and derived.justified_by == node.hash, derived
    assert isinstance(result, justify.Justification) and result.cls == justify.CONJECTURE, result
    _emit(
        M_AUTHOR_ID,
        statement=statement.hash,
        evidence=node.hash,
        order=output.n,
        attempts=[first.attempt_id, second.attempt_id],
        repro=record.hash,
        certificate=cold.sub.get_certificate(identity)["cert_hash"],
        class_name=derived.tag,
    )
    return REJECT


def audit_only_fact_refused(cold):
    gate_bundle = _build_gate_bundle(cold)
    certification = selftest.certify(cold.sub, gate_bundle.verifier_config())
    identity, first, second, output, record = _toy_pair(cold, gate_bundle=gate_bundle)
    assert certification["identity_bundle_hash"] == identity
    assert cold.sub.certified(identity)
    assert repro.must_fail_witnesses(cold.sub.get_certificate(identity)["selftest_summary"]) > 0
    statement = _computed_statement(output)
    claims.write_claim_statement(cold.sub, statement)
    node = _write_repro_node(
        cold,
        statement,
        identity,
        first,
        record,
        seed=681,
        replay_grade=repro.VERIFIABLE,
    )
    assert cold.sub.effective_grade(node.hash) == repro.VERIFIABLE
    grade, reason = repro.apply_owner_grade(
        cold.sub,
        node.hash,
        identity,
        repro.Verifier(repro.SKILL_VERIFIER, identity),
    )
    assert (grade, reason) == (repro.AUDIT_ONLY, "verifier-ships-in-producer-revision")
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    assert derived.tag == justify.SPECULATION and len(derived.results) == 1, derived
    assert isinstance(result, justify.Absent) and result.reason == justify.REASON_AUDIT_ONLY, result
    _emit(
        M_AUDIT_ID,
        statement=statement.hash,
        evidence=node.hash,
        order=output.n,
        attempts=[first.attempt_id, second.attempt_id],
        repro=record.hash,
        grade=grade,
        class_name=derived.tag,
        reason=result.reason,
    )
    return REJECT


def divergent_cold_rerun(cold):
    revision = cold.sub.put_identity_bundle(helpers.IDENTITY_A)
    recipe = helpers.recipe(seed=711, skill_identity_hash=revision)

    def launch():
        return cold.launch(
            "skills.nondeterministic",
            recipe,
            evaluation=Evaluation(0.05, 0.05, 0.05),
            ceiling_multiplier=4,
            tool_digests=recipe["tool_versions"],
            env_extra={"PYTHONPATH": str(FIXTURES)},
            stdin_document={"seed": 711},
        )

    first, second = launch(), launch()
    rows = tuple(cold.sub.get_attempt(attempt_id) for attempt_id in (first.attempt_id, second.attempt_id))
    assert all(row["status"] == "OK" and row["skip_cache_lookup"] == 1 for row in rows), rows
    assert rows[0]["recipe_key"] == rows[1]["recipe_key"]
    assert rows[0]["output_manifest_hash"] != rows[1]["output_manifest_hash"]
    manifests = tuple(row["output_manifest_hash"] for row in rows)
    assert all(row["inadmissible"] for row in rows), rows
    assert all(cold.sub.is_root("divergence", manifest) for manifest in manifests), manifests
    record, marked = repro.record_rerun(
        cold.sub,
        first.attempt_id,
        second.attempt_id,
        attest_path=ATTEST_PATH,
    )
    assert record.passed is False and marked == (), (record, marked)
    assert all(cold.sub.get_attempt(attempt_id)["inadmissible"] for attempt_id in (first.attempt_id, second.attempt_id))
    assert all(cold.sub.is_root("divergence", manifest) for manifest in manifests)
    scope = {
        "target_family": "nondeterministic_process",
        "size_interval": [711, 711],
        "param_ranges": {"seed": [711, 711]},
        "assumption_set": [],
    }
    statement = _claim(scope, "the same recipe returns identical bytes", claim_id="nondeterministic-recipe")
    claims.write_claim_statement(cold.sub, statement)
    evidence = factories.evidence_node(
        "repro_node",
        statement.hash,
        scope,
        (),
        producer=(revision, "skill"),
        attempt_id=first.attempt_id,
        repro=record,
        seed=712,
    )
    claims.write_evidence_node(cold.sub, evidence)
    derived = justify.derive_tag(cold.sub, statement.hash, ATTEST_PATH)
    result = derived.results[0][1]
    assert derived.tag == justify.SPECULATION
    assert isinstance(result, justify.Absent) and result.reason == "attempt-inadmissible", result
    _emit(
        I_ID,
        recipe=first.recipe_key,
        attempts=[first.attempt_id, second.attempt_id],
        manifests=list(manifests),
        repro=record.hash,
        rooted=list(manifests),
    )
    return REJECT


ENTRIES = (
    Entry(E_ID, "e", MUST_FAIL, REJECT, OWNER, small_n_hunt_killed),
    Entry(F_ID, "f", MUST_FAIL, REJECT, OWNER, strong_without_repro_capped),
    Entry(G_ID, "g", MUST_FAIL, REJECT, OWNER, statistical_proven_refused, launches=False),
    Entry(H_ID, "h", MUST_FAIL, REJECT, OWNER, weak_foundation_at_depth_three, launches=False),
    Entry(I_ID, "i", MUST_FAIL, REJECT, OWNER, divergent_cold_rerun),
    Entry(M_ADMIT_ID, "m", MUST_PASS, ADMIT, OWNER, tier_one_fact_admitted),
    Entry(M_COST_STAT_ID, "m", MUST_FAIL, REJECT, OWNER, cost_statistical_capped, launches=False),
    Entry(M_COST_REPRO_ID, "m", MUST_FAIL, REJECT, OWNER, cost_repro_capped),
    Entry(M_AUTHOR_ID, "m", MUST_FAIL, REJECT, OWNER, author_only_fact_capped),
    Entry(M_AUDIT_ID, "m", MUST_FAIL, REJECT, OWNER, audit_only_fact_refused),
)
