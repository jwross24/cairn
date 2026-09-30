import argparse
import importlib.metadata
import json
import math
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from cairn import canon, claims, hunt, justify, substrate
from cairn import small_numbers_floor as floor
from cairn.substrate import EDGE_INPUT, blob_hash


@dataclass(frozen=True)
class FixtureAdapter:
    sub: substrate.Substrate
    scratch_root: Path
    control: str
    endpoint: int = 1000
    mode: str = "normal"

    @staticmethod
    def worker(verifier=False):
        return (
            Path(__file__).resolve().parents[3]
            / "tests"
            / "fixtures"
            / ("small_numbers_floor_verifier.py" if verifier else "small_numbers_floor_executor.py")
        )

    @classmethod
    def identity(cls, verifier=False):
        return blob_hash(cls.worker(verifier).read_bytes())

    def _launch(self, context, execution=None):
        is_verifier = execution is not None
        worker = self.worker(is_verifier)
        identity = self.identity(is_verifier)
        document = {
            "statement_hash": context.plan.statement_hash,
            "plan_hash": context.plan.hash,
            "run_id": context.run_id,
            "trial": context.trial,
            "point": dict(context.point),
            "seed": context.seed,
            "input_blob_hash": context.input_blob_hash,
            "control": self.control,
            "endpoint": self.endpoint,
            "mode": self.mode,
        }
        inputs = {"hunt_input": (context.input_blob_hash, context.input_blob_size)}
        if is_verifier:
            document["executor_output_digest"] = execution.output_json_hash
            inputs["executor_output"] = (execution.output_json_hash, len(self.sub.get_blob(execution.output_json_hash)))
        source_hash = self.sub.put_blob(worker.read_bytes())
        dispatch = {
            "module": worker.stem,
            "source_hash": source_hash,
            "source_path": str(worker),
            "bundle_hash": "b" * 64,
            "evaluation": ["0.05", "0.05", "0.05"],
            "ceiling_multiplier": "4",
            "wall_cap_multiplier": "4",
            "wall_cap_floor_s": "120",
            "subprocess_startup_ms": 77,
            "replay": "Replayable",
            "budget_remaining": None,
            "env_extra": {"PYTHONPATH": str(worker.parent)},
            "stdin_document": document,
            "tool_digests": {"worker_source": identity},
        }
        dispatch_hash = floor._write(self.sub, floor.DISPATCH_KIND, dispatch, (source_hash,))
        dispatch_data = floor._bytes(dispatch)
        dispatch_blob = self.sub.put_blob(dispatch_data)
        self.sub.add_lineage(dispatch_hash, dispatch_blob, EDGE_INPUT)
        inputs["floor_dispatch"] = (dispatch_blob, len(dispatch_data))
        recipe = {
            "skill_identity_hash": identity,
            "inputs": inputs,
            "seed": context.seed,
            "tool_versions": dispatch["tool_digests"],
            "container_digest": "c" * 64,
            "salt": f"floor/{context.run_id}/{context.trial}/{worker.stem}",
        }
        attempt = floor.launch_dispatch(self.sub, recipe, dispatch, self.scratch_root)
        self.sub.add_lineage(attempt.recipe_key, dispatch_hash, EDGE_INPUT)
        return attempt

    def executor(self, context):
        return self._launch(context)

    def verifier(self, context, execution):
        return self._launch(context, execution)


def verify_committed_source(source_sha):
    return _verify_committed_source(Path(__file__).resolve().parents[3], source_sha)


def _verify_committed_source(root, source_sha):
    root = Path(root)
    git = shutil.which("git")
    if git is None or len(source_sha) != 40 or any(character not in "0123456789abcdef" for character in source_sha):
        raise floor.FloorRefused("full committed source SHA and git executable required")
    required = {
        "pyproject.toml",
        "uv.lock",
        "tests/fixtures/small_numbers_floor_executor.py",
        "tests/fixtures/small_numbers_floor_verifier.py",
        "research/grounding/small-numbers-floor-2026-09-30/run_experiment.py",
        "research/grounding/small-numbers-floor-2026-09-30/preregistration.json",
    }
    revision = subprocess.run(
        [git, "rev-parse", "--verify", f"{source_sha}^{{commit}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    runtime_paths = set(
        subprocess.run(
            [git, "ls-tree", "-r", "-z", "--name-only", revision, "--", "src/cairn"],
            cwd=root,
            check=True,
            capture_output=True,
        )
        .stdout.decode()
        .rstrip("\0")
        .split("\0")
    )
    if not runtime_paths or "" in runtime_paths:
        raise floor.FloorRefused("committed runtime source tree is missing")
    present_runtime = {
        path.relative_to(root).as_posix()
        for path in (root / "src/cairn").rglob("*")
        if path.is_file() and not ("__pycache__" in path.parts and path.suffix == ".pyc")
    }
    unknown = present_runtime - runtime_paths
    if unknown:
        raise floor.FloorRefused(f"untracked runtime source or resource: {sorted(unknown)}")
    for path in sorted(runtime_paths | required):
        committed = subprocess.run(
            [git, "show", f"{revision}:{path}"], cwd=root, check=True, capture_output=True
        ).stdout
        if not (root / path).is_file():
            raise floor.FloorRefused(f"committed source missing from disk: {path}")
        if committed != (root / path).read_bytes():
            raise floor.FloorRefused(f"source differs from committed revision: {path}")
    return revision


def runtime_metadata():
    executable = Path(sys.executable).resolve()
    return {
        "python": sys.version,
        "implementation": sys.implementation.name,
        "executable": str(executable),
        "executable_blob_hash": blob_hash(executable.read_bytes()),
        "packages": {name: importlib.metadata.version(name) for name in ("cairn", "blake3", "cypari2", "cysignals")},
    }


def finite_control_rows(case):
    low, high = case["D"]["ranges"]["n"]
    if case["name"] == "R4-euler":
        rows = []
        for n in range(low, high + 1):
            value = n * n + n + 41
            divisors = [divisor for divisor in range(2, math.isqrt(value) + 1) if value % divisor == 0]
            rows.append({"n": n, "value": value, "counterexample": bool(divisors), "divisors": divisors})
        return rows
    endpoint = high + 1
    return [{"n": n, "counterexample": (n + 1) % endpoint == 0} for n in range(low, high + 1)]


def prepare_case(sub, case, study_hash, scratch_root):
    bounds = tuple(case["D"]["ranges"]["n"])
    control = "euler" if case["name"] == "R4-euler" else ("clean" if case["name"].startswith("clean-") else "endpoint")
    adapter = FixtureAdapter(sub, scratch_root, control, endpoint=bounds[1] + 1)
    family = f"floor-study/{case['name']}"
    scope = {
        "target_family": family,
        "size_interval": list(bounds),
        "param_ranges": {"n": list(bounds)},
        "assumption_set": [],
    }
    statement = claims.ClaimStatement(case["name"], 1, case["statement"], scope, {"units": {}, "cost_model": None})
    claims.write_claim_statement(sub, statement)
    distribution = hunt.Distribution({"n": bounds})
    method = {"interface_version": "floor_fixture/1", "params": {"control": control, "endpoint": str(bounds[1] + 1)}}
    hypothesis = claims.HypothesisObject(
        family, {"control": control}, method, {"n": list(bounds)}, distribution.hash, statement.hash
    )
    claims.write_hypothesis_object(sub, hypothesis)
    plan = hunt.HuntPlan(
        statement.hash,
        hypothesis.hash,
        distribution,
        case["budget"],
        {"n": bounds},
        method_identity=method,
        target_family=family,
        executor_identity=adapter.identity(),
        verifier_identity=adapter.identity(True),
    )
    protocol = floor.Protocol(
        plan.hash, hypothesis.hash, distribution.hash, case["epsilon"], "1/20", case["budget"], study_hash
    )
    floor.register_protocol(sub, protocol, plan)
    return statement, plan, protocol, adapter


def record_decision(sub, summary):
    if summary["decision"] not in ("ADOPT", "DROP") or not summary["runs"]:
        raise floor.FloorRefused("only completed ADOPT or DROP comparisons have a decision record")
    if any(entry["status"] != "COMPLETED" for entry in summary["runs"]):
        raise floor.FloorRefused("incomplete runs cannot mint a completed decision")
    study = floor._read(sub, summary["study_hash"], floor.STUDY_KIND)
    runtime = floor._read(sub, summary["runtime_hash"], "small_numbers_floor_runtime")
    if runtime["source_sha"] != summary["source_sha"]:
        raise floor.FloorRefused("decision source differs from registered runtime")
    cases = [*study["false_controls"], study["positive_control"]]
    if [case["name"] for case in cases] != [entry["name"] for entry in summary["runs"]]:
        raise floor.FloorRefused("decision must include every registered case in order")
    registered = []
    parents = [summary["study_hash"], summary["runtime_hash"]]
    binding = []
    for index, (case, entry) in enumerate(zip(cases, summary["runs"], strict=True)):
        protocol = floor._read(sub, entry["protocol_hash"], floor.PROTOCOL_KIND)
        result = floor._read(sub, entry["floor_hash"], floor.RESULT_KIND)
        reproduction = floor._read(sub, entry["reproduction_hash"], floor.REPRO_KIND)
        distribution = sub.get_node(protocol["distribution_hash"])
        if distribution is None or distribution["kind"] != "hunt_distribution":
            raise floor.FloorRefused("decision distribution is missing")
        if canon.decode(hunt.DISTRIBUTION, distribution["canonical"]) != case["D"]:
            raise floor.FloorRefused("decision distribution differs from registered case")
        if (
            protocol["study_hash"] != summary["study_hash"]
            or floor.rational(protocol["epsilon"]) != floor.rational(case["epsilon"])
            or floor.rational(protocol["alpha"]) != floor.rational(study["alpha"])
            or protocol["budget"] != case["budget"]
            or result["protocol_hash"] != entry["protocol_hash"]
            or result["verdict"] not in ("SURVIVED", "KILLED")
            or reproduction["floor_hash"] != entry["floor_hash"]
            or reproduction["hunt_hash"] != result["hunt_hash"]
            or reproduction["passed"] is not True
        ):
            raise floor.FloorRefused("decision needs registered complete results and passed reproductions")
        if index < len(cases) - 1 and result["verdict"] == "SURVIVED" and not result["resource_observation_pass"]:
            binding.append(case["name"])
        registered.append(
            {
                "name": case["name"],
                "epsilon": protocol["epsilon"],
                "alpha": protocol["alpha"],
                "distribution_hash": protocol["distribution_hash"],
                "hypothesis_hash": protocol["hypothesis_hash"],
                "protocol_hash": entry["protocol_hash"],
                "floor_hash": entry["floor_hash"],
                "reproduction_hash": entry["reproduction_hash"],
                "hunt_hash": result["hunt_hash"],
            }
        )
        parents.extend(
            (entry["protocol_hash"], entry["floor_hash"], entry["reproduction_hash"], protocol["distribution_hash"])
        )
    if summary["decision"] != ("ADOPT" if binding else "DROP"):
        raise floor.FloorRefused("decision differs from registered result comparison")
    return floor._write(
        sub,
        "small_numbers_floor_decision",
        {
            "decision": summary["decision"],
            "source_sha": summary["source_sha"],
            "study_hash": summary["study_hash"],
            "runtime_hash": summary["runtime_hash"],
            "criterion": study["decision_rule"],
            "alpha": study["alpha"],
            "registered_cases": registered,
            "binding_false_survivors": binding,
            "enforced": False,
            "scope": "registered resource comparison; no tag, reward, promotion, or mathematical proof",
        },
        parents,
    )


def run_study(source_sha, output):
    source_sha = verify_committed_source(source_sha)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    scratch_root = Path(tempfile.mkdtemp(prefix="cairn-floor-study-"))
    preregistration_path = Path(__file__).with_name("preregistration.json")
    preregistration_bytes = preregistration_path.read_bytes()
    preregistration = json.loads(preregistration_bytes)
    if preregistration["version"] != 2 or preregistration["replicates"] != 1:
        raise floor.FloorRefused("unsupported committed study version or replicate count")
    summary = {
        "source_sha": source_sha,
        "runtime": runtime_metadata(),
        "preregistration_blob_hash": blob_hash(preregistration_bytes),
        "preregistration": preregistration,
        "scratch_root": str(scratch_root),
        "runs": [],
        "decision": "INCOMPLETE",
        "skips": [],
    }
    with substrate.Substrate.open(output / "substrate.sqlite") as sub:
        study_hash = floor._write(sub, floor.STUDY_KIND, preregistration)
        summary["study_hash"] = study_hash
        runtime_hash = floor._write(
            sub, "small_numbers_floor_runtime", {"source_sha": source_sha, "runtime": summary["runtime"]}
        )
        summary["runtime_hash"] = runtime_hash
        sub.add_lineage(study_hash, runtime_hash, EDGE_INPUT)
        for case in [*preregistration["false_controls"], preregistration["positive_control"]]:
            entry = {"name": case["name"], "case": case, "status": "STARTED"}
            summary["runs"].append(entry)
            try:
                if case in preregistration["false_controls"]:
                    rows = finite_control_rows(case)
                    observed_rate = Fraction(sum(row["counterexample"] for row in rows), len(rows))
                    if observed_rate != floor.rational(case["epsilon"]):
                        raise floor.FloorRefused("declared control epsilon differs from exact finite enumeration")
                    entry["finite_enumeration"] = rows
                    entry["exact_failure_rate"] = str(observed_rate)
                statement, plan, protocol, adapter = prepare_case(sub, case, study_hash, scratch_root)
                entry.update(
                    statement_hash=statement.hash,
                    hypothesis_hash=plan.hypothesis_key,
                    plan_hash=plan.hash,
                    protocol_hash=protocol.hash,
                )
                result = hunt.run_hunt(sub, plan, adapter.executor, adapter.verifier, floor_protocol=protocol)
                before = justify.derive_tag(sub, statement.hash, None)
                history = claims.tag_history_for(sub, statement.hash)
                floor_hash = floor.record_result(sub, protocol, result)
                registration_hash, registration = floor.registration_for(sub, result)
                entry.update(
                    hunt_hash=result.run_hash,
                    hunt_evidence_hash=result.evidence_hash,
                    floor_hash=floor_hash,
                    registration_hash=registration_hash,
                    commitment_hash=registration["commitment_hash"],
                    nonce=result.record.nonce,
                    seeds=[
                        hunt.hunt_trial_seed(result.record.nonce, plan.hypothesis_key, index)
                        for index in range(plan.trial_count)
                    ],
                    declared_count=plan.trial_count,
                    completed_count=result.record.completed_trial_count,
                    verdict=result.verdict,
                    floor=floor._read(sub, floor_hash, floor.RESULT_KIND),
                )
                if result.verdict == "INCOMPLETE":
                    raise floor.FloorRefused("real hunt incomplete; no clean statistical outcome")
                reproduction_hash = floor.reproduce(
                    sub, protocol, plan, result, floor_hash, scratch_root=scratch_root, attest_path=None
                )
                after = justify.derive_tag(sub, statement.hash, None)
                invariant = before.tag == after.tag and before.justified_by == after.justified_by
                invariant = invariant and history == claims.tag_history_for(sub, statement.hash)
                if not invariant:
                    raise floor.FloorRefused("floor changed tag, tag history, or justified_by")
                entry.update(
                    status="COMPLETED",
                    reproduction_hash=reproduction_hash,
                    reproduction=floor._read(sub, reproduction_hash, floor.REPRO_KIND),
                    tag=after.tag,
                    justified_by=after.justified_by,
                    tag_invariance=True,
                )
            except Exception as exc:
                entry.update(status="FAILED", error_type=type(exc).__name__, error=str(exc))
            (output / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
        if all(entry["status"] == "COMPLETED" for entry in summary["runs"]):
            binding = [
                entry["name"]
                for entry in summary["runs"][:-1]
                if entry["verdict"] == "SURVIVED" and not entry["floor"]["resource_observation_pass"]
            ]
            summary["binding_false_survivors"] = binding
            summary["decision"] = "ADOPT" if binding else "DROP"
            summary["adoption_wiring_required"] = bool(binding)
            summary["decision_hash"] = record_decision(sub, summary)
        (output / "summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = run_study(args.source_sha, args.output)
    print(
        json.dumps(
            {
                "decision": summary["decision"],
                "runs": [
                    {
                        name: entry.get(name)
                        for name in ("name", "status", "verdict", "completed_count", "floor_hash", "reproduction_hash")
                    }
                    for entry in summary["runs"]
                ],
            },
            sort_keys=True,
        )
    )
    return 1 if summary["decision"] == "INCOMPLETE" else 0


if __name__ == "__main__":
    raise SystemExit(main())
