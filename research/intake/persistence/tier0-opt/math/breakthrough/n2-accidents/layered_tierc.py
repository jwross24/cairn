import json
D = json.load(open("/Users/jwross/Documents/cairn/research/intake/persistence/tier0-opt/math/h1-anchoring/density.json"))
rho = {int(L): int(v["index"]) / int(v["phi"]) for L, v in D.items()}
V = [
 ("3416267673274176", 1.724e19, 3.485e17, 2.333e24, 6.694e6, 1.9e11),
 ("128421199872",     2.566e19, 5.185e17, 1.009e24, 1.947e6, 5.1e11),
 ("913217421312",     8.595e19, 1.735e18, 8.482e24, 4.888e6, 1.5e12),
 ("727326941773824",  5.531e21, 1.119e20, 6.623e27, 5.916e7, 8.9e13),
 ("112717121716224",  9.864e21, 1.992e20, 8.375e27, 4.204e7, 1.5e14),
 ("1438916737499136", 1.380e22, 2.786e20, 9.045e27, 3.246e7, 1.4e14),
]
print("rho", {L: f"{r:.3e}" for L, r in rho.items()})
print("vertex  S12  C24  S24  C48  S48  C96  S96_uniform  anchored_pred  ratio")
for s, n12, s12, c24, lam, anch in V:
    S24 = c24 * rho[24] / rho[12]
    C48 = S24 * lam
    S48 = C48 * rho[48] / rho[24]
    C96 = S48 * lam
    S96 = C96 * rho[96] / rho[48]
    print(f"{s:>17} {s12:.2e} {c24:.2e} {S24:.2e} {C48:.2e} {S48:.2e} {C96:.2e} {S96:.2e} {anch:.1e} {S96/anch:.2e}")
