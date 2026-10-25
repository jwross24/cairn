import random
from oldbound import original, old_capped
from fonga_v2 import exact_max_v2
orig=original()
random.seed(1)
bad=0;eq=0;lt=0
for _ in range(300):
    k=random.randint(1,9)
    M=tuple(random.choice([2,3,4,6,7,8,9,2,2,3]) for _ in range(k))
    o=orig(M); c=old_capped(M); n=exact_max_v2(M)
    assert o==c,(M,o,c)
    if n>o: bad+=1; print("NEW>OLD",M,n,o)
    elif n==o: eq+=1
    else: lt+=1; print("lt",M,n,o)
print(bad,eq,lt)
