import sys; sys.dont_write_bytecode=True
from joint import *
a,b,c,K=1,5,7,5
y=2**a*3**b*7**c; Bt=y%10**K
m=K-a; m5=5**K
t5=Bt%m5*pow(2,-a,m5)%m5
x3,mod5=dlog5(3,K); x7,_=dlog5(7,K); xt,_=dlog5(t5,K)
print((b*x3+c*x7-(xt-a))%mod5, "mod5 cong residual")
print(pow(2,x3,m5)==3, pow(2,xt,m5)==t5)
t_odd=Bt>>a
e3,y3=dlog2adic(3,m); e7,y7=dlog2adic(7,m); et,yt=dlog2adic(t_odd%(1<<m),m)
print(m,(b*e3+c*e7-et)%2,(b*y3+c*y7-yt)%(1<<(m-2)))
