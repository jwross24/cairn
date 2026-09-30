import argparse
import gzip
import hashlib
import json
import math
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from cairn import bundle, canon, claims, hunt, keys, ladder, substrate
from cairn import small_numbers_floor as floor

ROOT = Path(__file__).resolve().parents[3]


class AuditRefused(ValueError):
    pass


def require(condition, detail):
    if not condition:
        raise AuditRefused(detail)


def file_identity(path):
    digest = hashlib.sha256()
    size = 0
    with Path(path).open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            size += len(block)
    return {"sha256": digest.hexdigest(), "bytes": size}


def committed_bytes(source_sha, path):
    require(
        len(source_sha) == 40 and all(character in "0123456789abcdef" for character in source_sha), "invalid source SHA"
    )
    git = shutil.which("git")
    if git is None:
        raise AuditRefused("git executable is missing")
    return subprocess.run([git, "show", f"{source_sha}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


class Archive:
    def __init__(self, path):
        self.conn = sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro&immutable=1", uri=True)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA query_only=ON")

    def get_node(self, digest):
        row = self.conn.execute("SELECT * FROM nodes WHERE hash = ?", (digest,)).fetchone()
        return None if row is None else dict(row)

    def get_blob(self, digest):
        row = self.conn.execute("SELECT bytes FROM blobs WHERE hash = ?", (digest,)).fetchone()
        return None if row is None else bytes(row[0])

    def row(self, table, column, value):
        queries = {
            "attempts": "SELECT * FROM attempts WHERE attempt_id = ?",
            "recipes": "SELECT * FROM recipes WHERE recipe_key = ?",
            "receipts": "SELECT * FROM receipts WHERE receipt_hash = ?",
            "repro_records": "SELECT * FROM repro_records WHERE hash = ?",
        }
        require(column in ("attempt_id", "recipe_key", "receipt_hash", "hash"), "invalid archive lookup")
        row = self.conn.execute(queries[table], (value,)).fetchone()
        require(row is not None, f"missing {table} row {value}")
        return dict(row)

    def node(self, digest, kind, schema=None):
        row = self.get_node(digest)
        require(row is not None and row["kind"] == kind, f"missing {kind} node {digest}")
        require(substrate.node_hash_for(kind, row["canonical"]) == digest, f"node hash differs: {digest}")
        return bundle._decode(row["canonical"]) if schema is None else canon.decode(schema, row["canonical"])

    def blob(self, digest, size=None):
        value = self.get_blob(digest)
        require(value is not None and substrate.blob_hash(value) == digest, f"blob hash differs: {digest}")
        require(size is None or size == len(value), f"blob size differs: {digest}")
        return value

    def position(self, digest):
        row = self.conn.execute("SELECT rowid FROM nodes WHERE hash = ?", (digest,)).fetchone()
        require(row is not None, f"missing node position: {digest}")
        return row[0]

    def linked(self, child, parent):
        require(
            self.conn.execute(
                "SELECT 1 FROM lineage WHERE child_hash = ? AND parent_hash = ? AND edge_kind = ?",
                (child, parent, substrate.EDGE_INPUT),
            ).fetchone()
            is not None,
            f"missing lineage {child} -> {parent}",
        )

    def check_content(self):
        require(self.conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity check refused")
        nodes = blobs = 0
        for row in self.conn.execute("SELECT hash, kind, canonical FROM nodes"):
            require(substrate.node_hash_for(row["kind"], row["canonical"]) == row["hash"], "archive node hash differs")
            nodes += 1
        for row in self.conn.execute("SELECT hash, size, bytes FROM blobs"):
            require(
                substrate.blob_hash(row["bytes"]) == row["hash"] and len(row["bytes"]) == row["size"],
                "archive blob differs",
            )
            blobs += 1
        return nodes, blobs


def attempt_output(archive, attempt_id, context, identity, source_bytes, executor_digest=None):
    attempt = archive.row("attempts", "attempt_id", attempt_id)
    require(
        attempt["status"] == "OK"
        and attempt["ended_at"] is not None
        and attempt["skip_cache_lookup"] == 1
        and attempt["disowned_at"] is None
        and attempt["inadmissible"] == 0,
        f"attempt is not a successful fresh admissible execution: {attempt_id}",
    )
    recipe = archive.node(attempt["recipe_key"], "recipe", keys.RECIPE)
    stored_recipe = archive.row("recipes", "recipe_key", attempt["recipe_key"])
    require(stored_recipe["do_not_cache"] == 1, "recipe is cacheable")
    require(
        recipe["skill_identity_hash"] == identity and recipe["seed"] == context.seed, "recipe identity or seed differs"
    )
    require(
        recipe["inputs"]["hunt_input"] == (context.input_blob_hash, context.input_blob_size),
        "recipe trial input differs",
    )
    for digest, size in recipe["inputs"].values():
        archive.blob(digest, size)
    dispatch = floor.dispatch_for(archive, recipe)
    require(
        dispatch["source_hash"] == substrate.blob_hash(source_bytes), "dispatch source differs from committed worker"
    )
    require(
        archive.blob(dispatch["source_hash"]) == source_bytes and identity == dispatch["source_hash"],
        "worker source blob differs",
    )
    require("nonce" not in dispatch["stdin_document"], "child document exposes gate nonce")
    require(dispatch["stdin_document"]["mode"] == "normal", "study dispatch changes failure mode")
    manifest = archive.node(attempt["output_manifest_hash"], "output_manifest", substrate.OUTPUT_MANIFEST)
    output_digest, output_size = manifest["artifacts"]["output.json"]
    output_bytes = archive.blob(output_digest, output_size)
    output = json.loads(output_bytes)
    hunt._validate_binding(output, context, candidate=executor_digest is None, executor_output_hash=executor_digest)
    if executor_digest is not None:
        require(recipe["inputs"]["executor_output"][0] == executor_digest, "verifier recipe output binding differs")
        require(output["counterexample_valid"] is True, "counterexample verifier did not pass")
    receipt = archive.row("receipts", "receipt_hash", attempt["receipt_hash"])
    require(substrate.receipt_hash(receipt) == attempt["receipt_hash"], "receipt companion hash differs")
    require(
        archive.get_node(attempt["receipt_hash"])["canonical"] == substrate.receipt_canonical(receipt),
        "receipt node differs from companion",
    )
    require(
        receipt["exit_status"] == 0 and receipt["stdout_digest"] == output_digest,
        "receipt does not bind successful output",
    )
    archive.blob(receipt["stderr_digest"])
    require(receipt["gate_bundle_hash"] == dispatch["bundle_hash"], "dispatch bundle differs from receipt")
    require(
        receipt["tool_digests_hash"]
        == keys.node_hash("tool_digests", canon.encode(canon.Map(canon.STR, canon.STR), dispatch["tool_digests"])),
        "dispatch tool digests differ from receipt",
    )
    return attempt, output, output_digest


def expected_failure(case, n):
    if case["name"] == "R4-euler":
        value = n * n + n + 41
        return any(value % divisor == 0 for divisor in range(2, math.isqrt(value) + 1))
    if case["name"] == "clean-1000":
        return n > 999
    return (n + 1) % case["budget"] == 0


def audit_run(archive, entry, case, study_hash, alpha, source_sha):
    require(
        entry["case"] == case and entry["name"] == case["name"] and entry["status"] == "COMPLETED",
        "summary case differs from preregistration",
    )
    protocol = archive.node(entry["protocol_hash"], floor.PROTOCOL_KIND)
    require(
        protocol["study_hash"] == study_hash and protocol["epsilon"] == case["epsilon"] and protocol["alpha"] == alpha,
        "protocol epsilon, alpha or study differs",
    )
    require(protocol["budget"] == case["budget"] == entry["declared_count"], "registered budget differs")
    distribution = archive.node(protocol["distribution_hash"], "hunt_distribution", hunt.DISTRIBUTION)
    require(distribution == case["D"], "registered D differs")
    low, high = distribution["ranges"]["n"]
    enumeration = [{"n": n, "counterexample": expected_failure(case, n)} for n in range(low, high + 1)]
    if case["name"] == "R4-euler":
        for row in enumeration:
            value = row["n"] * row["n"] + row["n"] + 41
            row.update(value=value, divisors=[d for d in range(2, math.isqrt(value) + 1) if value % d == 0])
    rate = floor.rational(sum(row["counterexample"] for row in enumeration)) / len(enumeration)
    if case["name"] != "clean-1000":
        require(entry["finite_enumeration"] == enumeration, "finite control enumeration differs")
        require(floor.rational(entry["exact_failure_rate"]) == rate, "finite failure rate differs")
    require(
        rate == (floor.probability(case["epsilon"]) if case["name"] != "clean-1000" else 0),
        "preregistered control premise differs",
    )
    plan = archive.node(entry["plan_hash"], "hunt_plan", hunt.PLAN)
    require(
        protocol["plan_hash"] == entry["plan_hash"] and protocol["hypothesis_hash"] == entry["hypothesis_hash"],
        "protocol plan differs",
    )
    require(
        plan["distribution_hash"] == protocol["distribution_hash"] and plan["trial_count"] == case["budget"],
        "plan D or budget differs",
    )
    hypothesis = archive.node(entry["hypothesis_hash"], "hypothesis_object", keys.HYPOTHESIS_OBJECT)
    require(hypothesis["sampling_distribution"] == protocol["distribution_hash"], "hypothesis D differs")
    runtime_plan = hunt.HuntPlan(
        plan["statement_hash"],
        plan["hypothesis_key"],
        hunt.Distribution({axis: tuple(bounds) for axis, bounds in distribution["ranges"].items()}),
        plan["trial_count"],
        {axis: tuple(bounds) for axis, bounds in plan["family_bounds"].items()},
        plan["size_axis"],
        plan["method_identity"],
        plan["target_family"],
        frozenset(plan["assumption_set"]),
        plan["executor_identity"],
        plan["verifier_identity"],
    )
    require(
        runtime_plan.hash == entry["plan_hash"]
        and runtime_plan.statement_hash == entry["statement_hash"]
        and runtime_plan.hypothesis_key == entry["hypothesis_hash"],
        "reconstructed hunt plan differs",
    )
    registration = archive.node(entry["registration_hash"], floor.RUN_KIND)
    commitment = archive.node(entry["commitment_hash"], ladder.COMMITMENT_KIND)
    require(
        registration["protocol_hash"] == entry["protocol_hash"]
        and registration["commitment_hash"] == entry["commitment_hash"],
        "run registration differs",
    )
    require(
        registration["plan_hash"] == entry["plan_hash"]
        and registration["hypothesis_hash"] == entry["hypothesis_hash"]
        and registration["distribution_hash"] == protocol["distribution_hash"]
        and registration["run_id"] == commitment["run_id"],
        "registration identities differ",
    )
    require(
        registration["nonce"] == commitment["nonce"] == entry["nonce"]
        and commitment["hypothesis_hash"] == entry["hypothesis_hash"],
        "entropy commitment differs",
    )
    sampler_hash = substrate.blob_hash(committed_bytes(source_sha, "src/cairn/hunt.py"))
    require(
        registration["sampler_hash"] == protocol["sampler_hash"] == sampler_hash, "committed sampler source differs"
    )
    require(
        archive.position(entry["hypothesis_hash"])
        < archive.position(entry["protocol_hash"])
        < archive.position(entry["commitment_hash"])
        < archive.position(entry["registration_hash"])
        < archive.position(entry["hunt_hash"]),
        "protocol does not precede entropy and hunt",
    )
    archive.linked(entry["protocol_hash"], study_hash)
    archive.linked(entry["registration_hash"], entry["protocol_hash"])
    archive.linked(entry["registration_hash"], entry["commitment_hash"])
    archive.linked(entry["hunt_hash"], entry["registration_hash"])
    nonce_rows = archive.conn.execute(
        "SELECT * FROM instance_nonces WHERE hypothesis_key = ?", (entry["hypothesis_hash"],)
    ).fetchall()
    require(
        len(nonce_rows) == 1 and nonce_rows[0]["nonce"] == entry["nonce"] and nonce_rows[0]["published_at"] is not None,
        "run lacks one published gate nonce",
    )
    expected_seeds = [
        hunt.hunt_trial_seed(entry["nonce"], entry["hypothesis_hash"], trial) for trial in range(case["budget"])
    ]
    require(entry["seeds"] == expected_seeds, "declared seed transcript differs, including unused seeds")
    record = hunt.record_for(archive, entry["hunt_hash"])
    require(
        record is not None
        and record.verdict == entry["verdict"]
        and record.completed_trial_count == entry["completed_count"],
        "hunt summary differs",
    )
    require(
        record.verdict in ("SURVIVED", "KILLED") and record.declared_trial_count == case["budget"],
        "hunt is incomplete or has another budget",
    )
    require(
        record.nonce == entry["nonce"]
        and record.plan_hash == entry["plan_hash"]
        and record.hypothesis_key == entry["hypothesis_hash"]
        and record.distribution_hash == protocol["distribution_hash"],
        "hunt registration binding differs",
    )
    result = archive.node(entry["floor_hash"], floor.RESULT_KIND)
    require(result == entry["floor"] and result["hunt_hash"] == entry["hunt_hash"], "floor summary differs")
    epsilon = floor.probability(protocol["epsilon"])
    wealth = floor.rational(1)
    transcript = []
    originals = []
    worker_sources = [
        committed_bytes(source_sha, f"tests/fixtures/small_numbers_floor_{name}.py")
        for name in ("executor", "verifier")
    ]
    for trial in record.trials:
        require(trial.seed == expected_seeds[trial.trial], "executed trial seed differs")
        require(
            all(low <= trial.point[axis] <= high for axis, (low, high) in distribution["ranges"].items()),
            "point lies outside D",
        )
        original = archive.row("attempts", "attempt_id", trial.attempt_id)
        recipe = archive.node(original["recipe_key"], "recipe", keys.RECIPE)
        input_digest, input_size = recipe["inputs"]["hunt_input"]
        input_document = json.loads(archive.blob(input_digest, input_size))
        input_row = archive.conn.execute("SELECT created_at FROM blobs WHERE hash = ?", (input_digest,)).fetchone()
        input_created = input_row[0]
        require(
            input_created >= archive.get_node(entry["registration_hash"])["created_at"],
            "trial input precedes run registration",
        )
        context = hunt.TrialContext(
            runtime_plan, registration["run_id"], trial.trial, trial.point, trial.seed, input_digest, input_size
        )
        require(
            input_document
            == {
                "statement_hash": entry["statement_hash"],
                "plan_hash": entry["plan_hash"],
                "run_id": registration["run_id"],
                "trial": trial.trial,
                "point": dict(trial.point),
                "seed": trial.seed,
            },
            "input document differs",
        )
        execution, output, output_digest = attempt_output(
            archive, trial.attempt_id, context, plan["executor_identity"], worker_sources[0]
        )
        require(output["candidate"] == (trial.outcome == "COUNTEREXAMPLE"), "executor outcome differs")
        require(
            output["candidate"] is expected_failure(case, trial.point["n"]),
            "fixture outcome differs from finite control",
        )
        originals.append((execution, context, plan["executor_identity"], worker_sources[0], None))
        if trial.verifier_attempt_id is not None:
            verification, _, _ = attempt_output(
                archive, trial.verifier_attempt_id, context, plan["verifier_identity"], worker_sources[1], output_digest
            )
            originals.append((verification, context, plan["verifier_identity"], worker_sources[1], output_digest))
        require(trial.outcome in ("SURVIVED_TRIAL", "COUNTEREXAMPLE"), "unclean trial in completed transcript")
        outcome = int(trial.outcome == "COUNTEREXAMPLE")
        wealth = floor.update(wealth, outcome, epsilon, 1 / (1 - epsilon))
        transcript.append(
            {
                "trial": trial.trial,
                "point": dict(trial.point),
                "seed": trial.seed,
                "outcome": trial.outcome,
                "X": outcome,
            }
        )
    require(
        result["transcript"] == transcript and floor.rational(result["E"]) == wealth,
        "exact outcome/wealth transcript differs",
    )
    require(floor.rational(result["threshold"]) == 1 / floor.probability(alpha), "threshold differs")
    admitted = record.verdict == "SURVIVED" and floor.passes(wealth, alpha)
    require(result["resource_observation_pass"] is admitted, "resource comparison differs")
    reproduction = archive.node(entry["reproduction_hash"], floor.REPRO_KIND)
    require(
        reproduction == entry["reproduction"]
        and reproduction["passed"] is True
        and reproduction["independent_sample"] is False,
        "reproduction summary differs",
    )
    require(
        reproduction["floor_hash"] == entry["floor_hash"] and reproduction["hunt_hash"] == entry["hunt_hash"],
        "reproduction binding differs",
    )
    substantive = bundle.canonical_bytes(
        "small_numbers_floor", {"transcript": transcript, "E": floor.exact_text(wealth), "verdict": record.verdict}
    )
    require(
        reproduction["substantive_hash"] == substrate.blob_hash(substantive)
        and reproduction["substantive_bytes"] == len(substantive),
        "canonical substantive replay differs",
    )
    require(
        len(originals) == len(reproduction["repro_records"]) == len(reproduction["rerun_attempts"]),
        "reproduction count differs",
    )
    require(len(set(reproduction["rerun_attempts"])) == len(originals), "rerun attempt IDs repeat")
    require(
        {original["attempt_id"] for original, *_ in originals}.isdisjoint(reproduction["rerun_attempts"]),
        "reruns reuse original attempts",
    )
    for (original, context, identity, source, executor_digest), repro_hash, rerun_id in zip(
        originals, reproduction["repro_records"], reproduction["rerun_attempts"], strict=True
    ):
        rerun, _, _ = attempt_output(archive, rerun_id, context, identity, source, executor_digest)
        require(
            original["recipe_key"] == rerun["recipe_key"]
            and original["output_manifest_hash"] == rerun["output_manifest_hash"],
            "fresh recipe replay differs",
        )
        row = archive.row("repro_records", "hash", repro_hash)
        require(
            row["attempt_id"] == original["attempt_id"]
            and row["kind"] == "second_attempt_agree"
            and row["passed"] == 1,
            "repro companion differs",
        )
        canonical = claims.repro_record_canonical(
            claims.ReproRecord(row["attempt_id"], row["kind"], bool(row["passed"]), row["at"])
        )
        require(archive.get_node(repro_hash)["canonical"] == canonical, "repro canonical record differs")
        archive.linked(entry["reproduction_hash"], repro_hash)
    history = archive.conn.execute(
        "SELECT * FROM tag_history WHERE statement_hash = ? ORDER BY seq", (entry["statement_hash"],)
    ).fetchall()
    require(
        len(history) == 1
        and history[0]["to_tag"] == entry["tag"]
        and history[0]["evidence_hash"] == entry["justified_by"] == entry["hunt_evidence_hash"],
        "tag history differs from ordinary hunt evidence",
    )
    require(
        entry["tag_invariance"] is True
        and entry["tag"] == ("CONJECTURE" if record.verdict == "SURVIVED" else "SPECULATION"),
        "tag invariance differs",
    )
    for digest in (entry["floor_hash"], entry["reproduction_hash"]):
        require(
            archive.conn.execute("SELECT 1 FROM evidence_nodes WHERE hash = ?", (digest,)).fetchone() is None,
            "floor record enters claim evidence",
        )
    archive.linked(entry["floor_hash"], entry["hunt_hash"])
    archive.linked(entry["reproduction_hash"], entry["floor_hash"])
    return {
        "name": case["name"],
        "verdict": record.verdict,
        "completed": len(record.trials),
        "declared": case["budget"],
        "E_display": str(float(wealth)),
        "resource_pass": admitted,
        "fresh_reruns": len(originals),
    }


def audit(artifact_dir):
    artifact_dir = Path(artifact_dir)
    summary = json.loads((artifact_dir / "summary.json").read_bytes())
    manifest = json.loads((artifact_dir / "manifest.json").read_bytes())
    require(file_identity(artifact_dir / "summary.json") == manifest["summary"], "summary archive identity differs")
    require(
        summary["source_sha"] == manifest["source_sha"] and summary["decision_hash"] == manifest["decision_hash"],
        "manifest source or decision differs",
    )
    require(
        manifest["enforced"] is False and manifest["independent_replication"] is False and manifest["exit_status"] == 0,
        "manifest execution scope differs",
    )
    database = artifact_dir / "substrate.sqlite"
    compressed = artifact_dir / "substrate.sqlite.gz"
    if compressed.is_file():
        require(file_identity(compressed) == manifest["substrate_archive"], "compressed substrate identity differs")
        database = Path(tempfile.mkdtemp(prefix="cairn-floor-audit-")) / "substrate.sqlite"
        with gzip.open(compressed, "rb") as incoming, database.open("wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing)
    require(database.is_file(), "substrate archive is missing")
    require(file_identity(database) == manifest["substrate_uncompressed"], "uncompressed substrate identity differs")
    archive = Archive(database)
    try:
        nodes, blobs = archive.check_content()
        preregistration_bytes = committed_bytes(
            summary["source_sha"], "research/grounding/small-numbers-floor-2026-09-30/preregistration.json"
        )
        study = archive.node(summary["study_hash"], floor.STUDY_KIND)
        require(
            study == summary["preregistration"] == json.loads(preregistration_bytes), "study preregistration differs"
        )
        require(
            substrate.blob_hash(preregistration_bytes) == summary["preregistration_blob_hash"],
            "preregistration raw hash differs",
        )
        require(
            hashlib.sha256(preregistration_bytes).hexdigest() == manifest["preregistration_sha256"],
            "manifest preregistration identity differs",
        )
        runtime = archive.node(summary["runtime_hash"], "small_numbers_floor_runtime")
        require(
            runtime == {"source_sha": summary["source_sha"], "runtime": summary["runtime"]},
            "runtime registration differs",
        )
        archive.linked(summary["study_hash"], summary["runtime_hash"])
        cases = [*study["false_controls"], study["positive_control"]]
        require(len(cases) == len(summary["runs"]) == 5 and summary["skips"] == [], "study case count or skips differs")
        runs = [
            audit_run(archive, entry, case, summary["study_hash"], study["alpha"], summary["source_sha"])
            for entry, case in zip(summary["runs"], cases, strict=True)
        ]
        binding = [run["name"] for run in runs[:-1] if run["verdict"] == "SURVIVED" and not run["resource_pass"]]
        decision = archive.node(summary["decision_hash"], "small_numbers_floor_decision")
        require(
            summary["decision"] == decision["decision"] == ("ADOPT" if binding else "DROP"),
            "registered decision differs",
        )
        require(
            decision["enforced"] is False
            and decision["criterion"] == study["decision_rule"]
            and decision["alpha"] == study["alpha"],
            "decision criterion or enforcement differs",
        )
        require(
            decision["source_sha"] == summary["source_sha"] and decision["study_hash"] == summary["study_hash"],
            "decision source or study differs",
        )
        require(
            decision["binding_false_survivors"] == summary["binding_false_survivors"] == binding,
            "binding survivor set differs",
        )
        require(len(decision["registered_cases"]) == len(cases), "decision cases differ")
        for registered, entry in zip(decision["registered_cases"], summary["runs"], strict=True):
            protocol = archive.node(entry["protocol_hash"], floor.PROTOCOL_KIND)
            require(
                registered["name"] == entry["name"]
                and registered["epsilon"] == protocol["epsilon"]
                and registered["alpha"] == protocol["alpha"],
                "decision registered parameters differ",
            )
            for name in ("protocol_hash", "floor_hash", "reproduction_hash", "hunt_hash", "hypothesis_hash"):
                require(registered[name] == entry[name], f"decision {name} differs")
            require(registered["distribution_hash"] == protocol["distribution_hash"], "decision D binding differs")
            for name in ("protocol_hash", "floor_hash", "reproduction_hash", "distribution_hash"):
                archive.linked(summary["decision_hash"], registered[name])
        archive.linked(summary["decision_hash"], summary["study_hash"])
        require(
            archive.conn.execute("SELECT 1 FROM evidence_nodes WHERE hash = ?", (summary["decision_hash"],)).fetchone()
            is None,
            "decision enters claim evidence",
        )
        receipts = archive.conn.execute("SELECT COUNT(*) FROM receipts").fetchone()[0]
        attempts = archive.conn.execute("SELECT COUNT(*) FROM attempts").fetchone()[0]
        reruns = sum(run["fresh_reruns"] for run in runs)
        require(receipts == attempts == 2 * reruns, "receipt/attempt coverage differs")
        require(
            receipts == manifest["receipts"] and len(runs) == manifest["registered_runs"],
            "manifest execution counts differ",
        )
        return {
            "passed": True,
            "decision": summary["decision"],
            "enforced": False,
            "decision_hash": summary["decision_hash"],
            "source_sha": summary["source_sha"],
            "runs": runs,
            "fresh_reruns": reruns,
            "receipts": receipts,
            "nodes": nodes,
            "blobs": blobs,
            "summary": file_identity(artifact_dir / "summary.json"),
            "database": file_identity(database),
        }
    finally:
        archive.conn.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = audit(args.artifact_dir)
    except Exception as error:
        print(json.dumps({"passed": False, "error_type": type(error).__name__, "error": str(error)}, sort_keys=True))
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
