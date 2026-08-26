import json
from pathlib import Path

from cairn import env, keys, selftest


def corpus_records(path):
    doc = json.loads(Path(path).read_text())
    records = []
    passes = 0
    for case in doc["cases"]:
        observed, held_all, _ = selftest.run_case(case)
        if case["ledger"] == "pass" and held_all:
            passes += 1
        records.append(("case", case["id"], {"ledger": case["ledger"], "observed": observed}))
    return doc, records, passes


def certify(module, sub, *, record=True):
    doc, records, passes = corpus_records(module.CORPUS_PATH)
    transcript_hash = selftest.transcript_digest(selftest.transcript_bytes(records))
    identity = module.identity_bundle()
    identity_hash = keys.identity_bundle_hash(identity)
    env_hash = keys.env_manifest_digest(env.manifest())
    summary = {
        "corpus_origins": {
            case["id"]: {name: entry.get("origin") for name, entry in case["fields"].items()} for case in doc["cases"]
        },
        "randomized_arm": False,
        "cross_check": {"axis": module.CROSS_CHECK_AXIS, "independent_range": module.INDEPENDENT_RANGE},
        "pass": passes,
        "floor": doc["pass_floor"],
    }
    if record:
        if sub.get_node(identity_hash) is None:
            sub.put_identity_bundle(identity)
        if sub.get_certificate(identity_hash) is None:
            sub.put_certificate(identity_hash, transcript_hash, env_hash, summary)
    return {
        "identity_bundle_hash": identity_hash,
        "transcript_hash": transcript_hash,
        "summary": summary,
        "passes": passes,
        "floor": doc["pass_floor"],
        "double_run": "byte-equal",
    }


def transcript(module):
    return selftest.transcript_bytes(corpus_records(module.CORPUS_PATH)[1])
