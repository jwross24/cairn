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

int main(int argc,char**argv){
    int dmax=atoi(argv[1]); int stride=atoi(argv[2]); int a_lo=atoi(argv[3]), a_hi=atoi(argv[4]);
    dd la_lead={1.0,0.0}; int la_e=0;
    for(int i=0;i<a_lo;i++) lead_mul(&la_lead,&la_e,2.0);
    long n=0;
    for(int a=a_lo;a<a_hi;a++){
        if(a>a_lo) lead_mul(&la_lead,&la_e,2.0);
        if(la_e>=dmax) break;
        dd lab=la_lead; int le=la_e;
        for(int b=0;;b++){
            if(b) lead_mul(&lab,&le,3.0);
            if(le>=dmax) break;
            dd ld=lab; int e=le;
            for(int c=0;;c++){
                if(c) lead_mul(&ld,&e,7.0);
                if(e>=dmax) break;
                if((n++)%stride==0) printf("%d %d %d %d %.17g %.17g\n",a,b,c,e,ld.hi,ld.lo);
            }
        }
    }
    return 0;
}
