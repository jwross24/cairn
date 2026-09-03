"""The §2 self-test for the M1 baseline skills: rho_dp, bsgs and the instance-maker.

Each skill runs its vendored corpus under a pinned case seed, then a
randomized_postcondition arm keyed on H(implementation_revision || label): a
fresh instance from toy_curve, the skill's own answer checked end to end, a
wrong answer refused by the Tier-0 verifier, and for rho_dp the witness refused
in each planted form by the gate-side witness verifier. The certificate is the
digest of the canonical transcript, and a double run must be byte-equal.
"""

import json
from pathlib import Path

from cairn import canon, ec, env, keys, log, selftest, verifier, witness
from cairn.selftest import SelftestFailed

REPO_ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = Path(__file__).resolve().parent / "skills"
RHO_DP = "rho-dp"
BSGS = "bsgs"
INSTANCE_MAKER = "instance-maker"
NAMES = (RHO_DP, BSGS, INSTANCE_MAKER)
MODULES = {RHO_DP: "cairn.skills.rho_dp", BSGS: "cairn.skills.bsgs", INSTANCE_MAKER: "cairn.skills.instance_maker"}
CORPUS_PATHS = {
    RHO_DP: SKILLS_DIR / "rho_dp_corpus.json",
    BSGS: SKILLS_DIR / "bsgs_corpus.json",
    INSTANCE_MAKER: SKILLS_DIR / "instance_maker_corpus.json",
}
LOG_STEP = "selftest"
CASE_SEED = 1
ARM_BITS = 30
OUTCOME_PASS = "pass"
OUTCOME_REFUSED = "refused"
OUTCOME_WRONG = "wrong"
LABEL_X = {RHO_DP: b"rho-dp-x", BSGS: b"bsgs-x"}
LABEL_X_PRIME = {RHO_DP: b"rho-dp-x-prime", BSGS: b"bsgs-x-prime"}
LABEL_NONCE = b"instance-maker-nonce"
LABEL_HYPOTHESIS = b"instance-maker-hypothesis"
MAKER_VECTOR_FIELDS = ("nonce", "hypothesis_key", "bits", "trial", "seed")
MAKER_INSTANCE_FIELDS = ("p", "a", "b", "n", "P", "Q", "x")
MAKER_CASE_KEYS = ("id", "ledger", "source", "fields")
HEX_DIGITS = frozenset("0123456789abcdef")


def module_for(which):
    import importlib

    if which not in MODULES:
        raise KeyError(f"no self-test for {which!r}; one of {NAMES}")
    return importlib.import_module(MODULES[which])


def postcondition_errors():
    from cairn.skills import toy_curve

    return (toy_curve.PostconditionFailed, *(module_for(which).PostconditionFailed for which in NAMES))


def _values(case):
    return {name: field["value"] for name, field in case["fields"].items()}


def _instance_seed(revision):
    return selftest.arm_seed(revision) or 1


def _revision(module, root):
    return module.implementation_revision() if root is None else module.implementation_revision(root)


def _identity(module, root):
    return module.identity_bundle() if root is None else module.identity_bundle(root)


def _run_dlp_case(module, case):
    v = _values(case)
    bits = v["p"].bit_length()
    try:
        out = module.run(bits, CASE_SEED, v["p"], v["a"], v["b"], v["n"], v["P"], v.get("Q", [0, 0]))
    except module.InputError as exc:
        return {"outcome": OUTCOME_REFUSED, "reason": str(exc)}
    body = {"x": out.x, "ops": out.ops, "cross_check": out.cross_check["result"], "status": out.status}
    if hasattr(out, "memory"):
        body["entries"] = out.memory["entries"]
        body["table_bytes"] = out.memory["table_bytes"]
    if hasattr(out, "witness"):
        body["witness_verdict"] = witness.verify(witness.witness_from_output(out.to_dict())).reason or "accepted"
        body["collision"] = out.witness["collision"]
    expected = v.get("x")
    body["outcome"] = (
        OUTCOME_PASS if expected is not None and out.x == expected and out.status == "OK" else OUTCOME_WRONG
    )
    return body


def _dlp_cases(module, doc, lg):
    records = []
    ledger = {}
    passes = 0
    for case in doc["cases"]:
        observed, held_all, held = selftest.run_case(case)
        skill = _run_dlp_case(module, case)
        declared = case["ledger"]
        if declared == "pass":
            if not held_all:
                broken = sorted(name for name, value in held.items() if not value)
                raise SelftestFailed("ledger", f"case {case['id']} declares pass but {', '.join(broken)} failed")
            if skill["outcome"] != OUTCOME_PASS:
                raise SelftestFailed("ledger", f"case {case['id']} declares pass but the skill reported {skill}")
            passes += 1
        ledger[case["id"]] = declared
        lg.info(
            "case",
            id=case["id"],
            ledger=declared,
            observed=selftest._canonical_json(observed),
            skill=selftest._canonical_json(skill),
            held=selftest._canonical_json(held),
        )
        records.append(("case", case["id"], {"ledger": declared, "observed": observed, "skill": skill}))
    return records, ledger, passes


def _arm_instance(seed, label):
    from cairn.skills import toy_curve

    curve = toy_curve.run(ARM_BITS, seed)
    toy_curve.check_postcondition(curve)
    x = selftest._draws(seed, curve.n, 1, label)[0]
    P = tuple(curve.P)
    Q = ec.mul(curve.p, curve.a, P, x)
    return curve, x, P, Q


def _other_scalar(seed, n, x, label):
    other = selftest._draws(seed, n, 1, label)[0]
    if other == x:
        other = x % (n - 1) + 1
    return other


def _verifier_arm(config, instance, x, other):
    driver = verifier.Verifier(config)
    accepted = driver.run(instance, x)
    if not accepted.accepted:
        raise SelftestFailed("verifier-arm", f"the skill's x = {x} was refused: {accepted.reason}")
    refused = driver.run(instance, other)
    if refused.accepted:
        raise SelftestFailed("verifier-arm", f"x' = {other} != x was accepted")
    if refused.reason != "xP-ne-Q":
        raise SelftestFailed("verifier-arm", f"unexpected refusal reason {refused.reason!r}")
    return {"ok": 1, "fail": 1, "reasons": {refused.reason: 1}, "outcome": OUTCOME_PASS}


def _next_prime(n):
    from cairn import pari

    return int(pari.pari.nextprime(n + 1))


def _witness_arm(out):
    good = witness.witness_from_output(out.to_dict())
    accepted = witness.verify(good)
    if not accepted.accepted or accepted.x != out.x:
        raise SelftestFailed("witness-arm", f"the skill's own witness was refused: {accepted.reason}")
    planted = {
        witness.B_EQ_D: {**good, "second": list(good["first"])},
        witness.FIRST_TRIPLE_NE_X: {**good, "first": [good["first"][0] + 1, good["first"][1]]},
        witness.XP_NE_Q: {**good, "n": _next_prime(good["n"])},
    }
    reasons = {}
    for expected, form in planted.items():
        verdict = witness.verify(form)
        if verdict.accepted or verdict.reason != expected:
            raise SelftestFailed("witness-arm", f"a witness planted for {expected} came back {verdict.reason}")
        reasons[expected] = 1
    return {"accepted": 1, "refused": reasons, "outcome": OUTCOME_PASS}


def rho_dp_run_once(config, *, doc=None, root=None):
    from cairn.skills import rho_dp

    lg = log.get(LOG_STEP)
    doc = selftest.load_corpus(CORPUS_PATHS[RHO_DP]) if doc is None else selftest.check_corpus(doc)
    seed = _instance_seed(_revision(rho_dp, root))
    records, ledger, passes = _dlp_cases(rho_dp, doc, lg)
    floor = doc["pass_floor"]
    if passes < floor:
        raise SelftestFailed("floor", f"{passes} passing cases is below the floor {floor}")
    curve, x, P, Q = _arm_instance(seed, LABEL_X[RHO_DP])
    out = rho_dp.run(ARM_BITS, seed, curve.p, curve.a, curve.b, curve.n, P, Q)
    rho_dp.check_postcondition(out)
    if out.x != x:
        raise SelftestFailed("postcondition-arm", f"the walk solved x = {out.x} for a drawn x = {x}")
    negation = rho_dp.run(ARM_BITS, seed, curve.p, curve.a, curve.b, curve.n, P, Q, True)
    rho_dp.check_postcondition(negation)
    if negation.x != x:
        raise SelftestFailed("postcondition-arm", f"the negation-map walk solved x = {negation.x} for x = {x}")
    arm_body = {
        "bits": ARM_BITS,
        "p": curve.p,
        "n": curve.n,
        "x": x,
        "plain": {"ops": out.ops, "distinguished_points": out.distinguished_points, "restarts": out.walk["restarts"]},
        "negation_map": {
            "ops": negation.ops,
            "distinguished_points": negation.distinguished_points,
            "fruitless_escapes": negation.walk["fruitless_escapes"],
        },
        "outcome": OUTCOME_PASS,
    }
    lg.info("arm", name="postcondition", seed=seed, observed=selftest._canonical_json(arm_body))
    records.append(("arm", "postcondition", arm_body))
    instance = verifier.Instance(curve.p, curve.a, curve.b, curve.n, P, Q)
    verifier_body = _verifier_arm(config, instance, out.x, _other_scalar(seed, curve.n, x, LABEL_X_PRIME[RHO_DP]))
    lg.info("arm", name="verifier", bundle_hash=config.bundle_hash, ok=1, fail=1, expected=1)
    records.append(("arm", "verifier", verifier_body))
    witness_body = _witness_arm(out)
    lg.info("arm", name="witness", observed=selftest._canonical_json(witness_body))
    records.append(("arm", "witness", witness_body))
    arms = {
        "postcondition": arm_body["outcome"],
        "verifier": {"ok": verifier_body["ok"], "fail": verifier_body["fail"]},
        "witness": {"accepted": witness_body["accepted"], "refused": len(witness_body["refused"])},
    }
    return _result(records, ledger, passes, floor, arms, seed, doc)


def bsgs_run_once(config, *, doc=None, root=None):
    from cairn.skills import bsgs

    lg = log.get(LOG_STEP)
    doc = selftest.load_corpus(CORPUS_PATHS[BSGS]) if doc is None else selftest.check_corpus(doc)
    seed = _instance_seed(_revision(bsgs, root))
    records, ledger, passes = _dlp_cases(bsgs, doc, lg)
    floor = doc["pass_floor"]
    if passes < floor:
        raise SelftestFailed("floor", f"{passes} passing cases is below the floor {floor}")
    curve, x, P, Q = _arm_instance(seed, LABEL_X[BSGS])
    out = bsgs.run(ARM_BITS, seed, curve.p, curve.a, curve.b, curve.n, P, Q)
    bsgs.check_postcondition(out)
    if out.x != x:
        raise SelftestFailed("postcondition-arm", f"the table solved x = {out.x} for a drawn x = {x}")
    arm_body = {
        "bits": ARM_BITS,
        "p": curve.p,
        "n": curve.n,
        "x": x,
        "ops": out.ops,
        "memory": dict(out.memory),
        "giant_steps": out.giant_steps,
        "outcome": OUTCOME_PASS,
    }
    lg.info("arm", name="postcondition", seed=seed, observed=selftest._canonical_json(arm_body))
    records.append(("arm", "postcondition", arm_body))
    instance = verifier.Instance(curve.p, curve.a, curve.b, curve.n, P, Q)
    verifier_body = _verifier_arm(config, instance, out.x, _other_scalar(seed, curve.n, x, LABEL_X_PRIME[BSGS]))
    lg.info("arm", name="verifier", bundle_hash=config.bundle_hash, ok=1, fail=1, expected=1)
    records.append(("arm", "verifier", verifier_body))
    arms = {
        "postcondition": arm_body["outcome"],
        "verifier": {"ok": verifier_body["ok"], "fail": verifier_body["fail"]},
    }
    return _result(records, ledger, passes, floor, arms, seed, doc)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_hex64(value):
    return isinstance(value, str) and len(value) == 64 and set(value) <= HEX_DIGITS


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


def _nonce_from(seed, label):
    material = canon.length_prefix(str(seed).encode("utf-8")) + canon.length_prefix(label)
    return canon.digest("cairn/selftest-nonce/v1", material)


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
    import dataclasses

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


def _result(records, ledger, passes, floor, arms, seed, doc):
    transcript = selftest.transcript_bytes(records)
    return {
        "records": records,
        "transcript": transcript,
        "transcript_hash": selftest.transcript_digest(transcript),
        "ledger": ledger,
        "passes": passes,
        "floor": floor,
        "arms": arms,
        "seed": seed,
        "origins": selftest.field_origins(doc),
    }


RUN_ONCE = {RHO_DP: rho_dp_run_once, BSGS: bsgs_run_once, INSTANCE_MAKER: instance_maker_run_once}


def run_once(which, config, *, doc=None, root=None):
    return RUN_ONCE[which](config, doc=doc, root=root)


def certify(sub, config, which, *, doc=None, root=None):
    module = module_for(which)
    first = run_once(which, config, doc=doc, root=root)
    second = run_once(which, config, doc=doc, root=root)
    if first["transcript"] != second["transcript"]:
        raise SelftestFailed(
            "double-run", f"transcript {first['transcript_hash']} differs from {second['transcript_hash']}"
        )
    identity = _identity(module, root)
    identity_hash = keys.identity_bundle_hash(identity)
    env_hash = keys.env_manifest_digest(env.manifest())
    transcript_hash = first["transcript_hash"]
    cert = selftest.certificate_hash(identity_hash, transcript_hash, env_hash)
    summary = {
        "corpus_origins": first["origins"],
        "randomized_arm": True,
        "cross_check": {"axis": module.CROSS_CHECK_AXIS, "independent_range": module.INDEPENDENT_RANGE},
        "pass": first["passes"],
        "floor": first["floor"],
        "must_fail_witnesses": first["arms"]["verifier"]["fail"],
    }
    existing = sub.get_certificate(identity_hash)
    if existing is not None:
        if existing["cert_hash"] != cert:
            raise SelftestFailed("certificate", f"recorded {existing['cert_hash']} differs from the minted {cert}")
        recorded = "present"
    else:
        if sub.get_node(identity_hash) is None:
            sub.put_identity_bundle(identity)
        sub.put_certificate(identity_hash, transcript_hash, env_hash, summary)
        recorded = "inserted"
    return {
        "identity_bundle_hash": identity_hash,
        "transcript_hash": transcript_hash,
        "env_manifest_hash": env_hash,
        "certificate": cert,
        "summary": summary,
        "records": first["records"],
        "transcript": first["transcript"],
        "passes": first["passes"],
        "floor": first["floor"],
        "arms": first["arms"],
        "seed": first["seed"],
        "recorded": recorded,
        "double_run": "byte-equal",
    }
