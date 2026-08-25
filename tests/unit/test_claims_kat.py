import json
import shutil
import sys
from pathlib import Path

import pytest

from cairn import canon, claims, keys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import factories

VECTOR_FILE = "claims_kat.json"
VECTORS_PATH = Path(__file__).resolve().parent.parent / "vectors" / VECTOR_FILE
SEED = 20260821


def build_objects():
    stmt = factories.claim_statement(cost_model=True, seed=SEED)
    hyp = factories.hypothesis_object(claim_statement_hash=stmt.hash, seed=SEED)
    table, repro = factories.ladder_table_keep(stmt, stmt.scope, seed=SEED)
    return {
        "hypothesis_object": (hyp, claims.hypothesis_object_canonical(hyp)),
        "claim_statement": (stmt, claims.claim_statement_canonical(stmt)),
        "evidence_node": (table, claims.evidence_node_canonical(table)),
        "repro_record": (repro, claims.repro_record_canonical(repro)),
        "review_verdict": (factories.review_verdict(stmt.hash, seed=SEED), None),
        "gate_run": (factories.gate_run(statement_hash=stmt.hash, seed=SEED), None),
        "ticket": (factories.ticket(hypothesis_key=hyp.hash, node_hash=hyp.hash, seed=SEED), None),
    }


def build_vectors():
    canonicals = {"review_verdict": claims.review_verdict_canonical, "gate_run": claims.gate_run_canonical, "ticket": claims.ticket_canonical}
    vectors = []
    for kind, (obj, canonical) in build_objects().items():
        canonical = canonical if canonical is not None else canonicals[kind](obj)
        vectors.append({"name": kind, "kind": kind, "hash": obj.hash, "canonical_hex": canonical.hex()})
    return {
        "generator": "UPDATE_GOLDENS=1 uv run pytest tests/unit/test_claims_kat.py -k kat_matches",
        "origin": "author_supplied",
        "factory_seed": SEED,
        "created_at": factories.CREATED_AT,
        "vectors": vectors,
    }


def build_text():
    return json.dumps(build_vectors(), indent=1, sort_keys=True) + "\n"


def test_claims_kat_matches_golden(assert_golden):
    assert_golden(VECTOR_FILE, build_text())


@pytest.mark.parametrize("kind", ["hypothesis_object", "claim_statement", "evidence_node", "repro_record", "review_verdict", "gate_run", "ticket"])
def test_committed_hash_recomputes_from_the_committed_canonical(kind, load_vector):
    vector = next(v for v in load_vector(VECTOR_FILE)["vectors"] if v["kind"] == kind)
    canonical = bytes.fromhex(vector["canonical_hex"])
    if kind == "hypothesis_object":
        assert canon.digest(keys.TAG_HYPOTHESIS_KEY, canonical) == vector["hash"]
    else:
        assert keys.node_hash(kind, canonical) == vector["hash"]


def test_claims_kat_guard_rejects_drift(assert_golden, tmp_path, monkeypatch):
    monkeypatch.delenv("UPDATE_GOLDENS", raising=False)
    copy = tmp_path / VECTOR_FILE
    shutil.copy(VECTORS_PATH, copy)
    text = copy.read_text()
    i = text.index('"hash": "') + len('"hash": "')
    copy.write_text(text[:i] + ("0" if text[i] != "0" else "1") + text[i + 1 :])
    with pytest.raises(AssertionError, match="golden mismatch"):
        assert_golden(copy, build_text())
