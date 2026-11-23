import stat
from dataclasses import dataclass
from pathlib import Path

from cairn import bundle, kat

BREW_LINE = "brew install pari"
PIN_MODE = 0o444
ATTEST_MODE = 0o644
APPEND_FLAG = stat.UF_APPEND
GP_MAJOR_MINOR = "2.17"
GP_STACK_BYTES = 64_000_000
GITIGNORE_ENTRIES = (".doctor/", "var/")
UV_INDEX_LINES = '[[tool.uv.index]]\nname = "pypi"\nurl = "https://pypi.org/simple"\ndefault = true'
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
    vectors: Path = kat.DEFAULT_VECTORS


def selftest_command(ctx):
    return f"cairn selftest toy-curve --db {ctx.db} --bundle {ctx.bundle} --pin {ctx.pin}"


def repin_command(ctx):
    return bundle.repin_sequence(ctx.bundle, ctx.pin)


def _mode_of(path):
    return stat.S_IMODE(Path(path).stat().st_mode)


def _flags_of(path):
    return Path(path).stat().st_flags
