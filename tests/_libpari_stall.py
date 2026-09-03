import sys

import pytest
from cysignals.alarm import AlarmInterrupt

# The session deadline exits 124 for a run killed by a time limit; a libpari call past its
# bound is the same event seen from inside the process, so a .check.log reader sees one code.
EXIT_CODE = 124


def _stall_type():
    module = sys.modules.get("cairn.pari")
    return None if module is None else module.PariStall


def reason_for(nodeid, exc):
    stall = _stall_type()
    if stall is not None and isinstance(exc, stall):
        return f"libpari stall in {nodeid}: {exc}; no later test ran because libpari is unusable in this process"
    return (
        f"libpari bound fired after its call returned in {nodeid}: {exc!r}; "
        "no later test ran because the timer that landed belonged to a bounded call"
    )


@pytest.hookimpl(wrapper=True)
def pytest_runtest_protocol(item, nextitem):
    try:
        return (yield)
    except AlarmInterrupt as exc:
        pytest.exit(reason_for(item.nodeid, exc), returncode=EXIT_CODE)
