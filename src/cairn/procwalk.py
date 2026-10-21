import ctypes
import ctypes.util
import sys
from pathlib import Path

PROC_PIDTBSDINFO = 3
PROC_ALL_CAP = 8192
PROC_CHILD_CAP = 1024


class BsdInfo(ctypes.Structure):
    _fields_ = [
        ("flags", ctypes.c_uint32),
        ("status", ctypes.c_uint32),
        ("xstatus", ctypes.c_uint32),
        ("pid", ctypes.c_uint32),
        ("ppid", ctypes.c_uint32),
        ("uid", ctypes.c_uint32),
        ("gid", ctypes.c_uint32),
        ("ruid", ctypes.c_uint32),
        ("rgid", ctypes.c_uint32),
        ("svuid", ctypes.c_uint32),
        ("svgid", ctypes.c_uint32),
        ("rfu", ctypes.c_uint32),
        ("comm", ctypes.c_char * 16),
        ("name", ctypes.c_char * 32),
        ("nfiles", ctypes.c_uint32),
        ("pgid", ctypes.c_uint32),
        ("pjobc", ctypes.c_uint32),
        ("tdev", ctypes.c_uint32),
        ("tpgid", ctypes.c_uint32),
        ("nice", ctypes.c_int32),
        ("start_sec", ctypes.c_uint64),
        ("start_usec", ctypes.c_uint64),
    ]


def _load_libproc():
    path = ctypes.util.find_library("proc")
    if path is None:
        return None
    lib = ctypes.CDLL(path, use_errno=True)
    lib.proc_listpgrppids.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_int]
    lib.proc_listpgrppids.restype = ctypes.c_int
    lib.proc_listallpids.argtypes = [ctypes.c_void_p, ctypes.c_int]
    lib.proc_listallpids.restype = ctypes.c_int
    lib.proc_pidinfo.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_uint64, ctypes.c_void_p, ctypes.c_int]
    lib.proc_pidinfo.restype = ctypes.c_int
    lib.proc_listchildpids.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_int]
    lib.proc_listchildpids.restype = ctypes.c_int
    return lib


def _darwin_lister(lib, cap):
    def lister(pgid):
        buf = (ctypes.c_uint32 * cap)()
        written = lib.proc_listpgrppids(pgid, ctypes.byref(buf), ctypes.sizeof(buf))
        if written < 0:
            raise OSError(ctypes.get_errno(), "proc_listpgrppids")
        return frozenset(buf[i] for i in range(written))

    return lister


def _darwin_row(lib, pid, info, size):
    if lib.proc_pidinfo(pid, PROC_PIDTBSDINFO, 0, ctypes.byref(info), size) != size:
        return None
    return (info.ppid, info.pgid, (info.start_sec, info.start_usec))


def _darwin_full_table(lib):
    pids = (ctypes.c_int * PROC_ALL_CAP)()
    count = lib.proc_listallpids(ctypes.byref(pids), ctypes.sizeof(pids))
    if count < 0:
        raise OSError(ctypes.get_errno(), "proc_listallpids")
    info = BsdInfo()
    size = ctypes.sizeof(info)
    rows = {}
    for i in range(count):
        pid = pids[i]
        row = _darwin_row(lib, pid, info, size) if pid > 0 else None
        if row is not None:
            rows[pid] = row
    return rows


def _darwin_table(lib):
    def table(leader):
        children = (ctypes.c_int * PROC_CHILD_CAP)()
        child_bytes = ctypes.sizeof(children)
        info = BsdInfo()
        size = ctypes.sizeof(info)
        rows = {}
        seen = {leader}
        pending = [leader]
        while pending:
            pid = pending.pop()
            row = _darwin_row(lib, pid, info, size)
            if row is not None:
                rows[pid] = row
            written = lib.proc_listchildpids(pid, ctypes.byref(children), child_bytes)
            if written < 0:
                raise OSError(ctypes.get_errno(), "proc_listchildpids")
            if written >= PROC_CHILD_CAP:
                return _darwin_full_table(lib)
            for i in range(written):
                child = children[i]
                if child > 0 and child not in seen:
                    seen.add(child)
                    pending.append(child)
        return rows

    return table


def _linux_fields(entry):
    try:
        stat_line = (entry / "stat").read_text()
    except OSError:
        return None
    fields = stat_line[stat_line.rfind(")") + 2 :].split()
    return fields if len(fields) > 19 else None


def _linux_lister():
    def lister(pgid):
        found = set()
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit():
                continue
            fields = _linux_fields(entry)
            if fields is not None and fields[2] == str(pgid):
                found.add(int(entry.name))
        return frozenset(found)

    return lister


def _linux_table(_leader):
    rows = {}
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit():
            continue
        fields = _linux_fields(entry)
        if fields is not None:
            rows[int(entry.name)] = (int(fields[1]), int(fields[2]), fields[19])
    return rows


def load_probes(cap):
    if sys.platform == "darwin":
        lib = _load_libproc()
        if lib is None:
            return None, None
        return _darwin_lister(lib, cap), _darwin_table(lib)
    if sys.platform.startswith("linux"):
        return _linux_lister(), _linux_table
    return None, None


class EscapeWatch:
    def __init__(self, leader, pgid, table):
        self.leader = leader
        self.pgid = pgid
        self.table = table
        self.escaped = set()

    def tick(self):
        if self.table is None or self.escaped:
            return bool(self.escaped)
        rows = self.table(self.leader)
        children = {}
        for pid, (ppid, _, _) in rows.items():
            children.setdefault(ppid, []).append(pid)
        seen = {self.leader}
        pending = [self.leader]
        while pending:
            for child in children.get(pending.pop(), ()):
                if child in seen:
                    continue
                seen.add(child)
                pending.append(child)
                if rows[child][1] != self.pgid:
                    self.escaped.add((child, rows[child][2]))
        return bool(self.escaped)
