import sys, random, time, faulthandler
faulthandler.dump_traceback_later(20, exit=True)
sys.dont_write_bytecode = True
from joint import *
E=int(sys.argv[1]); a=int(sys.argv[2]); P=E+6; K=E+6+a//2+1
random.seed(7)
b=random.randrange(10**E//3,10**E); c=random.randrange(10**E//3,10**E)
n,D,fr=leading_digits(a,b,c,P)
Bt=pow(2,a,10**K)*pow(3,b,10**K)*pow(7,c,10**K)%10**K
st={}
t0=time.perf_counter()
r=query(D,P,Bt,K,P+K,2*n,st)
print(E,a,K,(time.perf_counter()-t0)*1000,"ms",r==[(a,b,c,n)],st,flush=True)
