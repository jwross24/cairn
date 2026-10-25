import ast
import functools
from collections import Counter

TIER0V2 = "/Users/jwross/Documents/cairn/research/intake/persistence/tier0/tier0v2.py"


def original():
    src = open(TIER0V2).read()
    tree = ast.parse(src)
    keep = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ("two_adic_bound", "_two_adic_bound")]
    mod = ast.Module(body=keep, type_ignores=[])
    ns = {"functools": functools, "Counter": Counter}
    exec(compile(ast.fix_missing_locations(mod), TIER0V2, "exec"), ns)
    return ns["two_adic_bound"]


class StateCap(Exception):
    pass


def old_capped(M, state_cap=300000, kcap=200):
    M = Counter(M)
    states = {(0, tuple(sorted(M.elements())), False)}
    for k in range(1, kcap):
        new = set()
        for tail, rem, ended in states:
            choices = {0} if ended else ({0, 1} | set(rem))
            for d in choices:
                t = d * 10 ** (k - 1) + tail
                if t % (2 ** k) == 0:
                    if d == 0:
                        if tail:
                            new.add((t, rem, True))
                    elif d == 1:
                        new.add((t, rem, False))
                    else:
                        r = list(rem)
                        r.remove(d)
                        new.add((t, tuple(r), False))
            if len(new) > state_cap:
                raise StateCap(k)
        if not new:
            return k - 1
        states = new
    raise StateCap(kcap)
