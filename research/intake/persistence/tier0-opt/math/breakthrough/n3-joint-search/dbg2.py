import sys, random
sys.dont_write_bytecode = True
from joint import *
E=6;P=K=E+6
random.seed(5)
a=random.randrange(1,100); b=random.randrange(10**E//3,10**E); c=random.randrange(10**E//3,10**E)
n,D,fr=leading_digits(a,b,c,P)
Bt=pow(2,a,10**K)*pow(3,b,10**K)*pow(7,c,10**K)%10**K
print(a,K,n,Bt, (Bt&-Bt).bit_length()-1, Bt%(1<<K))
