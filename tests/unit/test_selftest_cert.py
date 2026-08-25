import copy
import json
import re

import pytest

from cairn import selftest
from cairn.selftest import CorpusSchemaError

BASE = json.loads(selftest.CORPUS_PATH.read_text())


def _vector(doc, name):
    return next(v for v in doc["vectors"] if v["name"] == name)


def _cert(vector):
    field = vector["input"]
    return selftest.certificate_hash(
        field["identity_bundle_hash"],
        field["transcript_hash"],
        field["env_manifest_hash"],
    )


@pytest.mark.parametrize(
    ("case_index", "field_name"),
    [(0, "p"), (1, "P"), (2, "n"), (3, "Q")],
    ids=["F5.p", "GF101.P", "bits150.n", "negative_control.Q"],
)
def test_a_field_without_an_origin_is_refused_at_its_path(case_index, field_name):
    doc = copy.deepcopy(BASE)
    del doc["cases"][case_index]["fields"][field_name]["origin"]
    with pytest.raises(
        CorpusSchemaError, match=re.escape(f"$.cases[{case_index}].fields.{field_name}")
    ):
        selftest.check_corpus(doc)


@pytest.mark.parametrize("ledger", ["", "passed", "PASS", "known gap", "ok"])
def test_a_ledger_value_outside_the_three_is_refused(ledger):
    doc = copy.deepcopy(BASE)
    doc["cases"][0]["ledger"] = ledger
    with pytest.raises(CorpusSchemaError, match=re.escape("$.cases[0].ledger")):
        selftest.check_corpus(doc)


@pytest.mark.parametrize("ledger", selftest.LEDGER_VALUES)
def test_each_of_the_three_ledger_values_is_accepted(ledger):
    doc = copy.deepcopy(BASE)
    doc["cases"][0]["ledger"] = ledger
    assert selftest.check_corpus(doc) is doc


def test_certificate_composition_matches_the_committed_vector(load_vector):
    vector = _vector(load_vector("canon_kat.json"), "selftest_cert")
    assert _cert(vector) == vector["expected"]


def test_swapping_the_identity_hash_changes_the_certificate(load_vector):
    doc = load_vector("canon_kat.json")
    original, transplanted = (
        _vector(doc, "selftest_cert"),
        _vector(doc, "selftest_cert_transplanted"),
    )
    assert (
        original["input"]["transcript_hash"] == transplanted["input"]["transcript_hash"]
    )
    assert (
        original["input"]["env_manifest_hash"]
        == transplanted["input"]["env_manifest_hash"]
    )
    assert (
        original["input"]["identity_bundle_hash"]
        != transplanted["input"]["identity_bundle_hash"]
    )
    assert _cert(transplanted) == transplanted["expected"] != _cert(original)


@pytest.mark.parametrize(
    "swap",
    ["identity_bundle_hash", "transcript_hash", "env_manifest_hash"],
)
def test_every_certificate_field_is_load_bearing(load_vector, swap):
    field = dict(_vector(load_vector("canon_kat.json"), "selftest_cert")["input"])
    before = selftest.certificate_hash(**field)
    field[swap] = "ab" * 32
    assert selftest.certificate_hash(**field) != before


def test_arm_seed_is_stable_for_a_revision_and_moves_when_it_is_bumped():
    revision = "ab" * 32
    assert selftest.arm_seed(revision) == selftest.arm_seed(revision)
    assert selftest.arm_seed(revision) != selftest.arm_seed("ac" * 32)
    assert 0 <= selftest.arm_seed(revision) < 2**64


def test_transcript_bytes_are_the_concatenated_records_and_order_is_load_bearing():
    records = [
        ("case", "F5", {"ledger": "pass"}),
        ("arm", "postcondition", {"outcome": "pass"}),
    ]
    joined = selftest.transcript_bytes(records)
    assert [bytes.fromhex(line) for line in selftest.transcript_lines(records)] == [
        selftest.record_bytes(*r) for r in records
    ]
    assert selftest.transcript_digest(joined) != selftest.transcript_digest(
        selftest.transcript_bytes(list(reversed(records)))
    )


def test_transcript_digest_moves_when_one_observed_output_moves():
    records = [("case", "F5", {"n": 7})]
    before = selftest.transcript_digest(selftest.transcript_bytes(records))
    after = selftest.transcript_digest(
        selftest.transcript_bytes([("case", "F5", {"n": 8})])
    )
    assert before != after


@pytest.mark.parametrize(
    "text", ["{", "", "not json", '{"cases": [}', "[1, 2, 3"], ids=range(5)
)
def test_a_corpus_file_that_is_not_json_is_refused(tmp_path, text):
    path = tmp_path / "corpus.json"
    path.write_text(text)
    with pytest.raises(CorpusSchemaError, match="not valid JSON"):
        selftest.load_corpus(path)


def test_a_corpus_file_that_is_json_but_not_an_object_is_refused(tmp_path):
    path = tmp_path / "corpus.json"
    path.write_text("[1, 2, 3]")
    with pytest.raises(CorpusSchemaError, match=re.escape("$")):
        selftest.load_corpus(path)


def test_the_shipped_corpus_loads_from_its_committed_path():
    assert selftest.load_corpus() == selftest.load_corpus(selftest.CORPUS_PATH)
