import fonga_v2
from fonga_v2 import *
hits=[0]
orig=Search.value
class S2(Search):
    def value(self,digits,a,T):
        if (digits,a,T) in self.memo: hits[0]+=1
        return orig(self,digits,a,T)
import time
s=S2()
M=(2,)*14+(3,)*3+(7,)
digits=tuple(sorted(M))
for i,d in enumerate(digits):
    if d%2 or (i and digits[i-1]==d): continue
    s.value(digits[:i]+digits[i+1:],0,9*(d-1)-1)
print(s.nodes,hits)
