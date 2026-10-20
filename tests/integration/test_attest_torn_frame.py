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


def _assert_whole(path):
    size = Path(path).stat().st_size
    assert sum(attest.LENGTH_BYTES + len(body) for _, body in attest.records(path)) == size


@pytest.mark.parametrize(
    "torn",
    [
        (100).to_bytes(8, "little") + b"x" * 30,
        (100).to_bytes(8, "little")[:3],
        (100).to_bytes(8, "little"),
    ],
    ids=["body", "prefix", "prefix-only"],
)
def test_a_record_appended_after_a_torn_frame_is_found_by_enumeration(tmp_path, clear_flags, torn):
    path = _log(tmp_path, clear_flags)
    _tear(path, torn)
    offset = attest.append_record(path, b"after the torn frame")
    assert attest.read_record(path, offset) == b"after the torn frame"
    assert (offset, b"after the torn frame") in list(attest.records(path))
    _assert_whole(path)


def test_an_untorn_log_appends_at_its_end(tmp_path, clear_flags):
    path = _log(tmp_path, clear_flags)
    size = Path(path).stat().st_size
    offset = attest.append_record(path, b"next")
    assert offset == size
    _assert_whole(path)


def test_a_torn_frame_claiming_an_implausible_length_refuses_and_leaves_the_log_unchanged(tmp_path, clear_flags):
    path = _log(tmp_path, clear_flags)
    _tear(path, (1 << 40).to_bytes(8, "little") + b"x")
    before = Path(path).read_bytes()
    with pytest.raises(attest.AttestationError, match="torn frame"):
        attest.append_record(path, b"never written")
    assert Path(path).read_bytes() == before
