import time
from fonga_v2 import exact_max_v2
for M in [(2,)*14+(3,)*3+(7,),(2,)*18+(3,)*3+(7,),(4,4,7),(2,7,8)]:
    st={}
    t=time.time()
    r=exact_max_v2(M,stats=st)
    print(len(M),r,st,round(time.time()-t,2),flush=True)
