import fcntl
import os
import re
import shutil
import stat
from contextlib import contextmanager
from datetime import UTC, date, datetime, time
from pathlib import Path

from cairn.doctor import artifacts, mutate

RUN_ID_RE = re.compile(r"(?P<stamp>\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}Z)__[0-9a-f]{6}(?:-[1-9]\d{0,2})?")


class UnsafeCollection(Exception):
    pass


class CollectionFailure(Exception):
    def __init__(self, cause, candidates, removed, cleared_flags, path):
        super().__init__(str(cause))
        self.candidates = [_public_candidate(candidate) for candidate in candidates]
        self.removed = list(removed)
        self.cleared_flags = list(cleared_flags)
        self.path = str(path) if path is not None else None


def parse_cutoff(value):
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return datetime.combine(date.fromisoformat(value), time.min, UTC)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})", value):
        raise ValueError("expected YYYY-MM-DD or a timezone-aware ISO-8601 instant")
    instant = datetime.fromisoformat(value)
    if instant.utcoffset() is None:
        raise ValueError("the cutoff instant must include a timezone")
    return instant.astimezone(UTC)


def _lstat(path):
    try:
        return Path(path).lstat()
    except FileNotFoundError:
        return None


def _require_directory(path, label):
    st = _lstat(path)
    if st is None:
        return False
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
        raise UnsafeCollection(f"unsafe {label}: {path} must be a real directory")
    return True


def _layout(root):
    root = Path(root)
    doctor = root / artifacts.DOCTOR_DIRNAME
    runs = doctor / artifacts.RUNS_DIRNAME
    if not _require_directory(doctor, ".doctor directory"):
        return doctor, runs, False
    if not _require_directory(runs, ".doctor/runs directory"):
        return doctor, runs, False
    return doctor, runs, True


def _created_at(run_id):
    match = RUN_ID_RE.fullmatch(run_id)
    if match is None:
        return None
    try:
        stamp = match.group("stamp")
        return datetime(
            int(stamp[0:4]),
            int(stamp[5:7]),
            int(stamp[8:10]),
            int(stamp[11:13]),
            int(stamp[14:16]),
            int(stamp[17:19]),
            tzinfo=UTC,
        )
    except ValueError:
        return None


def _latest_target(root):
    latest = Path(root) / artifacts.DOCTOR_DIRNAME / artifacts.LATEST_NAME
    st = _lstat(latest)
    if st is None:
        return None
    if not stat.S_ISLNK(st.st_mode):
        raise UnsafeCollection(f"unsafe latest path: {latest} must be a symlink to one direct run")
    target = str(latest.readlink())
    match = re.fullmatch(r"runs/([^/]+)", target)
    if match is None or _created_at(match.group(1)) is None:
        raise UnsafeCollection(f"unsafe latest target: {latest} -> {target}")
    run_path = artifacts.runs_dir(root) / match.group(1)
    run_stat = _lstat(run_path)
    if run_stat is None or stat.S_ISLNK(run_stat.st_mode) or not stat.S_ISDIR(run_stat.st_mode):
        raise UnsafeCollection(f"unsafe latest target: {latest} does not point to one direct run directory")
    return match.group(1)


def _validate_tree(candidate):
    stack = [Path(candidate)]
    paths = []
    while stack:
        path = stack.pop()
        st = _lstat(path)
        if st is None:
            raise UnsafeCollection(f"candidate changed during validation: {path}")
        if stat.S_ISLNK(st.st_mode):
            raise UnsafeCollection(f"symlink in selected run: {path}")
        paths.append(path)
        if stat.S_ISDIR(st.st_mode):
            try:
                with os.scandir(path) as entries:
                    children = [Path(entry.path) for entry in entries]
            except OSError as exc:
                raise UnsafeCollection(f"cannot inspect selected run {path}: {exc}") from exc
            stack.extend(children)
    return paths


def _select(root, cutoff):
    doctor, runs, present = _layout(root)
    latest = _latest_target(root) if _lstat(doctor) is not None else None
    if not present:
        return doctor, runs, []
    selected = []
    try:
        children = list(os.scandir(runs))
    except OSError as exc:
        raise UnsafeCollection(f"cannot inspect {runs}: {exc}") from exc
    for entry in children:
        created_at = _created_at(entry.name)
        if created_at is None or created_at >= cutoff:
            continue
        candidate = runs / entry.name
        st = _lstat(candidate)
        if st is None:
            raise UnsafeCollection(f"candidate changed during selection: {candidate}")
        if stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
            raise UnsafeCollection(f"unsafe selected run: {candidate} must be a real directory")
        paths = _validate_tree(candidate)
        selected.append(
            {
                "run_id": entry.name,
                "created_at": created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "path": str(candidate),
                "latest": entry.name == latest,
                "_paths": paths,
            }
        )
    selected.sort(key=lambda candidate: candidate["run_id"])
    return doctor, runs, selected


@contextmanager
def _shared_lock(root):
    lock_path = Path(root) / mutate.LOCK_RELPATH
    st = _lstat(lock_path)
    if st is None:
        yield
        return
    if stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode):
        raise UnsafeCollection(f"unsafe doctor lock: {lock_path}")
    with lock_path.open("rb") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
        except OSError as exc:
            raise mutate.ConcurrencyLost(lock_path, "another doctor process") from exc
        try:
            yield
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _validate_lock_path(root):
    lock_path = Path(root) / mutate.LOCK_RELPATH
    st = _lstat(lock_path)
    if st is not None and (stat.S_ISLNK(st.st_mode) or not stat.S_ISREG(st.st_mode)):
        raise UnsafeCollection(f"unsafe doctor lock: {lock_path} must be a regular file")


def _public_candidate(candidate):
    return {key: value for key, value in candidate.items() if key != "_paths"}


def _refuse_latest(selected):
    latest = next((candidate for candidate in selected if candidate["latest"]), None)
    if latest is not None:
        raise UnsafeCollection(f"refusing entire batch: {latest['path']} is the target of .doctor/latest")


def collect(root, cutoff, *, yes=False):
    cutoff = parse_cutoff(cutoff) if isinstance(cutoff, str) else cutoff.astimezone(UTC)
    root = Path(root)
    if not yes:
        _layout(root)
        _validate_lock_path(root)
        with _shared_lock(root):
            _, _, selected = _select(root, cutoff)
            _refuse_latest(selected)
            return {
                "dry_run": True,
                "candidates": [_public_candidate(candidate) for candidate in selected],
                "removed": [],
                "cleared_flags": [],
            }
    _, _, initial = _select(root, cutoff)
    if not initial:
        return {"dry_run": False, "candidates": [], "removed": [], "cleared_flags": []}
    _refuse_latest(initial)
    _validate_lock_path(root)
    with mutate.acquire(root):
        _, _, selected = _select(root, cutoff)
        _refuse_latest(selected)
        candidate_paths = []
        cleared_flags = []
        for candidate in selected:
            current = _validate_tree(candidate["path"])
            candidate_paths.append((candidate, current))
        removed = []
        current_path = None
        try:
            for _candidate, paths in candidate_paths:
                for path in paths:
                    current_path = path
                    st = _lstat(path)
                    if st is None or stat.S_ISLNK(st.st_mode):
                        raise UnsafeCollection(f"candidate changed before flag clearing: {path}")
                    if st.st_flags:
                        os.chflags(path, 0, follow_symlinks=False)
                        cleared_flags.append({"path": str(path), "flags": st.st_flags})
            for candidate, _ in candidate_paths:
                path = Path(candidate["path"])
                current_path = path
                st = _lstat(path)
                if st is None or stat.S_ISLNK(st.st_mode) or not stat.S_ISDIR(st.st_mode):
                    raise UnsafeCollection(f"candidate changed before removal: {path}")
                if not shutil.rmtree.avoids_symlink_attacks:
                    raise UnsafeCollection("this platform cannot safely remove a directory tree")
                shutil.rmtree(path)
                removed.append(candidate["run_id"])
        except (OSError, UnsafeCollection) as exc:
            raise CollectionFailure(exc, selected, removed, cleared_flags, current_path) from exc
        return {
            "dry_run": False,
            "candidates": [_public_candidate(candidate) for candidate in selected],
            "removed": removed,
            "cleared_flags": cleared_flags,
        }
