/*
 * libpydesc: batched classification and 10-adic descent of persistence-lifting survivors.
 *
 * Semantics are those of tier0v2.classify / ten_adic_K and descent.descend. Anything the library
 * does not decide exactly (a limit exceeded, an invariant that fails) is reported as code 9 and the
 * caller redoes that survivor in Python.
 */
#include <gmp.h>
#include <pthread.h>
#include <setjmp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXQ 32
#define MAXENT 160
#define KLIM 1400
#define KDESC (KLIM - 8)
#define MAXDEPTH 12
#define BUFSZ (KLIM + 64)
#define NA 72
#define LATLIMIT 4000000

typedef unsigned __int128 u128;
typedef uint64_t u64;

static int G_L, G_kcap, G_q;
static int G_M[MAXQ];
static int G_Mc[10];
static jmp_buf G_jb;
static pthread_mutex_t G_mu = PTHREAD_MUTEX_INITIALIZER;

#define FAIL() _longjmp(G_jb, 1)

typedef struct {
    int d;
    long e;
} ent;

typedef struct {
    int n, cap;
    mpz_t *v;
} svec;

static void sv_init(svec *s) { s->n = 0; s->cap = 0; s->v = NULL; }
static void sv_push(svec *s, const mpz_t x) {
    if (s->n == s->cap) {
        s->cap = s->cap ? s->cap * 2 : 4;
        s->v = (mpz_t *)realloc(s->v, sizeof(mpz_t) * s->cap);
    }
    mpz_init_set(s->v[s->n++], x);
}
static void sv_clear(svec *s) {
    for (int i = 0; i < s->n; i++) mpz_clear(s->v[i]);
    free(s->v);
    s->v = NULL; s->n = s->cap = 0;
}

static mpz_t p5[KLIM + 3];
static int p5_built = 0;
static mpz_t p10[KLIM + 3];
static int p10_built = 0;
static mpz_t ginv[KLIM + 3][5];
static mpz_t ginv0[4];
static mpz_t modbig, gcur;
static int ginv_built_to = 0;
static mpz_t l7tab[KLIM + 3];
static unsigned char l7have[KLIM + 3];
static int tables_ready = 0;

#define NK 28
static u64 P5U[NK];
static u64 gis[NK][NK][5];
static u64 gi0s[NK][4];

static void ensure_p5(int k) {
    while (p5_built <= k) {
        if (p5_built == 0) mpz_init_set_ui(p5[0], 1);
        else { mpz_init(p5[p5_built]); mpz_mul_ui(p5[p5_built], p5[p5_built - 1], 5); }
        p5_built++;
    }
}

static void ensure_p10(int k) {
    while (p10_built <= k) {
        if (p10_built == 0) mpz_init_set_ui(p10[0], 1);
        else { mpz_init(p10[p10_built]); mpz_mul_ui(p10[p10_built], p10[p10_built - 1], 10); }
        p10_built++;
    }
}

static void init_tables(void) {
    if (tables_ready) return;
    ensure_p5(KLIM + 2);
    ensure_p10(KLIM + 2);
    mpz_init_set(modbig, p5[KLIM + 2]);
    mpz_t g3, inv3;
    mpz_init_set_ui(g3, 3);
    mpz_init(inv3);
    mpz_invert(inv3, g3, modbig);
    mpz_init_set_ui(ginv0[0], 1);
    for (int x = 1; x < 4; x++) {
        mpz_init(ginv0[x]);
        mpz_mul(ginv0[x], ginv0[x - 1], inv3);
        mpz_mod(ginv0[x], ginv0[x], modbig);
    }
    mpz_clear(g3);
    mpz_clear(inv3);
    mpz_init_set_ui(gcur, 81);
    for (int j = 0; j < KLIM + 3; j++) {
        mpz_init(l7tab[j]); l7have[j] = 0;
        for (int t = 0; t < 5; t++) mpz_init(ginv[j][t]);
    }
    P5U[0] = 1;
    for (int k = 1; k < NK; k++) P5U[k] = P5U[k - 1] * 5;
    tables_ready = 1;
}

static void ensure_ginv(int k) {
    while (ginv_built_to < k) {
        int j = ginv_built_to + 1;
        mpz_t Gi;
        mpz_init(Gi);
        mpz_invert(Gi, gcur, modbig);
        mpz_set_ui(ginv[j][0], 1);
        for (int t = 1; t < 5; t++) {
            mpz_mul(ginv[j][t], ginv[j][t - 1], Gi);
            mpz_mod(ginv[j][t], ginv[j][t], modbig);
        }
        mpz_powm_ui(gcur, gcur, 5, modbig);
        mpz_clear(Gi);
        ginv_built_to = j;
    }
}

static int small_ready = 0;
static void ensure_small(void) {
    if (small_ready) return;
    ensure_ginv(NK);
    for (int k = 1; k < NK; k++) {
        for (int x = 0; x < 4; x++) gi0s[k][x] = mpz_fdiv_ui(ginv0[x], P5U[k]);
        for (int j = 1; j < k; j++)
            for (int t = 0; t < 5; t++) gis[k][j][t] = mpz_fdiv_ui(ginv[j][t], P5U[k]);
    }
    small_ready = 1;
}

static inline u64 mulmod(u64 a, u64 b, u64 m) { return m < 0x100000000ULL ? (a * b) % m : (u64)(((u128)a * b) % m); }

/* x in [0, 4*5^(k-1)) with 3^x = u (mod 5^k), k < NK; u a unit */
static u64 dlog5_u64(u64 u, int k) {
    static const int x1tab[5] = {-1, 0, 3, 1, 2};
    u64 m = P5U[k];
    u64 r = u % m;
    unsigned u5 = (unsigned)(r % 5);
    if (u5 == 0) FAIL();
    int x1 = x1tab[u5];
    r = mulmod(r, gi0s[k][x1], m);
    u64 x = (u64)x1;
    for (int j = 1; j < k; j++) {
        unsigned t = (unsigned)(((r - 1) / P5U[j]) % 5);
        if (t) {
            x += 4 * P5U[j - 1] * t;
            r = mulmod(r, gis[k][j][t], m);
        }
    }
    return x;
}

static void dlog5_mpz(mpz_t x, const mpz_t u, int k) {
    static mpz_t r, w, f;
    static int inited = 0;
    if (!inited) { mpz_inits(r, w, f, NULL); inited = 1; }
    ensure_ginv(k);
    mpz_fdiv_r(r, u, p5[k]);
    unsigned long u5 = mpz_fdiv_ui(r, 5);
    if (u5 == 0) FAIL();
    static const int x1tab[5] = {-1, 0, 3, 1, 2};
    int x1 = x1tab[u5];
    mpz_mul(r, r, ginv0[x1]);
    mpz_fdiv_r(r, r, p5[k]);
    mpz_set_ui(x, (unsigned long)x1);
    for (int j = 1; j < k; j++) {
        mpz_sub_ui(w, r, 1);
        mpz_fdiv_q(w, w, p5[j]);
        unsigned long t = mpz_fdiv_ui(w, 5);
        if (t) {
            mpz_mul_ui(f, p5[j - 1], 4 * t);
            mpz_add(x, x, f);
            mpz_mul(r, r, ginv[j][t]);
            mpz_fdiv_r(r, r, p5[k]);
        }
    }
}

static void ensure_l7(int k) {
    if (l7have[k]) return;
    mpz_t u;
    mpz_init_set_ui(u, 7);
    dlog5_mpz(l7tab[k], u, k);
    mpz_clear(u);
    l7have[k] = 1;
}

static long v2z(const mpz_t x) { return (long)mpz_scan1(x, 0); }

static void egcd(mpz_t g, mpz_t x0, mpz_t y0, const mpz_t A, const mpz_t B) {
    static mpz_t a, b, x1, y1, q, r, t;
    static int inited = 0;
    if (!inited) { mpz_inits(a, b, x1, y1, q, r, t, NULL); inited = 1; }
    mpz_set(a, A); mpz_set(b, B);
    mpz_set_ui(x0, 1); mpz_set_ui(y0, 0); mpz_set_ui(x1, 0); mpz_set_ui(y1, 1);
    while (mpz_sgn(b) != 0) {
        mpz_fdiv_qr(q, r, a, b);
        mpz_set(a, b); mpz_set(b, r);
        mpz_mul(t, q, x1); mpz_sub(t, x0, t); mpz_set(x0, x1); mpz_set(x1, t);
        mpz_mul(t, q, y1); mpz_sub(t, y0, t); mpz_set(y0, y1); mpz_set(y1, t);
    }
    if (mpz_sgn(a) < 0) { mpz_neg(a, a); mpz_neg(x0, x0); mpz_neg(y0, y0); }
    mpz_set(g, a);
}

static void reduce2(mpz_t u1b, mpz_t u1c, mpz_t u2b, mpz_t u2c) {
    static mpz_t n1, n2, d, q, t, n;
    static int inited = 0;
    if (!inited) { mpz_inits(n1, n2, d, q, t, n, NULL); inited = 1; }
    for (;;) {
        mpz_mul(n1, u1b, u1b); mpz_addmul(n1, u1c, u1c);
        mpz_mul(n2, u2b, u2b); mpz_addmul(n2, u2c, u2c);
        if (mpz_cmp(n1, n2) > 0) {
            mpz_swap(u1b, u2b); mpz_swap(u1c, u2c); mpz_swap(n1, n2);
        }
        if (mpz_sgn(n1) == 0) break;
        mpz_mul(d, u1b, u2b); mpz_addmul(d, u1c, u2c);
        mpz_mul_2exp(t, d, 1); mpz_add(t, t, n1);
        mpz_mul_2exp(n, n1, 1);
        mpz_fdiv_q(q, t, n);
        if (mpz_sgn(q) == 0) break;
        mpz_submul(u2b, q, u1b);
        mpz_submul(u2c, q, u1c);
    }
}

typedef struct lat lat;
typedef struct edge {
    int type, param;
    lat *child;
    mpz_t A, B, m, g2, us, vs;
} edge;
struct lat {
    mpz_t u1b, u1c, u2b, u2c, det;
    short Kc[NA];
    int ne, cap;
    edge **e;
};

static lat **roots = NULL;
static int nroots = 0, caproots = 0, lastroot = 0;
static long nlat = 0;
static int cache_kcap = -1;

static lat *lat_new(const mpz_t u1b, const mpz_t u1c, const mpz_t u2b, const mpz_t u2c) {
    if (++nlat > LATLIMIT) FAIL();
    lat *l = (lat *)malloc(sizeof(lat));
    mpz_init_set(l->u1b, u1b); mpz_init_set(l->u1c, u1c);
    mpz_init_set(l->u2b, u2b); mpz_init_set(l->u2c, u2c);
    mpz_init(l->det);
    mpz_mul(l->det, l->u1b, l->u2c);
    mpz_submul(l->det, l->u1c, l->u2b);
    for (int i = 0; i < NA; i++) l->Kc[i] = -1;
    l->ne = 0; l->cap = 0; l->e = NULL;
    return l;
}

static void lat_free(lat *l) {
    for (int i = 0; i < l->ne; i++) {
        edge *e = l->e[i];
        lat_free(e->child);
        mpz_clears(e->A, e->B, e->m, e->g2, e->us, e->vs, NULL);
        free(e);
    }
    free(l->e);
    mpz_clears(l->u1b, l->u1c, l->u2b, l->u2c, l->det, NULL);
    free(l);
}

static void cache_reset(int kcap) {
    for (int i = 0; i < nroots; i++) lat_free(roots[i]);
    nroots = 0; lastroot = 0; nlat = 0;
    cache_kcap = kcap;
}

static lat *find_root(const mpz_t u1b, const mpz_t u1c, const mpz_t u2b, const mpz_t u2c) {
    for (int k = 0; k < nroots; k++) {
        int i = (lastroot + k) % nroots;
        lat *l = roots[i];
        if (mpz_cmp(l->u1b, u1b) == 0 && mpz_cmp(l->u1c, u1c) == 0 && mpz_cmp(l->u2b, u2b) == 0 && mpz_cmp(l->u2c, u2c) == 0) {
            lastroot = i;
            return l;
        }
    }
    if (nroots == caproots) {
        caproots = caproots ? caproots * 2 : 8;
        roots = (lat **)realloc(roots, sizeof(lat *) * caproots);
    }
    lat *l = lat_new(u1b, u1c, u2b, u2c);
    roots[nroots] = l;
    lastroot = nroots++;
    return l;
}

/* the solution lattice of A b + B c = 0 (mod m) inside lattice p, and the data to move a coset onto it */
static edge *make_edge(lat *p, int type, int param, const mpz_t A, const mpz_t B, const mpz_t m) {
    mpz_t A2, B2, g1, u, v, C, g2, s, t, k1b, k1c, k2b, k2c, T, nu1b, nu1c, nu2b, nu2c;
    mpz_inits(A2, B2, g1, u, v, C, g2, s, t, k1b, k1c, k2b, k2c, T, nu1b, nu1c, nu2b, nu2c, NULL);
    mpz_mul(A2, A, p->u1b); mpz_addmul(A2, B, p->u1c); mpz_fdiv_r(A2, A2, m);
    mpz_mul(B2, A, p->u2b); mpz_addmul(B2, B, p->u2c); mpz_fdiv_r(B2, B2, m);
    egcd(g1, u, v, A2, B2);
    mpz_neg(C, m);
    egcd(g2, s, t, g1, C);
    if (mpz_sgn(g2) == 0) FAIL();
    if (mpz_sgn(g1) == 0) {
        mpz_set_ui(k1b, 1); mpz_set_ui(k1c, 0); mpz_set_ui(k2b, 0); mpz_set_ui(k2c, 1);
    } else {
        mpz_divexact(k1b, B2, g1);
        mpz_divexact(k1c, A2, g1); mpz_neg(k1c, k1c);
        mpz_mul(T, u, C); mpz_neg(T, T); mpz_divexact(k2b, T, g2);
        mpz_mul(T, v, C); mpz_neg(T, T); mpz_divexact(k2c, T, g2);
    }
    mpz_mul(nu1b, k1b, p->u1b); mpz_addmul(nu1b, k1c, p->u2b);
    mpz_mul(nu1c, k1b, p->u1c); mpz_addmul(nu1c, k1c, p->u2c);
    mpz_mul(nu2b, k2b, p->u1b); mpz_addmul(nu2b, k2c, p->u2b);
    mpz_mul(nu2c, k2b, p->u1c); mpz_addmul(nu2c, k2c, p->u2c);
    reduce2(nu1b, nu1c, nu2b, nu2c);
    edge *e = (edge *)malloc(sizeof(edge));
    e->type = type; e->param = param;
    mpz_init_set(e->A, A); mpz_init_set(e->B, B); mpz_init_set(e->m, m);
    mpz_init_set(e->g2, g2);
    mpz_init(e->us); mpz_mul(e->us, u, s);
    mpz_init(e->vs); mpz_mul(e->vs, v, s);
    e->child = lat_new(nu1b, nu1c, nu2b, nu2c);
    mpz_clears(A2, B2, g1, u, v, C, g2, s, t, k1b, k1c, k2b, k2c, T, nu1b, nu1c, nu2b, nu2c, NULL);
    if (p->ne == p->cap) {
        p->cap = p->cap ? p->cap * 2 : 8;
        p->e = (edge **)realloc(p->e, sizeof(edge *) * p->cap);
    }
    p->e[p->ne++] = e;
    return e;
}

static edge *get_edge(lat *p, int type, int param) {
    for (int i = 0; i < p->ne; i++) {
        edge *e = p->e[i];
        if (e->type == type && e->param == param) return e;
    }
    static mpz_t A, B, m;
    static int inited = 0;
    if (!inited) { mpz_inits(A, B, m, NULL); inited = 1; }
    if (type != 1) FAIL();
    ensure_l7(param);
    mpz_set_ui(A, 1); mpz_set(B, l7tab[param]);
    mpz_mul_ui(m, p5[param - 1], 4);
    return make_edge(p, type, param, A, B, m);
}

/* v0 of the coset on e->child, from v0 = (vb, vc) on p and the right-hand side r; 0 if empty. ob/oc may alias vb/vc. */
static int apply_edge(const edge *e, const lat *p, mpz_t ob, mpz_t oc, const mpz_t vb, const mpz_t vc, const mpz_t r) {
    static mpz_t r2, f, x0, y0;
    static int inited = 0;
    if (!inited) { mpz_inits(r2, f, x0, y0, NULL); inited = 1; }
    mpz_mul(r2, e->A, vb); mpz_addmul(r2, e->B, vc); mpz_sub(r2, r, r2); mpz_fdiv_r(r2, r2, e->m);
    if (!mpz_divisible_p(r2, e->g2)) return 0;
    mpz_divexact(f, r2, e->g2);
    mpz_mul(x0, e->us, f);
    mpz_mul(y0, e->vs, f);
    mpz_mul(r2, x0, p->u1b); mpz_addmul(r2, y0, p->u2b); mpz_add(r2, r2, vb);
    mpz_mul(f, x0, p->u1c); mpz_addmul(f, y0, p->u2c); mpz_add(f, f, vc);
    mpz_set(ob, r2);
    mpz_set(oc, f);
    return 1;
}

static int lat_contains(const lat *l, const mpz_t vb, const mpz_t vc, const mpz_t b, const mpz_t c) {
    static mpz_t db, dc, xn, yn;
    static int inited = 0;
    if (!inited) { mpz_inits(db, dc, xn, yn, NULL); inited = 1; }
    if (mpz_sgn(l->det) == 0) FAIL();
    mpz_sub(db, b, vb); mpz_sub(dc, c, vc);
    mpz_mul(xn, db, l->u2c); mpz_submul(xn, dc, l->u2b);
    mpz_mul(yn, dc, l->u1b); mpz_submul(yn, db, l->u1c);
    return mpz_divisible_p(xn, l->det) && mpz_divisible_p(yn, l->det);
}

/* min(limit, v5(3^be 7^ga - 1), a + v2(3^be 7^ga - 1)) */
static long vecK(const mpz_t be, const mpz_t ga, long a, long limit) {
    if (limit <= 0) return 0;
    static mpz_t m, phi, e, z, z2, T, B;
    static int inited = 0;
    if (!inited) { mpz_inits(m, phi, e, z, z2, T, B, NULL); inited = 1; }
    long kk = 16;
    for (;;) {
        if (kk > limit) kk = limit;
        int exact5, exact2;
        long c5, c2;
        mpz_set(m, p5[kk]);
        mpz_mul_ui(phi, p5[kk - 1], 4);
        mpz_fdiv_r(e, be, phi);
        mpz_set_ui(B, 3);
        mpz_powm(z, B, e, m);
        mpz_fdiv_r(e, ga, phi);
        mpz_set_ui(B, 7);
        mpz_powm(T, B, e, m);
        mpz_mul(z, z, T);
        mpz_fdiv_r(z, z, m);
        mpz_sub_ui(T, z, 1);
        if (mpz_sgn(T) == 0) { exact5 = 0; c5 = kk; }
        else { exact5 = 1; c5 = (long)mpz_remove(T, T, p5[1]); }
        mpz_set_ui(m, 1);
        mpz_mul_2exp(m, m, kk);
        {
            int sh = kk >= 3 ? kk - 2 : 1;
            mpz_fdiv_r_2exp(e, be, sh);
            mpz_set_ui(B, 3);
            mpz_powm(z2, B, e, m);
            mpz_fdiv_r_2exp(e, ga, sh);
            mpz_set_ui(B, 7);
            mpz_powm(T, B, e, m);
            mpz_mul(z2, z2, T);
            mpz_fdiv_r_2exp(z2, z2, kk);
        }
        mpz_sub_ui(T, z2, 1);
        if (mpz_sgn(T) == 0) { exact2 = 0; c2 = a + kk; }
        else { exact2 = 1; c2 = a + (long)mpz_scan1(T, 0); }
        long val = limit;
        int via_inexact = 0;
        if (c5 < val) { val = c5; via_inexact = !exact5; }
        else if (c5 == val && !exact5 && val < limit) via_inexact = 1;
        if (c2 < val) { val = c2; via_inexact = !exact2; }
        else if (c2 == val && !exact2 && val < limit) via_inexact = 1;
        if (!via_inexact || kk >= limit) return val;
        kk *= 2;
    }
}

static long lat_K(lat *l, long a) {
    if (a >= 0 && a < NA && l->Kc[a] >= 0) return l->Kc[a];
    long K = vecK(l->u1b, l->u1c, a, G_kcap);
    if (K != 0) {
        long K2 = vecK(l->u2b, l->u2c, a, K);
        if (K2 < K) K = K2;
    }
    if (a >= 0 && a < NA) l->Kc[a] = (short)K;
    return K;
}

/* 2^a 3^b 7^c mod 10^K */
static void tailval(mpz_t Y, long a, const mpz_t b, const mpz_t c, int K) {
    static mpz_t phi, e, T;
    static int inited = 0;
    if (!inited) { mpz_inits(phi, e, T, NULL); inited = 1; }
    mpz_mul_ui(phi, p10[K - 1], 4);
    mpz_fdiv_r(e, b, phi);
    mpz_set_ui(T, 3);
    mpz_powm(Y, T, e, p10[K]);
    mpz_fdiv_r(e, c, phi);
    mpz_set_ui(T, 7);
    mpz_powm(T, T, e, p10[K]);
    mpz_mul(Y, Y, T);
    mpz_fdiv_r(Y, Y, p10[K]);
    mpz_set_ui(T, 2);
    mpz_powm_ui(T, T, (unsigned long)a, p10[K]);
    mpz_mul(Y, Y, T);
    mpz_fdiv_r(Y, Y, p10[K]);
}

static int factor237(const mpz_t y0, long f[3]) {
    static mpz_t y;
    static int inited = 0;
    if (!inited) { mpz_init(y); inited = 1; }
    if (mpz_sgn(y0) <= 0) FAIL();
    mpz_set(y, y0);
    f[0] = (long)mpz_scan1(y, 0);
    mpz_tdiv_q_2exp(y, y, f[0]);
    f[1] = 0; f[2] = 0;
    while (mpz_divisible_ui_p(y, 3)) { mpz_divexact_ui(y, y, 3); f[1]++; }
    while (mpz_divisible_ui_p(y, 7)) { mpz_divexact_ui(y, y, 7); f[2]++; }
    return mpz_cmp_ui(y, 1) == 0;
}

static int digit_product_ok(const char *s, int n) {
    int cnt[10] = {0};
    for (int i = 0; i < n; i++) {
        char ch = s[i];
        if (ch == '0') return 0;
        if (ch != '1') cnt[ch - '0']++;
    }
    for (int d = 0; d < 10; d++)
        if (cnt[d] != G_Mc[d]) return 0;
    return 1;
}

static void sort_long(long *v, int n) {
    for (int i = 1; i < n; i++) {
        long x = v[i];
        int j = i - 1;
        while (j >= 0 && v[j] > x) { v[j + 1] = v[j]; j--; }
        v[j + 1] = x;
    }
}

static inline long emod(long e) { long r = e % G_L; return r < 0 ? r + G_L : r; }

static int have_eq_want(const char *s, int n, const ent *ents, int ne) {
    long hv[MAXENT + 8];
    long wv[MAXENT + 8];
    int nh = 0;
    for (int i = 0; i < n; i++) {
        char ch = s[n - 1 - i];
        if (ch == '1') continue;
        if (nh >= MAXENT) FAIL();
        hv[nh++] = (long)(ch - '0') * 1000 + (i % G_L);
    }
    if (nh != ne) return 0;
    for (int j = 0; j < ne; j++) wv[j] = (long)ents[j].d * 1000 + emod(ents[j].e);
    sort_long(hv, nh);
    sort_long(wv, ne);
    return memcmp(hv, wv, sizeof(long) * nh) == 0;
}

typedef struct {
    mpz_t Y, Yp, T, T2, P, cb, cc, tb, tc, lZ, Z, w;
} frame;
static frame FR[MAXDEPTH + 3];
static int frames_ready = 0;
static void init_frames(void) {
    if (frames_ready) return;
    for (int i = 0; i < MAXDEPTH + 3; i++)
        mpz_inits(FR[i].Y, FR[i].Yp, FR[i].T, FR[i].T2, FR[i].P, FR[i].cb, FR[i].cc, FR[i].tb, FR[i].tc, FR[i].lZ, FR[i].Z, FR[i].w, NULL);
    frames_ready = 1;
}

/* cut of the coset (p; vb, vc) by 2^a 3^b 7^c = Yp (mod 10^Kp). 1: result on *Lout with v0 (ob, oc); 0: empty. */
static int cut_coset(frame *fr, lat **Lout, mpz_t ob, mpz_t oc, lat *p, const mpz_t vb, const mpz_t vc, long a, const mpz_t Yp, int Kp) {
    if (Kp < 3 || Kp > KLIM - 4) FAIL();
    ensure_l7(Kp);
    mpz_ptr lZ = fr->lZ, Z = fr->Z, w = fr->w;
    if (Kp < NK) {
        ensure_small();
        u64 m = P5U[Kp];
        u64 y = mpz_fdiv_ui(Yp, m);
        u64 inv2 = (m + 1) / 2;
        u64 pw = 1, bs = inv2;
        for (unsigned long ee = (unsigned long)a; ee; ee >>= 1) {
            if (ee & 1) pw = mulmod(pw, bs, m);
            bs = mulmod(bs, bs, m);
        }
        u64 z5 = mulmod(y, pw, m);
        mpz_set_ui(lZ, dlog5_u64(z5, Kp));
    } else {
        mpz_add_ui(w, p5[Kp], 1);
        mpz_tdiv_q_2exp(w, w, 1);
        mpz_powm_ui(w, w, (unsigned long)a, p5[Kp]);
        mpz_fdiv_r(Z, Yp, p5[Kp]);
        mpz_mul(Z, Z, w);
        mpz_fdiv_r(Z, Z, p5[Kp]);
        dlog5_mpz(lZ, Z, Kp);
    }
    edge *e1 = get_edge(p, 1, Kp);
    if (!apply_edge(e1, p, fr->tb, fr->tc, vb, vc, lZ)) return 0;
    lat *L1 = e1->child;
    mpz_fdiv_r_2exp(w, Yp, Kp);
    if (Kp <= a) {
        if (mpz_sgn(w) != 0) return 0;
        *Lout = L1; mpz_set(ob, fr->tb); mpz_set(oc, fr->tc);
        return 1;
    }
    if (mpz_sgn(w) == 0 || v2z(w) != a) return 0;
    if (Kp - a != 1) FAIL();
    *Lout = L1; mpz_set(ob, fr->tb); mpz_set(oc, fr->tc);
    return 1;
}

/* 0 DEAD, 1 OPEN. ents: pattern (D, eps) with ne entries. Y is the tail of the coset (lat l; vb, vc) at K digits, s its decimal string. */
static int descend_core(long a, const ent *ents, int ne, long nu, lat *l, const mpz_t vb, const mpz_t vc, int K, int depth, svec *sols, const mpz_t Y, const char *s, int len);

static int descend_tail(long a, const ent *rem, int nr, long nu, lat *l, const mpz_t vb, const mpz_t vc, int K, int depth, svec *sols, const mpz_t Y) {
    char s[BUFSZ];
    if (K > KDESC) FAIL();
    mpz_get_str(s, 10, Y);
    int len = (int)strlen(s);
    int pad = K - len;
    if (pad < 0) FAIL();
    char tail[BUFSZ];
    memset(tail, '0', pad);
    memcpy(tail + pad, s, len);
    ent full[MAXENT];
    int nf = 0;
    for (int i = 0; i < K; i++) {
        char ch = tail[K - 1 - i];
        if (ch == '1') continue;
        if (nf >= MAXENT) FAIL();
        full[nf].d = ch - '0';
        full[nf].e = i;
        nf++;
    }
    if (nf + nr > MAXENT) FAIL();
    for (int j = 0; j < nr; j++) full[nf + j] = rem[j];
    return descend_core(a, full, nf + nr, nu, l, vb, vc, K, depth, sols, Y, s, len);
}

static int descend_core(long a, const ent *ents, int ne, long nu, lat *l, const mpz_t vb, const mpz_t vc, int K, int depth, svec *sols, const mpz_t Y, const char *s, int len) {
    if (K < 1 || K > KDESC) FAIL();
    frame *fr = &FR[depth];
    if (mpz_cmp_ui(Y, 10) >= 0 && len % G_L == nu && digit_product_ok(s, len)) {
        long f[3];
        if (factor237(Y, f) && f[0] == a) {
            mpz_set_si(fr->T, f[1]); mpz_set_si(fr->T2, f[2]);
            if (lat_contains(l, vb, vc, fr->T, fr->T2) && have_eq_want(s, len, ents, ne)) sv_push(sols, Y);
        }
    }
    if (len != K) FAIL();
    for (int i = 0; i < len; i++) if (s[i] == '0') return 0;
    ent avail[MAXENT];
    int na = ne;
    memcpy(avail, ents, sizeof(ent) * ne);
    for (int i = 0; i < K; i++) {
        char ch = s[K - 1 - i];
        if (ch == '1') continue;
        int d = ch - '0';
        int jf = -1;
        for (int j = 0; j < na; j++)
            if (avail[j].d == d && emod(avail[j].e) == i % G_L) { jf = j; break; }
        if (jf < 0) return 0;
        for (int j = jf; j + 1 < na; j++) avail[j] = avail[j + 1];
        na--;
    }
    mpz_mul_ui(fr->T, Y, 9);
    mpz_sub(fr->T, fr->T, p10[K]);
    if (mpz_sgn(fr->T) == 0) return 1;
    mpz_abs(fr->T, fr->T);
    long t = v2z(fr->T);
    if (a == t) return 1;
    if (t < K) return 0;
    if (na == 0) {
        for (long n = K + 1; n <= t; n++) {
            if (n % G_L != nu) continue;
            if (n - K > KLIM) FAIL();
            mpz_sub_ui(fr->T, p10[n - K], 1);
            mpz_divexact_ui(fr->T, fr->T, 9);
            mpz_mul(fr->T, fr->T, p10[K]);
            mpz_add(fr->T, fr->T, Y);
            long f[3];
            if (!factor237(fr->T, f) || f[0] != a) continue;
            mpz_set_si(fr->T2, f[1]); mpz_set_si(fr->P, f[2]);
            if (!lat_contains(l, vb, vc, fr->T2, fr->P)) continue;
            char sy[BUFSZ];
            if (mpz_sizeinbase(fr->T, 10) > BUFSZ - 8) FAIL();
            mpz_get_str(sy, 10, fr->T);
            if (digit_product_ok(sy, (int)strlen(sy))) sv_push(sols, fr->T);
        }
        return 0;
    }
    int status = 0;
    for (int j = 0; j < na; j++) {
        int dup = 0;
        for (int j0 = 0; j0 < j; j0++)
            if (avail[j0].d == avail[j].d && avail[j0].e == avail[j].e) { dup = 1; break; }
        if (dup) continue;
        int d = avail[j].d;
        long e_res = avail[j].e;
        for (long e = K; e <= t; e++) {
            if (emod(e) != emod(e_res)) continue;
            long Kp = e + 1;
            if (Kp < 3) continue;
            if (Kp > KDESC - 4 || Kp > G_kcap) FAIL();
            mpz_sub_ui(fr->Yp, p10[e - K], 1);
            mpz_divexact_ui(fr->Yp, fr->Yp, 9);
            mpz_mul(fr->Yp, fr->Yp, p10[K]);
            mpz_add(fr->Yp, fr->Yp, Y);
            mpz_addmul_ui(fr->Yp, p10[e], (unsigned long)d);
            lat *L2;
            if (!cut_coset(fr, &L2, fr->cb, fr->cc, l, vb, vc, a, fr->Yp, (int)Kp)) continue;
            long K2 = lat_K(L2, a);
            if (K2 != Kp) FAIL();
            if (depth >= MAXDEPTH) return 1;
            ent rem[MAXENT];
            int nr = 0;
            for (int j2 = 0; j2 < na; j2++)
                if (j2 != j) rem[nr++] = avail[j2];
            frame *ch = &FR[depth + 1];
            mpz_set(ch->Y, fr->Yp);
            int st = descend_tail(a, rem, nr, nu, L2, fr->cb, fr->cc, (int)K2, depth + 1, sols, ch->Y);
            if (st == 1) status = 1;
        }
    }
    return status;
}

/* result codes: 0 DEAD, 1 SOLUTION, 2 OPEN, 3 RESOLVED(descent) */
static int classify_one(long a, long nu, const long *eps, lat *l, const mpz_t vb, const mpz_t vc, int do_descent, svec *sols) {
    if (a < 0) FAIL();
    nu = emod(nu);
    long K = lat_K(l, a);
    if (K == 0) return 2;
    frame *fr = &FR[0];
    if (K > KDESC) FAIL();
    tailval(fr->Y, a, vb, vc, (int)K);
    char s[BUFSZ];
    mpz_get_str(s, 10, fr->Y);
    int len = (int)strlen(s);
    int have_sol = 0;
    ent ents[MAXQ];
    for (int i = 0; i < G_q; i++) { ents[i].d = G_M[i]; ents[i].e = eps[i]; }
    if (mpz_sgn(fr->Y) > 0 && len % G_L == nu && digit_product_ok(s, len)) {
        long f[3];
        if (factor237(fr->Y, f) && f[0] == a) {
            mpz_set_si(fr->T, f[1]); mpz_set_si(fr->T2, f[2]);
            if (lat_contains(l, vb, vc, fr->T, fr->T2) && have_eq_want(s, len, ents, G_q)) have_sol = 1;
        }
    }
    int pad = (int)K - len;
    if (pad < 0) FAIL();
    int open_ok = 1;
    if (pad > 0) open_ok = 0;
    else {
        int zero = 0, cnt[10] = {0};
        for (int i = 0; i < K; i++) { if (s[i] == '0') { zero = 1; break; } if (s[i] != '1') cnt[s[i] - '0']++; }
        if (zero) open_ok = 0;
        else {
            for (int d = 0; d < 10; d++) if (cnt[d] > G_Mc[d]) { open_ok = 0; break; }
            if (open_ok) {
                long hv[MAXENT + 8];
                long wv[MAXQ];
                int nh = 0;
                for (int i = 0; i < K; i++) {
                    char ch = s[K - 1 - i];
                    if (ch == '1') continue;
                    if (nh >= MAXENT) FAIL();
                    hv[nh++] = (long)(ch - '0') * 1000 + (i % G_L);
                }
                for (int j = 0; j < G_q; j++) wv[j] = (long)G_M[j] * 1000 + emod(eps[j]);
                sort_long(hv, nh);
                sort_long(wv, G_q);
                int iw = 0;
                for (int ih = 0; ih < nh && open_ok; ih++) {
                    while (iw < G_q && wv[iw] < hv[ih]) iw++;
                    if (iw >= G_q || wv[iw] != hv[ih]) open_ok = 0;
                    else iw++;
                }
            }
        }
    }
    int code;
    if (have_sol) sv_push(sols, fr->Y);
    if (have_sol && !open_ok) code = 1;
    else if (!have_sol && !open_ok) code = 0;
    else if (K >= 1 && do_descent) {
        int st = descend_core(a, ents, G_q, nu, l, vb, vc, (int)K, 0, sols, fr->Y, s, len);
        code = st == 1 ? 2 : 3;
    } else code = 2;
    return code;
}

static char *next_tok(char **p) {
    char *s = *p;
    while (*s == ' ' || *s == '\n' || *s == '\r' || *s == '\t') s++;
    if (!*s) { *p = s; return NULL; }
    char *e = s;
    while (*e && *e != ' ' && *e != '\n' && *e != '\r' && *e != '\t') e++;
    if (*e) *e++ = 0;
    *p = e;
    return s;
}

typedef struct { char *buf; size_t n, cap; } obuf;
static void ob_put(obuf *o, const char *s, size_t n) {
    if (o->n + n + 1 > o->cap) {
        while (o->n + n + 1 > o->cap) o->cap = o->cap ? o->cap * 2 : 1 << 16;
        o->buf = (char *)realloc(o->buf, o->cap);
    }
    memcpy(o->buf + o->n, s, n);
    o->n += n;
    o->buf[o->n] = 0;
}

static int begin_batch(int L, int kcap, int q) {
    if (q < 1 || q > MAXQ || L < 1 || L > 999 || kcap < 8 || kcap > KLIM - 8) return 3;
    init_tables();
    init_frames();
    G_L = L; G_q = q;
    if (kcap != cache_kcap || nlat > LATLIMIT / 2) cache_reset(kcap);
    G_kcap = kcap;
    return 0;
}

static int run_one(long a, long nu, const long *eps, const mpz_t u1b, const mpz_t u1c, const mpz_t u2b, const mpz_t u2c,
                   const mpz_t vb, const mpz_t vc, int do_descent, svec *sols) {
    int code;
    if (_setjmp(G_jb) == 0) {
        lat *l = find_root(u1b, u1c, u2b, u2c);
        code = classify_one(a, nu, eps, l, vb, vc, do_descent, sols);
    } else {
        code = 9;
        sv_clear(sols);
        sv_init(sols);
    }
    return code;
}

static int pydesc_batch_locked(const char *in, size_t inlen, char **out, size_t *outlen) {
    char *work = (char *)malloc(inlen + 1);
    memcpy(work, in, inlen);
    work[inlen] = 0;
    char *p = work;
    char *t;
    int L, kcap, q, do_descent;
    long n;
    if (!(t = next_tok(&p))) { free(work); return 2; } L = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } kcap = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } q = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } do_descent = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } n = atol(t);
    int rc = begin_batch(L, kcap, q);
    if (rc) { free(work); return rc; }
    memset(G_Mc, 0, sizeof G_Mc);
    for (int i = 0; i < q; i++) {
        if (!(t = next_tok(&p))) { free(work); return 2; }
        G_M[i] = atoi(t);
        if (G_M[i] < 2 || G_M[i] > 9) { free(work); return 3; }
        G_Mc[G_M[i]]++;
    }
    obuf o = {0};
    mpz_t f6[6];
    for (int j = 0; j < 6; j++) mpz_init(f6[j]);
    long eps[MAXQ];
    char line[64];
    for (long i = 0; i < n; i++) {
        long a, nu;
        if (!(t = next_tok(&p))) { rc = 2; break; } a = atol(t);
        if (!(t = next_tok(&p))) { rc = 2; break; } nu = atol(t);
        for (int j = 0; j < q; j++) { if (!(t = next_tok(&p))) { rc = 2; break; } eps[j] = atol(t); }
        if (rc) break;
        for (int j = 0; j < 6; j++) {
            if (!(t = next_tok(&p))) { rc = 2; break; }
            if (mpz_set_str(f6[j], t, 10) != 0) { rc = 2; break; }
        }
        if (rc) break;
        svec sols;
        sv_init(&sols);
        int code = run_one(a, nu, eps, f6[2], f6[3], f6[4], f6[5], f6[0], f6[1], do_descent, &sols);
        int len = snprintf(line, sizeof line, "%d %d", code, sols.n);
        ob_put(&o, line, len);
        for (int j = 0; j < sols.n; j++) {
            char *sb = mpz_get_str(NULL, 10, sols.v[j]);
            ob_put(&o, " ", 1); ob_put(&o, sb, strlen(sb)); free(sb);
        }
        ob_put(&o, "\n", 1);
        sv_clear(&sols);
    }
    for (int j = 0; j < 6; j++) mpz_clear(f6[j]);
    free(work);
    if (rc) { free(o.buf); return rc; }
    if (!o.buf) { o.buf = (char *)malloc(1); o.buf[0] = 0; }
    *out = o.buf;
    *outlen = o.n;
    return 0;
}

int pydesc_batch(const char *in, size_t inlen, char **out, size_t *outlen) {
    pthread_mutex_lock(&G_mu);
    int rc = pydesc_batch_locked(in, inlen, out, outlen);
    pthread_mutex_unlock(&G_mu);
    return rc;
}

static int read_whole(const char *path, char **buf, size_t *len) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    size_t cap = 1 << 20, n = 0;
    char *b = (char *)malloc(cap + 1);
    for (;;) {
        size_t r = fread(b + n, 1, cap - n, f);
        n += r;
        if (n < cap) break;
        cap *= 2;
        b = (char *)realloc(b, cap + 1);
    }
    int err = ferror(f);
    fclose(f);
    if (err) { free(b); return -1; }
    b[n] = 0;
    *buf = b;
    *len = n;
    return 0;
}

static int is_ws(char c) { return c == ' ' || c == '\t' || c == '\r' || c == '\n' || c == '\v' || c == '\f'; }

static int tokenize(char *s, char *e, char **tk, int *tl, int max) {
    int n = 0;
    while (s < e) {
        while (s < e && is_ws(*s)) s++;
        if (s >= e) break;
        char *b = s;
        while (s < e && !is_ws(*s)) s++;
        if (n < max) { tk[n] = b; tl[n] = (int)(s - b); }
        n++;
    }
    return n;
}

static int tok_int_ok(const char *t, int l) {
    int i = 0;
    if (l > 0 && t[0] == '-') i = 1;
    if (i >= l) return 0;
    for (; i < l; i++) if (t[i] < '0' || t[i] > '9') return 0;
    return 1;
}

#define MAXTOK (MAXQ + 16)

/* 0 ignored line, 1 OPEN, 2 EXACT, -1 a line the Python parser would not accept */
static int line_kind(char *s, char *e, int q, char **tk, int *tl) {
    int n = tokenize(s, e, tk, tl, MAXTOK);
    if (n == 0) return -1;
    if (tl[0] == 4 && memcmp(tk[0], "OPEN", 4) == 0) {
        if (n < 5 + q) return -1;
        for (int i = 1; i <= 4 + q; i++) if (!tok_int_ok(tk[i], tl[i])) return -1;
        return 1;
    }
    if (tl[0] == 5 && memcmp(tk[0], "EXACT", 5) == 0) {
        if (n < 6 + q) return -1;
        for (int i = 1; i <= 5 + q; i++) if (!tok_int_ok(tk[i], tl[i])) return -1;
        return 2;
    }
    return 0;
}

static int parse_paths(char **p, int nfiles, char **paths) {
    for (int i = 0; i < nfiles; i++) {
        char *s = *p;
        while (*s == '\n') s++;
        if (!*s) return -1;
        char *e = s;
        while (*e && *e != '\n') e++;
        if (*e) *e++ = 0;
        paths[i] = s;
        *p = e;
    }
    return 0;
}

int pydesc_scan12(const char *in, size_t inlen, char **out, size_t *outlen) {
    char *work = (char *)malloc(inlen + 1);
    memcpy(work, in, inlen);
    work[inlen] = 0;
    char *p = work, *t;
    int q, nfiles;
    if (!(t = next_tok(&p))) { free(work); return 2; } q = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } nfiles = atoi(t);
    if (q < 1 || q > MAXQ || nfiles < 0 || nfiles > 4096) { free(work); return 3; }
    char **paths = (char **)malloc(sizeof(char *) * (nfiles + 1));
    if (parse_paths(&p, nfiles, paths)) { free(paths); free(work); return 2; }
    obuf ex = {0};
    long n_open = 0, n_exact = 0;
    int rc = 0;
    char *tk[MAXTOK];
    int tl[MAXTOK];
    for (int fi = 0; fi < nfiles && !rc; fi++) {
        char *buf; size_t len;
        if (read_whole(paths[fi], &buf, &len)) { rc = 5; break; }
        char *s = buf, *end = buf + len;
        while (s < end) {
            char *e = (char *)memchr(s, '\n', end - s);
            if (!e) e = end;
            if (s == e && e == end) break;
            int k = line_kind(s, e, q, tk, tl);
            if (k < 0) { rc = 4; break; }
            if (k == 1) n_open++;
            else if (k == 2) { n_exact++; ob_put(&ex, s, e - s); ob_put(&ex, "\n", 1); }
            s = e + 1;
        }
        free(buf);
    }
    free(paths);
    free(work);
    if (rc) { free(ex.buf); return rc; }
    char head[64];
    int hl = snprintf(head, sizeof head, "%ld %ld\n", n_open, n_exact);
    char *o = (char *)malloc(hl + ex.n + 1);
    memcpy(o, head, hl);
    if (ex.n) memcpy(o + hl, ex.buf, ex.n);
    o[hl + ex.n] = 0;
    free(ex.buf);
    *out = o;
    *outlen = hl + ex.n;
    return 0;
}

static int pydesc_batch12_locked(const char *in, size_t inlen, char **out, size_t *outlen) {
    char *work = (char *)malloc(inlen + 1);
    memcpy(work, in, inlen);
    work[inlen] = 0;
    char *p = work, *t;
    int L, kcap, q, do_descent, nfiles;
    if (!(t = next_tok(&p))) { free(work); return 2; } L = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } kcap = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } q = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } do_descent = atoi(t);
    if (!(t = next_tok(&p))) { free(work); return 2; } nfiles = atoi(t);
    if (nfiles < 0 || nfiles > 4096) { free(work); return 3; }
    int rc0 = begin_batch(L, kcap, q);
    if (rc0) { free(work); return rc0; }
    memset(G_Mc, 0, sizeof G_Mc);
    for (int i = 0; i < q; i++) {
        if (!(t = next_tok(&p))) { free(work); return 2; }
        G_M[i] = atoi(t);
        if (G_M[i] < 2 || G_M[i] > 9 || (i > 0 && G_M[i] < G_M[i - 1])) { free(work); return 3; }
        G_Mc[G_M[i]]++;
    }
    mpz_t ul[4], vb, vc;
    for (int j = 0; j < 4; j++) mpz_init(ul[j]);
    mpz_init(vb); mpz_init(vc);
    for (int j = 0; j < 4; j++) {
        if (!(t = next_tok(&p)) || mpz_set_str(ul[j], t, 10) != 0) {
            for (int k = 0; k < 4; k++) mpz_clear(ul[k]);
            mpz_clear(vb); mpz_clear(vc);
            free(work);
            return 2;
        }
    }
    char **paths = (char **)malloc(sizeof(char *) * (nfiles + 1));
    int rc = 0;
    if (parse_paths(&p, nfiles, paths)) rc = 2;

    long cnt[10] = {0};
    int order[10], norder = 0;
    long nsurv = 0;
    svec allsols;
    sv_init(&allsols);
    obuf recs = {0};
    char *tk[MAXTOK];
    int tl[MAXTOK];
    char tmp[512];
    long eps[MAXQ];
    for (int fi = 0; fi < nfiles && !rc; fi++) {
        char *buf; size_t len;
        if (read_whole(paths[fi], &buf, &len)) { rc = 5; break; }
        char *s = buf, *end = buf + len;
        while (s < end) {
            char *e = (char *)memchr(s, '\n', end - s);
            if (!e) e = end;
            if (s == e && e == end) break;
            int k = line_kind(s, e, q, tk, tl);
            if (k < 0) { rc = 4; break; }
            if (k == 1) {
                long a, nu;
                int bad = 0;
                for (int i = 1; i <= 2 + q; i++) if (tl[i] > 18) bad = 1;
                if (bad) { rc = 4; break; }
                memcpy(tmp, tk[1], tl[1]); tmp[tl[1]] = 0; a = atol(tmp);
                memcpy(tmp, tk[2], tl[2]); tmp[tl[2]] = 0; nu = atol(tmp);
                for (int j = 0; j < q; j++) { memcpy(tmp, tk[3 + j], tl[3 + j]); tmp[tl[3 + j]] = 0; eps[j] = atol(tmp); }
                for (int i = 1; i < q; i++) {
                    long v = eps[i];
                    int j = i - 1;
                    while (j >= 0 && G_M[j] == G_M[i] && eps[j] > v) { eps[j + 1] = eps[j]; j--; }
                    eps[j + 1] = v;
                }
                int tb = tl[3 + q], tc = tl[4 + q];
                if (tb > 500 || tc > 500) { rc = 4; break; }
                memcpy(tmp, tk[3 + q], tb); tmp[tb] = 0;
                mpz_set_str(vb, tmp, 10);
                memcpy(tmp, tk[4 + q], tc); tmp[tc] = 0;
                mpz_set_str(vc, tmp, 10);
                svec sols;
                sv_init(&sols);
                int code = run_one(a, nu, eps, ul[0], ul[1], ul[2], ul[3], vb, vc, do_descent, &sols);
                if (cnt[code] == 0) order[norder++] = code;
                cnt[code]++;
                for (int j = 0; j < sols.n; j++) sv_push(&allsols, sols.v[j]);
                sv_clear(&sols);
                if (code == 2 || code == 9) {
                    char line[128];
                    int ll = snprintf(line, sizeof line, "%d %ld %ld %ld", code, nsurv, a, nu);
                    ob_put(&recs, line, ll);
                    for (int j = 0; j < q; j++) { ll = snprintf(line, sizeof line, " %ld", eps[j]); ob_put(&recs, line, ll); }
                    char *sb = mpz_get_str(NULL, 10, vb);
                    ob_put(&recs, " ", 1); ob_put(&recs, sb, strlen(sb)); free(sb);
                    sb = mpz_get_str(NULL, 10, vc);
                    ob_put(&recs, " ", 1); ob_put(&recs, sb, strlen(sb)); free(sb);
                    ob_put(&recs, "\n", 1);
                }
                nsurv++;
            }
            s = e + 1;
        }
        free(buf);
    }
    free(paths);
    free(work);
    for (int k = 0; k < 4; k++) mpz_clear(ul[k]);
    mpz_clear(vb); mpz_clear(vc);
    if (rc) { sv_clear(&allsols); free(recs.buf); return rc; }
    obuf o = {0};
    char line[256];
    int ll = snprintf(line, sizeof line, "%ld %ld %ld %ld %ld %ld\n", nsurv, cnt[0], cnt[1], cnt[2], cnt[3], cnt[9]);
    ob_put(&o, line, ll);
    for (int i = 0; i < norder; i++) { ll = snprintf(line, sizeof line, "%s%d", i ? " " : "", order[i]); ob_put(&o, line, ll); }
    ob_put(&o, "\n", 1);
    ll = snprintf(line, sizeof line, "%d", allsols.n);
    ob_put(&o, line, ll);
    for (int j = 0; j < allsols.n; j++) {
        char *sb = mpz_get_str(NULL, 10, allsols.v[j]);
        ob_put(&o, " ", 1); ob_put(&o, sb, strlen(sb)); free(sb);
    }
    ob_put(&o, "\n", 1);
    if (recs.n) ob_put(&o, recs.buf, recs.n);
    free(recs.buf);
    sv_clear(&allsols);
    if (!o.buf) { o.buf = (char *)malloc(1); o.buf[0] = 0; }
    *out = o.buf;
    *outlen = o.n;
    return 0;
}

int pydesc_batch12(const char *in, size_t inlen, char **out, size_t *outlen) {
    pthread_mutex_lock(&G_mu);
    int rc = pydesc_batch12_locked(in, inlen, out, outlen);
    pthread_mutex_unlock(&G_mu);
    return rc;
}

void pydesc_free(char *p) { free(p); }

int pydesc_abi(void) { return 2; }
