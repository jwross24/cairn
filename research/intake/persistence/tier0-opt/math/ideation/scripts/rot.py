import math
from idx import order_of_S
for L in (12,24,48,96):
    G,H,ind,r=order_of_S(L,(2,3,7))
    G5,H5,ind5,_=order_of_S(L,(2,3,5,7))
    G10,H10,ind10,_=order_of_S(L,(2,3,7,10))
    print(f"L={L} idx<2,3,7>={G//H}  idx<2,3,5,7>={G//H5}  idx<2,3,7,10>={G//H10}  |H|={math.log10(H):.2f} |H5|={math.log10(H5):.2f}")
