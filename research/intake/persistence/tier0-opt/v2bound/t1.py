import time
from fonga_v2 import exact_max_v2
for M,exp in [((4,4,7),7),((2,2,2,2,7),13),((2,2,4,7),15),((2,7,8),9)]:
    print(M,exact_max_v2(M),exp)
