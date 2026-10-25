from math import log, log10
from lat import lll, det2, norm_inf, v_p, intersect_2d

u = (-5834300434592217394015440000, -5252227908597256497593760000)
v = (24550795595028192589139040000, -26061931100684490688131840000)
R96 = (10 ** 96 - 1) // 9
while R96 % 3 == 0:
    R96 //= 3
while R96 % 7 == 0:
    R96 //= 7


def g_mod(vec, mod):
    return pow(3, vec[0], mod) * pow(7, vec[1], mod) % mod


def height_g(vec):
    pos = max(vec[0], 0) * log(3) + max(vec[1], 0) * log(7)
    neg = max(-vec[0], 0) * log(3) + max(-vec[1], 0) * log(7)
    return max(pos, neg)


def main():
    red = lll([u, v])
    print('Gauss/LLL-reduced recorded basis, sup norms: %.4e %.4e   |det| = %.4e' % (norm_inf(red[0]), norm_inf(red[1]), det2(red)))
    for name, vec in (('u', u), ('v', v)):
        print('g_%s == 1 mod R_96 with the factors 3 and 7 removed : %s' % (name, g_mod(vec, R96) == 1))
    planted = (u[0] + 1, u[1])
    print('planted negative, (u1+1, u2) == 1 mod the same modulus : %s' % (g_mod(planted, R96) == 1))
    for name, vec in (('u', u), ('v', v)):
        g5 = pow(3, vec[0], 5 ** 30) * pow(7, vec[1], 5 ** 30) % 5 ** 30
        g2 = pow(3, vec[0], 2 ** 60) * pow(7, vec[1], 2 ** 60) % 2 ** 60
        print('g_%s: v5(g-1)=%d  v2(g-1)=%d' % (name, v_p((g5 - 1) % 5 ** 30, 5), v_p((g2 - 1) % 2 ** 60, 2)))

    hu, hv = height_g(red[0]), height_g(red[1])
    print('absolute log heights of the lattice generators: h(g_1)=10^%.2f  h(g_2)=10^%.2f  (h(3)=%.3f, h(7)=%.3f)' % (log10(hu), log10(hv), log(3), log(7)))
    print()
    print('Matveev product of heights: standard form uses A(3)A(7) = %.3f ; lattice-coordinate form uses A(g_1)A(g_2)' % (log(3) * log(7)))
    ratio_A = (hu * hv) / (log(3) * log(7))
    print('  height-product inflation factor: 10^%.2f' % log10(ratio_A))
    for n_exp in (30, 300, 850):
        logB_std = log(2.1) + n_exp * log(10)
        zbits = max(n_exp - 27.9, 1.0)
        logB_lat = log(2.1) + zbits * log(10)
        print('  n ~ 10^%d: log B standard = %.1f, lattice coordinates z ~ n/10^28 gives log B = %.1f; net change in the Matveev exponent: x10^%.2f (loss)' % (
            n_exp, logB_std, logB_lat, log10(ratio_A) + log10((1 + logB_lat) / (1 + logB_std))))
    print()
    return det2(red)


if __name__ == '__main__':
    main()
