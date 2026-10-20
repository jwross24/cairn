import os
import stat
from pathlib import Path

import pytest

from cairn import attest


def _log(tmp_path, clear_flags):
    path = tmp_path / "attestations.log"
    clear_flags(path)
    attest.init(path, "d4" * 32)
    assert not hasattr(os, "chflags") or path.stat().st_flags & stat.UF_APPEND
    return path


def _tear(path, raw):
    with Path(path).open("ab") as fh:
        fh.write(raw)


def _string_tail_tear():
    record = attest.waiver_canonical(attest.fixture_waiver("e5" * 32))
    return attest.frame(record)[:-1]


@pytest.mark.parametrize(
    "torn",
    [
        (100).to_bytes(8, "little") + b"x" * 30,
        (100).to_bytes(8, "little")[:3],
        (0).to_bytes(8, "little")[:3],
        (100).to_bytes(8, "little"),
        (1 << 40).to_bytes(8, "little") + b"x",
        _string_tail_tear(),
    ],
    ids=["body", "prefix", "zero-length-prefix", "prefix-only", "implausible-length", "string-tail"],
)
def test_an_append_after_a_torn_frame_refuses_and_leaves_the_log_unchanged(tmp_path, clear_flags, torn):
    path = _log(tmp_path, clear_flags)
    whole = Path(path).stat().st_size
    before_records = list(attest.records(path))
    _tear(path, torn)
    before = Path(path).read_bytes()
    with pytest.raises(attest.AttestationError, match=f"torn frame at offset {whole} \\({len(torn)} bytes present\\)"):
        attest.append_record(path, b"never written")
    assert Path(path).read_bytes() == before
    assert list(attest.records(path)) == before_records
    assert attest.read_record(path, whole) is None


def test_an_untorn_log_appends_at_its_end(tmp_path, clear_flags):
    path = _log(tmp_path, clear_flags)
    size = Path(path).stat().st_size
    offset = attest.append_record(path, b"next")
    assert offset == size
    assert attest.read_record(path, offset) == b"next"
    assert sum(attest.LENGTH_BYTES + len(body) for _, body in attest.records(path)) == Path(path).stat().st_size
