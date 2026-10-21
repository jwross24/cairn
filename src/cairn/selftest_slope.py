import json
import os
import subprocess
import sys
from pathlib import Path

from cairn import canon, log, selftest
from cairn.selftest import SelftestFailed
from cairn.selftest_common import (
    CORPUS_PATHS,
    LOG_STEP,
    OUTCOME_PASS,
    OUTCOME_REFUSED,
    OUTCOME_WRONG,
    REPO_ROOT,
    SLOPE_WEIGHT_A,
    SLOPE_WEIGHT_B,
    _instance_seed,
    _is_int,
    _nonce_from,
    _result,
    _revision,
    _values,
    module_for,
)


def check_slope_corpus(doc):
    if not isinstance(doc, dict) or set(doc) != {"schema_version", "pass_floor", "cases"}:
        raise selftest.CorpusSchemaError("$", "corpus must hold exactly schema_version, pass_floor and cases")
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise selftest.CorpusSchemaError("$.schema_version", "schema_version must be 1")
    cases = doc["cases"]
    if not isinstance(cases, list) or not cases:
        raise selftest.CorpusSchemaError("$.cases", "cases must be a non-empty list")
    seen = set()
    for index, case in enumerate(cases):
        path = f"$.cases[{index}]"
        if not isinstance(case, dict) or set(case) != {"id", "ledger", "source", "fields"}:
            raise selftest.CorpusSchemaError(path, "case must hold exactly id, ledger, source and fields")
        if not isinstance(case["id"], str) or not case["id"] or case["id"] in seen:
            raise selftest.CorpusSchemaError(f"{path}.id", "id must be a unique non-empty string")
        seen.add(case["id"])
        if case["ledger"] not in selftest.LEDGER_VALUES:
            raise selftest.CorpusSchemaError(f"{path}.ledger", "unknown ledger value")
        if not isinstance(case["source"], str) or not case["source"]:
            raise selftest.CorpusSchemaError(f"{path}.source", "source must be a non-empty string")
        fields = case["fields"]
        if not isinstance(fields, dict) or set(fields) != {"l", "n", "W"}:
            raise selftest.CorpusSchemaError(f"{path}.fields", "fields must hold exactly l, n and W")
        for name, field in fields.items():
            field_path = f"{path}.fields.{name}"
            if not isinstance(field, dict) or set(field) != set(selftest.FIELD_KEYS):
                raise selftest.CorpusSchemaError(field_path, "field must hold exactly value and origin")
            if field["origin"] not in selftest.ORIGINS:
                raise selftest.CorpusSchemaError(f"{field_path}.origin", "unknown field origin")
            if not _is_int(field["value"]):
                raise selftest.CorpusSchemaError(f"{field_path}.value", "value must be an integer")
        values = _values(case)
        if not 3 <= values["l"] <= 2**22 or not 1 <= values["n"] <= values["l"] - 2 or values["W"] < 0:
            raise selftest.CorpusSchemaError(f"{path}.fields", "l, n or W is outside the evaluator's range")
    selftest._check_floor(doc["pass_floor"], len(cases))
    return doc


def load_slope_corpus(which, path=None):
    path = CORPUS_PATHS[which] if path is None else path
    try:
        doc = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise selftest.CorpusSchemaError("$", f"corpus is not valid JSON: {exc}") from None
    return check_slope_corpus(doc)


def _slope_decision_arm(seed, ell, weight):
    from cairn.skills import slope_weight_a, slope_weight_b
    from cairn.slopemodel import slope_hunt_executor

    child_env = {**os.environ, "PYTHONPATH": str(REPO_ROOT / "src"), "PYTHONSAFEPATH": "1"}
    records = []
    for name, predicate, expected in (
        ("holding", {"kind": "weight_ge_counting_bound"}, False),
        ("holding_weight_le", {"kind": "weight_le", "num": 10, "den": 1}, False),
        ("failing", {"kind": "weight_le", "num": 0, "den": 1}, True),
    ):
        document = {
            "statement_hash": _nonce_from(seed, name.encode()),
            "plan_hash": _nonce_from(seed, b"slope-hunt-plan"),
            "run_id": f"slope-selftest-{name}",
            "trial": 0,
            "point": {"t": ell},
            "seed": seed,
            "input_blob_hash": _nonce_from(seed, b"slope-hunt-input"),
            "predicate": predicate,
        }
        observations = {}
        for role, module, decision in (
            ("executor", slope_weight_a.HUNT_MODULE, "candidate"),
            ("verifier", slope_weight_b.HUNT_MODULE, "counterexample_valid"),
        ):
            completed = subprocess.run(
                [sys.executable, "-m", module],
                input=selftest._canonical_json(document),
                capture_output=True,
                text=True,
                timeout=60,
                env=child_env,
            )
            if completed.returncode != 0:
                raise SelftestFailed(f"hunt-{role}-arm", f"the {name} statement exited {completed.returncode}")
            try:
                output = json.loads(completed.stdout)
            except json.JSONDecodeError:
                raise SelftestFailed(f"hunt-{role}-arm", f"the {name} statement returned malformed JSON") from None
            if (
                not isinstance(output, dict)
                or any(output.get(field) != document[field] for field in slope_hunt_executor.BINDING)
                or output.get("status") != "OK"
                or output.get("l") != ell
                or output.get("weight") != weight
            ):
                raise SelftestFailed(f"hunt-{role}-arm", f"the {name} statement returned mismatched binding or result")
            if role == "verifier" and output.get("executor_output_digest") != document["executor_output_digest"]:
                raise SelftestFailed("hunt-verifier-arm", f"the {name} statement returned mismatched executor digest")
            observed = output.get(decision)
            if type(observed) is not bool or observed is not expected:
                raise SelftestFailed(
                    f"hunt-{role}-arm", f"the {name} statement returned {decision}={observed}, expected {expected}"
                )
            observations[decision] = observed
            if role == "executor":
                document["executor_output_digest"] = canon.digest(
                    "cairn/selftest-slope-executor/v1", completed.stdout.encode()
                )
        records.append({"id": name, "predicate": predicate, **observations})
    return records


def _slope_run_once(which, _config, *, doc=None, root=None):
    from cairn.slopemodel import slope_hunt_verifier, slope_predicates, slopemodel_b

    module = module_for(which)
    peer = module_for(SLOPE_WEIGHT_B if which == SLOPE_WEIGHT_A else SLOPE_WEIGHT_A)
    lg = log.get(LOG_STEP)
    doc = load_slope_corpus(which) if doc is None else check_slope_corpus(doc)
    seed = _instance_seed(_revision(module, root))
    records, ledger, passes = [], {}, 0
    for case in doc["cases"]:
        values = _values(case)
        try:
            output = module.run(values["l"], values["n"])
        except module.InputError as exc:
            body = {"outcome": OUTCOME_REFUSED, "reason": str(exc)}
        else:
            body = {**output, "outcome": OUTCOME_PASS if output["weight"] == values["W"] else OUTCOME_WRONG}
        if case["ledger"] == "pass":
            if body["outcome"] != OUTCOME_PASS:
                raise SelftestFailed("ledger", f"case {case['id']} declares pass but the evaluator reported {body}")
            passes += 1
        ledger[case["id"]] = case["ledger"]
        records.append(("case", case["id"], {"ledger": case["ledger"], "observed": body}))
        lg.info("case", id=case["id"], ledger=case["ledger"], observed=selftest._canonical_json(body))
    floor = doc["pass_floor"]
    if passes < floor:
        raise SelftestFailed("floor", f"{passes} passing cases is below the floor {floor}")
    ell = slopemodel_b.next_prime(257 + seed % 4096)
    n = slope_predicates.step_size(ell)
    if n != slope_hunt_verifier.step_size(ell):
        raise SelftestFailed("postcondition-arm", "the independent step-size rules disagree")
    output, independent = module.run(ell, n), peer.run(ell, n)
    if output != independent:
        raise SelftestFailed("postcondition-arm", f"independent evaluators disagree: {output} != {independent}")
    arm_body = {**output, "independent_match": True, "outcome": OUTCOME_PASS}
    records.append(("arm", "postcondition", arm_body))
    lg.info("arm", name="postcondition", seed=seed, observed=selftest._canonical_json(arm_body))
    try:
        module.check_weight(65537, 146, 20644183)
    except (module.InputError, module.PostconditionFailed) as exc:
        raise SelftestFailed("verifier-arm", f"the published weight was refused: {exc}") from None
    try:
        module.check_weight(65537, 145, 20644183)
    except module.PostconditionFailed:
        pass
    else:
        raise SelftestFailed("verifier-arm", "the planted weight 20644183 at (65537, 145) was accepted")
    decisions = _slope_decision_arm(seed, ell, output["weight"])
    ok = sum(record["counterexample_valid"] for record in decisions)
    fail = sum(not record["counterexample_valid"] for record in decisions)
    verifier_body = {
        "ok": ok,
        "fail": fail,
        "planted": {"l": 65537, "n": 145, "W": 20644183},
        "decisions": decisions,
        "outcome": OUTCOME_PASS,
    }
    records.append(("arm", "verifier", verifier_body))
    lg.info("arm", name="verifier", observed=selftest._canonical_json(verifier_body))
    arms = {
        "postcondition": OUTCOME_PASS,
        "executor": {
            "candidate": sum(record["candidate"] for record in decisions),
            "non_candidate": sum(not record["candidate"] for record in decisions),
        },
        "verifier": {"ok": ok, "fail": fail},
    }
    return _result(records, ledger, passes, floor, arms, seed, doc)


def slope_weight_a_run_once(config, *, doc=None, root=None):
    return _slope_run_once(SLOPE_WEIGHT_A, config, doc=doc, root=root)


def slope_weight_b_run_once(config, *, doc=None, root=None):
    return _slope_run_once(SLOPE_WEIGHT_B, config, doc=doc, root=root)
