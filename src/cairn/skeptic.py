import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass

from cairn import bundle, canon, claims, hunt, instances, keys, substrate
from cairn.substrate import EDGE_INPUT, node_hash_for

MAX_EVIDENCE_KINDS = frozenset({"repro_node", "ladder_table", "counterexample_hunt_record", "lean_artifact"})
SCOPE_FIELDS = frozenset({"evidence_kinds"})


class ScopedReadRefused(PermissionError):
    pass


@dataclass(frozen=True, slots=True)
class RerunRequest:
    statement_hash: str
    evidence_hash: str
    attempt_id: str
    recipe_key: str


@dataclass(frozen=True, slots=True)
class Handle:
    statement_hash: str
    _records: tuple[tuple[str, str], ...]

    @property
    def node_hashes(self):
        return tuple(digest for digest, _ in self._records)

    def read(self, node_hash):
        for digest, payload in self._records:
            if digest == node_hash:
                return json.loads(payload)
        raise ScopedReadRefused(f"node {node_hash!r} is outside the Skeptic scope")

    def request_rerun(self, evidence_hash):
        projection = self.read(evidence_hash)
        fields = {"kind", "recipe_hash", "certificate_hash", "repro_record_hash", "attempt_id"}
        if projection.get("kind") == hunt.KIND:
            fields.update(("hunt_run_hash", "verifier_certificate_hash"))
        if set(projection) != fields:
            raise ScopedReadRefused("reruns require a non-Lean evidence projection")
        if projection["kind"] == "lean_artifact":
            raise ScopedReadRefused("Lean evidence cannot request a worker rerun")
        if not projection["attempt_id"] or not projection["recipe_hash"]:
            raise ScopedReadRefused("evidence has no rerunnable attempt")
        return RerunRequest(
            statement_hash=self.statement_hash,
            evidence_hash=evidence_hash,
            attempt_id=projection["attempt_id"],
            recipe_key=projection["recipe_hash"],
        )


def _refuse(reason):
    raise ScopedReadRefused(reason)


def _pinned_gate(gate_bundle):
    try:
        pinned = bundle.GateBundle.open(gate_bundle.path, gate_bundle.pin_path)
    except Exception as exc:
        _refuse(f"gate bundle could not be reopened: {exc}")
    if pinned.hash != gate_bundle.hash or pinned.pin_hash != gate_bundle.pin_hash:
        _refuse("supplied gate bundle is not the pinned bundle")
    return pinned


def _scope_kinds(gate_bundle):
    try:
        skeptic_scope = gate_bundle.object("skeptic_scope")
    except (bundle.BundleError, canon.CanonError) as exc:
        _refuse(f"pinned gate bundle has no skeptic_scope object: {exc}")
    if not isinstance(skeptic_scope, Mapping) or set(skeptic_scope) != SCOPE_FIELDS:
        _refuse("skeptic_scope must have exactly the evidence_kinds field")
    kinds = skeptic_scope["evidence_kinds"]
    if not isinstance(kinds, list):
        _refuse("skeptic_scope.evidence_kinds must be a list")
    if any(not isinstance(kind, str) for kind in kinds):
        _refuse("skeptic_scope evidence kinds must be strings")
    if len(set(kinds)) != len(kinds):
        _refuse("skeptic_scope evidence kinds must be duplicate-free")
    if not set(kinds) <= MAX_EVIDENCE_KINDS:
        _refuse("skeptic_scope contains an unsupported evidence kind")
    return frozenset(kinds)


def _raw_node(sub, digest, kind, schema):
    row = sub.get_node(digest)
    if row is None:
        _refuse(f"scoped {kind} node {digest!r} is absent")
    if row["kind"] != kind:
        _refuse(f"scoped node {digest!r} is not a {kind}")
    canonical = bytes(row["canonical"])
    if node_hash_for(kind, canonical) != digest:
        _refuse(f"scoped {kind} node {digest!r} does not match its canonical bytes")
    try:
        value = canon.decode(schema, canonical)
    except canon.CanonError as exc:
        _refuse(f"scoped {kind} node {digest!r} is not canonically typed: {exc}")
    return canonical, value


def _canonical_projection(canonical):
    return {"canonical": {"encoding": "base64", "content": base64.b64encode(canonical).decode("ascii")}}


def _jsonable(value):
    if isinstance(value, frozenset):
        return sorted(_jsonable(item) for item in value)
    if isinstance(value, tuple):
        return [_jsonable(item) for item in value]
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def _store(records, digest, projection):
    encoded = json.dumps(_jsonable(projection), sort_keys=True, separators=(",", ":"))
    prior = records.get(digest)
    if prior is not None and prior != encoded:
        _refuse(f"scoped node {digest!r} has conflicting projections")
    records[digest] = encoded


def _store_certificate(sub, records, identity_bundle_hash):
    row = sub.get_certificate(identity_bundle_hash)
    if row is None:
        return None
    cert_hash = row["cert_hash"]
    canonical, certificate = _raw_node(sub, cert_hash, "skill_certificate", keys.SELFTEST_CERT)
    if certificate["identity_bundle_hash"] != identity_bundle_hash:
        _refuse(f"certificate {cert_hash!r} names another identity bundle")
    if any(
        row[field] != certificate[field] for field in ("identity_bundle_hash", "transcript_hash", "env_manifest_hash")
    ):
        _refuse(f"certificate {cert_hash!r} companion references differ from its canonical bytes")
    _store(
        records,
        cert_hash,
        {**_canonical_projection(canonical), "companion_observation": {"selftest_summary": row["selftest_summary"]}},
    )
    return cert_hash


def _store_repro(sub, records, repro_hash, attempt_id):
    if repro_hash is None:
        return
    canonical, value = _raw_node(sub, repro_hash, "repro_record", claims.REPRO_RECORD)
    if value["attempt_id"] != attempt_id:
        _refuse(f"repro record {repro_hash!r} names a different attempt")
    _store(records, repro_hash, _canonical_projection(canonical))


def _non_lean_projection(sub, records, evidence):
    attempt_id = evidence["attempt_id"]
    recipe_key = None
    certificate_hash = None
    if attempt_id is not None:
        attempt = sub.get_attempt(attempt_id)
        if attempt is None:
            _refuse(f"evidence attempt {attempt_id!r} is absent")
        recipe_key = attempt["recipe_key"]
        recipe_canonical, recipe = _raw_node(sub, recipe_key, "recipe", keys.RECIPE)
        _store(records, recipe_key, _canonical_projection(recipe_canonical))
        certificate_hash = _store_certificate(sub, records, recipe["skill_identity_hash"])
    else:
        certificate_hash = _store_certificate(sub, records, evidence["producer_identity"])
    _store_repro(sub, records, evidence["repro_record_hash"], attempt_id)
    return {
        "kind": evidence["kind"],
        "recipe_hash": recipe_key,
        "certificate_hash": certificate_hash,
        "repro_record_hash": evidence["repro_record_hash"],
        "attempt_id": attempt_id,
    }


def _typed_projection(kind, canonical, value):
    return {"kind": kind, **_canonical_projection(canonical), "value": value}


def _hunt_blob(sub, digest):
    data = sub.get_blob(digest)
    if data is None or substrate.blob_hash(data) != digest:
        _refuse(f"hunt evidence blob {digest!r} is absent or does not match its content")
    try:
        value = json.loads(data)
    except (TypeError, ValueError) as exc:
        _refuse(f"hunt evidence blob {digest!r} is not JSON: {exc}")
    if not isinstance(value, dict):
        _refuse(f"hunt evidence blob {digest!r} is not an object")
    return data, value


def _hunt_attempt(sub, records, digest, attempt_id, identity, context, executor_output=None):
    data, value = _hunt_blob(sub, digest)
    if attempt_id is None:
        _store(records, digest, _typed_projection("hunt_trial_evidence", data, value))
        return None
    attempt = sub.get_attempt(attempt_id)
    recorded = value.get("attempt")
    if (
        attempt is None
        or not isinstance(recorded, dict)
        or any(
            recorded.get(field) != attempt[field]
            for field in (
                "attempt_id",
                "recipe_key",
                "status",
                "output_manifest_hash",
                "receipt_hash",
                "skip_cache_lookup",
            )
        )
    ):
        _refuse(f"hunt evidence {digest!r} does not bind attempt {attempt_id!r}")
    recipe_canonical, recipe = _raw_node(sub, attempt["recipe_key"], "recipe", keys.RECIPE)
    if _jsonable(recipe) != value.get("recipe"):
        _refuse(f"hunt evidence {digest!r} recipe differs from its canonical bytes")
    if recipe["skill_identity_hash"] != identity or recipe["seed"] != context["seed"]:
        _refuse(f"hunt attempt {attempt_id!r} identity or seed differs from its trial")
    input_ref = recipe["inputs"].get("hunt_input")
    if input_ref is None:
        _refuse(f"hunt attempt {attempt_id!r} has no hunt_input")
    input_data, input_value = _hunt_blob(sub, input_ref[0])
    if len(input_data) != input_ref[1] or input_value != context:
        _refuse(f"hunt attempt {attempt_id!r} input differs from its trial")
    if executor_output is not None and tuple(recipe["inputs"].get("executor_output", ())) != executor_output:
        _refuse(f"hunt verifier {attempt_id!r} input does not bind executor output")
    _store(records, attempt["recipe_key"], _canonical_projection(recipe_canonical))
    receipt_hash = attempt["receipt_hash"]
    receipt = value.get("receipt")
    if receipt_hash is not None:
        receipt_canonical, _ = _raw_node(sub, receipt_hash, "receipt", substrate.RECEIPT)
        try:
            matches = isinstance(receipt, dict) and substrate.receipt_canonical(receipt) == receipt_canonical
        except substrate.SubstrateError, TypeError, ValueError, canon.CanonError:
            matches = False
        if not matches or receipt.get("receipt_hash") != receipt_hash:
            _refuse(f"hunt evidence {digest!r} receipt differs from its canonical bytes")
        _store(records, receipt_hash, _canonical_projection(receipt_canonical))
    elif receipt is not None:
        _refuse(f"hunt evidence {digest!r} carries an unbound receipt")
    output = None
    manifest_hash = attempt["output_manifest_hash"]
    if manifest_hash is not None:
        manifest_canonical, manifest = _raw_node(sub, manifest_hash, "output_manifest", substrate.OUTPUT_MANIFEST)
        output = manifest["artifacts"].get("output.json")
        if receipt is None or output is None or output[0] != receipt["stdout_digest"]:
            _refuse(f"hunt attempt {attempt_id!r} output manifest does not bind receipt stdout")
        output_data = sub.get_blob(output[0])
        if output_data is None or len(output_data) != output[1] or substrate.blob_hash(output_data) != output[0]:
            _refuse(f"hunt attempt {attempt_id!r} stdout is absent or does not match its content")
        try:
            output_value = json.loads(output_data)
        except TypeError, ValueError:
            output_value = None
        _store(records, output[0], _typed_projection("hunt_trial_output", output_data, output_value))
        _store(records, manifest_hash, _canonical_projection(manifest_canonical))
    _store(
        records,
        digest,
        {
            **_typed_projection("hunt_trial_evidence", data, value),
            "companion_observation": {"disowned_at": attempt["disowned_at"], "inadmissible": attempt["inadmissible"]},
        },
    )
    return output


def _hunt_projection(sub, records, evidence_hash, evidence):
    record = hunt.record_for_evidence(sub, {**evidence, "hash": evidence_hash})
    if record is None:
        _refuse(f"hunt evidence {evidence_hash!r} has no unique bound hunt run")
    nonce = instances.get_nonce(sub, record.nonce)
    if nonce is None or nonce.hypothesis_key != record.hypothesis_key:
        _refuse(f"hunt run {record.hash!r} has no matching persisted nonce")
    if nonce.withheld:
        _refuse(f"hunt run {record.hash!r} nonce is unpublished")
    run_canonical, run = _raw_node(sub, record.hash, "hunt_run", hunt.RUN)
    plan_canonical, plan = _raw_node(sub, record.plan_hash, "hunt_plan", hunt.PLAN)
    if any(plan[field] != run[field] for field in ("statement_hash", "hypothesis_key", "distribution_hash")) or (
        plan["trial_count"] != record.declared_trial_count
    ):
        _refuse(f"hunt plan {record.plan_hash!r} does not bind its run")
    distribution_canonical, distribution = _raw_node(
        sub, record.distribution_hash, "hunt_distribution", hunt.DISTRIBUTION
    )
    hypothesis_canonical, hypothesis = _raw_node(
        sub, record.hypothesis_key, "hypothesis_object", keys.HYPOTHESIS_OBJECT
    )
    hypothesis_row = claims.get_hypothesis_object(sub, record.hypothesis_key)
    if (
        hypothesis_row is None
        or hypothesis_row["claim_statement_hash"] != record.statement_hash
        or any(
            hypothesis[source] != plan[target]
            for source, target in (
                ("target_family", "target_family"),
                ("method_identity", "method_identity"),
                ("declared_parameter_ranges", "family_bounds"),
                ("sampling_distribution", "distribution_hash"),
            )
        )
    ):
        _refuse(f"hunt hypothesis {record.hypothesis_key!r} does not bind its plan")
    required = {record.plan_hash, record.distribution_hash}
    required.update(
        digest
        for trial in record.trials
        for digest in (trial.execution_evidence, trial.verifier_evidence)
        if digest is not None
    )
    parents = {edge["parent_hash"] for edge in sub.lineage_of(record.hash) if edge["edge_kind"] == EDGE_INPUT}
    if not required <= parents:
        _refuse(f"hunt run {record.hash!r} is missing recorded input bindings")
    for digest, kind, canonical, value in (
        (record.hash, "hunt_run", run_canonical, run),
        (record.plan_hash, "hunt_plan", plan_canonical, plan),
        (record.distribution_hash, "hunt_distribution", distribution_canonical, distribution),
        (record.hypothesis_key, "hypothesis_object", hypothesis_canonical, hypothesis),
    ):
        _store(records, digest, _typed_projection(kind, canonical, value))
    verifier_certificate_hash = None
    for role in ("executor", "verifier"):
        identity = plan[role + "_identity"]
        certificate_hash = _store_certificate(sub, records, identity)
        if role == "verifier":
            verifier_certificate_hash = certificate_hash
        if certificate_hash is not None or sub.get_node(identity) is not None:
            canonical, value = _raw_node(sub, identity, "identity_bundle", keys.IDENTITY_BUNDLE)
            _store(records, identity, _canonical_projection(canonical))
    for trial in record.trials:
        context = {
            "statement_hash": record.statement_hash,
            "plan_hash": record.plan_hash,
            "run_id": nonce.run_id,
            "trial": trial.trial,
            "point": dict(trial.point),
            "seed": trial.seed,
        }
        output = _hunt_attempt(
            sub, records, trial.execution_evidence, trial.attempt_id, plan["executor_identity"], context
        )
        if trial.verifier_evidence is not None:
            _hunt_attempt(
                sub,
                records,
                trial.verifier_evidence,
                trial.verifier_attempt_id,
                plan["verifier_identity"],
                context,
                output,
            )
    return {
        **_non_lean_projection(sub, records, evidence),
        "hunt_run_hash": record.hash,
        "verifier_certificate_hash": verifier_certificate_hash,
    }


def _lean_projection(sub, evidence_hash, statement_hash, pinned):
    edges = [edge for edge in sub.lineage_of(evidence_hash) if edge["edge_kind"] == EDGE_INPUT]
    if len(edges) != 1:
        _refuse(f"Lean evidence {evidence_hash!r} needs exactly one gate-run input edge")
    gate_hash = edges[0]["parent_hash"]
    _, gate = _raw_node(sub, gate_hash, "gate_run", claims.GATE_RUN)
    row = claims.get_gate_run(sub, gate_hash)
    if row is None:
        _refuse(f"gate run {gate_hash!r} is absent")
    if gate["statement_hash"] != statement_hash or row["statement_hash"] != statement_hash:
        _refuse(f"gate run {gate_hash!r} is for another statement")
    if gate["bundle_hash"] != pinned.hash or row["bundle_hash"] != pinned.hash:
        _refuse(f"gate run {gate_hash!r} is for another gate bundle")
    if not gate["formal_statement_hash"]:
        _refuse(f"gate run {gate_hash!r} has no formal statement hash")
    return {"formal_statement_hash": gate["formal_statement_hash"], "verdict": gate["result"]}


def snapshot(sub, gate_bundle, statement_hash):
    pinned = _pinned_gate(gate_bundle)
    kinds = _scope_kinds(pinned)
    _, statement = _raw_node(sub, statement_hash, "claim_statement", claims.CLAIM_STATEMENT)
    if claims.get_claim_statement(sub, statement_hash) is None:
        _refuse(f"claim statement {statement_hash!r} is absent")
    records = {}
    _store(records, statement_hash, statement)
    evidence_rows = claims.evidence_for(sub, statement_hash)
    for row in evidence_rows:
        evidence_hash = row["hash"]
        _, evidence = _raw_node(sub, evidence_hash, "evidence_node", claims.EVIDENCE_NODE)
        if evidence["target_statement_hash"] != statement_hash:
            _refuse(f"evidence {evidence_hash!r} does not name the scoped statement")
        if evidence["kind"] not in kinds:
            continue
        if evidence["kind"] == "lean_artifact":
            projection = _lean_projection(sub, evidence_hash, statement_hash, pinned)
        elif evidence["kind"] == hunt.KIND:
            projection = _hunt_projection(sub, records, evidence_hash, evidence)
        else:
            projection = _non_lean_projection(sub, records, evidence)
        _store(records, evidence_hash, projection)
    return Handle(statement_hash=statement_hash, _records=tuple(sorted(records.items())))
