import dataclasses
import importlib.util
import json
import sqlite3
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import pytest

from cairn import claims, hunt, instances, justify, keys, ladder, substrate
from cairn import small_numbers_floor as floor

ADAPTER_PATH = (
    Path(__file__).resolve().parents[2] / "research/grounding/small-numbers-floor-2026-09-30/run_experiment.py"
)
SPEC = importlib.util.spec_from_file_location("floor_experiment", ADAPTER_PATH)
assert SPEC is not None and SPEC.loader is not None
EXPERIMENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPERIMENT
SPEC.loader.exec_module(EXPERIMENT)

GIT_RUNNER = (
    "import shutil, subprocess, sys\n"
    "p = subprocess.run([shutil.which('git'), '-C', sys.argv[1], *sys.argv[2:]], capture_output=True, text=True)\n"
    "sys.stdout.write(p.stdout)\n"
    "sys.stderr.write(p.stderr)\n"
    "sys.exit(p.returncode)\n"
)
SOURCE_GUARD_RUNNER = (
    "import importlib.util, json, sys\n"
    "spec = importlib.util.spec_from_file_location('floor_guard_probe', sys.argv[1])\n"
    "module = importlib.util.module_from_spec(spec)\n"
    "sys.modules[spec.name] = module\n"
    "spec.loader.exec_module(module)\n"
    "try:\n"
    "    revision = module._verify_committed_source(sys.argv[2], sys.argv[3])\n"
    "except module.floor.FloorRefused as error:\n"
    "    print(json.dumps({'refused': True, 'error': str(error)}))\n"
    "else:\n"
    "    print(json.dumps({'refused': False, 'revision': revision}))\n"
)


def _git(root, *args):
    result = subprocess.run(
        [sys.executable, "-c", GIT_RUNNER, str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _source_guard(root, revision):
    result = subprocess.run(
        [sys.executable, "-c", SOURCE_GUARD_RUNNER, str(ADAPTER_PATH), str(root), revision],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


@pytest.fixture
def committed_floor_source(tmp_path):
    root = tmp_path / "source"
    root.mkdir()
    hooks = tmp_path / "hooks"
    hooks.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.name", "floor source fixture")
    _git(root, "config", "user.email", "floor@example.invalid")
    _git(root, "config", "commit.gpgsign", "false")
    _git(root, "config", "core.hooksPath", str(hooks))
    _git(root, "config", "core.excludesFile", "/dev/null")
    paths = [
        "src/cairn/hunt.py",
        "src/cairn/ladder.py",
        "src/cairn/instances.py",
        "src/cairn/runner.py",
        "src/cairn/repro.py",
        "src/cairn/gp/verify.gp",
        "pyproject.toml",
        "uv.lock",
        "tests/fixtures/small_numbers_floor_executor.py",
        "tests/fixtures/small_numbers_floor_verifier.py",
        "research/grounding/small-numbers-floor-2026-09-30/run_experiment.py",
        "research/grounding/small-numbers-floor-2026-09-30/preregistration.json",
        ".gitignore",
    ]
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("extra.py\n" if relative == ".gitignore" else "fixture payload\n")
    _git(root, "add", "--", *paths)
    _git(root, "commit", "-m", "Record floor source fixture")
    return root, _git(root, "rev-parse", "HEAD")


def _setup(tmp_path, *, bounds=(0, 0), trials=6, control="clean", mode="normal"):
    sub = substrate.Substrate.open(tmp_path / "substrate.sqlite")
    distribution = hunt.Distribution({"n": bounds})
    method = {"interface_version": "floor_fixture/1", "params": {"control": control}}
    statement = claims.ClaimStatement(
        "floor-fixture",
        1,
        "fixture control holds",
        {
            "target_family": "floor-fixture",
            "size_interval": list(bounds),
            "param_ranges": {"n": list(bounds)},
            "assumption_set": [],
        },
        {"units": {}, "cost_model": None},
    )
    claims.write_claim_statement(sub, statement)
    hypothesis = claims.HypothesisObject(
        "floor-fixture", {"control": control}, method, {"n": list(bounds)}, distribution.hash, statement.hash
    )
    claims.write_hypothesis_object(sub, hypothesis)
    adapter = EXPERIMENT.FixtureAdapter(sub, tmp_path / "runs", control, endpoint=1, mode=mode)
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        trials,
        {"n": bounds},
        method_identity=method,
        target_family="floor-fixture",
        executor_identity=adapter.identity(),
        verifier_identity=adapter.identity(True),
    )
    study_hash = floor._write(sub, floor.STUDY_KIND, {"decision_rule": "fixture integration only"})
    protocol = floor.Protocol(plan.hash, plan.hypothesis_key, distribution.hash, "1/2", "1/20", trials, study_hash)
    floor.register_protocol(sub, protocol, plan)
    return sub, plan, protocol, adapter, statement


def test_real_clean_hunt_registration_receipts_and_reproduction(tmp_path, monkeypatch):
    sub, plan, protocol, adapter, statement = _setup(tmp_path)
    real_sampler = hunt.sample_point
    sampled = []

    def observing_sampler(distribution, seed):
        rows = sub.conn.execute("SELECT hash FROM nodes WHERE kind = ?", (floor.RUN_KIND,)).fetchall()
        assert len(rows) == 1
        registration = floor._read(sub, rows[0]["hash"], floor.RUN_KIND)
        assert registration["protocol_hash"] == protocol.hash
        assert registration["sampler_hash"] == floor.sampler_identity()
        nonce = instances.get_nonce(sub, registration["nonce"])
        assert nonce.withheld is True or len(sampled) >= plan.trial_count
        sampled.append(seed)
        return real_sampler(distribution, seed)

    monkeypatch.setattr(hunt, "sample_point", observing_sampler)
    try:
        result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        assert result.verdict == "SURVIVED"
        registration_hash, registration = floor.registration_for(sub, result)
        commitment_position, commitment = ladder.commitment_for(sub, result.record.nonce)
        assert registration["commitment_hash"] == commitment.hash
        assert registration["nonce"] == result.record.nonce
        assert ladder.sequence_position(sub, plan.hypothesis_key) < ladder.sequence_position(sub, protocol.hash)
        assert ladder.sequence_position(sub, protocol.hash) < commitment_position
        assert commitment_position < ladder.sequence_position(sub, registration_hash)
        assert ladder.sequence_position(sub, registration_hash) < ladder.sequence_position(sub, result.run_hash)
        assert instances.get_nonce(sub, result.record.nonce).published_at is not None
        for trial in result.record.trials:
            evidence = json.loads(sub.get_blob(trial.execution_evidence))
            assert evidence["receipt"]["exit_status"] == 0
            recipe = evidence["recipe"]
            dispatch = floor.dispatch_for(sub, recipe)
            assert "nonce" not in dispatch["stdin_document"]
            assert dispatch["source_hash"] == plan.executor_identity
        first_derivation = justify.derive_tag(sub, statement.hash, None)
        before = claims.get_claim_statement(sub, statement.hash)
        history = sub.conn.execute("SELECT * FROM tag_history WHERE statement_hash = ?", (statement.hash,)).fetchall()
        floor_hash = floor.record_result(sub, protocol, result)
        observation = floor._read(sub, floor_hash, floor.RESULT_KIND)
        assert floor.rational(observation["E"]) == Fraction(64)
        assert observation["resource_observation_pass"] is True
        reproduction_hash = floor.reproduce(
            sub, protocol, plan, result, floor_hash, scratch_root=tmp_path / "replay", attest_path=None
        )
        reproduction = floor._read(sub, reproduction_hash, floor.REPRO_KIND)
        assert reproduction["passed"] is True
        assert reproduction["independent_sample"] is False
        assert len(reproduction["repro_records"]) == 6
        assert len(set(reproduction["rerun_attempts"])) == 6
        assert set(reproduction["rerun_attempts"]).isdisjoint(trial.attempt_id for trial in result.record.trials)
        assert claims.get_evidence_node(sub, floor_hash) is None
        assert claims.get_evidence_node(sub, reproduction_hash) is None
        second_derivation = justify.derive_tag(sub, statement.hash, None)
        assert claims.get_claim_statement(sub, statement.hash) == before
        assert (
            sub.conn.execute("SELECT * FROM tag_history WHERE statement_hash = ?", (statement.hash,)).fetchall()
            == history
        )
        assert second_derivation.justified_by == first_derivation.justified_by
        with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
            claims.write_evidence_node(
                sub,
                claims.EvidenceNode(
                    floor.RESULT_KIND, statement.hash, json.loads(before["scope"]), frozenset(), "floor", "gate"
                ),
            )
    finally:
        sub.close()


def test_real_verified_counterexample_sets_zero_and_reproduces(tmp_path):
    sub, plan, protocol, adapter, _ = _setup(tmp_path, control="endpoint")
    try:
        result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        assert result.verdict == "KILLED"
        assert result.record.trials[0].verifier_attempt_id is not None
        floor_hash = floor.record_result(sub, protocol, result)
        observation = floor._read(sub, floor_hash, floor.RESULT_KIND)
        assert floor.rational(observation["E"]) == 0
        assert observation["resource_observation_pass"] is False
        reproduction = floor._read(
            sub,
            floor.reproduce(
                sub, protocol, plan, result, floor_hash, scratch_root=tmp_path / "replay", attest_path=None
            ),
            floor.REPRO_KIND,
        )
        assert len(reproduction["repro_records"]) == 2
    finally:
        sub.close()


@pytest.mark.parametrize("mode", ["fail", "unverified"])
def test_incomplete_is_not_clean(tmp_path, mode):
    sub, plan, protocol, adapter, _ = _setup(tmp_path, mode=mode)
    try:
        result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        assert result.verdict == "INCOMPLETE"
        observation_hash = floor.record_result(sub, protocol, result)
        observation = floor._read(sub, observation_hash, floor.RESULT_KIND)
        assert observation["transcript"][0]["X"] is None
        assert observation["resource_observation_pass"] is False
        with pytest.raises(floor.FloorRefused, match="only completed"):
            floor.reproduce(
                sub, protocol, plan, result, observation_hash, scratch_root=tmp_path / "replay", attest_path=None
            )
    finally:
        sub.close()


def test_changed_distribution_and_late_or_mutated_protocol_refused(tmp_path):
    sub, plan, protocol, adapter, statement = _setup(tmp_path)
    try:
        mutated = dataclasses.replace(protocol)
        object.__setattr__(mutated, "epsilon", Fraction(1, 3))
        with pytest.raises(floor.FloorRefused, match="mutation"):
            hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=mutated)
        assert instances.nonces_for(sub, plan.hypothesis_key) == []
        result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        original_registration_hash, _ = floor.registration_for(sub, result)
        changed_distribution = hunt.Distribution({"n": (0, 1)})
        changed_hypothesis = claims.HypothesisObject(
            "floor-fixture",
            {"control": "clean"},
            dict(plan.method_identity),
            {"n": [0, 1]},
            changed_distribution.hash,
            statement.hash,
        )
        claims.write_hypothesis_object(sub, changed_hypothesis)
        assert changed_hypothesis.hash != plan.hypothesis_key
        changed_plan = dataclasses.replace(
            plan, hypothesis_key=changed_hypothesis.hash, distribution=changed_distribution, family_bounds={"n": (0, 1)}
        )
        changed_protocol = dataclasses.replace(
            protocol,
            plan_hash=changed_plan.hash,
            hypothesis_hash=changed_hypothesis.hash,
            distribution_hash=changed_distribution.hash,
        )
        assert changed_protocol.hash != protocol.hash
        floor.register_protocol(sub, changed_protocol, changed_plan)
        changed_commitment, _ = ladder.commit_entropy(
            sub, hypothesis_hash=changed_plan.hypothesis_key, run_id="changed-distribution-registration"
        )
        changed_registration_hash = floor.register_run(sub, changed_protocol, changed_plan, changed_commitment)
        assert changed_registration_hash != original_registration_hash
        changed_registration = floor._read(sub, changed_registration_hash, floor.RUN_KIND)
        assert changed_registration["hypothesis_hash"] == changed_hypothesis.hash
        assert changed_registration["distribution_hash"] == changed_distribution.hash
        with pytest.raises(floor.FloorRefused, match="does not bind"):
            hunt.run_hunt(sub, changed_plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
        late_hash = floor._write(sub, floor.STUDY_KIND, {"decision_rule": "late integration only"})
        late = dataclasses.replace(protocol, study_hash=late_hash)
        with pytest.raises(floor.FloorRefused, match="precede"):
            floor.register_protocol(sub, late, plan)
        floor._write(sub, floor.PROTOCOL_KIND, late.value())
        with pytest.raises(floor.FloorRefused, match="precede every entropy"):
            hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=late)
        assert keys.node_hash("hunt_run", hunt.run_canonical(result.record)) == result.run_hash
    finally:
        sub.close()


def test_frozen_control_rates_are_exact_without_sampling():
    registration = json.loads(ADAPTER_PATH.with_name("preregistration.json").read_text())
    for case in registration["false_controls"]:
        rows = EXPERIMENT.finite_control_rows(case)
        assert Fraction(sum(row["counterexample"] for row in rows), len(rows)) == floor.rational(case["epsilon"])
        if case["name"] == "R4-euler":
            assert [row["n"] for row in rows if row["counterexample"]] == [40]


def test_study_refuses_uncommitted_or_invalid_source():
    with pytest.raises(floor.FloorRefused, match="full committed source"):
        EXPERIMENT.verify_committed_source("HEAD")


@pytest.mark.parametrize(
    "relative",
    [
        "src/cairn/ladder.py",
        "src/cairn/instances.py",
        "src/cairn/runner.py",
        "src/cairn/repro.py",
        "src/cairn/gp/verify.gp",
        "pyproject.toml",
        "uv.lock",
    ],
)
def test_committed_runtime_guard_accepts_same_bytes_and_refuses_changed_dependency(committed_floor_source, relative):
    root, revision = committed_floor_source
    assert _source_guard(root, revision) == {"refused": False, "revision": revision}
    (root / relative).write_text("different fixture payload\n")
    refusal = _source_guard(root, revision)
    assert refusal["refused"] is True
    assert refusal["error"] == f"source differs from committed revision: {relative}"


@pytest.mark.parametrize("relative", ["src/cairn/extra.py", "src/cairn/untracked.json"])
def test_committed_runtime_guard_refuses_untracked_sources_and_resources(committed_floor_source, relative):
    root, revision = committed_floor_source
    assert _source_guard(root, revision) == {"refused": False, "revision": revision}
    (root / relative).write_text("untracked fixture payload\n")
    refusal = _source_guard(root, revision)
    assert refusal["refused"] is True
    assert "untracked runtime source or resource" in refusal["error"]
    assert relative in refusal["error"]


def test_runtime_metadata_records_interpreter_and_installed_packages():
    metadata = EXPERIMENT.runtime_metadata()
    assert metadata["python"] == sys.version
    assert metadata["implementation"] == sys.implementation.name
    assert metadata["executable"] == str(Path(sys.executable).resolve())
    assert len(metadata["executable_blob_hash"]) == 64
    assert set(metadata["packages"]) == {"cairn", "blake3", "cypari2", "cysignals"}
    assert all(metadata["packages"].values())


def test_completed_decision_links_real_hunt_results_and_reproductions(tmp_path, committed_floor_source):
    _, revision = committed_floor_source
    false_case = {
        "name": "endpoint-fixture",
        "statement": "2 does not divide n+1",
        "D": {"kind": "uniform_integer", "ranges": {"n": [0, 1]}},
        "epsilon": "1/2",
        "budget": 1,
    }
    positive_case = {
        "name": "clean-fixture",
        "statement": "n is at most zero",
        "D": {"kind": "uniform_integer", "ranges": {"n": [0, 0]}},
        "epsilon": "1/2",
        "budget": 6,
    }
    study = {
        "alpha": "1/20",
        "decision_rule": "ADOPT iff any completed SURVIVED false control has E<20; otherwise DROP",
        "false_controls": [false_case],
        "positive_control": positive_case,
    }
    with substrate.Substrate.open(tmp_path / "decision.sqlite") as sub:
        study_hash = floor._write(sub, floor.STUDY_KIND, study)
        runtime_hash = floor._write(sub, "small_numbers_floor_runtime", {"source_sha": revision, "runtime": {}})
        summary = {"source_sha": revision, "study_hash": study_hash, "runtime_hash": runtime_hash, "runs": []}
        for case in (false_case, positive_case):
            statement, plan, protocol, adapter = EXPERIMENT.prepare_case(sub, case, study_hash, tmp_path / "runs")
            result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
            floor_hash = floor.record_result(sub, protocol, result)
            reproduction_hash = floor.reproduce(
                sub, protocol, plan, result, floor_hash, scratch_root=tmp_path / "replay", attest_path=None
            )
            for trial in result.record.trials:
                attempt = sub.get_attempt(trial.attempt_id)
                assert sub.get_receipt(attempt["receipt_hash"])["exit_status"] == 0
            summary["runs"].append(
                {
                    "name": case["name"],
                    "status": "COMPLETED",
                    "protocol_hash": protocol.hash,
                    "floor_hash": floor_hash,
                    "reproduction_hash": reproduction_hash,
                }
            )
        false_result = floor._read(sub, summary["runs"][0]["floor_hash"], floor.RESULT_KIND)
        summary["decision"] = "ADOPT" if false_result["verdict"] == "SURVIVED" else "DROP"
        decision_hash = EXPERIMENT.record_decision(sub, summary)
        decision = floor._read(sub, decision_hash, "small_numbers_floor_decision")
        assert EXPERIMENT.record_decision(sub, summary) == decision_hash
        assert decision["decision"] == summary["decision"]
        assert decision["source_sha"] == revision
        assert decision["study_hash"] == study_hash
        assert decision["criterion"] == study["decision_rule"]
        assert decision["alpha"] == "1/20"
        assert decision["enforced"] is False
        assert len(decision["registered_cases"]) == 2
        assert claims.get_evidence_node(sub, decision_hash) is None
        parents = {
            row["parent_hash"]
            for row in sub.conn.execute(
                "SELECT parent_hash FROM lineage WHERE child_hash = ? AND edge_kind = ?",
                (decision_hash, substrate.EDGE_INPUT),
            )
        }
        assert {study_hash, runtime_hash} <= parents
        for registered, entry in zip(decision["registered_cases"], summary["runs"], strict=True):
            assert registered["epsilon"] == "1/2"
            assert registered["alpha"] == "1/20"
            for name in ("protocol_hash", "floor_hash", "reproduction_hash"):
                assert registered[name] == entry[name]
                assert registered[name] in parents
            assert registered["distribution_hash"] in parents
        summary["runs"][0]["status"] = "FAILED"
        before = sub.conn.execute("SELECT COUNT(*) FROM nodes WHERE kind = 'small_numbers_floor_decision'").fetchone()[
            0
        ]
        with pytest.raises(floor.FloorRefused, match="incomplete runs"):
            EXPERIMENT.record_decision(sub, summary)
        summary["runs"][0]["status"] = "COMPLETED"
        summary["decision"] = "INCOMPLETE"
        with pytest.raises(floor.FloorRefused, match="only completed"):
            EXPERIMENT.record_decision(sub, summary)
        summary["decision"] = decision["decision"]
        incomplete = hunt.run_hunt(
            sub, plan, dataclasses.replace(adapter, mode="fail").executor, adapter.verifier, floor_protocol=protocol
        )
        assert incomplete.verdict == "INCOMPLETE"
        summary["runs"][-1]["floor_hash"] = floor.record_result(sub, protocol, incomplete)
        with pytest.raises(floor.FloorRefused, match="registered complete results"):
            EXPERIMENT.record_decision(sub, summary)
        assert (
            sub.conn.execute("SELECT COUNT(*) FROM nodes WHERE kind = 'small_numbers_floor_decision'").fetchone()[0]
            == before
        )
