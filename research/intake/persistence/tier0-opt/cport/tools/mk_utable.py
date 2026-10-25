import os, sys
py='/private/tmp/persist-cport/py'
os.chdir(py); sys.path.insert(0,py)
from baker_chain import baker_upper_bound
W='/private/tmp/persist-cport/'
with open(W+'utable.txt','w') as f:
    for k in range(1,17):
        for a in range(0,13):
            f.write(f"{k} {a} {baker_upper_bound(k,a)}\n")
