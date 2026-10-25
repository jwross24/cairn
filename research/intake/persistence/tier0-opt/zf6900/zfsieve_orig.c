#define _GNU_SOURCE
// zfsieve: enumerate (a,b,c) with 2^a 3^b 7^c < 10^dmax and emit candidates that survive
// two exact (no-false-negative) zero-digit filters:
//   * low window : x mod 10^72, kept as 12 limbs of 10^6, updated by small multiplications
//   * high window: 11 leading digits, from long-double log10 arithmetic (>= 15 correct digits)
// Survivors ("a b c" lines on stdout) must be fully verified afterwards (zfcheck.py).
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NL   24
#define LIMB 1000000u

static uint8_t *hz;   // hz[v] = 1 if the 6-digit zero-padded decimal of v contains a 0

static inline void mulsmall(uint32_t *l, uint32_t m) {
    uint64_t carry = 0;
    for (int i = 0; i < NL; i++) {
        uint64_t t = (uint64_t)l[i] * m + carry;
        l[i] = (uint32_t)(t % LIMB);
        carry = t / LIMB;
    }
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: zfsieve dmax a_lo a_hi\n"); return 1; }
    int dmax = atoi(argv[1]), a_lo = atoi(argv[2]), a_hi = atoi(argv[3]);
    hz = malloc(LIMB);
    for (uint32_t v = 0; v < LIMB; v++) {
        uint32_t t = v; int z = 0;
        for (int i = 0; i < 6; i++) { if (t % 10 == 0) z = 1; t /= 10; }
        hz[v] = (uint8_t)z;
    }
    const long double L2 = log10l(2.0L), L3 = log10l(3.0L), L7 = log10l(7.0L);
    int amax = (int)(dmax / L2) + 1;
    if (a_hi > amax) a_hi = amax;

    unsigned long long tested = 0, surv = 0;
    uint32_t pa[NL], pab[NL], r[NL];

    for (int a = a_lo; a < a_hi; a++) {
        long double la = a * L2;
        if (la >= dmax) break;
        memset(pa, 0, sizeof pa); pa[0] = 1;
        for (int i = 0; i < a; i++) mulsmall(pa, 2);
        memcpy(pab, pa, sizeof pa);
        for (int b = 0; ; b++) {
            long double lab = la + b * L3;
            if (lab >= dmax) break;
            if (b) mulsmall(pab, 3);
            memcpy(r, pab, sizeof pab);
            long double lg = lab;
            long double lead = exp10l(lab - floorl(lab));   // in [1,10)
            for (int c = 0; ; c++) {
                if (c) {
                    lg += L7;
                    lead *= 7.0L;
                    while (lead >= 10.0L) lead *= 0.1L;
                    mulsmall(r, 7);
                }
                if (lg >= dmax) break;
                tested++;
                int ndigits = (int)floorl(lg) + 1;
                if (ndigits >= 13) {
                    uint64_t v = (uint64_t)(lead * 1e11L);        // 12 leading digits, trust 11
                    uint32_t hi = (uint32_t)(v / LIMB);
                    uint32_t lo5 = (uint32_t)((v % LIMB) / 10) + 100000u; // 5 digits, forced lead 1
                    if (hz[hi] || hz[lo5]) continue;
                }
                {   // low window: limbs that lie strictly below the top digit are exact digits of x
                    int usable = (ndigits - 2) / 6; if (usable > NL) usable = NL;
                    int bad = 0;
                    for (int i = 0; i < usable; i++) if (hz[r[i]]) { bad = 1; break; }
                    if (bad) continue;
                }
                surv++;
                printf("%d %d %d\n", a, b, c);
            }
        }
    }
    fprintf(stderr, "a in [%d,%d) dmax=%d: tested %llu, survivors %llu\n", a_lo, a_hi, dmax, tested, surv);
    return 0;
}
