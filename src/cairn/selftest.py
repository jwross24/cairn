import json
from pathlib import Path

import blake3

from cairn import canon, keys
from cairn.canon import STR, Field, Struct

SCHEMA_VERSION = 1
CORPUS_PATH = Path(__file__).resolve().parent / "skills" / "toy_curve_corpus.json"
ORIGINS = ("upstream_vendored", "author_supplied", "randomized_postcondition")
LEDGER_VALUES = ("pass", "intentional_non_goal", "known_gap")
SCALAR_FIELDS = ("p", "a", "b", "n", "x")
POINT_FIELDS = ("P", "Q")
REQUIRED_FIELDS = ("p", "a", "b", "n", "P")
FIELD_KEYS = ("value", "origin")
CASE_KEYS = ("id", "ledger", "source", "postconditions", "fields")


class CorpusSchemaError(ValueError):
    def __init__(self, path, what):
        self.path = path
        self.what = what
        super().__init__(f"{path}: {what}")


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _check_field(path, name, field):
    if not isinstance(field, dict):
        raise CorpusSchemaError(
            path, f"field must be an object, got {type(field).__name__}"
        )
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
    if (
        not isinstance(value, list)
        or len(value) != 2
        or not all(_is_int(v) for v in value)
    ):
        raise CorpusSchemaError(
            f"{path}.value", f"{name} must be a pair of integers, got {value!r}"
        )


def _check_case(index, case, seen_ids):
    path = f"$.cases[{index}]"
    if not isinstance(case, dict):
        raise CorpusSchemaError(
            path, f"case must be an object, got {type(case).__name__}"
        )
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
        raise CorpusSchemaError(
            f"{path}.fields", f"fields must be an object, got {type(fields).__name__}"
        )
    unknown = sorted(set(fields) - set(SCALAR_FIELDS) - set(POINT_FIELDS))
    if unknown:
        raise CorpusSchemaError(
            f"{path}.fields", f"unknown fields {', '.join(unknown)}"
        )
    absent = [k for k in REQUIRED_FIELDS if k not in fields]
    if absent:
        raise CorpusSchemaError(
            f"{path}.fields", f"missing required fields {', '.join(absent)}"
        )
    for name in sorted(fields):
        _check_field(f"{path}.fields.{name}", name, fields[name])


def _cases_to_check(cases):
    return list(enumerate(cases))


def _check_floor(floor, count):
    if not _is_int(floor):
        raise CorpusSchemaError(
            "$.pass_floor", f"pass_floor must be an integer, got {type(floor).__name__}"
        )
    if floor < 0 or floor > count:
        raise CorpusSchemaError(
            "$.pass_floor", f"pass_floor must be within [0, {count}], got {floor}"
        )


def check_corpus(doc):
    if not isinstance(doc, dict):
        raise CorpusSchemaError(
            "$", f"corpus must be an object, got {type(doc).__name__}"
        )
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
        case["id"]: {
            name: field["origin"] for name, field in sorted(case["fields"].items())
        }
        for case in doc["cases"]
    }


TAG_TRANSCRIPT = "cairn/selftest-transcript/v1"
SEED_LABEL = b"selftest-seed"
RECORD = Struct(
    "selftest_record",
    [Field("kind", STR), Field("id", STR), Field("body", STR)],
)


def _canonical_json(body):
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def record_bytes(kind, record_id, body):
    return canon.encode(
        RECORD, {"kind": kind, "id": record_id, "body": _canonical_json(body)}
    )


def transcript_bytes(records):
    return b"".join(record_bytes(*record) for record in records)


def transcript_digest(transcript):
    return canon.digest(TAG_TRANSCRIPT, transcript)


def transcript_lines(records):
    return [record_bytes(*record).hex() for record in records]


def arm_seed(implementation_revision):
    material = canon.length_prefix(
        implementation_revision.encode("utf-8")
    ) + canon.length_prefix(SEED_LABEL)
    return int.from_bytes(blake3.blake3(material).digest()[:8], "big")


def certificate_hash(identity_bundle_hash, transcript_hash, env_manifest_hash):
    return keys.selftest_cert_hash(
        {
            "identity_bundle_hash": identity_bundle_hash,
            "transcript_hash": transcript_hash,
            "env_manifest_hash": env_manifest_hash,
        }
    )
