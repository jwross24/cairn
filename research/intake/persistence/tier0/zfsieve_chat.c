// zfsieve.c — zero-free {2,3,7}-units with 10^L0 <= y < 10^L1, by a 10-adic sieve.
// Enumerates every (a,b,c) with a log2 + b log3 + c log7 in [(L0-1) log10, (L1+1) log10] (generous bounds; the exact
// digit count is checked later in Python), keeps the running value modulo 10^M1 and 10^M2 in base-10^6 limbs, and
// rejects as soon as a genuine digit 0 appears among the lowest min(M, n-2) digits (n = digit count from logs; the -2
// guards the float boundary — a limb above the number's top would show spurious leading zeros).  Survivors of both
// stages are printed as "a b c" for the exact check.  Zero-free: no digit 0 anywhere.
// Usage: zfsieve L0 L1 cmod cres [cstart]   (processes c ≡ cres mod cmod, c >= cstart; prints "DONE c count" per c)
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <math.h>
#include <string.h>
#define M1 36
#define M2 108
#define L1N (M1/6)
#define L2N (M2/6)
#define BASE 1000000u
static uint8_t *zt;   // zt[v] = 1 iff the 6-digit block v (with leading zeros) contains a digit 0

static inline void mul_small(uint32_t *x, int n, uint32_t m) {
    uint64_t carry = 0;
    for (int i = 0; i < n; i++) { uint64_t t = (uint64_t)x[i] * m + carry; x[i] = (uint32_t)(t % BASE); carry = t / BASE; }
}
static inline void dbl(uint32_t *x, int n) {
    uint32_t carry = 0;
    for (int i = 0; i < n; i++) { uint32_t t = x[i] * 2 + carry; carry = t >= BASE; x[i] = t - (carry ? BASE : 0); }
}
// check the lowest `digits` digits of x (n limbs) for a zero; returns 1 if a zero digit is present
static inline int has_zero(const uint32_t *x, int nlimbs, int digits) {
    int full = digits / 6, rest = digits % 6;
    for (int i = 0; i < full && i < nlimbs; i++) if (zt[x[i]]) return 1;
    if (rest && full < nlimbs) { uint32_t v = x[full]; for (int j = 0; j < rest; j++) { if (v % 10 == 0) return 1; v /= 10; } }
    return 0;
}
int main(int argc, char **argv) {
    if (argc < 5) { fprintf(stderr, "usage: zfsieve L0 L1 cmod cres [cstart]\n"); return 1; }
    int L0 = atoi(argv[1]), L1 = atoi(argv[2]), cmod = atoi(argv[3]), cres = atoi(argv[4]), cstart = argc > 5 ? atoi(argv[5]) : 0;
    zt = malloc(BASE);
    for (uint32_t v = 0; v < BASE; v++) { uint32_t w = v; int z = 0; for (int j = 0; j < 6; j++) { if (w % 10 == 0) z = 1; w /= 10; } zt[v] = z; }
    const double l2 = log(2.0), l3 = log(3.0), l7 = log(7.0), l10 = log(10.0);
    double lo = (L0 - 1) * l10, hi = (L1 + 1) * l10;
    int cmax = (int)(hi / l7);
    uint32_t X1[L1N], X2[L2N], Y1[L1N], Y2[L2N], Z1[L1N], Z2[L2N];
    unsigned long long tot = 0, surv = 0;
    for (int c = cstart; c <= cmax; c++) {
        if (c % cmod != cres) continue;
        // X = 7^c mod 10^M (computed from scratch per c for resumability: c multiplications)
        memset(X1, 0, sizeof X1); memset(X2, 0, sizeof X2); X1[0] = 1; X2[0] = 1;
        for (int i = 0; i < c; i++) { mul_small(X1, L1N, 7); mul_small(X2, L2N, 7); }
        int bmax = (int)((hi - c * l7) / l3);
        memcpy(Y1, X1, sizeof Y1); memcpy(Y2, X2, sizeof Y2);
        unsigned long long cnt = 0;
        for (int b = 0; b <= bmax; b++) {
            if (b) { mul_small(Y1, L1N, 3); mul_small(Y2, L2N, 3); }
            double base = c * l7 + b * l3;
            int amax = (int)((hi - base) / l2);
            int amin = (lo - base) > 0 ? (int)ceil((lo - base) / l2) : 0;
            if (amax < amin) continue;
            memcpy(Z1, Y1, sizeof Z1); memcpy(Z2, Y2, sizeof Z2);
            for (int i = 0; i < amin; i++) { dbl(Z1, L1N); dbl(Z2, L2N); }
            for (int a = amin; a <= amax; a++) {
                if (a > amin) { dbl(Z1, L1N); dbl(Z2, L2N); }
                cnt++;
                int n = (int)floor((base + a * l2) / l10) + 1;        // digit count (float; -2 margin below)
                int d1 = n - 2 < M1 ? n - 2 : M1;
                if (d1 > 0 && has_zero(Z1, L1N, d1)) continue;
                int d2 = n - 2 < M2 ? n - 2 : M2;
                if (d2 > 0 && has_zero(Z2, L2N, d2)) continue;
                surv++;
                printf("%d %d %d\n", a, b, c);
            }
        }
        tot += cnt;
        printf("DONE %d %llu %llu\n", c, cnt, surv); fflush(stdout);
    }
    fprintf(stderr, "total %llu survivors %llu\n", tot, surv);
    return 0;
}
