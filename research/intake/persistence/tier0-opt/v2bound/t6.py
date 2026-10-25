import itertools, random
from fonga_v2 import exact_max_v2
def brute(M,maxlen):
    best=0;k=len(M)
    perms=set(itertools.permutations(M))
    for L in range(k,maxlen+1):
        for pos in itertools.combinations(range(L),k):
            for p in perms:
                x=[1]*L
                for i,d in zip(pos,p): x[i]=d
                n=int(''.join(map(str,x)))
                v=(n&-n).bit_length()-1
                if v>best:best=v
    return best
random.seed(3)
res=[]
for M in [(4,4,7),(2,7,8),(2,2,4),(2,3,6),(4,8,3),(2,2,2,3),(6,6,7),(8,8,9),(2,4,8),(4,6,9),(2,2,7)]:
    b=brute(M,12);n=exact_max_v2(M)
    print(M,b,n,"ok" if b<=n else "VIOLATION")
