import importlib
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from cairn import keys, runner, substrate

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
# The harness measures conformance, never speed, so the ceiling only has to be
# generous enough that a loaded machine does not kill a subject mid-run. toy_curve
# declares 0.13s at 40 bits; under the full suite, which keeps several PARI
# processes busy, 8x that is not enough and the child is SIGTERMed with an empty
# stdout.
CEILING_MULTIPLIER = 60


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
    cross_check_inputs: Mapping = field(default_factory=dict)


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


class LaunchFailed(RuntimeError):
    pass


def _stdout_bytes(ctx, attempt):
    return (Path(ctx.scratch_root) / attempt.attempt_id / "stdout").read_bytes()


def _document(ctx, attempt):
    """The subject's output document, or a refusal that names what the launch did.

    An empty stdout parses as a JSONDecodeError, which reads as a defect in the
    subject and is the wrong verdict entirely: the launch was killed, so the clause
    was never measured.
    """
    raw = _stdout_bytes(ctx, attempt)
    if not raw.strip():
        killed = attempt.launch is not None and attempt.launch.timed_out
        detail = "was killed at its ceiling" if killed else "wrote nothing to stdout"
        raise LaunchFailed(f"the launch {detail} with status {attempt.status}, so the clause was not measured")
    return json.loads(raw)


def _stderr_bytes(ctx, attempt):
    return (Path(ctx.scratch_root) / attempt.attempt_id / "stderr").read_bytes()
