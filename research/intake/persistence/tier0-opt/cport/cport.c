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
        for (unsigned mask = 0; mask < (1u << nf); mask++) {
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

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: cport deepcut|sandwich|selftest ...\n"); return 2; }
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
    die("unknown command");
    return 2;
}
