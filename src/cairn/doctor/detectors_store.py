import os
import sqlite3
from pathlib import Path

from cairn import kat, pari, substrate
from cairn.doctor.detectors_base import (
    ERROR,
    F_DIRS,
    GITIGNORE_ENTRIES,
    INFO,
    UV_INDEX_LINES,
    WARN,
    Finding,
    _mode_of,
    selftest_command,
)


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
        schema_reasons = substrate.schema_mismatches(conn)
        if schema_reasons:
            findings.append(
                Finding(
                    "D-substrate/schema",
                    "substrate",
                    ERROR,
                    "the substrate does not match the shipped schema",
                    f"{ctx.db}: {'; '.join(schema_reasons)}",
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


def d_kat(ctx):
    failures = kat.run(ctx.vectors)
    if not failures:
        return []
    return [
        Finding(
            "D-kat/mismatch",
            "gates",
            ERROR,
            "the canonicalizer known-answer vectors do not reproduce; every hash downstream is suspect",
            f"{ctx.vectors}: {'; '.join(failures)}",
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
