import json
import os
from pathlib import Path

import blake3

from cairn import canon, cli, exits, keys, log
from cairn.canon import STR, Field, Struct
from cairn.errors import CliError

SCHEMA_VERSION = 1
CORPUS_PATH = Path(__file__).resolve().parent / "skills" / "toy_curve_corpus.json"
ORIGINS = ("upstream_vendored", "independent_oracle", "randomized_postcondition", "author_supplied")
LEDGER_VALUES = ("pass", "intentional_non_goal", "known_gap")
SCALAR_FIELDS = ("p", "a", "b", "n", "x")
POINT_FIELDS = ("P", "Q")
REQUIRED_FIELDS = ("p", "a", "b", "n", "P")
FIELD_KEYS = ("value", "origin")
CASE_KEYS = ("id", "ledger", "source", "postconditions", "fields")
POSTCONDITION_FIELDS = {
    "oncurve": ("P",),
    "ellorder": ("P", "n"),
    "ellmul": ("P", "x", "Q"),
    "ellcard": ("n",),
    "order_kills": ("P", "n"),
    "order_does_not_kill": ("Q", "n"),
}
POSTCONDITIONS = tuple(POSTCONDITION_FIELDS)


class CorpusSchemaError(ValueError):
    def __init__(self, path, what):
        self.path = path
        self.what = what
        super().__init__(f"{path}: {what}")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_field(path, name, field):
    if not isinstance(field, dict):
        raise CorpusSchemaError(path, f"field must be an object, got {type(field).__name__}")
    missing = [k for k in FIELD_KEYS if k not in field]
    if missing:
        raise CorpusSchemaError(path, f"field is missing {', '.join(missing)}")
    extra = sorted(set(field) - set(FIELD_KEYS))
    if extra:
        raise CorpusSchemaError(path, f"field has unknown keys {', '.join(extra)}")
    if field["origin"] not in ORIGINS:
        raise CorpusSchemaError(
            f"{path}.origin",
            f"origin must be one of {ORIGINS}, got {field['origin']!r}",
        )
    value = field["value"]
    if name in SCALAR_FIELDS:
        if not _is_int(value):
            raise CorpusSchemaError(
                f"{path}.value",
                f"{name} must be an integer, got {type(value).__name__}",
            )
        return
    if not isinstance(value, list) or len(value) != 2 or not all(_is_int(v) for v in value):
        raise CorpusSchemaError(f"{path}.value", f"{name} must be a pair of integers, got {value!r}")


def _check_case(index, case, seen_ids):
    path = f"$.cases[{index}]"
    if not isinstance(case, dict):
        raise CorpusSchemaError(path, f"case must be an object, got {type(case).__name__}")
    missing = [k for k in CASE_KEYS if k not in case]
    if missing:
        raise CorpusSchemaError(path, f"case is missing {', '.join(missing)}")
    case_id = case["id"]
    if not isinstance(case_id, str) or not case_id:
        raise CorpusSchemaError(f"{path}.id", "id must be a non-empty string")
    if case_id in seen_ids:
        raise CorpusSchemaError(f"{path}.id", f"duplicate case id {case_id!r}")
    seen_ids.add(case_id)
    if case["ledger"] not in LEDGER_VALUES:
        raise CorpusSchemaError(
            f"{path}.ledger",
            f"ledger must be one of {LEDGER_VALUES}, got {case['ledger']!r}",
        )
    if not isinstance(case["source"], str) or not case["source"]:
        raise CorpusSchemaError(f"{path}.source", "source must be a non-empty string")
    postconditions = case["postconditions"]
    if (
        not isinstance(postconditions, list)
        or not postconditions
        or not all(isinstance(v, str) and v for v in postconditions)
    ):
        raise CorpusSchemaError(
            f"{path}.postconditions",
            "postconditions must be a non-empty list of non-empty strings",
        )
    fields = case["fields"]
    if not isinstance(fields, dict):
        raise CorpusSchemaError(f"{path}.fields", f"fields must be an object, got {type(fields).__name__}")
    unknown = sorted(set(fields) - set(SCALAR_FIELDS) - set(POINT_FIELDS))
    if unknown:
        raise CorpusSchemaError(f"{path}.fields", f"unknown fields {', '.join(unknown)}")
    absent = [k for k in REQUIRED_FIELDS if k not in fields]
    if absent:
        raise CorpusSchemaError(f"{path}.fields", f"missing required fields {', '.join(absent)}")
    for name in sorted(fields):
        _check_field(f"{path}.fields.{name}", name, fields[name])
    for name, floor in (("p", 2), ("n", 1)):
        value = fields[name]["value"]
        if value < floor:
            raise CorpusSchemaError(f"{path}.fields.{name}.value", f"{name} must be >= {floor}, got {value}")
    for name in postconditions:
        needed = POSTCONDITION_FIELDS.get(name)
        if needed is None:
            raise CorpusSchemaError(f"{path}.postconditions", f"unknown postcondition {name!r}")
        lacking = [k for k in needed if k not in fields]
        if lacking:
            raise CorpusSchemaError(
                f"{path}.postconditions",
                f"{name} needs fields {', '.join(lacking)}",
            )


def _cases_to_check(cases):
    return list(enumerate(cases))


def _check_floor(floor, count):
    if not _is_int(floor):
        raise CorpusSchemaError("$.pass_floor", f"pass_floor must be an integer, got {type(floor).__name__}")
    if floor < 0 or floor > count:
        raise CorpusSchemaError("$.pass_floor", f"pass_floor must be within [0, {count}], got {floor}")


def check_corpus(doc):
    if not isinstance(doc, dict):
        raise CorpusSchemaError("$", f"corpus must be an object, got {type(doc).__name__}")
    missing = [k for k in ("schema_version", "pass_floor", "cases") if k not in doc]
    if missing:
        raise CorpusSchemaError("$", f"corpus is missing {', '.join(missing)}")
    if doc["schema_version"] != SCHEMA_VERSION:
        raise CorpusSchemaError(
            "$.schema_version",
            f"schema_version must be {SCHEMA_VERSION}, got {doc['schema_version']!r}",
        )
    cases = doc["cases"]
    if not isinstance(cases, list) or not cases:
        raise CorpusSchemaError("$.cases", "cases must be a non-empty list")
    seen_ids = set()
    for index, case in _cases_to_check(cases):
        _check_case(index, case, seen_ids)
    _check_floor(doc["pass_floor"], len(cases))
    return doc


def load_corpus(path=CORPUS_PATH):
    try:
        doc = json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise CorpusSchemaError("$", f"corpus is not valid JSON: {exc}") from None
    return check_corpus(doc)


def field_origins(doc):
    return {
        case["id"]: {name: field["origin"] for name, field in sorted(case["fields"].items())} for case in doc["cases"]
    }


TAG_TRANSCRIPT = "cairn/selftest-transcript/v1"
SEED_LABEL = b"selftest-seed"
LOG_STEP = "selftest"
RECORD = Struct(
    "selftest_record",
    [Field("kind", STR), Field("id", STR), Field("body", STR)],
)


def _canonical_json(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def record_bytes(kind, record_id, body):
    return canon.encode(RECORD, {"kind": kind, "id": record_id, "body": _canonical_json(body)})


def transcript_bytes(records):
    return b"".join(record_bytes(*record) for record in records)


def transcript_digest(transcript):
    return canon.digest(TAG_TRANSCRIPT, transcript)


def transcript_lines(records):
    return [record_bytes(*record).hex() for record in records]


def arm_seed(implementation_revision):
    material = canon.length_prefix(implementation_revision.encode("utf-8")) + canon.length_prefix(SEED_LABEL)
    return int.from_bytes(blake3.blake3(material).digest()[:8], "big")


def certificate_hash(identity_bundle_hash, transcript_hash, env_manifest_hash):
    return keys.selftest_cert_hash(
        {
            "identity_bundle_hash": identity_bundle_hash,
            "transcript_hash": transcript_hash,
            "env_manifest_hash": env_manifest_hash,
        }
    )


DRAW_COUNT = 20
ARM_BITS = 30


class SelftestFailed(Exception):
    def __init__(self, what, detail):
        self.what = what
        self.detail = detail
        super().__init__(f"{what}: {detail}")


def _values(case):
    return {name: field["value"] for name, field in case["fields"].items()}


def _point(value):
    return [int(c) for c in value]


def _is_identity(value):
    return len(value) == 1


def _evaluate(name, E, v):
    from cairn import pari

    if name == "oncurve":
        points = {"P": bool(pari.pari.ellisoncurve(E, _point(v["P"])))}
        if "Q" in v:
            points["Q"] = bool(pari.pari.ellisoncurve(E, _point(v["Q"])))
        return points, all(points.values())
    if name == "ellorder":
        observed = int(pari.ellorder(E, _point(v["P"])))
        return observed, observed == v["n"]
    if name == "ellmul":
        observed = _point(pari.pari.ellmul(E, _point(v["P"]), v["x"]))
        return observed, observed == _point(v["Q"])
    if name == "ellcard":
        observed = int(pari.ellcard(E))
        return observed, observed == v["n"]
    if name == "order_kills":
        observed = _point(pari.pari.ellmul(E, _point(v["P"]), v["n"]))
        return observed, _is_identity(observed)
    observed = _point(pari.pari.ellmul(E, _point(v["Q"]), v["n"]))
    return observed, not _is_identity(observed)


def run_case(case):
    from cairn import pari

    v = _values(case)
    E = pari.pari.ellinit([v["a"], v["b"]], v["p"])
    observed = {}
    held = {}
    for name in case["postconditions"]:
        observed[name], held[name] = _evaluate(name, E, v)
    return observed, all(held.values()), held


def _draws(seed, bound, count, label):
    values = []
    counter = 0
    while len(values) < count:
        material = (
            canon.length_prefix(str(seed).encode("utf-8")) + canon.length_prefix(label) + counter.to_bytes(8, "big")
        )
        value = int.from_bytes(blake3.blake3(material).digest(), "big") % bound
        if value >= 1:
            values.append(value)
        counter += 1
    return values


def postcondition_arm(seed):
    from cairn.skills import toy_curve

    out = toy_curve.run(ARM_BITS, seed)
    toy_curve.check_postcondition(out)
    body = {
        "bits": out.bits,
        "p": out.p,
        "a": out.a,
        "b": out.b,
        "n": out.n,
        "P": list(out.P),
        "cross_check": out.cross_check["result"],
        "status": out.status,
        "outcome": "pass",
    }
    return out, body


def verifier_arm(out, config, seed):
    from cairn import pari, verifier

    E = pari.pari.ellinit([out.a, out.b], out.p)
    driver = verifier.Verifier(config)
    right = _draws(seed, out.n, DRAW_COUNT, b"verifier-x")
    wrong = _draws(seed, out.n, DRAW_COUNT, b"verifier-x-prime")
    ok = 0
    failed = 0
    reasons = {}
    for index, x in enumerate(right):
        Q = tuple(_point(pari.pari.ellmul(E, list(out.P), x)))
        instance = verifier.Instance(out.p, out.a, out.b, out.n, tuple(out.P), Q)
        if driver.run(instance, x).accepted:
            ok += 1
        else:
            raise SelftestFailed("verifier-arm", f"draw {index} with Q = xP was refused")
        other = wrong[index]
        if other == x:
            other = x % (out.n - 1) + 1
        result = driver.run(instance, other)
        if result.accepted:
            raise SelftestFailed("verifier-arm", f"draw {index} with x' != x was accepted")
        failed += 1
        reasons[result.reason] = reasons.get(result.reason, 0) + 1
    if reasons != {"xP-ne-Q": DRAW_COUNT}:
        raise SelftestFailed("verifier-arm", f"unexpected refusal reasons {reasons}")
    return {"ok": ok, "fail": failed, "reasons": reasons, "outcome": "pass"}


def run_once(config, *, doc=None, root=None):
    from cairn.skills import toy_curve

    lg = log.get(LOG_STEP)
    doc = load_corpus() if doc is None else check_corpus(doc)
    revision = toy_curve.implementation_revision() if root is None else toy_curve.implementation_revision(root)
    seed = arm_seed(revision) or 1
    records = []
    ledger = {}
    passes = 0
    for case in doc["cases"]:
        observed, held_all, held = run_case(case)
        declared = case["ledger"]
        if declared == "pass" and not held_all:
            broken = sorted(name for name, value in held.items() if not value)
            raise SelftestFailed(
                "ledger",
                f"case {case['id']} declares pass but {', '.join(broken)} failed",
            )
        if declared == "pass":
            passes += 1
        ledger[case["id"]] = declared
        lg.info(
            "case",
            id=case["id"],
            ledger=declared,
            observed=_canonical_json(observed),
            expected=_canonical_json(_values(case)),
            held=_canonical_json(held),
        )
        records.append(("case", case["id"], {"ledger": declared, "observed": observed}))
    floor = doc["pass_floor"]
    if passes < floor:
        raise SelftestFailed("floor", f"{passes} passing cases is below the floor {floor}")
    out, arm_body = postcondition_arm(seed)
    lg.info("arm", name="postcondition", seed=seed, observed=_canonical_json(arm_body))
    records.append(("arm", "postcondition", arm_body))
    verifier_body = verifier_arm(out, config, seed)
    lg.info(
        "arm",
        name="verifier",
        bundle_hash=config.bundle_hash,
        ok=verifier_body["ok"],
        fail=verifier_body["fail"],
        expected=DRAW_COUNT,
    )
    records.append(("arm", "verifier", verifier_body))
    transcript = transcript_bytes(records)
    arms = {
        "postcondition": arm_body["outcome"],
        "verifier": {"ok": verifier_body["ok"], "fail": verifier_body["fail"]},
    }
    return {
        "records": records,
        "transcript": transcript,
        "transcript_hash": transcript_digest(transcript),
        "ledger": ledger,
        "passes": passes,
        "floor": floor,
        "arms": arms,
        "seed": seed,
        "origins": field_origins(doc),
    }


def certify(sub, config, *, doc=None, root=None):
    from cairn import env
    from cairn.skills import toy_curve

    first = run_once(config, doc=doc, root=root)
    second = run_once(config, doc=doc, root=root)
    if first["transcript"] != second["transcript"]:
        raise SelftestFailed(
            "double-run",
            f"transcript {first['transcript_hash']} differs from {second['transcript_hash']}",
        )
    identity = toy_curve.identity_bundle() if root is None else toy_curve.identity_bundle(root)
    identity_hash = keys.identity_bundle_hash(identity)
    env_hash = keys.env_manifest_digest(env.manifest())
    transcript_hash = first["transcript_hash"]
    cert = certificate_hash(identity_hash, transcript_hash, env_hash)
    summary = {
        "corpus_origins": first["origins"],
        "randomized_arm": True,
        "cross_check": {
            "axis": toy_curve.CROSS_CHECK_AXIS,
            "independent_range": toy_curve.INDEPENDENT_RANGE,
        },
        "pass": first["passes"],
        "floor": first["floor"],
    }
    existing = sub.get_certificate(identity_hash)
    if existing is not None:
        if existing["cert_hash"] != cert:
            raise SelftestFailed(
                "certificate",
                f"recorded {existing['cert_hash']} differs from the minted {cert}",
            )
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


def _configure(parser):
    parser.add_argument("which", nargs="?", default="toy-curve", choices=["toy-curve"])


def _run(ns):
    from cairn import bundle, substrate
    from cairn.skills import toy_curve

    gate = bundle.open_or_refuse(ns, command="cairn selftest toy-curve")
    debug = f"cairn selftest {ns.which} --db {ns.db} --bundle {ns.bundle} --pin {ns.pin} --log DEBUG"
    # Path.resolve() would follow the /var symlink and create the directory off the db's own path
    parent = Path(os.path.abspath(ns.db)).parent  # noqa: PTH100
    parent.mkdir(parents=True, exist_ok=True)
    try:
        with substrate.Substrate.open(ns.db) as sub:
            result = certify(sub, gate.verifier_config())
    except CorpusSchemaError as exc:
        raise CliError(
            exits.USER_INPUT,
            f"the toy_curve corpus is malformed at {exc.path}: {exc.what}",
            where=str(CORPUS_PATH),
            next_command=debug,
        ) from None
    except (SelftestFailed, toy_curve.PostconditionFailed) as exc:
        raise CliError(
            exits.GATE_REFUSED,
            f"the toy_curve self-test failed ({exc})",
            where=str(CORPUS_PATH),
            next_command=debug,
        ) from None
    payload = {
        "which": ns.which,
        "pass": result["passes"],
        "floor": result["floor"],
        "arms": result["arms"],
        "certificate": result["certificate"],
        "bundle": gate.hash,
        "identity_bundle_hash": result["identity_bundle_hash"],
        "transcript_hash": result["transcript_hash"],
        "recorded": result["recorded"],
        "double_run": result["double_run"],
    }
    if getattr(ns, "json", False):
        cli.emit_json("selftest", payload)
    else:
        print(result["certificate"])
    return exits.OK


cli.register(
    "selftest",
    _configure,
    _run,
    summary="run a skill's vendored known-answer corpus and record its certificate; exit 2 on any failure",
    read_only=False,
    json=True,
    aliases=("self-test",),
)
