"""The §2 self-test for the M1 baseline skills: rho_dp, bsgs and the instance-maker.

Each skill runs its vendored corpus under a pinned case seed, then a
randomized_postcondition arm keyed on H(implementation_revision || label): a
fresh instance from toy_curve, the skill's own answer checked end to end, a
wrong answer refused by the Tier-0 verifier, and for rho_dp the witness refused
in each planted form by the gate-side witness verifier. The certificate binds the
identity, the digest of the canonical transcript, the environment and the summary
the standing rules read, and a double run must be byte-equal.
"""

from cairn import ec, env, keys, log, selftest, verifier, witness
from cairn.selftest import SelftestFailed
from cairn.selftest_common import (
    ARM_BITS,
    BSGS,
    CASE_SEED,
    CORPUS_PATHS,
    HEX_DIGITS,
    INSTANCE_MAKER,
    LABEL_HYPOTHESIS,
    LABEL_NONCE,
    LABEL_X,
    LABEL_X_PRIME,
    LOG_STEP,
    MAKER_CASE_KEYS,
    MAKER_INSTANCE_FIELDS,
    MAKER_VECTOR_FIELDS,
    MODULES,
    NAMES,
    OUTCOME_PASS,
    OUTCOME_REFUSED,
    OUTCOME_WRONG,
    REPO_ROOT,
    RHO_DP,
    SKILLS_DIR,
    SLOPE_WEIGHT_A,
    SLOPE_WEIGHT_B,
    _identity,
    _instance_seed,
    _is_hex64,
    _is_int,
    _nonce_from,
    _other_scalar,
    _result,
    _revision,
    _values,
    _verifier_arm,
    module_for,
)
from cairn.selftest_maker import (
    _check_vector_field,
    _run_maker_case,
    check_maker_corpus,
    instance_maker_run_once,
    load_maker_corpus,
)
from cairn.selftest_slope import (
    _slope_decision_arm,
    _slope_run_once,
    check_slope_corpus,
    load_slope_corpus,
    slope_weight_a_run_once,
    slope_weight_b_run_once,
)

__all__ = [
    "HEX_DIGITS",
    "LABEL_HYPOTHESIS",
    "LABEL_NONCE",
    "MAKER_CASE_KEYS",
    "MAKER_INSTANCE_FIELDS",
    "MAKER_VECTOR_FIELDS",
    "MODULES",
    "OUTCOME_REFUSED",
    "OUTCOME_WRONG",
    "REPO_ROOT",
    "SKILLS_DIR",
    "_check_vector_field",
    "_is_hex64",
    "_is_int",
    "_nonce_from",
    "_run_maker_case",
    "_slope_decision_arm",
    "_slope_run_once",
    "check_maker_corpus",
    "check_slope_corpus",
    "load_maker_corpus",
    "load_slope_corpus",
]


def postcondition_errors():
    from cairn.skills import toy_curve

    return (toy_curve.PostconditionFailed, *(module_for(which).PostconditionFailed for which in NAMES))


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


RUN_ONCE = {
    RHO_DP: rho_dp_run_once,
    BSGS: bsgs_run_once,
    INSTANCE_MAKER: instance_maker_run_once,
    SLOPE_WEIGHT_A: slope_weight_a_run_once,
    SLOPE_WEIGHT_B: slope_weight_b_run_once,
}


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
    summary = {
        "corpus_origins": first["origins"],
        "randomized_arm": True,
        "cross_check": selftest.cross_check_summary(module),
        "pass": first["passes"],
        "floor": first["floor"],
        "must_fail_witnesses": first["arms"]["verifier"]["fail"],
    }
    cert = selftest.certificate_hash(identity_hash, transcript_hash, env_hash, summary)
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
