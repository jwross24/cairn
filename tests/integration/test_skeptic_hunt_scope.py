import base64
import json
from dataclasses import replace

import pytest
from test_counterexample_hunt import _setup
from test_skeptic_isolation import _make_skeptic_bundle

from cairn import bundle, canon, claims, hunt, instances, skeptic, substrate


@pytest.fixture
def hunt_gate(tmp_path, clear_flags):
    return bundle.GateBundle.open(*_make_skeptic_bundle(tmp_path, clear_flags, "hunt", [hunt.KIND]))


def _run(tmp_path, **kwargs):
    root = tmp_path / "hunt"
    root.mkdir()
    return _setup(root, **kwargs)


@pytest.mark.parametrize(
    ("bounds", "certified", "verdict"),
    [((0, 2), False, "SURVIVED"), ((40, 40), True, "KILLED"), ((40, 40), False, "INCOMPLETE")],
)
def test_published_hunts_expose_bound_transcripts_without_write_authority(
    tmp_path, hunt_gate, bounds, certified, verdict
):
    sub, plan, executor, verifier, statement = _run(tmp_path, bounds=bounds, certified=certified)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert result.verdict == verdict
        before = sub.conn.total_changes
        handle = skeptic.snapshot(sub, hunt_gate, statement.hash)
        assert handle.read(result.evidence_hash)["hunt_run_hash"] == result.run_hash
        for digest, schema in (
            (plan.hash, hunt.PLAN),
            (result.run_hash, hunt.RUN),
            (plan.distribution.hash, hunt.DISTRIBUTION),
        ):
            projected = handle.read(digest)
            canonical = base64.b64decode(projected["canonical"]["content"])
            assert canonical == sub.get_node(digest)["canonical"]
            assert projected["value"] == skeptic._jsonable(canon.decode(schema, canonical))
        run = handle.read(result.run_hash)["value"]
        assert run["trials"][0]["seed"] == result.record.trials[0].seed
        assert run["trials"][0]["outcome"] == result.record.trials[0].outcome
        for trial in result.record.trials:
            for digest, attempt_id in (
                (trial.execution_evidence, trial.attempt_id),
                (trial.verifier_evidence, trial.verifier_attempt_id),
            ):
                projected = handle.read(digest)
                assert base64.b64decode(projected["canonical"]["content"]) == sub.get_blob(digest)
                if attempt_id is not None:
                    assert projected["value"]["attempt"]["attempt_id"] == attempt_id
                    with pytest.raises(skeptic.ScopedReadRefused):
                        handle.read(attempt_id)
        if certified:
            assert (
                handle.read(result.evidence_hash)["verifier_certificate_hash"]
                == sub.get_certificate(plan.verifier_identity)["cert_hash"]
            )
            for identity in (plan.executor_identity, plan.verifier_identity):
                certificate = sub.get_certificate(identity)
                projected = handle.read(certificate["cert_hash"])
                assert projected["companion_observation"]["selftest_summary"] == certificate["selftest_summary"]
                assert json.loads(projected["companion_observation"]["selftest_summary"])["must_fail_witnesses"] == 1
        if verdict == "INCOMPLETE":
            assert run["trials"][0]["verifier_status"] == "verifier-uncertified"
            assert handle.read(result.evidence_hash)["verifier_certificate_hash"] is None
        request = handle.request_rerun(result.evidence_hash)
        assert request.attempt_id == result.record.trials[-1].attempt_id
        assert request.statement_hash == statement.hash
        assert sub.conn.total_changes == before
        run["nonce"] = "changed"
        assert handle.read(result.run_hash)["value"]["nonce"] == result.record.nonce
        assert not hasattr(handle, "conn")
    finally:
        sub.close()


def _foreign_hunt(sub, plan, executor, verifier, statement):
    other = replace(statement, claim_id=statement.claim_id + "-other")
    claims.write_claim_statement(sub, other)
    hypothesis = claims.HypothesisObject(
        plan.target_family,
        {"claim": "other"},
        dict(plan.method_identity),
        {axis: list(bounds) for axis, bounds in plan.family_bounds.items()},
        plan.distribution.hash,
        other.hash,
    )
    claims.write_hypothesis_object(sub, hypothesis)
    other_plan = replace(plan, statement_hash=other.hash, hypothesis_key=hypothesis.hash)
    return other_plan, hunt.run_hunt(sub, other_plan, executor, verifier)


def test_other_statement_hunt_material_is_outside_scope(tmp_path, hunt_gate):
    sub, plan, executor, verifier, statement = _run(tmp_path, certified=True)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        other_plan, other = _foreign_hunt(sub, plan, executor, verifier, statement)
        handle = skeptic.snapshot(sub, hunt_gate, statement.hash)
        for digest in (
            other_plan.hash,
            other.run_hash,
            other.evidence_hash,
            other.record.trials[0].execution_evidence,
            other.record.trials[0].verifier_evidence,
        ):
            with pytest.raises(skeptic.ScopedReadRefused, match="outside"):
                handle.read(digest)
        assert handle.read(result.run_hash)["value"]["statement_hash"] == statement.hash
    finally:
        sub.close()


def test_unpublished_entropy_refuses_snapshot_before_publication(tmp_path, hunt_gate, monkeypatch):
    sub, plan, executor, verifier, statement = _run(tmp_path, certified=True)
    publish = instances.publish_nonce
    observed = []

    def observing_publish(store, nonce, **kwargs):
        assert instances.get_nonce(store, nonce).withheld
        with pytest.raises(skeptic.ScopedReadRefused, match="unpublished"):
            skeptic.snapshot(store, hunt_gate, statement.hash)
        observed.append(nonce)
        return publish(store, nonce, **kwargs)

    monkeypatch.setattr(instances, "publish_nonce", observing_publish)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        assert observed == [result.record.nonce]
        assert skeptic.snapshot(sub, hunt_gate, statement.hash).read(result.run_hash)["value"]["nonce"] == observed[0]
    finally:
        sub.close()


def _bound_evidence(sub, result, record, identity):
    run_hash = sub.put_node("hunt_run", hunt.run_canonical(record), producer_identity="gate:hunt")
    for edge in sub.lineage_of(result.run_hash):
        sub.add_lineage(run_hash, edge["parent_hash"], edge["edge_kind"])
    for digest in (record.plan_hash, record.distribution_hash):
        sub.add_lineage(run_hash, digest, substrate.EDGE_INPUT)
    for trial in record.trials:
        for digest in (trial.execution_evidence, trial.verifier_evidence):
            if digest is not None:
                sub.add_lineage(run_hash, digest, substrate.EDGE_INPUT)
    evidence = claims.EvidenceNode(
        **canon.decode(claims.EVIDENCE_NODE, sub.get_node(result.evidence_hash)["canonical"])
    )
    evidence = replace(evidence, producer_identity=identity)
    claims.write_evidence_node(sub, evidence)
    sub.add_lineage(evidence.hash, run_hash, substrate.EDGE_INPUT)
    return evidence


@pytest.mark.parametrize(
    "mutation", ["foreign_plan", "missing_nonce", "verifier_attempt", "trial_seed", "evidence_recipe"]
)
def test_mismatched_canonical_hunt_sources_are_refused(tmp_path, hunt_gate, mutation):
    sub, plan, executor, verifier, statement = _run(tmp_path, certified=True)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        if mutation == "foreign_plan":
            other_plan, _ = _foreign_hunt(sub, plan, executor, verifier, statement)
            record = replace(result.record, plan_hash=other_plan.hash)
        elif mutation == "missing_nonce":
            record = replace(result.record, nonce=instances.fresh_nonce())
        elif mutation == "evidence_recipe":
            trial = result.record.trials[0]
            payload = json.loads(sub.get_blob(trial.execution_evidence))
            payload["recipe"]["seed"] += 1
            digest = sub.put_blob(json.dumps(payload, sort_keys=True).encode())
            record = replace(result.record, trials=(replace(trial, execution_evidence=digest),))
        else:
            trial = result.record.trials[0]
            trial = (
                replace(trial, verifier_attempt_id=trial.attempt_id)
                if mutation == "verifier_attempt"
                else replace(trial, seed=trial.seed + 1)
            )
            record = replace(result.record, trials=(trial,))
        _bound_evidence(sub, result, record, "gate:bad-" + mutation)
        with pytest.raises(skeptic.ScopedReadRefused):
            skeptic.snapshot(sub, hunt_gate, statement.hash)
    finally:
        sub.close()


def test_missing_and_ambiguous_hunt_bindings_are_refused(tmp_path, hunt_gate):
    sub, plan, executor, verifier, statement = _run(tmp_path, certified=True)
    try:
        result = hunt.run_hunt(sub, plan, executor, verifier)
        detached = claims.EvidenceNode(
            **canon.decode(claims.EVIDENCE_NODE, sub.get_node(result.evidence_hash)["canonical"])
        )
        detached = replace(detached, producer_identity="gate:detached")
        claims.write_evidence_node(sub, detached)
        with pytest.raises(skeptic.ScopedReadRefused, match="unique bound"):
            skeptic.snapshot(sub, hunt_gate, statement.hash)
        sub.add_lineage(detached.hash, result.run_hash, substrate.EDGE_INPUT)
        another = replace(result.record, nonce=instances.fresh_nonce())
        other_hash = sub.put_node("hunt_run", hunt.run_canonical(another), producer_identity="gate:hunt")
        sub.add_lineage(detached.hash, other_hash, substrate.EDGE_INPUT)
        with pytest.raises(skeptic.ScopedReadRefused, match="unique bound"):
            skeptic.snapshot(sub, hunt_gate, statement.hash)
    finally:
        sub.close()
