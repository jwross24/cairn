from plants import *
ms,kids=recorded()
print(len(ms),len(kids))
z=zf_units()
print(len(z))
ks=Counter()
for a,b,c in z:
    y=mpz(2)**a*mpz(3)**b*mpz(7)**c
    M,zero=digits_of(y); assert not zero
    ks[len(M)//10*10]+=1
print(sorted(ks.items()))
print(Counter(len(m) for m in ms).most_common(60))
