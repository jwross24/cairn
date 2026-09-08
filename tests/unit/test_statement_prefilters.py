import pytest

from cairn import bundle, prefilter
from cairn import statement_prefilters as battery

CLEAN = battery.Statement(name="clean", binders="(n : Nat)", hypotheses=("n > 0",), conclusion="∃ m : Nat, m > n")
VACUOUS = battery.Statement(name="vacuous", binders="(n : Nat)", hypotheses=("n > 0", "n < 0"), conclusion="n = n")
PLAIN_TRAP = battery.Statement(name="trap", conclusion="∃ n : Nat, n ≠ 0 → False")
BINDER_TRAP = battery.Statement(name="silent", conclusion="∃ n : Nat, n > 0 ∧ (n ≠ 1 → False)")
NESTED_TRAP = battery.Statement(name="nested", conclusion="∃ n : Nat, (n ≠ 0 → False) ∧ True")
STUBBED = battery.Statement(name="stubbed", conclusion="Nat", kind=battery.OPAQUE)
AXIOMATIZED = battery.Statement(name="axiomatized", conclusion="1 = 1", kind=battery.AXIOM)

EXISTS = "Declaration contains the pattern the expression ∃ n, n ≠ 0 → False. Did you mean …?"
STUB = "Placeholder definitions (e.g., `opaque foo : Type*`) are not allowed."
AXIOM = "New axioms (e.g., `axiom foo : ...`) are not allowed."
SORRY = "declaration uses `sorry`"


def _classify(statement, statement_warnings=(), unproved=()):
    _, anchors = battery.render(statement)
    found = [(anchors["statement"], text) for text in statement_warnings]
    found += [(anchors[name], SORRY) for name in unproved if name in anchors]
    return battery.classify(tuple(found), anchors)


def _all_unproved(statement):
    _, anchors = battery.render(statement)
    return tuple(name for name in anchors if name != "statement")


def test_module_defined_public_api_is_closed():
    public = {
        name
        for name, value in vars(battery).items()
        if not name.startswith("_") and callable(value) and getattr(value, "__module__", None) == battery.__name__
    }
    assert public == {
        "PrefilterBatteryError",
        "Statement",
        "Battery",
        "linter_objects",
        "provenance",
        "module_name",
        "module_path",
        "render",
        "warnings_for",
        "classify",
        "write_linters",
        "scratch_project",
        "run",
        "record",
    }
    assert battery.LINTER_KINDS == (
        "linter_exists_implication",
        "linter_infotree_util",
        "linter_stub",
        "linter_term",
    )
    assert battery.DECLARATION_KINDS == ("theorem", "axiom", "opaque", "def")


def test_every_vendored_linter_is_a_raw_object_the_bundle_carries():
    assert set(battery.LINTER_KINDS) <= set(bundle.RAW_KINDS)
    assert battery.PROVENANCE_KIND not in bundle.RAW_KINDS
    objects = battery.linter_objects()
    assert set(objects) == set(battery.LINTER_KINDS)
    for kind, relative in battery.LINTER_SOURCES.items():
        assert objects[kind] == (battery.VENDOR_DIR / relative).read_bytes()
        assert objects[kind]


def test_the_provenance_object_names_the_revision_that_runs():
    value = battery.provenance()
    assert value["rev"] == battery.VENDOR_REV == "e13dd7284e72012a1616806d09cb6b8025e387af"
    assert value["repo"] == battery.VENDOR_REPO
    assert set(value["files"]) == set(battery.LINTER_KINDS)
    assert value["imports"] == list(battery.LINTER_IMPORTS)
    assert value["rev"] in (battery.VENDOR_DIR / "NOTICE").read_text()


def test_the_statement_renders_its_proposition_and_its_premise():
    assert VACUOUS.proposition == "∀ (n : Nat), (n > 0) → (n < 0) → (n = n)"
    assert VACUOUS.premise == "∀ (n : Nat), (n > 0) → (n < 0) → False"
    assert PLAIN_TRAP.proposition == "(∃ n : Nat, n ≠ 0 → False)"
    assert PLAIN_TRAP.premise == "False"


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        (CLEAN, "theorem clean : ∀ (n : Nat), (n > 0) → (∃ m : Nat, m > n)"),
        (AXIOMATIZED, "axiom axiomatized : (1 = 1)"),
        (STUBBED, "opaque stubbed : Nat"),
        (battery.Statement(name="d", conclusion="Nat", kind=battery.DEFINITION), "def d : Nat"),
    ],
)
def test_each_declaration_kind_renders_its_own_form(statement, expected):
    assert statement.declaration[0] == expected


def test_a_declaration_kind_outside_the_battery_is_refused():
    with pytest.raises(battery.PrefilterBatteryError, match="is not one of"):
        battery.Statement(name="x", conclusion="True", kind="instance")


def test_the_rendered_module_imports_the_linters_and_anchors_every_probe():
    source, anchors = battery.render(CLEAN)
    for name in battery.LINTER_IMPORTS:
        assert f"import {name}" in source
    assert "set_option linter.style.stubs true" in source
    assert set(anchors) == {"statement", "vacuity", "provable", "refutable"}
    lines = source.split("\n")
    for anchor, at in anchors.items():
        assert lines[at - 1].startswith(("theorem", "axiom", "opaque", "def")), anchor


def test_a_declaration_that_is_not_proposition_valued_carries_no_prover_probe():
    _, anchors = battery.render(STUBBED)
    assert set(anchors) == {"statement", "vacuity"}
    verdicts, flags, detail = _classify(STUBBED, [STUB], _all_unproved(STUBBED))
    assert prefilter.BOUNDED_PROVER not in verdicts
    assert detail["bounded_prover"] == "not-run: the declaration is not proposition-valued"
    assert flags == (prefilter.STUB_OR_AXIOM,)


def test_a_premise_that_derives_False_rejects():
    verdicts, flags, _ = _classify(VACUOUS, [], ("provable", "refutable"))
    assert verdicts[prefilter.VACUITY] == prefilter.REJECT
    assert prefilter.VACUITY not in flags


def test_a_premise_that_stands_stays_quiet():
    verdicts, flags, _ = _classify(CLEAN, [], _all_unproved(CLEAN))
    assert verdicts == dict.fromkeys(battery.PRODUCED_FILTERS, prefilter.QUIET)
    assert flags == ()


def test_the_plain_existential_trap_flags():
    verdicts, flags, _ = _classify(PLAIN_TRAP, [EXISTS], _all_unproved(PLAIN_TRAP))
    assert verdicts[prefilter.EXISTS_IMPLICATION] == prefilter.FLAG
    assert prefilter.EXISTS_IMPLICATION in flags


@pytest.mark.parametrize("statement", [BINDER_TRAP, NESTED_TRAP])
def test_the_binder_predicate_and_conjunction_nested_traps_pass_the_linter(statement):
    verdicts, flags, _ = _classify(statement, [], _all_unproved(statement))
    assert verdicts[prefilter.EXISTS_IMPLICATION] == prefilter.QUIET
    assert flags == ()


@pytest.mark.parametrize(
    ("warning", "expected"),
    [(STUB, battery.STUB), (AXIOM, battery.NEW_AXIOM)],
)
def test_stub_and_new_axiom_share_one_verdict_and_are_separated_in_the_detail(warning, expected):
    verdicts, flags, detail = _classify(AXIOMATIZED, [warning], _all_unproved(AXIOMATIZED))
    assert verdicts[prefilter.STUB_OR_AXIOM] == prefilter.FLAG
    assert flags == (prefilter.STUB_OR_AXIOM,)
    assert detail["stub_or_axiom"] == [expected]


def test_a_statement_the_bounded_prover_closes_flags_and_names_which_side_closed():
    verdicts, _, detail = _classify(CLEAN, [], ("vacuity", "refutable"))
    assert verdicts[prefilter.BOUNDED_PROVER] == prefilter.FLAG
    assert detail["bounded_prover"] == [battery.PROVABLE]
    verdicts, _, detail = _classify(CLEAN, [], ("vacuity", "provable"))
    assert detail["bounded_prover"] == [battery.REFUTABLE]


def test_a_warning_on_another_file_is_not_read_as_this_statements():
    stdout = "warning: Prefilter/P_other.lean:6:8: declaration uses `sorry`\n"
    stdout += "warning: Prefilter/P_mine.lean:6:8: declaration uses `sorry`\n"
    assert battery.warnings_for(stdout, "", "P_mine.lean") == ((6, SORRY),)


def test_a_warning_the_linter_repeats_is_read_once():
    verdicts, flags, _ = _classify(PLAIN_TRAP, [EXISTS, EXISTS, EXISTS], _all_unproved(PLAIN_TRAP))
    assert verdicts[prefilter.EXISTS_IMPLICATION] == prefilter.FLAG
    assert flags.count(prefilter.EXISTS_IMPLICATION) == 1


@pytest.mark.parametrize(
    ("statement", "warnings"),
    [(CLEAN, []), (VACUOUS, []), (PLAIN_TRAP, [EXISTS]), (AXIOMATIZED, [AXIOM]), (STUBBED, [STUB])],
)
def test_the_flags_the_battery_emits_always_validate_against_the_reader(statement, warnings):
    verdicts, flags, _ = _classify(statement, warnings, _all_unproved(statement))
    prefilter._validate("a" * 64, "b" * 64, verdicts, flags)


@pytest.mark.parametrize("statement", [CLEAN, VACUOUS, PLAIN_TRAP, AXIOMATIZED, STUBBED])
def test_roundtrip_divergence_never_carries_a_verdict_so_the_record_fails_closed(statement):
    verdicts, flags, _ = _classify(statement, [], _all_unproved(statement))
    assert prefilter.ROUNDTRIP_DIVERGENCE not in verdicts
    result = prefilter.PrefilterResult("a" * 64, "b" * 64, verdicts, flags, "2026-09-08T00:00:00Z")
    assert prefilter.ROUNDTRIP_DIVERGENCE in result.missing
    assert result.passed is False


@pytest.mark.parametrize("statement", [CLEAN, VACUOUS, PLAIN_TRAP, AXIOMATIZED])
def test_a_proposition_valued_statement_is_held_shut_by_the_round_trip_filter_alone(statement):
    verdicts, flags, _ = _classify(statement, [], _all_unproved(statement))
    result = prefilter.PrefilterResult("a" * 64, "b" * 64, verdicts, flags, "2026-09-08T00:00:00Z")
    assert result.missing == (prefilter.ROUNDTRIP_DIVERGENCE,)
    supplied = {**verdicts, prefilter.ROUNDTRIP_DIVERGENCE: prefilter.QUIET}
    admitted = prefilter.PrefilterResult("a" * 64, "b" * 64, supplied, flags, "2026-09-08T00:00:00Z")
    assert admitted.passed is (prefilter.REJECT not in verdicts.values())
