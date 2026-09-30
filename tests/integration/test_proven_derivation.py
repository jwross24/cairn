import json
from dataclasses import replace

import _substrate_helpers as helpers
import factories
import pytest
import test_container_statement_hash as linux_tests
import test_solution_build_compile as dev_tests

from cairn import attest, challenge, claims, container, human_queue, justify, solutionchecks, solutionplan

linux_bundle = linux_tests.linux_bundle
linux_image = linux_tests.linux_image
linux_dependencies = linux_tests.linux_dependencies
linux_project = linux_tests.linux_project
mathlib_free_bundle = dev_tests.mathlib_free_bundle
prepared_free = dev_tests.prepared_free
statement = dev_tests.statement
comparator = dev_tests.comparator


@pytest.fixture(scope="module", autouse=True)
def bounded_containers():
    run = container.run_docker
    calls = []

    def bounded(ctx, *args, **kwargs):
        if args and args[0] == "run":
            args = (args[0], "--memory=6g", *args[1:])
            calls.append(args)
        return run(ctx, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(container, "run_docker", bounded)
        yield calls


def _baseline(sub, stmt):
    claims.write_claim_statement(sub, stmt)
    node = claims.EvidenceNode(
        kind="model_proof",
        target_statement_hash=stmt.hash,
        population=stmt.scope,
        assumptions=frozenset(stmt.scope["assumption_set"]),
        producer_identity="test:model",
        producer_tag="gate",
    )
    claims.write_evidence_node(sub, node)


def _review(sub, path, stmt, gate, decision="approve"):
    unplaced = claims.ReviewVerdict(
        statement_hash=stmt.hash,
        reviewer="test-owned-operator",
        verdict=decision,
        checklist_template_hash=gate.digest_of("role_templates"),
        gate_bundle_hash=gate.hash,
        at="2026-09-30T16:00:00Z",
    )
    offset = attest.append_record(path, claims.review_verdict_canonical(unplaced))
    verdict = replace(unplaced, file_offset=offset)
    claims.write_review_verdict(sub, verdict)
    return verdict


def _artifact(sub, stmt, arm):
    nodes = [row for row in claims.evidence_for(sub, stmt.hash) if row["kind"] == "lean_artifact"]
    assert len(nodes) == 1
    node = nodes[0]
    run = claims.get_gate_run(sub, node["producer_identity"])
    assert run is not None
    assert (run["gate"], run["plan_step"], run["result"], run["arm"]) == (
        solutionplan.SUMMARY_GATE,
        solutionplan.SUMMARY_STEP,
        "pass",
        arm,
    )
    assert run["statement_hash"] == stmt.hash
    assert run["formal_statement_hash"]
    assert [edge["parent_hash"] for edge in sub.lineage_of(node["hash"]) if edge["edge_kind"] == "input"] == [
        run["run_id"]
    ]
    return node, run


def _plan_rows():
    return [
        {
            "step": kind,
            "kind": kind,
            "expect": solutionplan.KIND_EXPECTATION[kind],
            "blocking": True,
            "timeout_s": 600.0,
        }
        for kind in solutionplan.STEP_KINDS
    ]


@pytest.mark.timeout(1800)
def test_real_gold_artifact_requires_matching_review_and_records_the_bindings(
    linux_bundle, linux_image, linux_project, tmp_path, clear_flags, bounded_containers
):
    old = factories.claim_statement(seed=4, formal_source=linux_tests.FORMAL)
    current = replace(old, version=old.version + 1, informal="Reviewed replacement statement", supersedes=old.hash)
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, linux_bundle.waiver_target())
    sub = helpers.open_writer(tmp_path)
    try:
        claims.write_claim_statement(sub, old)
        _baseline(sub, current)
        assert justify.derive_tag(sub, current.hash, path).tag == justify.CONJECTURE
        prepared = solutionchecks.prepare_container(
            linux_bundle,
            linux_image,
            current,
            ("challenge_curve",),
            root=tmp_path / "prepared",
            dependency_project=linux_project[0],
        )
        result = solutionchecks.run_container(
            linux_bundle,
            linux_image,
            current,
            challenge.Submission(
                solution_module=linux_bundle.challenge_prelude + linux_tests.FORMAL.replace("sorry", "rfl").encode(),
                formal_statement_hash=prepared.formal_statement_hash,
            ),
            ("challenge_curve",),
            _plan_rows(),
            sub=sub,
            root=tmp_path / "candidate",
            work_dir=tmp_path / "axioms",
            prepared=prepared,
        )
        assert result.ok, result.steps
        artifact, run = _artifact(sub, current, container.GOLD_ARM)
        missing = justify.derive_tag(sub, current.hash, path)
        assert missing.tag == justify.CONJECTURE
        assert any(isinstance(value, justify.Pending) for _, value in missing.results)
        pending = human_queue.open_items(sub, path)
        assert len(pending) == 1
        assert (pending[0]["class"], pending[0]["target"], pending[0]["blocker"]) == (
            human_queue.STATEMENT_REVIEW,
            current.hash,
            human_queue.STATEMENT_REVIEW,
        )
        _review(sub, path, old, linux_bundle)
        stale = justify.derive_tag(sub, current.hash, path)
        assert stale.tag == justify.CONJECTURE
        assert len(human_queue.open_items(sub, path)) == 1
        rejected = _review(sub, path, current, linux_bundle, "reject")
        row_id = claims.review_verdicts_for(sub, current.hash)[-1]["row_id"]
        sub.conn.execute(
            "INSERT INTO review_verdicts "
            "(statement_hash, reviewer, verdict, checklist_template_hash, gate_bundle_hash, at, supersedes, record_digest, file_offset) "
            "SELECT statement_hash, reviewer, 'approve', checklist_template_hash, gate_bundle_hash, at, supersedes, record_digest, file_offset "
            "FROM review_verdicts WHERE row_id = ?",
            (row_id,),
        )
        sub.conn.commit()
        misplaced = replace(rejected, verdict="approve", file_offset=rejected.file_offset + 1)
        claims.write_review_verdict(sub, misplaced)
        assert [review["verdict"] for review in claims.visible_review_verdicts(sub, current.hash, path)] == ["reject"]
        context = justify.context_for(sub, artifact, claims.get_claim_statement(sub, current.hash), path)
        assert context.formalization_reason is None
        assert not context.approved
        refused = justify.derive_tag(sub, current.hash, path)
        assert refused.tag == justify.CONJECTURE
        assert any(isinstance(value, justify.Pending) for _, value in refused.results)
        verdict = _review(sub, path, current, linux_bundle)
        proven = justify.derive_tag(sub, current.hash, path)
        assert proven.tag == justify.PROVEN
        history = claims.tag_history_for(sub, current.hash)[-1]
        assert (history["from_tag"], history["to_tag"], history["evidence_hash"]) == (
            justify.CONJECTURE,
            justify.PROVEN,
            artifact["hash"],
        )
        pointers = json.loads(history["justification"])
        assert pointers["gate_run_hash"] == run["run_id"]
        assert pointers["review_verdict_hash"] == verdict.hash
        assert pointers["record_digest"] == verdict.record_digest
        assert pointers["file_offset"] == verdict.file_offset
        assert bounded_containers
        assert all("--memory=6g" in args for args in bounded_containers)
        print(f"real docker memory-bound invocations: {len(bounded_containers)}")
        print(
            "gold matching review: PROVEN; missing review: CONJECTURE + statement_review; superseded review: CONJECTURE"
        )
    finally:
        sub.close()


@pytest.mark.timeout(1800)
def test_real_approved_dev_artifact_stays_at_its_supported_tag_with_the_arm_named(
    mathlib_free_bundle, statement, prepared_free, comparator, tmp_path, clear_flags
):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, mathlib_free_bundle.waiver_target())
    sub = helpers.open_writer(tmp_path)
    try:
        _baseline(sub, statement)
        assert justify.derive_tag(sub, statement.hash, path).tag == justify.CONJECTURE
        result = solutionchecks.run_dev(
            mathlib_free_bundle,
            statement,
            challenge.Submission(
                solution_module=dev_tests.PROOF.encode(), formal_statement_hash=prepared_free.formal_statement_hash
            ),
            dev_tests.THEOREMS,
            dev_tests._plan_rows(),
            sub=sub,
            root=tmp_path / "candidate",
            prepared=prepared_free,
            comparator=comparator,
        )
        assert result.ok, result.steps
        artifact, _ = _artifact(sub, statement, container.DEV_ARM)
        _review(sub, path, statement, mathlib_free_bundle)
        derived = justify.derive_tag(sub, statement.hash, path)
        assert derived.tag == justify.CONJECTURE
        refusal = next(value for row, value in derived.results if row["hash"] == artifact["hash"])
        assert isinstance(refusal, justify.Absent)
        assert container.DEV_ARM in refusal.reason
        print(f"approved {container.DEV_ARM}: CONJECTURE; reason={refusal.reason}")
    finally:
        sub.close()
