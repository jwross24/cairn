import faulthandler
import math
import os
import sys
import threading

import pytest

SECONDS_VAR = "CAIRN_SESSION_DEADLINE"
SKIP_VAR = "CAIRN_SESSION_DEADLINE_SKIP"
# Twice the idle full-run wall time on the development Mac (1424-1483 s, 2026-09-02), rounded,
# so a run under load average 6-9 (2053 s, 2026-09-03) finishes inside it; CI sets 900 through
# ci.yml. Revisit when an idle run passes half of it.
DEFAULT_SECONDS = 3000
# pytest reserves 0-5 and so does src/cairn/exits.py, so neither offers a code that reads as
# "killed by a time limit"; 124 is timeout(1)'s, which a .check.log reader already knows.
TIMEOUT_EXIT_CODE = 124
# faulthandler's later-dump exits with this and offers no way to change it, so the banner on
# stderr, not the code, is what tells a deadline kill from an ordinary failure.
BACKSTOP_EXIT_CODE = 1
# Long enough that the watchdog thread always wins when it is merely slow to wake and dump,
# and far inside the gap between CI's 900 s deadline and its 20-minute job ceiling.
BACKSTOP_GRACE = 15
JOIN_TIMEOUT_S = 5
THREAD_NAME = "cairn-session-deadline"

_active = None
_backstop_owner = None


def _usage_error(raw, complaint):
    return pytest.UsageError(
        f"{SECONDS_VAR}={raw!r} {complaint}. "
        f"Unset it for the {DEFAULT_SECONDS} s default, "
        f"or set {SKIP_VAR}='<reason>' to run with no session deadline."
    )


def resolve_seconds(raw):
    if raw is None or not raw.strip():
        return float(DEFAULT_SECONDS)
    try:
        seconds = float(raw)
    except ValueError:
        raise _usage_error(raw, "is not a number of seconds") from None
    if not math.isfinite(seconds) or seconds <= 0:
        raise _usage_error(raw, "is not a positive, finite number of seconds")
    return seconds


def format_elapsed(seconds):
    whole = int(seconds)
    hours, rest = divmod(whole, 3600)
    minutes, secs = divmod(rest, 60)
    text = f"{hours}:{minutes:02d}:{secs:02d}"
    fraction = seconds - whole
    if fraction:
        text += f"{fraction:.6f}"[1:]
    return text


class SessionDeadline:
    def __init__(self, seconds, fd):
        self.seconds = seconds
        self.fd = fd
        self.released = False
        self.expired = threading.Event()
        self.thread = threading.Thread(target=self._watch, name=THREAD_NAME, daemon=True)

    def arm(self):
        global _backstop_owner
        self.thread.start()
        # faulthandler owns a single process-global later-dump slot: a nested arm would displace
        # the session's backstop, and its disarm would leave the session with none.
        if _backstop_owner is None:
            _backstop_owner = self
            faulthandler.dump_traceback_later(self.seconds + BACKSTOP_GRACE, exit=True, file=self.fd)
        return self

    def owns_backstop(self):
        return _backstop_owner is self

    def disarm(self):
        global _backstop_owner
        if _backstop_owner is self:
            faulthandler.cancel_dump_traceback_later()
            _backstop_owner = None
        self.expired.set()
        self.thread.join(JOIN_TIMEOUT_S)
        if not self.released:
            self.released = True
            os.close(self.fd)

    def _watch(self):
        if self.expired.wait(self.seconds):
            return
        os.write(self.fd, f"Timeout ({format_elapsed(self.seconds)})!\n".encode())
        faulthandler.dump_traceback(all_threads=True, file=self.fd)
        os._exit(TIMEOUT_EXIT_CODE)


def active_deadline():
    return _active


def pytest_configure(config):
    global _active
    reason = os.environ.get(SKIP_VAR, "").strip()
    if reason:
        os.write(2, f"[deadline] BYPASSED: {reason} ({SKIP_VAR})\n".encode())
        return
    seconds = resolve_seconds(os.environ.get(SECONDS_VAR))
    # Captured fd 2 is redirected once tests start, so the dump needs a handle taken before that.
    fd = os.dup(sys.__stderr__.fileno() if sys.__stderr__ is not None else 2)
    # Two instruments with complementary holes: pytest's bundled faulthandler plugin cancels the
    # C timer on any reported failure, which -p no:faulthandler in addopts prevents, and a
    # GIL-holding C call starves the thread, which only the C timer survives.
    _active = SessionDeadline(seconds, fd).arm()


def pytest_unconfigure(config):
    global _active
    if _active is not None:
        _active.disarm()
        _active = None
