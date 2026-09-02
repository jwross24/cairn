import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import _corpus
import _substrate_helpers as helpers
import family_self_check as self_check
from _corpus import (
    COLD_CACHE,
    CONTROL_MISMATCH,
    CONTROLS_BAR,
    CORPUS_COMPLETE,
    ESCAPED,
    INCONCLUSIVE,
    MUST_FAIL,
    MUST_PASS,
    NO_ATTEMPT,
    PLANTINGS_BAR,
    RUN_ERROR,
    SELF_CHECK,
    Entry,
    Observation,
    RegistryError,
)

from cairn import runner
from cairn.substrate import Substrate

HERE = Path(__file__).resolve().parent
OWNER = "cairn-m1-cqt.3.1"


def _noop(cold):
    return "unused"


def entry(test_id, family="a", expected_class=MUST_FAIL, expected_verdict="REJECT", run=_noop, owner=OWNER, **kw):
    return Entry(test_id, family, expected_class, expected_verdict, owner, run, **kw)


def observed(test_id, verdict, *, violation=None, error=None, attempts=(("att", 1, "OK"),)):
    return Observation(test_id, verdict, attempts, violation, error)


def ids(escapes):
    return sorted(e.test_id for e in escapes)


def test_the_registry_is_one_entry_per_planted_artifact(planted_registry):
    rows = [
        (e.test_id, e.family, e.expected_class, e.expected_verdict, e.owner_bead, e.launches)
        for e in planted_registry.entries
        if e.family == SELF_CHECK
    ]
    assert rows == [
        (self_check.WRONG_X_ID, SELF_CHECK, MUST_FAIL, "fail", OWNER, True),
        (self_check.NULL_ARM_ID, SELF_CHECK, MUST_PASS, INCONCLUSIVE, OWNER, True),
        (self_check.MIS_REGISTERED_ID, SELF_CHECK, MUST_PASS, "pass", OWNER, True),
    ]
    assert planted_registry.expected_escapes == {self_check.MIS_REGISTERED_ID}
    assert len(planted_registry.corpus) == len(planted_registry.entries) - 3


def test_every_planting_runs_cold_and_lands_as_its_family_declares(planted_registry, observe, rollup):
    for entry in planted_registry.entries:
        obs = observe(entry)
        assert obs.violation is None and obs.error is None, obs
        assert all(skip == 1 for _, skip, _ in obs.attempts), obs
        listed = entry.test_id in ids(rollup.escapes)
        assert listed == (entry.test_id in planted_registry.expected_escapes), rollup.report()


def test_the_self_check_family_reports_through_the_rollup(rollup):
    escapes = rollup.family(SELF_CHECK)
    assert [(e.test_id, e.kind, e.detail) for e in escapes] == [
        (self_check.MIS_REGISTERED_ID, CONTROL_MISMATCH, "landed 'fail', expected 'pass'")
    ]
    assert rollup.self_check_as_declared
    assert rollup.observations[self_check.WRONG_X_ID].observed_verdict == "fail"
    assert rollup.observations[self_check.NULL_ARM_ID].observed_verdict == INCONCLUSIVE
    for test_id in (self_check.WRONG_X_ID, self_check.NULL_ARM_ID, self_check.MIS_REGISTERED_ID):
        obs = rollup.observations[test_id]
        assert [(skip, status) for _, skip, status in obs.attempts] == [(1, "OK")], obs


def test_the_corpus_has_no_escapes(rollup):
    assert rollup.corpus_escapes == (), rollup.report()


@pytest.mark.xfail(not CORPUS_COMPLETE, strict=True, reason="corpus_complete is False until bead C7 flips it")
def test_the_corpus_bars_are_met(rollup):
    assert rollup.bars_met, rollup.shortfall()


def test_the_shortfall_is_reported_by_name(rollup):
    assert rollup.shortfall() == (
        f"plantings {rollup.plantings}/{PLANTINGS_BAR}, positive controls {rollup.controls}/{CONTROLS_BAR}"
        " (the self_check family is excluded from both)"
    )
    assert rollup.bars_met == (rollup.plantings >= PLANTINGS_BAR and rollup.controls >= CONTROLS_BAR)


def test_the_rollup_is_computed_from_the_registry():
    reg = _corpus.registry(
        [
            entry("a/caught"),
            entry("a/inconclusive_escape"),
            entry("a/accepted_escape"),
            entry("b/second_solution", family="b"),
            entry("k/control", family="k", expected_class=MUST_PASS, expected_verdict=INCONCLUSIVE),
            entry("k/control_wrong", family="k", expected_class=MUST_PASS, expected_verdict=INCONCLUSIVE),
            entry("j/control", family="j", expected_class=MUST_PASS, expected_verdict="KEEP"),
        ]
    )
    result = _corpus.rollup(
        reg,
        {
            "a/caught": observed("a/caught", "REJECT"),
            "a/inconclusive_escape": observed("a/inconclusive_escape", INCONCLUSIVE),
            "a/accepted_escape": observed("a/accepted_escape", "KEEP"),
            "b/second_solution": observed("b/second_solution", "REJECT"),
            "k/control": observed("k/control", INCONCLUSIVE),
            "k/control_wrong": observed("k/control_wrong", "KEEP"),
            "j/control": observed("j/control", "KEEP"),
        },
    )
    assert (result.plantings, result.controls) == (4, 3)
    assert [(e.test_id, e.kind, e.detail) for e in result.escapes] == [
        ("a/inconclusive_escape", ESCAPED, "landed INCONCLUSIVE, expected 'REJECT'"),
        ("a/accepted_escape", ESCAPED, "landed 'KEEP', expected 'REJECT'"),
        ("k/control_wrong", CONTROL_MISMATCH, "landed 'KEEP', expected 'INCONCLUSIVE'"),
    ]
    assert result.corpus_escapes == result.escapes
    assert result.report().splitlines()[1:] == [
        "escaped a/inconclusive_escape [a]: landed INCONCLUSIVE, expected 'REJECT'",
        "escaped a/accepted_escape [a]: landed 'KEEP', expected 'REJECT'",
        "control_mismatch k/control_wrong [k]: landed 'KEEP', expected 'INCONCLUSIVE'",
    ]


def test_a_cold_cache_violation_a_crash_or_an_inert_run_is_listed_not_counted_as_caught():
    reg = _corpus.registry(
        [entry("a/served"), entry("a/crashed"), entry("a/inert"), entry("a/gate_only", launches=False)]
    )
    result = _corpus.rollup(
        reg,
        {
            "a/served": observed("a/served", None, violation="served"),
            "a/crashed": observed("a/crashed", None, error="Traceback"),
            "a/inert": observed("a/inert", "REJECT", attempts=()),
            "a/gate_only": observed("a/gate_only", "REJECT", attempts=()),
        },
    )
    assert [(e.test_id, e.kind) for e in result.escapes] == [
        ("a/served", COLD_CACHE),
        ("a/crashed", RUN_ERROR),
        ("a/inert", NO_ATTEMPT),
    ]


def test_an_unobserved_entry_refuses_the_rollup():
    reg = _corpus.registry([entry("a/one"), entry("a/two")])
    with pytest.raises(RegistryError, match="'a/two' was never observed"):
        _corpus.rollup(reg, {"a/one": observed("a/one", "REJECT")})


def _synthetic(family, n_fail, n_pass):
    fails = [entry(f"{family}/fail{i}", family=family) for i in range(n_fail)]
    passes = [
        entry(f"{family}/pass{i}", family=family, expected_class=MUST_PASS, expected_verdict="KEEP")
        for i in range(n_pass)
    ]
    return fails + passes


def _landed(entries):
    return {e.test_id: observed(e.test_id, e.expected_verdict) for e in entries}


def test_self_check_entries_count_toward_neither_bar():
    padded = _synthetic(SELF_CHECK, PLANTINGS_BAR, CONTROLS_BAR)
    reg = _corpus.registry(padded, expected_escapes=())
    result = _corpus.rollup(reg, _landed(padded))
    assert (result.plantings, result.controls) == (0, 0)
    assert not result.bars_met
    assert result.escapes == () and result.self_check_as_declared


def test_the_same_entries_under_a_corpus_family_meet_both_bars():
    real = _synthetic("a", PLANTINGS_BAR, CONTROLS_BAR)
    result = _corpus.rollup(_corpus.registry(real), _landed(real))
    assert (result.plantings, result.controls) == (PLANTINGS_BAR, CONTROLS_BAR)
    assert result.bars_met


def test_one_short_of_either_bar_is_a_shortfall():
    fails = _synthetic("a", PLANTINGS_BAR - 1, CONTROLS_BAR)
    passes = _synthetic("a", PLANTINGS_BAR, CONTROLS_BAR - 1)
    for entries in (fails, passes):
        result = _corpus.rollup(_corpus.registry(entries), _landed(entries))
        assert not result.bars_met, result.shortfall()


@pytest.mark.parametrize(
    ("entries", "expected_escapes", "message"),
    [
        ([entry("a/x"), entry("a/x")], (), "'a/x' is registered twice"),
        ([entry("")], (), "test_id must be a non-empty str"),
        ([entry("a/x", family="")], (), "family must be a non-empty str"),
        ([entry("a/x", launches="yes")], (), "launches must be a bool"),
        ([entry("a/x", family="z")], (), "family 'z' is not one of"),
        ([entry("a/x", expected_class="must-MAYBE")], (), "expected_class 'must-MAYBE' is not one of"),
        ([entry("a/x", expected_verdict=INCONCLUSIVE)], (), "landing INCONCLUSIVE is an escape, never its target"),
        ([entry("a/x", expected_verdict="")], (), "expected_verdict must be a non-empty str"),
        ([entry("a/x", owner="")], (), "owner_bead must be a non-empty str"),
        ([entry("a/x", run="not callable")], (), "run is not callable"),
        (
            [
                entry("a/x", expected_verdict="REJECT"),
                entry("a/y", expected_class=MUST_PASS, expected_verdict="REJECT"),
            ],
            (),
            "family 'a' registers \\['REJECT'\\] as both",
        ),
        ([entry("a/x")], ("a/x",), "expected escape 'a/x' is outside the self_check family"),
        ([entry("a/x")], ("a/nope",), "expected escape 'a/nope' names no registered entry"),
        (["not an entry"], (), "registry holds a str, not an Entry"),
    ],
)
def test_the_registry_refuses_an_entry_the_rollup_could_not_judge(entries, expected_escapes, message):
    with pytest.raises(RegistryError, match=message):
        _corpus.registry(entries, expected_escapes)


def test_a_self_check_entry_may_be_an_expected_escape():
    reg = _corpus.registry([entry("self_check/x", family=SELF_CHECK)], ("self_check/x",))
    assert reg.expected_escapes == {"self_check/x"}
    assert reg.by_id("self_check/x").family == SELF_CHECK
    with pytest.raises(KeyError):
        reg.by_id("self_check/y")


def test_discovery_reads_every_family_module_and_nothing_else(tmp_path):
    (tmp_path / "family_one.py").write_text(
        "from _corpus import Entry\nENTRIES = (Entry('a/one', 'a', 'must-FAIL', 'REJECT', 'bead', lambda cold: 'REJECT'),)\n"
    )
    (tmp_path / "family_two.py").write_text(
        "from _corpus import Entry\nENTRIES = (Entry('b/two', 'b', 'must-PASS', 'KEEP', 'bead', lambda cold: 'KEEP'),)\n"
    )
    (tmp_path / "family_self_check.py").write_text(
        "from _corpus import Entry\n"
        "ENTRIES = (Entry('self_check/two', 'self_check', 'must-PASS', 'KEEP', 'bead', lambda cold: 'KEEP'),)\n"
        "EXPECTED_ESCAPES = ('self_check/two',)\n"
    )
    (tmp_path / "test_ignored.py").write_text("ENTRIES = 'never read'\n")
    reg = _corpus.discover(tmp_path)
    assert reg.ids == ("a/one", "self_check/two", "b/two")
    assert (reg.by_id("b/two"),) == sys.modules["family_two"].ENTRIES
    assert reg.expected_escapes == {"self_check/two"}
    assert Path(sys.modules["family_self_check"].__file__ or "").parent == HERE


@pytest.mark.parametrize(
    ("body", "message"),
    [
        (
            "from _corpus import Entry\n"
            "ENTRIES = (Entry('self_check/x', 'self_check', 'must-FAIL', 'REJECT', 'bead', lambda cold: 'KEEP'),)\n",
            r"family_c\.py registers \['self_check/x'\] under 'self_check'; only family_self_check\.py may",
        ),
        (
            "from _corpus import Entry\n"
            "ENTRIES = (Entry('a/x', 'a', 'must-FAIL', 'REJECT', 'bead', lambda cold: 'KEEP'),)\n"
            "EXPECTED_ESCAPES = ()\n",
            r"family_c\.py declares EXPECTED_ESCAPES; only family_self_check\.py may",
        ),
    ],
)
def test_only_the_harness_module_may_register_the_self_check_family(tmp_path, body, message):
    (tmp_path / "family_c.py").write_text(body)
    with pytest.raises(RegistryError, match=message):
        _corpus.discover(tmp_path)


def test_discovery_imports_a_family_module_once(tmp_path):
    counter = tmp_path / "loads"
    (tmp_path / "family_once.py").write_text(
        "from pathlib import Path\n"
        f"counter = Path({str(counter)!r})\n"
        "counter.write_text(str(int(counter.read_text() or 0) + 1) if counter.exists() else '1')\n"
        "ENTRIES = ()\n"
    )
    first = _corpus.discover(tmp_path)
    second = _corpus.discover(tmp_path)
    assert first.entries == second.entries == ()
    assert counter.read_text() == "1"


def test_a_family_module_without_entries_refuses_discovery(tmp_path):
    (tmp_path / "family_empty.py").write_text("OWNER = 'bead'\n")
    with pytest.raises(RegistryError, match=r"family_empty\.py declares no ENTRIES"):
        _corpus.discover(tmp_path)


def test_the_control_driven_to_keep_is_listed_by_id(observe):
    driven = entry(
        "self_check/null_arm_driven_to_keep",
        family=SELF_CHECK,
        expected_class=MUST_PASS,
        expected_verdict=INCONCLUSIVE,
        run=self_check.null_arm_driven_to_keep,
    )
    obs = observe(driven, fresh=True)
    assert obs.observed_verdict == "KEEP" and obs.violation is None and obs.error is None, obs
    result = _corpus.rollup(_corpus.registry([driven]), {driven.test_id: obs})
    assert [(e.test_id, e.kind, e.detail) for e in result.escapes] == [
        (driven.test_id, CONTROL_MISMATCH, "landed 'KEEP', expected 'INCONCLUSIVE'")
    ]


def _warm(db_path, document):
    with Substrate.open(db_path, role="writer") as sub:
        recipe = self_check._recipe(sub, document)
        first = runner.launch(
            sub,
            "cairn.skills.toy_curve",
            recipe,
            stdin_document=document,
            bundle_hash=_corpus.HARNESS_BUNDLE_HASH,
            evaluation=self_check.toy_curve.COST_PROFILE.evaluate(self_check.BITS),
            ceiling_multiplier=4,
            tool_digests=self_check.toy_curve.identity_bundle()["tool_digests"],
            scratch_root=db_path.parent / "warm",
        )
        assert first.status == "OK" and not first.served_from_cache
        assert sub.serve(first.recipe_key) is not None
    return recipe, first.recipe_key


def test_a_run_served_from_cache_fails_the_cold_cache_assertion(tmp_path):
    document = {"bits": self_check.BITS, "seed": self_check.SEED}
    db_path = tmp_path / "substrate.sqlite"
    recipe, key = _warm(db_path, document)

    def served_run(cold):
        attempt = runner.launch(
            cold.sub,
            "cairn.skills.toy_curve",
            recipe,
            stdin_document=document,
            bundle_hash=cold.bundle_hash,
            evaluation=self_check.toy_curve.COST_PROFILE.evaluate(self_check.BITS),
            ceiling_multiplier=4,
            tool_digests=self_check.toy_curve.identity_bundle()["tool_digests"],
            scratch_root=cold.scratch_root,
        )
        return "pass" if attempt.status == "OK" else "fail"

    planted = entry("self_check/served", family=SELF_CHECK, expected_verdict="fail", run=served_run)
    obs = _corpus.observe(planted, db_path=db_path, scratch_root=tmp_path / "runs")
    assert obs.observed_verdict is None and obs.attempts == ()
    assert obs.violation == f"a fixture run asked the cache to serve recipe {key}"
    result = _corpus.rollup(_corpus.registry([planted]), {planted.test_id: obs})
    assert [(e.test_id, e.kind) for e in result.escapes] == [(planted.test_id, COLD_CACHE)]


def test_an_attempt_started_with_the_lookup_on_fails_the_cold_cache_assertion(tmp_path):
    def warm_start(cold):
        key = cold.sub.put_recipe(helpers.recipe(1))
        attempt_id = cold.sub.start_attempt(key)
        cold.sub.close_attempt(attempt_id, "OK")
        return "REJECT"

    planted = entry("self_check/warm_start", family=SELF_CHECK, run=warm_start)
    obs = _corpus.observe(planted, db_path=tmp_path / "substrate.sqlite", scratch_root=tmp_path / "runs")
    assert obs.observed_verdict == "REJECT"
    assert [skip for _, skip, _ in obs.attempts] == [0]
    assert obs.violation == f"attempt(s) started with the cache lookup on: {[obs.attempts[0][0]]}"


def test_a_fixture_asking_for_a_warm_launch_is_refused_before_it_spawns(tmp_path):
    def asks_warm(cold):
        return cold.launch("cairn.skills.toy_curve", helpers.recipe(1), skip_cache_lookup=False)

    planted = entry("self_check/asks_warm", family=SELF_CHECK, run=asks_warm)
    obs = _corpus.observe(planted, db_path=tmp_path / "substrate.sqlite", scratch_root=tmp_path / "runs")
    assert obs.attempts == ()
    assert obs.violation == "a fixture asked to launch cairn.skills.toy_curve with the cache lookup on"


def test_a_crashing_fixture_is_an_error_with_its_traceback(tmp_path):
    def crashes(cold):
        raise ValueError("planted crash")

    planted = entry("self_check/crash", family=SELF_CHECK, run=crashes)
    obs = _corpus.observe(planted, db_path=tmp_path / "substrate.sqlite", scratch_root=tmp_path / "runs")
    assert obs.observed_verdict is None and obs.violation is None
    assert obs.error is not None and "ValueError: planted crash" in obs.error


def test_a_fixture_returning_no_verdict_str_is_an_error(tmp_path):
    planted = entry("self_check/int", family=SELF_CHECK, run=lambda cold: 7)
    obs = _corpus.observe(planted, db_path=tmp_path / "substrate.sqlite", scratch_root=tmp_path / "runs")
    assert obs.observed_verdict is None and obs.error == "run returned a int, not a verdict str"


def test_the_cold_substrate_is_the_real_substrate_with_serve_refused(tmp_path):
    with _corpus.ColdSubstrate.open(tmp_path / "substrate.sqlite", role="writer") as sub:
        key = sub.put_recipe(helpers.recipe(1))
        helpers.launch(sub, key, "OK", {"out": b"x"}, skip_cache_lookup=True)
        assert sub.get_recipe(key) is not None
        with pytest.raises(_corpus.ColdCacheViolation, match=f"serve recipe {key}"):
            sub.serve(key)
    with Substrate.open(tmp_path / "substrate.sqlite", role="writer") as plain:
        assert plain.serve(key) is not None
