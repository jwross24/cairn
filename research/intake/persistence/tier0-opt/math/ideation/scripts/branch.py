import math
from idx import order_of_S
res={}
for L in (12,24,48,96):
    G,H237,i237,r=order_of_S(L,(2,3,7))
    _,H23,_,_=order_of_S(L,(2,3)); _,H27,_,_=order_of_S(L,(2,7)); _,H2,_,_=order_of_S(L,(2,))
    I237=G//H237; I23=G//H23; I27=G//H27; I2=G//H2
    cur=1/I237
    new=(1/21)/I237+(2/7)/I23+(2/21)/I27+(4/7)/I2
    print(f"L={L}: I(2,3,7)={I237:.4g} I(2,3)={I23:.4g} I(2,7)={I27:.4g} I(2)={I2:.4g}  survival now {cur:.3e}  branch-split {new:.3e}  gain x{cur/new:.2f}")
