"""Batched classify + 10-adic descent through libpydesc (GMP); survivors the library declines are redone by the caller in Python."""
import ctypes, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
_lib = None
ABI = 2
ENABLED = os.environ.get('PYDESC') != '0'
CODE_DEAD, CODE_SOLUTION, CODE_OPEN, CODE_RESOLVED, CODE_FALLBACK = 0, 1, 2, 3, 9
KIND = {CODE_DEAD: 'DEAD', CODE_SOLUTION: 'SOLUTION', CODE_OPEN: 'OPEN', CODE_RESOLVED: 'RESOLVED(descent)'}


def _load():
    global _lib
    if _lib is None:
        path = os.environ.get('PYDESC_LIB') or os.path.join(HERE, 'libpydesc.dylib' if sys.platform == 'darwin' else 'libpydesc.so')
        try:
            lib = ctypes.CDLL(path)
        except OSError as e:
            raise RuntimeError(f"cannot load {path} ({e}); build it with build.sh or set PYDESC=0 to use the pure Python path") from e
        sig = [ctypes.c_char_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(ctypes.c_size_t)]
        for name in ('pydesc_batch', 'pydesc_scan12', 'pydesc_batch12'):
            getattr(lib, name).argtypes = sig
            getattr(lib, name).restype = ctypes.c_int
        lib.pydesc_free.argtypes = [ctypes.c_void_p]
        lib.pydesc_free.restype = None
        lib.pydesc_abi.restype = ctypes.c_int
        if lib.pydesc_abi() != ABI:
            raise RuntimeError(f"{path}: library ABI {lib.pydesc_abi()}, expected {ABI}")
        _lib = lib
    return _lib


def classify_batch(surv, D, L, kcap, do_descent):
    """-> list of (code, [solutions]) aligned with surv, or None when the parameters are outside the library's range; D is the sorted digit multiset."""
    lib = _load()
    q = len(D)
    parts = [f"{L} {kcap} {q} {1 if do_descent else 0} {len(surv)}\n", ' '.join(map(str, D)), '\n']
    for (a, nu, eps, co) in surv:
        v0, u1, u2 = co.v0, co.u1, co.u2
        parts.append(f"{a} {nu} {' '.join(map(str, eps))} {v0[0]} {v0[1]} {u1[0]} {u1[1]} {u2[0]} {u2[1]}\n")
    data = ''.join(parts).encode()
    outp = ctypes.c_void_p()
    outn = ctypes.c_size_t()
    rc = lib.pydesc_batch(data, len(data), ctypes.byref(outp), ctypes.byref(outn))
    if rc == 3:
        return None
    if rc:
        raise RuntimeError(f"libpydesc rejected the batch (rc {rc})")
    try:
        text = ctypes.string_at(outp.value, outn.value).decode()
    finally:
        lib.pydesc_free(outp)
    res = []
    for line in text.splitlines():
        f = line.split()
        res.append((int(f[0]), [int(x) for x in f[2:2 + int(f[1])]]))
    if len(res) != len(surv):
        raise RuntimeError("libpydesc returned a short batch")
    return res


def _call(fn_name, text):
    lib = _load()
    fn = getattr(lib, fn_name)
    data = text.encode()
    outp = ctypes.c_void_p()
    outn = ctypes.c_size_t()
    rc = fn(data, len(data), ctypes.byref(outp), ctypes.byref(outn))
    if rc in (3, 4, 5):
        return None
    if rc:
        raise RuntimeError(f"libpydesc.{fn_name} rejected its input (rc {rc})")
    try:
        return ctypes.string_at(outp.value, outn.value).decode()
    finally:
        lib.pydesc_free(outp)


def scan12(paths, q):
    """-> (number of OPEN lines, [EXACT lines]) or None when some line is not one the Python parser accepts."""
    text = _call('pydesc_scan12', f"{q} {len(paths)}\n" + '\n'.join(paths) + '\n')
    if text is None:
        return None
    head, _, rest = text.partition('\n')
    n_open, n_exact = map(int, head.split())
    exact = rest.splitlines()
    if len(exact) != n_exact:
        raise RuntimeError("libpydesc scan12 returned a short EXACT list")
    return n_open, exact


class RawSurv:
    """Level-12 survivors held as the kernel's output files; Python tuples are built only on demand."""

    def __init__(self, paths, M, U2, n):
        self.paths, self.M, self.U2, self.n = list(paths), tuple(M), U2, n
        self._list = None

    def __len__(self):
        return self.n

    def _items(self):
        if self._list is None:
            from tier0v2 import canon
            from lattice import Coset
            M, U2, q = self.M, self.U2, len(self.M)
            out = []
            for outp in self.paths:
                for line in open(outp):
                    f = line.split()
                    if f[0] == 'OPEN':
                        a, nu = int(f[1]), int(f[2]); eps = tuple(int(x) for x in f[3:3 + q]); b, c = int(f[3 + q]), int(f[4 + q])
                        nu2, eps2 = canon(M, nu, eps)
                        out.append((a, nu2, eps2, Coset((b, c), tuple(U2[0]), tuple(U2[1]))))
            self._list = out
        return self._list

    def __iter__(self):
        return iter(self._items())

    def __getitem__(self, i):
        return self._items()[i]

    def classify(self, D, L, kcap, do_descent):
        """-> (kinds in first-seen order as (kind, count), solutions, open survivors) or None when any survivor needs the Python path."""
        if tuple(D) != self.M or list(D) != sorted(D):
            return None
        from lattice import Coset
        u = self.U2
        text = (f"{L} {kcap} {len(D)} {1 if do_descent else 0} {len(self.paths)}\n" + ' '.join(map(str, D)) + '\n'
                + f"{u[0][0]} {u[0][1]} {u[1][0]} {u[1][1]}\n" + '\n'.join(self.paths) + '\n')
        res = _call('pydesc_batch12', text)
        if res is None:
            return None
        lines = res.split('\n')
        nsurv, c0, c1, c2, c3, c9 = map(int, lines[0].split())
        if nsurv != self.n:
            raise RuntimeError("libpydesc batch12 disagrees with scan12 on the survivor count")
        if c9:
            return None
        counts = {0: c0, 1: c1, 2: c2, 3: c3}
        kinds = [(KIND[int(c)], counts[int(c)]) for c in lines[1].split()]
        sf = lines[2].split()
        sols = [int(x) for x in sf[1:1 + int(sf[0])]]
        u1, u2 = tuple(u[0]), tuple(u[1])
        opn = []
        q = len(D)
        for ln in lines[3:]:
            if not ln:
                continue
            f = ln.split()
            opn.append((int(f[2]), int(f[3]), tuple(int(x) for x in f[4:4 + q]), Coset((int(f[4 + q]), int(f[5 + q])), u1, u2)))
        if len(opn) != c2:
            raise RuntimeError("libpydesc batch12 returned a short survivor list")
        return kinds, sols, opn
