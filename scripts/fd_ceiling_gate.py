from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

EXIT_OK = 0
EXIT_REFUSED = 2
EXIT_ENVIRONMENT = 3
EXIT_USAGE = 64
SYSCTL_TIMEOUT_SECONDS = 5
SKIP_ENV = "CAIRN_FD_CEILING_SKIP"


@dataclass(frozen=True)
class Snapshot:
    used: int
    maximum: int


def parse_snapshot(stdout: bytes, stderr: bytes) -> Snapshot:
    if stderr:
        raise ValueError("sysctl wrote to stderr")
    try:
        lines = stdout.decode("ascii").splitlines()
    except UnicodeDecodeError as exc:
        raise ValueError("sysctl output is not ASCII") from exc
    if len(lines) != 2 or any(re.fullmatch(r"[0-9]+", line) is None for line in lines):
        raise ValueError("sysctl output must contain exactly two ASCII decimal integers")
    used, maximum = (int(line) for line in lines)
    if maximum <= 0:
        raise ValueError("kern.maxfiles must be greater than zero")
    return Snapshot(used=used, maximum=maximum)


def has_minimum_free_capacity(snapshot: Snapshot) -> bool:
    return (snapshot.maximum - snapshot.used) * 5 >= snapshot.maximum


def read_snapshot() -> Snapshot:
    completed = subprocess.run(
        ["sysctl", "-n", "kern.num_files", "kern.maxfiles"],
        capture_output=True,
        check=False,
        timeout=SYSCTL_TIMEOUT_SECONDS,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"sysctl exited {completed.returncode}")
    return parse_snapshot(completed.stdout, completed.stderr)


def append_log(log: Path, event: str) -> None:
    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    with log.open("a", encoding="ascii") as handle:
        handle.write(f"{stamp} {event}\n")


def deny_for_log_failure(log: Path, exc: OSError | UnicodeError) -> int:
    print(f"[fd-ceiling] INFRASTRUCTURE DENY: cannot write {log}: {exc}", file=sys.stderr)
    return EXIT_ENVIRONMENT


def log_and_print(log: Path, event: str, message: str, code: int) -> int:
    try:
        append_log(log, event)
    except (OSError, UnicodeError) as exc:
        return deny_for_log_failure(log, exc)
    if event.startswith("FD-INFRA-DENY"):
        message += f"\n              bypass (logged): {SKIP_ENV}='<reason>'"
    print(message, file=sys.stderr)
    return code


def is_valid_reason(reason: str) -> bool:
    return bool(reason.strip()) and "\n" not in reason and "\r" not in reason


def run(log: Path) -> int:
    skip = os.environ.get(SKIP_ENV)
    if skip is not None:
        if is_valid_reason(skip):
            return log_and_print(
                log,
                f"FD-BYPASS {SKIP_ENV} reason={skip}",
                f"[fd-ceiling] BYPASS: {SKIP_ENV}={skip} (logged to {log.name})",
                EXIT_OK,
            )
        return log_and_print(
            log,
            f"FD-INFRA-DENY invalid {SKIP_ENV} reason",
            f"[fd-ceiling] INFRASTRUCTURE DENY: {SKIP_ENV} requires a nonblank single-line reason.",
            EXIT_ENVIRONMENT,
        )
    try:
        snapshot = read_snapshot()
    except subprocess.TimeoutExpired:
        return log_and_print(
            log,
            "FD-INFRA-DENY sysctl timed out",
            "[fd-ceiling] INFRASTRUCTURE DENY: sysctl timed out before capacity could be read.",
            EXIT_ENVIRONMENT,
        )
    except (OSError, RuntimeError, ValueError, UnicodeError) as exc:
        return log_and_print(
            log,
            f"FD-INFRA-DENY {exc}",
            f"[fd-ceiling] INFRASTRUCTURE DENY: {exc}",
            EXIT_ENVIRONMENT,
        )
    event = f"used={snapshot.used} maximum={snapshot.maximum} min_free=20%"
    if has_minimum_free_capacity(snapshot):
        return log_and_print(log, f"FD-CLEAR {event}", "[fd-ceiling] CLEAR: " + event, EXIT_OK)
    return log_and_print(
        log,
        f"FD-CEILING {event}",
        "[fd-ceiling] BLOCKED: " + event + "; free at least 20% of the file descriptor capacity and retry.",
        EXIT_REFUSED,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=None)
    parser.add_argument("--log", default=None)
    try:
        ns = parser.parse_args(argv)
    except SystemExit as exc:
        return EXIT_OK if exc.code in (0, None) else EXIT_USAGE
    root = Path(ns.root).resolve() if ns.root else Path(__file__).resolve().parents[1]
    return run(Path(ns.log) if ns.log else root / ".check.log")


if __name__ == "__main__":
    raise SystemExit(main())
