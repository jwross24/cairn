import json

import pytest

from cairn import claims, gc, hunt, instances, ledger, runner, substrate
from cairn.profile import Evaluation

EXECUTOR = "e" * 64
VERIFIER = "v" * 64
TOOL_DIGESTS = {"fixture": "f" * 64}


def _programs(root):
    (root / "hunt_evaluator.py").write_text(
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "n = d['point']['n']\n"
        "assert 'nonce' not in d\n"
        "value = n * n + n + 41\n"
        "divisor = 2\n"
        "while divisor * divisor <= value and value % divisor:\n"
        "    divisor += 1\n"
        "candidate = divisor * divisor <= value\n"
        "print(json.dumps({'status': 'OK', 'statement_hash': d['statement_hash'], 'plan_hash': d['plan_hash'], 'run_id': d['run_id'], 'trial': d['trial'], 'point': d['point'], 'seed': d['seed'], 'input_blob_hash': d['input_blob_hash'], 'candidate': candidate, 'value': value}, sort_keys=True))\n"
    )
    (root / "hunt_verifier.py").write_text(
        "import json, sys\n"
        "d = json.load(sys.stdin)\n"
        "n = d['point']['n']\n"
        "assert 'nonce' not in d\n"
        "value = n * n + n + 41\n"
        "divisor = 2\n"
        "while divisor * divisor <= value and value % divisor:\n"
        "    divisor += 1\n"
        "valid = divisor * divisor <= value and d.get('accept', True)\n"
        "print(json.dumps({'status': 'OK', 'statement_hash': d['statement_hash'], 'plan_hash': d['plan_hash'], 'run_id': d['run_id'], 'trial': d['trial'], 'point': d['point'], 'seed': d['seed'], 'input_blob_hash': d['input_blob_hash'], 'executor_output_digest': d['executor_output_digest'], 'counterexample_valid': valid, 'value': value}, sort_keys=True))\n"
    )


def _claim(sub, bounds):
    scope = {
        "target_family": "euler",
        "size_interval": list(bounds),
        "param_ranges": {"n": list(bounds)},
        "assumption_set": [],
    }
    statement = claims.ClaimStatement(
        "euler-prime",
        1,
        "n*n+n+41 is prime",
        scope,
        {"units": {}, "cost_model": None},
    )
    claims.write_claim_statement(sub, statement)
    return statement


def _setup(tmp_path, bounds=(40, 41), trials=2, verifier_valid=True):
    _programs(tmp_path)
    sub = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    statement = _claim(sub, bounds)
    distribution = hunt.Distribution({"n": bounds})
    plan = hunt.HuntPlan(
        statement.hash,
        "h" * 64,
        distribution,
        trials,
        {"n": bounds},
        target_family="euler",
        executor_identity=EXECUTOR,
        verifier_identity=VERIFIER,
    )
    hypothesis = claims.HypothesisObject(
        "euler",
        {"claim": "prime"},
        dict(plan.method_identity),
        {"n": list(bounds)},
        distribution.hash,
        statement.hash,
    )
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        trials,
        {"n": bounds},
        target_family="euler",
        executor_identity=EXECUTOR,
        verifier_identity=VERIFIER,
    )
    claims.write_hypothesis_object(sub, hypothesis)

    def launch(ctx, identity, module, inputs, document, expected_wall=0.05):
        recipe = {
            "skill_identity_hash": identity,
            "inputs": inputs,
            "seed": ctx.seed,
            "tool_versions": TOOL_DIGESTS,
            "container_digest": "c" * 64,
            "salt": f"hunt/{ctx.run_id}/{ctx.trial}/{module}",
        }
        return runner.launch(
            sub,
            module,
            recipe,
            bundle_hash="b" * 64,
            evaluation=Evaluation(expected_wall, expected_wall, expected_wall),
            ceiling_multiplier=4,
            tool_digests=TOOL_DIGESTS,
            scratch_root=tmp_path / "runs",
            skip_cache_lookup=True,
            do_not_cache=True,
            env_extra={"PYTHONPATH": str(tmp_path)},
            stdin_document=document,
        )

    def executor(ctx):
        document = {
            "statement_hash": ctx.plan.statement_hash,
            "plan_hash": ctx.plan.hash,
            "run_id": ctx.run_id,
            "trial": ctx.trial,
            "point": dict(ctx.point),
            "seed": ctx.seed,
            "input_blob_hash": ctx.input_blob_hash,
        }
        return launch(
            ctx,
            EXECUTOR,
            "hunt_evaluator",
            {"hunt_input": (ctx.input_blob_hash, ctx.input_blob_size)},
            document,
        )

    def verifier(ctx, execution):
        output_size = len(sub.get_blob(execution.output_json_hash))
        document = {
            "statement_hash": ctx.plan.statement_hash,
            "plan_hash": ctx.plan.hash,
            "run_id": ctx.run_id,
            "trial": ctx.trial,
            "point": dict(ctx.point),
            "seed": ctx.seed,
            "input_blob_hash": ctx.input_blob_hash,
            "executor_output_digest": execution.output_json_hash,
            "accept": verifier_valid,
        }
        return launch(
            ctx,
            VERIFIER,
            "hunt_verifier",
            {
                "hunt_input": (ctx.input_blob_hash, ctx.input_blob_size),
                "executor_output": (execution.output_json_hash, output_size),
            },
            document,
        )

    return sub, plan, executor, verifier, statement


def test_killed_hunt_records_real_counterexample_and_full_transcript(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "KILLED"
        assert result.record.trials[0].outcome == "COUNTEREXAMPLE"
        assert result.ledger_hash is not None
        entry = ledger.get_entry(sub, result.ledger_hash)
        assert entry["decision"] == "REFUTED"
        assert entry["evidence_node"] == result.evidence_hash
        assert json.loads(entry["measured_points"]) == [
            {"numeric": dict(result.record.trials[0].point), "categorical": {}}
        ]
        assert json.loads(entry["result"])["ci"] == ["1", "1"]
        verified = sub.get_attempt(result.record.trials[0].verifier_attempt_id)
        assert verified["status"] == "OK"
        assert sub.get_receipt(verified["receipt_hash"])["exit_status"] == 0
        assert sub.get_attempt(result.record.trials[0].attempt_id)["status"] == "OK"
        assert hunt.record_for(sub, result.run_hash) == result.record
        assert instances.nonces_for(sub, result.record.hypothesis_key)[0].published_at is not None
        assert (
            sub.conn.execute("SELECT status FROM claim_statements WHERE hash = ?", (statement.hash,)).fetchone()[0]
            == "refuted"
        )
        for trial in result.record.trials:
            for digest in (trial.execution_evidence, trial.verifier_evidence):
                evidence = json.loads(sub.get_blob(digest))
                assert set(evidence["stream_blobs"]) == {"stdout", "stderr"}
                assert sub.get_blob(evidence["stream_blobs"]["stderr"]) == b""
                assert json.loads(sub.get_blob(evidence["stream_blobs"]["stdout"]))["status"] == "OK"
        print(json.dumps({"record": hunt.canon.decode(hunt.RUN, hunt.run_canonical(result.record)), "ledger": entry}))
    finally:
        sub.close()


def test_survived_hunt_runs_every_declared_trial_and_exposes_only_standing(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, bounds=(0, 39), trials=40)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "SURVIVED"
        assert result.standing is True
        assert len(result.record.trials) == 40
        assert all(trial.outcome == "SURVIVED_TRIAL" for trial in result.record.trials)
        assert sub.conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 40
        assert result.ledger_hash is None
        assert gc.plan(sub)["candidates"] == []
        assert (
            sub.conn.execute("SELECT status FROM claim_statements WHERE hash = ?", (statement.hash,)).fetchone()[0]
            == "open"
        )
        print(json.dumps(hunt.canon.decode(hunt.RUN, hunt.run_canonical(result.record))))
    finally:
        sub.close()


def test_failed_verifier_keeps_hunt_incomplete_without_standing(tmp_path):
    sub, plan, executor, verifier, statement = _setup(tmp_path, verifier_valid=False)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == "INCOMPLETE"
        assert result.standing is False
        assert result.ledger_hash is None
        assert result.record.trials[0].outcome == "VERIFIER_FAILED"
        assert (
            sub.conn.execute("SELECT status FROM claim_statements WHERE hash = ?", (statement.hash,)).fetchone()[0]
            == "open"
        )
        print(json.dumps(hunt.canon.decode(hunt.RUN, hunt.run_canonical(result.record))))
    finally:
        sub.close()


def test_sampler_outside_declared_distribution_is_refused_before_execution(tmp_path, monkeypatch):
    sub, plan, executor, verifier, _ = _setup(tmp_path, bounds=(40, 41), trials=2)
    calls = []

    def unexpected_executor(_):
        calls.append(True)
        raise AssertionError("executor must not run")

    monkeypatch.setattr(hunt, "sample_point", lambda *_: {"n": 42})
    try:
        with pytest.raises(hunt.SamplerRefused):
            hunt.run_hunt(sub, plan, unexpected_executor, verifier)
        assert calls == []
        assert sub.conn.execute("SELECT count(*) FROM attempts").fetchone()[0] == 0
        print("SamplerRefused: point n=42 outside declared [40,41]; attempts=0")
    finally:
        sub.close()


def test_ceiling_stopped_real_attempt_is_incomplete_without_standing(tmp_path):
    _programs(tmp_path)
    sub = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    statement = _claim(sub, (1, 1))
    distribution = hunt.Distribution({"n": (1, 1)})
    hypothesis = claims.HypothesisObject(
        "euler",
        {"claim": "prime"},
        {"interface_version": "counterexample_hunt/1", "params": {}},
        {"n": [1, 1]},
        distribution.hash,
        statement.hash,
    )
    claims.write_hypothesis_object(sub, hypothesis)
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        2,
        {"n": (1, 1)},
        target_family="euler",
        executor_identity=EXECUTOR,
        verifier_identity=VERIFIER,
    )

    def executor(ctx):
        recipe = {
            "skill_identity_hash": EXECUTOR,
            "inputs": {"hunt_input": (ctx.input_blob_hash, ctx.input_blob_size)},
            "seed": ctx.seed,
            "tool_versions": TOOL_DIGESTS,
            "container_digest": "c" * 64,
            "salt": f"budget/{ctx.run_id}",
        }
        return runner.launch(
            sub,
            "tests.fixtures.skills.cpu_burner",
            recipe,
            bundle_hash="b" * 64,
            evaluation=Evaluation(0.005, 0.005, 0.005),
            ceiling_multiplier=4,
            tool_digests=TOOL_DIGESTS,
            scratch_root=tmp_path / "runs",
            skip_cache_lookup=True,
            do_not_cache=True,
            stdin_document={
                "statement_hash": ctx.plan.statement_hash,
                "plan_hash": ctx.plan.hash,
                "run_id": ctx.run_id,
                "trial": ctx.trial,
                "point": dict(ctx.point),
                "seed": ctx.seed,
                "input_blob_hash": ctx.input_blob_hash,
            },
        )

    try:
        result = hunt.run_hunt(sub, plan, executor, lambda *_: (_ for _ in ()).throw(AssertionError("verifier called")))
        assert result.verdict == "INCOMPLETE"
        assert result.standing is False
        assert result.record.budget_status == runner.STATUS_BUDGET_EXCEEDED
        attempt = sub.get_attempt(result.record.trials[0].attempt_id)
        assert attempt["status"] == runner.STATUS_BUDGET_EXCEEDED
        receipt = sub.get_receipt(attempt["receipt_hash"])
        assert receipt is not None
        assert receipt["exit_status"] == 0
        assert receipt["cpu_user_s"] + receipt["cpu_sys_s"] > 0.02
        evidence = json.loads(sub.get_blob(result.record.trials[0].execution_evidence))
        assert evidence["receipt"]["stdout_digest"] == receipt["stdout_digest"]
        assert set(evidence["stream_blobs"]) == {"stdout", "stderr"}
        assert sub.get_blob(evidence["stream_blobs"]["stdout"]) == b'{"status":"OK"}\n'
        assert sub.get_blob(evidence["stream_blobs"]["stderr"]) == b""
        assert result.record.completed_trial_count < result.record.declared_trial_count
        print(
            json.dumps({"record": hunt.canon.decode(hunt.RUN, hunt.run_canonical(result.record)), "receipt": receipt})
        )
    finally:
        sub.close()
