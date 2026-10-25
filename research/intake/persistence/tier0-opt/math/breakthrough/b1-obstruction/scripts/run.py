import math, sys
from baker_chain import baker_upper_bound
rows=[("3416267673274176","2^6 3^27 7",34,17),("128421199872","2^23 3^7 7",31,13),("913217421312","2^29 3^5 7",35,14),("727326941773824","2^39 3^3 7^2",44,17),("112717121716224","2^34 3^8",42,16),("1438916737499136","2^24 3^6 7^6",36,17)]
for s,f,k,kmin in rows:
    for a in (1,):
        G=baker_upper_bound(k,a)
        lg=math.log10(G) if G<10**300 else len(str(G))-1+math.log10(int(str(G)[:15])/1e14)
        D=max(1,math.ceil((lg-72)/48)+1)
        cases=(D+1)**k
        print(s,f,"kmax",k,"log10G(a>=1)=%.1f"%lg,"D=",D,"(D+1)^k=10^%.1f"%(k*math.log10(D+1)),"2^k=10^%.1f"%(k*math.log10(2)))
