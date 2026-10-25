import sys, cProfile, pstats
sys.path.insert(0, "/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierb-anchored")
import ref_check as RC
rows = [l.split() for l in open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/tierb-anchored/work/xc100.out")][:5]
def go():
    for t in rows:
        y = int(t[1]); n = int(t[6]); De = [tuple(map(int, x.split(":"))) for x in t[7:7+n]]
        RC.exact_verdict(y, De)
pr = cProfile.Profile(); pr.runcall(go)
pstats.Stats(pr).sort_stats("cumtime").print_stats(8)
