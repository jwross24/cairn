import copy
import json
import re
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from cairn import pari, selftest
from cairn.selftest import CorpusSchemaError

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import selftest_mutants

CORPUS = Path(__file__).resolve().parent.parent / "fuzz_corpus" / "selftest_corpus"
BASE = json.loads(selftest.CORPUS_PATH.read_text())
fixture_ok = settings(
    deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture]
)

leaves = (
    st.none()
    | st.booleans()
    | st.integers()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.text()
)
json_values = st.recursive(
    leaves,
    lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(), c, max_size=4),
    max_leaves=12,
)


def _unknown_field(name):
    return name not in selftest.SCALAR_FIELDS and name not in selftest.POINT_FIELDS


non_integers = (
    st.text()
    | st.none()
    | st.booleans()
    | st.floats(allow_nan=False, allow_infinity=False)
    | st.lists(st.integers(), max_size=3)
)


@pytest.fixture
def pari_spy(monkeypatch):
    calls = []
    for name in ("ellcard", "ellsea", "ellorder"):
        real = getattr(pari, name)
        monkeypatch.setattr(
            pari,
            name,
            lambda *a, _n=name, _r=real, **k: (calls.append(_n), _r(*a, **k))[1],
        )
    return calls


def _seed_corpus():
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(CORPUS.glob("corpus_*.json"))
    ]


def _replay_seeds(fn):
    for case in _seed_corpus():
        fn = example(doc=case["doc"])(fn)
    return fn


MUTATION_KINDS = [
    "drop_origin",
    "unknown_origin",
    "bad_ledger",
    "floor_above",
    "floor_negative",
    "floor_not_int",
    "duplicate_id",
    "empty_cases",
    "drop_required_field",
    "unknown_postcondition",
    "postcondition_missing_field",
    "bad_scalar_type",
    "bad_point_shape",
    "extra_field_key",
    "field_not_object",
    "case_not_object",
    "drop_case_key",
    "empty_id",
    "empty_postconditions",
    "fields_not_object",
    "unknown_field_name",
    "bad_schema_version",
    "degenerate_modulus",
    "degenerate_order",
]


@st.composite
def mutated_corpus(draw):
    doc = copy.deepcopy(BASE)
    cases = doc["cases"]
    pick = lambda: cases[draw(st.integers(0, len(cases) - 1))]  # noqa: E731
    kind = draw(st.sampled_from(MUTATION_KINDS))
    if kind == "drop_origin":
        case = pick()
        del case["fields"][draw(st.sampled_from(sorted(case["fields"])))]["origin"]
    elif kind == "unknown_origin":
        case = pick()
        case["fields"][draw(st.sampled_from(sorted(case["fields"])))]["origin"] = draw(
            st.text().filter(lambda t: t not in selftest.ORIGINS)
        )
    elif kind == "bad_ledger":
        pick()["ledger"] = draw(
            st.text().filter(lambda t: t not in selftest.LEDGER_VALUES)
        )
    elif kind == "floor_above":
        doc["pass_floor"] = draw(st.integers(len(cases) + 1, len(cases) + 50))
    elif kind == "floor_negative":
        doc["pass_floor"] = draw(st.integers(-50, -1))
    elif kind == "floor_not_int":
        doc["pass_floor"] = draw(non_integers)
    elif kind == "duplicate_id":
        cases.append(copy.deepcopy(pick()))
    elif kind == "empty_cases":
        doc["cases"] = []
    elif kind == "drop_required_field":
        case = pick()
        del case["fields"][draw(st.sampled_from(list(selftest.REQUIRED_FIELDS)))]
    elif kind == "unknown_postcondition":
        pick()["postconditions"] = [
            draw(st.text(min_size=1).filter(lambda t: t not in selftest.POSTCONDITIONS))
        ]
    elif kind == "postcondition_missing_field":
        case = next(c for c in cases if "x" in c["fields"])
        case["postconditions"] = ["ellmul"]
        del case["fields"]["x"]
    elif kind == "bad_scalar_type":
        pick()["fields"]["n"]["value"] = draw(non_integers)
    elif kind == "bad_point_shape":
        pick()["fields"]["P"]["value"] = draw(
            st.one_of(
                st.integers(),
                st.lists(st.integers(), min_size=3, max_size=5),
                st.lists(st.integers(), max_size=1),
                st.lists(st.text(), min_size=2, max_size=2),
            )
        )
    elif kind == "extra_field_key":
        pick()["fields"]["p"]["note"] = draw(st.text())
    elif kind == "field_not_object":
        pick()["fields"]["p"] = draw(st.integers())
    elif kind == "case_not_object":
        cases[draw(st.integers(0, len(cases) - 1))] = draw(st.text() | st.integers())
    elif kind == "drop_case_key":
        del pick()[draw(st.sampled_from(list(selftest.CASE_KEYS)))]
    elif kind == "empty_id":
        pick()["id"] = ""
    elif kind == "empty_postconditions":
        pick()["postconditions"] = []
    elif kind == "fields_not_object":
        pick()["fields"] = draw(st.lists(st.text(), max_size=2) | st.text())
    elif kind == "unknown_field_name":
        pick()["fields"][draw(st.text(min_size=1).filter(_unknown_field))] = {
            "value": 1,
            "origin": "author_supplied",
        }
    elif kind == "degenerate_modulus":
        pick()["fields"]["p"]["value"] = draw(st.integers(-50, 1))
    elif kind == "degenerate_order":
        pick()["fields"]["n"]["value"] = draw(st.integers(-50, 0))
    else:
        doc["schema_version"] = draw(
            st.integers().filter(lambda v: v != selftest.SCHEMA_VERSION)
        )
    return doc


def test_the_shipped_corpus_is_accepted_and_meets_its_own_floor():
    doc = selftest.load_corpus()
    assert len(doc["cases"]) == 4 and doc["pass_floor"] == 4
    assert [c["id"] for c in doc["cases"]] == [
        "F5",
        "GF101",
        "bits150",
        "negative_control",
    ]


@fixture_ok
@given(doc=json_values)
def test_arbitrary_json_is_refused_typed_or_accepted_never_unhandled(doc, pari_spy):
    try:
        selftest.check_corpus(doc)
    except CorpusSchemaError as exc:
        assert exc.path.startswith("$") and str(exc).startswith(exc.path)
    assert pari_spy == []


@fixture_ok
@_replay_seeds
@given(doc=mutated_corpus())
def test_every_corpus_mutation_is_refused_with_a_path_before_any_pari_call(
    doc, pari_spy
):
    with pytest.raises(CorpusSchemaError) as info:
        selftest.check_corpus(doc)
    assert re.fullmatch(r"\$(\.[A-Za-z_]+|\[\d+\])*", info.value.path)
    assert pari_spy == []


def test_mutant_schema_checks_first_case_only_is_killed_by_a_late_case_defect():
    doc = copy.deepcopy(BASE)
    del doc["cases"][3]["fields"]["P"]["origin"]
    with pytest.raises(CorpusSchemaError, match=re.escape("$.cases[3].fields.P")):
        selftest.check_corpus(doc)
    with selftest_mutants.schema_checks_first_case_only():
        selftest.check_corpus(doc)


def test_mutant_floor_not_validated_is_killed_by_a_floor_above_the_case_count():
    doc = copy.deepcopy(BASE)
    doc["pass_floor"] = len(doc["cases"]) + 1
    with pytest.raises(CorpusSchemaError, match=re.escape("$.pass_floor")):
        selftest.check_corpus(doc)
    with selftest_mutants.floor_not_validated():
        selftest.check_corpus(doc)


def test_every_planted_mutant_is_exercised():
    assert set(selftest_mutants.ALL) == {
        "schema_checks_first_case_only",
        "floor_not_validated",
    }
