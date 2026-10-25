import os, sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stage_io import records

out = sys.argv[1]
n = 0
with open(out, 'w') as f:
    for _, k in records(sys.argv[2:]):
        f.write(k + '\n')
        n += 1
print(n, 'records ->', out)
