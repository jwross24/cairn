import sys
sys.dont_write_bytecode = True
import joint
from proto import *
orig = joint.lll_rows
def wrapped(rows):
    try:
        return orig(rows)
    except ZeroDivisionError:
        print("ROWS", [[str(x) for x in r] for r in rows], flush=True)
        raise
joint.lll_rows = wrapped
for Mi in multisets(exps(216))[2:]:
    try:
        run_equation(Mi, 4, 4, 40, {"pairs":0,"a_free_pairs":0,"queries":0})
        print("ok", Mi, flush=True)
    except Exception as e:
        print("FAIL M=", Mi, repr(e), flush=True); break
