import dataclasses
import importlib
import inspect
import json
import re
import shutil
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from cairn import keys, log, profile, runner, selftest, substrate

LOG_STEP = "conformance"
MUST = "MUST"
SHOULD = "SHOULD"
PASS = "PASS"
FAIL = "FAIL"
XFAIL = "XFAIL"
NA = "NA"
LEVELS = (MUST, SHOULD)
STATUSES = (PASS, FAIL, XFAIL, NA)
ORIGIN_VOCABULARY = ("upstream_vendored", "independent_oracle", "randomized_postcondition", "author_supplied")
LEDGER_VOCABULARY = ("pass", "intentional_non_goal", "known_gap")
AXES = ("implementation", "algorithm")
IDENTITY_FIELDS = (
    "interface_version",
    "implementation_revision",
    "tool_digests",
    "container_digest",
    "numeric_profile",
)
INTERFACE_VERSION_RE = re.compile(r"^[a-z][a-z0-9_]*/[0-9]+$")
SUBSTRATE_ENV_RE = re.compile(r"CAIRN_DB")
SUBSTRATE_PATH_MARK = ".sqlite"
CEILING_MULTIPLIER = 8


@dataclass(frozen=True)
class Verdict:
    clause_id: str
    level: str
    status: str
    reason: str


@dataclass(frozen=True)
class Clause:
    id: str
    level: str
    text: str
    check: Callable


@dataclass(frozen=True)
class Context:
    sub: substrate.Substrate
    config: object
    bundle_hash: str
    scratch_root: Path
    fixtures_path: str
    repo_root: Path
    workspace: Path
    cache: dict = field(default_factory=dict)


@dataclass(frozen=True)
class SkillSubject:
    name: str
    module: str
    corpus_path: Path
    floor_golden: str
    inputs: Mapping
    out_of_range_inputs: Mapping
    conforming: bool
    certify: Callable
    transcript: Callable
    postcondition: Callable | None = None
    expected_must_failures: frozenset = field(default_factory=frozenset)


def imported(subject):
    return importlib.import_module(subject.module)


def certified(subject, ctx):
    key = ("certify", subject.name)
    if key not in ctx.cache:
        ctx.cache[key] = subject.certify(subject, ctx)
    return ctx.cache[key]


def _corpus(subject):
    return json.loads(Path(subject.corpus_path).read_text())


def _recipe(subject, seed, salt=""):
    module = imported(subject)
    identity = module.identity_bundle()
    return {
        "skill_identity_hash": keys.identity_bundle_hash(identity),
        "inputs": {},
        "seed": seed,
        "tool_versions": {"cypari2": identity["tool_digests"]["cypari2"]},
        "container_digest": identity["container_digest"],
        "salt": salt,
    }


def _launch(subject, ctx, *, module=None, inputs=None, salt="", env_extra=None, seed=None):
    document = dict(subject.inputs if inputs is None else inputs)
    evaluation = imported(subject).COST_PROFILE.evaluate(document["bits"])
    extra = {"PYTHONPATH": ctx.fixtures_path}
    extra.update(env_extra or {})
    return runner.launch(
        ctx.sub,
        subject.module if module is None else module,
        _recipe(subject, document["seed"] if seed is None else seed, salt),
        stdin_document=document,
        bundle_hash=ctx.bundle_hash,
        evaluation=evaluation,
        ceiling_multiplier=CEILING_MULTIPLIER,
        tool_digests=imported(subject).identity_bundle()["tool_digests"],
        scratch_root=ctx.scratch_root,
        env_extra=extra,
        skip_cache_lookup=True,
    )


def _stdout_bytes(ctx, attempt):
    return (Path(ctx.scratch_root) / attempt.attempt_id / "stdout").read_bytes()


def _stderr_bytes(ctx, attempt):
    return (Path(ctx.scratch_root) / attempt.attempt_id / "stderr").read_bytes()


def check_typed_interface(subject, ctx):
    module = imported(subject)
    version = getattr(module, "INTERFACE_VERSION", None)
    if not isinstance(version, str) or not INTERFACE_VERSION_RE.match(version):
        return Verdict("S2-01", MUST, FAIL, f"INTERFACE_VERSION {version!r} is not <name>/<int>")
    for name in ("run", "main"):
        if not callable(getattr(module, name, None)):
            return Verdict("S2-01", MUST, FAIL, f"{subject.module}.{name} is not callable")
    kinds = {p.kind for p in inspect.signature(module.run).parameters.values()}
    if kinds & {inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD}:
        return Verdict("S2-01", MUST, FAIL, "run() takes *args or **kwargs, so its interface is not fixed")
    bundle = module.identity_bundle()
    missing = [name for name in IDENTITY_FIELDS if name not in bundle]
    if missing:
        return Verdict("S2-01", MUST, FAIL, f"identity_bundle() omits {missing}")
    moved = _revision_moves_with_content(module, ctx)
    if moved is not None:
        return Verdict("S2-01", MUST, FAIL, moved)
    return Verdict("S2-01", MUST, PASS, f"{version}, five identity fields, revision derived from IDENTITY_SOURCES")


def _revision_moves_with_content(module, ctx):
    root = ctx.workspace / f"revision-{module.__name__.rsplit('.', 1)[-1]}"
    if root.exists():
        shutil.rmtree(root)
    for rel in module.IDENTITY_SOURCES:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(Path(ctx.repo_root) / rel, target)
    if module.implementation_revision(root) != module.implementation_revision(ctx.repo_root):
        return "implementation_revision differs for a byte-identical copy of IDENTITY_SOURCES"
    edited = root / module.IDENTITY_SOURCES[0]
    edited.write_bytes(edited.read_bytes() + b"\n")
    if module.implementation_revision(root) == module.implementation_revision(ctx.repo_root):
        return f"implementation_revision does not move when {module.IDENTITY_SOURCES[0]} changes"
    return None


def check_content_addressed_io(subject, ctx):
    attempt = _launch(subject, ctx, salt="s2-02")
    if attempt.parsed is None or not attempt.parsed.well_formed:
        return Verdict("S2-02", MUST, FAIL, f"stdout is not one JSON object: {attempt.parsed}")
    raw = _stdout_bytes(ctx, attempt)
    document = json.loads(raw)
    canonical = (json.dumps(document, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    if raw != canonical:
        return Verdict("S2-02", MUST, FAIL, "stdout is not canonical JSON: it does not round-trip byte-identically")
    if attempt.output_manifest_hash is None:
        return Verdict("S2-02", MUST, FAIL, "no output manifest was recorded")
    recomputed = _manifest_from_child_bytes(ctx, attempt, raw)
    if recomputed != attempt.output_manifest_hash:
        return Verdict(
            "S2-02", MUST, FAIL, f"the declared manifest {attempt.output_manifest_hash[:12]} is not {recomputed[:12]}"
        )
    if ctx.sub.get_blob(substrate.blob_hash(raw)) != raw:
        return Verdict("S2-02", MUST, FAIL, "the stdout bytes are not stored under their own content hash")
    return Verdict("S2-02", MUST, PASS, f"canonical JSON in and out; manifest {recomputed[:12]} rebuilds from stdout")


def _manifest_from_child_bytes(ctx, attempt, raw):
    artifacts = {"output.json": (substrate.blob_hash(raw), len(raw))}
    scratch = Path(ctx.scratch_root) / attempt.attempt_id / "scratch"
    for path in sorted(scratch.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        data = path.read_bytes()
        artifacts[str(path.relative_to(scratch))] = (substrate.blob_hash(data), len(data))
    return substrate.output_manifest_hash(artifacts)


def check_captured_seed(subject, ctx):
    document = dict(subject.inputs)
    if "seed" not in document:
        return Verdict("S2-03", MUST, FAIL, "seed is not an input field")
    first = _stdout_bytes(ctx, _launch(subject, ctx, salt="s2-03-a"))
    again = _stdout_bytes(ctx, _launch(subject, ctx, salt="s2-03-b"))
    if first != again:
        return Verdict("S2-03", MUST, FAIL, "two runs under one seed are not byte-equal")
    other = dict(document, seed=document["seed"] + 1)
    differing = _stdout_bytes(ctx, _launch(subject, ctx, inputs=other, salt="s2-03-c", seed=other["seed"]))
    if _without_seed(differing) == _without_seed(first):
        return Verdict("S2-03", MUST, FAIL, "a second seed changes only the echoed seed, so nothing is drawn from it")
    return Verdict("S2-03", MUST, PASS, f"seed {document['seed']} replays byte-equal; seed {other['seed']} draws apart")


def _without_seed(raw):
    document = json.loads(raw)
    document.pop("seed", None)
    return json.dumps(document, sort_keys=True, separators=(",", ":"))


def check_corpus_origins(subject, ctx):
    doc = _corpus(subject)
    cases = doc.get("cases") or []
    if not cases:
        return Verdict("S2-04", MUST, FAIL, f"{subject.corpus_path.name} vendors no cases")
    for case in cases:
        for name, entry in case["fields"].items():
            origin = entry.get("origin")
            if origin not in ORIGIN_VOCABULARY:
                return Verdict("S2-04", MUST, FAIL, f"case {case['id']} field {name} declares origin {origin!r}")
    return Verdict("S2-04", MUST, PASS, f"{len(cases)} vendored cases, every field carries a declared origin")


def check_ledger_and_floor(subject, ctx):
    doc = _corpus(subject)
    cases = doc.get("cases") or []
    for case in cases:
        if case.get("ledger") not in LEDGER_VOCABULARY:
            return Verdict("S2-05", MUST, FAIL, f"case {case['id']} declares ledger {case.get('ledger')!r}")
    floor = doc.get("pass_floor")
    if not isinstance(floor, int) or isinstance(floor, bool) or floor < 1 or floor > len(cases):
        return Verdict("S2-05", MUST, FAIL, f"pass_floor {floor!r} is not an integer in [1, {len(cases)}]")
    return Verdict("S2-05", MUST, PASS, f"{len(cases)} ledgered cases with a committed pass_floor of {floor}")


def check_floor_is_attributed(subject, ctx):
    doc = _corpus(subject)
    floor = doc.get("pass_floor")
    result = certified(subject, ctx)
    if floor > result["passes"]:
        return Verdict("S2-06", MUST, FAIL, f"pass_floor {floor} exceeds the measured {result['passes']} passes")
    row = ctx.sub.get_certificate(result["identity_bundle_hash"])
    recorded = json.loads(row["selftest_summary"])["floor"]
    if recorded != floor:
        return Verdict("S2-06", MUST, FAIL, f"the certificate records floor {recorded}, the corpus commits {floor}")
    golden = json.loads((ctx.repo_root / "tests" / "goldens" / f"{subject.floor_golden}.golden").read_text())
    if golden["floor"] != floor:
        return Verdict("S2-06", MUST, FAIL, f"the committed golden holds floor {golden['floor']}, the corpus {floor}")
    return Verdict("S2-06", MUST, PASS, f"floor {floor} <= {result['passes']} measured, and matches row and golden")


def check_golden_certificate(subject, ctx):
    result = certified(subject, ctx)
    identity_hash = result["identity_bundle_hash"]
    row = ctx.sub.get_certificate(identity_hash)
    if row is None:
        return Verdict("S2-07", MUST, FAIL, f"no skill_certificates row for {identity_hash[:12]}")
    if not ctx.sub.certified(identity_hash):
        return Verdict("S2-07", MUST, FAIL, f"certified() is false for {identity_hash[:12]}")
    recomputed = substrate.certificate_hash(
        row["identity_bundle_hash"], row["transcript_hash"], row["env_manifest_hash"]
    )
    if recomputed != row["cert_hash"]:
        return Verdict("S2-07", MUST, FAIL, f"cert_hash {row['cert_hash'][:12]} does not recompute from the row")
    return Verdict("S2-07", MUST, PASS, f"cert {row['cert_hash'][:12]} recomputes from its own row and is certified")


def check_byte_equal_double_run(subject, ctx):
    first = subject.transcript(subject, ctx)
    second = subject.transcript(subject, ctx)
    if first != second:
        return Verdict("S2-08", MUST, FAIL, f"transcript bytes differ across two runs: {len(first)} vs {len(second)}")
    digest = selftest.transcript_digest(first)
    return Verdict("S2-08", MUST, PASS, f"{len(first)} transcript bytes, byte-equal twice, digest {digest[:12]}")


def check_declared_cost_profile(subject, ctx):
    module = imported(subject)
    cost = getattr(module, "COST_PROFILE", None)
    if not isinstance(cost, profile.CostProfile):
        return Verdict("S2-09", MUST, FAIL, f"COST_PROFILE is {type(cost).__name__}, not a CostProfile")
    if not isinstance(cost.tier, int) or isinstance(cost.tier, bool):
        return Verdict("S2-09", MUST, FAIL, f"tier {cost.tier!r} is not an integer")
    if not cost.production.per_size or not cost.verification.grade:
        return Verdict("S2-09", MUST, FAIL, "the profile declares no production sizes or no verification component")
    sizes = cost.declared_sizes()
    evaluation = cost.evaluate(sizes[0])
    fields = (evaluation.expected_wall_s, evaluation.expected_core_s, evaluation.expected_verification_core_s)
    if not all(isinstance(v, float) and v > 0 for v in fields):
        return Verdict("S2-09", MUST, FAIL, f"evaluate({sizes[0]}) returned {fields}")
    undeclared = max(sizes) + 1
    try:
        cost.evaluate(undeclared)
    except profile.ProfileUndeclared:
        return Verdict("S2-09", MUST, PASS, f"tier {cost.tier}, sizes {list(sizes)}, ProfileUndeclared at {undeclared}")
    return Verdict("S2-09", MUST, FAIL, f"evaluate({undeclared}) did not raise ProfileUndeclared")


def check_disagree_semantics(subject, ctx):
    module = imported(subject)
    seam = getattr(module, "SEAM", None)
    if not isinstance(seam, str) or "." not in seam:
        return Verdict("S2-10", MUST, FAIL, f"the subject declares no seam for its cross-check: {seam!r}")
    attempt = _launch(
        subject,
        ctx,
        module="skills.harness_child",
        salt="s2-10",
        env_extra={"CAIRN_HARNESS_SUBJECT": subject.module, "CAIRN_HARNESS_MODE": "seam"},
    )
    document = json.loads(_stdout_bytes(ctx, attempt))
    if document.get("status") != runner.STATUS_DISAGREE:
        return Verdict("S2-10", MUST, FAIL, f"a planted disagreement at {seam} still returned {document.get('status')}")
    transcripts = document.get("transcripts")
    if not isinstance(transcripts, list) or len(transcripts) < 2:
        return Verdict("S2-10", MUST, FAIL, f"DISAGREE carries {transcripts!r} rather than both transcripts")
    digests = [t.get("digest") for t in transcripts]
    if len(set(digests)) != len(digests):
        return Verdict("S2-10", MUST, FAIL, "the two transcripts share a digest, so neither records a disagreement")
    stored = ctx.sub.get_blob(substrate.blob_hash(_stdout_bytes(ctx, attempt)))
    if stored is None or not all(d and d.encode() in stored for d in digests):
        return Verdict("S2-10", MUST, FAIL, "the transcript digests do not reach a substrate node")
    if ctx.sub.serve(attempt.recipe_key) is not None:
        return Verdict("S2-10", MUST, FAIL, "a DISAGREE attempt is served from cache")
    return Verdict(
        "S2-10", MUST, PASS, f"{seam} planted: DISAGREE, digests {digests[0][:8]}/{digests[1][:8]}, never served"
    )


def check_no_substrate_handle(subject, ctx):
    attempt = _launch(
        subject,
        ctx,
        module="skills.harness_child",
        salt="s2-11",
        env_extra={"CAIRN_HARNESS_SUBJECT": subject.module, "CAIRN_HARNESS_MODE": "env-dump"},
    )
    dump = json.loads(_stderr_bytes(ctx, attempt).splitlines()[0])
    leaked = sorted(k for k in dump["environ"] if k.startswith(runner.SCRUB_PREFIX))
    if leaked:
        return Verdict("S2-11", MUST, FAIL, f"the child environment holds {leaked}")
    carrying = sorted(k for k, v in dump["environ"].items() if SUBSTRATE_PATH_MARK in str(v))
    if carrying:
        return Verdict("S2-11", MUST, FAIL, f"the child environment carries a substrate path in {carrying}")
    if any(SUBSTRATE_PATH_MARK in str(arg) for arg in dump["argv"]):
        return Verdict("S2-11", MUST, FAIL, f"argv carries a substrate path: {dump['argv']}")
    source = Path(str(inspect.getsourcefile(imported(subject)))).read_text()
    if SUBSTRATE_ENV_RE.search(source):
        return Verdict("S2-11", MUST, FAIL, f"{subject.module} reads a {runner.SCRUB_PREFIX}* variable of its own")
    return Verdict("S2-11", MUST, PASS, f"{len(dump['environ'])} child variables, none a substrate handle; argv clean")


def check_axis_declaration(subject, ctx):
    module = imported(subject)
    axis = getattr(module, "CROSS_CHECK_AXIS", None)
    if axis not in AXES:
        return Verdict("S2-12", MUST, FAIL, f"cross_check.axis {axis!r} is not one of {list(AXES)}")
    declared = getattr(module, "INDEPENDENT_RANGE", None)
    if not isinstance(declared, Mapping) or not declared:
        return Verdict("S2-12", MUST, FAIL, f"independent_range {declared!r} is not an interval record")
    for name, interval in declared.items():
        if name not in subject.inputs:
            return Verdict("S2-12", MUST, FAIL, f"independent_range names {name!r}, which is not an input field")
        if not (isinstance(interval, (list, tuple)) and len(interval) == 2 and interval[0] <= interval[1]):
            return Verdict("S2-12", MUST, FAIL, f"independent_range[{name!r}] = {interval!r} is not an interval")
    outside = json.loads(_stdout_bytes(ctx, _launch(subject, ctx, inputs=subject.out_of_range_inputs, salt="s2-12")))
    if outside["cross_check"]["result"] != "untested":
        return Verdict(
            "S2-12", MUST, FAIL, f"outside {declared} the cross-check reports {outside['cross_check']['result']!r}"
        )
    summary = certified(subject, ctx)["summary"]["cross_check"]
    if set(summary) != {"axis", "independent_range"}:
        return Verdict("S2-12", MUST, FAIL, f"the ledger's cross_check block claims more than an axis: {summary}")
    return Verdict("S2-12", MUST, PASS, f"axis {axis}, range {dict(declared)}, untested outside it and in the ledger")


def check_numeric_profile(subject, ctx):
    module = imported(subject)
    numeric = module.identity_bundle()["numeric_profile"]
    document = json.loads(_stdout_bytes(ctx, _launch(subject, ctx, salt="s2-13")))
    if not _emits_float(document):
        if numeric is None:
            return Verdict("S2-13", SHOULD, NA, "the subject emits no floats, so no numeric profile is owed")
        return Verdict("S2-13", SHOULD, PASS, f"numeric_profile {numeric!r} declared although no float is emitted")
    if numeric is None:
        return Verdict("S2-13", SHOULD, FAIL, "the subject emits floats and declares no numeric profile")
    return Verdict("S2-13", SHOULD, PASS, f"numeric_profile {numeric!r} declared for a float-emitting subject")


def _emits_float(value):
    if isinstance(value, float):
        return True
    if isinstance(value, Mapping):
        return any(_emits_float(v) for v in value.values())
    if isinstance(value, list):
        return any(_emits_float(v) for v in value)
    return False


def check_postcondition_arm(subject, ctx):
    tier = imported(subject).COST_PROFILE.tier
    if tier != 0:
        return Verdict("S2-14", SHOULD, NA, f"tier {tier} is not the Tier-0 arithmetic case")
    if subject.postcondition is None:
        return Verdict("S2-14", SHOULD, FAIL, "a Tier-0 subject declares no postcondition arm")
    held, refused = subject.postcondition(subject, ctx)
    if not held:
        return Verdict("S2-14", SHOULD, FAIL, "the postcondition refused the subject's own answer")
    if not refused:
        return Verdict("S2-14", SHOULD, FAIL, "the postcondition accepted a planted wrong answer")
    return Verdict("S2-14", SHOULD, PASS, "the postcondition holds on the real answer and refuses a planted one")


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
        "the skill declares its axis - implementation or algorithm - and the input range over which that axis is "
        "independent ... a cross-check that has never disagreed is reported as untested, not as passing",
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
    expected_must_failures=frozenset({"S2-01", "S2-04", "S2-10", "S2-11"}),
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

SUBJECTS = (TOY_CURVE, NONCONFORMING, WITNESS)
SUBJECTS_BY_NAME = {subject.name: subject for subject in SUBJECTS}
EXPECTED_SHOULD = {
    "toy_curve": {"S2-13": NA, "S2-14": PASS},
    "nonconforming": {"S2-13": NA, "S2-14": FAIL},
    "witness": {"S2-13": FAIL, "S2-14": FAIL},
}
