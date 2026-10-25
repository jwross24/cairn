import sys, random
sys.dont_write_bytecode = True
from joint import *
E=int(sys.argv[1]);P=K=E+6
random.seed(5)
a=random.randrange(1,min(100,K-5)); b=random.randrange(10**E//3,10**E); c=random.randrange(10**E//3,10**E)
n,D,fr=leading_digits(a,b,c,P)
Bt=pow(2,a,10**K)*pow(3,b,10**K)*pow(7,c,10**K)%10**K
a2=(Bt&-Bt).bit_length()-1
print(a,a2)
raw=query_fixed_a(D,P,Bt,K,a,P+K,2*n)
print(len(raw), (a,b,c,n) in raw)
print([ (r[0]==a, verify_candidate(*r,D,P,Bt,K)) for r in raw][:10])
print(fr)
