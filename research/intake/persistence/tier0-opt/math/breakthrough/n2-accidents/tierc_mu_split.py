import math
from tierc_budget import VERT, multisets, npat, rho96
print("vertex  #eq  #eq(mu<0.01)  #eq(mu<1)  share_of_sum_mu_from_mu>=1  sum_mu(per a)")
for s, e in VERT.items():
    Ms = multisets(e)
    mus = [npat(M, 96) * rho96 for M in Ms]
    tot = sum(mus)
    print(s, len(Ms), sum(m < 0.01 for m in mus), sum(m < 1 for m in mus), f"{sum(m for m in mus if m >= 1)/tot:.6f}", f"{tot:.3e}")
