import errno
import os
import platform
import stat
import sys

import pytest

from cairn import log

pytestmark = pytest.mark.skipif(
    sys.platform != "darwin",
    reason="uappnd is a macOS/BSD chflags bit; the Linux chattr +a probe belongs to the M1 container bead",
)

SEED = "seed\n"


def _append(path):
    with path.open("a") as fh:
        fh.write("x\n")


def _os_open_append(path):
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    try:
        os.write(fd, b"y\n")
    finally:
        os.close(fd)


def _open_w(path):
    with path.open("w") as fh:
        fh.write("z")


def _open_rplus(path):
    with path.open("r+") as fh:
        fh.write("z")


def _truncate(path):
    os.truncate(path, 0)


def _chmod(path):
    path.chmod(0o600)


def _unlink(path):
    path.unlink()


def _rename(path):
    path.rename(str(path) + ".moved")


OPS = {
    "append": _append,
    "os_open_append": _os_open_append,
    "open_w": _open_w,
    "open_rplus": _open_rplus,
    "truncate": _truncate,
    "chmod": _chmod,
    "unlink": _unlink,
    "rename": _rename,
}

EFFECTS = {
    "append": lambda p: p.read_text() == SEED + "x\n",
    "os_open_append": lambda p: p.read_text() == SEED + "y\n",
    "open_w": lambda p: p.read_text() == "z",
    "open_rplus": lambda p: p.read_text() == "zeed\n",
    "truncate": lambda p: p.stat().st_size == 0,
    "chmod": lambda p: stat.S_IMODE(p.stat().st_mode) == 0o600,
    "unlink": lambda p: not os.path.lexists(p),
    "rename": lambda p: not os.path.lexists(p) and os.path.lexists(str(p) + ".moved"),
}

ROLES = {
    (0o644, True): "attest",
    (0o444, True): "pin",
    (0o444, False): "readonly",
    (0o644, False): "control",
}

ROWS = [
    (0o644, True, "append", None),
    (0o644, True, "os_open_append", None),
    (0o644, True, "open_w", errno.EPERM),
    (0o644, True, "open_rplus", errno.EPERM),
    (0o644, True, "truncate", errno.EPERM),
    (0o644, True, "chmod", errno.EPERM),
    (0o644, True, "unlink", errno.EPERM),
    (0o644, True, "rename", errno.EPERM),
    (0o444, True, "append", errno.EACCES),
    (0o444, True, "os_open_append", errno.EACCES),
    (0o444, True, "open_w", errno.EPERM),
    (0o444, True, "open_rplus", errno.EPERM),
    (0o444, True, "truncate", errno.EPERM),
    (0o444, True, "chmod", errno.EPERM),
    (0o444, True, "unlink", errno.EPERM),
    (0o444, True, "rename", errno.EPERM),
    (0o444, False, "append", errno.EACCES),
    (0o444, False, "os_open_append", errno.EACCES),
    (0o444, False, "open_w", errno.EACCES),
    (0o444, False, "open_rplus", errno.EACCES),
    (0o444, False, "truncate", errno.EACCES),
    (0o444, False, "chmod", None),
    (0o444, False, "unlink", None),
    (0o444, False, "rename", None),
    (0o644, False, "append", None),
    (0o644, False, "os_open_append", None),
    (0o644, False, "open_w", None),
    (0o644, False, "open_rplus", None),
    (0o644, False, "truncate", None),
    (0o644, False, "chmod", None),
    (0o644, False, "unlink", None),
    (0o644, False, "rename", None),
]


def _row_id(mode, flagged, op, expected_errno):
    outcome = "OK" if expected_errno is None else errno.errorcode[expected_errno]
    return f"{ROLES[(mode, flagged)]}-{mode:04o}-{'uappnd' if flagged else 'noflag'}-{op}-{outcome}"


@pytest.fixture
def flagged_files(tmp_path):
    created = []

    def make(name, mode, flagged):
        path = tmp_path / name
        path.write_text(SEED)
        path.chmod(mode)
        if flagged:
            os.chflags(path, stat.UF_APPEND)
        created.append(path)
        return path

    yield make
    for path in created:
        for candidate in (path, path.with_name(path.name + ".moved")):
            if os.path.lexists(candidate):
                os.chflags(candidate, 0)
                candidate.chmod(0o644)


def _env():
    return {
        "os": f"{platform.system()} {platform.mac_ver()[0]} {platform.release()} {platform.machine()}",
        "uid": os.getuid(),
    }


@pytest.mark.parametrize(
    ("mode", "flagged", "op", "expected_errno"),
    ROWS,
    ids=[_row_id(*row) for row in ROWS],
)
def test_mode_x_uappnd_x_op_by_owner(flagged_files, mode, flagged, op, expected_errno):
    lg = log.get("grounding.fs")
    path = flagged_files(f"{ROLES[(mode, flagged)]}.txt", mode, flagged)
    assert bool(path.stat().st_flags & stat.UF_APPEND) is flagged
    try:
        OPS[op](path)
        observed_errno, observed = None, "OK"
    except PermissionError as exc:
        code = errno.errorcode[exc.errno] if exc.errno is not None else "?"
        observed_errno, observed = exc.errno, f"{code} {exc.strerror}"
    lg.info(
        "mode_flag_op",
        command=f"chmod {mode:04o}; {'chflags uappnd; ' if flagged else ''}{op}",
        mode=f"{mode:04o}",
        uappnd=flagged,
        op=op,
        observed=observed,
        expected="OK" if expected_errno is None else errno.errorcode[expected_errno],
        **_env(),
    )
    assert observed_errno == expected_errno
    if expected_errno is None:
        assert EFFECTS[op](path)
    else:
        assert os.path.lexists(path)
        if op in ("append", "os_open_append", "open_w", "open_rplus", "truncate"):
            assert path.read_text() == SEED
        if op == "chmod":
            assert stat.S_IMODE(path.stat().st_mode) == mode
        if op == "rename":
            assert not os.path.lexists(str(path) + ".moved")


@pytest.mark.parametrize(
    ("role", "mode", "truncate_errno_after_clear"),
    [("pin", 0o444, errno.EACCES), ("attest", 0o644, None)],
    ids=["pin-0444-truncate-EACCES-until-chmod", "attest-0644-truncate-OK"],
)
def test_owner_clears_uappnd_then_chmod_truncate_rename_unlink_succeed(
    flagged_files, role, mode, truncate_errno_after_clear
):
    lg = log.get("grounding.fs")
    path = flagged_files(f"{role}.txt", mode, True)
    flags_before = path.stat().st_flags
    os.chflags(path, 0)
    flags_after = path.stat().st_flags
    try:
        os.truncate(path, 0)
        truncate_errno, truncate_observed = None, "OK"
    except PermissionError as exc:
        code = errno.errorcode[exc.errno] if exc.errno is not None else "?"
        truncate_errno, truncate_observed = exc.errno, f"{code} {exc.strerror}"
    size_after_truncate = path.stat().st_size
    path.chmod(0o644)
    os.truncate(path, 0)
    moved = path.with_name(path.name + ".moved")
    path.rename(moved)
    moved.unlink()
    lg.info(
        "owner_clears_flag",
        command=f"chmod {mode:04o}; chflags uappnd; chflags nouappnd; truncate; chmod 0644; truncate; rename; unlink (same uid)",
        role=role,
        mode=f"{mode:04o}",
        flags_before=flags_before,
        flags_after=flags_after,
        truncate_after_clear=truncate_observed,
        size_after_truncate=size_after_truncate,
        observed="chflags nouappnd by the owner succeeded; chmod 0644, truncate, rename, unlink then succeeded",
        **_env(),
    )
    assert flags_before & stat.UF_APPEND
    assert flags_after == 0
    assert truncate_errno == truncate_errno_after_clear
    assert size_after_truncate == (len(SEED) if truncate_errno_after_clear else 0)
    assert not os.path.lexists(path) and not os.path.lexists(moved)
