import sys
sys.path.insert(0, '/private/tmp/persist-branchsplit/cand')
from export_cfg import export
for M in ((2, 7), (2, 2, 3, 4, 7), (8, 8, 8, 8, 9, 9, 9)):
    c = export(M, '/private/tmp/persist-branchsplit/tmpcfg.txt')
    u = c['U2']
    print(M, u, u[0][0] * u[1][1] - u[0][1] * u[1][0])
