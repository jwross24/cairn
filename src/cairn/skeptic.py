import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass

from cairn import bundle, canon, claims, keys
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
        if set(projection) != {"kind", "recipe_hash", "certificate_hash", "repro_record_hash", "attempt_id"}:
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
    _store(records, cert_hash, _canonical_projection(canonical))
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
        else:
            projection = _non_lean_projection(sub, records, evidence)
        _store(records, evidence_hash, projection)
    return Handle(statement_hash=statement_hash, _records=tuple(sorted(records.items())))
