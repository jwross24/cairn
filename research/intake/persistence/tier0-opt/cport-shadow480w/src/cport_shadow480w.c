/*
 * cport.c -- C port of deepcut.py (Lemma C, deep 10-adic cut) and sandwich.py (Baker-lattice sandwich).
 *
 * Arithmetic: GMP (mpz) throughout. Every decision is an exact integer decision; doubles appear only in
 * printed display values. Build: see Makefile.
 *
 *   cport deepcut  --lattice L --cases C [--only K] [--depth 1] [--maxcases 200000] [--tsv F] [--sound] [--eager] [--break X]
 *   cport sandwich --lattice L --utable U --cases C --only K [--maxdepth 5] [--maxcases 2000000] [--tsv F] [--sound] [--break X]
 *   cport selftest --lattice L [--trials N]
 */
#include <gmp.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <assert.h>
#include <stdint.h>

#define LMAX 96
#define MAXE 2400
#define MAXA 64
#define KCAP 1300
#define MAXIT 320
#define KMAXC 24

static int g_eager = 0;
static int g_break_lz5 = 0, g_break_t2 = 0, g_break_nearest = 0, g_break_v2 = 0;
static long g_n5L = 0;

static double cpu_s(void) {
    struct timespec ts; clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

static void die(const char *m) { fprintf(stderr, "FATAL: %s\n", m); exit(2); }

/* ---------------------------------------------------------------- tables */
static mpz_t P5[MAXE], P10[MAXE], P2[MAXE];

static void init_tables(void) {
    for (int i = 0; i < MAXE; i++) {
        mpz_init(P5[i]); mpz_init(P10[i]); mpz_init(P2[i]);
        mpz_ui_pow_ui(P5[i], 5, i); mpz_ui_pow_ui(P10[i], 10, i); mpz_ui_pow_ui(P2[i], 2, i);
    }
}

/* ---------------------------------------------------------------- cosets */
typedef struct { mpz_t v0b, v0c, u1b, u1c, u2b, u2c; } Co;

static void co_init(Co *c) { mpz_inits(c->v0b, c->v0c, c->u1b, c->u1c, c->u2b, c->u2c, NULL); }
static void co_clear(Co *c) { mpz_clears(c->v0b, c->v0c, c->u1b, c->u1c, c->u2b, c->u2c, NULL); }
static void co_set(Co *d, const Co *s) {
    mpz_set(d->v0b, s->v0b); mpz_set(d->v0c, s->v0c); mpz_set(d->u1b, s->u1b);
    mpz_set(d->u1c, s->u1c); mpz_set(d->u2b, s->u2b); mpz_set(d->u2c, s->u2c);
}

/* port of lattice._egcd: a*x + b*y = g >= 0, floor division (Python semantics) */
static void egcd_py(mpz_t g, mpz_t x, mpz_t y, const mpz_t A, const mpz_t B) {
    mpz_t a, b, x0, y0, x1, y1, q, r, t;
    mpz_inits(a, b, x0, y0, x1, y1, q, r, t, NULL);
    mpz_set(a, A); mpz_set(b, B); mpz_set_ui(x0, 1); mpz_set_ui(y1, 1);
    while (mpz_sgn(b) != 0) {
        mpz_fdiv_qr(q, r, a, b);
        mpz_set(a, b); mpz_set(b, r);
        mpz_mul(t, q, x1); mpz_sub(t, x0, t); mpz_set(x0, x1); mpz_set(x1, t);
        mpz_mul(t, q, y1); mpz_sub(t, y0, t); mpz_set(y0, y1); mpz_set(y1, t);
    }
    if (mpz_sgn(a) < 0) { mpz_neg(a, a); mpz_neg(x0, x0); mpz_neg(y0, y0); }
    mpz_set(g, a); mpz_set(x, x0); mpz_set(y, y0);
    mpz_clears(a, b, x0, y0, x1, y1, q, r, t, NULL);
}

static void dot2(mpz_t out, const mpz_t a0, const mpz_t a1, const mpz_t b0, const mpz_t b1) {
    mpz_mul(out, a0, b0); mpz_addmul(out, a1, b1);
}

/* Lagrange-Gauss reduction with exact rounding: ends with |u1| <= |u2| and -|u1|^2 <= 2<u1,u2> < |u1|^2 */
static void co_reduce(Co *c) {
    mpz_t n1, n2, d, q, num, den;
    mpz_inits(n1, n2, d, q, num, den, NULL);
    for (;;) {
        dot2(n1, c->u1b, c->u1c, c->u1b, c->u1c);
        dot2(n2, c->u2b, c->u2c, c->u2b, c->u2c);
        if (mpz_cmp(n1, n2) > 0) {
            mpz_swap(c->u1b, c->u2b); mpz_swap(c->u1c, c->u2c); mpz_swap(n1, n2);
        }
        if (mpz_sgn(n1) == 0) break;
        dot2(d, c->u1b, c->u1c, c->u2b, c->u2c);
        mpz_mul_2exp(num, d, 1); mpz_add(num, num, n1);
        mpz_mul_2exp(den, n1, 1);
        mpz_fdiv_q(q, num, den);
        if (mpz_sgn(q) == 0) break;
        mpz_submul(c->u2b, q, c->u1b); mpz_submul(c->u2c, q, c->u1c);
    }
    mpz_clears(n1, n2, d, q, num, den, NULL);
}

/* round(p/q) = floor((2p+q)/(2q)) for q>0 */
static void round_div(mpz_t out, const mpz_t p, const mpz_t q) {
    mpz_t num, den; mpz_inits(num, den, NULL);
    mpz_mul_2exp(num, p, 1); mpz_add(num, num, q); mpz_mul_2exp(den, q, 1);
    mpz_fdiv_q(out, num, den);
    mpz_clears(num, den, NULL);
}

/* v0 <- v0 + x u1 + y u2 with (x,y) the rounded coordinates of -v0: same coset, representative near the origin */
static void co_babai(Co *c) {
    mpz_t det, xn, yn, x, y, t;
    mpz_inits(det, xn, yn, x, y, t, NULL);
    mpz_mul(det, c->u1b, c->u2c); mpz_submul(det, c->u1c, c->u2b);
    if (mpz_sgn(det) == 0) die("degenerate coset");
    mpz_mul(xn, c->v0b, c->u2c); mpz_submul(xn, c->v0c, c->u2b); mpz_neg(xn, xn);
    mpz_mul(yn, c->v0b, c->u1c); mpz_submul(yn, c->v0c, c->u1b);
    if (mpz_sgn(det) < 0) { mpz_neg(det, det); mpz_neg(xn, xn); mpz_neg(yn, yn); }
    round_div(x, xn, det); round_div(y, yn, det);
    mpz_addmul(c->v0b, x, c->u1b); mpz_addmul(c->v0b, y, c->u2b);
    mpz_addmul(c->v0c, x, c->u1c); mpz_addmul(c->v0c, y, c->u2c);
    mpz_clears(det, xn, yn, x, y, t, NULL);
}

static void co_index(mpz_t out, const Co *c) {
    mpz_mul(out, c->u1b, c->u2c); mpz_submul(out, c->u1c, c->u2b); mpz_abs(out, out);
}

/* exact membership: (b,c) in v0 + Z u1 + Z u2 */
static int co_contains(const Co *c, const mpz_t b, const mpz_t cc) {
    mpz_t d, db, dc, xn, yn; int ok;
    mpz_inits(d, db, dc, xn, yn, NULL);
    mpz_mul(d, c->u1b, c->u2c); mpz_submul(d, c->u1c, c->u2b);
    mpz_sub(db, b, c->v0b); mpz_sub(dc, cc, c->v0c);
    mpz_mul(xn, db, c->u2c); mpz_submul(xn, dc, c->u2b);
    mpz_mul(yn, dc, c->u1b); mpz_submul(yn, db, c->u1c);
    ok = mpz_divisible_p(xn, d) && mpz_divisible_p(yn, d);
    mpz_clears(d, db, dc, xn, yn, NULL);
    return ok;
}

/*
 * Exact minimum squared norm over the coset (nn) and a minimizing point.
 * Completeness: after co_reduce the basis is Gauss-reduced, so the Voronoi-relevant vectors of the lattice are
 * contained in R = {+-u1, +-u2, +-(u1+u2), +-(u1-u2)} (the obtuse superbase is (u1,u2,-u1-u2) when <u1,u2> <= 0
 * and (u1,-u2,u2-u1) otherwise). A point p of the coset is a global minimizer of |p| iff -p lies in the Voronoi
 * cell iff |p+r| >= |p| for every relevant r; the loop below stops exactly when that holds for all r in R, and
 * strictly decreases the integer |p|^2 until then, so it terminates at a global minimizer.
 */
static void co_nearest(const Co *src, mpz_t nn, mpz_t pb, mpz_t pc) {
    Co c; co_init(&c); co_set(&c, src);
    co_reduce(&c); co_babai(&c);
    mpz_t rb[8], rc[8], cb, cc, cn, t;
    for (int i = 0; i < 8; i++) { mpz_init(rb[i]); mpz_init(rc[i]); }
    mpz_inits(cb, cc, cn, t, NULL);
    mpz_set(rb[0], c.u1b); mpz_set(rc[0], c.u1c);
    mpz_set(rb[1], c.u2b); mpz_set(rc[1], c.u2c);
    mpz_add(rb[2], c.u1b, c.u2b); mpz_add(rc[2], c.u1c, c.u2c);
    mpz_sub(rb[3], c.u1b, c.u2b); mpz_sub(rc[3], c.u1c, c.u2c);
    for (int i = 0; i < 4; i++) { mpz_neg(rb[4 + i], rb[i]); mpz_neg(rc[4 + i], rc[i]); }
    if (g_break_nearest) {
        mpz_add(c.v0b, c.v0b, c.u1b); mpz_add(c.v0c, c.v0c, c.u1c);
        mpz_add(c.v0b, c.v0b, c.u1b); mpz_add(c.v0c, c.v0c, c.u1c);
    }
    dot2(nn, c.v0b, c.v0c, c.v0b, c.v0c);
    if (!g_break_nearest) {
        int improved = 1;
        while (improved) {
            improved = 0;
            for (int i = 0; i < 8; i++) {
                mpz_add(cb, c.v0b, rb[i]); mpz_add(cc, c.v0c, rc[i]);
                dot2(cn, cb, cc, cb, cc);
                if (mpz_cmp(cn, nn) < 0) {
                    mpz_set(c.v0b, cb); mpz_set(c.v0c, cc); mpz_set(nn, cn); improved = 1;
                }
            }
        }
    }
    mpz_set(pb, c.v0b); mpz_set(pc, c.v0c);
    for (int i = 0; i < 8; i++) { mpz_clear(rb[i]); mpz_clear(rc[i]); }
    mpz_clears(cb, cc, cn, t, NULL);
    co_clear(&c);
}

/*
 * port of lattice.Coset.intersect(A,B,r,m): coset of (b,c) in src with A b + B c = r (mod m); returns 0 if empty.
 * dst may alias src.
 */
static int co_intersect(Co *dst, const Co *src, const mpz_t A, const mpz_t B, const mpz_t r, const mpz_t m) {
    mpz_t A2, B2, r2, g1, u, v, C, g2, s, t, f, x0, y0, k1b, k1c, k2b, k2c, tmp;
    mpz_inits(A2, B2, r2, g1, u, v, C, g2, s, t, f, x0, y0, k1b, k1c, k2b, k2c, tmp, NULL);
    Co o; co_init(&o);
    int ok = 1;
    mpz_mul(A2, A, src->u1b); mpz_addmul(A2, B, src->u1c); mpz_fdiv_r(A2, A2, m);
    mpz_mul(B2, A, src->u2b); mpz_addmul(B2, B, src->u2c); mpz_fdiv_r(B2, B2, m);
    mpz_set(r2, r); mpz_submul(r2, A, src->v0b); mpz_submul(r2, B, src->v0c); mpz_fdiv_r(r2, r2, m);
    egcd_py(g1, u, v, A2, B2);
    mpz_neg(C, m);
    egcd_py(g2, s, t, g1, C);
    if (mpz_sgn(g2) == 0) die("intersect: g2 == 0");
    if (!mpz_divisible_p(r2, g2)) { ok = 0; goto done; }
    if (mpz_sgn(g1) == 0) {
        mpz_set_ui(k1b, 1); mpz_set_ui(k1c, 0); mpz_set_ui(k2b, 0); mpz_set_ui(k2c, 1);
    } else {
        mpz_set(k1b, B2); mpz_divexact(k1b, k1b, g1);
        mpz_neg(k1c, A2); mpz_divexact(k1c, k1c, g1);
        mpz_mul(k2b, u, C); mpz_neg(k2b, k2b); mpz_divexact(k2b, k2b, g2);
        mpz_mul(k2c, v, C); mpz_neg(k2c, k2c); mpz_divexact(k2c, k2c, g2);
    }
    mpz_divexact(f, r2, g2);
    mpz_mul(x0, u, s); mpz_mul(x0, x0, f);
    mpz_mul(y0, v, s); mpz_mul(y0, y0, f);
    mpz_set(o.v0b, src->v0b); mpz_addmul(o.v0b, x0, src->u1b); mpz_addmul(o.v0b, y0, src->u2b);
    mpz_set(o.v0c, src->v0c); mpz_addmul(o.v0c, x0, src->u1c); mpz_addmul(o.v0c, y0, src->u2c);
    mpz_mul(o.u1b, k1b, src->u1b); mpz_addmul(o.u1b, k1c, src->u2b);
    mpz_mul(o.u1c, k1b, src->u1c); mpz_addmul(o.u1c, k1c, src->u2c);
    mpz_mul(o.u2b, k2b, src->u1b); mpz_addmul(o.u2b, k2c, src->u2b);
    mpz_mul(o.u2c, k2b, src->u1c); mpz_addmul(o.u2c, k2c, src->u2c);
    co_reduce(&o); co_babai(&o);
    co_set(dst, &o);
done:
    co_clear(&o);
    mpz_clears(A2, B2, r2, g1, u, v, C, g2, s, t, f, x0, y0, k1b, k1c, k2b, k2c, tmp, NULL);
    return ok;
}

static int co_intersect_ui(Co *dst, const Co *src, long A, long B, const mpz_t r, long m) {
    mpz_t a, b, mm; mpz_init_set_si(a, A); mpz_init_set_si(b, B); mpz_init_set_si(mm, m);
    int ok = co_intersect(dst, src, a, b, r, mm);
    mpz_clears(a, b, mm, NULL);
    return ok;
}

/* ---------------------------------------------------------------- p-adic logarithms */

/* sum_{i>=1} (-1)^(i+1) p^(e_i) t^i / i' mod R with e_i = i*sh - v_p(i) - c0 ; p=5: log(1+5t)/5 ; p=2: log(1+4q)/4 */
static void plog5(mpz_t out, const mpz_t w, int kk) {
    /* w = 1 mod 5, known mod 5^kk; out = log(w)/5 mod 5^(kk-1) */
    mpz_t t, R, tp, term, inv, ii;
    mpz_inits(t, R, tp, term, inv, ii, NULL);
    mpz_set(R, P5[kk - 1]);
    mpz_sub_ui(t, w, 1); mpz_divexact_ui(t, t, 5); mpz_fdiv_r(t, t, R);
    mpz_set_ui(out, 0); mpz_set_ui(tp, 1);
    int imax = kk + 12;
    for (int i = 1; i <= imax; i++) {
        mpz_mul(tp, tp, t); mpz_fdiv_r(tp, tp, R);
        int j = 0; unsigned long ip = i; while (ip % 5 == 0) { ip /= 5; j++; }
        int e = i - 1 - j;
        if (e >= kk - 1) continue;
        mpz_mul(term, tp, P5[e]);
        mpz_set_ui(ii, ip);
        if (!mpz_invert(inv, ii, R)) die("plog5 invert");
        mpz_mul(term, term, inv);
        if (i & 1) mpz_add(out, out, term); else mpz_sub(out, out, term);
    }
    mpz_fdiv_r(out, out, R);
    mpz_clears(t, R, tp, term, inv, ii, NULL);
}

static mpz_t inv_lg5[KCAP]; static char inv_lg5_ok[KCAP];
static mpz_t l7c[KCAP]; static char l7c_ok[KCAP];
static mpz_t inv2a[MAXA][KCAP]; static char inv2a_ok[MAXA][KCAP];

/* x in [0, 4*5^(kk-1)) with 3^x = u (mod 5^kk); u coprime to 5. Certified by re-exponentiation. */
static void log3_5(mpz_t x, const mpz_t u, int kk) {
    static const int lg5[5] = {-1, 0, 3, 1, 2};
    unsigned long u5 = mpz_fdiv_ui(u, 5);
    if (u5 == 0) die("log3_5: u divisible by 5");
    int i4 = lg5[u5];
    if (kk == 1) { mpz_set_ui(x, i4); return; }
    mpz_t M, um, U, lu, x5, tmp;
    mpz_inits(M, um, U, lu, x5, tmp, NULL);
    mpz_set(M, P5[kk]);
    mpz_fdiv_r(um, u, M);
    mpz_powm_ui(U, um, 4, M);
    plog5(lu, U, kk);
    if (!inv_lg5_ok[kk]) {
        mpz_set_ui(tmp, 81); plog5(tmp, tmp, kk);
        if (!mpz_invert(inv_lg5[kk], tmp, P5[kk - 1])) die("log81 not a unit");
        inv_lg5_ok[kk] = 1;
    }
    mpz_mul(x5, lu, inv_lg5[kk]); mpz_fdiv_r(x5, x5, P5[kk - 1]);
    long dd = (i4 - (long)mpz_fdiv_ui(x5, 4)) & 3;
    mpz_mul_ui(tmp, P5[kk - 1], dd); mpz_add(x, x5, tmp);
    mpz_set_ui(tmp, 3); mpz_powm(tmp, tmp, x, M);
    if (mpz_cmp(tmp, um) != 0) die("log3_5 certificate failed");
    mpz_clears(M, um, U, lu, x5, tmp, NULL);
}

static void plog2(mpz_t out, const mpz_t w, int k) {
    /* w = 1 mod 4 known mod 2^k; out = log(w)/4 mod 2^(k-2) */
    mpz_t q, R, qp, term, inv, ii;
    mpz_inits(q, R, qp, term, inv, ii, NULL);
    mpz_set(R, P2[k - 2]);
    mpz_sub_ui(q, w, 1); mpz_divexact_ui(q, q, 4); mpz_fdiv_r(q, q, R);
    mpz_set_ui(out, 0); mpz_set_ui(qp, 1);
    int imax = k + 8;
    for (int i = 1; i <= imax; i++) {
        mpz_mul(qp, qp, q); mpz_fdiv_r(qp, qp, R);
        int j = 0; unsigned long ip = i; while ((ip & 1) == 0) { ip >>= 1; j++; }
        int e = 2 * i - 2 - j;
        if (e >= k - 2) continue;
        mpz_mul_2exp(term, qp, e);
        mpz_set_ui(ii, ip);
        if (!mpz_invert(inv, ii, R)) die("plog2 invert");
        mpz_mul(term, term, inv);
        if (i & 1) mpz_add(out, out, term); else mpz_sub(out, out, term);
    }
    mpz_fdiv_r(out, out, R);
    mpz_clears(q, R, qp, term, inv, ii, NULL);
}

static mpz_t inv_l52[KCAP]; static char inv_l52_ok[KCAP];
static mpz_t s3c[KCAP], t3c[KCAP], s7c[KCAP], t7c[KCAP]; static char u37_ok[KCAP];

/* u odd, k>=3: u = (-1)^s 5^t (mod 2^k), t in [0, 2^(k-2)). Certified by re-exponentiation. */
static void log_mod2k(int *s, mpz_t t, const mpz_t u, int k) {
    mpz_t M, w, tmp;
    mpz_inits(M, w, tmp, NULL);
    mpz_set(M, P2[k]);
    mpz_fdiv_r(w, u, M);
    *s = (mpz_fdiv_ui(w, 4) == 1) ? 0 : 1;
    if (*s) { mpz_sub(w, M, w); }
    if (!inv_l52_ok[k]) {
        mpz_set_ui(tmp, 5); plog2(tmp, tmp, k);
        if (!mpz_invert(inv_l52[k], tmp, P2[k - 2])) die("log5 not a unit");
        inv_l52_ok[k] = 1;
    }
    plog2(t, w, k);
    mpz_mul(t, t, inv_l52[k]); mpz_fdiv_r(t, t, P2[k - 2]);
    mpz_set_ui(tmp, 5); mpz_powm(tmp, tmp, t, M);
    if (mpz_cmp(tmp, w) != 0) die("log_mod2k certificate failed");
    mpz_clears(M, w, tmp, NULL);
}

static void ensure_u37(int k) {
    if (u37_ok[k]) return;
    mpz_t u; int s;
    mpz_init(u);
    mpz_set_ui(u, 3); log_mod2k(&s, t3c[k], u, k); mpz_set_ui(s3c[k], s);
    mpz_set_ui(u, 7); log_mod2k(&s, t7c[k], u, k); mpz_set_ui(s7c[k], s);
    mpz_clear(u);
    u37_ok[k] = 1;
}

static void ensure_l7(int K) {
    if (l7c_ok[K]) return;
    mpz_t seven; mpz_init_set_ui(seven, 7);
    log3_5(l7c[K], seven, K);
    mpz_clear(seven);
    l7c_ok[K] = 1;
}

static mpz_t *get_inv2a(int a, int kk) {
    if (a >= MAXA) die("a too large");
    if (!inv2a_ok[a][kk]) {
        mpz_t t; mpz_init(t);
        mpz_powm_ui(t, P2[1], a, P5[kk]);
        if (!mpz_invert(inv2a[a][kk], t, P5[kk])) die("inv 2^a");
        mpz_clear(t);
        inv2a_ok[a][kk] = 1;
    }
    return &inv2a[a][kk];
}

static void init_caches(void) {
    for (int i = 0; i < KCAP; i++) {
        mpz_init(inv_lg5[i]); mpz_init(l7c[i]); mpz_init(inv_l52[i]);
        mpz_init(s3c[i]); mpz_init(t3c[i]); mpz_init(s7c[i]); mpz_init(t7c[i]);
        for (int a = 0; a < MAXA; a++) mpz_init(inv2a[a][i]);
    }
}

/*
 * port of descent.cut_coset(co, a, Yp, Kp) for Yp=L, Kp=K>=96, with v2(L)==a already established.
 * Returns 0 when the cut is empty. Eager (full-precision) form.
 */
static int cut_full(Co *dst, const Co *co, int a, const mpz_t L, int K) {
    if (K <= a || K - a < 3) die("cut_full: K too small");
    if (mpz_fdiv_ui(L, 5) == 0) die("cut_full: 5 divides L");
    mpz_t Z5, lZ, N, A, B, one, tZ, sZ, Z2, half, two;
    mpz_inits(Z5, lZ, N, A, B, one, tZ, sZ, Z2, half, two, NULL);
    int ok = 1; Co c1; co_init(&c1);
    mpz_fdiv_r(Z5, L, P5[K]); mpz_mul(Z5, Z5, *get_inv2a(a, K)); mpz_fdiv_r(Z5, Z5, P5[K]);
    log3_5(lZ, Z5, K);
    if (g_break_lz5) mpz_add_ui(lZ, lZ, 1);
    ensure_l7(K);
    mpz_mul_ui(N, P5[K - 1], 4);
    mpz_set_ui(one, 1);
    if (!co_intersect(&c1, co, one, l7c[K], lZ, N)) { ok = 0; goto done; }
    {
        int k2 = K - a, sz; mpz_t u;
        mpz_init(u);
        mpz_fdiv_r(Z2, L, P2[K]); mpz_fdiv_q_2exp(Z2, Z2, a); mpz_fdiv_r(Z2, Z2, P2[k2]);
        log_mod2k(&sz, tZ, Z2, k2);
        if (g_break_t2) mpz_add_ui(tZ, tZ, 1);
        ensure_u37(k2);
        mpz_set_ui(sZ, sz); mpz_set_ui(two, 2);
        if (!co_intersect(&c1, &c1, s3c[k2], s7c[k2], sZ, two)) { ok = 0; mpz_clear(u); goto done; }
        mpz_set(half, P2[k2 - 2]);
        if (!co_intersect(&c1, &c1, t3c[k2], t7c[k2], tZ, half)) { ok = 0; mpz_clear(u); goto done; }
        mpz_clear(u);
    }
    co_set(dst, &c1);
done:
    co_clear(&c1);
    mpz_clears(Z5, lZ, N, A, B, one, tZ, sZ, Z2, half, two, NULL);
    return ok;
}

/* lazy 5-adic prefilter data for one (coset, K): the cut is empty iff (lZ + offs) is not divisible by g */
typedef struct { mpz_t g, offs; int y5; } Pre5;
static void pre5_init(Pre5 *p) { mpz_init(p->g); mpz_init(p->offs); }
static void pre5_clear(Pre5 *p) { mpz_clear(p->g); mpz_clear(p->offs); }
static void pre5_make(Pre5 *p, const Co *co, int K) {
    mpz_t N, A2, B2, one;
    mpz_inits(N, A2, B2, one, NULL);
    ensure_l7(K);
    mpz_mul_ui(N, P5[K - 1], 4);
    mpz_mul(A2, l7c[K], co->u1c); mpz_add(A2, A2, co->u1b); mpz_fdiv_r(A2, A2, N);
    mpz_mul(B2, l7c[K], co->u2c); mpz_add(B2, B2, co->u2b); mpz_fdiv_r(B2, B2, N);
    mpz_gcd(p->g, A2, B2); mpz_gcd(p->g, p->g, N);
    mpz_t tmp; mpz_init(tmp);
    p->y5 = (int)mpz_remove(tmp, p->g, (mpz_srcptr)P5[1]);
    mpz_clear(tmp);
    mpz_mul(p->offs, l7c[K], co->v0c); mpz_add(p->offs, p->offs, co->v0b); mpz_neg(p->offs, p->offs);
    mpz_clears(N, A2, B2, one, NULL);
}
static int pre5_alive(const Pre5 *p, int a, const mpz_t L) {
    int kk = p->y5 + 1;
    mpz_t Zs, lz;
    mpz_inits(Zs, lz, NULL);
    mpz_fdiv_r(Zs, L, P5[kk]); mpz_mul(Zs, Zs, *get_inv2a(a, kk)); mpz_fdiv_r(Zs, Zs, P5[kk]);
    log3_5(lz, Zs, kk);
    if (g_break_lz5) mpz_add_ui(lz, lz, 1);
    mpz_add(lz, lz, p->offs);
    int r = mpz_divisible_p(lz, p->g) != 0;
    mpz_clears(Zs, lz, NULL);
    return r;
}

/* ---------------------------------------------------------------- lattice (Lambda_96) */
static Co g_lam;
static mpz_t g_lam_index;

static void load_lattice(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open lattice file");
    char *line = NULL; size_t cap = 0;
    mpz_t Rm, p, g, l3, l7, pm1, q, tmp, prod, e1, zero, m, one;
    mpz_inits(Rm, p, g, l3, l7, pm1, q, tmp, prod, e1, zero, m, one, NULL);
    mpz_ui_pow_ui(Rm, 10, LMAX); mpz_sub_ui(Rm, Rm, 1);
    co_init(&g_lam); mpz_set_ui(g_lam.u1b, 1); mpz_set_ui(g_lam.u2c, 1);
    mpz_init(g_lam_index);
    int nprimes = 0;
    mpz_t rest; mpz_init_set(rest, Rm);
    while (getline(&line, &cap, f) > 0) {
        if (line[0] == '#' || line[0] == '\n') continue;
        char sp[256], sg[256], s3[256], s7[256]; int nf, off = 0, n;
        if (sscanf(line, "%255s %255s %255s %255s %d%n", sp, sg, s3, s7, &nf, &n) != 5) die("bad lattice line");
        off = n;
        mpz_set_str(p, sp, 10); mpz_set_str(g, sg, 10); mpz_set_str(l3, s3, 10); mpz_set_str(l7, s7, 10);
        if (!mpz_divisible_p(Rm, p)) die("lattice prime does not divide 10^96-1");
        if (!mpz_probab_prime_p(p, 40)) die("lattice prime not prime");
        mpz_sub_ui(pm1, p, 1);
        mpz_set_ui(prod, 1);
        for (int i = 0; i < nf; i++) {
            char sq[256]; int e;
            if (sscanf(line + off, "%255s %d%n", sq, &e, &n) != 2) die("bad factor list");
            off += n;
            mpz_set_str(q, sq, 10);
            if (!mpz_probab_prime_p(q, 40)) die("p-1 factor not prime");
            mpz_pow_ui(tmp, q, e); mpz_mul(prod, prod, tmp);
            mpz_divexact(e1, pm1, q);
            mpz_powm(tmp, g, e1, p);
            if (mpz_cmp_ui(tmp, 1) == 0) die("g is not a primitive root");
        }
        if (mpz_cmp(prod, pm1) != 0) die("factorization of p-1 does not multiply out");
        if (mpz_sgn(l3) < 0 || mpz_cmp(l3, pm1) >= 0 || mpz_sgn(l7) < 0 || mpz_cmp(l7, pm1) >= 0) die("log out of range");
        mpz_powm(tmp, g, l3, p); if (mpz_cmp_ui(tmp, 3) != 0 && mpz_cmp_ui(p, 3) > 0) die("g^l3 != 3");
        mpz_powm(tmp, g, l7, p); { mpz_t seven; mpz_init_set_ui(seven, 7); mpz_mod(seven, seven, p);
            if (mpz_cmp(tmp, seven) != 0) die("g^l7 != 7"); mpz_clear(seven); }
        while (mpz_divisible_p(rest, p)) mpz_divexact(rest, rest, p);
        mpz_set_ui(zero, 0);
        if (!co_intersect(&g_lam, &g_lam, l3, l7, zero, pm1)) die("lattice intersection empty");
        nprimes++;
    }
    for (int sm = 3; sm <= 7; sm += 4) while (mpz_divisible_ui_p(rest, sm)) mpz_divexact_ui(rest, rest, sm);
    if (mpz_cmp_ui(rest, 1) != 0) die("prime list incomplete: 10^96-1 has other prime factors");
    co_index(g_lam_index, &g_lam);
    fclose(f); free(line);
    mpz_clears(Rm, p, g, l3, l7, pm1, q, tmp, prod, e1, zero, m, one, rest, NULL);
    fprintf(stderr, "lattice: %d primes, index %s\n", nprimes, mpz_get_str(NULL, 10, g_lam_index));
}

/* ---------------------------------------------------------------- display helpers (floats for display only) */
static double mpz_log10d(const mpz_t x) {
    long ex; double m = mpz_get_d_2exp(&ex, x);
    return log10(m) + ex * 0.30102999566398119521;
}
static double digits_bound_log10(const mpz_t nn) {
    if (mpz_sgn(nn) == 0) return -1.0;
    return 0.5 * mpz_log10d(nn) - 0.5 * log10(2.0) + log10(log10(3.0));
}
static void fmt_round2(char *buf, double v) {
    snprintf(buf, 64, "%.2f", v);
    int n = (int)strlen(buf);
    while (n > 1 && buf[n - 1] == '0' && buf[n - 2] != '.') { buf[--n] = 0; }
}

/* ---------------------------------------------------------------- representations */
typedef struct { int nu; int n; int d[MAXIT]; int e[MAXIT]; } Rep;
typedef struct { Rep *v; int n, cap; } RepList;
static void rl_push(RepList *l, const Rep *r) {
    if (l->n == l->cap) { l->cap = l->cap ? 2 * l->cap : 16; l->v = realloc(l->v, l->cap * sizeof(Rep)); }
    l->v[l->n++] = *r;
}

typedef struct { RepList *out; int nu; Rep cur; int emax; } EnumCtx;

/*
 * Sub-multiset table per remaining multiset (count vector over digits 0..9), in the order deepcut.all_representations
 * visits them: size ascending, index-combinations lexicographic over the sorted list, first occurrence of each distinct
 * digit tuple. Bucketed by (sum of d-1) mod 10.
 */
typedef struct { int tot; int nd; signed char dig[KMAXC]; uint64_t rest; } Sub;
typedef struct { uint64_t key; int used; int cnt[10]; int n[10], cap[10]; Sub *b[10]; } MsEnt;
#define MSTAB 262144
static MsEnt g_ms[MSTAB];
static int g_ms_used;

static uint64_t cnt_key(const int *cnt) { uint64_t k = 0; for (int d = 0; d < 10; d++) k |= (uint64_t)cnt[d] << (5 * d); return k; }

static MsEnt *ms_get(const int *cnt) {
    uint64_t key = cnt_key(cnt);
    unsigned h = (unsigned)((key * 0x9E3779B97F4A7C15ULL) >> 40) & (MSTAB - 1);
    while (g_ms[h].used) { if (g_ms[h].key == key) return &g_ms[h]; h = (h + 1) & (MSTAB - 1); }
    if (++g_ms_used > MSTAB / 2) die("multiset table overloaded");
    MsEnt *m = &g_ms[h]; m->used = 1; m->key = key; memcpy(m->cnt, cnt, 10 * sizeof(int));
    int ms[KMAXC], nms = 0;
    for (int d = 0; d < 10; d++) for (int c = 0; c < cnt[d]; c++) ms[nms++] = d;
    static uint64_t tried[1 << 16]; int ntried = 0, idx[KMAXC];
    for (int kk = 0; kk <= nms; kk++) {
        for (int i = 0; i < kk; i++) idx[i] = i;
        for (;;) {
            uint64_t k2 = 0; int tot = 0;
            for (int i = 0; i < kk; i++) { k2 += 1ULL << (5 * ms[idx[i]]); tot += ms[idx[i]] - 1; }
            int dup = 0;
            for (int i = 0; i < ntried; i++) if (tried[i] == k2) { dup = 1; break; }
            if (!dup) {
                if (ntried >= (1 << 16)) die("sub-multiset table overflow");
                tried[ntried++] = k2;
                int r = ((tot % 10) + 10) % 10;
                if (m->n[r] == m->cap[r]) { m->cap[r] = m->cap[r] ? 2 * m->cap[r] : 8; m->b[r] = realloc(m->b[r], m->cap[r] * sizeof(Sub)); }
                Sub *sb = &m->b[r][m->n[r]++];
                sb->tot = tot; sb->nd = kk;
                for (int i = 0; i < kk; i++) sb->dig[i] = (signed char)ms[idx[i]];
                int rc[10]; memcpy(rc, cnt, sizeof rc);
                for (int i = 0; i < kk; i++) rc[ms[idx[i]]]--;
                sb->rest = cnt_key(rc);
            }
            int i = kk - 1;
            while (i >= 0 && idx[i] == nms - kk + i) i--;
            if (i < 0) break;
            idx[i]++;
            for (int j2 = i + 1; j2 < kk; j2++) idx[j2] = idx[j2 - 1] + 1;
        }
    }
    return m;
}

static mpz_t g_qpool[LMAX + 4]; static int g_qpool_ok;
static void enum_rec(EnumCtx *cx, int e, const int *cnt, int nms, mpz_t q) {
    /* q = floor(rem / 10^e); rem is divisible by 10^e at every call (digits below e are matched) */
    if (nms == 0) {
        if (mpz_sgn(q) == 0) { cx->cur.nu = cx->nu; rl_push(cx->out, &cx->cur); }
        return;
    }
    if (e > cx->emax || e >= LMAX || mpz_sgn(q) < 0) return;
    if (mpz_sgn(q) == 0) return;
    if (mpz_sizeinbase(q, 10) > (size_t)(LMAX - 1 - e) + 4) return;
    { unsigned long sumrem = 0; for (int d = 2; d < 10; d++) sumrem += (unsigned long)cnt[d] * (d - 1); if (mpz_cmp_ui(q, sumrem) < 0) return; if (mpz_fdiv_ui(q, 9) != sumrem % 9) return; }
    MsEnt *m = ms_get(cnt);
    int need = (int)mpz_fdiv_ui(q, 10);
    int base_n = cx->cur.n;
    for (int bi = 0; bi < m->n[need]; bi++) {
        Sub *sb = &m->b[need][bi];
        mpz_ptr q2 = g_qpool[e + 1];
        mpz_sub_ui(q2, q, sb->tot);
        if (mpz_sgn(q2) >= 0 || 1) {
            mpz_divexact_ui(q2, q2, 10);
            int rc[10];
            for (int d = 0; d < 10; d++) rc[d] = (int)((sb->rest >> (5 * d)) & 31);
            for (int i = 0; i < sb->nd; i++) { cx->cur.d[cx->cur.n] = sb->dig[i]; cx->cur.e[cx->cur.n] = e; cx->cur.n++; }
            enum_rec(cx, e + 1, rc, nms - sb->nd, q2);
            cx->cur.n = base_n;
        }
    }
}

static void all_representations(RepList *out, const int *M, int k, const mpz_t y) {
    int ms[KMAXC]; memcpy(ms, M, k * sizeof(int));
    for (int i = 1; i < k; i++) { int v = ms[i], j = i - 1; while (j >= 0 && ms[j] > v) { ms[j + 1] = ms[j]; j--; } ms[j + 1] = v; }
    mpz_t RL, target, rn;
    mpz_inits(RL, target, rn, NULL);
    if (!g_qpool_ok) { for (int i = 0; i < LMAX + 4; i++) mpz_init(g_qpool[i]); g_qpool_ok = 1; }
    mpz_sub_ui(RL, P10[LMAX], 1); mpz_divexact_ui(RL, RL, 9);
    int cnt0[10] = {0}; for (int i2 = 0; i2 < k; i2++) cnt0[ms[i2]]++;
    MsEnt *root = ms_get(cnt0);
    unsigned long sum9 = 0; for (int d = 2; d < 10; d++) sum9 += (unsigned long)cnt0[d] * (d - 1); sum9 %= 9;
    for (int kq = 0; kq < 8 * k + 2; kq++) {
        mpz_mul_ui(target, RL, kq); mpz_add(target, target, y);
        for (int nu = 0; nu < LMAX; nu++) {
            if (nu > 0) mpz_sub(target, target, P10[nu - 1]);
            if (mpz_sgn(target) < 0) continue;
            if (k > 0 && root->n[mpz_fdiv_ui(target, 10)] == 0) continue;
            if (mpz_fdiv_ui(target, 9) != sum9) continue;
            size_t sz = mpz_sizeinbase(target, 10);
            if (sz > 1 && mpz_cmp(target, P10[sz - 1]) < 0) sz--;
            EnumCtx cx; memset(&cx, 0, sizeof cx);
            cx.out = out; cx.nu = nu; cx.emax = (int)sz;
            enum_rec(&cx, 0, cnt0, k, target);
        }
    }
    mpz_clears(RL, target, rn, NULL);
}

/* ---------------------------------------------------------------- deep cut */
typedef struct { Co co; signed char t[MAXIT]; } Surv;
typedef struct {
    Rep rep; Surv *sv; int nsv, capsv;
    int D; long cases; int closed; int budget; long stats[16];
    int stage_done;
} DC;

static void dc_push(DC *s, const Co *co, const signed char *t, int n) {
    if (s->nsv == s->capsv) { s->capsv = s->capsv ? 2 * s->capsv : 64; s->sv = realloc(s->sv, s->capsv * sizeof(Surv)); }
    Surv *x = &s->sv[s->nsv++];
    co_init(&x->co); co_set(&x->co, co);
    memcpy(x->t, t, n);
}
static void dc_free_surv(DC *s) {
    for (int i = 0; i < s->nsv; i++) co_clear(&s->sv[i].co);
    s->nsv = 0;
}

static long g_total_cases_eager_mismatch = 0;

static int g_dedup = 0;
static int cmp_u32(const void *x, const void *y) {
    unsigned a = *(const unsigned *)x, b = *(const unsigned *)y;
    return a < b ? -1 : a > b;
}
static unsigned *dedup_masks(const DC *s, const int *fr, int nf, unsigned long long *cnt) {
    int ge[32], gc[32], gn = 0, gm[32][32];
    for (int q = 0; q < nf; q++) {
        int dom = 0;
        for (int r = 0; r < q; r++) if (s->rep.d[fr[r]] == s->rep.d[fr[q]] && s->rep.e[fr[r]] == s->rep.e[fr[q]]) dom = 1;
        if (dom) continue;
        int g = -1;
        for (int x = 0; x < gn; x++) if (ge[x] == s->rep.e[fr[q]]) g = x;
        if (g < 0) { g = gn++; ge[g] = s->rep.e[fr[q]]; gc[g] = 0; }
        gm[g][gc[g]++] = q;
    }
    unsigned long long total = 1;
    for (int g = 0; g < gn; g++) total *= (unsigned long long)(1 + gc[g]);
    unsigned *out = malloc(total * sizeof(unsigned));
    int idx[32]; for (int g = 0; g < gn; g++) idx[g] = 0;
    for (unsigned long long n = 0; n < total; n++) {
        unsigned m = 0;
        for (int g = 0; g < gn; g++) if (idx[g]) m |= 1u << gm[g][idx[g] - 1];
        out[n] = m;
        for (int g = 0; g < gn; g++) { if (++idx[g] <= gc[g]) break; idx[g] = 0; }
    }
    qsort(out, total, sizeof(unsigned), cmp_u32);
    *cnt = total;
    return out;
}


static long g_y5hist[16];
static uint32_t *g_dl5[10];
static uint32_t *dl5_table(int kk) {
    if (g_dl5[kk]) return g_dl5[kk];
    unsigned long M = mpz_get_ui(P5[kk]), N = 4 * (M / 5);
    uint32_t *t = malloc(M * sizeof(uint32_t));
    for (unsigned long i = 0; i < M; i++) t[i] = 0xffffffffu;
    unsigned long x = 1;
    for (unsigned long i = 0; i < N; i++) { t[x] = (uint32_t)i; x = x * 3 % M; }
    if (x != 1) die("dl5 table: 3 is not a primitive root of 5^k");
    g_dl5[kk] = t;
    return t;
}
static uint64_t lo64(const mpz_t x) {
    mpz_t t; mpz_init(t); mpz_fdiv_r_2exp(t, x, 64);
    uint64_t v = mpz_getlimbn(t, 0);
    mpz_clear(t);
    return v;
}

/* advance one stage: D-1 -> D. Returns 1 if the pattern is still alive afterwards. */
static void dc_stage(DC *s, int a, long maxcases) {
    int D = ++s->D, K = LMAX * D, n = s->rep.n;
    Surv *old = s->sv; int nold = s->nsv;
    s->sv = NULL; s->nsv = 0; s->capsv = 0;
    mpz_t RK, Lbase, L, tmp;
    mpz_inits(RK, Lbase, L, tmp, NULL);
    mpz_sub_ui(RK, P10[K], 1); mpz_divexact_ui(RK, RK, 9);
    ensure_l7(K);
    for (int si = 0; si < nold && !s->budget; si++) {
        Surv *sv = &old[si];
        signed char fixt[MAXIT]; int fixed[MAXIT];
        for (int i = 0; i < n; i++) { fixed[i] = 0; fixt[i] = -1; }
        for (int i = 0; i < n; i++) if (sv->t[i] >= 0) { fixed[i] = 1; fixt[i] = sv->t[i]; }
        mpz_set(Lbase, RK);
        for (int i = 0; i < n; i++) {
            if (!fixed[i]) continue;
            mpz_set_si(tmp, s->rep.d[i] - 1); mpz_mul(tmp, tmp, P10[s->rep.e[i] + LMAX * fixt[i]]);
            mpz_add(Lbase, Lbase, tmp);
        }
        int fr[MAXIT], nf = 0;
        for (int i = 0; i < n; i++) if (!fixed[i]) fr[nf++] = i;
        static mpz_t term[32]; static unsigned conf[32];
        static int term_init = 0; if (!term_init) { for (int q = 0; q < 32; q++) mpz_init(term[q]); term_init = 1; }
        if (nf > 31) { s->budget = 1; break; }
        for (int q = 0; q < nf; q++) {
            mpz_set_si(term[q], s->rep.d[fr[q]] - 1); mpz_mul(term[q], term[q], P10[s->rep.e[fr[q]] + LMAX * (D - 1)]);
            conf[q] = 0;
            for (int r = 0; r < nf; r++) if (r != q && s->rep.e[fr[r]] == s->rep.e[fr[q]]) conf[q] |= 1u << r;
        }
        Pre5 pre; pre5_init(&pre); pre5_make(&pre, &sv->co, K);
        g_y5hist[pre.y5 < 15 ? pre.y5 : 15]++;
        int fast = (pre.y5 + 1 <= 8) && a < 64 && !g_break_v2;
        unsigned long M5 = 0, gul = 0, offul = 0, invul = 0, b5 = 0, t5[32]; uint64_t b2 = 0, t2l[32]; uint32_t *tab = NULL;
        if (fast) {
            int kk = pre.y5 + 1;
            M5 = mpz_get_ui(P5[kk]); gul = mpz_get_ui(pre.g);
            { mpz_t tt; mpz_init(tt); mpz_fdiv_r(tt, pre.offs, pre.g); offul = mpz_get_ui(tt); mpz_clear(tt); }
            invul = mpz_get_ui(*get_inv2a(a, kk));
            tab = dl5_table(kk);
            b5 = mpz_fdiv_ui(Lbase, M5); b2 = lo64(Lbase);
            for (int q = 0; q < nf; q++) { t5[q] = mpz_fdiv_ui(term[q], M5); t2l[q] = lo64(term[q]); }
        }
        unsigned *mlist = NULL; unsigned long long nmask = 1ULL << nf;
        if (g_dedup) mlist = dedup_masks(s, fr, nf, &nmask);
        for (unsigned long long mi = 0; mi < nmask; mi++) {
            unsigned mask = mlist ? mlist[mi] : (unsigned)mi;
            int okm = 1;
            for (int q = 0; q < nf; q++) if ((mask >> q & 1) && (conf[q] & mask)) { okm = 0; break; }
            if (!okm) continue;
            s->cases++;
            if (s->cases > maxcases) { s->budget = 1; break; }
            if (fast && !g_eager) {
                unsigned long s5 = b5; uint64_t s2 = b2;
                for (unsigned mm = mask; mm; mm &= mm - 1) { int q = __builtin_ctz(mm); s5 += t5[q]; s2 += t2l[q]; }
                s5 %= M5;
                if (s2 == 0 || __builtin_ctzll(s2) != a) continue;
                if (s5 % 5 == 0) { g_n5L++; continue; }
                unsigned long zs = (unsigned long)(((unsigned __int128)s5 * invul) % M5);
                unsigned long lz = tab[zs] + (g_break_lz5 ? 1 : 0);
                if ((lz + offul) % gul != 0) continue;
            }
            mpz_set(L, Lbase);
            for (int q = 0; q < nf; q++) if (mask >> q & 1) mpz_add(L, L, term[q]);
            if (!g_break_v2 && (long)mpz_scan1(L, 0) != a) continue;
            if (mpz_fdiv_ui(L, 5) == 0) { g_n5L++; continue; }
            int alive_lazy = pre5_alive(&pre, a, L);
            if (!alive_lazy && !g_eager) continue;
            Co c2; co_init(&c2);
            int ok = cut_full(&c2, &sv->co, a, L, K);
            if (g_eager && ok != alive_lazy && !(alive_lazy && !ok)) {
                /* lazy said dead but eager survives: soundness of the prefilter violated */
                if (!alive_lazy && ok) { g_total_cases_eager_mismatch++; }
            }
            if (ok) {
                signed char t2[MAXIT]; memcpy(t2, sv->t, MAXIT);
                for (int q = 0; q < nf; q++) if (mask >> q & 1) t2[fr[q]] = (signed char)(D - 1);
                dc_push(s, &c2, t2, MAXIT);
            }
            co_clear(&c2);
        }
        free(mlist);
        pre5_clear(&pre);
    }
    for (int i = 0; i < nold; i++) co_clear(&old[i].co);
    free(old);
    mpz_clears(RK, Lbase, L, tmp, NULL);
    if (!s->budget) {
        s->stats[D - 1] = s->nsv;
        if (s->nsv == 0) s->closed = 1;
    }
}

static void dc_init(DC *s, const Rep *rep, const Co *co0) {
    memset(s, 0, sizeof *s);
    s->rep = *rep;
    signed char t[MAXIT]; memset(t, -1, MAXIT);
    dc_push(s, co0, t, MAXIT);
}
static void dc_free(DC *s) { dc_free_surv(s); free(s->sv); s->sv = NULL; }

/* min squared nearest-point norm over the survivors */
static void dc_min_nn(const DC *s, mpz_t out) {
    mpz_t nn, pb, pc; mpz_inits(nn, pb, pc, NULL);
    int first = 1;
    for (int i = 0; i < s->nsv; i++) {
        co_nearest(&s->sv[i].co, nn, pb, pc);
        if (first || mpz_cmp(nn, out) < 0) { mpz_set(out, nn); first = 0; }
    }
    mpz_clears(nn, pb, pc, NULL);
}

/* ---------------------------------------------------------------- input parsing */
typedef struct {
    char s[64], Mstr[32]; int a; mpz_t y; int M[KMAXC]; int k; int has_nu; int nu; int eps[KMAXC]; int neps;
    char fullkey[2700];
} Case;

static int read_case(FILE *f, Case *c) {
    char line[4096];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '\n' || line[0] == '#') continue;
        char ys[512], nus[64], eps[2048];
        if (sscanf(line, "%63s %31s %d %511s %63s %2047s", c->s, c->Mstr, &c->a, ys, nus, eps) != 6) die("bad case line");
        mpz_init_set_str(c->y, ys, 10);
        c->k = (int)strlen(c->Mstr);
        if (c->k > KMAXC) die("pattern with more than 24 non-1 digits is unsupported");
        snprintf(c->fullkey, sizeof c->fullkey, "%s %s %d %s %s %s", c->s, c->Mstr, c->a, ys, nus, eps);
        for (int i = 0; i < c->k; i++) c->M[i] = c->Mstr[i] - '0';
        if (strcmp(nus, "-") == 0) { c->has_nu = 0; c->neps = 0; }
        else {
            c->has_nu = 1; c->nu = atoi(nus); c->neps = 0;
            char *p = eps, *tok;
            while ((tok = strsep(&p, ",")) != NULL) if (*tok) {
                if (c->neps >= KMAXC) die("recorded pattern with more than 24 positions is unsupported");
                c->eps[c->neps++] = atoi(tok);
            }
        }
        return 1;
    }
    return 0;
}

typedef struct { char (*k)[600]; int n; } KeySet;
static KeySet load_keys(const char *path) {
    KeySet ks = {0, 0};
    if (!path) return ks;
    FILE *f = fopen(path, "r"); if (!f) die("cannot open --only file");
    char line[1024]; int cap = 0;
    while (fgets(line, sizeof line, f)) {
        char s[64], M[32], a[16], y[512];
        if (sscanf(line, "%63s %31s %15s %511s", s, M, a, y) != 4) continue;
        if (ks.n == cap) { cap = cap ? 2 * cap : 128; ks.k = realloc(ks.k, cap * sizeof *ks.k); }
        snprintf(ks.k[ks.n++], 600, "%s %s %s %s", s, M, a, y);
    }
    fclose(f);
    return ks;
}
static char **g_seen; static int g_nseen, g_capseen;
static int seen_before(const char *key) {
    for (int i = 0; i < g_nseen; i++) if (strcmp(g_seen[i], key) == 0) return 1;
    if (g_nseen == g_capseen) { g_capseen = g_capseen ? 2 * g_capseen : 256; g_seen = realloc(g_seen, g_capseen * sizeof *g_seen); }
    g_seen[g_nseen++] = strdup(key);
    return 0;
}
static int key_wanted(const KeySet *ks, const char *s, const char *M, int a, const mpz_t y) {
    char *ys = mpz_get_str(NULL, 10, y); char key[600];
    snprintf(key, sizeof key, "%s %s %d %s", s, M, a, ys); free(ys);
    for (int i = 0; i < ks->n; i++) if (strcmp(ks->k[i], key) == 0) return 1;
    return 0;
}

/* representations after the nu/eps filter of deepcut.py / sandwich.py */
static void filtered_reps(RepList *out, const Case *c) {
    RepList all = {0, 0, 0};
    all_representations(&all, c->M, c->k, c->y);
    if (all.n == 0) { fprintf(stderr, "FATAL: no representation of the anchor: %s\n", c->fullkey); exit(3); }
    if (c->has_nu) {
        for (int i = 0; i < all.n; i++) {
            const Rep *r = &all.v[i];
            if (r->nu != c->nu || r->n != c->neps) continue;
            int cnt[LMAX] = {0}, cnt2[LMAX] = {0};
            for (int j = 0; j < r->n; j++) cnt[r->e[j]]++;
            for (int j = 0; j < c->neps; j++) cnt2[c->eps[j] % LMAX]++;
            if (memcmp(cnt, cnt2, sizeof cnt) == 0) rl_push(out, r);
        }
    }
    else for (int i = 0; i < all.n; i++) rl_push(out, &all.v[i]);
    if (out->n == 0) { fprintf(stderr, "FATAL: recorded pattern not among the representations: %s\n", c->fullkey); exit(3); }
    free(all.v);
}

static int factor237(const mpz_t y, int *a, int *b, int *c) {
    mpz_t t; mpz_init_set(t, y);
    int e[3] = {0, 0, 0}; unsigned p[3] = {2, 3, 7};
    for (int i = 0; i < 3; i++) while (mpz_divisible_ui_p(t, p[i])) { mpz_divexact_ui(t, t, p[i]); e[i]++; }
    int one = mpz_cmp_ui(t, 1) == 0; mpz_clear(t);
    *a = e[0]; *b = e[1]; *c = e[2];
    return one;
}

static int dup_keys(const Rep *r) {
    for (int i = 0; i < r->n; i++) for (int j = i + 1; j < r->n; j++)
        if (r->d[i] == r->d[j] && r->e[i] == r->e[j]) return 1;
    return 0;
}

/* ---------------------------------------------------------------- deepcut driver */
static int cmd_deepcut(int argc, char **argv) {
    const char *lat = NULL, *cases = NULL, *only = NULL, *tsv = NULL;
    int depth = 2; long maxcases = 200000;
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--lattice")) lat = argv[++i];
        else if (!strcmp(argv[i], "--cases")) cases = argv[++i];
        else if (!strcmp(argv[i], "--only")) only = argv[++i];
        else if (!strcmp(argv[i], "--tsv")) tsv = argv[++i];
        else if (!strcmp(argv[i], "--depth")) depth = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--maxcases")) maxcases = atol(argv[++i]);
    }
    if (!lat || !cases) die("deepcut needs --lattice and --cases");
    double t0 = cpu_s();
    load_lattice(lat);
    KeySet ks = load_keys(only);
    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");
    FILE *ft = tsv ? fopen(tsv, "w") : NULL;
    printf("Lambda_96: index %.3e [%.2fs]\n", mpz_get_d(g_lam_index), cpu_s() - t0);
    long npat = 0, nrep = 0, nclosed = 0, ndup = 0; double minw = 1e300, trep_tot = 0;
    Case c;
    while (read_case(f, &c)) {
        if (only && !key_wanted(&ks, c.s, c.Mstr, c.a, c.y)) { mpz_clear(c.y); continue; }
        if (seen_before(c.fullkey)) { mpz_clear(c.y); continue; }
        int a, b, cc;
        if (!factor237(c.y, &a, &b, &cc) || a != c.a) die("anchor is not 2^a 3^b 7^c with the recorded a");
        Co co0; co_init(&co0); co_set(&co0, &g_lam);
        mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, cc);
        co_babai(&co0);
        double tp = cpu_s();
        RepList reps = {0, 0, 0};
        filtered_reps(&reps, &c);
        double t_rep = cpu_s() - tp;
        int closed_all = 1, budget = 0; int have_worst = 0; double worst = 0; long tcase = 0;
        mpz_t worst_nn; mpz_init(worst_nn);
        for (int ri = 0; ri < reps.n; ri++) {
            nrep++;
            if (dup_keys(&reps.v[ri])) ndup++;
            DC s; dc_init(&s, &reps.v[ri], &co0);
            double tr = cpu_s();
            for (int D = 1; D <= depth && !s.closed && !s.budget; D++) dc_stage(&s, c.a, maxcases);
            tcase += s.cases;
            mpz_t nn; mpz_init(nn);
            if (s.budget) {
                closed_all = 0; budget = 1;
                if (ft) fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t-1\t%ld\t-\t%.9f\n", c.fullkey, c.s, c.Mstr, c.a, mpz_get_str(NULL, 10, c.y), ri, s.cases, cpu_s() - tr);
                mpz_clear(nn); dc_free(&s); break;
            }
            if (!s.closed) {
                closed_all = 0;
                dc_min_nn(&s, nn);
                double w = digits_bound_log10(nn);
                if (!have_worst || mpz_cmp(nn, worst_nn) < 0) { worst = w; mpz_set(worst_nn, nn); have_worst = 1; }
            }
            double dt = cpu_s() - tr;
            if (ft) {
                char *nns = s.closed ? strdup("-") : mpz_get_str(NULL, 10, nn);
                fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t%d\t%ld\t%s\t%.9f\n", c.fullkey, c.s, c.Mstr, c.a, mpz_get_str(NULL, 10, c.y), ri, s.closed, s.cases, nns, dt);
                free(nns);
            }
            mpz_clear(nn);
            dc_free(&s);
        }
        npat++; nclosed += closed_all;
        char ys[600]; char *y10 = mpz_get_str(NULL, 10, c.y); snprintf(ys, sizeof ys, "%s", y10); free(y10);
        printf("s=%-10s M=%-12s a=%-2d y=%-12s reps=%-3d cases=%-7ld ", c.s, c.Mstr, c.a, ys, reps.n, tcase);
        if (closed_all) printf("CLOSED\n");
        else if (budget) printf("BUDGET\n");
        else {
            printf("bound 10^(10^%.2f) digits\n", worst);
            if (worst < minw) minw = worst;
        }
        fflush(stdout);
        mpz_clear(worst_nn); free(reps.v); co_clear(&co0); mpz_clear(c.y);
        trep_tot += t_rep;
    }
    printf("\n%ld anchored patterns (%ld representations): %ld CLOSED outright by the deep cut; others: bound >= 10^(10^%.2f) digits [%.0fs]\n",
           npat, nrep, nclosed, minw, cpu_s() - t0);
    fprintf(stderr, "rep enumeration CPU %.3fs; total %.3fs\n", trep_tot, cpu_s() - t0);
    fprintf(stderr, "y5 histogram:"); for (int i = 0; i < 16; i++) fprintf(stderr, " %ld", g_y5hist[i]); fprintf(stderr, "\n");
    fprintf(stderr, "reps with a repeated (d,e) key: %ld; 5|L events: %ld; eager/lazy disagreements: %ld\n", ndup, g_n5L, g_total_cases_eager_mismatch);
    if (ft) fclose(ft);
    return 0;
}

/* ---------------------------------------------------------------- sandwich driver */
typedef struct { int k, a; mpz_t U; } UEnt;
static UEnt *g_u; static int g_nu;
static void load_utable(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open utable");
    char line[4096]; int cap = 0;
    while (fgets(line, sizeof line, f)) {
        int k, a; char us[4000];
        if (sscanf(line, "%d %d %3999s", &k, &a, us) != 3) continue;
        if (g_nu == cap) { cap = cap ? 2 * cap : 64; g_u = realloc(g_u, cap * sizeof *g_u); }
        g_u[g_nu].k = k; g_u[g_nu].a = a; mpz_init_set_str(g_u[g_nu].U, us, 10); g_nu++;
    }
    fclose(f);
}
static const mpz_t *get_U(int k, int a) {
    for (int i = 0; i < g_nu; i++) if (g_u[i].k == k && g_u[i].a == a) return (const mpz_t *)&g_u[i].U;
    die("no Baker bound for this (k,a) in the utable");
    return NULL;
}

/* exact certificate: nn*ell_lo^2 > 2*U^2 with ell_lo = 4771212547/10^10 < log10(3);
   then min norm / sqrt(2) * log10(3) > U, i.e. every candidate has more than U digits. */
static int sandwich_closes(const mpz_t nn, const mpz_t U) {
    mpz_t lhs, rhs, l; mpz_inits(lhs, rhs, l, NULL);
    mpz_set_ui(l, 4771212547UL);
    mpz_mul(lhs, l, l); mpz_mul(lhs, lhs, nn);
    mpz_mul(rhs, U, U); mpz_mul_2exp(rhs, rhs, 1); mpz_mul(rhs, rhs, P10[20]);
    int r = mpz_cmp(lhs, rhs) > 0;
    mpz_clears(lhs, rhs, l, NULL);
    return r;
}

typedef struct { long cases; long cnt[16]; int budget; mpz_t nn; int have; } Acc;

static void dfs_node(DC *par, int target, int a, long maxcases, Acc *acc) {
    int d = par->D;
    par->cases = 0;
    dc_stage(par, a, maxcases - acc->cases);
    acc->cases += par->cases;
    if (par->budget) { acc->budget = 1; return; }
    acc->cnt[d + 1] += par->nsv;
    if (d + 1 == target) {
        mpz_t nn, pb, pc; mpz_inits(nn, pb, pc, NULL);
        for (int i = 0; i < par->nsv; i++) {
            co_nearest(&par->sv[i].co, nn, pb, pc);
            if (!acc->have || mpz_cmp(nn, acc->nn) < 0) { mpz_set(acc->nn, nn); acc->have = 1; }
        }
        mpz_clears(nn, pb, pc, NULL);
        return;
    }
    for (int i = 0; i < par->nsv && !acc->budget; i++) {
        DC sub; memset(&sub, 0, sizeof sub);
        sub.rep = par->rep; sub.D = d + 1;
        dc_push(&sub, &par->sv[i].co, par->sv[i].t, MAXIT);
        dfs_node(&sub, target, a, maxcases, acc);
        dc_free(&sub);
    }
}

static int g_dfs = 0;

static int cmd_sandwich(int argc, char **argv) {
    const char *lat = NULL, *cases = NULL, *only = NULL, *tsv = NULL, *ut = NULL;
    int maxdepth = 5; long maxcases = 2000000;
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--lattice")) lat = argv[++i];
        else if (!strcmp(argv[i], "--cases")) cases = argv[++i];
        else if (!strcmp(argv[i], "--only")) only = argv[++i];
        else if (!strcmp(argv[i], "--utable")) ut = argv[++i];
        else if (!strcmp(argv[i], "--tsv")) tsv = argv[++i];
        else if (!strcmp(argv[i], "--maxdepth")) maxdepth = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--maxcases")) maxcases = atol(argv[++i]);
        else if (!strcmp(argv[i], "--dfs")) g_dfs = 1;
    }
    if (!lat || !cases || !ut || !only) die("sandwich needs --lattice --cases --utable --only");
    double t0 = cpu_s();
    load_lattice(lat); load_utable(ut);
    KeySet ks = load_keys(only);
    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");
    FILE *ft = tsv ? fopen(tsv, "w") : NULL;
    if (ft) setvbuf(ft, NULL, _IOLBF, 0);
    long nall = 0, nclosed = 0, fdis = 0;
    Case c;
    while (read_case(f, &c)) {
        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey)) { mpz_clear(c.y); continue; }
        nall++;
        const mpz_t *U = get_U(c.k, c.a);
        double logU = mpz_log10d(*U);
        int a, b, cc;
        if (!factor237(c.y, &a, &b, &cc) || a != c.a) die("anchor is not 2^a 3^b 7^c with the recorded a");
        Co co0; co_init(&co0); co_set(&co0, &g_lam);
        mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, cc); co_babai(&co0);
        RepList reps = {0, 0, 0};
        filtered_reps(&reps, &c);
        char ys[600]; char *y10 = mpz_get_str(NULL, 10, c.y); snprintf(ys, sizeof ys, "%s", y10); free(y10);
        int allclosed = 1;
        char out[16384]; out[0] = 0; size_t on = 0;
        on += snprintf(out + on, sizeof out - on, "[");
        for (int ri = 0; ri < reps.n; ri++) {
            DC s; dc_init(&s, &reps.v[ri], &co0);
            const char *res = "open"; int resD = 0; long rescases = 0; char bstr[64] = ""; char st[256] = "";
            mpz_t nn; mpz_init(nn);
            for (int D = 1; D <= maxdepth; D++) {
                double tr = cpu_s();
                Acc acc; memset(&acc, 0, sizeof acc); mpz_init(acc.nn);
                if (g_dfs) {
                    DC root; dc_init(&root, &reps.v[ri], &co0);
                    dfs_node(&root, D, c.a, maxcases, &acc);
                    dc_free(&root);
                    s.cases = acc.cases; s.budget = acc.budget; s.closed = !acc.budget && acc.cnt[D] == 0;
                    for (int q = 0; q < D; q++) s.stats[q] = acc.cnt[q + 1];
                } else dc_stage(&s, c.a, maxcases);
                resD = D; rescases = s.cases;
                if (s.budget) { res = "BUDGET"; if (ft) fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t%d\tBUDGET\t%ld\t-\t-\t%.9f\n", c.fullkey, c.s, c.Mstr, c.a, ys, ri, D, s.cases, cpu_s() - tr); break; }
                if (s.closed) { res = "CLOSED-cut"; if (ft) fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t%d\tCLOSED-cut\t%ld\t-\t-\t%.9f\n", c.fullkey, c.s, c.Mstr, c.a, ys, ri, D, s.cases, cpu_s() - tr); break; }
                if (g_dfs) mpz_set(nn, acc.nn); else dc_min_nn(&s, nn);
                mpz_clear(acc.nn);
                double bound = digits_bound_log10(nn);
                int exact = sandwich_closes(nn, *U);
                int flt = bound > logU;
                if (exact != flt) fdis++;
                fmt_round2(bstr, bound);
                size_t sn = 0; sn += snprintf(st + sn, sizeof st - sn, "[");
                for (int q = 0; q < D; q++) sn += snprintf(st + sn, sizeof st - sn, "%s%ld", q ? ", " : "", s.stats[q]);
                snprintf(st + sn, sizeof st - sn, "]");
                res = exact ? "CLOSED-sandwich" : "open";
                if (ft) {
                    char *nns = mpz_get_str(NULL, 10, nn);
                    fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t%d\t%s\t%ld\t%s\t%s\t%.9f\n", c.fullkey, c.s, c.Mstr, c.a, ys, ri, D, res, s.cases, st, nns, cpu_s() - tr);
                    free(nns);
                }
                if (exact) break;
            }
            if (ft && !strcmp(res, "open") && 0) {}
            if (ri) on += snprintf(out + on, sizeof out - on, ", ");
            if (!strcmp(res, "CLOSED-cut")) on += snprintf(out + on, sizeof out - on, "('CLOSED-cut', %d, %ld)", resD, rescases);
            else if (!strcmp(res, "BUDGET")) on += snprintf(out + on, sizeof out - on, "('BUDGET', %d, %ld)", resD, rescases);
            else on += snprintf(out + on, sizeof out - on, "('%s', %d, %ld, %s, %s)", res, resD, rescases, bstr, st);
            if (strcmp(res, "CLOSED-cut") && strcmp(res, "CLOSED-sandwich")) allclosed = 0;
            mpz_clear(nn); dc_free(&s);
        }
        snprintf(out + on, sizeof out - on, "]");
        nclosed += allclosed;
        printf("s=%-8s M=%-12s a=%d y=%-11s k=%d log10 U=%.1f reps=%d -> %s %s [%.0fs]\n", c.s, c.Mstr, c.a, ys, c.k, logU, reps.n,
               allclosed ? "CLOSED" : "OPEN", out, cpu_s() - t0);
        fflush(stdout);
        free(reps.v); co_clear(&co0); mpz_clear(c.y);
    }
    printf("\n%ld of %ld patterns closed by the sandwich\n", nclosed, nall);
    fprintf(stderr, "float/exact sandwich decision disagreements: %ld; 5|L events: %ld\n", fdis, g_n5L);
    if (ft) fclose(ft);
    return 0;
}

/* ---------------------------------------------------------------- selftest: planted checks */
static unsigned long long rng_state = 0x9E3779B97F4A7C15ULL;
static unsigned long long rng(void) {
    rng_state ^= rng_state << 13; rng_state ^= rng_state >> 7; rng_state ^= rng_state << 17; return rng_state;
}

static int cmd_selftest(int argc, char **argv) {
    const char *lat = NULL; int trials = 300;
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--lattice")) lat = argv[++i];
        else if (!strcmp(argv[i], "--trials")) trials = atoi(argv[++i]);
    }
    if (!lat) die("selftest needs --lattice");
    load_lattice(lat);
    int fails = 0;

    /* 1. nearest-point: exact descent against a 9x9 brute window on random reduced cosets */
    {
        int bad = 0, n = 0;
        mpz_t nn, pb, pc, bn, tb, tc, tn;
        mpz_inits(nn, pb, pc, bn, tb, tc, tn, NULL);
        for (int it = 0; it < 2000; it++) {
            Co c; co_init(&c);
            long a1 = (long)(rng() % 2000) - 1000, a2 = (long)(rng() % 2000) - 1000, b1 = (long)(rng() % 2000) - 1000, b2 = (long)(rng() % 2000) - 1000;
            if (a1 * b2 - a2 * b1 == 0) { co_clear(&c); continue; }
            mpz_set_si(c.u1b, a1); mpz_set_si(c.u1c, a2); mpz_set_si(c.u2b, b1); mpz_set_si(c.u2c, b2);
            mpz_set_si(c.v0b, (long)(rng() % 100000) - 50000); mpz_set_si(c.v0c, (long)(rng() % 100000) - 50000);
            co_nearest(&c, nn, pb, pc);
            co_reduce(&c); co_babai(&c);
            int first = 1;
            for (int x = -4; x <= 4; x++) for (int y = -4; y <= 4; y++) {
                mpz_set(tb, c.v0b); mpz_addmul_ui(tb, c.u1b, 0);
                mpz_set(tb, c.v0b); mpz_set(tc, c.v0c);
                mpz_t xs, ys; mpz_init_set_si(xs, x); mpz_init_set_si(ys, y);
                mpz_addmul(tb, xs, c.u1b); mpz_addmul(tb, ys, c.u2b);
                mpz_addmul(tc, xs, c.u1c); mpz_addmul(tc, ys, c.u2c);
                dot2(tn, tb, tc, tb, tc);
                if (first || mpz_cmp(tn, bn) < 0) { mpz_set(bn, tn); first = 0; }
                mpz_clears(xs, ys, NULL);
            }
            n++; if (mpz_cmp(bn, nn) != 0) bad++;
            co_clear(&c);
        }
        printf("PLANT nearest-point: %d random reduced cosets, exact descent vs 9x9 brute window: %d mismatches\n", n, bad);
        if (bad) fails++;
        mpz_clears(nn, pb, pc, bn, tb, tc, tn, NULL);
    }

    /* 2. genuine S-units with >= 300 digits survive their own chain (K = 96..480); nearest norm <= b^2+c^2 */
    int Ks[5] = {96, 192, 288, 384, 480};
    int nsurv = 0, ntry = 0, nneg_ex = 0, nneg = 0, nlazy_bad = 0, nbound_bad = 0;
    for (int tr = 0; tr < trials; tr++) {
        int a = (int)(rng() % 35); long b = (long)(rng() % 500), c = (long)(rng() % 500);
        mpz_t y, bb, cb; mpz_inits(y, bb, cb, NULL);
        mpz_ui_pow_ui(y, 3, b); mpz_t t7; mpz_init(t7); mpz_ui_pow_ui(t7, 7, c); mpz_mul(y, y, t7); mpz_mul_2exp(y, y, a); mpz_clear(t7);
        if (mpz_sizeinbase(y, 10) < 300 || mpz_sizeinbase(y, 10) < 301) { mpz_clears(y, bb, cb, NULL); tr--; continue; }
        mpz_set_si(bb, b); mpz_set_si(cb, c);
        Co co; co_init(&co); co_set(&co, &g_lam); mpz_set_si(co.v0b, b); mpz_set_si(co.v0c, c); co_babai(&co);
        int alive = 1; ntry++;
        for (int ki = 0; ki < 5 && alive; ki++) {
            int K = Ks[ki];
            mpz_t L; mpz_init(L); mpz_fdiv_r(L, y, P10[K]);
            if ((long)mpz_scan1(L, 0) != a) die("v2 of genuine S-unit tail != a");
            Pre5 pre; pre5_init(&pre); pre5_make(&pre, &co, K);
            int lz = pre5_alive(&pre, a, L);
            Co nco; co_init(&nco);
            int ok = cut_full(&nco, &co, a, L, K);
            if (!lz) nlazy_bad++;
            if (!ok) { alive = 0; }
            else {
                if (!co_contains(&nco, bb, cb)) alive = 0;
                mpz_t nn, pb, pc, own; mpz_inits(nn, pb, pc, own, NULL);
                co_nearest(&nco, nn, pb, pc);
                mpz_mul(own, bb, bb); mpz_addmul(own, cb, cb);
                if (mpz_cmp(nn, own) > 0) nbound_bad++;
                mpz_clears(nn, pb, pc, own, NULL);
                co_set(&co, &nco);
            }
            co_clear(&nco); pre5_clear(&pre); mpz_clear(L);
        }
        if (alive) nsurv++;
        /* negative: corrupt one tail digit of the same point at K=96 (position >= a+1 keeps v2) */
        {
            Co co0; co_init(&co0); co_set(&co0, &g_lam); mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, c); co_babai(&co0);
            mpz_t L; mpz_init(L); mpz_fdiv_r(L, y, P10[96]);
            int cand[16], nc = 0; for (int p = 0; p < 5; p++) if (p > a) cand[nc++] = p; for (int p = a + 1; p <= a + 8; p++) cand[nc++] = p; int pos = cand[rng() % nc];
            mpz_add(L, L, P10[pos]); mpz_fdiv_r(L, L, P10[96]);
            Co nco; co_init(&nco);
            if ((long)mpz_scan1(L, 0) == a && mpz_fdiv_ui(L, 5) != 0) {
                nneg++;
                if (!cut_full(&nco, &co0, a, L, 96)) nneg_ex++;
            }
            co_clear(&nco); co_clear(&co0); mpz_clear(L);
        }
        co_clear(&co); mpz_clears(y, bb, cb, NULL);
    }
    printf("PLANT positive: %d/%d genuine S-units (>=300 digits, a in 0..34) survive the chain K=96,192,288,384,480 with (b,c) inside every sub-coset; "
           "nearest norm exceeded the point's own norm in %d cases; lazy prefilter wrongly dead in %d cases\n", nsurv, ntry, nbound_bad, nlazy_bad);
    printf("PLANT negative: %d/%d corrupted-digit tails (digit moved at a position the verdict depends on) excluded at K=96\n", nneg_ex, nneg);
    if (nsurv != ntry || nbound_bad || nlazy_bad || nneg_ex * 100 < nneg * 97) fails++;

    /* 3. planted: a genuine S-unit's own pattern, driven through the real dc_stage with its true copy assignment */
    {
        int ok_true = 0, ok_neg_dead = 0, ntr = 0, nneg2 = 0;
        for (int tr = 0; tr < 60; tr++) {
            int a = (int)(rng() % 35); long b = (long)(rng() % 500), c = (long)(rng() % 500);
            mpz_t y, bb, cb, q; mpz_inits(y, bb, cb, q, NULL);
            mpz_ui_pow_ui(y, 3, b); mpz_ui_pow_ui(q, 7, c); mpz_mul(y, y, q); mpz_mul_2exp(y, y, a);
            if (mpz_sizeinbase(y, 10) < 302) { mpz_clears(y, bb, cb, q, NULL); tr--; continue; }
            mpz_set_si(bb, b); mpz_set_si(cb, c);
            Rep rep; memset(&rep, 0, sizeof rep);
            signed char t0[MAXIT];
            for (int p = 0; p < 3 * LMAX; p++) {
                mpz_tdiv_q(q, y, P10[p]);
                int dg = (int)mpz_fdiv_ui(q, 10);
                if (dg == 1) continue;
                rep.d[rep.n] = dg; rep.e[rep.n] = p % LMAX; t0[rep.n] = (signed char)(p / LMAX); rep.n++;
            }
            Co co0; co_init(&co0); co_set(&co0, &g_lam); mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, c); co_babai(&co0);
            for (int neg = 0; neg < 2; neg++) {
                DC s; dc_init(&s, &rep, &co0);
                memset(s.sv[0].t, -1, MAXIT);
                memcpy(s.sv[0].t, t0, rep.n);
                if (neg) { int i = 0; while (t0[i] != 0) i++; s.sv[0].t[i] = 1; }
                int alive = 1;
                for (int D = 1; D <= 3 && alive; D++) {
                    dc_stage(&s, a, 1000000);
                    if (s.nsv == 0) { alive = 0; break; }
                    int has = 0;
                    for (int i = 0; i < s.nsv; i++) if (co_contains(&s.sv[i].co, bb, cb)) has = 1;
                    if (!has && !neg) alive = 0;
                    if (neg && !has) alive = 0;
                }
                if (!neg) { ntr++; ok_true += alive; } else { nneg2++; ok_neg_dead += !alive; }
                dc_free(&s);
            }
            co_clear(&co0); mpz_clears(y, bb, cb, q, NULL);
        }
        printf("PLANT own-pattern: %d/%d genuine S-unit patterns (all non-1 digits of the lowest 288, true copies) keep their point through dc_stage D=1..3; "
               "%d/%d with one copy index moved are dropped\n", ok_true, ntr, ok_neg_dead, nneg2);
        if ((ok_true != ntr || ok_neg_dead != nneg2)) fails++;
    }
    printf("SELFTEST %s\n", fails ? "FAILED" : "PASSED");
    return fails != 0;
}

/* ================================================================================================================
 * shadow certificate (tier0/HSHADOW.md) -- one DP over Z/148417 per representation instead of per-word children
 * enumeration at level 192, and an exact meet-in-the-middle over the level-384 children of each level-192 shadow.
 *
 *   cport_shadow shadow --lattice L --utable U --cases C --only K --levelprimes P [--tsv F] [--stats F] [--dump F]
 *                       [--dump-surv F] [--faithful] [--diag] [--stats-only] [--use192 p,p..] [--use384 p,p..]
 *                       [--mutant noNu|wrongmod] [--no-assert]
 * ============================================================================================================== */
typedef uint64_t u64;
typedef unsigned __int128 u128;

static u64 mulm(u64 a, u64 b, u64 m) { return (u64)((u128)a * b % m); }
static u64 powm(u64 b, u64 e, u64 m) {
    u64 r = 1 % m; b %= m;
    while (e) { if (e & 1) r = mulm(r, b, m); b = mulm(b, b, m); e >>= 1; }
    return r;
}
static u64 gcd64(u64 a, u64 b) { while (b) { u64 t = a % b; a = b; b = t; } return a; }
static u64 invm_gen(u64 a, u64 m) {
    __int128 r0 = m, r1 = a % m, s0 = 0, s1 = 1;
    while (r1) { __int128 q = r0 / r1, t = r0 - q * r1; r0 = r1; r1 = t; t = s0 - q * s1; s0 = s1; s1 = t; }
    if (r0 != 1) die("invm_gen: not invertible");
    if (s0 < 0) s0 += m;
    return (u64)s0;
}

typedef struct { u64 q, qe, m, gq, ginvq, gamma, gim, hmask; int e; u64 *hk; uint32_t *hv; int built; } PF;
typedef struct { int L, on; u64 p, g, l2, l3, l7; int nf; PF f[16]; } LP;
static LP g_lp[64]; static int g_nlp;
static u64 g_PT = 148417;
static int g_brute = 0, g_trace = 0;
static long g_brute_checked = 0, g_brute_pass = 0;
static int g_mut_nonu = 0, g_mut_wrongmod = 0, g_faithful = 0, g_diag = 0, g_stats_only = 0;
static long g_ndlog = 0;

static void pf_build(const LP *P, PF *f) {
    u64 p = P->p, n = p - 1;
    f->gq = powm(P->g, n / f->qe, p);
    f->ginvq = powm(f->gq, f->qe - 1, p);
    f->gamma = powm(f->gq, f->qe / f->q, p);
    u64 m = (u64)sqrtl((long double)f->q) + 1; f->m = m;
    u64 cap = 1; while (cap < 4 * m) cap <<= 1;
    f->hmask = cap - 1;
    f->hk = calloc(cap, sizeof(u64)); f->hv = calloc(cap, sizeof(uint32_t));
    u64 cur = 1;
    for (u64 j = 0; j < m; j++) {
        u64 h = (cur * 0x9E3779B97F4A7C15ULL) >> 20 & f->hmask;
        while (f->hk[h] && f->hk[h] != cur) h = (h + 1) & f->hmask;
        if (!f->hk[h]) { f->hk[h] = cur; f->hv[h] = (uint32_t)j; }
        cur = mulm(cur, f->gamma, p);
    }
    f->gim = invm_gen(powm(f->gamma, m, p), p);
    f->built = 1;
}
static u64 pf_bsgs(const LP *P, PF *f, u64 h) {
    u64 x = h;
    for (u64 i = 0; i <= f->m; i++) {
        u64 hh = (x * 0x9E3779B97F4A7C15ULL) >> 20 & f->hmask;
        while (f->hk[hh]) { if (f->hk[hh] == x) return (i * f->m + f->hv[hh]) % f->q; hh = (hh + 1) & f->hmask; }
        x = mulm(x, f->gim, P->p);
    }
    die("bsgs: no discrete log");
    return 0;
}
static u64 lp_dlog(LP *P, u64 h) {
    u64 p = P->p, n = p - 1, X = 0, Mm = 1;
    h %= p; if (h == 0) die("dlog of 0");
    g_ndlog++;
    for (int i = 0; i < P->nf; i++) {
        PF *f = &P->f[i];
        if (!f->built) pf_build(P, f);
        u64 hq = powm(h, n / f->qe, p), x = 0, qpow = 1, ex = f->qe;
        for (int k = 0; k < f->e; k++) {
            ex /= f->q;
            u64 t = mulm(hq, powm(f->ginvq, x, p), p);
            u64 hk = powm(t, ex, p);
            u64 dk = pf_bsgs(P, f, hk);
            x += dk * qpow; qpow *= f->q;
        }
        u64 m = f->qe, r = x % m;
        u64 tt = mulm((r + m - X % m) % m, invm_gen(Mm % m, m), m);
        X += Mm * tt; Mm *= m;
    }
    if (powm(P->g, X, p) != h) die("dlog certificate failed");
    return X;
}
typedef struct { u64 q; int e; u64 qe, m; unsigned long nb; u64 *bk; uint32_t *bj; mpz_t gam, gim; int built; } BF;
typedef struct { int L, on, nf; mpz_t p, pm1, g, l2, l3, l7; BF f[12]; } BP;
static BP g_bp[4]; static int g_nbp;

static void bp_parse(const char *s) {
    if (g_nbp >= 4) die("too many big level primes");
    BP *B = &g_bp[g_nbp];
    char sp[160], sg[160], s2[160], s3[160], s7[160]; int L, nf, n, off;
    if (sscanf(s, "%d %159s %159s %159s %159s %159s %d%n", &L, sp, sg, s2, s3, s7, &nf, &n) != 7) die("bad big levelprimes line");
    off = n;
    if (nf > 12) die("big prime: too many factors");
    memset(B, 0, sizeof *B);
    mpz_inits(B->p, B->pm1, B->g, B->l2, B->l3, B->l7, NULL);
    mpz_set_str(B->p, sp, 10); mpz_set_str(B->g, sg, 10); mpz_set_str(B->l2, s2, 10); mpz_set_str(B->l3, s3, 10); mpz_set_str(B->l7, s7, 10);
    if (!mpz_probab_prime_p(B->p, 40)) die("big levelprime is not prime");
    mpz_sub_ui(B->pm1, B->p, 1);
    mpz_t t, prod; mpz_inits(t, prod, NULL);
    mpz_ui_pow_ui(t, 10, L); mpz_sub_ui(t, t, 1);
    if (!mpz_divisible_p(t, B->p)) die("big levelprime does not divide 10^L-1");
    mpz_set_ui(prod, 1);
    for (int i = 0; i < nf; i++) {
        unsigned long long q; int e;
        if (sscanf(s + off, "%llu %d%n", &q, &e, &n) != 2) die("bad big factor list");
        off += n;
        B->f[i].q = q; B->f[i].e = e; B->f[i].qe = 1;
        for (int j = 0; j < e; j++) B->f[i].qe *= q;
        mpz_ui_pow_ui(t, q, e); mpz_mul(prod, prod, t);
        mpz_t ex; mpz_init(ex); mpz_divexact_ui(ex, B->pm1, q); mpz_powm(t, B->g, ex, B->p);
        if (mpz_cmp_ui(t, 1) == 0) die("big levelprime: g is not a primitive root");
        mpz_clear(ex);
    }
    if (mpz_cmp(prod, B->pm1) != 0) die("big levelprime: factorization of p-1 does not multiply out");
    mpz_powm(t, B->g, B->l2, B->p); if (mpz_cmp_ui(t, 2) != 0) die("big levelprime: g^l2 != 2");
    mpz_powm(t, B->g, B->l3, B->p); if (mpz_cmp_ui(t, 3) != 0) die("big levelprime: g^l3 != 3");
    mpz_powm(t, B->g, B->l7, B->p); if (mpz_cmp_ui(t, 7) != 0) die("big levelprime: g^l7 != 7");
    mpz_clears(t, prod, NULL);
    B->L = L; B->on = 1; B->nf = nf;
    g_nbp++;
}
typedef struct { u64 k; uint32_t j; } BKJ;
static int cmp_bkj(const void *x, const void *y) {
    const BKJ *a = x, *b = y;
    return a->k < b->k ? -1 : a->k > b->k;
}
static void bf_build(BP *B, BF *f) {
    mpz_t ex, gq; mpz_inits(ex, gq, NULL);
    mpz_divexact_ui(ex, B->pm1, f->qe);
    mpz_init(f->gam); mpz_init(f->gim);
    mpz_powm(gq, B->g, ex, B->p);
    mpz_set_ui(ex, f->qe / f->q); mpz_powm(f->gam, gq, ex, B->p);
    f->m = (u64)sqrtl((long double)f->q) + 1;
    BKJ *tab = malloc(f->m * sizeof(BKJ));
    mpz_t cur; mpz_init_set_ui(cur, 1);
    for (u64 j = 0; j < f->m; j++) {
        tab[j].k = mpz_getlimbn(cur, 0); tab[j].j = (uint32_t)j;
        mpz_mul(cur, cur, f->gam); mpz_mod(cur, cur, B->p);
    }
    qsort(tab, f->m, sizeof(BKJ), cmp_bkj);
    f->bk = malloc(f->m * sizeof(u64)); f->bj = malloc(f->m * sizeof(uint32_t));
    for (u64 j = 0; j < f->m; j++) { f->bk[j] = tab[j].k; f->bj[j] = tab[j].j; }
    free(tab);
    mpz_set_ui(ex, f->m); mpz_powm(cur, f->gam, ex, B->p); mpz_invert(f->gim, cur, B->p);
    f->built = 1;
    mpz_clears(ex, gq, cur, NULL);
}
static u64 bf_bsgs(BP *B, BF *f, const mpz_t h) {
    mpz_t x, gj, ej; mpz_init_set(x, h); mpz_inits(gj, ej, NULL);
    for (u64 i = 0; i <= f->m; i++) {
        u64 key = mpz_getlimbn(x, 0);
        long lo = 0, hi = (long)f->m;
        while (lo < hi) { long mid = (lo + hi) / 2; if (f->bk[mid] < key) lo = mid + 1; else hi = mid; }
        for (long q = lo; q < (long)f->m && f->bk[q] == key; q++) {
            mpz_set_ui(ej, f->bj[q]); mpz_powm(gj, f->gam, ej, B->p);
            if (mpz_cmp(gj, x) == 0) { u64 r = (i * f->m + f->bj[q]) % f->q; mpz_clears(x, gj, ej, NULL); return r; }
        }
        mpz_mul(x, x, f->gim); mpz_mod(x, x, B->p);
    }
    die("big bsgs: no discrete log");
    return 0;
}
static void bp_dlog(mpz_t out, BP *B, const mpz_t h) {
    mpz_t X, Mm, hq, gq, ginv, t, hk, ex, tmp, rr, inv, mod;
    mpz_inits(X, Mm, hq, gq, ginv, t, hk, ex, tmp, rr, inv, mod, NULL);
    mpz_set_ui(X, 0); mpz_set_ui(Mm, 1);
    for (int i = 0; i < B->nf; i++) {
        BF *f = &B->f[i];
        if (!f->built) bf_build(B, f);
        mpz_divexact_ui(ex, B->pm1, f->qe);
        mpz_powm(hq, h, ex, B->p); mpz_powm(gq, B->g, ex, B->p); mpz_invert(ginv, gq, B->p);
        u64 x = 0, qpow = 1;
        for (int k = 0; k < f->e; k++) {
            mpz_set_ui(tmp, x); mpz_powm(t, ginv, tmp, B->p); mpz_mul(t, t, hq); mpz_mod(t, t, B->p);
            u64 expo = f->qe; for (int j = 0; j <= k; j++) expo /= f->q;
            mpz_set_ui(tmp, expo); mpz_powm(hk, t, tmp, B->p);
            u64 dk = bf_bsgs(B, f, hk);
            x += dk * qpow; qpow *= f->q;
        }
        mpz_set_ui(mod, f->qe); mpz_set_ui(rr, x % f->qe);
        mpz_sub(rr, rr, X); mpz_mod(rr, rr, mod);
        mpz_mod(tmp, Mm, mod); mpz_invert(inv, tmp, mod);
        mpz_mul(rr, rr, inv); mpz_mod(rr, rr, mod);
        mpz_addmul(X, Mm, rr); mpz_mul_ui(Mm, Mm, f->qe);
    }
    mpz_powm(t, B->g, X, B->p);
    if (mpz_cmp(t, h) != 0) die("big dlog certificate failed");
    mpz_set(out, X);
    mpz_clears(X, Mm, hq, gq, ginv, t, hk, ex, tmp, rr, inv, mod, NULL);
}
static int bp_cut(Co *c, BP *B, const mpz_t Vx, int a, mpz_t *cache, unsigned char *cs) {
    if (*cs == 0) {
        mpz_t vm; mpz_init(vm); mpz_mod(vm, Vx, B->p);
        if (mpz_sgn(vm) == 0) { *cs = 2; }
        else {
            mpz_t lr, am; mpz_inits(lr, am, NULL);
            bp_dlog(lr, B, vm);
            mpz_mul_ui(am, B->l2, (unsigned long)a);
            mpz_sub(lr, lr, am); mpz_mod(*cache, lr, B->pm1);
            *cs = 1; mpz_clears(lr, am, NULL);
        }
        mpz_clear(vm);
    }
    if (*cs == 2) return 0;
    return co_intersect(c, c, B->l3, B->l7, *cache, B->pm1);
}

static void load_levelprimes(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open levelprimes file");
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        if (line[0] == 'B') { bp_parse(line + 1); continue; }
        LP P; memset(&P, 0, sizeof P);
        unsigned long long p, g, l2, l3, l7; int L, nf, off, n;
        if (sscanf(line, "%d %llu %llu %llu %llu %llu %d%n", &L, &p, &g, &l2, &l3, &l7, &nf, &n) != 7) die("bad levelprimes line");
        off = n;
        P.L = L; P.p = p; P.g = g; P.l2 = l2; P.l3 = l3; P.l7 = l7; P.nf = nf; P.on = 1;
        u64 prod = 1;
        for (int i = 0; i < nf; i++) {
            unsigned long long q; int e;
            if (sscanf(line + off, "%llu %d%n", &q, &e, &n) != 2) die("bad factor list");
            off += n;
            P.f[i].q = q; P.f[i].e = e; P.f[i].qe = 1;
            for (int j = 0; j < e; j++) P.f[i].qe *= q;
            prod *= P.f[i].qe;
        }
        if (prod != p - 1) die("levelprimes: factorization of p-1 does not multiply out");
        if (powm(g, l2, p) != 2 % p || powm(g, l3, p) != 3 % p || powm(g, l7, p) != 7 % p) die("levelprimes: logs wrong");
        mpz_t t, pm; mpz_inits(t, pm, NULL);
        mpz_ui_pow_ui(t, 10, L); mpz_sub_ui(t, t, 1);
        if (!mpz_divisible_ui_p(t, p)) die("levelprime does not divide 10^L-1");
        mpz_clears(t, pm, NULL);
        int dup = 0;
        for (int i = 0; i < g_nlp; i++) if (g_lp[i].p == p && g_lp[i].L == L) dup = 1;
        if (dup) continue;
        if (g_nlp >= 64) die("too many level primes");
        g_lp[g_nlp++] = P;
    }
    fclose(f);
}
static void set_use(int level, const char *list) {
    for (int i = 0; i < g_nlp; i++) if (g_lp[i].L == level) g_lp[i].on = 0;
    if (!strcmp(list, "none")) return;
    char *s = strdup(list), *tok, *q = s;
    while ((tok = strsep(&q, ",")) != NULL) if (*tok) {
        u64 p = strtoull(tok, NULL, 10); int hit = 0;
        for (int i = 0; i < g_nlp; i++) if (g_lp[i].L == level && g_lp[i].p == p) { g_lp[i].on = 1; hit = 1; }
        if (!hit) die("--use list names a prime that is not a new prime of that level");
    }
    free(s);
}
static LP *lp_find(u64 p) { for (int i = 0; i < g_nlp; i++) if (g_lp[i].p == p) return &g_lp[i]; die("lp_find"); return NULL; }

static u64 tgt_for(LP *P, u64 vmodp, int a) {
    u64 lr = lp_dlog(P, vmodp), am = (u64)((u128)a * P->l2 % (P->p - 1));
    return (lr + (P->p - 1) - am) % (P->p - 1);
}
static int cut_lp_tgt(Co *c, const LP *P, u64 tgt) {
    mpz_t A, B, r, m; mpz_inits(A, B, r, m, NULL);
    mpz_set_ui(A, P->l3); mpz_set_ui(B, P->l7); mpz_set_ui(r, tgt); mpz_set_ui(m, P->p - 1);
    int ok = co_intersect(c, c, A, B, r, m);
    mpz_clears(A, B, r, m, NULL);
    return ok;
}
/* cut the coset by every enabled new prime of `level` against the value Vx; 0 when empty */
static int chain_level(Co *c, const mpz_t Vx, int a, int level) {
    for (int i = 0; i < g_nlp; i++) {
        LP *P = &g_lp[i];
        if (P->L != level || !P->on) continue;
        u64 vm = mpz_fdiv_ui(Vx, P->p);
        if (vm == 0) return 0;
        if (!cut_lp_tgt(c, P, tgt_for(P, vm, a))) return 0;
    }
    return 1;
}
static int window_cut(Co *dst, const Co *co, int a, const mpz_t L, int K) {
    if ((long)mpz_scan1(L, 0) != a) return 0;
    if (mpz_fdiv_ui(L, 5) == 0) return 0;
    return cut_full(dst, co, a, L, K);
}

/* ---------------------------------------------------------------- Lambda'_a and its content */
static Co g_lama[MAXA]; static int g_lama_ok[MAXA];
static const Co *lam_a(int a) {
    if (a >= MAXA) die("lam_a: a too large");
    if (!g_lama_ok[a]) {
        Co z; co_init(&z); co_set(&z, &g_lam);
        mpz_set_ui(z.v0b, 0); mpz_set_ui(z.v0c, 0);
        mpz_t L; mpz_init(L); mpz_set_ui(L, 1); mpz_mul_2exp(L, L, a);
        co_init(&g_lama[a]);
        if (!cut_full(&g_lama[a], &z, a, L, LMAX)) die("lam_a: empty");
        mpz_clear(L); co_clear(&z);
        g_lama_ok[a] = 1;
    }
    return &g_lama[a];
}
static void co_content(mpz_t out, const Co *c) {
    mpz_gcd(out, c->u1b, c->u1c); mpz_gcd(out, out, c->u2b); mpz_gcd(out, out, c->u2c);
}
static int basis_trivial_at(const Co *c, u64 p) {
    u64 n = p - 1;
    u64 b1 = mpz_fdiv_ui(c->u1b, n), c1 = mpz_fdiv_ui(c->u1c, n), b2 = mpz_fdiv_ui(c->u2b, n), c2 = mpz_fdiv_ui(c->u2c, n);
    return mulm(powm(3, b1, p), powm(7, c1, p), p) == 1 && mulm(powm(3, b2, p), powm(7, c2, p), p) == 1;
}
static int lattice_same(const Co *x, const Co *y) {
    mpz_t i1, i2; mpz_inits(i1, i2, NULL);
    co_index(i1, x); co_index(i2, y);
    int same = mpz_cmp(i1, i2) == 0;
    mpz_clears(i1, i2, NULL);
    if (!same) return 0;
    mpz_t z; mpz_init_set_ui(z, 0);
    int ok = co_contains(y, x->u1b, x->u1c) && co_contains(y, x->u2b, x->u2c);
    mpz_clear(z);
    return ok;
}
static int run_content_assertions(int amax, int die_on_fail) {
    int fails = 0;
    mpz_t c, t; mpz_inits(c, t, NULL);
    for (int a = 0; a <= amax; a++) {
        const Co *L = lam_a(a);
        co_content(c, L);
        int div768 = mpz_divisible_ui_p(c, 768) != 0;
        int tr193 = basis_trivial_at(L, 193), tr769 = basis_trivial_at(L, 769);
        char fac[256]; int fo = 0; fac[0] = 0;
        mpz_set(t, c);
        for (unsigned pr = 2; pr < 2000 && mpz_cmp_ui(t, 1) > 0; pr++) {
            int ex = 0; while (mpz_divisible_ui_p(t, pr)) { mpz_divexact_ui(t, t, pr); ex++; }
            if (ex) fo += snprintf(fac + fo, sizeof fac - fo, "%s%u^%d", fo ? "*" : "", pr, ex);
        }
        if (mpz_cmp_ui(t, 1) > 0) { char *r = mpz_get_str(NULL, 10, t); fo += snprintf(fac + fo, sizeof fac - fo, "%s(cofactor %.40s)", fo ? "*" : "", r); free(r); }
        char *cs = mpz_get_str(NULL, 10, c);
        printf("CONTENT a=%-2d content=%s = %s  768|content=%s  basis images at 193/769 trivial=%s/%s\n", a, cs, fac, div768 ? "yes" : "NO", tr193 ? "yes" : "NO", tr769 ? "yes" : "NO");
        free(cs);
        if (!div768 || !tr193 || !tr769) fails++;
    }
    mpz_clears(c, t, NULL);
    if (fails && die_on_fail) die("content(Lambda'_a) assertion failed");
    return fails;
}

/* ---------------------------------------------------------------- DP over Z/PT */
typedef struct { unsigned mask; int sn; } Sol;
typedef struct { Sol *v; long n, cap; } SolList;
static void sl_push(SolList *l, unsigned mask, int sn) {
    if (l->n == l->cap) { l->cap = l->cap ? 2 * l->cap : 64; l->v = realloc(l->v, l->cap * sizeof(Sol)); }
    l->v[l->n].mask = mask; l->v[l->n].sn = sn; l->n++;
}
static unsigned char *g_reach; static u64 g_reach_pt; static int g_reach_cap;
static u64 g_wv[MAXIT + 2]; static int g_nit;
static void dp_build(const u64 *val, int nit) {
    if (!g_reach || g_reach_pt != g_PT || g_reach_cap < nit + 1) {
        free(g_reach); g_reach = malloc((size_t)(nit + 2) * g_PT); g_reach_pt = g_PT; g_reach_cap = nit + 1;
    }
    memset(g_reach, 0, (size_t)(nit + 1) * g_PT);
    g_reach[0] = 1;
    for (int i = 0; i < nit; i++) {
        unsigned char *src = g_reach + (size_t)i * g_PT, *dst = g_reach + (size_t)(i + 1) * g_PT;
        u64 w = val[i] % g_PT;
        for (u64 r = 0; r < g_PT; r++) if (src[r]) { dst[r] = 1; u64 r2 = r + w; if (r2 >= g_PT) r2 -= g_PT; dst[r2] = 1; }
    }
    g_nit = nit;
    for (int i = 0; i < nit; i++) g_wv[i] = val[i] % g_PT;
}
static long g_dp_cap = 2000000;
static void dp_rec(int i, u64 r, unsigned mask, int sn, int k, SolList *out) {
    if (out->n > g_dp_cap) die("DP: too many solutions");
    if (i == 0) { if (r == 0) sl_push(out, mask, sn); return; }
    unsigned char *prev = g_reach + (size_t)(i - 1) * g_PT;
    if (prev[r]) dp_rec(i - 1, r, mask, sn, k, out);
    u64 r2 = (r + g_PT - g_wv[i - 1]) % g_PT;
    if (prev[r2]) {
        if (i - 1 == k) dp_rec(i - 1, r2, mask, 1, k, out);
        else dp_rec(i - 1, r2, mask | (1u << (i - 1)), sn, k, out);
    }
}
static void dp_solutions(u64 tau, int k, SolList *out) {
    out->n = 0;
    if (g_reach[(size_t)g_nit * g_PT + tau % g_PT]) dp_rec(g_nit, tau % g_PT, 0, 0, k, out);
}

/* ---------------------------------------------------------------- result accumulators */
typedef struct {
    int nwords, nonappl, content_fail, lat_mismatch, shadow192_dead, shadow192_win_dead;
    long ncand_dp, ncand_tested, nextra, nwords_tau_nonzero;
    int budget;
    long fv_alive, full_alive, fv_words_alive, full_words_alive, n384_cands, n384_pass_primes;
    int rmin, rmax; double sum2r1; long hist[MAXIT + 1];
    int have_nn; mpz_t nn;
} RepRes;
static void rr_init(RepRes *r) { memset(r, 0, sizeof *r); r->rmin = 1 << 20; mpz_init(r->nn); }
static void rr_note_nn(RepRes *r, const Co *c) {
    mpz_t nn, pb, pc; mpz_inits(nn, pb, pc, NULL);
    co_nearest(c, nn, pb, pc);
    if (!r->have_nn || mpz_cmp(nn, r->nn) < 0) { mpz_set(r->nn, nn); r->have_nn = 1; }
    mpz_clears(nn, pb, pc, NULL);
}

static FILE *g_surv_out;
static void dump_surv(const char *key, int ri, int wi, const char *tag, const Co *c) {
    if (!g_surv_out) return;
    char *a = mpz_get_str(NULL, 10, c->v0b), *b = mpz_get_str(NULL, 10, c->v0c), *c1 = mpz_get_str(NULL, 10, c->u1b),
         *c2 = mpz_get_str(NULL, 10, c->u1c), *c3 = mpz_get_str(NULL, 10, c->u2b), *c4 = mpz_get_str(NULL, 10, c->u2c);
    fprintf(g_surv_out, "{\"key\":\"%s\",\"rep\":%d,\"word\":%d,\"tag\":\"%s\",\"offset\":[\"%s\",\"%s\"],\"basis\":[[\"%s\",\"%s\"],[\"%s\",\"%s\"]]}\n", key, ri, wi, tag, a, b, c1, c2, c3, c4);
    free(a); free(b); free(c1); free(c2); free(c3); free(c4);
}

/* ---------------------------------------------------------------- level 384 step for one level-192 shadow */
typedef struct { u64 sum; unsigned mask; } SM;
static int cmp_sm(const void *x, const void *y) {
    const SM *a = x, *b = y;
    return a->sum < b->sum ? -1 : a->sum > b->sum;
}

/*
 * Level-384 children of one level-192 state. tfix[j] >= 0: digit j fixed at copy tfix[j] (0 or 1); tfix[j] < 0: unplaced with
 * t == rho[j] (mod 2). V1 is the state's level-192 pattern value (length residue nu1). A level-384 child is (sn', b): length
 * nu1 + 192 sn', unplaced digit j at residue rho[j] + 2 b_j (mod 4). With 10^192 == -1 at all four level-384 primes,
 *   V2 = V1 + (10^192 - 1) (sum_{b_j = 1} (d_j - 1) 10^(e_j + 96 rho_j) + sn' 10^nu1 R_192)
 * so V2 == V1 - 2 Delta' with Delta' = sum_{b_j=1} iv_j + sn' 10^nu1 / 9: the children whose residues land in the image of the
 * coset at the two smallest-image primes are found by meet-in-the-middle and every candidate is then tested exactly.
 */
static void lift384_state(const char *key, int ri, int wi, const Co *co_in, const int *tfix, const int *rho, const mpz_t V1, int nu1,
                          int a, const Rep *rep, mpz_t *w, RepRes *rr, const char *tag) {
    int k = rep->n;
    int U[MAXIT], nU = 0;
    for (int j = 0; j < k; j++) if (tfix[j] < 0) U[nU++] = j;
    int nit = nU + 1;
    if (nit > 30) { rr->budget = 1; return; }
    mpz_t iv[MAXIT];
    for (int t = 0; t < nU; t++) { mpz_init(iv[t]); mpz_mul(iv[t], w[U[t]], P10[96 * rho[U[t]]]); }
    int idx[8], ni = 0;
    for (int i = 0; i < g_nlp; i++) if (g_lp[i].L == 384 && g_lp[i].on) idx[ni++] = i;
    struct { int i; u64 count, dd, lb; } pc[8];
    SolList cands = {0, 0, 0};
    if (ni == 0) {
        if (nit > 22) { rr->budget = 1; goto out_iv; }
        for (unsigned m = 0; m < (1u << nit); m++) sl_push(&cands, m & ((1u << nU) - 1), (m >> nU) & 1);
    }
    else {
    for (int t = 0; t < ni; t++) {
        LP *P = &g_lp[idx[t]]; u64 n = P->p - 1;
        u64 lb = ((u128)(a % n) * P->l2 + (u128)mpz_fdiv_ui(co_in->v0b, n) * P->l3 + (u128)mpz_fdiv_ui(co_in->v0c, n) * P->l7) % n;
        u64 s1 = (u64)(((u128)mpz_fdiv_ui(co_in->u1b, n) * P->l3 + (u128)mpz_fdiv_ui(co_in->u1c, n) * P->l7) % n);
        u64 s2 = (u64)(((u128)mpz_fdiv_ui(co_in->u2b, n) * P->l3 + (u128)mpz_fdiv_ui(co_in->u2c, n) * P->l7) % n);
        u64 dd = gcd64(gcd64(s1, s2), n);
        pc[t].i = idx[t]; pc[t].dd = dd; pc[t].lb = lb; pc[t].count = n / dd;
    }
    for (int x = 0; x < ni; x++) for (int y = x + 1; y < ni; y++) if (pc[y].count < pc[x].count) { __typeof__(pc[0]) tmp = pc[x]; pc[x] = pc[y]; pc[y] = tmp; }
    int ns = ni < 2 ? ni : 2;
    u64 pp[2];
    u64 M = 1; u64 ntarg = 1;
    for (int t = 0; t < ns; t++) { LP *P = &g_lp[pc[t].i]; pp[t] = P->p; M *= P->p; ntarg *= pc[t].count; if (pc[t].count > 4096) { rr->budget = 1; goto out_iv; } }
    if (ntarg > 400000) { rr->budget = 1; goto out_iv; }
    u64 tau_p[2][4096];
    for (int t = 0; t < ns; t++) {
        LP *P = &g_lp[pc[t].i];
        u64 inv2 = (P->p + 1) / 2, Vp = mpz_fdiv_ui(V1, P->p);
        u64 gd = powm(P->g, pc[t].dd, P->p), x = powm(P->g, pc[t].lb, P->p);
        for (u64 c = 0; c < pc[t].count; c++) {
            tau_p[t][c] = mulm((Vp + P->p - x) % P->p, inv2, P->p);
            x = mulm(x, gd, P->p);
        }
    }
    u64 *targets = malloc(ntarg * sizeof(u64)); u64 nt = 0;
    if (ns == 1) { for (u64 c = 0; c < pc[0].count; c++) targets[nt++] = tau_p[0][c]; }
    else {
        u64 inv12 = invm_gen(pp[0] % pp[1], pp[1]);
        for (u64 c0 = 0; c0 < pc[0].count; c0++) for (u64 c1 = 0; c1 < pc[1].count; c1++) {
            u64 t0 = tau_p[0][c0], t1 = tau_p[1][c1];
            u64 tt = mulm((t1 + pp[1] - t0 % pp[1]) % pp[1], inv12, pp[1]);
            targets[nt++] = t0 + pp[0] * tt;
        }
    }
    u64 val[34];
    for (int t = 0; t < nU; t++) val[t] = mpz_fdiv_ui(iv[t], M);
    val[nU] = mulm(mpz_fdiv_ui(P10[nu1], M), invm_gen(9 % M, M), M);
    int h = nit / 2, nb = nit - h;
    SM *SA = malloc(((size_t)1 << h) * sizeof(SM));
    SA[0].sum = 0; SA[0].mask = 0;
    for (unsigned m = 1; m < (1u << h); m++) { int b = __builtin_ctz(m); SA[m].sum = (SA[m & (m - 1)].sum + val[b]) % M; SA[m].mask = m; }
    qsort(SA, (size_t)1 << h, sizeof(SM), cmp_sm);
    u64 *SB = malloc(((size_t)1 << nb) * sizeof(u64));
    SB[0] = 0;
    for (unsigned m = 1; m < (1u << nb); m++) SB[m] = (SB[m & (m - 1)] + val[h + __builtin_ctz(m)]) % M;
    for (unsigned mb = 0; mb < (1u << nb); mb++) {
        for (u64 t = 0; t < nt; t++) {
            u64 need = (targets[t] % M + M - SB[mb]) % M;
            long lo = 0, hi = (1L << h);
            while (lo < hi) { long mid = (lo + hi) / 2; if (SA[mid].sum < need) lo = mid + 1; else hi = mid; }
            for (long q = lo; q < (1L << h) && SA[q].sum == need; q++) {
                unsigned full = SA[q].mask | (mb << h);
                sl_push(&cands, full & ((1u << nU) - 1), (full >> nU) & 1);
                if (cands.n > g_dp_cap) die("384 MITM: too many candidates");
            }
        }
    }
    free(SA); free(SB); free(targets);
    }
    rr->n384_cands += cands.n;
    {
    mpz_t V2, tmp, R192, R384, Lv, P192m1; mpz_inits(V2, tmp, R192, R384, Lv, P192m1, NULL);
    mpz_sub_ui(R192, P10[192], 1); mpz_divexact_ui(R192, R192, 9);
    mpz_sub_ui(R384, P10[384], 1); mpz_divexact_ui(R384, R384, 9);
    mpz_sub_ui(P192m1, P10[192], 1);
    long passm = 0;
    for (long ci = 0; ci < cands.n; ci++) {
        unsigned Tm = cands.v[ci].mask; int sn = cands.v[ci].sn;
        mpz_set(V2, V1); mpz_set_ui(tmp, 0);
        for (int t = 0; t < nU; t++) if (Tm >> t & 1) mpz_add(tmp, tmp, iv[t]);
        mpz_addmul(V2, P192m1, tmp);
        if (sn) { mpz_mul(tmp, P10[nu1], R192); mpz_add(V2, V2, tmp); }
        Co c3; co_init(&c3); co_set(&c3, co_in);
        if (!chain_level(&c3, V2, a, 384)) { co_clear(&c3); continue; }
        passm++;
        rr->n384_pass_primes++;
        int cj[MAXIT], ncj = 0, rho2[MAXIT];
        for (int t = 0; t < nU; t++) { rho2[U[t]] = rho[U[t]] + ((Tm >> t & 1) ? 2 : 0); if (rho2[U[t]] >= 1) cj[ncj++] = U[t]; }
        int found = 0;
        for (unsigned am = 0; am < (1u << ncj); am++) {
            int pos[MAXIT], npos = 0, bad = 0;
            mpz_set(Lv, R384);
            for (int j = 0; j < k; j++) {
                int t_j = -1;
                if (tfix[j] >= 0) t_j = tfix[j];
                else { for (int x = 0; x < ncj; x++) if (cj[x] == j && (am >> x & 1)) t_j = rho2[j]; }
                if (t_j < 0) continue;
                int ps = rep->e[j] + 96 * t_j;
                for (int x = 0; x < npos; x++) if (pos[x] == ps) bad = 1;
                pos[npos++] = ps;
                mpz_set_si(tmp, rep->d[j] - 1); mpz_mul(tmp, tmp, P10[ps]); mpz_add(Lv, Lv, tmp);
            }
            if (bad) continue;
            Co c4; co_init(&c4);
            if (window_cut(&c4, &c3, a, Lv, 384)) {
                rr->full_alive++; found = 1;
                rr_note_nn(rr, &c4);
                char tagb[96]; snprintf(tagb, sizeof tagb, "%s:T=%u,sn=%d,A=%u", tag, Tm, sn, am);
                dump_surv(key, ri, wi, tagb, &c4);
            }
            co_clear(&c4);
        }
        if (found) rr->full_words_alive++;
        co_clear(&c3);
    }
    if (g_brute) {
        if (nit > 24) die("brute384: too many children");
        long passb = 0;
        for (unsigned m = 0; m < (1u << nit); m++) {
            unsigned Tm = m & ((1u << nU) - 1); int sn = (m >> nU) & 1;
            Co c3; co_init(&c3); co_set(&c3, co_in);
            mpz_set(V2, V1); mpz_set_ui(tmp, 0);
            for (int t = 0; t < nU; t++) if (Tm >> t & 1) mpz_add(tmp, tmp, iv[t]);
            mpz_addmul(V2, P192m1, tmp);
            if (sn) { mpz_mul(tmp, P10[nu1], R192); mpz_add(V2, V2, tmp); }
            if (chain_level(&c3, V2, a, 384)) passb++;
            co_clear(&c3);
        }
        g_brute_checked++; g_brute_pass += passb;
        if (passm != passb) { fprintf(stderr, "BRUTE384 MISMATCH: MITM %ld passing, brute %ld passing (nU=%d)\n", passm, passb, nU); exit(5); }
    }
    mpz_clears(V2, tmp, R192, R384, Lv, P192m1, NULL);
    free(cands.v);
    }
out_iv:
    for (int t = 0; t < nU; t++) mpz_clear(iv[t]);
}

/* the 384 step exactly as shadowcert.py: fixed V at the four level-384 primes, copy-2 window subsets, no K=192 window */
static void lift384_faithful(const char *key, int ri, int wi, const Co *co1, unsigned fixedmask, const mpz_t V, int a,
                             const Rep *rep, mpz_t *w, RepRes *rr, int count_only) {
    int k = rep->n;
    Co c2; co_init(&c2); co_set(&c2, co1);
    if (!chain_level(&c2, V, a, 384)) { co_clear(&c2); return; }
    int U[MAXIT], nU = 0;
    for (int j = 0; j < k; j++) if (!(fixedmask >> j & 1)) U[nU++] = j;
    if (nU > 26) { rr->budget = 1; co_clear(&c2); return; }
    mpz_t R384, Lv, tmp; mpz_inits(R384, Lv, tmp, NULL);
    mpz_sub_ui(R384, P10[384], 1); mpz_divexact_ui(R384, R384, 9);
    int found = 0;
    for (unsigned am = 0; am < (1u << nU); am++) {
        int bad = 0;
        for (int x = 0; x < nU && !bad; x++) if (am >> x & 1) for (int y = x + 1; y < nU; y++) if ((am >> y & 1) && rep->e[U[x]] == rep->e[U[y]]) { bad = 1; break; }
        if (bad) continue;
        mpz_set(Lv, R384);
        for (int j = 0; j < k; j++) if (fixedmask >> j & 1) mpz_add(Lv, Lv, w[j]);
        mpz_set_ui(tmp, 0);
        for (int x = 0; x < nU; x++) if (am >> x & 1) mpz_add(tmp, tmp, w[U[x]]);
        mpz_addmul(Lv, P10[192], tmp);
        Co c4; co_init(&c4);
        if (window_cut(&c4, &c2, a, Lv, 384)) {
            rr->fv_alive++; found = 1;
            if (!count_only) { rr_note_nn(rr, &c4); dump_surv(key, ri, wi, "faithful", &c4); }
        }
        co_clear(&c4);
    }
    if (found) rr->fv_words_alive++;
    mpz_clears(R384, Lv, tmp, NULL);
    co_clear(&c2);
}

/* ---------------------------------------------------------------- one representation */
static FILE *g_dump;
static void json_word(FILE *f, int wi, unsigned fixedmask, int k, const Co *c, int last) {
    char *a = mpz_get_str(NULL, 10, c->v0b), *b = mpz_get_str(NULL, 10, c->v0c), *c1 = mpz_get_str(NULL, 10, c->u1b),
         *c2 = mpz_get_str(NULL, 10, c->u1c), *c3 = mpz_get_str(NULL, 10, c->u2b), *c4 = mpz_get_str(NULL, 10, c->u2c);
    fprintf(f, "{\"id\":\"w%d\",\"fixed\":[", wi);
    int first = 1;
    for (int j = 0; j < k; j++) if (fixedmask >> j & 1) { fprintf(f, "%s%d", first ? "" : ",", j); first = 0; }
    fprintf(f, "],\"offset\":[\"%s\",\"%s\"],\"basis\":[[\"%s\",\"%s\"],[\"%s\",\"%s\"]]}%s", a, b, c1, c2, c3, c4, last ? "" : ",");
    free(a); free(b); free(c1); free(c2); free(c3); free(c4);
}

static void run_rep(const char *key, int ri, const Rep *rep, const Co *co0, int a, long maxcases, RepRes *rr, const mpz_t Ubound, const Case *cs) {
    int k = rep->n, nu = rep->nu;
    DC s; dc_init(&s, rep, co0);
    dc_stage(&s, a, maxcases);
    if (s.budget) { rr->budget = 1; dc_free(&s); return; }
    rr->nwords = s.nsv;
    for (int wi = 0; wi < s.nsv; wi++) {
        int r = 0; for (int j = 0; j < k; j++) if (s.sv[wi].t[j] < 0) r++;
        if (r < rr->rmin) rr->rmin = r;
        if (r > rr->rmax) rr->rmax = r;
        rr->sum2r1 += ldexp(1.0, r + 1);
        rr->hist[r]++;
    }
    if (s.nsv == 0 || (g_stats_only && !g_dump)) { dc_free(&s); return; }
    mpz_t w[MAXIT], V, tmp;
    mpz_init(V); mpz_init(tmp);
    for (int j = 0; j < k; j++) { mpz_init(w[j]); mpz_set_si(w[j], rep->d[j] - 1); mpz_mul(w[j], w[j], P10[rep->e[j]]); }
    mpz_sub_ui(V, P10[nu], 1); mpz_divexact_ui(V, V, 9);
    for (int j = 0; j < k; j++) mpz_add(V, V, w[j]);
    unsigned *fmask = malloc((s.nsv + 1) * sizeof(unsigned));
    for (int wi = 0; wi < s.nsv; wi++) { unsigned m = 0; for (int j = 0; j < k; j++) if (s.sv[wi].t[j] >= 0) m |= 1u << j; fmask[wi] = m; }
    if (g_dump) {
        fprintf(g_dump, "{\"id\":\"%s#%d\",\"modulus\":148417,\"a\":\"%d\",\"nu\":\"%d\",\"min_digits\":\"384\",\"digits\":[", key, ri, a, nu);
        for (int j = 0; j < k; j++) fprintf(g_dump, "%s{\"d\":%d,\"e\":%d}", j ? "," : "", rep->d[j], rep->e[j]);
        char *us = mpz_get_str(NULL, 10, Ubound);
        fprintf(g_dump, "],\"upper_digits\":\"%s\",\"words\":[", us); free(us);
        for (int wi = 0; wi < s.nsv; wi++) json_word(g_dump, wi, fmask[wi], k, &s.sv[wi].co, wi == s.nsv - 1);
        fprintf(g_dump, "]}\n");
    }
    if (g_stats_only) goto cleanup;

    /* representation-level data for the level-192 DP */
    u64 PT = g_PT;
    u64 val[MAXIT + 2];
    for (int j = 0; j < k; j++) val[j] = mpz_fdiv_ui(w[j], PT);
    {
        u64 ex = 0;
        if (!g_mut_nonu) ex = mulm(mpz_fdiv_ui(P10[nu], PT), invm_gen(9, PT), PT);
        val[k] = ex;
    }
    dp_build(val, k + 1);
    SolList zero = {0, 0, 0}; SolList tl = {0, 0, 0};
    dp_solutions(0, k, &zero);
    long nz = 0;
    for (long i = 0; i < zero.n; i++) if (!(zero.v[i].mask == 0 && zero.v[i].sn == 0)) nz++;
    rr->ncand_dp = nz;

    mpz_t R192, Lv, V1; mpz_inits(R192, Lv, V1, NULL);
    mpz_sub_ui(R192, P10[192], 1); mpz_divexact_ui(R192, R192, 9);
    LP *P193 = lp_find(193), *P769 = lp_find(769);
    mpz_t m96; mpz_init(m96); mpz_sub_ui(m96, P10[96], 1);
    for (int wi = 0; wi < s.nsv; wi++) {
        const Co *wc = &s.sv[wi].co; unsigned fx = fmask[wi];
        const Co *la = lam_a(a);
        mpz_t cont; mpz_init(cont); co_content(cont, wc);
        if (!mpz_divisible_ui_p(cont, 768)) rr->content_fail++;
        mpz_clear(cont);
        if (!lattice_same(wc, la)) rr->lat_mismatch++;
        if (!basis_trivial_at(wc, 193) || !basis_trivial_at(wc, 769)) { rr->nonappl++; continue; }
        u64 tau = 0;
        {
            u64 tp[2]; LP *PP[2] = {P193, P769};
            for (int t = 0; t < 2; t++) {
                u64 p = PP[t]->p, n = p - 1;
                u64 T = mulm(mulm(powm(2, a, p), powm(3, mpz_fdiv_ui(wc->v0b, n), p), p), powm(7, mpz_fdiv_ui(wc->v0c, n), p), p);
                u64 Vp = mpz_fdiv_ui(V, p);
                u64 den = (mpz_fdiv_ui(m96, p));
                tp[t] = mulm((T + p - Vp) % p, invm_gen(den, p), p);
            }
            u64 tt = mulm((tp[1] + 769 - tp[0] % 769) % 769, invm_gen(193 % 769, 769), 769);
            tau = tp[0] + 193 * tt;
            if (g_mut_wrongmod) tau = 0;
        }
        const SolList *sol = &zero;
        if (tau != 0 && !g_mut_wrongmod) { dp_solutions(tau, k, &tl); sol = &tl; rr->nwords_tau_nonzero++; }
        for (long ci = 0; ci < sol->n; ci++) {
            unsigned Sm = sol->v[ci].mask; int sn = sol->v[ci].sn;
            if (Sm == 0 && sn == 0) continue;
            if (Sm & fx) continue;
            rr->ncand_tested++;
            mpz_set(V1, V);
            mpz_set_ui(tmp, 0);
            for (int j = 0; j < k; j++) if (Sm >> j & 1) mpz_add(tmp, tmp, w[j]);
            mpz_addmul(V1, m96, tmp);
            if (sn) { mpz_t r; mpz_init(r); mpz_sub_ui(r, P10[96], 1); mpz_divexact_ui(r, r, 9); mpz_mul(r, r, P10[nu]); mpz_add(V1, V1, r); mpz_clear(r); }
            Co c1; co_init(&c1); co_set(&c1, wc);
            if (chain_level(&c1, V1, a, 192)) {
                if (g_faithful) { rr->nextra++; }
                else {
                    int Sl[MAXIT], nS = 0; for (int j = 0; j < k; j++) if (Sm >> j & 1) Sl[nS++] = j;
                    for (unsigned cb = 0; cb < (1u << nS); cb++) {
                        int bad = 0;
                        for (int x = 0; x < nS && !bad; x++) if (cb >> x & 1) for (int y = x + 1; y < nS; y++) if ((cb >> y & 1) && rep->e[Sl[x]] == rep->e[Sl[y]]) { bad = 1; break; }
                        if (bad) continue;
                        mpz_set(Lv, R192);
                        for (int j = 0; j < k; j++) if (fx >> j & 1) mpz_add(Lv, Lv, w[j]);
                        mpz_set_ui(tmp, 0);
                        for (int x = 0; x < nS; x++) if (cb >> x & 1) mpz_add(tmp, tmp, w[Sl[x]]);
                        mpz_addmul(Lv, P10[96], tmp);
                        Co c2; co_init(&c2);
                        if (window_cut(&c2, &c1, a, Lv, 192)) {
                            rr->nextra++;
                            if (g_trace) fprintf(stderr, "CHILD192 key=[%s] rep=%d word=%d S=0x%x sn=%d cbits=0x%x tau=%llu\n", key, ri, wi, Sm, sn, cb, (unsigned long long)tau);
                            int tfix[MAXIT], rho[MAXIT];
                            for (int j = 0; j < k; j++) { tfix[j] = (fx >> j & 1) ? 0 : -1; rho[j] = 0; }
                            for (int x = 0; x < nS; x++) { if (cb >> x & 1) tfix[Sl[x]] = 1; else rho[Sl[x]] = 1; }
                            lift384_state(key, ri, wi, &c2, tfix, rho, V1, nu + 96 * sn, a, rep, w, rr, "child");
                        }
                        co_clear(&c2);
                    }
                }
            }
            co_clear(&c1);
        }
        /* the shadow: all unplaced digits at even copies */
        Co c1; co_init(&c1); co_set(&c1, wc);
        int alive192 = chain_level(&c1, V, a, 192);
        if (!alive192) { rr->shadow192_dead++; co_clear(&c1); continue; }
        if (g_faithful) {
            lift384_faithful(key, ri, wi, &c1, fx, V, a, rep, w, rr, 0);
            co_clear(&c1);
            continue;
        }
        mpz_set(Lv, R192);
        for (int j = 0; j < k; j++) if (fx >> j & 1) mpz_add(Lv, Lv, w[j]);
        Co c2; co_init(&c2);
        if (g_diag) lift384_faithful(key, ri, wi, &c1, fx, V, a, rep, w, rr, 1);
        if (!window_cut(&c2, &c1, a, Lv, 192)) { rr->shadow192_win_dead++; co_clear(&c1); co_clear(&c2); continue; }
        {
            int tfix[MAXIT], rho[MAXIT];
            for (int j = 0; j < k; j++) { tfix[j] = (fx >> j & 1) ? 0 : -1; rho[j] = 0; }
            lift384_state(key, ri, wi, &c2, tfix, rho, V, nu, a, rep, w, rr, "shadow");
        }
        co_clear(&c1); co_clear(&c2);
    }
    mpz_clears(R192, Lv, V1, m96, NULL);
    free(zero.v); free(tl.v);
cleanup:
    for (int j = 0; j < k; j++) mpz_clear(w[j]);
    mpz_clears(V, tmp, NULL);
    free(fmask);
    dc_free(&s);
}


static int cmd_dptest(int argc, char **argv) {
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--mutant")) {
            const char *m = argv[++i];
            if (!strcmp(m, "noNu")) g_mut_nonu = 1; else if (!strcmp(m, "wrongmod")) { g_mut_wrongmod = 1; g_PT = 193ULL * 773ULL; } else die("unknown mutant");
        }
    }
    init_tables();
    char line[8192];
    while (fgets(line, sizeof line, stdin)) {
        int nu, k, off, n;
        if (sscanf(line, "%d %d%n", &nu, &k, &off) != 2) continue;
        int d[MAXIT], e[MAXIT];
        for (int j = 0; j < k; j++) { if (sscanf(line + off, "%d %d%n", &d[j], &e[j], &n) != 2) die("dptest: bad line"); off += n; }
        u64 val[MAXIT + 2];
        for (int j = 0; j < k; j++) { mpz_t t; mpz_init(t); mpz_set_si(t, d[j] - 1); mpz_mul(t, t, P10[e[j]]); val[j] = mpz_fdiv_ui(t, g_PT); mpz_clear(t); }
        val[k] = g_mut_nonu ? 0 : mulm(mpz_fdiv_ui(P10[nu], g_PT), invm_gen(9, g_PT), g_PT);
        dp_build(val, k + 1);
        SolList sl = {0, 0, 0};
        dp_solutions(0, k, &sl);
        printf("%ld", sl.n);
        for (long i = 0; i < sl.n; i++) printf(" %u:%d", sl.v[i].mask, sl.v[i].sn);
        printf("\n");
        free(sl.v);
    }
    return 0;
}

static int cmd_shadow(int argc, char **argv) {
    const char *lat = NULL, *cases = NULL, *only = NULL, *tsv = NULL, *ut = NULL, *lpf = NULL, *statsf = NULL, *dumpf = NULL, *survf = NULL, *repsf = NULL;
    long maxcases = 5000000; int noassert = 0;
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--lattice")) lat = argv[++i];
        else if (!strcmp(argv[i], "--cases")) cases = argv[++i];
        else if (!strcmp(argv[i], "--only")) only = argv[++i];
        else if (!strcmp(argv[i], "--utable")) ut = argv[++i];
        else if (!strcmp(argv[i], "--tsv")) tsv = argv[++i];
        else if (!strcmp(argv[i], "--stats")) statsf = argv[++i];
        else if (!strcmp(argv[i], "--dump")) dumpf = argv[++i];
        else if (!strcmp(argv[i], "--dump-surv")) survf = argv[++i];
        else if (!strcmp(argv[i], "--reps")) repsf = argv[++i];
        else if (!strcmp(argv[i], "--levelprimes")) lpf = argv[++i];
        else if (!strcmp(argv[i], "--maxcases")) maxcases = atol(argv[++i]);
        else if (!strcmp(argv[i], "--faithful")) g_faithful = 1;
        else if (!strcmp(argv[i], "--diag")) g_diag = 1;
        else if (!strcmp(argv[i], "--brute384")) g_brute = 1;
        else if (!strcmp(argv[i], "--trace")) g_trace = 1;
        else if (!strcmp(argv[i], "--stats-only")) g_stats_only = 1;
        else if (!strcmp(argv[i], "--no-assert")) noassert = 1;
        else if (!strcmp(argv[i], "--mutant")) {
            const char *m = argv[++i];
            if (!strcmp(m, "noNu")) g_mut_nonu = 1; else if (!strcmp(m, "wrongmod")) { g_mut_wrongmod = 1; g_PT = 193ULL * 773ULL; }
            else die("unknown mutant");
        }
    }
    if (!lat || !cases || !only || !lpf || (!ut && !g_stats_only)) die("shadow needs --lattice --cases --only --levelprimes --utable");
    load_lattice(lat); if (ut) load_utable(ut);
    load_levelprimes(lpf);
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--use192")) set_use(192, argv[i + 1]);
        if (!strcmp(argv[i], "--use384")) set_use(384, argv[i + 1]);
    }
    double t0 = cpu_s();
    if (!g_stats_only) {
        int nf = run_content_assertions(63, 0);
        printf("CONTENT assertion over a = 0..63: %d failures\n", nf);
        if (nf && !noassert) die("content(Lambda'_a) assertion failed");
    }
    KeySet ks = load_keys(only);
    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");
    FILE *ft = tsv ? fopen(tsv, "w") : NULL;
    FILE *fs = statsf ? fopen(statsf, "w") : NULL;
    FILE *frep = repsf ? fopen(repsf, "w") : NULL;
    if (dumpf) g_dump = fopen(dumpf, "w");
    if (survf) g_surv_out = fopen(survf, "w");
    long nall = 0, nclosed = 0; int tot_content_fail = 0, tot_lat_mismatch = 0, tot_nonappl = 0;
    Case c;
    while (read_case(f, &c)) {
        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey)) { mpz_clear(c.y); continue; }
        nall++;
        mpz_t Ub; mpz_init(Ub);
        double logU = 0;
        if (!g_stats_only) { const mpz_t *U = get_U(c.k, c.a); mpz_set(Ub, *U); logU = mpz_log10d(*U); }
        int a, b, cc;
        if (!factor237(c.y, &a, &b, &cc) || a != c.a) die("anchor is not 2^a 3^b 7^c with the recorded a");
        Co co0; co_init(&co0); co_set(&co0, &g_lam);
        mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, cc); co_babai(&co0);
        RepList reps = {0, 0, 0};
        filtered_reps(&reps, &c);
        char *ys = mpz_get_str(NULL, 10, c.y);
        RepRes tot; rr_init(&tot);
        const char *verdict = NULL;
        int anyextra = 0, anybudget = 0, anynonappl = 0;
        char detail[8192]; size_t dn = 0; detail[0] = 0;
        long totwords = 0;
        for (int ri = 0; ri < reps.n; ri++) {
            RepRes rr; rr_init(&rr);
            run_rep(c.fullkey, ri, &reps.v[ri], &co0, c.a, maxcases, &rr, Ub, &c);
            totwords += rr.nwords;
            if (frep && !g_stats_only && rr.nwords) {
                const char *rv = rr.budget ? "BUDGET" : rr.nonappl ? "NOT_APPLICABLE" : (!rr.have_nn ? "CLOSED_CUT" : (sandwich_closes(rr.nn, Ub) ? "CLOSED_SANDWICH" : "OPEN"));
                char *nns = rr.have_nn ? mpz_get_str(NULL, 10, rr.nn) : strdup("-");
                fprintf(frep, "%s#%d\t%s\t%s\n", c.fullkey, ri, rv, nns); free(nns);
            }
            if (fs) {
                fprintf(fs, "%s\t%d\t%d\t%d\t%d\t%d\t%.0f\t", c.fullkey, ri, c.k, rr.nwords, rr.nwords ? rr.rmin : -1, rr.nwords ? rr.rmax : -1, rr.sum2r1);
                for (int q = 0; q <= c.k; q++) fprintf(fs, "%s%ld", q ? "," : "", rr.hist[q]);
                fprintf(fs, "\n");
            }
            if (!g_stats_only && rr.nwords) {
                dn += snprintf(detail + dn, sizeof detail - dn, "%s(w=%d,cand=%ld/%ld,xtra=%ld,sh192dead=%d,win192dead=%d,n384=%ld/%ld,full=%ld,fv=%ld%s%s)", dn ? " " : "",
                               rr.nwords, rr.ncand_dp, rr.ncand_tested, rr.nextra, rr.shadow192_dead, rr.shadow192_win_dead, rr.n384_cands, rr.n384_pass_primes,
                               rr.full_alive, g_faithful ? rr.fv_alive : rr.fv_alive, rr.nonappl ? ",NONAPPL" : "", rr.budget ? ",BUDGET" : "");
            }
            if (rr.nextra && g_faithful) anyextra = 1;
            if (rr.budget) anybudget = 1;
            if (rr.nonappl) anynonappl = 1;
            tot_content_fail += rr.content_fail; tot_lat_mismatch += rr.lat_mismatch; tot_nonappl += rr.nonappl;
            tot.full_alive += rr.full_alive; tot.fv_alive += rr.fv_alive;
            tot.full_words_alive += rr.full_words_alive; tot.fv_words_alive += rr.fv_words_alive;
            if (rr.have_nn && (!tot.have_nn || mpz_cmp(rr.nn, tot.nn) < 0)) { mpz_set(tot.nn, rr.nn); tot.have_nn = 1; }
            mpz_clear(rr.nn);
        }
        if (g_stats_only) {
            printf("s=%-8s M=%-12s a=%d y=%-11s k=%d reps=%d words=%ld\n", c.s, c.Mstr, c.a, ys, c.k, reps.n, totwords);
        } else {
            char bstr[64] = "";
            int closes = 0;
            if (anybudget) verdict = "BUDGET";
            else if (anynonappl) verdict = "NOTAPPL";
            else if (anyextra) verdict = "EXTRA";
            else if (!tot.have_nn) verdict = "CLOSED-cut";
            else {
                closes = sandwich_closes(tot.nn, Ub);
                fmt_round2(bstr, digits_bound_log10(tot.nn));
                verdict = closes ? "CLOSED-sandwich" : "open";
            }
            int closed = !strcmp(verdict, "CLOSED-cut") || !strcmp(verdict, "CLOSED-sandwich");
            nclosed += closed;
            printf("s=%-8s M=%-12s a=%d y=%-11s k=%d log10 U=%.1f reps=%d words=%ld -> %s%s%s [%s] full=%ld fv=%ld [%.0fs]\n", c.s, c.Mstr, c.a, ys, c.k, logU, reps.n, totwords, verdict,
                   bstr[0] ? " bound 10^(10^" : "", bstr[0] ? bstr : "", detail, tot.full_alive, tot.fv_alive, cpu_s() - t0);
            if (ft) fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t%ld\t%s\t%s\t%ld\t%ld\n", c.fullkey, c.s, c.Mstr, c.a, ys, reps.n, totwords, verdict, bstr, tot.full_alive, tot.fv_alive);
        }
        fflush(stdout);
        free(ys); mpz_clear(tot.nn); mpz_clear(Ub);
        free(reps.v); co_clear(&co0); mpz_clear(c.y);
    }
    if (g_brute) printf("\nbrute384 cross-check: %ld words checked, %ld passing children (MITM set == brute set on every word)\n", g_brute_checked, g_brute_pass);
    if (!g_stats_only) printf("\n%ld of %ld patterns closed by the shadow certificate; content failures %d, lattice mismatches %d, non-applicable words %d; discrete logs %ld [%.0fs]\n", nclosed, nall, tot_content_fail, tot_lat_mismatch, tot_nonappl, g_ndlog, cpu_s() - t0);
    else printf("\n%ld patterns [%.0fs]\n", nall, cpu_s() - t0);
    if (ft) fclose(ft);
    if (fs) fclose(fs);
    if (frep) fclose(frep);
    if (g_dump) fclose(g_dump);
    if (g_surv_out) fclose(g_surv_out);
    return 0;
}

/* ---------------------------------------------------------------- level 480 (x5 over 96) */
typedef struct { int d, e, m, isnu, nc; unsigned char (*n)[5]; u64 *val; } Unit;
typedef struct { Unit u[MAXIT + 1]; int nun; int dunit[MAXIT]; u64 geo[5]; u64 PT; int nT; u64 T[16]; } UnitSet;
typedef struct { int nun; long n, cap; uint32_t *ci; } GList;

static int g_brute480 = 0, g_word_only = -1, g_mut_loosen = 0, g_mut_nonu480 = 0, g_verbose480 = 0;
static const char *g_plantf; static int g_plant_mitm, g_plant_mitm_miss; static u64 g_plant_seed = 88172645463325252ULL;
static FILE *g_wdump; static mpz_t g_Upp;
static u64 g_mut_skipT = 0;
static mpz_t g_y;
static int g_mut_target0 = 0, g_mut_oldtau = 0, g_mut_wrapp1 = 0;
static FILE *g_ptdump;
static long g_bloom_cands, g_true_matches;
static double g_mitm_space, g_mitm_left, g_mitm_right;

static void comps_build(Unit *U) {
    if (U->isnu) U->nc = 5; else U->nc = (U->m + 1) * (U->m + 2) * (U->m + 3) * (U->m + 4) / 24;
    U->n = malloc((size_t)U->nc * 5); U->val = malloc((size_t)U->nc * sizeof(u64));
    if (U->isnu) {
        for (int s = 0; s < 5; s++) { memset(U->n[s], 0, 5); U->n[s][s] = 1; }
        return;
    }
    int c = 0, m = U->m;
    for (int n0 = 0; n0 <= m; n0++) for (int n1 = 0; n1 <= m - n0; n1++) for (int n2 = 0; n2 <= m - n0 - n1; n2++) for (int n3 = 0; n3 <= m - n0 - n1 - n2; n3++) {
        U->n[c][0] = n0; U->n[c][1] = n1; U->n[c][2] = n2; U->n[c][3] = n3; U->n[c][4] = m - n0 - n1 - n2 - n3; c++;
    }
    if (c != U->nc) die("comps_build: composition count mismatch");
}
static void unitset_free(UnitSet *S) {
    for (int i = 0; i < S->nun; i++) { free(S->u[i].n); free(S->u[i].val); }
    S->nun = 0;
}
static int unitset_build(UnitSet *S, const Rep *rep, int nu) {
    memset(S, 0, sizeof *S);
    int k = rep->n;
    for (int j = 0; j < k; j++) {
        int f = -1;
        for (int i = 0; i < S->nun; i++) if (S->u[i].d == rep->d[j] && S->u[i].e == rep->e[j]) f = i;
        if (f < 0) { f = S->nun++; S->u[f].d = rep->d[j]; S->u[f].e = rep->e[j]; S->u[f].m = 0; S->u[f].isnu = 0; }
        S->u[f].m++; S->dunit[j] = f;
    }
    int nuu = S->nun++;
    S->u[nuu].isnu = 1; S->u[nuu].m = 1; S->u[nuu].d = 0; S->u[nuu].e = 0;
    return nuu;
}
static void unitset_vals(UnitSet *S, const Rep *rep, int nu, u64 PT) {
    S->PT = PT;
    u64 Q = mpz_fdiv_ui(P10[LMAX], PT);
    u64 base = (Q + PT - 1) % PT, binv = invm_gen(base, PT);
    u64 pw = 1;
    for (int s = 0; s < 5; s++) { S->geo[s] = mulm((pw + PT - 1) % PT, binv, PT); pw = mulm(pw, Q, PT); }
    u64 inv9 = invm_gen(9, PT);
    u64 nuterm = g_mut_nonu480 ? 0 : mulm(mpz_fdiv_ui(P10[nu], PT), inv9, PT);
    for (int i = 0; i < S->nun; i++) {
        Unit *U = &S->u[i];
        comps_build(U);
        u64 A = U->isnu ? nuterm : mulm((u64)(U->d - 1) % PT, mpz_fdiv_ui(P10[U->e], PT), PT);
        for (int c = 0; c < U->nc; c++) {
            u64 sg = 0;
            for (int s = 0; s < 5; s++) sg = (sg + (u64)U->n[c][s] * S->geo[s]) % PT;
            U->val[c] = mulm(A, sg, PT);
        }
    }
}

typedef void (*cbfn)(u64 sum, u64 idx, void *ctx);
static void enum_space(const UnitSet *S, const int *us, int n, cbfn cb, void *ctx) {
    u64 P = S->PT;
    if (n == 0) { cb(0, 0, ctx); return; }
    int dig[MAXIT + 2]; u64 part[MAXIT + 3];
    for (int i = 0; i < n; i++) dig[i] = 0;
    part[n] = 0;
    for (int i = n - 1; i >= 1; i--) { u64 s = part[i + 1] + S->u[us[i]].val[0]; if (s >= P) s -= P; part[i] = s; }
    const Unit *U0 = &S->u[us[0]];
    u64 idx = 0;
    for (;;) {
        u64 base = (n > 1) ? part[1] : 0;
        for (int c = 0; c < U0->nc; c++) { u64 s = base + U0->val[c]; if (s >= P) s -= P; cb(s, idx++, ctx); }
        int j = 1;
        while (j < n) { dig[j]++; if (dig[j] < S->u[us[j]].nc) break; dig[j] = 0; j++; }
        if (j >= n) break;
        for (int i = j; i >= 1; i--) { u64 s = part[i + 1] + S->u[us[i]].val[dig[i]]; if (s >= P) s -= P; part[i] = s; }
    }
}
static void decode_idx(const UnitSet *S, const int *us, int n, u64 idx, uint32_t *ci) {
    for (int i = 0; i < n; i++) { int nc = S->u[us[i]].nc; ci[us[i]] = (uint32_t)(idx % (u64)nc); idx /= (u64)nc; }
}
static void gl_push(GList *g, const uint32_t *ci) {
    if (g->n == g->cap) { g->cap = g->cap ? 2 * g->cap : 64; g->ci = realloc(g->ci, (size_t)g->cap * g->nun * sizeof(uint32_t)); }
    memcpy(g->ci + (size_t)g->n * g->nun, ci, (size_t)g->nun * sizeof(uint32_t)); g->n++;
}

typedef struct { u64 *bits; int nb; } Bloom;
static const u64 BC1 = 0x9E3779B97F4A7C15ULL, BC2 = 0xC2B2AE3D27D4EB4FULL, BC3 = 0x165667B19E3779F9ULL;
static inline u64 bl_h(u64 x, u64 c, int nb) { return ((x ^ (x >> 29)) * c) >> (64 - nb); }
static void cb_bloom(u64 s, u64 idx, void *c) {
    Bloom *b = c; u64 h;
    h = bl_h(s, BC1, b->nb); b->bits[h >> 6] |= 1ULL << (h & 63);
    h = bl_h(s, BC2, b->nb); b->bits[h >> 6] |= 1ULL << (h & 63);
    h = bl_h(s, BC3, b->nb); b->bits[h >> 6] |= 1ULL << (h & 63);
}
typedef struct { u64 ridx, need; } Cand;
typedef struct { u64 x, lidx; } LM;
static int cmp_cand(const void *x, const void *y) {
    const Cand *a = x, *b = y;
    if (a->need != b->need) return a->need < b->need ? -1 : 1;
    return a->ridx < b->ridx ? -1 : a->ridx > b->ridx;
}
static int cmp_lm(const void *x, const void *y) {
    const LM *a = x, *b = y;
    if (a->x != b->x) return a->x < b->x ? -1 : 1;
    return a->lidx < b->lidx ? -1 : a->lidx > b->lidx;
}
typedef struct { u64 *tab; int nb; LM *m; long n, cap; } VCtx;
static void cb_verify(u64 s, u64 idx, void *c) {
    VCtx *v = c;
    u64 mask = ((u64)1 << v->nb) - 1, h = bl_h(s, BC1, v->nb);
    while (v->tab[h] != ~0ULL) {
        if (v->tab[h] == s) {
            if (v->n == v->cap) { v->cap = v->cap ? 2 * v->cap : 1024; v->m = realloc(v->m, (size_t)v->cap * sizeof(LM)); }
            v->m[v->n].x = s; v->m[v->n].lidx = idx; v->n++;
            return;
        }
        h = (h + 1) & mask;
    }
}
static void cb_collect_inner(u64 s, u64 idx, void *c) { ((u64 *)c)[idx] = s; }

static int mitm480(const UnitSet *S, GList *G, u64 target) {
    int nun = S->nun; u64 P = S->PT;
    G->nun = nun; G->n = 0;
    int ord[MAXIT + 1];
    for (int i = 0; i < nun; i++) ord[i] = i;
    for (int i = 1; i < nun; i++) { int x = ord[i], j = i - 1; while (j >= 0 && S->u[ord[j]].nc < S->u[x].nc) { ord[j + 1] = ord[j]; j--; } ord[j + 1] = x; }
    double tot = 1; for (int i = 0; i < nun; i++) tot *= S->u[i].nc;
    g_mitm_space = tot;
    if (tot > 6e16) return 1;
    double lcap = sqrt(tot) * 4; if (lcap > 6e7) lcap = 6e7; if (lcap < 1) lcap = 1;
    int L[MAXIT + 1], R[MAXIT + 1], nL = 0, nR = 0; u64 NL = 1, NR = 1;
    for (int t = 0; t < nun; t++) {
        int u = ord[t];
        if ((double)NL * S->u[u].nc <= lcap) { L[nL++] = u; NL *= S->u[u].nc; } else { R[nR++] = u; NR *= S->u[u].nc; }
    }
    g_mitm_left = (double)NL; g_mitm_right = (double)NR;
    if ((double)NR > 5e9) return 1;
    u64 NI = 1; int RU[MAXIT + 1], nRU = 0;
    for (int t = 0; t < nR; t++) { if (NI * S->u[R[t]].nc <= (1u << 20)) { RU[nRU++] = R[t]; NI *= S->u[R[t]].nc; } }
    int RO[MAXIT + 1], nRO = 0; u64 NO = 1;
    for (int t = 0; t < nR; t++) { int in = 0; for (int q = 0; q < nRU; q++) if (RU[q] == R[t]) in = 1; if (!in) { RO[nRO++] = R[t]; NO *= S->u[R[t]].nc; } }
    int RA[MAXIT + 1], nRA = 0;
    for (int t = 0; t < nRU; t++) RA[nRA++] = RU[t];
    for (int t = 0; t < nRO; t++) RA[nRA++] = RO[t];

    int nb = 16; while (((u64)1 << nb) < NL * 40 && nb < 31) nb++;
    Bloom bl; bl.nb = nb; bl.bits = calloc(((u64)1 << nb) / 64 + 1, 8);
    if (!bl.bits) die("mitm480: cannot allocate the Bloom filter");
    enum_space(S, L, nL, cb_bloom, &bl);

    u64 *tin = malloc(NI * sizeof(u64)), *tout = malloc(NO * sizeof(u64));
    enum_space(S, RU, nRU, cb_collect_inner, tin);
    enum_space(S, RO, nRO, cb_collect_inner, tout);

    Cand *cands = NULL; long ncand = 0, capc = 0;
    for (u64 o = 0; o < NO; o++) {
        u64 base = tout[o];
        for (u64 i0 = 0; i0 < NI; i0 += 32) {
            int m = (int)(NI - i0 < 32 ? NI - i0 : 32);
            u64 need[32], h1[32];
            for (int t = 0; t < m; t++) {
                u64 s = base + tin[i0 + t]; if (s >= P) s -= P;
                need[t] = target >= s ? target - s : target + P - s;
                h1[t] = bl_h(need[t], BC1, nb);
                __builtin_prefetch(&bl.bits[h1[t] >> 6]);
            }
            for (int t = 0; t < m; t++) {
                if (!(bl.bits[h1[t] >> 6] >> (h1[t] & 63) & 1)) continue;
                u64 h2 = bl_h(need[t], BC2, nb); if (!(bl.bits[h2 >> 6] >> (h2 & 63) & 1)) continue;
                u64 h3 = bl_h(need[t], BC3, nb); if (!(bl.bits[h3 >> 6] >> (h3 & 63) & 1)) continue;
                if (ncand == capc) { capc = capc ? 2 * capc : 1 << 16; cands = realloc(cands, (size_t)capc * sizeof(Cand)); if (capc > (1L << 26)) die("mitm480: candidate list too large"); }
                cands[ncand].ridx = o * NI + i0 + t; cands[ncand].need = need[t]; ncand++;
            }
        }
    }
    free(bl.bits); free(tin); free(tout);
    g_bloom_cands = ncand;
    VCtx vc; vc.nb = 16; while (((u64)1 << vc.nb) < (u64)ncand * 4 + 16) vc.nb++;
    vc.tab = malloc(((size_t)1 << vc.nb) * sizeof(u64)); for (size_t i = 0; i < ((size_t)1 << vc.nb); i++) vc.tab[i] = ~0ULL;
    vc.m = NULL; vc.n = vc.cap = 0;
    for (long i = 0; i < ncand; i++) {
        u64 mask = ((u64)1 << vc.nb) - 1, h = bl_h(cands[i].need, BC1, vc.nb);
        int have = 0;
        while (vc.tab[h] != ~0ULL) { if (vc.tab[h] == cands[i].need) { have = 1; break; } h = (h + 1) & mask; }
        if (!have) vc.tab[h] = cands[i].need;
    }
    enum_space(S, L, nL, cb_verify, &vc);
    free(vc.tab);
    qsort(vc.m, (size_t)vc.n, sizeof(LM), cmp_lm);
    qsort(cands, (size_t)ncand, sizeof(Cand), cmp_cand);
    uint32_t *ci = malloc((size_t)nun * sizeof(uint32_t));
    long nsol = 0;
    for (long i = 0; i < ncand; i++) {
        long lo = 0, hi = vc.n;
        while (lo < hi) { long mid = (lo + hi) / 2; if (vc.m[mid].x < cands[i].need) lo = mid + 1; else hi = mid; }
        for (long q = lo; q < vc.n && vc.m[q].x == cands[i].need; q++) {
            decode_idx(S, L, nL, vc.m[q].lidx, ci);
            decode_idx(S, RA, nRA, cands[i].ridx, ci);
            gl_push(G, ci); nsol++;
        }
    }
    g_true_matches = nsol;
    free(ci); free(vc.m); free(cands);
    return 0;
}

static int g_cmpw;
static int cmp_row(const void *a, const void *b) { return memcmp(a, b, (size_t)g_cmpw * 4); }
typedef struct { u64 *idx; long n, cap; } IdxList;
static u64 g_brute_target; static double g_brute_max = 1.2e9;
static void cb_zero(u64 s, u64 idx, void *c) {
    IdxList *l = c;
    if (s != g_brute_target) return;
    if (l->n == l->cap) { l->cap = l->cap ? 2 * l->cap : 64; l->idx = realloc(l->idx, (size_t)l->cap * sizeof(u64)); }
    l->idx[l->n++] = idx;
}
static int brute480(const UnitSet *S, const GList *G, u64 target) {
    int nun = S->nun;
    g_brute_target = target;
    int all[MAXIT + 1]; for (int i = 0; i < nun; i++) all[i] = i;
    IdxList il = {0, 0, 0};
    enum_space(S, all, nun, cb_zero, &il);
    GList B; B.nun = nun; B.n = 0; B.cap = 0; B.ci = NULL;
    uint32_t *ci = malloc((size_t)nun * 4);
    for (long i = 0; i < il.n; i++) { decode_idx(S, all, nun, il.idx[i], ci); gl_push(&B, ci); }
    free(ci); free(il.idx);
    int same = (B.n == G->n);
    if (same) {
        g_cmpw = nun;
        qsort(B.ci, (size_t)B.n, (size_t)nun * 4, cmp_row);
        uint32_t *c2 = malloc((size_t)G->n * nun * 4); memcpy(c2, G->ci, (size_t)G->n * nun * 4);
        qsort(c2, (size_t)G->n, (size_t)nun * 4, cmp_row);
        same = memcmp(B.ci, c2, (size_t)B.n * nun * 4) == 0;
        free(c2);
    }
    if (!same) fprintf(stderr, "BRUTE480 MISMATCH: brute %ld solutions, MITM %ld\n", B.n, G->n);
    free(B.ci);
    return same ? 0 : 1;
}

typedef struct {
    int nwords, nonappl, taubad, budget, nT, nun, shadow_ok;
    double space; long nG, compat, passchain, nwin, alive, wordsalive, notshadow_compat, notshadow_alive, win_budget;
    int have_nn; mpz_t nn; long wrap;
} R480;
static void r480_init(R480 *r) { memset(r, 0, sizeof *r); mpz_init(r->nn); }

typedef struct { mpz_t V; int shadow; int sn; u64 tgt[64]; unsigned char ts[64]; mpz_t btgt[4]; unsigned char bts[4]; } GInfo;

static char g_killer[96];
static u64 g_filter480[16]; static int g_nfilter480;
static int chain480(Co *c, GInfo *gi, int a) {
    for (int i = 0; i < g_nlp; i++) {
        LP *P = &g_lp[i];
        if (P->L != 480 || !P->on) continue;
        if (!gi->ts[i]) {
            u64 vm = mpz_fdiv_ui(gi->V, P->p);
            if (vm == 0) gi->ts[i] = 2; else { gi->tgt[i] = tgt_for(P, vm, a); gi->ts[i] = 1; }
        }
        if (gi->ts[i] == 2) { snprintf(g_killer, sizeof g_killer, "%llu(V=0)", (unsigned long long)P->p); return 0; }
        if (!cut_lp_tgt(c, P, gi->tgt[i])) { snprintf(g_killer, sizeof g_killer, "%llu", (unsigned long long)P->p); return 0; }
    }
    for (int i = 0; i < g_nbp; i++) {
        BP *B = &g_bp[i];
        if (B->L != 480 || !B->on) continue;
        if (!bp_cut(c, B, gi->V, a, &gi->btgt[i], &gi->bts[i])) { char *ps = mpz_get_str(NULL, 10, B->p); snprintf(g_killer, sizeof g_killer, "%s", ps); free(ps); return 0; }
    }
    return 1;
}

static void run_plants(const char *path, const DC *s, int a, const mpz_t Upp) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open plants file");
    char *line = NULL; size_t cap = 0; int n = 0, refused = 0, negok = 0;
    while (getline(&line, &cap, f) > 0) {
        int wi; char sb[600], sc[600], sU[600], sL[1400];
        if (sscanf(line, "%d %599s %599s %599s %1399s", &wi, sb, sc, sU, sL) != 5) continue;
        if (wi < 0 || wi >= s->nsv) die("plants: word index out of range");
        mpz_t b, c, U, Lv, nn, pb, pc, tg, t2; mpz_inits(b, c, U, Lv, nn, pb, pc, tg, t2, NULL);
        mpz_set_str(b, sb, 10); mpz_set_str(c, sc, 10); mpz_set_str(U, sU, 10); mpz_set_str(Lv, sL, 10);
        const Co *wc = &s->sv[wi].co;
        int inword = co_contains(wc, b, c);
        Co cc; co_init(&cc); co_set(&cc, wc);
        int alive = 1; char killer[64] = "";
        for (int i = 0; i < g_nlp && alive; i++) {
            LP *P = &g_lp[i];
            if (P->L != 480 || !P->on) continue;
            u64 m = P->p - 1;
            u64 t = (u64)(((u128)mpz_fdiv_ui(b, m) * P->l3 + (u128)mpz_fdiv_ui(c, m) * P->l7) % m);
            if (!cut_lp_tgt(&cc, P, t)) { alive = 0; snprintf(killer, sizeof killer, "%llu", (unsigned long long)P->p); }
        }
        for (int i = 0; i < g_nbp && alive; i++) {
            BP *B = &g_bp[i];
            if (B->L != 480 || !B->on) continue;
            mpz_mul(tg, b, B->l3); mpz_addmul(tg, c, B->l7); mpz_mod(tg, tg, B->pm1);
            if (!co_intersect(&cc, &cc, B->l3, B->l7, tg, B->pm1)) { alive = 0; snprintf(killer, sizeof killer, "big"); }
        }
        Co c4; co_init(&c4);
        int win = alive ? window_cut(&c4, &cc, a, Lv, 480) : 0;
        int has = 0, hasp = 0, closes = 0, closesU = 0, le = 0;
        if (win) {
            co_nearest(&c4, nn, pb, pc);
            has = co_contains(&c4, b, c);
            mpz_add_ui(t2, b, 1); hasp = co_contains(&c4, t2, c);
            closes = sandwich_closes(nn, U);
            closesU = sandwich_closes(nn, Upp);
            mpz_mul(t2, b, b); mpz_addmul(t2, c, c); le = mpz_cmp(nn, t2) <= 0;
        }
        int ref = win && has && !closes && le;
        refused += ref; negok += (win && !hasp);
        n++;
        printf("PLANT %d word=%d point_in_word_coset=%d survives_primes=%d%s%s survives_window=%d contains_point=%d contains_shifted_point=%d nn<=norm=%d closes_at_own_U=%d closes_at_Upp=%d => %s\n",
               n, wi, inword, alive, killer[0] ? " killer=" : "", killer, win, has, hasp, le, closes, closesU, ref ? "REFUSED" : "NOT-REFUSED");
        mpz_clears(b, c, U, Lv, nn, pb, pc, tg, t2, NULL); co_clear(&cc); co_clear(&c4);
    }
    free(line); fclose(f);
    printf("PLANTS %d refused %d, shifted-point control rejected %d\n", n, refused, negok);
}

static void dump_point(const char *key, int ri, int wi, const char *tag, const GInfo *gi, const mpz_t Lv, const Co *c, int a) {
    if (!g_ptdump) return;
    mpz_t nn, pb, pc; mpz_inits(nn, pb, pc, NULL);
    co_nearest(c, nn, pb, pc);
    char *s1 = mpz_get_str(NULL, 10, gi->V), *s2 = mpz_get_str(NULL, 10, Lv), *s3 = mpz_get_str(NULL, 10, nn), *s4 = mpz_get_str(NULL, 10, pb), *s5 = mpz_get_str(NULL, 10, pc);
    fprintf(g_ptdump, "{\"key\":\"%s\",\"rep\":%d,\"word\":%d,\"tag\":\"%s\",\"a\":%d,\"V\":\"%s\",\"Lv\":\"%s\",\"nn\":\"%s\",\"pb\":\"%s\",\"pc\":\"%s\"}\n", key, ri, wi, tag, a, s1, s2, s3, s4, s5);
    free(s1); free(s2); free(s3); free(s4); free(s5);
    mpz_clears(nn, pb, pc, NULL);
}

static void run_rep480(const char *key, int ri, const Rep *rep, const Co *co0, int a, long maxcases, R480 *rr) {
    int k = rep->n, nu = rep->nu;
    for (int j = 0; j < k; j++) if (rep->e[j] < 0 || rep->e[j] >= LMAX) die("shadow480: digit position outside 0..95");
    DC s; dc_init(&s, rep, co0);
    dc_stage(&s, a, maxcases);
    if (s.budget) { rr->budget = 1; dc_free(&s); return; }
    rr->nwords = s.nsv;
    if (s.nsv == 0) { dc_free(&s); return; }

    UnitSet S;
    int nuu = unitset_build(&S, rep, nu);
    u64 Tl[16]; int nT = 0;
    u64 PT = 1;
    for (int i = 0; i < g_nlp; i++) {
        LP *P = &g_lp[i];
        if (P->L != 480 || !P->on) continue;
        if (!basis_trivial_at(&s.sv[0].co, P->p)) continue;
        if (g_mut_skipT == P->p) continue;
        if (g_nfilter480) { int in = 0; for (int q = 0; q < g_nfilter480; q++) if (g_filter480[q] == P->p) in = 1; if (!in) continue; }
        if (nT >= 16 || (double)PT * (double)P->p > 1.8e19) die("shadow480: trivial-image modulus overflows 64 bits");
        Tl[nT++] = P->p; PT *= P->p;
    }
    if (nT == 0) { rr->nonappl++; unitset_free(&S); dc_free(&s); return; }
    rr->nT = nT; rr->nun = S.nun;
    unitset_vals(&S, rep, nu, PT);

    mpz_t w[MAXIT], V, tmp;
    mpz_init(V); mpz_init(tmp);
    for (int j = 0; j < k; j++) { mpz_init(w[j]); mpz_set_si(w[j], rep->d[j] - 1); mpz_mul(w[j], w[j], P10[rep->e[j]]); }
    mpz_sub_ui(V, P10[nu], 1); mpz_divexact_ui(V, V, 9);
    for (int j = 0; j < k; j++) mpz_add(V, V, w[j]);

    mpz_t wrap, R96, wrem;
    mpz_inits(wrap, R96, wrem, NULL);
    mpz_sub_ui(R96, P10[96], 1); mpz_divexact_ui(R96, R96, 9);
    mpz_sub(wrap, V, g_y);
    mpz_tdiv_qr(wrap, wrem, wrap, R96);
    if (mpz_sgn(wrem) != 0 || mpz_sgn(wrap) < 0) die("shadow480: V - y is not a nonnegative multiple of R_96, the representation has no integer wrap");
    rr->wrap = mpz_get_si(wrap);
    int wrap_used = g_mut_wrapp1 ? 1 : 0;

    unsigned *fmask = malloc((s.nsv + 1) * sizeof(unsigned));
    char *wok = calloc(s.nsv + 1, 1);
    for (int wi = 0; wi < s.nsv; wi++) {
        unsigned m = 0; for (int j = 0; j < k; j++) if (s.sv[wi].t[j] >= 0) m |= 1u << j;
        fmask[wi] = m;
        const Co *wc = &s.sv[wi].co;
        int ok = 1;
        for (int i = 0; i < nT; i++) {
            u64 p = Tl[i], n = p - 1;
            if (!basis_trivial_at(wc, p)) ok = 0;
            u64 Tw = mulm(mulm(powm(2, a, p), powm(3, mpz_fdiv_ui(wc->v0b, n), p), p), powm(7, mpz_fdiv_ui(wc->v0c, n), p), p);
            u64 den = mpz_fdiv_ui(P10[96], p); den = (den + p - 1) % p;
            u64 tau_w = mulm((Tw + p - mpz_fdiv_ui(V, p)) % p, invm_gen(den, p), p);
            u64 wm = (mpz_fdiv_ui(wrap, p) + (u64)wrap_used) % p;
            u64 tau_exp = g_mut_oldtau ? 0 : (p - mulm(wm, invm_gen(9, p), p)) % p;
            if (g_mut_oldtau) { if (Tw != mpz_fdiv_ui(V, p)) { rr->taubad++; ok = 0; } }
            else if (tau_w != tau_exp) {
                fprintf(stderr, "shadow480: per-word tau %llu != -w/9 = %llu mod %llu (key=[%s] word=%d wrap=%ld)\n", (unsigned long long)tau_w, (unsigned long long)tau_exp, (unsigned long long)p, key, wi, rr->wrap);
                die("shadow480: per-word tau differs from the wrap target");
            }
        }
        if (!ok) { rr->nonappl++; continue; }
        wok[wi] = 1;
    }

    GList G = {0, 0, 0, NULL};
    double tm0 = cpu_s();
    if (g_wdump) for (int wi = 0; wi < s.nsv; wi++) json_word(g_wdump, wi, fmask[wi], k, &s.sv[wi].co, 1), fputc('\n', g_wdump);
    if (g_plantf) { mpz_t Upp; mpz_init_set(Upp, g_Upp); run_plants(g_plantf, &s, a, Upp); mpz_clear(Upp); }
    for (int pt = 0; pt < g_plant_mitm; pt++) {
        uint32_t *pci = malloc((size_t)S.nun * 4); u64 tgt = 0;
        for (int u = 0; u < S.nun; u++) {
            g_plant_seed ^= g_plant_seed << 13; g_plant_seed ^= g_plant_seed >> 7; g_plant_seed ^= g_plant_seed << 17;
            pci[u] = (uint32_t)(g_plant_seed % (u64)S.u[u].nc);
            tgt = (tgt + S.u[u].val[pci[u]]) % PT;
        }
        GList G2 = {0, 0, 0, NULL};
        if (mitm480(&S, &G2, tgt)) die("plant-mitm: budget");
        int found = 0;
        for (long q = 0; q < G2.n && !found; q++) if (memcmp(G2.ci + (size_t)q * G2.nun, pci, (size_t)S.nun * 4) == 0) found = 1;
        int brute_same = -1;
        if (g_brute480 && g_mitm_space <= g_brute_max) brute_same = brute480(&S, &G2, tgt) == 0;
        printf("PLANT-MITM %d target=%llu solutions=%ld planted_found=%d brute_same=%d (space %.4g, bloom candidates %ld)\n", pt + 1, (unsigned long long)tgt, G2.n, found, brute_same, g_mitm_space, g_bloom_cands);
        if (brute_same == 0) g_plant_mitm_miss++;
        if (!found) g_plant_mitm_miss++;
        free(G2.ci); free(pci);
    }
    u64 tau_true = (PT - mulm(mpz_fdiv_ui(wrap, PT), invm_gen(9, PT), PT)) % PT;
    u64 tau_rep = (g_mut_oldtau || g_mut_target0) ? 0 : tau_true;
    if (mitm480(&S, &G, tau_rep)) { rr->budget = 1; goto cleanup; }
    rr->space = g_mitm_space; rr->nG = G.n;
    if (g_verbose480) fprintf(stderr, "MITM480 key=[%s] rep=%d wrap=%ld target=%llu units=%d space=%.3g left=%.3g right=%.3g bloom_cands=%ld matches=%ld [%.1fs]\n", key, ri, rr->wrap, (unsigned long long)tau_rep, S.nun, g_mitm_space, g_mitm_left, g_mitm_right, g_bloom_cands, g_true_matches, cpu_s() - tm0);
    if (g_brute480) {
        if (g_mitm_space > g_brute_max) die("brute480: space too large");
        if (brute480(&S, &G, tau_true)) die("brute480: MITM set differs from the exhaustive set");
    }

    int nG = (int)G.n;
    GInfo *gis = calloc((size_t)nG + 1, sizeof(GInfo));
    int shadow_found = 0;
    mpz_t Rw, Lv, V2, Rn;
    mpz_inits(Rw, Lv, V2, Rn, NULL);
    mpz_sub_ui(Rw, P10[480], 1); mpz_divexact_ui(Rw, Rw, 9);
    for (int g = 0; g < nG; g++) {
        const uint32_t *ci = G.ci + (size_t)g * G.nun;
        GInfo *gi = &gis[g];
        mpz_init(gi->V); for (int b2 = 0; b2 < 4; b2++) mpz_init(gi->btgt[b2]);
        int sh = 1, sn = 0;
        mpz_set_ui(gi->V, 0);
        for (int u = 0; u < S.nun; u++) {
            const Unit *U = &S.u[u]; const unsigned char *nv = U->n[ci[u]];
            if (U->isnu) { for (int q = 0; q < 5; q++) if (nv[q]) sn = q; if (sn) sh = 0; continue; }
            if (nv[0] != U->m) sh = 0;
            for (int q = 0; q < 5; q++) if (nv[q]) {
                mpz_set_si(tmp, U->d - 1); mpz_mul(tmp, tmp, P10[U->e + 96 * q]); mpz_mul_ui(tmp, tmp, nv[q]); mpz_add(gi->V, gi->V, tmp);
            }
        }
        mpz_sub_ui(Rn, P10[nu + 96 * sn], 1); mpz_divexact_ui(Rn, Rn, 9); mpz_add(gi->V, gi->V, Rn);
        gi->shadow = sh; gi->sn = sn;
        if (sh) shadow_found = 1;
    }
    rr->shadow_ok = shadow_found;
    if (tau_rep == 0 && !shadow_found) die("shadow480: the shadow composition is missing from the zero-sum set");
    if (tau_rep != 0 && shadow_found) die("shadow480: the shadow composition is present at a nonzero target");

    for (int wi = 0; wi < s.nsv; wi++) {
        if (!wok[wi]) continue;
        if (g_word_only >= 0 && wi != g_word_only) continue;
        int fu[MAXIT + 1]; for (int u = 0; u < S.nun; u++) fu[u] = 0;
        for (int j = 0; j < k; j++) if (fmask[wi] >> j & 1) fu[S.dunit[j]]++;
        const Co *wc = &s.sv[wi].co;
        int walive = 0; long wcompat = 0, wchain = 0; g_killer[0] = 0;
        for (int g = 0; g < nG; g++) {
            const uint32_t *ci = G.ci + (size_t)g * G.nun;
            int comp = 1;
            for (int u = 0; u < S.nun && comp; u++) { if (S.u[u].isnu) continue; if (S.u[u].n[ci[u]][0] < fu[u]) comp = 0; }
            if (!comp) continue;
            GInfo *gi = &gis[g];
            rr->compat++; wcompat++; if (!gi->shadow) rr->notshadow_compat++;
            Co c3; co_init(&c3); co_set(&c3, wc);
            if (!chain480(&c3, gi, a)) { co_clear(&c3); continue; }
            rr->passchain++; wchain++;
            int ncell = 0; int cell_e[160], cell_s[160]; int cell_nopt[160]; int cell_u[160][12];
            for (int sg = 1; sg < 5; sg++) {
                for (int u = 0; u < S.nun; u++) {
                    const Unit *U = &S.u[u]; if (U->isnu) continue;
                    if (U->n[ci[u]][sg] == 0) continue;
                    int cidx = -1;
                    for (int x = 0; x < ncell; x++) if (cell_e[x] == U->e && cell_s[x] == sg) cidx = x;
                    if (cidx < 0) { if (ncell >= 160) { rr->win_budget++; cidx = -2; } else { cidx = ncell++; cell_e[cidx] = U->e; cell_s[cidx] = sg; cell_nopt[cidx] = 0; } }
                    if (cidx == -2) break;
                    if (cell_nopt[cidx] >= 12) die("shadow480: too many values in one window cell");
                    cell_u[cidx][cell_nopt[cidx]++] = u;
                }
            }
            double combos = 1; for (int x = 0; x < ncell; x++) combos *= (1 + cell_nopt[x]);
            if (combos > 4e6) { rr->win_budget++; rr->budget = 1; co_clear(&c3); continue; }
            mpz_set(Lv, Rw);
            for (int j = 0; j < k; j++) if (fmask[wi] >> j & 1) mpz_add(Lv, Lv, w[j]);
            int pick[160]; for (int x = 0; x < ncell; x++) pick[x] = 0;
            for (;;) {
                mpz_set(V2, Lv);
                for (int x = 0; x < ncell; x++) if (pick[x]) {
                    const Unit *U = &S.u[cell_u[x][pick[x] - 1]];
                    mpz_set_si(tmp, U->d - 1); mpz_mul(tmp, tmp, P10[U->e + 96 * cell_s[x]]); mpz_add(V2, V2, tmp);
                }
                rr->nwin++;
                Co c4; co_init(&c4);
                if (window_cut(&c4, &c3, a, V2, 480)) {
                    rr->alive++; walive = 1; if (!gi->shadow) rr->notshadow_alive++;
                    mpz_t nn, pb, pc; mpz_inits(nn, pb, pc, NULL);
                    co_nearest(&c4, nn, pb, pc);
                    if (!rr->have_nn || mpz_cmp(nn, rr->nn) < 0) { mpz_set(rr->nn, nn); rr->have_nn = 1; }
                    mpz_clears(nn, pb, pc, NULL);
                    char tg[64]; snprintf(tg, sizeof tg, "g%d%s", g, gi->shadow ? "sh" : "");
                    dump_point(key, ri, wi, tg, gi, V2, &c4, a);
                    dump_surv(key, ri, wi, tg, &c4);
                }
                co_clear(&c4);
                int x = 0;
                while (x < ncell) { if (++pick[x] <= cell_nopt[x]) break; pick[x] = 0; x++; }
                if (x == ncell) break;
            }
            co_clear(&c3);
        }
        if (walive) rr->wordsalive++;
        if (g_verbose480) {
            char fx[128]; int fo = 0; fx[0] = 0;
            for (int j = 0; j < k; j++) if (fmask[wi] >> j & 1) fo += snprintf(fx + fo, sizeof fx - fo, "%s%d@%d", fo ? "," : "", rep->d[j], rep->e[j]);
            fprintf(stderr, "WORD %d fixed=[%s] children=%ld passed_primes=%ld alive=%d%s%s\n", wi, fx, wcompat, wchain, walive, g_killer[0] && !walive ? " last_killer=" : "", walive ? "" : g_killer);
        }
    }
    for (int g = 0; g < nG; g++) { mpz_clear(gis[g].V); for (int b2 = 0; b2 < 4; b2++) mpz_clear(gis[g].btgt[b2]); }
    free(gis);
    mpz_clears(Rw, Lv, V2, Rn, NULL);
cleanup:
    free(G.ci);
    for (int j = 0; j < k; j++) mpz_clear(w[j]);
    mpz_clears(V, tmp, wrap, R96, wrem, NULL);
    free(fmask); free(wok);
    unitset_free(&S);
    (void)nuu;
    dc_free(&s);
}

static void tierc_rep(Rep *r) {
    static const int cls_n[10] = {1, 1, 2, 1, 2, 8, 6, 2, 4, 4};
    static const int cls_d[10][8] = {{3}, {2}, {2, 7}, {2}, {2, 3}, {2, 2, 2, 2, 2, 2, 2, 2}, {2, 2, 2, 2, 2, 2}, {2, 2}, {2, 2, 3, 3}, {2, 3, 3, 3}};
    int d[64], e[64], n = 0;
    for (int c = 0; c < 10; c++) for (int i = 0; i < cls_n[c]; i++) { d[n] = cls_d[c][i]; e[n] = c; n++; }
    for (int i = 1; i < n; i++) { int xd = d[i], xe = e[i], j = i - 1; while (j >= 0 && (d[j] > xd || (d[j] == xd && e[j] > xe))) { d[j + 1] = d[j]; e[j + 1] = e[j]; j--; } d[j + 1] = xd; e[j + 1] = xe; }
    memset(r, 0, sizeof *r);
    r->nu = 2; r->n = n;
    for (int i = 0; i < n; i++) { r->d[i] = d[i]; r->e[i] = e[i]; }
}

static const char *verdict480(const R480 *t, const mpz_t Ub, char *bstr, int *closes) {
    bstr[0] = 0; *closes = 0;
    if (t->budget) return "BUDGET";
    if (t->nonappl) return "NOTAPPL";
    if (!t->have_nn) return "CLOSED-cut";
    mpz_t U; mpz_init_set(U, Ub);
    if (g_mut_loosen) mpz_sub_ui(U, U, 1);
    *closes = sandwich_closes(t->nn, U);
    mpz_clear(U);
    fmt_round2(bstr, digits_bound_log10(t->nn));
    return *closes ? "CLOSED-sandwich" : "open";
}

static int cmd_shadow480(int argc, char **argv) {
    const char *lat = NULL, *cases = NULL, *only = NULL, *tsv = NULL, *ut = NULL, *lpf = NULL, *ptf = NULL, *survf = NULL;
    long maxcases = 5000000; int tierc = 0, no480 = 0; const char *use480 = NULL;
    for (int i = 0; i < argc; i++) {
        if (!strcmp(argv[i], "--lattice")) lat = argv[++i];
        else if (!strcmp(argv[i], "--cases")) cases = argv[++i];
        else if (!strcmp(argv[i], "--only")) only = argv[++i];
        else if (!strcmp(argv[i], "--utable")) ut = argv[++i];
        else if (!strcmp(argv[i], "--tsv")) tsv = argv[++i];
        else if (!strcmp(argv[i], "--levelprimes")) lpf = argv[++i];
        else if (!strcmp(argv[i], "--points")) ptf = argv[++i];
        else if (!strcmp(argv[i], "--dump-surv")) survf = argv[++i];
        else if (!strcmp(argv[i], "--maxcases")) maxcases = atol(argv[++i]);
        else if (!strcmp(argv[i], "--tierc")) tierc = 1;
        else if (!strcmp(argv[i], "--no480")) no480 = 1;
        else if (!strcmp(argv[i], "--brute480")) g_brute480 = 1;
        else if (!strcmp(argv[i], "--brute-max")) g_brute_max = atof(argv[++i]);
        else if (!strcmp(argv[i], "--verbose")) g_verbose480 = 1;
        else if (!strcmp(argv[i], "--word-only")) g_word_only = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--plants")) g_plantf = argv[++i];
        else if (!strcmp(argv[i], "--plant-mitm")) { g_plant_mitm = atoi(argv[++i]); if (i + 1 < argc && argv[i + 1][0] != '-') g_plant_seed ^= strtoull(argv[++i], NULL, 10) * 0x9E3779B97F4A7C15ULL; }
        else if (!strcmp(argv[i], "--dump-words")) g_wdump = fopen(argv[++i], "w");
        else if (!strcmp(argv[i], "--filter480")) {
            char *sl = strdup(argv[++i]), *tok, *q = sl;
            while ((tok = strsep(&q, ",")) != NULL) if (*tok && g_nfilter480 < 16) g_filter480[g_nfilter480++] = strtoull(tok, NULL, 10);
            free(sl);
        }
        else if (!strcmp(argv[i], "--use480")) use480 = argv[++i];
        else if (!strcmp(argv[i], "--mutant")) {
            const char *m = argv[++i];
            if (!strcmp(m, "loosen")) g_mut_loosen = 1;
            else if (!strcmp(m, "noNu480")) g_mut_nonu480 = 1;
            else if (!strcmp(m, "target0")) g_mut_target0 = 1;
            else if (!strcmp(m, "oldtau")) g_mut_oldtau = 1;
            else if (!strcmp(m, "wrapp1")) g_mut_wrapp1 = 1;
            else if (!strncmp(m, "skipT=", 6)) g_mut_skipT = strtoull(m + 6, NULL, 10);
            else if (!strncmp(m, "skipchain=", 10)) continue;
            else die("unknown mutant");
        }
    }
    if (no480) return cmd_shadow(argc, argv);
    if (!lat || !lpf || !ut || (!tierc && (!cases || !only))) die("shadow480 needs --lattice --levelprimes --utable and (--tierc | --cases --only)");
    load_lattice(lat); load_utable(ut);
    load_levelprimes(lpf);
    for (int i = 0; i < argc; i++) if (!strncmp(argv[i], "--mutant", 8) && i + 1 < argc && !strncmp(argv[i + 1], "skipchain=", 10)) {
        u64 p = strtoull(argv[i + 1] + 10, NULL, 10); int hit = 0;
        for (int q = 0; q < g_nlp; q++) if (g_lp[q].L == 480 && g_lp[q].p == p) { g_lp[q].on = 0; hit = 1; }
        if (!hit) die("skipchain names a prime that is not a level-480 prime");
    }
    if (use480) {
        for (int q = 0; q < g_nlp; q++) if (g_lp[q].L == 480) g_lp[q].on = 0;
        for (int q = 0; q < g_nbp; q++) if (g_bp[q].L == 480) g_bp[q].on = 0;
        char *sl = strdup(use480), *tok, *qq = sl;
        while ((tok = strsep(&qq, ",")) != NULL) if (*tok) {
            int hit = 0;
            for (int q = 0; q < g_nlp; q++) if (g_lp[q].L == 480 && g_lp[q].p == strtoull(tok, NULL, 10)) { g_lp[q].on = 1; hit = 1; }
            for (int q = 0; q < g_nbp; q++) { char *ps = mpz_get_str(NULL, 10, g_bp[q].p); if (!strcmp(ps, tok)) { g_bp[q].on = 1; hit = 1; } free(ps); }
            if (!hit) die("--use480 names a prime that is not a level-480 prime");
        }
        free(sl);
    }
    g_dedup = tierc;
    mpz_init(g_Upp); mpz_init(g_y);
    if (ptf) g_ptdump = fopen(ptf, "w");
    if (survf) g_surv_out = fopen(survf, "w");
    FILE *ft = tsv ? fopen(tsv, "w") : NULL;
    double t0 = cpu_s();
    long nall = 0, nclosed = 0;
    if (tierc) {
        Rep rep; tierc_rep(&rep);
        mpz_t y, Ub; mpz_init_set_ui(y, 1); mpz_init(Ub);
        mpz_ui_pow_ui(y, 3, 3); { mpz_t s7; mpz_init(s7); mpz_ui_pow_ui(s7, 7, 10); mpz_mul(y, y, s7); mpz_clear(s7); }
        mpz_set(Ub, *get_U(rep.n, 0)); mpz_set(g_Upp, Ub);
        Co co0; co_init(&co0); co_set(&co0, &g_lam);
        mpz_set_si(co0.v0b, 3); mpz_set_si(co0.v0c, 10); co_babai(&co0);
        char *ys = mpz_get_str(NULL, 10, y);
        printf("tierc pattern: y=%s a=0 b=3 c=10 k=%d nu=%d log10 U''=%.4f\n", ys, rep.n, rep.nu, mpz_log10d(Ub));
        mpz_set(g_y, y);
        R480 rr; r480_init(&rr);
        run_rep480("tierc k31 3^3 7^10", 0, &rep, &co0, 0, maxcases, &rr);
        char bstr[64]; int closes;
        const char *vd = verdict480(&rr, Ub, bstr, &closes);
        printf("rep0: words=%d (notappl=%d taubad=%d) T=%d units=%d space=%.4g |G|=%ld shadow=%d compat(word,child)=%ld notshadow_compat=%ld passchain=%ld windows=%ld alive=%ld wordsalive=%ld notshadow_alive=%ld win_budget=%ld\n",
               rr.nwords, rr.nonappl, rr.taubad, rr.nT, rr.nun, rr.space, rr.nG, rr.shadow_ok, rr.compat, rr.notshadow_compat, rr.passchain, rr.nwin, rr.alive, rr.wordsalive, rr.notshadow_alive, rr.win_budget);
        if (rr.have_nn) { char *nns = mpz_get_str(NULL, 10, rr.nn); printf("min nn=%.60s... (%zu digits)\n", nns, strlen(nns)); free(nns); }
        printf("VERDICT %s%s%s log10 U''=%.4f [%.0fs]\n", vd, bstr[0] ? " bound 10^(10^" : "", bstr[0] ? bstr : "", mpz_log10d(Ub), cpu_s() - t0);
        if (bstr[0]) printf("bound log10(digits) = %s vs log10 U'' = %.4f\n", bstr, mpz_log10d(Ub));
        free(ys); mpz_clears(y, Ub, rr.nn, NULL); co_clear(&co0);
        if (ft) fclose(ft);
        if (g_ptdump) fclose(g_ptdump);
        if (g_surv_out) fclose(g_surv_out);
        return 0;
    }
    KeySet ks = load_keys(only);
    FILE *f = fopen(cases, "r"); if (!f) die("cannot open cases");
    Case c;
    while (read_case(f, &c)) {
        if (!key_wanted(&ks, c.s, c.Mstr, c.a, c.y) || seen_before(c.fullkey)) { mpz_clear(c.y); continue; }
        nall++;
        mpz_t Ub; mpz_init_set(Ub, *get_U(c.k, c.a)); mpz_set(g_Upp, Ub); mpz_set(g_y, c.y);
        double logU = mpz_log10d(Ub);
        int a, b, cc;
        if (!factor237(c.y, &a, &b, &cc) || a != c.a) die("anchor is not 2^a 3^b 7^c with the recorded a");
        Co co0; co_init(&co0); co_set(&co0, &g_lam);
        mpz_set_si(co0.v0b, b); mpz_set_si(co0.v0c, cc); co_babai(&co0);
        RepList reps = {0, 0, 0};
        filtered_reps(&reps, &c);
        char *ys = mpz_get_str(NULL, 10, c.y);
        R480 tot; r480_init(&tot);
        char detail[8192]; size_t dn = 0; detail[0] = 0;
        long totwords = 0;
        for (int ri = 0; ri < reps.n; ri++) {
            R480 rr; r480_init(&rr);
            run_rep480(c.fullkey, ri, &reps.v[ri], &co0, c.a, maxcases, &rr);
            if (g_verbose480) fprintf(stderr, "REP480 key=[%s] rep=%d wrap=%ld words=%d notappl=%d G=%ld shadow=%d compat=%ld notshadow_compat=%ld passchain=%ld windows=%ld alive=%ld notshadow_alive=%ld\n", c.fullkey, ri, rr.wrap, rr.nwords, rr.nonappl, rr.nG, rr.shadow_ok, rr.compat, rr.notshadow_compat, rr.passchain, rr.nwin, rr.alive, rr.notshadow_alive);
            totwords += rr.nwords;
            if (rr.nwords) dn += snprintf(detail + dn, sizeof detail - dn, "%s(w=%d,T=%d,G=%ld,compat=%ld,chain=%ld,win=%ld,alive=%ld%s%s)", dn ? " " : "", rr.nwords, rr.nT, rr.nG, rr.compat, rr.passchain, rr.nwin, rr.alive, rr.nonappl ? ",NONAPPL" : "", rr.budget ? ",BUDGET" : "");
            tot.budget |= rr.budget; tot.nonappl += rr.nonappl; tot.alive += rr.alive; tot.nG += rr.nG; tot.compat += rr.compat; tot.nwords += rr.nwords;
            if (rr.have_nn && (!tot.have_nn || mpz_cmp(rr.nn, tot.nn) < 0)) { mpz_set(tot.nn, rr.nn); tot.have_nn = 1; }
            mpz_clear(rr.nn);
        }
        char bstr[64]; int closes;
        const char *vd = verdict480(&tot, Ub, bstr, &closes);
        int closed = !strcmp(vd, "CLOSED-cut") || !strcmp(vd, "CLOSED-sandwich");
        nclosed += closed;
        printf("s=%-8s M=%-12s a=%d y=%-11s k=%d log10 U=%.1f reps=%d words=%ld -> %s%s%s %s alive=%ld [%.0fs]\n", c.s, c.Mstr, c.a, ys, c.k, logU, reps.n, totwords, vd,
               bstr[0] ? " bound 10^(10^" : "", bstr[0] ? bstr : "", detail, tot.alive, cpu_s() - t0);
        if (ft) fprintf(ft, "%s\t%s\t%s\t%d\t%s\t%d\t%ld\t%s\t%s\t%ld\n", c.fullkey, c.s, c.Mstr, c.a, ys, reps.n, totwords, vd, bstr, tot.alive);
        fflush(stdout);
        free(ys); mpz_clear(tot.nn); mpz_clear(Ub);
        free(reps.v); co_clear(&co0); mpz_clear(c.y);
    }
    printf("\n%ld of %ld patterns closed by the level-480 step; discrete logs %ld [%.0fs]\n", nclosed, nall, g_ndlog, cpu_s() - t0);
    if (ft) fclose(ft);
    if (g_ptdump) fclose(g_ptdump);
    if (g_surv_out) fclose(g_surv_out);
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: cport_shadow480 deepcut|sandwich|selftest|shadow|shadow480 ...\n"); return 2; }
    init_tables(); init_caches();
    for (int i = 2; i < argc; i++) {
        if (!strcmp(argv[i], "--eager")) g_eager = 1;
        else if (!strcmp(argv[i], "--break")) {
            const char *b = argv[i + 1];
            if (!strcmp(b, "lz5")) g_break_lz5 = 1; else if (!strcmp(b, "t2")) g_break_t2 = 1;
            else if (!strcmp(b, "nearest")) g_break_nearest = 1; else if (!strcmp(b, "v2")) g_break_v2 = 1;
            else die("unknown --break");
        }
    }
    if (!strcmp(argv[1], "deepcut")) return cmd_deepcut(argc - 2, argv + 2);
    if (!strcmp(argv[1], "sandwich")) return cmd_sandwich(argc - 2, argv + 2);
    if (!strcmp(argv[1], "selftest")) return cmd_selftest(argc - 2, argv + 2);
    if (!strcmp(argv[1], "shadow")) return cmd_shadow(argc - 2, argv + 2);
    if (!strcmp(argv[1], "dptest")) return cmd_dptest(argc - 2, argv + 2);
    if (!strcmp(argv[1], "shadow480")) return cmd_shadow480(argc - 2, argv + 2);
    die("unknown command");
    return 2;
}
