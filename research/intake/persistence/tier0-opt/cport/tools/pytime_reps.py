import os, sys, time
py = '/private/tmp/persist-cport/py'
os.chdir(py); sys.path.insert(0, py)
import deepcut as DC
t = time.process_time(); n = 0; nr = 0
for l in open('/private/tmp/persist-cport/cases_0545.txt'):
    s, M, a, y, nu, eps = l.split()
    reps = DC.all_representations(tuple(int(c) for c in M), int(y)); n += 1; nr += len(reps)
print(f"python all_representations: {n} patterns, {nr} unfiltered reps, {time.process_time() - t:.1f}s CPU")
