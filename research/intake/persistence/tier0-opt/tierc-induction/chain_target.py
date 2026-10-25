from math import log10
import importlib.util, sys
src = open("chain_calc.py").read().split("L.append(\"T6 reproduction")[0]
ns = {}
exec(src.replace("OUT = sys.argv[1] if len(sys.argv) > 1 else \"chain_out.txt\"", "OUT='x'"), ns)
F = ns["F_two_ended"]
out = []
for k, logU in ((31, 281.5), (44, 402.1)):
    Gne = 4 * logU
    for tgt in (72.0, 14.8):
        found = None
        for j0 in range(1, k + 1):
            v = F(k, 16.7, 18.2, 14.7, 14.7, top_levels=j0, top_step=Gne)
            if v[0] <= tgt:
                found = (j0, v[0], j0 * log10(8 * Gne))
                break
        out.append("k=%d target log10 U<=%.1f: %s" % (k, tgt, found))
open("chain_target_out.txt", "w").write("\n".join(out) + "\n")
