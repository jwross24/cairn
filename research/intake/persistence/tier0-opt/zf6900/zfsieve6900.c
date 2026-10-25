#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>

#define NL   24
#define LIMB 1000000u
#define LEADEPS 1e-24

typedef struct { double hi, lo; } dd;

static uint8_t *hz;

static inline void mulsmall(uint32_t *l, uint32_t m) {
    uint64_t carry = 0;
    for (int i = 0; i < NL; i++) {
        uint64_t t = (uint64_t)l[i] * m + carry;
        l[i] = (uint32_t)(t % LIMB);
        carry = t / LIMB;
    }
}

static inline dd dd_renorm(double h, double l) {
    double s = h + l;
    dd r = { s, l - (s - h) };
    return r;
}

static inline dd dd_mulint(dd x, double m) {
    double p = x.hi * m;
    double e = fma(x.hi, m, -p);
    return dd_renorm(p, e + x.lo * m);
}

static inline dd dd_div10(dd x) {
    double q = x.hi / 10.0;
    double r = fma(-q, 10.0, x.hi) + x.lo;
    return dd_renorm(q, r / 10.0);
}

// leading digit mantissa in [1,10) and decimal exponent e: value = lead * 10^e
static inline void lead_mul(dd *x, int *e, double m) {
    *x = dd_mulint(*x, m);
    while (x->hi >= 10.0) { *x = dd_div10(*x); (*e)++; }
}

static inline uint64_t floor12(double hi, double lo) {
    double p = hi * 1e11;
    double pe = fma(hi, 1e11, -p) + lo * 1e11;
    double fl = floor(p);
    double r = (p - fl) + pe;
    return (uint64_t)((int64_t)fl + (int64_t)floor(r));
}

static inline int hi_zero(uint64_t v) {
    return hz[(uint32_t)(v / LIMB)] || hz[(uint32_t)((v % LIMB) / 10) + 100000u];
}

int main(int argc, char **argv) {
    if (argc < 4) { fprintf(stderr, "usage: zfsieve6900 dmax a_lo a_hi\n"); return 1; }
    int dmax = atoi(argv[1]), a_lo = atoi(argv[2]), a_hi = atoi(argv[3]);
    hz = malloc(LIMB);
    for (uint32_t v = 0; v < LIMB; v++) {
        uint32_t t = v; int z = 0;
        for (int i = 0; i < 6; i++) { if (t % 10 == 0) z = 1; t /= 10; }
        hz[v] = (uint8_t)z;
    }
    int amax = (int)(dmax / 0.30102999566398120) + 1;
    if (a_hi > amax) a_hi = amax;

    unsigned long long tested = 0, surv = 0;
    uint32_t pa[NL], pab[NL], r[NL];

    dd la_lead = {1.0, 0.0}; int la_e = 0;
    for (int i = 0; i < a_lo; i++) lead_mul(&la_lead, &la_e, 2.0);

    for (int a = a_lo; a < a_hi; a++) {
        if (a > a_lo) lead_mul(&la_lead, &la_e, 2.0);
        if (la_e >= dmax) break;
        memset(pa, 0, sizeof pa); pa[0] = 1;
        for (int i = 0; i < a; i++) mulsmall(pa, 2);
        memcpy(pab, pa, sizeof pa);
        dd lab_lead = la_lead; int lab_e = la_e;
        for (int b = 0; ; b++) {
            if (b) { lead_mul(&lab_lead, &lab_e, 3.0); mulsmall(pab, 3); }
            if (lab_e >= dmax) break;
            memcpy(r, pab, sizeof pab);
            dd lead = lab_lead; int e = lab_e;
            for (int c = 0; ; c++) {
                if (c) { lead_mul(&lead, &e, 7.0); mulsmall(r, 7); }
                if (e >= dmax) break;
                tested++;
                int ndigits = e + 1;
                if (ndigits >= 13 && lead.hi > 1.000001 && lead.hi < 9.999999) {
                    double d = lead.hi * LEADEPS;
                    uint64_t v0 = floor12(lead.hi, lead.lo - d);
                    uint64_t v1 = floor12(lead.hi, lead.lo + d);
                    if (hi_zero(v0) && hi_zero(v1)) continue;
                }
                {
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
