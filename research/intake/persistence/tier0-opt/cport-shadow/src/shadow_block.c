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
static LP g_lp[32]; static int g_nlp;
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
static void load_levelprimes(const char *path) {
    FILE *f = fopen(path, "r"); if (!f) die("cannot open levelprimes file");
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        if (line[0] == '#' || line[0] == '\n') continue;
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
        if (g_nlp >= 32) die("too many level primes");
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

