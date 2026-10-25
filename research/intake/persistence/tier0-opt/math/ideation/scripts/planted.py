import numpy as np
from branchtest import *
cnt=0; passn=0; pass_now=0; byclass={}
for a in range(0,140):
    for b in range(0,90):
        base=(2**a)*(3**b)
        for c in range(0,50):
            y=base*7**c
            if y<10**6: continue
            s=str(y)
            if '0' in s: continue
            n=len(s); nu=n%12
            digs=s[::-1]
            pos=[(i,int(ch)) for i,ch in enumerate(digs) if ch!='1']
            res={}
            for p in P+[3,7]:
                if p==3: u=(nu+sum(d-1 for i,d in pos))%3
                else:
                    Rt=((pow(10,nu,9*p)-1)//9)%p
                    u=(Rt+sum((d-1)*pow(10,i%12,p) for i,d in pos))%p
                res[p]=u
            assert res[3]==y%3 and res[7]==y%7 and all(res[p]==y%p for p in P)
            ok=all(res[p]!=0 for p in P)
            L=np.array([[int(LOG[p][res[p]]) if res[p]!=0 else 0 for p in P]],dtype=np.int64)
            b3=res[3]==0; b7=res[7]==0
            if b3 and b7: m=member(B237,L)[0]
            elif b3: m=member(B23,L)[0]
            elif b7: m=member(B27,L)[0]
            else: m=member(B2,L)[0]
            m0=member(B237,L)[0]
            cnt+=1; passn+=bool(m and ok); pass_now+=bool(m0 and ok)
            k=(int(b3),int(b7)); byclass[k]=byclass.get(k,0)+1
print("planted zero-free S-units (>=7 digits):",cnt,"pass branch-split:",passn,"pass current rank-3 test:",pass_now,"classes",byclass)
