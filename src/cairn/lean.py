import json
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from cairn import log

REPO_ROOT = Path(__file__).resolve().parents[2]
PINS_PATH = REPO_ROOT / "bundle" / "lean.json"
PROJECT_DIR = REPO_ROOT / "lean"
TOOLCHAIN_FILE = PROJECT_DIR / "lean-toolchain"
MANIFEST_PATH = PROJECT_DIR / "lake-manifest.json"
MANIFEST_KIND = "lake_manifest"
RESOLVER = "elan"
TOOLS = ("lean", "lake", "leanchecker")
NO_TOOLCHAINS = "no installed toolchains"
DEFAULT_TIMEOUT_S = 600.0
VERSION_RE = re.compile(
    r"^Lean \(version (?P<version>[^,]+), (?P<target>[^,]+), commit (?P<commit>[0-9a-f]{40}), (?P<build>[^)]+)\)"
)

lg = log.get("lean")


class LeanMissing(RuntimeError):
    pass


class LeanTimeout(RuntimeError):
    def __init__(self, argv, timeout_s):
        super().__init__(f"{argv[0]} exceeded {timeout_s}s and was killed")
        self.argv = argv
        self.timeout_s = timeout_s


class LeanPinMismatch(RuntimeError):
    def __init__(self, pinned, observed):
        super().__init__(f"lean toolchain pin {pinned} differs from the toolchain that resolved {observed}")
        self.pinned = pinned
        self.observed = observed


@dataclass(frozen=True)
class Run:
    argv: tuple
    cwd: str | None
    rc: int
    stdout: str
    stderr: str
    wall_ms: float


def elan_home():
    return Path(os.environ.get("ELAN_HOME") or Path.home() / ".elan")


def tool_path(tool):
    if tool != RESOLVER and tool not in TOOLS:
        raise ValueError(f"{tool!r} is not a pinned lean tool; choose from {TOOLS}")
    return elan_home() / "bin" / tool


def tool_paths():
    return {str(tool_path(tool)) for tool in (RESOLVER, *TOOLS)}


def source_pins():
    return json.loads(PINS_PATH.read_text())


def manifest_object(path=MANIFEST_PATH):
    return json.loads(Path(path).read_text())


def manifest_rev(manifest, package="mathlib"):
    for entry in manifest.get("packages", []):
        if entry.get("name") == package:
            return entry.get("rev")
    return None


def toolchain_version(toolchain):
    return toolchain.rsplit(":", 1)[-1].removeprefix("v")


def argv(pins, tool, *args):
    if tool not in TOOLS:
        raise ValueError(f"{tool!r} takes no +toolchain; choose from {TOOLS}")
    return [str(tool_path(tool)), f"+{pins['toolchain']}", *args]


def resolver_argv(*args):
    return [str(tool_path(RESOLVER)), *args]


def command(pins, name, **fields):
    tool, *rest = pins["checker"][name]
    return argv(pins, tool, *(part.format(**fields) for part in rest))


def run(pins, tool, args, *, cwd=None, timeout_s=DEFAULT_TIMEOUT_S):
    return run_argv(argv(pins, tool, *args), cwd=cwd, timeout_s=timeout_s)


def run_argv(cmd, *, cwd=None, timeout_s=DEFAULT_TIMEOUT_S):
    if not Path(cmd[0]).is_file():
        raise LeanMissing(cmd[0])
    env = {**os.environ, "ELAN_HOME": str(elan_home())}
    where = str(cwd) if cwd else None
    lg.debug("spawn", argv=cmd, cwd=where)
    start = time.monotonic()
    proc = subprocess.Popen(
        cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=env, start_new_session=True
    )
    try:
        out, err = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.communicate()
        lg.info("timeout", argv=cmd, pid=proc.pid, timeout_s=timeout_s)
        raise LeanTimeout(cmd, timeout_s) from None
    wall_ms = round((time.monotonic() - start) * 1000, 3)
    lg.info("exit", argv=cmd, cwd=where, rc=proc.returncode, wall_ms=wall_ms)
    return Run(tuple(cmd), where, proc.returncode, out, err, wall_ms)


def parse_toolchain_list(stdout):
    names = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or line == NO_TOOLCHAINS:
            continue
        names.append(line.split()[0])
    return names


def installed_toolchains():
    result = run_argv(resolver_argv("toolchain", "list"))
    if result.rc != 0:
        raise LeanMissing(f"{' '.join(result.argv)}: rc={result.rc} stderr={result.stderr!r}")
    return parse_toolchain_list(result.stdout)


def assert_installed(pins):
    installed = installed_toolchains()
    if pins["toolchain"] not in installed:
        lg.info("toolchain_absent", toolchain=pins["toolchain"], installed=installed, elan_home=str(elan_home()))
        raise LeanMissing(f"toolchain {pins['toolchain']} is not installed under {elan_home()}; installed: {installed}")
    return installed


def version(pins):
    result = run(pins, "lean", ["--version"])
    match = VERSION_RE.match(result.stdout)
    if result.rc != 0 or match is None:
        raise LeanMissing(
            f"{' '.join(result.argv)} did not identify a toolchain: rc={result.rc} "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
    return {**match.groupdict(), "wall_ms": result.wall_ms}


def assert_pinned(pins):
    assert_installed(pins)
    observed = version(pins)
    pinned = {"version": toolchain_version(pins["toolchain"]), "commit": pins["lean_commit"]}
    seen = {key: observed[key] for key in pinned}
    if seen != pinned:
        lg.info("pin_mismatch", pinned=pinned, observed=seen)
        raise LeanPinMismatch(pinned, seen)
    lg.info("pinned", toolchain=pins["toolchain"], commit=observed["commit"], target=observed["target"])
    return observed
