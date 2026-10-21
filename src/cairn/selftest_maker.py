import dataclasses
import json
from pathlib import Path

from cairn import log, selftest, verifier
from cairn.selftest import SelftestFailed
from cairn.selftest_common import (
    ARM_BITS,
    CORPUS_PATHS,
    INSTANCE_MAKER,
    LABEL_HYPOTHESIS,
    LABEL_NONCE,
    LOG_STEP,
    MAKER_CASE_KEYS,
    MAKER_INSTANCE_FIELDS,
    MAKER_VECTOR_FIELDS,
    OUTCOME_PASS,
    OUTCOME_REFUSED,
    OUTCOME_WRONG,
    _instance_seed,
    _is_hex64,
    _is_int,
    _nonce_from,
    _other_scalar,
    _result,
    _revision,
    _values,
    _verifier_arm,
)


def check_maker_corpus(doc):
    if not isinstance(doc, dict):
        raise selftest.CorpusSchemaError("$", f"corpus must be an object, got {type(doc).__name__}")
    missing = [k for k in ("schema_version", "pass_floor", "cases") if k not in doc]
    if missing:
        raise selftest.CorpusSchemaError("$", f"corpus is missing {', '.join(missing)}")
    if doc["schema_version"] != selftest.SCHEMA_VERSION:
        raise selftest.CorpusSchemaError("$.schema_version", f"schema_version must be {selftest.SCHEMA_VERSION}")
    cases = doc["cases"]
    if not isinstance(cases, list) or not cases:
        raise selftest.CorpusSchemaError("$.cases", "cases must be a non-empty list")
    seen = set()
    for index, case in enumerate(cases):
        path = f"$.cases[{index}]"
        if not isinstance(case, dict):
            raise selftest.CorpusSchemaError(path, f"case must be an object, got {type(case).__name__}")
        absent = [k for k in MAKER_CASE_KEYS if k not in case]
        if absent:
            raise selftest.CorpusSchemaError(path, f"case is missing {', '.join(absent)}")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen:
            raise selftest.CorpusSchemaError(f"{path}.id", "id must be a unique non-empty string")
        seen.add(case["id"])
        if case["ledger"] not in selftest.LEDGER_VALUES:
            raise selftest.CorpusSchemaError(f"{path}.ledger", f"ledger must be one of {selftest.LEDGER_VALUES}")
        if not isinstance(case["source"], str) or not case["source"]:
            raise selftest.CorpusSchemaError(f"{path}.source", "source must be a non-empty string")
        fields = case["fields"]
        if not isinstance(fields, dict):
            raise selftest.CorpusSchemaError(f"{path}.fields", "fields must be an object")
        unknown = sorted(set(fields) - set(MAKER_VECTOR_FIELDS) - set(MAKER_INSTANCE_FIELDS))
        if unknown:
            raise selftest.CorpusSchemaError(f"{path}.fields", f"unknown fields {', '.join(unknown)}")
        lacking = [k for k in MAKER_VECTOR_FIELDS if k not in fields]
        if lacking:
            raise selftest.CorpusSchemaError(f"{path}.fields", f"missing required fields {', '.join(lacking)}")
        present = [k for k in MAKER_INSTANCE_FIELDS if k in fields]
        if present and len(present) != len(MAKER_INSTANCE_FIELDS):
            raise selftest.CorpusSchemaError(f"{path}.fields", "an instance case carries all of p, a, b, n, P, Q, x")
        for name in sorted(fields):
            selftest._check_field(f"{path}.fields.{name}", name, fields[name]) if name in (
                "p",
                "a",
                "b",
                "n",
                "x",
                "P",
                "Q",
            ) else _check_vector_field(f"{path}.fields.{name}", name, fields[name])
    selftest._check_floor(doc["pass_floor"], len(cases))
    return doc


def _check_vector_field(path, name, field):
    if not isinstance(field, dict) or set(field) != set(selftest.FIELD_KEYS):
        raise selftest.CorpusSchemaError(path, f"field must hold exactly {selftest.FIELD_KEYS}")
    if field["origin"] not in selftest.ORIGINS:
        raise selftest.CorpusSchemaError(f"{path}.origin", f"origin must be one of {selftest.ORIGINS}")
    value = field["value"]
    if name in ("nonce", "hypothesis_key"):
        if not _is_hex64(value):
            raise selftest.CorpusSchemaError(f"{path}.value", f"{name} must be 64 lowercase hex digits")
    elif not _is_int(value) or value < 0:
        raise selftest.CorpusSchemaError(f"{path}.value", f"{name} must be a non-negative integer")


def load_maker_corpus(path=None):
    path = CORPUS_PATHS[INSTANCE_MAKER] if path is None else path
    try:
        doc = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise selftest.CorpusSchemaError("$", f"corpus is not valid JSON: {exc}") from None
    return check_maker_corpus(doc)


def _run_maker_case(case):
    from cairn import instances
    from cairn.skills import instance_maker

    v = _values(case)
    derived = instances.trial_seed(v["nonce"], v["hypothesis_key"], v["bits"], v["trial"])
    body = {"derived_seed": derived, "seed_matches": derived == v["seed"]}
    if "p" not in v:
        body["outcome"] = OUTCOME_PASS if body["seed_matches"] else OUTCOME_WRONG
        return body
    try:
        out = instance_maker.run(v["bits"], v["seed"])
    except instance_maker.InputError as exc:
        return {**body, "outcome": OUTCOME_REFUSED, "reason": str(exc)}
    instance_maker.check_postcondition(out)
    matches = {
        name: (list(getattr(out, name)) if name in ("P", "Q") else getattr(out, name)) == v[name]
        for name in MAKER_INSTANCE_FIELDS
    }
    body.update(
        instance_hash=out.instance_hash,
        cross_check=out.cross_check["result"],
        status=out.status,
        matches=matches,
        outcome=OUTCOME_PASS
        if body["seed_matches"] and all(matches.values()) and out.status == "OK"
        else OUTCOME_WRONG,
    )
    return body


def instance_maker_run_once(config, *, doc=None, root=None):
    from cairn import instances
    from cairn.skills import instance_maker

    lg = log.get(LOG_STEP)
    doc = load_maker_corpus() if doc is None else check_maker_corpus(doc)
    seed = _instance_seed(_revision(instance_maker, root))
    records = []
    ledger = {}
    passes = 0
    for case in doc["cases"]:
        body = _run_maker_case(case)
        declared = case["ledger"]
        if declared == "pass" and body["outcome"] != OUTCOME_PASS:
            raise SelftestFailed("ledger", f"case {case['id']} declares pass but the maker reported {body}")
        if declared == "pass":
            passes += 1
        ledger[case["id"]] = declared
        lg.info("case", id=case["id"], ledger=declared, observed=selftest._canonical_json(body))
        records.append(("case", case["id"], {"ledger": declared, "observed": body}))
    floor = doc["pass_floor"]
    if passes < floor:
        raise SelftestFailed("floor", f"{passes} passing cases is below the floor {floor}")
    nonce = _nonce_from(seed, LABEL_NONCE)
    hypothesis_key = _nonce_from(seed, LABEL_HYPOTHESIS)
    derived = instances.trial_seed(nonce, hypothesis_key, ARM_BITS, 0)
    again = instances.trial_seed(nonce, hypothesis_key, ARM_BITS, 0)
    if derived != again:
        raise SelftestFailed("derivation-arm", f"the same inputs derived {derived} and {again}")
    flipped = ("0" if nonce[0] != "0" else "1") + nonce[1:]
    diverged = {
        "nonce": instances.trial_seed(flipped, hypothesis_key, ARM_BITS, 0) != derived,
        "hypothesis_key": instances.trial_seed(nonce, flipped, ARM_BITS, 0) != derived,
        "bits": instances.trial_seed(nonce, hypothesis_key, ARM_BITS + 1, 0) != derived,
        "trial": instances.trial_seed(nonce, hypothesis_key, ARM_BITS, 1) != derived,
    }
    if not all(diverged.values()):
        raise SelftestFailed("derivation-arm", f"a flipped input did not diverge: {diverged}")
    out = instance_maker.run(ARM_BITS, derived)
    instance_maker.check_postcondition(out)
    planted = dataclasses.replace(out, x=out.x % (out.n - 1) + 1)
    try:
        instance_maker.check_postcondition(planted)
    except instance_maker.PostconditionFailed:
        planted_refused = True
    else:
        planted_refused = False
    if not planted_refused:
        raise SelftestFailed("postcondition-arm", "a planted x' != x passed the maker's postcondition")
    arm_body = {
        "bits": ARM_BITS,
        "derived_seed": derived,
        "diverged": diverged,
        "instance_hash": out.instance_hash,
        "tries": out.tries,
        "planted_refused": planted_refused,
        "outcome": OUTCOME_PASS,
    }
    lg.info("arm", name="postcondition", seed=seed, observed=selftest._canonical_json(arm_body))
    records.append(("arm", "postcondition", arm_body))
    instance = verifier.Instance(out.p, out.a, out.b, out.n, tuple(out.P), tuple(out.Q))
    verifier_body = _verifier_arm(config, instance, out.x, _other_scalar(seed, out.n, out.x, b"instance-maker-x-prime"))
    lg.info("arm", name="verifier", bundle_hash=config.bundle_hash, ok=1, fail=1, expected=1)
    records.append(("arm", "verifier", verifier_body))
    arms = {
        "postcondition": arm_body["outcome"],
        "verifier": {"ok": verifier_body["ok"], "fail": verifier_body["fail"]},
    }
    return _result(records, ledger, passes, floor, arms, seed, doc)
