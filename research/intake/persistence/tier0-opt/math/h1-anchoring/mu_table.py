from math import comb
rho96 = 280999509749509611991995562563818636457519792000000000000 / 3871883799019448631695955148383646690801203347343308190525887136228937039872000000000000000000
def npat(counts, L=96):
    n = L
    for m in counts:
        n *= comb(L + m - 1, m)
    return n
print("rho96", f"{rho96:.4e}")
for q in range(14, 47, 2):
    shapes = {"2^{2q/3}3^{q/3}": (2 * q // 3, q - 2 * q // 3), "all 2": (q,), "2^{q/2}3^{q/4}4^{q/4}": (q // 2, q // 4, q - q // 2 - q // 4)}
    print(q, "  ".join(f"{k}: {npat(v) * rho96:.2e}" for k, v in shapes.items()))
