import json
import sys
from pathlib import Path

import pytest
from hypothesis import HealthCheck, example, given, settings
from hypothesis import strategies as st

from cairn import runner
from cairn.runner import ParsedOutput

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from mutants import runner_mutants

CORPUS = Path(__file__).resolve().parent.parent / "fuzz_corpus" / "runner"
CEILING = 10.0
fixture_ok = settings(deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])

leaves = st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False, allow_infinity=False) | st.text()
json_values = st.recursive(
    leaves,
    lambda c: st.lists(c, max_size=4) | st.dictionaries(st.text(), c, max_size=4),
    max_leaves=12,
)
VALID = b'{"status":"OK"}\n'


def _seed_corpus():
    return [
        bytes.fromhex(json.loads(p.read_text(encoding="utf-8"))["raw_hex"])
        for p in sorted(CORPUS.glob("stdout_*.json"))
    ]


def _replay_seeds(fn):
    for raw in _seed_corpus():
        fn = example(raw=raw)(fn)
    return fn


@st.composite
def documents(draw):
    document = draw(st.dictionaries(st.text(max_size=8), json_values, max_size=4))
    if draw(st.booleans()):
        document["status"] = draw(st.sampled_from(["OK", "FAIL", "DISAGREE"]) | st.text() | st.integers())
    if draw(st.booleans()):
        document["receipt"] = draw(json_values)
    return (json.dumps(document, sort_keys=True) + "\n").encode("utf-8")


mangled = st.one_of(
    st.binary(max_size=64),
    documents(),
    documents().map(lambda b: b + b"trailing"),
    documents().map(lambda b: b"\xef\xbb\xbf" + b),
    documents().map(lambda b: b + b),
    st.integers(0, len(VALID)).map(lambda n: VALID[:n]),
    st.just(b"[" * 20000),
    st.just(b'{"status":"OK","pad":"' + b"x" * (1024 * 1024) + b'"}'),
)


@fixture_ok
@_replay_seeds
@given(raw=mangled)
def test_the_parser_never_raises_and_the_receipt_is_never_trusted(raw):
    parsed = runner.parse_skill_output(raw)
    assert isinstance(parsed, ParsedOutput)
    assert "receipt" not in parsed.document
    if parsed.well_formed:
        assert parsed.status in runner.SKILL_STATUSES
    else:
        assert parsed.status is None and parsed.reason


@fixture_ok
@_replay_seeds
@given(raw=mangled)
def test_a_malformed_document_always_maps_to_fail(raw):
    parsed = runner.parse_skill_output(raw)
    if not parsed.well_formed:
        assert runner.status_for(parsed, 0, 0.0, CEILING) == "FAIL"


@fixture_ok
@given(raw=mangled, exit_status=st.integers(-64, 64), wall=st.floats(0.0, 100.0))
def test_the_status_is_always_one_of_the_four(raw, exit_status, wall):
    status = runner.status_for(runner.parse_skill_output(raw), exit_status, wall, CEILING)
    assert status in ("OK", "FAIL", "DISAGREE", "BUDGET_EXCEEDED")


@pytest.mark.parametrize("raw", _seed_corpus(), ids=lambda r: str(len(r)))
def test_every_seed_negative_is_refused(raw):
    parsed = runner.parse_skill_output(raw)
    assert not parsed.well_formed
    assert runner.status_for(parsed, 0, 0.0, CEILING) == "FAIL"


def test_a_well_formed_document_survives_with_its_receipt_stripped():
    parsed = runner.parse_skill_output(b'{"status":"OK","p":"5","receipt":{"cpu_user_s":"9999"}}\n')
    assert parsed.well_formed and parsed.status == "OK"
    assert parsed.document == {"status": "OK", "p": "5"}


def test_mutant_parser_json_loads_bare_is_killed_by_a_malformed_document():
    assert not runner.parse_skill_output(b"not json").well_formed
    with runner_mutants.parser_json_loads_bare(), pytest.raises(json.JSONDecodeError):
        runner.parse_skill_output(b"not json")


def test_mutant_status_default_ok_is_killed_by_a_document_with_no_status():
    raw = b'{"nope":1}'
    assert runner.status_for(runner.parse_skill_output(raw), 0, 0.0, CEILING) == "FAIL"
    with runner_mutants.status_default_ok():
        assert runner.status_for(runner.parse_skill_output(raw), 0, 0.0, CEILING) == "OK"


def test_mutant_receipt_trusted_is_killed_by_a_self_written_receipt():
    raw = b'{"status":"OK","receipt":{"cpu_user_s":"9999"}}'
    assert "receipt" not in runner.parse_skill_output(raw).document
    with runner_mutants.receipt_trusted():
        assert "receipt" in runner.parse_skill_output(raw).document


def test_every_planted_mutant_is_exercised():
    assert set(runner_mutants.ALL) == {
        "parser_json_loads_bare",
        "status_default_ok",
        "receipt_trusted",
    }
