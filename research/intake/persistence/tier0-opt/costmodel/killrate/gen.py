import sys; sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
from export_cfg import export
for M in sys.argv[1:]:
    t=tuple(int(x) for x in M.split(','))
    export(t,"cfg_"+''.join(map(str,t))+".txt")
