#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define NPOS 96
#define MAXC 14
#define MAXM 140

typedef unsigned long long u64;

static const int DW[7] = {1, 2, 3, 5, 6, 7, 8};
static const int DD[7] = {2, 3, 4, 6, 7, 8, 9};
static const int DEA[7] = {1, 0, 2, 1, 0, 3, 0};
static const int DEB[7] = {0, 1, 0, 1, 0, 0, 2};
static const int DEC[7] = {0, 0, 0, 0, 1, 0, 0};

static int TA, TB, TC;
static int SA, SB, SC;
static int overflowed = 0;

typedef struct { int sid; int da, db, dc; u64 ways; } Ent;
static Ent *tm[MAXM + 1];
static int tmn[MAXM + 1];
static u64 *dp0;
static int *MX;
static int MXALL;
static int dsrem[NPOS + 1];

static inline int sidx(int a, int b, int c) { return (a * SB + b) * SC + c; }

static void build_tm(void)
{
    size_t sz = (size_t)(MAXM + 1) * SA * SB * SC;
    u64 *cur = calloc(sz, sizeof(u64));
    cur[0] = 1;
    for (int t = 0; t < 7; t++) {
        u64 *nx = calloc(sz, sizeof(u64));
        for (int m = 0; m <= MAXM; m++)
            for (int a = 0; a < SA; a++)
                for (int b = 0; b < SB; b++)
                    for (int c = 0; c < SC; c++) {
                        u64 v = cur[((size_t)m * SA + a) * SB * SC + b * SC + c];
                        if (!v) continue;
                        for (int j = 0;; j++) {
                            int mm = m + j * DW[t], aa = a + j * DEA[t], bb = b + j * DEB[t], cc = c + j * DEC[t];
                            if (mm > MAXM || aa >= SA || bb >= SB || cc >= SC) break;
                            nx[((size_t)mm * SA + aa) * SB * SC + bb * SC + cc] += v;
                        }
                    }
        free(cur);
        cur = nx;
    }
    for (int m = 0; m <= MAXM; m++) {
        int n = 0;
        for (int a = 0; a < SA; a++)
            for (int b = 0; b < SB; b++)
                for (int c = 0; c < SC; c++)
                    if (cur[((size_t)m * SA + a) * SB * SC + b * SC + c]) n++;
        tm[m] = malloc(sizeof(Ent) * (n ? n : 1));
        tmn[m] = n;
        int i = 0;
        for (int a = 0; a < SA; a++)
            for (int b = 0; b < SB; b++)
                for (int c = 0; c < SC; c++) {
                    u64 v = cur[((size_t)m * SA + a) * SB * SC + b * SC + c];
                    if (!v) continue;
                    tm[m][i].sid = sidx(a, b, c);
                    tm[m][i].da = a; tm[m][i].db = b; tm[m][i].dc = c;
                    tm[m][i].ways = v;
                    i++;
                }
    }
    free(cur);
    MX = malloc(sizeof(int) * SA * SB * SC);
    for (int i = 0; i < SA * SB * SC; i++) MX[i] = -1;
    for (int m = 0; m <= MAXM; m++)
        for (int i = 0; i < tmn[m]; i++) MX[tm[m][i].sid] = m;
    MXALL = MX[sidx(TA, TB, TC)];
}

static int vdig[NPOS];
static int vhi;

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

static inline int ci(int cin, int sid) { return cin * (SA * SB * SC) + sid; }

static u64 run_dp(void)
{
    int S = SA * SB * SC;
    size_t n = (size_t)MAXC * S;
    u64 *cur = calloc(n, sizeof(u64)), *nx = calloc(n, sizeof(u64));
    cur[ci(0, 0)] = 1;
    for (int e = 0; e < NPOS; e++) {
        memset(nx, 0, n * sizeof(u64));
        int v = vdig[e];
        for (int cin = 0; cin < MAXC; cin++)
            for (int sid = 0; sid < S; sid++) {
                u64 x = cur[ci(cin, sid)];
                if (!x) continue;
                int a = sid / (SB * SC), b = (sid / SC) % SB, c = sid % SC;
                {
                    int rem = sidx(TA - a, TB - b, TC - c);
                    if (MX[rem] < dsrem[e] + 10 * vhi - cin) continue;
                }
                for (int cout = 0; cout < MAXC; cout++) {
                    int m = v + 10 * cout - cin;
                    if (m < 0) continue;
                    if (m > MAXM) break;
                    Ent *en = tm[m];
                    for (int i = 0; i < tmn[m]; i++) {
                        int aa = a + en[i].da, bb = b + en[i].db, cc = c + en[i].dc;
                        if (aa >= SA || bb >= SB || cc >= SC) continue;
                        u64 add = x * en[i].ways;
                        u64 *p = &nx[ci(cout, sidx(aa, bb, cc))];
                        if (__builtin_add_overflow(*p, add, p)) overflowed = 1;
                    }
                }
            }
        u64 *t = cur; cur = nx; nx = t;
    }
    u64 r = cur[ci(vhi, sidx(TA, TB, TC))];
    free(cur); free(nx);
    return r;
}

static u64 *G[NPOS + 1];

static void run_back(void)
{
    int S = SA * SB * SC;
    size_t n = (size_t)MAXC * S;
    for (int e = 0; e <= NPOS; e++) { G[e] = calloc(n, sizeof(u64)); }
    G[NPOS][ci(vhi, sidx(TA, TB, TC))] = 1;
    for (int e = NPOS - 1; e >= 0; e--) {
        int v = vdig[e];
        for (int cin = 0; cin < MAXC; cin++)
            for (int sid = 0; sid < S; sid++) {
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
                        tot += en[i].ways * G[e + 1][ci(cout, sidx(aa, bb, cc))];
                    }
                }
                G[e][ci(cin, sid)] = tot;
            }
    }
}

static unsigned long long rng_s = 88172645463325252ULL;
static u64 rnd(void)
{
    rng_s ^= rng_s << 13; rng_s ^= rng_s >> 7; rng_s ^= rng_s << 17;
    return rng_s;
}
static u64 rnd_below(u64 n)
{
    u64 lim = (~0ULL) - ((~0ULL) % n);
    u64 r;
    do { r = rnd(); } while (r >= lim);
    return r % n;
}

static int cv[7];
static int lst[100000][7];
static int nl;

static void enum_cv(int t, int m, int da, int db, int dc, int *cur)
{
    if (t == 7) {
        if (m == 0 && da == 0 && db == 0 && dc == 0) {
            if (nl < 100000) { memcpy(lst[nl], cur, 7 * sizeof(int)); nl++; }
        }
        return;
    }
    for (int j = 0;; j++) {
        int mm = m - j * DW[t], aa = da - j * DEA[t], bb = db - j * DEB[t], cc = dc - j * DEC[t];
        if (mm < 0 || aa < 0 || bb < 0 || cc < 0) break;
        cur[t] = j;
        enum_cv(t + 1, mm, aa, bb, cc, cur);
    }
    cur[t] = 0;
}

static void sample_one(void)
{
    int S = SA * SB * SC;
    int cin = 0, a = 0, b = 0, c = 0;
    printf("[");
    int first = 1;
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
                u64 w = en[i].ways * G[e + 1][ci(cout, sidx(aa, bb, cc))];
                if (!w) continue;
                if (r < acc + w) {
                    u64 sub = rnd_below(en[i].ways);
                    nl = 0;
                    int cur[7] = {0};
                    enum_cv(0, m, en[i].da, en[i].db, en[i].dc, cur);
                    for (int t = 0; t < 7; t++)
                        for (int j = 0; j < lst[sub][t]; j++) {
                            printf("%s[%d,%d]", first ? "" : ",", DD[t], e);
                            first = 0;
                        }
                    cin = cout; a = aa; b = bb; c = cc;
                    done = 1;
                    break;
                }
                acc += w;
            }
        }
        if (!done) { printf("]\n"); fprintf(stderr, "sample failure at %d\n", e); return; }
    }
    printf("]\n");
    (void)S;
}

int main(int argc, char **argv)
{
    if (argc < 5) { fprintf(stderr, "usage: anchor_dp A B C mode [seed nsamples]\n"); return 2; }
    TA = atoi(argv[1]); TB = atoi(argv[2]); TC = atoi(argv[3]);
    SA = TA + 1; SB = TB + 1; SC = TC + 1;
    const char *mode = argv[4];
    build_tm();
    char line[512];
    if (!strcmp(mode, "count")) {
        while (fgets(line, sizeof line, stdin)) {
            char ys[256]; int k;
            if (sscanf(line, "%255s %d", ys, &k) != 2) continue;
            u64 total = 0;
            printf("%s %d", ys, k);
            for (int nu = 0; nu < NPOS; nu++) {
                if (!build_v(ys, k, nu)) continue;
                u64 r = run_dp();
                if (r) { printf(" %d:%llu", nu, r); total += r; }
            }
            printf(" T:%llu%s\n", total, overflowed ? " OVERFLOW" : "");
            fflush(stdout);
        }
    } else if (!strcmp(mode, "sample")) {
        if (argc >= 6) rng_s ^= (u64)atoll(argv[5]) * 0x9E3779B97F4A7C15ULL;
        int ns = argc >= 7 ? atoi(argv[6]) : 1;
        while (fgets(line, sizeof line, stdin)) {
            char ys[256]; int k, nu, mm = 0;
            int got = sscanf(line, "%255s %d %d %d", ys, &k, &nu, &mm);
            if (got < 3) continue;
            if (!build_v(ys, k, nu)) { printf("NOV\n"); continue; }
            run_back();
            u64 tot = G[0][ci(0, 0)];
            printf("%s %d %d total %llu\n", ys, k, nu, tot);
            int reps = got == 4 ? mm : ns;
            if (tot) for (int s = 0; s < reps; s++) sample_one();
            for (int e = 0; e <= NPOS; e++) free(G[e]);
        }
    }
    return 0;
}
