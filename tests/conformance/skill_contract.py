import dataclasses
import json
from pathlib import Path

from skill_contract_axes import (
    AxisDeclarationError,
    _axis_probes,
    _axis_records,
    _check_declared_axes,
    _emits_float,
    check_axis_declaration,
    check_numeric_profile,
    check_postcondition_arm,
)
from skill_contract_base import (
    AXES,
    CEILING_MULTIPLIER,
    FAIL,
    IDENTITY_FIELDS,
    INTERFACE_VERSION_RE,
    LEDGER_VOCABULARY,
    LEVELS,
    LOG_STEP,
    MUST,
    NA,
    ORIGIN_VOCABULARY,
    PASS,
    SHOULD,
    STATUSES,
    SUBSTRATE_ENV_RE,
    SUBSTRATE_PATH_MARK,
    XFAIL,
    Clause,
    Context,
    LaunchFailed,
    SkillSubject,
    Verdict,
    _corpus,
    _document,
    _launch,
    _recipe,
    _stderr_bytes,
    _stdout_bytes,
    certified,
    imported,
)
from skill_contract_checks import (
    _declared_seam,
    _launch_with_planted_seam,
    _manifest_from_child_bytes,
    _revision_moves_with_content,
    _without_seed,
    check_byte_equal_double_run,
    check_captured_seed,
    check_content_addressed_io,
    check_corpus_origins,
    check_declared_cost_profile,
    check_disagree_semantics,
    check_floor_is_attributed,
    check_golden_certificate,
    check_ledger_and_floor,
    check_no_substrate_handle,
    check_typed_interface,
)

from cairn import log, selftest, selftest_skills

__all__ = [
    "AXES",
    "CEILING_MULTIPLIER",
    "FAIL",
    "IDENTITY_FIELDS",
    "INTERFACE_VERSION_RE",
    "LEDGER_VOCABULARY",
    "LEVELS",
    "LOG_STEP",
    "MUST",
    "NA",
    "ORIGIN_VOCABULARY",
    "PASS",
    "SHOULD",
    "STATUSES",
    "SUBSTRATE_ENV_RE",
    "SUBSTRATE_PATH_MARK",
    "XFAIL",
    "AxisDeclarationError",
    "Clause",
    "Context",
    "LaunchFailed",
    "SkillSubject",
    "Verdict",
    "_axis_probes",
    "_axis_records",
    "_check_declared_axes",
    "_corpus",
    "_declared_seam",
    "_document",
    "_emits_float",
    "_launch",
    "_launch_with_planted_seam",
    "_manifest_from_child_bytes",
    "_recipe",
    "_revision_moves_with_content",
    "_stderr_bytes",
    "_stdout_bytes",
    "_without_seed",
    "certified",
    "check_axis_declaration",
    "check_byte_equal_double_run",
    "check_captured_seed",
    "check_content_addressed_io",
    "check_corpus_origins",
    "check_declared_cost_profile",
    "check_disagree_semantics",
    "check_floor_is_attributed",
    "check_golden_certificate",
    "check_ledger_and_floor",
    "check_no_substrate_handle",
    "check_numeric_profile",
    "check_postcondition_arm",
    "check_typed_interface",
    "imported",
]

CLAUSES = [
    Clause(
        "S2-01",
        MUST,
        "a skill has a typed interface and a fixed version, so it's testable, cacheable, and reproducible",
        check_typed_interface,
    ),
    Clause(
        "S2-02",
        MUST,
        "the whole bundle names the executable that a recipe key, a ladder run and a tier ticket bind",
        check_content_addressed_io,
    ),
    Clause(
        "S2-03",
        MUST,
        "every nondeterminism source pinned (seed, hashers, clock)",
        check_captured_seed,
    ),
    Clause(
        "S2-04",
        MUST,
        "a vendored known-answer corpus ... Every corpus declares its origin, corpus_origin in "
        "{upstream_vendored, independent_oracle, randomized_postcondition, author_supplied}",
        check_corpus_origins,
    ),
    Clause(
        "S2-05",
        MUST,
        "a per-case ledger (pass | intentional_non_goal | known_gap) and a committed pass floor",
        check_ledger_and_floor,
    ),
    Clause(
        "S2-06",
        MUST,
        "a lower bound that only an explicit, attributed update may raise, so the advertised floor and the "
        "measured floor cannot drift apart",
        check_floor_is_attributed,
    ),
    Clause(
        "S2-07",
        MUST,
        "a golden certificate = hash over the canonical transcript of the corpus and the exact outputs",
        check_golden_certificate,
    ),
    Clause(
        "S2-08",
        MUST,
        "a byte-equal double run asserted",
        check_byte_equal_double_run,
    ),
    Clause(
        "S2-09",
        MUST,
        "grain a skill at a capability with a stable interface, a self-test, and a declared cost profile",
        check_declared_cost_profile,
    ),
    Clause(
        "S2-10",
        MUST,
        "On disagreement the skill returns status = DISAGREE (not OK, so never cached), writes both transcripts "
        "and digests to a substrate node",
        check_disagree_semantics,
    ),
    Clause(
        "S2-11",
        MUST,
        "M0 operator decision (cairn-m0-e0s.9, not PLAN 2): the child is launched with an environment allowlist "
        "and no substrate handle",
        check_no_substrate_handle,
    ),
    Clause(
        "S2-12",
        MUST,
        "the skill declares each of its axes, `implementation` or `algorithm`, and the input range over which "
        "each axis is independent; every declared axis must satisfy every arm, and a cross-check that has "
        "never disagreed is reported as untested, not as passing",
        check_axis_declaration,
    ),
    Clause(
        "S2-13",
        SHOULD,
        "Skills that produce floats declare a numeric profile or a tolerance",
        check_numeric_profile,
    ),
    Clause(
        "S2-14",
        SHOULD,
        "Tier-0 arithmetic skills verify their own answer before returning",
        check_postcondition_arm,
    ),
]

CLAUSES_BY_ID = {clause.id: clause for clause in CLAUSES}
MUST_IDS = tuple(clause.id for clause in CLAUSES if clause.level == MUST)


def run_conformance(subject, ctx):
    lg = log.get(LOG_STEP)
    verdicts = []
    for clause in CLAUSES:
        try:
            verdict = clause.check(subject, ctx)
        except Exception as exc:
            verdict = Verdict(clause.id, clause.level, FAIL, f"{type(exc).__name__}: {exc}")
        if verdict.clause_id != clause.id:
            verdict = Verdict(clause.id, clause.level, FAIL, f"the check reported {verdict.clause_id}")
        lg.info(
            "verdict",
            subject=subject.name,
            clause_id=verdict.clause_id,
            level=verdict.level,
            status=verdict.status,
            reason=verdict.reason,
        )
        verdicts.append(verdict)
    return verdicts


def must_score(verdicts):
    must = [v for v in verdicts if v.level == MUST]
    return sum(1 for v in must if v.status == PASS), len(must)


def failures(verdicts, level=MUST):
    return frozenset(v.clause_id for v in verdicts if v.level == level and v.status == FAIL)


def matrix(results):
    names = sorted(results)
    width = max([len("clause"), *[len(n) for n in names]])
    lines = ["clause".ljust(width + 2) + "  ".join(n.ljust(width) for n in names)]
    for clause in CLAUSES:
        cells = "  ".join(next(v.status for v in results[n] if v.clause_id == clause.id).ljust(width) for n in names)
        lines.append(f"{clause.id} {clause.level:<6}".ljust(width + 2) + cells)
    for name in names:
        passed, total = must_score(results[name])
        lines.append(f"{name} MUST score {passed}/{total}")
    return "\n".join(lines)


def module_transcript(subject, ctx):
    return imported(subject).transcript()


def module_certify(subject, ctx):
    return imported(subject).certify(ctx.sub)


def toy_curve_certify(subject, ctx):
    return selftest.certify(ctx.sub, ctx.config)


def toy_curve_transcript(subject, ctx):
    return selftest.run_once(ctx.config)["transcript"]


def toy_curve_postcondition(subject, ctx):
    from cairn.skills import toy_curve

    out = toy_curve.run(subject.inputs["bits"], subject.inputs["seed"])
    try:
        toy_curve.check_postcondition(out)
        held = True
    except toy_curve.PostconditionFailed:
        held = False
    planted = dataclasses.replace(out, n=out.n + 2)
    try:
        toy_curve.check_postcondition(planted)
        refused = False
    except toy_curve.PostconditionFailed:
        refused = True
    return held, refused


TOY_CURVE = SkillSubject(
    name="toy_curve",
    module="cairn.skills.toy_curve",
    corpus_path=selftest.CORPUS_PATH,
    floor_golden="toy_curve_floor",
    inputs={"bits": 40, "seed": 1},
    out_of_range_inputs={"bits": 60, "seed": 1},
    conforming=True,
    certify=toy_curve_certify,
    transcript=toy_curve_transcript,
    postcondition=toy_curve_postcondition,
    expected_must_failures=frozenset(),
    cross_check_inputs={
        "algorithm": {"inside": {"bits": 40, "seed": 1}, "outside": {"bits": 60, "seed": 1}},
        "implementation": {"inside": {"bits": 60, "seed": 1}, "outside": {"bits": 70, "seed": 1}},
    },
)

DLP_INSTANCES = json.loads((Path(__file__).resolve().parents[1] / "vectors" / "dlp_instances.json").read_text())[
    "instances"
]


def _dlp_inputs(name, seed=1):
    row = DLP_INSTANCES[name]
    return {"bits": row["bits"], "seed": seed, **{k: row[k] for k in ("p", "a", "b", "n", "P", "Q")}}


def _skill_certify(which):
    def certify(subject, ctx):
        return selftest_skills.certify(ctx.sub, ctx.config, which)

    return certify


def _skill_transcript(which):
    def transcript(subject, ctx):
        return selftest_skills.run_once(which, ctx.config)["transcript"]

    return transcript


def instance_maker_postcondition(subject, ctx):
    from cairn.skills import instance_maker

    out = instance_maker.run(subject.inputs["bits"], subject.inputs["seed"])
    try:
        instance_maker.check_postcondition(out)
        held = True
    except instance_maker.PostconditionFailed:
        held = False
    planted = dataclasses.replace(out, x=out.x % (out.n - 1) + 1)
    try:
        instance_maker.check_postcondition(planted)
        refused = False
    except instance_maker.PostconditionFailed:
        refused = True
    return held, refused


RHO_DP = SkillSubject(
    name="rho_dp",
    module="cairn.skills.rho_dp",
    corpus_path=selftest_skills.CORPUS_PATHS[selftest_skills.RHO_DP],
    floor_golden="rho_dp_floor",
    inputs=_dlp_inputs("bits28_seed1"),
    out_of_range_inputs=_dlp_inputs("bits30_seed1"),
    conforming=True,
    certify=_skill_certify(selftest_skills.RHO_DP),
    transcript=_skill_transcript(selftest_skills.RHO_DP),
    postcondition=None,
    expected_must_failures=frozenset(),
)

BSGS = SkillSubject(
    name="bsgs",
    module="cairn.skills.bsgs",
    corpus_path=selftest_skills.CORPUS_PATHS[selftest_skills.BSGS],
    floor_golden="bsgs_floor",
    inputs=_dlp_inputs("bits28_seed1"),
    out_of_range_inputs=_dlp_inputs("bits30_seed1"),
    conforming=True,
    certify=_skill_certify(selftest_skills.BSGS),
    transcript=_skill_transcript(selftest_skills.BSGS),
    postcondition=None,
    expected_must_failures=frozenset(),
)

INSTANCE_MAKER = SkillSubject(
    name="instance_maker",
    module="cairn.skills.instance_maker",
    corpus_path=selftest_skills.CORPUS_PATHS[selftest_skills.INSTANCE_MAKER],
    floor_golden="instance_maker_floor",
    inputs={"bits": 28, "seed": 1},
    out_of_range_inputs={"bits": 30, "seed": 1},
    conforming=True,
    certify=_skill_certify(selftest_skills.INSTANCE_MAKER),
    transcript=_skill_transcript(selftest_skills.INSTANCE_MAKER),
    postcondition=instance_maker_postcondition,
    expected_must_failures=frozenset(),
)

NONCONFORMING = SkillSubject(
    name="nonconforming",
    module="skills.nonconforming",
    corpus_path=Path(__file__).resolve().parents[1] / "fixtures" / "skills" / "nonconforming_corpus.json",
    floor_golden="nonconforming_floor",
    inputs={"bits": 20, "seed": 1},
    out_of_range_inputs={"bits": 60, "seed": 1},
    conforming=False,
    certify=module_certify,
    transcript=module_transcript,
    postcondition=None,
    expected_must_failures=frozenset({"S2-01", "S2-04", "S2-10", "S2-11", "S2-12"}),
)

WITNESS = SkillSubject(
    name="witness",
    module="skills.witness",
    corpus_path=Path(__file__).resolve().parents[1] / "fixtures" / "skills" / "witness_corpus.json",
    floor_golden="witness_floor",
    inputs={"bits": 20, "seed": 1},
    out_of_range_inputs={"bits": 60, "seed": 1},
    conforming=False,
    certify=module_certify,
    transcript=module_transcript,
    postcondition=None,
    expected_must_failures=frozenset({"S2-02", "S2-03", "S2-05", "S2-06", "S2-07", "S2-08", "S2-09", "S2-10", "S2-12"}),
)

SUBJECTS = (TOY_CURVE, RHO_DP, BSGS, INSTANCE_MAKER, NONCONFORMING, WITNESS)
SUBJECTS_BY_NAME = {subject.name: subject for subject in SUBJECTS}
CONFORMING = tuple(subject for subject in SUBJECTS if subject.conforming)
EXPECTED_SHOULD = {
    "toy_curve": {"S2-13": PASS, "S2-14": PASS},
    "rho_dp": {"S2-13": NA, "S2-14": NA},
    "bsgs": {"S2-13": NA, "S2-14": NA},
    "instance_maker": {"S2-13": PASS, "S2-14": PASS},
    "nonconforming": {"S2-13": NA, "S2-14": FAIL},
    "witness": {"S2-13": FAIL, "S2-14": FAIL},
}
