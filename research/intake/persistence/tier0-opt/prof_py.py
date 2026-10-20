import cProfile, pstats, sys, time
from eq_golden import kids
from run_c import run
s=int(sys.argv[1]); M=tuple(int(x) for x in sys.argv[2].split(','))
K=kids()
t0=time.time()
pr=cProfile.Profile(); pr.enable(); r=run(s,M,K[s],ncores=1); pr.disable()
print('total',round(time.time()-t0,2))
pstats.Stats(pr).sort_stats('cumulative').print_stats(18)
