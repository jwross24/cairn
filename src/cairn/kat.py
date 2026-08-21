import json
from pathlib import Path

from cairn import canon, cli, exits, keys, log

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VECTORS = REPO_ROOT / "tests" / "vectors" / "canon_kat.json"


def compute(vector):
    kind = vector["kind"]
    if kind == "node":
        payload = canon.encode(canon.STR, vector["input"]["payload"])
        return keys.node_hash(vector["input"]["node_kind"], payload), (canon.encode(canon.STR, vector["input"]["node_kind"]) + payload).hex()
    if vector["domain_tag"] != keys.TAGS_BY_KIND[kind]:
        raise canon.CanonError(f"{vector['name']}: domain tag {vector['domain_tag']} is not the {kind} tag")
    canonical = canon.encode(keys.SCHEMAS[kind], vector["input"])
    return keys.HASHERS[kind](vector["input"]), canonical.hex()


def run(path=DEFAULT_VECTORS):
    data = json.loads(Path(path).read_text())
    lg = log.get("kat.canon")
    computed = {}
    failures = []
    for vector in data["vectors"]:
        name = vector["name"]
        digest, canonical_hex = compute(vector)
        computed[name] = digest
        match = digest == vector["expected"] and canonical_hex == vector["canonical_hex"]
        lg.info("vector", name=name, expected=vector["expected"], computed=digest, match=match)
        if not match:
            failures.append(f"{name}: expected {vector['expected']} got {digest}")
    for vector in data["vectors"]:
        relation = vector.get("relation") or {}
        if "equals" in relation and computed[vector["name"]] != computed[relation["equals"]]:
            failures.append(f"{vector['name']} must equal {relation['equals']}")
        if "differs" in relation and computed[vector["name"]] == computed[relation["differs"]]:
            failures.append(f"{vector['name']} must differ from {relation['differs']}")
    lg.info("result", vectors=len(data["vectors"]), failures=len(failures))
    return failures


def _configure(parser):
    parser.add_argument("which", nargs="?", default="canon", choices=["canon"])
    parser.add_argument("--vectors", default=str(DEFAULT_VECTORS))


def _run(ns):
    failures = run(ns.vectors)
    if ns.json:
        cli.emit_json("kat", {"which": ns.which, "vectors": str(ns.vectors), "ok": not failures, "failures": failures})
    elif failures:
        print("FAIL")
        for line in failures:
            print(line)
    else:
        print("PASS")
    return exits.GATE_REFUSED if failures else exits.OK


cli.register("kat", _configure, _run, summary="run the canonicalizer known-answer vectors (a gate self-test); exit 2 on any mismatch", read_only=True, json=True)
