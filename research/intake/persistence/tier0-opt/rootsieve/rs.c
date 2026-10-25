#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef long long ll; typedef unsigned long long ull; typedef unsigned __int128 u128;
#define MAXP 8
#define MAXQ 48
#define MAXC 8
#define NCAP 3
static const int CAPS[NCAP] = {60, 118, 160};

static int L, A, q, digits[MAXQ];
static int np; static ll P[MAXP], L2[MAXP], L3[MAXP], L7[MAXP]; static ll POW10[MAXP][64], R[MAXP][64]; static int *LOGT[MAXP];
static int nc; static int cn[MAXC], cidx[MAXC][MAXP]; static ll cmod[MAXC][MAXP], ccrt[MAXC]; static ll csize[MAXC];
static int *crep[MAXC];
static ll N, G, U[3], U2[2][2]; static int KT[64 * 4];
static ull pow10u[19];
static int *CONTRIB[MAXC][MAXP];
static ll Dd[10][64][MAXP];
static int eps[MAXQ];
static int pattern_has[10][64];
static int cntmg[10];
static ll LAMK[19]; static ull *T3K[19], *T7K[19]; static ull P2A[256];

static inline ull mulmod(ull a, ull b, ull m) { if (m <= 0xFFFFFFFFULL) return (a % m) * (b % m) % m; return (ull)(((u128)a * b) % m); }
static ull powmod(ull b, ull e, ull m) { ull r = 1 % m; b %= m; while (e) { if (e & 1) r = mulmod(r, b, m); b = mulmod(b, b, m); e >>= 1; } return r; }
static ll gcdll(ll a, ll b) { while (b) { ll t = a % b; a = b; b = t; } return a; }
static ll absll(ll x) { return x < 0 ? -x : x; }

static void init_tail(void) {
  for (int a = 0; a <= A && a < 256; a++) {
    int K = KT[a]; if (K > 18) K = 18; if (K < 1) continue; ull m = pow10u[K];
    P2A[a] = powmod(2, (ull)a, m);
    if (T3K[K] || LAMK[K] < 0) continue;
    ll l2 = K == 1 ? 1 : (K == 2 ? 2 : (1LL << (K - 2))), l5 = 4; for (int i = 1; i < K; i++) l5 *= 5;
    ll lam = l2 / gcdll(l2, l5) * l5;
    if (lam > 65536) { LAMK[K] = -1; continue; }
    ull *t3 = malloc(sizeof(ull) * lam), *t7 = malloc(sizeof(ull) * lam); t3[0] = 1 % m; t7[0] = 1 % m;
    for (ll e = 1; e < lam; e++) { t3[e] = mulmod(t3[e - 1], 3, m); t7[e] = mulmod(t7[e - 1], 7, m); }
    T3K[K] = t3; T7K[K] = t7; LAMK[K] = lam;
  }
}

static void read_cfg(const char *path) {
  FILE *f = fopen(path, "r"); if (!f) { perror("cfg"); exit(1); }
  if (fscanf(f, "%d %d %d", &L, &A, &q) != 3) exit(2);
  for (int i = 0; i < q; i++) if (fscanf(f, "%d", &digits[i]) != 1) exit(2);
  if (fscanf(f, "%d", &np) != 1) exit(2);
  for (int i = 0; i < np; i++) {
    if (fscanf(f, "%lld %lld %lld %lld", &P[i], &L2[i], &L3[i], &L7[i]) != 4) exit(2);
    for (int j = 0; j < L; j++) if (fscanf(f, "%lld", &POW10[i][j]) != 1) exit(2);
    for (int j = 0; j < L; j++) if (fscanf(f, "%lld", &R[i][j]) != 1) exit(2);
    LOGT[i] = malloc(sizeof(int) * P[i]); for (ll j = 0; j < P[i]; j++) if (fscanf(f, "%d", &LOGT[i][j]) != 1) exit(2);
  }
  if (fscanf(f, "%d", &nc) != 1) exit(2);
  for (int c = 0; c < nc; c++) {
    if (fscanf(f, "%d", &cn[c]) != 1) exit(2);
    for (int j = 0; j < cn[c]; j++) if (fscanf(f, "%d", &cidx[c][j]) != 1) exit(2);
    for (int j = 0; j < cn[c]; j++) if (fscanf(f, "%lld", &cmod[c][j]) != 1) exit(2);
    ll hs; if (fscanf(f, "%lld %lld", &ccrt[c], &hs) != 2) exit(2);
    csize[c] = 1; for (int j = 0; j < cn[c]; j++) csize[c] *= cmod[c][j];
    crep[c] = malloc(sizeof(int) * 3 * csize[c]); for (ll i = 0; i < 3 * csize[c]; i++) crep[c][i] = -1;
    for (ll h = 0; h < hs; h++) {
      ll key[MAXP]; int rep[3];
      for (int j = 0; j < cn[c]; j++) if (fscanf(f, "%lld", &key[j]) != 1) exit(2);
      for (int j = 0; j < 3; j++) if (fscanf(f, "%d", &rep[j]) != 1) exit(2);
      ll idx = 0; for (int j = 0; j < cn[c]; j++) idx = idx * cmod[c][j] + key[j];
      crep[c][idx * 3] = rep[0]; crep[c][idx * 3 + 1] = rep[1]; crep[c][idx * 3 + 2] = rep[2];
    }
  }
  if (fscanf(f, "%lld %lld %lld %lld %lld", &N, &G, &U[0], &U[1], &U[2]) != 5) exit(2);
  if (fscanf(f, "%lld %lld %lld %lld", &U2[0][0], &U2[0][1], &U2[1][0], &U2[1][1]) != 4) exit(2);
  for (int a = 0; a <= A; a++) if (fscanf(f, "%d", &KT[a]) != 1) exit(2);
  fclose(f);
  pow10u[0] = 1; for (int i = 1; i < 19; i++) pow10u[i] = pow10u[i - 1] * 10ULL;
  for (int cc = 0; cc < nc; cc++) {
    for (int i = 0; i < np; i++) CONTRIB[cc][i] = NULL;
    ll stride = 1;
    for (int j = cn[cc] - 1; j >= 0; j--) {
      int i = cidx[cc][j]; CONTRIB[cc][i] = malloc(sizeof(int) * (P[i] - 1));
      for (ll lg = 0; lg < P[i] - 1; lg++) CONTRIB[cc][i][lg] = (int)((lg % cmod[cc][j]) * stride);
      stride *= cmod[cc][j];
    }
  }
}

static int bs_s1, bs_r7[6]; static const int bs_p7[6] = {1, 3, 2, 6, 4, 5}; static ll bs_gb, bs_gc; static __int128 bs_det;
static int mut_mode = 0;
static void init_bs(void) {
  bs_det = (__int128)U2[0][0] * U2[1][1] - (__int128)U2[0][1] * U2[1][0];
  bs_gb = gcdll(absll(U2[0][0]), absll(U2[1][0])); bs_gc = gcdll(absll(U2[0][1]), absll(U2[1][1]));
  bs_r7[0] = 0; for (int n = 0; n < 5; n++) bs_r7[n + 1] = (bs_r7[n] * 10 + 1) % 7;
}
static int rank_of(int nu, int *need_b0, int *need_c0) {
  int s3 = (nu + bs_s1) % 3;
  int y7 = bs_r7[nu % 6]; for (int i = 0; i < q; i++) y7 += (digits[i] - 1) * bs_p7[eps[i] % 6];
  *need_b0 = s3 != 0; *need_c0 = (y7 % 7) != 0;
  return (!*need_b0) + (!*need_c0);
}
static int lattice_keep(int need_b0, int need_c0, ll b0, ll c0) {
  const ll p = U2[0][0], qq = U2[0][1], r = U2[1][0], s = U2[1][1];
  if (mut_mode == 1) { need_b0 = !need_b0; }
  if (mut_mode == 2) { need_c0 = !need_c0; }
  if (mut_mode == 3) { b0 += 1; }
  if (need_b0 && need_c0) {
    __int128 xn = -((__int128)b0 * s - (__int128)c0 * r), yn = -((__int128)p * c0 - (__int128)qq * b0);
    return xn % bs_det == 0 && yn % bs_det == 0;
  }
  if (need_b0) return bs_gb == 0 ? b0 == 0 : b0 % bs_gb == 0;
  if (need_c0) return bs_gc == 0 ? c0 == 0 : c0 % bs_gc == 0;
  return 1;
}

static int tail_flags(int a0, ll b, ll c, int K, ll lamc, ull m) {
  ull Y;
  if (lamc > 0) { ll lam = lamc; ll bm = b % lam; if (bm < 0) bm += lam; ll cm = c % lam; if (cm < 0) cm += lam;
    Y = mulmod(mulmod(P2A[a0], T3K[K][bm], m), T7K[K][cm], m); }
  else return 2;
  int dg[20]; ull t = Y; for (int i = 0; i < K; i++) { dg[i] = (int)(t % 10); t /= 10; }
  int open = 1; int have[10] = {0};
  for (int i = 0; i < K; i++) { int d = dg[i]; if (d == 0) { open = 0; break; } if (d == 1) continue; have[d]++; if (have[d] > cntmg[d]) { open = 0; break; }
    if (pattern_has[d][i] < 1) { open = 0; break; } }
  return open ? 2 : 0;
}

static ull s[4];
static inline ull rotl(ull x, int k) { return (x << k) | (x >> (64 - k)); }
static inline ull rnd(void) { ull r = rotl(s[1] * 5, 7) * 9, t = s[1] << 17; s[2] ^= s[0]; s[3] ^= s[1]; s[1] ^= s[2]; s[0] ^= s[3]; s[2] ^= t; s[3] = rotl(s[3], 45); return r; }
static void seed(ull x) { for (int i = 0; i < 4; i++) { x += 0x9e3779b97f4a7c15ULL; ull z = x; z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL; z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL; s[i] = z ^ (z >> 31); } }
static inline unsigned rnd_below(unsigned n) { return (unsigned)(((u128)rnd() * n) >> 64); }

static ll cnt_pat[3], cnt_zero[3], cnt_pre[3], cnt_surv[3], cnt_surv_keep[3], cnt_lines[NCAP][3], cnt_lines_keep[NCAP][3];
static ll cnt_open[NCAP][3], cnt_open_keep[NCAP][3], cnt_openpat[3], cnt_openpat_keep[3], cnt_survpat_by_a0zero[3];
static ll cnt_a0hist[3][12], cnt_open_a0hist[3][12];
static FILE *dumpf;
static double dump_prob = 0;

static void sample_pattern(int nu) {
  int need_b0, need_c0;
  int rk = rank_of(nu, &need_b0, &need_c0);
  cnt_pat[rk]++;
  ll ya[MAXP]; for (int i = 0; i < np; i++) ya[i] = 0;
  for (int j = 0; j < q; j++) for (int i = 0; i < np; i++) { ll v = ya[i] + Dd[digits[j]][eps[j]][i]; ya[i] = v >= P[i] ? v - P[i] : v; }
  ll logs[MAXP];
  for (int i = 0; i < np; i++) { ll y = R[i][nu] + ya[i]; if (y >= P[i]) y -= P[i]; if (y == 0) { cnt_zero[rk]++; return; } logs[i] = LOGT[i][y]; }
  ll v0 = 0, v1 = 0, v2 = 0;
  for (int c = 0; c < nc; c++) {
    ll idx = 0; for (int j = 0; j < cn[c]; j++) { int i = cidx[c][j]; idx += CONTRIB[c][i][logs[i]]; }
    int *rp = &crep[c][idx * 3]; if (rp[0] < 0) { cnt_pre[rk]++; return; }
    v0 += ccrt[c] * rp[0]; v1 += ccrt[c] * rp[1]; v2 += ccrt[c] * rp[2];
  }
  cnt_surv[rk]++;
  ll r = ((v0 % 12) + 12) % 12;
  int any_keep = 0, any_open = 0, any_open_keep = 0;
  int dumpit = dump_prob > 0 && (rnd() >> 11) * (1.0 / 9007199254740992.0) < dump_prob;
  char buf[4096]; int bl = 0;
  bl += sprintf(buf + bl, "%c %d %d %d", dumpit ? 'U' : 'O', rk, nu, q); for (int j = 0; j < q; j++) bl += sprintf(buf + bl, " %d:%d", digits[j], eps[j]);
  for (ll a0 = r; a0 <= A; a0 += 12) {
    ll k = (a0 - v0) / 12; ll b = v1 + k * U[1], c = v2 + k * U[2];
    int keep = lattice_keep(need_b0, need_c0, b, c);
    int K = KT[a0]; if (K > 18) K = 18;
    int fl = (K == 3 && LAMK[3] == 100) ? tail_flags((int)a0, b, c, 3, 100, 1000ULL) : tail_flags((int)a0, b, c, K, LAMK[K], pow10u[K]);
    int open = (fl & 2) != 0;
    for (int ci = 0; ci < NCAP; ci++) if (a0 <= CAPS[ci]) {
      cnt_lines[ci][rk]++; if (keep) cnt_lines_keep[ci][rk]++;
      if (open) { cnt_open[ci][rk]++; if (keep) cnt_open_keep[ci][rk]++; }
    }
    if (a0 <= CAPS[1]) { if (keep) any_keep = 1; if (open) any_open = 1; if (open && keep) any_open_keep = 1; }
    bl += sprintf(buf + bl, " | %lld %d %d %lld %lld", a0, keep, open, b, c);
  }
  if (any_keep) cnt_surv_keep[rk]++;
  if (any_open) cnt_openpat[rk]++;
  if (any_open_keep) cnt_openpat_keep[rk]++;
  cnt_a0hist[rk][r]++;
  if (any_open) cnt_open_a0hist[rk][r]++;
  if (dumpit || any_open_keep) { buf[bl++] = '\n'; fwrite(buf, 1, bl, dumpf); }
}

static void draw_class_multiset(int m, int *out) {
  unsigned long long used = 0; int v[64]; int n = 0;
  while (n < m) { unsigned x = rnd_below(m + 11); if (used >> x & 1) continue; used |= 1ULL << x; v[n++] = x; }
  for (int i = 0; i < m; i++) for (int j = i + 1; j < m; j++) if (v[j] < v[i]) { int t = v[i]; v[i] = v[j]; v[j] = t; }
  for (int i = 0; i < m; i++) out[i] = v[i] - i;
}

static void check_mode(void) {
  char line[8192];
  while (fgets(line, sizeof line, stdin)) {
    int nu; int qq; char *ptr = line; int off;
    if (sscanf(ptr, "%d %d%n", &nu, &qq, &off) != 2) continue; ptr += off;
    q = qq; memset(cntmg, 0, sizeof cntmg); memset(pattern_has, 0, sizeof pattern_has); bs_s1 = 0;
    for (int j = 0; j < q; j++) { int d, e; if (sscanf(ptr, " %d:%d%n", &d, &e, &off) != 2) exit(5); ptr += off; digits[j] = d; eps[j] = e; cntmg[d]++; pattern_has[d][e]++; bs_s1 += d - 1; }
    int need_b0, need_c0; int rk = rank_of(nu, &need_b0, &need_c0);
    ll ya[MAXP]; for (int i = 0; i < np; i++) ya[i] = 0;
    for (int j = 0; j < q; j++) for (int i = 0; i < np; i++) { ll v = ya[i] + Dd[digits[j]][eps[j]][i]; ya[i] = v >= P[i] ? v - P[i] : v; }
    ll logs[MAXP]; int dead = 0;
    for (int i = 0; i < np; i++) { ll y = R[i][nu] + ya[i]; if (y >= P[i]) y -= P[i]; if (y == 0) { dead = 1; break; } logs[i] = LOGT[i][y]; }
    ll v0 = 0, v1 = 0, v2 = 0;
    if (!dead) for (int c = 0; c < nc; c++) {
      ll idx = 0; for (int j = 0; j < cn[c]; j++) { int i = cidx[c][j]; idx += CONTRIB[c][i][logs[i]]; }
      int *rp = &crep[c][idx * 3]; if (rp[0] < 0) { dead = 2; break; }
      v0 += ccrt[c] * rp[0]; v1 += ccrt[c] * rp[1]; v2 += ccrt[c] * rp[2];
    }
    if (dead) { printf("rank %d dead %d\n", rk, dead); continue; }
    ll r = ((v0 % 12) + 12) % 12;
    printf("rank %d", rk);
    for (ll a0 = r; a0 <= A; a0 += 12) {
      ll k = (a0 - v0) / 12; ll b = v1 + k * U[1], c = v2 + k * U[2];
      int keep = lattice_keep(need_b0, need_c0, b, c);
      int K = KT[a0]; if (K > 18) K = 18;
      int fl = (K == 3 && LAMK[3] == 100) ? tail_flags((int)a0, b, c, 3, 100, 1000ULL) : tail_flags((int)a0, b, c, K, LAMK[K], pow10u[K]);
      printf(" | %lld %d %d", a0, keep, (fl & 2) != 0);
    }
    printf("\n");
  }
}

int main(int argc, char **argv) {
  if (argc >= 3 && !strcmp(argv[2], "-check")) {
    read_cfg(argv[1]); init_tail(); init_bs();
    if (argc > 3) mut_mode = atoi(argv[3]);
    for (int d = 2; d <= 9; d++) for (int r = 0; r < 12; r++) for (int i = 0; i < np; i++) Dd[d][r][i] = (((ll)(d - 1) * POW10[i][r]) % P[i] + P[i]) % P[i];
    for (int i = 0; i < np; i++) for (int j = 0; j < L; j++) R[i][j] = ((R[i][j] % P[i]) + P[i]) % P[i];
    check_mode(); return 0;
  }
  if (argc < 6) { fprintf(stderr, "usage: rs cfg multisets total_samples seed dumpfile [dump_prob] [mut_mode]\n"); return 1; }
  read_cfg(argv[1]); init_tail(); init_bs();
  ll total = atoll(argv[3]); seed((ull)atoll(argv[4]));
  dumpf = fopen(argv[5], "w"); if (argc > 6) dump_prob = atof(argv[6]); if (argc > 7) mut_mode = atoi(argv[7]);
  for (int d = 2; d <= 9; d++) for (int r = 0; r < 12; r++) for (int i = 0; i < np; i++) Dd[d][r][i] = (((ll)(d - 1) * POW10[i][r]) % P[i] + P[i]) % P[i];
  for (int i = 0; i < np; i++) for (int j = 0; j < L; j++) R[i][j] = ((R[i][j] % P[i]) + P[i]) % P[i];
  FILE *mf = fopen(argv[2], "r"); if (!mf) { perror("multisets"); return 1; }
  static double wt[1000]; static int mm[1000][7]; int nm = 0; double wsum = 0;
  while (1) { double w; int c[7]; if (fscanf(mf, "%lf %d %d %d %d %d %d %d", &w, &c[0], &c[1], &c[2], &c[3], &c[4], &c[5], &c[6]) != 8) break; wt[nm] = w; memcpy(mm[nm], c, sizeof c); wsum += w; nm++; }
  fclose(mf);
  const int dv[7] = {2, 3, 4, 6, 7, 8, 9};
  ll done = 0;
  for (int im = 0; im < nm; im++) {
    ll ns = (ll)((double)total * wt[im] / wsum + 0.5);
    q = 0; memset(cntmg, 0, sizeof cntmg);
    int grp_d[7], grp_m[7], ng = 0;
    for (int t = 0; t < 7; t++) { for (int j = 0; j < mm[im][t]; j++) digits[q++] = dv[t]; cntmg[dv[t]] = mm[im][t]; if (mm[im][t]) { grp_d[ng] = dv[t]; grp_m[ng] = mm[im][t]; ng++; } }
    bs_s1 = 0; for (int i = 0; i < q; i++) bs_s1 += digits[i] - 1;
    for (ll sidx = 0; sidx < ns; sidx++) {
      int nu = rnd_below(12);
      memset(pattern_has, 0, sizeof pattern_has);
      int pos = 0;
      for (int g = 0; g < ng; g++) { int cls[64]; draw_class_multiset(grp_m[g], cls); for (int j = 0; j < grp_m[g]; j++) { eps[pos++] = cls[j]; pattern_has[grp_d[g]][cls[j]]++; } }
      sample_pattern(nu);
    }
    done += ns;
  }
  printf("samples %lld\n", done);
  for (int rk = 0; rk < 3; rk++) printf("rank %d pat %lld zero %lld pre %lld surv %lld surv_keep %lld openpat %lld openpat_keep %lld\n", rk, cnt_pat[rk], cnt_zero[rk], cnt_pre[rk], cnt_surv[rk], cnt_surv_keep[rk], cnt_openpat[rk], cnt_openpat_keep[rk]);
  for (int ci = 0; ci < NCAP; ci++) for (int rk = 0; rk < 3; rk++) printf("cap %d rank %d lines %lld lines_keep %lld open %lld open_keep %lld\n", CAPS[ci], rk, cnt_lines[ci][rk], cnt_lines_keep[ci][rk], cnt_open[ci][rk], cnt_open_keep[ci][rk]);
  for (int rk = 0; rk < 3; rk++) { printf("a0hist rank %d:", rk); for (int r = 0; r < 12; r++) printf(" %lld/%lld", cnt_open_a0hist[rk][r], cnt_a0hist[rk][r]); printf("\n"); }
  fclose(dumpf);
  return 0;
}
