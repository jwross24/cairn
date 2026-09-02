"""The planted-corpus harness: one registry entry per planted artifact, every run cold, one rollup.

A family module `family_<name>.py` beside this file exports ENTRIES, a tuple of Entry, and the
self_check family alone may export EXPECTED_ESCAPES, the ids the rollup must list. discover()
reads them all; registry() refuses an entry the rollup could not judge; observe() runs one entry
on a substrate whose cache refuses to serve; rollup() turns observations into counted escapes.
"""

import importlib.util
import sys
import traceback
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cairn import runner
from cairn.substrate import Substrate

MUST_FAIL = "must-FAIL"
MUST_PASS = "must-PASS"
CLASSES = (MUST_FAIL, MUST_PASS)
INCONCLUSIVE = "INCONCLUSIVE"
SELF_CHECK = "self_check"
LETTERS = tuple("abcdefghijklm")
ITEMS = ("tier_gate", "escrow", "yank", "ladder_execution", "canary")
FAMILIES = LETTERS + ITEMS + (SELF_CHECK,)
PLANTINGS_BAR = 30
CONTROLS_BAR = 4
CORPUS_COMPLETE = False
FAMILY_MODULE_GLOB = "family_*.py"
ENTRIES_NAME = "ENTRIES"
EXPECTED_ESCAPES_NAME = "EXPECTED_ESCAPES"
HARNESS_BUNDLE_HASH = "9c" * 32
ESCAPED = "escaped"
CONTROL_MISMATCH = "control_mismatch"
COLD_CACHE = "cold_cache"
RUN_ERROR = "run_error"
NO_ATTEMPT = "no_attempt"
KINDS = (ESCAPED, CONTROL_MISMATCH, COLD_CACHE, RUN_ERROR, NO_ATTEMPT)
SELF_CHECK_MODULE = "family_self_check"


class RegistryError(ValueError):
    pass


class ColdCacheViolation(AssertionError):
    pass


@dataclass(frozen=True)
class Entry:
    test_id: str
    family: str
    expected_class: str
    expected_verdict: str
    owner_bead: str
    run: Callable
    launches: bool = True


@dataclass(frozen=True)
class Registry:
    entries: tuple
    expected_escapes: frozenset

    def by_id(self, test_id):
        for entry in self.entries:
            if entry.test_id == test_id:
                return entry
        raise KeyError(test_id)

    @property
    def corpus(self):
        return tuple(e for e in self.entries if e.family != SELF_CHECK)

    @property
    def ids(self):
        return tuple(e.test_id for e in self.entries)


def _check_entry(entry):
    if not isinstance(entry, Entry):
        raise RegistryError(f"registry holds a {type(entry).__name__}, not an Entry")
    for name in ("test_id", "family", "expected_class", "expected_verdict", "owner_bead"):
        value = getattr(entry, name)
        if not isinstance(value, str) or not value:
            raise RegistryError(f"{entry.test_id!r}: {name} must be a non-empty str")
    if entry.family not in FAMILIES:
        raise RegistryError(f"{entry.test_id!r}: family {entry.family!r} is not one of {FAMILIES}")
    if entry.expected_class not in CLASSES:
        raise RegistryError(f"{entry.test_id!r}: expected_class {entry.expected_class!r} is not one of {CLASSES}")
    if entry.expected_class == MUST_FAIL and entry.expected_verdict == INCONCLUSIVE:
        raise RegistryError(
            f"{entry.test_id!r}: a {MUST_FAIL} entry landing {INCONCLUSIVE} is an escape, never its target"
        )
    if not callable(entry.run):
        raise RegistryError(f"{entry.test_id!r}: run is not callable")
    if not isinstance(entry.launches, bool):
        raise RegistryError(f"{entry.test_id!r}: launches must be a bool")


def registry(entries, expected_escapes=()):
    entries = tuple(entries)
    seen = set()
    for entry in entries:
        _check_entry(entry)
        if entry.test_id in seen:
            raise RegistryError(f"{entry.test_id!r} is registered twice")
        seen.add(entry.test_id)
    for family in {e.family for e in entries}:
        failing = {e.expected_verdict for e in entries if e.family == family and e.expected_class == MUST_FAIL}
        passing = {e.expected_verdict for e in entries if e.family == family and e.expected_class == MUST_PASS}
        both = sorted(failing & passing)
        if both:
            raise RegistryError(f"family {family!r} registers {both} as both a {MUST_FAIL} and a {MUST_PASS} outcome")
    expected = frozenset(expected_escapes)
    for test_id in sorted(expected):
        if test_id not in seen:
            raise RegistryError(f"expected escape {test_id!r} names no registered entry")
        if next(e for e in entries if e.test_id == test_id).family != SELF_CHECK:
            raise RegistryError(
                f"expected escape {test_id!r} is outside the {SELF_CHECK} family; a corpus entry may never expect one"
            )
    return Registry(entries, expected)


def _load(path):
    name = path.stem
    cached = sys.modules.get(name)
    if cached is not None and getattr(cached, "__file__", None) == str(path):
        return cached
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RegistryError(f"{path} is not importable")
    module = importlib.util.module_from_spec(spec)
    if cached is None:
        sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def discover(directory):
    entries, expected = [], set()
    for path in sorted(Path(directory).glob(FAMILY_MODULE_GLOB)):
        module = _load(path)
        if not hasattr(module, ENTRIES_NAME):
            raise RegistryError(f"{path.name} declares no {ENTRIES_NAME}")
        own = tuple(getattr(module, ENTRIES_NAME))
        if path.stem != SELF_CHECK_MODULE:
            foreign = [e.test_id for e in own if isinstance(e, Entry) and e.family == SELF_CHECK]
            if foreign:
                raise RegistryError(
                    f"{path.name} registers {foreign} under {SELF_CHECK!r}; only {SELF_CHECK_MODULE}.py may"
                )
            if hasattr(module, EXPECTED_ESCAPES_NAME):
                raise RegistryError(f"{path.name} declares {EXPECTED_ESCAPES_NAME}; only {SELF_CHECK_MODULE}.py may")
        entries.extend(own)
        expected.update(getattr(module, EXPECTED_ESCAPES_NAME, ()))
    return registry(entries, expected)


class ColdSubstrate(Substrate):
    def serve(self, recipe_key):
        raise ColdCacheViolation(f"a fixture run asked the cache to serve recipe {recipe_key}")


class Cold:
    def __init__(self, sub, scratch_root):
        self.sub = sub
        self.scratch_root = Path(scratch_root)
        self.bundle_hash = HARNESS_BUNDLE_HASH

    def launch(self, skill_module, recipe, **kw):
        if kw.get("skip_cache_lookup") is False:
            raise ColdCacheViolation(f"a fixture asked to launch {skill_module} with the cache lookup on")
        kw["skip_cache_lookup"] = True
        kw.setdefault("bundle_hash", self.bundle_hash)
        kw.setdefault("scratch_root", self.scratch_root)
        return runner.launch(self.sub, skill_module, recipe, **kw)


@dataclass(frozen=True)
class Observation:
    test_id: str
    observed_verdict: str | None
    attempts: tuple
    violation: str | None = None
    error: str | None = None


def _last_rowid(sub):
    row = sub.conn.execute("SELECT max(rowid) AS last FROM attempts").fetchone()
    return row["last"] or 0


def _attempt_rows_since(sub, rowid):
    rows = sub.conn.execute(
        "SELECT attempt_id, skip_cache_lookup, status FROM attempts WHERE rowid > ? ORDER BY rowid", (rowid,)
    ).fetchall()
    return tuple((r["attempt_id"], r["skip_cache_lookup"], r["status"]) for r in rows)


def observe(entry, *, db_path, scratch_root):
    sub = ColdSubstrate.open(db_path, role="writer")
    try:
        start = _last_rowid(sub)
        cold = Cold(sub, scratch_root)
        verdict, violation, error = None, None, None
        try:
            verdict = entry.run(cold)
        except ColdCacheViolation as exc:
            violation = str(exc)
        except Exception:
            error = traceback.format_exc()
        rows = _attempt_rows_since(sub, start)
        warm = [attempt_id for attempt_id, skip, _ in rows if skip != 1]
        if warm and violation is None:
            violation = f"attempt(s) started with the cache lookup on: {warm}"
        if verdict is not None and not isinstance(verdict, str):
            error = f"run returned a {type(verdict).__name__}, not a verdict str"
            verdict = None
        return Observation(entry.test_id, verdict, rows, violation, error)
    finally:
        sub.close()


@dataclass(frozen=True)
class Escape:
    test_id: str
    family: str
    kind: str
    detail: str


def _judge(entry, obs):
    if obs.violation is not None:
        return Escape(entry.test_id, entry.family, COLD_CACHE, obs.violation)
    if obs.error is not None:
        return Escape(entry.test_id, entry.family, RUN_ERROR, obs.error)
    if entry.launches and not obs.attempts:
        return Escape(entry.test_id, entry.family, NO_ATTEMPT, "registered as launching a skill, ran no attempt")
    if obs.observed_verdict == entry.expected_verdict:
        return None
    if entry.expected_class == MUST_FAIL:
        landed = "INCONCLUSIVE" if obs.observed_verdict == INCONCLUSIVE else repr(obs.observed_verdict)
        return Escape(entry.test_id, entry.family, ESCAPED, f"landed {landed}, expected {entry.expected_verdict!r}")
    return Escape(
        entry.test_id,
        entry.family,
        CONTROL_MISMATCH,
        f"landed {obs.observed_verdict!r}, expected {entry.expected_verdict!r}",
    )


@dataclass(frozen=True)
class Rollup:
    registry: Registry
    observations: dict
    escapes: tuple

    def family(self, name):
        return tuple(e for e in self.escapes if e.family == name)

    @property
    def corpus_escapes(self):
        return tuple(e for e in self.escapes if e.family != SELF_CHECK)

    @property
    def plantings(self):
        return sum(1 for e in self.registry.corpus if e.expected_class == MUST_FAIL)

    @property
    def controls(self):
        return sum(1 for e in self.registry.corpus if e.expected_class == MUST_PASS)

    @property
    def bars_met(self):
        return self.plantings >= PLANTINGS_BAR and self.controls >= CONTROLS_BAR

    @property
    def self_check_as_declared(self):
        return {e.test_id for e in self.family(SELF_CHECK)} == set(self.registry.expected_escapes)

    def shortfall(self):
        return (
            f"plantings {self.plantings}/{PLANTINGS_BAR}, positive controls {self.controls}/{CONTROLS_BAR}"
            f" (the {SELF_CHECK} family is excluded from both)"
        )

    def report(self):
        lines = [self.shortfall()]
        lines.extend(f"{e.kind} {e.test_id} [{e.family}]: {e.detail}" for e in self.escapes)
        return "\n".join(lines)


def rollup(registry, observations):
    escapes = []
    for entry in registry.entries:
        if entry.test_id not in observations:
            raise RegistryError(f"{entry.test_id!r} was never observed")
        escape = _judge(entry, observations[entry.test_id])
        if escape is not None:
            escapes.append(escape)
    return Rollup(registry, dict(observations), tuple(escapes))
