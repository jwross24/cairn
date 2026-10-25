#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NPOS 96
#define MAXC 14
#define MAXM 140
#define MAXV 200000

typedef unsigned long long u64;
typedef unsigned __int128 u128;

static const int DW[7] = {1, 2, 3, 5, 6, 7, 8};
static const int DD[7] = {2, 3, 4, 6, 7, 8, 9};
static const int DEA[7] = {1, 0, 2, 1, 0, 3, 0};
static const int DEB[7] = {0, 1, 0, 1, 0, 0, 2};
static const int DEC[7] = {0, 0, 0, 0, 1, 0, 0};

static int TA, TB, TC, SA, SB, SC, S;
static int overflowed = 0;

typedef struct { int sid, da, db, dc; int nv; int *vi; } Ent;
static Ent *tm[MAXM + 1];
static int tmn[MAXM + 1];
static signed char (*VJ)[7];
static int nvec;
static int *MX;
static int MXALL;
static int dsrem[NPOS + 1];

static inline int sidx(int a, int b, int c) { return (a * SB + b) * SC + c; }
static inline int ci(int cin, int sid) { return cin * S + sid; }

static void gen_vec(int t, int m, int a, int b, int c, signed char *cur)
{
    if (t == 7) {
        memcpy(VJ[nvec++], cur, 7);
        return;
    }
    for (int j = 0;; j++) {
        int mm = m + j * DW[t], aa = a + j * DEA[t], bb = b + j * DEB[t], cc = c + j * DEC[t];
        if (mm > MAXM || aa >= SA || bb >= SB || cc >= SC) break;
        cur[t] = (signed char)j;
        gen_vec(t + 1, mm, aa, bb, cc, cur);
    }
    cur[t] = 0;
}

static void build_tm(void)
{
    VJ = malloc(7 * (size_t)MAXV);
    signed char cur[7] = {0};
    nvec = 0;
    gen_vec(0, 0, 0, 0, 0, cur);
    int *vm = malloc(sizeof(int) * nvec), *vs = malloc(sizeof(int) * nvec);
    for (int v = 0; v < nvec; v++) {
        int m = 0, a = 0, b = 0, c = 0;
        for (int t = 0; t < 7; t++) { m += VJ[v][t] * DW[t]; a += VJ[v][t] * DEA[t]; b += VJ[v][t] * DEB[t]; c += VJ[v][t] * DEC[t]; }
        vm[v] = m; vs[v] = sidx(a, b, c);
    }
    for (int m = 0; m <= MAXM; m++) {
        int *seen = calloc(S, sizeof(int));
        int n = 0;
        for (int v = 0; v < nvec; v++) if (vm[v] == m && !seen[vs[v]]++) n++;
        tm[m] = malloc(sizeof(Ent) * (n ? n : 1));
        tmn[m] = n;
        int idx[S > 0 ? S : 1];
        int i = 0;
        for (int sid = 0; sid < S; sid++) {
            if (!seen[sid]) { idx[sid] = -1; continue; }
            idx[sid] = i;
            tm[m][i].sid = sid;
            tm[m][i].da = sid / (SB * SC); tm[m][i].db = (sid / SC) % SB; tm[m][i].dc = sid % SC;
            tm[m][i].nv = 0;
            tm[m][i].vi = malloc(sizeof(int) * seen[sid]);
            i++;
        }
        for (int v = 0; v < nvec; v++) if (vm[v] == m) { Ent *e = &tm[m][idx[vs[v]]]; e->vi[e->nv++] = v; }
        free(seen);
    }
    free(vm); free(vs);
    MX = malloc(sizeof(int) * S);
    for (int i = 0; i < S; i++) MX[i] = -1;
    for (int m = 0; m <= MAXM; m++)
        for (int i = 0; i < tmn[m]; i++) MX[tm[m][i].sid] = m;
    MXALL = MX[sidx(TA, TB, TC)];
}

static int vdig[NPOS], vhi;

static int build_v(const char *ystr, int k, int nu)
{
    int d[200];
    memset(d, 0, sizeof d);
    for (int i = 0; i < NPOS; i++) d[i] = k;
    int len = (int)strlen(ystr);
    for (int i = 0; i < len; i++) d[i] += ystr[len - 1 - i] - '0';
    for (int i = 0; i < nu; i++) d[i] -= 1;
    int carry = 0;
    for (int i = 0; i < 200; i++) {
        int x = d[i] + carry;
        carry = x >= 0 ? x / 10 : -((-x + 9) / 10);
        d[i] = x - carry * 10;
    }
    if (carry < 0) return 0;
    for (int i = 0; i < NPOS; i++) vdig[i] = d[i];
    long hi = 0, mul = 1;
    for (int i = NPOS; i < 200; i++) {
        if (d[i]) {
            if (i - NPOS > 3) return 0;
            hi += d[i] * mul;
        }
        mul *= 10;
    }
    if (hi >= MAXC) return 0;
    vhi = (int)hi;
    dsrem[NPOS] = 0;
    for (int i = NPOS - 1; i >= 0; i--) dsrem[i] = dsrem[i + 1] + vdig[i];
    if (dsrem[0] + 10 * vhi > MXALL) return 0;
    return 1;
}

static u64 *F[NPOS + 1], *G[NPOS + 1];

static void alloc_layers(void)
{
    size_t n = (size_t)MAXC * S;
    for (int e = 0; e <= NPOS; e++) { F[e] = calloc(n, sizeof(u64)); G[e] = calloc(n, sizeof(u64)); }
}

static void run_forward(void)
{
    size_t n = (size_t)MAXC * S;
    for (int e = 0; e <= NPOS; e++) { memset(F[e], 0, n * sizeof(u64)); memset(G[e], 0, n * sizeof(u64)); }
    F[0][ci(0, 0)] = 1;
    for (int e = 0; e < NPOS; e++) {
        int v = vdig[e];
        u64 *cur = F[e], *nx = F[e + 1];
        for (int cin = 0; cin < MAXC; cin++)
            for (int sid = 0; sid < S; sid++) {
                u64 x = cur[ci(cin, sid)];
                if (!x) continue;
                int a = sid / (SB * SC), b = (sid / SC) % SB, c = sid % SC;
                int rem = sidx(TA - a, TB - b, TC - c);
                if (MX[rem] < dsrem[e] + 10 * vhi - cin) continue;
                for (int cout = 0; cout < MAXC; cout++) {
                    int m = v + 10 * cout - cin;
                    if (m < 0) continue;
                    if (m > MAXM) break;
                    Ent *en = tm[m];
                    for (int i = 0; i < tmn[m]; i++) {
                        int aa = a + en[i].da, bb = b + en[i].db, cc = c + en[i].dc;
                        if (aa >= SA || bb >= SB || cc >= SC) continue;
                        u64 add = x * (u64)en[i].nv;
                        u64 *p = &nx[ci(cout, sidx(aa, bb, cc))];
                        if (__builtin_add_overflow(*p, add, p)) overflowed = 1;
                    }
                }
            }
    }
}

static u64 run_back(void)
{
    G[NPOS][ci(vhi, sidx(TA, TB, TC))] = F[NPOS][ci(vhi, sidx(TA, TB, TC))] ? 1 : 0;
    for (int e = NPOS - 1; e >= 0; e--) {
        int v = vdig[e];
        for (int cin = 0; cin < MAXC; cin++)
            for (int sid = 0; sid < S; sid++) {
                if (!F[e][ci(cin, sid)]) continue;
                int a = sid / (SB * SC), b = (sid / SC) % SB, c = sid % SC;
                u64 tot = 0;
                for (int cout = 0; cout < MAXC; cout++) {
                    int m = v + 10 * cout - cin;
                    if (m < 0) continue;
                    if (m > MAXM) break;
                    Ent *en = tm[m];
                    for (int i = 0; i < tmn[m]; i++) {
                        int aa = a + en[i].da, bb = b + en[i].db, cc = c + en[i].dc;
                        if (aa >= SA || bb >= SB || cc >= SC) continue;
                        u64 g = G[e + 1][ci(cout, sidx(aa, bb, cc))];
                        if (!g) continue;
                        u64 add = (u64)en[i].nv * g;
                        if (__builtin_add_overflow(tot, add, &tot)) overflowed = 1;
                    }
                }
                G[e][ci(cin, sid)] = tot;
            }
    }
    return G[0][ci(0, 0)];
}

static u128 MOD, R96M, YM, P10[NPOS + 2], G5[80];
static int LOWE;
static int ya;

typedef struct { int e; int nd; int dv[8]; } Cls;
static Cls cls[NPOS];
static int ncls;

static int rec_survive(int ci_, u128 res)
{
    if (ci_ == ncls) return res % MOD == 0;
    int e = cls[ci_].e;
    u128 g = G5[e];
    if (res % g != 0) return 0;
    if (rec_survive(ci_ + 1, res)) return 1;
    for (int j = 0; j < cls[ci_].nd; j++) {
        u128 add = (u128)(cls[ci_].dv[j] - 1) * P10[e] % MOD;
        if (rec_survive(ci_ + 1, (res + add) % MOD)) return 1;
    }
    return 0;
}

static int survive_digits(const int *dd, const int *ee, int n)
{
    ncls = 0;
    int pos[NPOS];
    for (int i = 0; i < NPOS; i++) pos[i] = -1;
    for (int i = 0; i < n; i++) {
        int e = ee[i];
        if (e >= LOWE) continue;
        if (pos[e] < 0) { pos[e] = 0; cls[ncls].e = e; cls[ncls].nd = 0; ncls++; }
    }
    for (int a = 1; a < ncls; a++) { Cls t = cls[a]; int b = a - 1; while (b >= 0 && cls[b].e > t.e) { cls[b + 1] = cls[b]; b--; } cls[b + 1] = t; }
    for (int i = 0; i < ncls; i++) pos[cls[i].e] = i;
    for (int i = 0; i < n; i++) {
        int e = ee[i];
        if (e >= LOWE) continue;
        Cls *c = &cls[pos[e]];
        int dup = 0;
        for (int j = 0; j < c->nd; j++) if (c->dv[j] == dd[i]) dup = 1;
        if (!dup && c->nd < 8) c->dv[c->nd++] = dd[i];
    }
    u128 res = (R96M + MOD - YM) % MOD;
    return rec_survive(0, res);
}

static void set_target(const char *ys)
{
    int len = (int)strlen(ys);
    long long a = 0;
    char buf[256];
    strcpy(buf, ys);
    for (;;) {
        int bl = (int)strlen(buf);
        if (((buf[bl - 1] - '0') & 1) || !strcmp(buf, "0")) break;
        int r = 0, on = 0;
        char out[256];
        for (int i = 0; i < bl; i++) {
            int x = r * 10 + (buf[i] - '0');
            int q = x / 2;
            r = x % 2;
            if (on || q) out[on++] = (char)('0' + q);
        }
        out[on] = 0;
        strcpy(buf, on ? out : "0");
        a++;
    }
    ya = (int)a;
    LOWE = ya + 9;
    MOD = (u128)1 << LOWE;
    for (int i = 0; i < 5; i++) MOD *= 5;
    P10[0] = 1 % MOD;
    for (int i = 1; i < NPOS + 2; i++) P10[i] = P10[i - 1] * 10 % MOD;
    R96M = 0;
    for (int i = 0; i < NPOS; i++) R96M = (R96M * 10 + 1) % MOD;
    YM = 0;
    for (int i = 0; i < len; i++) YM = (YM * 10 + (u128)(ys[i] - '0')) % MOD;
    for (int e = 0; e < 80; e++) {
        u128 g = (u128)1 << e;
        int f5 = e < 5 ? e : 5;
        for (int i = 0; i < f5; i++) g *= 5;
        G5[e] = g;
    }
}

static unsigned long long rng_s = 88172645463325252ULL;
static u64 rnd(void) { rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17; return rng_s; }
static double emit_p = 1.0;
static signed char stk[NPOS][7];
static int dd_[400], ee_[400];
static u64 surv_total, non_total;
static int mode_emit;
static char cur_y[256];
static int cur_k, cur_nu;

static int collect(int upto, int *dd, int *ee)
{
    int n = 0;
    for (int e = 0; e < upto; e++)
        for (int t = 0; t < 7; t++)
            for (int j = 0; j < stk[e][t]; j++) { dd[n] = DD[t]; ee[n] = e; n++; }
    return n;
}

static void dfs(int e, int cin, int a, int b, int c)
{
    if (e == LOWE && !mode_emit) {
        int n = collect(e, dd_, ee_);
        u64 g = G[e][ci(cin, sidx(a, b, c))];
        if (survive_digits(dd_, ee_, n)) surv_total += g; else non_total += g;
        return;
    }
    if (e == LOWE && mode_emit) {
        int n = collect(e, dd_, ee_);
        u64 g = G[e][ci(cin, sidx(a, b, c))];
        if (!survive_digits(dd_, ee_, n)) { non_total += g; return; }
    }
    if (e == NPOS) {
        int n = collect(NPOS, dd_, ee_);
        if (mode_emit && (emit_p >= 1.0 || (double)(rnd() >> 11) * (1.0 / 9007199254740992.0) < emit_p)) {
            int ndd[400], nee[400];
            memcpy(ndd, dd_, sizeof(int) * n); memcpy(nee, ee_, sizeof(int) * n);
            for (int x = 1; x < n; x++) {
                int td = ndd[x], te = nee[x], y = x - 1;
                while (y >= 0 && (ndd[y] > td || (ndd[y] == td && nee[y] > te))) { ndd[y + 1] = ndd[y]; nee[y + 1] = nee[y]; y--; }
                ndd[y + 1] = td; nee[y + 1] = te;
            }
            printf("%s %d %d %d %d", cur_y, cur_k, cur_nu, ya, n);
            for (int x = 0; x < n; x++) printf(" %d:%d", ndd[x], nee[x]);
            printf("\n");
        }
        surv_total++;
        return;
    }
    int v = vdig[e];
    for (int cout = 0; cout < MAXC; cout++) {
        int m = v + 10 * cout - cin;
        if (m < 0) continue;
        if (m > MAXM) break;
        Ent *en = tm[m];
        for (int i = 0; i < tmn[m]; i++) {
            int aa = a + en[i].da, bb = b + en[i].db, cc = c + en[i].dc;
            if (aa >= SA || bb >= SB || cc >= SC) continue;
            if (!G[e + 1][ci(cout, sidx(aa, bb, cc))]) continue;
            for (int q = 0; q < en[i].nv; q++) {
                memcpy(stk[e], VJ[en[i].vi[q]], 7);
                dfs(e + 1, cout, aa, bb, cc);
            }
        }
    }
    memset(stk[e], 0, 7);
}

static u64 rnd_below(u64 n)
{
    u64 lim = (~0ULL) - ((~0ULL) % n), r;
    do { r = rnd(); } while (r >= lim);
    return r % n;
}

static int sample_one(void)
{
    int cin = 0, a = 0, b = 0, c = 0;
    memset(stk, 0, sizeof stk);
    for (int e = 0; e < NPOS; e++) {
        int v = vdig[e];
        u64 tot = G[e][ci(cin, sidx(a, b, c))];
        u64 r = rnd_below(tot), acc = 0;
        int done = 0;
        for (int cout = 0; cout < MAXC && !done; cout++) {
            int m = v + 10 * cout - cin;
            if (m < 0) continue;
            if (m > MAXM) break;
            Ent *en = tm[m];
            for (int i = 0; i < tmn[m]; i++) {
                int aa = a + en[i].da, bb = b + en[i].db, cc = c + en[i].dc;
                if (aa >= SA || bb >= SB || cc >= SC) continue;
                u64 w = (u64)en[i].nv * G[e + 1][ci(cout, sidx(aa, bb, cc))];
                if (!w) continue;
                if (r < acc + w) {
                    u64 sub = rnd_below((u64)en[i].nv);
                    memcpy(stk[e], VJ[en[i].vi[sub]], 7);
                    cin = cout; a = aa; b = bb; c = cc; done = 1;
                    break;
                }
                acc += w;
            }
        }
        if (!done) return 0;
    }
    return 1;
}

static void print_pattern(const char *tag, int verdict)
{
    int n = collect(NPOS, dd_, ee_);
    printf("%s %s %d %d %d %d %d", tag, cur_y, cur_k, cur_nu, ya, verdict, n);
    for (int x = 0; x < n; x++) printf(" %d:%d", dd_[x], ee_[x]);
    printf("\n");
}

int main(int argc, char **argv)
{
    if (argc < 5) { fprintf(stderr, "usage: enum_surv A B C count|emit|sample|verdict [seed]\n"); return 2; }
    TA = atoi(argv[1]); TB = atoi(argv[2]); TC = atoi(argv[3]);
    SA = TA + 1; SB = TB + 1; SC = TC + 1; S = SA * SB * SC;
    const char *mode = argv[4];
    if (argc >= 6) rng_s ^= (u64)atoll(argv[5]) * 0x9E3779B97F4A7C15ULL;
    if (argc >= 7) emit_p = atof(argv[6]);
    static char line[1 << 16];
    if (!strcmp(mode, "verdict")) {
        while (fgets(line, sizeof line, stdin)) {
            char ys[256]; int k, nu, off = 0, n = 0;
            if (sscanf(line, "%255s %d %d%n", ys, &k, &nu, &off) < 3) continue;
            set_target(ys);
            char *p = line + off;
            int dd[400], ee[400], d, e, used;
            while (sscanf(p, " %d:%d%n", &d, &e, &used) == 2) { dd[n] = d; ee[n] = e; n++; p += used; }
            printf("%s %d %d %d %d\n", ys, k, nu, ya, survive_digits(dd, ee, n));
        }
        return 0;
    }
    build_tm();
    alloc_layers();
    mode_emit = !strcmp(mode, "emit");
    while (fgets(line, sizeof line, stdin)) {
        char ys[256]; int k, nu, ns = 0;
        int got = sscanf(line, "%255s %d %d %d", ys, &k, &nu, &ns);
        if (got < 3) continue;
        strcpy(cur_y, ys); cur_k = k; cur_nu = nu;
        set_target(ys);
        if (!build_v(ys, k, nu)) { printf("NOV %s %d %d\n", ys, k, nu); fflush(stdout); continue; }
        run_forward();
        u64 tot = run_back();
        if (!strcmp(mode, "sample")) {
            for (int s = 0; s < ns && tot; s++) {
                if (!sample_one()) { fprintf(stderr, "sample failure\n"); continue; }
                int n = collect(NPOS, dd_, ee_);
                print_pattern("P", survive_digits(dd_, ee_, n));
            }
            fflush(stdout);
            continue;
        }
        surv_total = non_total = 0;
        memset(stk, 0, sizeof stk);
        if (tot) dfs(0, 0, 0, 0, 0);
        if (!mode_emit) printf("T %s %d %d %d %llu %llu %llu%s\n", ys, k, nu, ya, tot, surv_total, non_total, overflowed ? " OVERFLOW" : "");
        else printf("T %s %d %d %d %llu %llu %llu%s\n", ys, k, nu, ya, tot, surv_total, non_total, overflowed ? " OVERFLOW" : "");
        fflush(stdout);
    }
    return 0;
}
