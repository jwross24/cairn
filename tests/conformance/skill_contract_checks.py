import inspect
import json
import shutil
from pathlib import Path

from skill_contract_base import (
    FAIL,
    IDENTITY_FIELDS,
    INTERFACE_VERSION_RE,
    LEDGER_VOCABULARY,
    MUST,
    ORIGIN_VOCABULARY,
    PASS,
    SUBSTRATE_ENV_RE,
    SUBSTRATE_PATH_MARK,
    Verdict,
    _corpus,
    _document,
    _launch,
    _stderr_bytes,
    _stdout_bytes,
    certified,
    imported,
)

from cairn import profile, runner, selftest, substrate


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
    first_attempt = _launch(subject, ctx, salt="s2-03-a")
    _document(ctx, first_attempt)
    first = _stdout_bytes(ctx, first_attempt)
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
        row["identity_bundle_hash"], row["transcript_hash"], row["env_manifest_hash"], row["selftest_summary"]
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


def _declared_seam(module):
    seam = getattr(module, "SEAM", None)
    return seam if isinstance(seam, str) and "." in seam else None


def _launch_with_planted_seam(subject, ctx, salt):
    return _launch(
        subject,
        ctx,
        module="skills.harness_child",
        salt=salt,
        env_extra={"CAIRN_HARNESS_SUBJECT": subject.module, "CAIRN_HARNESS_MODE": "seam"},
    )


def check_disagree_semantics(subject, ctx):
    module = imported(subject)
    seam = _declared_seam(module)
    if seam is None:
        declared = getattr(module, "SEAM", None)
        return Verdict("S2-10", MUST, FAIL, f"the subject declares no seam for its cross-check: {declared!r}")
    attempt = _launch_with_planted_seam(subject, ctx, "s2-10")
    document = _document(ctx, attempt)
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
