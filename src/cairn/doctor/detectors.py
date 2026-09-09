import os
import re
import sqlite3
import stat
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cairn import attest, bundle, kat, log, pari, substrate

lg = log.get("doctor.detect")

BREW_LINE = "brew install pari"
PIN_MODE = 0o444
ATTEST_MODE = 0o644
APPEND_FLAG = stat.UF_APPEND
GP_MAJOR_MINOR = "2.17"
GP_STACK_BYTES = 64_000_000
GITIGNORE_ENTRIES = (".doctor/", "var/")
UV_INDEX_LINES = '[[tool.uv.index]]\nname = "pypi"\nurl = "https://pypi.org/simple"\ndefault = true'
TRIGGER_RE = re.compile(r"CREATE TRIGGER IF NOT EXISTS (\w+)")

ERROR = "error"
WARN = "warn"
INFO = "info"

F_MODES = "F-modes"
F_DIRS = "F-dirs"


@dataclass(frozen=True)
class Finding:
    id: str
    subsystem: str
    severity: str
    message: str
    evidence: str
    fixable: bool
    recommended_command: str
    fixer: str | None = None
    target: str | None = None
    want_mode: int | None = None
    want_flags: int | None = None

    def as_dict(self):
        return {
            "id": self.id,
            "subsystem": self.subsystem,
            "severity": self.severity,
            "message": self.message,
            "evidence": self.evidence,
            "fixable": self.fixable,
            "recommended_command": self.recommended_command,
            "fixer": self.fixer,
        }


@dataclass(frozen=True)
class Context:
    root: Path
    db: Path
    bundle: Path
    pin: Path
    attest: Path
    quick: bool = False


def selftest_command(ctx):
    return f"cairn selftest toy-curve --db {ctx.db} --bundle {ctx.bundle} --pin {ctx.pin}"


def repin_command(ctx):
    return bundle.repin_sequence(ctx.bundle, ctx.pin)


def _mode_of(path):
    return stat.S_IMODE(Path(path).stat().st_mode)


def _flags_of(path):
    return Path(path).stat().st_flags


def d_gp_binary(ctx):
    if not Path(pari.GP_BIN).is_file():
        return [
            Finding(
                "D-gp-binary/absent",
                "gp",
                ERROR,
                "the gp binary named by cairn.pari.GP_BIN is not a file",
                f"{pari.GP_BIN}: absent",
                False,
                BREW_LINE,
            )
        ]
    if ctx.quick:
        return []
    rc, out, err = pari.run_gp(["--version-short"], "")
    version = out.strip()
    if rc != 0 or not version:
        return [
            Finding(
                "D-gp-binary/version-refused",
                "gp",
                ERROR,
                "gp --version-short did not print a version",
                f"{pari.GP_BIN}: rc={rc} stdout={out!r} stderr={err!r}",
                False,
                BREW_LINE,
            )
        ]
    if ".".join(version.split(".")[:2]) != GP_MAJOR_MINOR:
        return [
            Finding(
                "D-gp-binary/version-drift",
                "gp",
                ERROR,
                f"gp is not {GP_MAJOR_MINOR}.x; every vendored known answer was probed against it",
                f"{pari.GP_BIN}: {version}",
                False,
                BREW_LINE,
            )
        ]
    return []


def d_gp_facts(ctx):
    if ctx.quick or not Path(pari.GP_BIN).is_file():
        return []
    rc, out, err = pari.run_gp([], 'print("OK")')
    if (rc, out.strip(), err) == (0, "OK", ""):
        return []
    return [
        Finding(
            "D-gp-facts/stdin-script",
            "gp",
            ERROR,
            "one stdin line through cairn.pari.run_gp did not return rc 0 / OK / empty stderr",
            f"{' '.join(pari.gp_argv())}: rc={rc} stdout={out!r} stderr={err!r}",
            False,
            BREW_LINE,
        )
    ]


def _corpus_case_one():
    from cairn import selftest

    fields = selftest.load_corpus()["cases"][0]["fields"]
    return {name: fields[name]["value"] for name in ("p", "a", "b", "n")}


def d_pari_inprocess(ctx):
    findings = []
    size = pari.pari.stacksize()
    if size < GP_STACK_BYTES:
        findings.append(
            Finding(
                "D-pari-inprocess/stack",
                "pari",
                ERROR,
                "the in-process PARI stack is smaller than the 64 MB cairn.pari allocates at import",
                f"stacksize={size} want>={GP_STACK_BYTES}",
                False,
                "reinstall the environment: uv sync",
            )
        )
    case = _corpus_case_one()
    card = int(pari.ellcard(pari.pari.ellinit([case["a"], case["b"]], case["p"])))
    if card != case["n"]:
        findings.append(
            Finding(
                "D-pari-inprocess/ellcard",
                "pari",
                ERROR,
                "cypari2 ellcard disagrees with the vendored corpus case 1",
                f"ellinit([{case['a']},{case['b']}],{case['p']}): ellcard={card} want={case['n']}",
                False,
                selftest_command(ctx),
            )
        )
    version = pari.pari_versions()["libpari"]
    if not version.startswith(GP_MAJOR_MINOR + "."):
        findings.append(
            Finding(
                "D-pari-inprocess/libpari-version",
                "pari",
                ERROR,
                f"libpari is not {GP_MAJOR_MINOR}.x",
                f"cypari2 pari.version(): {version}",
                False,
                "reinstall the environment: uv sync",
            )
        )
    return findings


def d_bundle(ctx):
    for path, what in ((ctx.bundle, "gate bundle"), (ctx.pin, "gate-bundle pin")):
        if not Path(path).is_file():
            return [
                Finding(
                    "D-bundle/absent",
                    "deploy",
                    ERROR,
                    f"the {what} is absent; every gate reads through it",
                    f"{path}: absent",
                    False,
                    repin_command(ctx),
                )
            ]
    try:
        rows = bundle.read_rows(ctx.bundle)
    except sqlite3.Error as exc:
        return [
            Finding(
                "D-bundle/unreadable",
                "deploy",
                ERROR,
                "the gate bundle does not open read-only as a SQLite database",
                f"{ctx.bundle}: {type(exc).__name__}: {exc}",
                False,
                repin_command(ctx),
            )
        ]
    computed = bundle.bundle_hash(rows)
    pinned = bundle.read_pin(ctx.pin)
    if computed != pinned:
        return [
            Finding(
                "D-bundle/pin-mismatch",
                "deploy",
                ERROR,
                "the gate bundle's recomputed hash differs from the pin; every gate fails closed until it is re-pinned",
                f"{ctx.bundle}: {computed} != {ctx.pin}: {pinned}",
                False,
                repin_command(ctx),
            )
        ]
    return []


def _mode_findings(path, prefix, subsystem, want_mode, want_flags, recommended):
    findings = []
    mode, flags = _mode_of(path), _flags_of(path)
    if mode != want_mode:
        findings.append(
            Finding(
                f"{prefix}/mode",
                subsystem,
                ERROR,
                f"mode is {mode:04o}, want {want_mode:04o}",
                f"{path}: mode={mode:04o}",
                True,
                recommended,
                F_MODES,
                str(path),
                want_mode,
                want_flags,
            )
        )
    if not flags & APPEND_FLAG:
        findings.append(
            Finding(
                f"{prefix}/flag",
                subsystem,
                ERROR,
                "the uappnd flag is clear; the file can be rewritten in place",
                f"{path}: flags={flags:#x}",
                True,
                recommended,
                F_MODES,
                str(path),
                want_mode,
                want_flags,
            )
        )
    return findings


def d_pin_mode(ctx):
    if not Path(ctx.pin).is_file():
        return []
    return _mode_findings(ctx.pin, "D-pin-mode", "deploy", PIN_MODE, APPEND_FLAG, "cairn doctor --fix")


def _waiver_finding(ctx, body):
    try:
        gate = bundle.GateBundle.open(ctx.bundle, ctx.pin)
    except Exception:
        return [
            Finding(
                "D-attest-mode/waiver-unchecked",
                "deploy",
                INFO,
                "record 0 could not be compared with the fixture waiver: the gate bundle does not open",
                f"{ctx.attest}: record 0 unchecked",
                False,
                repin_command(ctx),
            )
        ]
    want = attest.waiver_canonical(attest.fixture_waiver(gate.waiver_target()))
    if bytes(body) == bytes(want):
        return []
    return [
        Finding(
            "D-attest-mode/waiver",
            "deploy",
            ERROR,
            "record 0 of the attestation file is not this bundle's fixture waiver",
            f"{ctx.attest}: record 0 = {substrate.blob_hash(body)}, want {substrate.blob_hash(want)}",
            False,
            f"cairn attest init --attest {ctx.attest} --bundle {ctx.bundle} --pin {ctx.pin}",
        )
    ]


def d_attest_mode(ctx):
    if not Path(ctx.attest).is_file():
        return [
            Finding(
                "D-attest-mode/absent",
                "deploy",
                ERROR,
                "the attestation file is absent; the gate plan's fixture waiver lives at record 0",
                f"{ctx.attest}: absent",
                False,
                f"cairn attest init --attest {ctx.attest} --bundle {ctx.bundle} --pin {ctx.pin}",
            )
        ]
    findings = _mode_findings(ctx.attest, "D-attest-mode", "deploy", ATTEST_MODE, APPEND_FLAG, "cairn doctor --fix")
    size = Path(ctx.attest).stat().st_size
    parsed = list(attest.records(ctx.attest))
    consumed = sum(attest.LENGTH_BYTES + len(body) for _, body in parsed)
    if consumed != size:
        findings.append(
            Finding(
                "D-attest-mode/framing",
                "deploy",
                ERROR,
                "the attestation file has trailing bytes that do not frame a record",
                f"{ctx.attest}: {len(parsed)} records consume {consumed} of {size} bytes",
                False,
                f"cairn attest init --attest {ctx.attest} --bundle {ctx.bundle} --pin {ctx.pin}",
            )
        )
        return findings
    if not parsed:
        findings.append(
            Finding(
                "D-attest-mode/empty",
                "deploy",
                ERROR,
                "the attestation file holds no records; record 0 must be the fixture waiver",
                f"{ctx.attest}: 0 records",
                False,
                f"cairn attest init --attest {ctx.attest} --bundle {ctx.bundle} --pin {ctx.pin}",
            )
        )
        return findings
    return findings + _waiver_finding(ctx, parsed[0][1])


def _expected_triggers():
    return set(TRIGGER_RE.findall(substrate.SCHEMA_PATH.read_text()))


def d_substrate(ctx):
    if not Path(ctx.db).exists():
        return [
            Finding(
                "D-substrate/absent",
                "substrate",
                INFO,
                "the substrate does not exist yet; the first certifying run creates it",
                f"{ctx.db}: absent",
                False,
                selftest_command(ctx),
            )
        ]
    if not os.access(ctx.db, os.R_OK):
        return [
            Finding(
                "D-substrate/unreadable",
                "substrate",
                ERROR,
                "this process cannot open the substrate read-only",
                f"{ctx.db}: mode={_mode_of(ctx.db):04o} uid={Path(ctx.db).stat().st_uid}",
                False,
                f"chmod u+r {ctx.db}",
            )
        ]
    findings = []
    conn = None
    try:
        conn = sqlite3.connect(f"file:{ctx.db}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        # the connect is lazy, so a file that is not a database first says so here
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    except sqlite3.Error as exc:
        if conn is not None:
            conn.close()
        return [
            Finding(
                "D-substrate/unopenable",
                "substrate",
                ERROR,
                "the substrate does not open read-only as a SQLite database",
                f"{ctx.db}: {type(exc).__name__}: {exc}",
                False,
                selftest_command(ctx),
            )
        ]
    try:
        if mode != "wal":
            findings.append(
                Finding(
                    "D-substrate/journal-mode",
                    "substrate",
                    ERROR,
                    "journal_mode is not wal; concurrent readers are not what the substrate assumes",
                    f"{ctx.db}: journal_mode={mode}",
                    False,
                    selftest_command(ctx),
                )
            )
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if integrity != "ok":
            findings.append(
                Finding(
                    "D-substrate/integrity",
                    "substrate",
                    ERROR,
                    "PRAGMA integrity_check did not return ok",
                    f"{ctx.db}: integrity_check={integrity}",
                    False,
                    selftest_command(ctx),
                )
            )
        present = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'")}
        missing = sorted(_expected_triggers() - present)
        if missing:
            findings.append(
                Finding(
                    "D-substrate/triggers",
                    "substrate",
                    ERROR,
                    "append-only triggers are missing; rows the schema forbids updating could be updated",
                    f"{ctx.db}: missing {', '.join(missing)}",
                    False,
                    selftest_command(ctx),
                )
            )
            return findings
        running = conn.execute(
            "SELECT count(*) FROM attempts WHERE status = 'RUNNING' AND ended_at IS NULL"
        ).fetchone()[0]
        if running:
            findings.append(
                Finding(
                    "D-substrate/running-attempts",
                    "substrate",
                    WARN,
                    "attempts left RUNNING by a dead harness are still eligible; a startup scan closes them",
                    f"{ctx.db}: {running} rows with status='RUNNING' and ended_at IS NULL",
                    False,
                    f"cairn startup-scan --db {ctx.db}",
                )
            )
    finally:
        conn.close()
    return findings


def d_kat(_ctx):
    failures = kat.run()
    if not failures:
        return []
    return [
        Finding(
            "D-kat/mismatch",
            "gates",
            ERROR,
            "the canonicalizer known-answer vectors do not reproduce; every hash downstream is suspect",
            f"{kat.DEFAULT_VECTORS}: {'; '.join(failures)}",
            False,
            "cairn kat canon --json",
        )
    ]


def d_certificate(ctx):
    if not Path(ctx.db).is_file() or not os.access(ctx.db, os.R_OK):
        return []
    from cairn.skills import toy_curve

    try:
        identity = toy_curve.skill_identity_hash()
    except pari.GpMissing:
        return []
    try:
        with substrate.Substrate.open(ctx.db, role="reader") as sub:
            certificate = sub.get_certificate(identity)
    except (sqlite3.Error, substrate.SubstrateError) as exc:
        return [
            Finding(
                "D-certificate/unreadable",
                "gates",
                ERROR,
                "the certificate lookup could not open the substrate; D-substrate names the shape it is in",
                f"{ctx.db}: {type(exc).__name__}: {exc}",
                False,
                selftest_command(ctx),
            )
        ]
    if certificate is not None:
        return []
    return [
        Finding(
            "D-certificate/uncertified",
            "gates",
            ERROR,
            "the toy_curve identity in this checkout carries no certificate; no run may use it",
            f"{ctx.db}: no skill_certificates row for identity_bundle_hash {identity}",
            False,
            selftest_command(ctx),
        )
    ]


def _gitignore_missing(root):
    path = Path(root) / ".gitignore"
    if not path.is_file():
        return list(GITIGNORE_ENTRIES)
    lines = {line.strip() for line in path.read_text().splitlines()}
    return [entry for entry in GITIGNORE_ENTRIES if entry not in lines]


def d_dirs(ctx):
    findings = []
    for name in ("deploy", "var"):
        path = Path(ctx.root) / name
        if not path.is_dir():
            findings.append(
                Finding(
                    f"D-dirs/{name}-absent",
                    "dirs",
                    ERROR,
                    f"{name}/ does not exist; the commands that write there fail on the open, not on a check",
                    f"{path}: absent",
                    True,
                    "cairn doctor --fix",
                    F_DIRS,
                    str(path),
                )
            )
        elif not os.access(path, os.W_OK):
            findings.append(
                Finding(
                    f"D-dirs/{name}-unwritable",
                    "dirs",
                    ERROR,
                    f"{name}/ is not writable by this process",
                    f"{path}: mode={_mode_of(path):04o}",
                    False,
                    f"chmod u+w {path}",
                )
            )
    missing = _gitignore_missing(ctx.root)
    if missing:
        findings.append(
            Finding(
                "D-dirs/gitignore",
                "dirs",
                WARN,
                "run artifacts and runtime state would be offered to git",
                f"{Path(ctx.root) / '.gitignore'}: missing {', '.join(missing)}",
                True,
                "cairn doctor --fix",
                F_DIRS,
                str(Path(ctx.root) / ".gitignore"),
            )
        )
    return findings


def d_uv_index(ctx):
    path = Path(ctx.root) / "pyproject.toml"
    if not path.is_file():
        return [
            Finding(
                "D-uv-index/absent",
                "project",
                INFO,
                "pyproject.toml is absent, so nothing pins the package index",
                f"{path}: absent",
                False,
                f"add to {path}:\n{UV_INDEX_LINES}",
            )
        ]
    text = path.read_text()
    if "[[tool.uv.index]]" in text and "https://pypi.org/simple" in text and "default = true" in text:
        return []
    return [
        Finding(
            "D-uv-index/unpinned",
            "project",
            INFO,
            "pyproject.toml does not pin PyPI as the default index; a corporate mirror in ~/.config/uv/uv.toml wins",
            f"{path}: no [[tool.uv.index]] naming https://pypi.org/simple as default",
            False,
            f"add to {path}:\n{UV_INDEX_LINES}",
        )
    ]


@dataclass(frozen=True)
class Detector:
    id: str
    subsystem: str
    fn: Callable
    summary: str


DETECTORS = (
    Detector("D-gp-binary", "gp", d_gp_binary, "GP_BIN exists and reports 2.17.x at rc 0"),
    Detector("D-gp-facts", "gp", d_gp_facts, "one stdin line through run_gp returns rc 0 / OK / empty stderr"),
    Detector("D-pari-inprocess", "pari", d_pari_inprocess, "cypari2 stack, corpus case 1 ellcard, libpari version"),
    Detector("D-bundle", "deploy", d_bundle, "the gate bundle opens and its recomputed hash equals the pin"),
    Detector("D-pin-mode", "deploy", d_pin_mode, "the pin is 0444 and carries uappnd"),
    Detector("D-attest-mode", "deploy", d_attest_mode, "the attestation file is 0644+uappnd and frames its records"),
    Detector("D-substrate", "substrate", d_substrate, "wal, integrity_check, append-only triggers, RUNNING attempts"),
    Detector("D-kat", "gates", d_kat, "the canonicalizer known-answer vectors reproduce"),
    Detector("D-certificate", "gates", d_certificate, "the toy_curve identity in this checkout is certified"),
    Detector("D-dirs", "dirs", d_dirs, "deploy/ and var/ exist and are writable; .doctor/ and var/ are gitignored"),
    Detector("D-uv-index", "project", d_uv_index, "pyproject.toml pins PyPI as the default index"),
)
SUBSYSTEMS = tuple(sorted({d.subsystem for d in DETECTORS}))
QUICK_SKIPPED = ("D-gp-facts", "D-kat")
# D-gp-binary keeps its isfile half under --quick and drops only the version probe,
# so neither "runs" nor "skipped" describes it.
QUICK_PARTIAL = ("D-gp-binary",)
UNDER_QUICK_FULL = "full"
UNDER_QUICK_PARTIAL = "partial"
UNDER_QUICK_SKIPPED = "skipped"


def under_quick(detector_id):
    if detector_id in QUICK_SKIPPED:
        return UNDER_QUICK_SKIPPED
    if detector_id in QUICK_PARTIAL:
        return UNDER_QUICK_PARTIAL
    return UNDER_QUICK_FULL


def detect(ctx, *, only=None):
    findings = []
    for detector in DETECTORS:
        if only and detector.subsystem not in only:
            continue
        if ctx.quick and detector.id in QUICK_SKIPPED:
            lg.info("skip", detector=detector.id, reason="quick")
            continue
        found = detector.fn(ctx)
        lg.info("detector", detector=detector.id, findings=[f.id for f in found])
        findings += found
    return findings
