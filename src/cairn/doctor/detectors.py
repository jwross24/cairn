import sqlite3
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cairn import attest, bundle, gateplan, ladderplan, log, pari, substrate
from cairn.doctor.detectors_base import APPEND_FLAG as APPEND_FLAG
from cairn.doctor.detectors_base import ATTEST_MODE as ATTEST_MODE
from cairn.doctor.detectors_base import BREW_LINE as BREW_LINE
from cairn.doctor.detectors_base import ERROR as ERROR
from cairn.doctor.detectors_base import F_DIRS as F_DIRS
from cairn.doctor.detectors_base import F_MODES as F_MODES
from cairn.doctor.detectors_base import GITIGNORE_ENTRIES as GITIGNORE_ENTRIES
from cairn.doctor.detectors_base import GP_MAJOR_MINOR as GP_MAJOR_MINOR
from cairn.doctor.detectors_base import GP_STACK_BYTES as GP_STACK_BYTES
from cairn.doctor.detectors_base import INFO as INFO
from cairn.doctor.detectors_base import PIN_MODE as PIN_MODE
from cairn.doctor.detectors_base import UV_INDEX_LINES as UV_INDEX_LINES
from cairn.doctor.detectors_base import WARN as WARN
from cairn.doctor.detectors_base import Context as Context
from cairn.doctor.detectors_base import Finding as Finding
from cairn.doctor.detectors_base import _flags_of as _flags_of
from cairn.doctor.detectors_base import _mode_of as _mode_of
from cairn.doctor.detectors_base import repin_command as repin_command
from cairn.doctor.detectors_base import selftest_command as selftest_command
from cairn.doctor.detectors_store import _gitignore_missing as _gitignore_missing
from cairn.doctor.detectors_store import d_certificate as d_certificate
from cairn.doctor.detectors_store import d_dirs as d_dirs
from cairn.doctor.detectors_store import d_kat as d_kat
from cairn.doctor.detectors_store import d_substrate as d_substrate
from cairn.doctor.detectors_store import d_uv_index as d_uv_index

lg = log.get("doctor.detect")


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


def d_bundle_plans(ctx):
    if d_bundle(ctx):
        return []
    gate_bundle = bundle.GateBundle.open(ctx.bundle, ctx.pin)
    reasons = []
    for name, parser in (
        ("gate_plan", gateplan.GatePlan.from_bundle),
        ("ladder_plan", ladderplan.LadderPlan.from_bundle),
    ):
        try:
            parser(gate_bundle)
        except (gateplan.PlanInvalid, ladderplan.LadderPlanInvalid, bundle.BundleError) as exc:
            reasons.append(f"{name}: {exc}")
    if not reasons:
        return []
    return [
        Finding(
            "D-bundle-plans/invalid",
            "deploy",
            ERROR,
            "the pinned gate bundle carries a plan the current parsers refuse",
            f"{ctx.bundle}: {'; '.join(reasons)}",
            False,
            repin_command(ctx),
        )
    ]


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
    Detector("D-bundle-plans", "deploy", d_bundle_plans, "the pinned bundle's gate and ladder plans parse read-only"),
    Detector("D-pin-mode", "deploy", d_pin_mode, "the pin is 0444 and carries uappnd"),
    Detector("D-attest-mode", "deploy", d_attest_mode, "the attestation file is 0644+uappnd and frames its records"),
    Detector("D-substrate", "substrate", d_substrate, "wal, integrity_check, shipped schema, RUNNING attempts"),
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
