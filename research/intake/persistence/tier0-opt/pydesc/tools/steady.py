import sys, os, time
src, s = sys.argv[1], int(sys.argv[2]); reps = int(sys.argv[3]) if len(sys.argv) > 3 else 3
os.chdir(src); sys.path.insert(0, src)
import run_c, tier0v2
eqs = [tuple(sorted(M)) for M in tier0v2.multisets(s)]
for r in range(reps):
    t = time.perf_counter(); c0 = time.process_time()
    for M in eqs: run_c.run(s, M, [], ncores=1)
    print(f'pass {r}: {len(eqs)} equations, wall {time.perf_counter()-t:.3f}s ({(time.perf_counter()-t)/len(eqs)*1e3:.1f} ms/eq), parent cpu {time.process_time()-c0:.3f}s')
