#include <math.h>
#include <time.h>
#define main lvlN_orig_main
#include "lvlNf.c"
#undef main
#include "gpu.h"

#define MAXS 64
typedef struct { int d, r, m, pos; } Slot;
typedef struct { int a, nu, pidx; i128 vb, vc; int nslots; Slot slots[MAXS]; int inA[MAXS]; ll nA, nB; ull *HA, *HB; ull base[2][MAXP]; } PR;

static ull pw(ull b, ll e, ull p){ ll m = (ll)(p - 1); e %= m; if(e < 0) e += m; return powmod(b, (ull)e, p); }
static double now_s(void){ struct timespec t; clock_gettime(CLOCK_MONOTONIC, &t); return t.tv_sec + 1e-9 * t.tv_nsec; }

static int build_K1(int i0, ll limit, ull **ox, ll *on){
  ull g[2];
  for(int v = 0; v < 2; v++) g[v] = mulmod(pw(3, Uold[v][0], P[i0]), pw(7, Uold[v][1], P[i0]), P[i0]);
  ull *qx = malloc(sizeof(ull) * limit); ll n = 1; qx[0] = 1;
  ull hs = 1; while(hs < (ull)(4 * limit)) hs <<= 1;
  ull *tab = malloc(sizeof(ull) * hs); for(ull i = 0; i < hs; i++) tab[i] = ~0ULL;
  tab[(1ULL * 11400714819323198485ULL) & (hs - 1)] = 1;
  for(ll h = 0; h < n; h++) for(int v = 0; v < 2; v++){
    ull x = mulmod(qx[h], g[v], P[i0]); ull s = (x * 11400714819323198485ULL) & (hs - 1); int found = 0;
    while(tab[s] != ~0ULL){ if(tab[s] == x){ found = 1; break; } s = (s + 1) & (hs - 1); }
    if(found) continue;
    if(n >= limit){ free(tab); free(qx); return 0; }
    tab[s] = x; qx[n++] = x; }
  free(tab); *ox = qx; *on = n; return 1;
}

static void fill(const PR *pr, int want, ull *H, ll cnt, ull contrib[MAXS][64][MAXP]){
  int idxs[MAXS], ns = 0;
  for(int s = 0; s < pr->nslots; s++) if(pr->inA[s] == want) idxs[ns++] = s;
  for(ll t = 0; t < cnt; t++){
    ll rest = t; ull acc[MAXP]; for(int i = 0; i < np; i++) acc[i] = 0;
    for(int u = 0; u < ns; u++){ int s = idxs[u]; int rad = pr->slots[s].m + 1; int k = (int)(rest % rad); rest /= rad;
      for(int i = 0; i < np; i++) acc[i] += contrib[s][k][i]; }
    for(int i = 0; i < np; i++) H[t * np + i] = acc[i] % P[i];
  }
}
static void decode(const PR *pr, int want, ll t, int *ks){
  ll rest = t;
  for(int s = 0; s < pr->nslots; s++) if(pr->inA[s] == want){ int rad = pr->slots[s].m + 1; ks[s] = (int)(rest % rad); rest /= rad; }
}

static int cmpc(const void *a, const void *b){
  const u32 *x = a, *y = b; u32 kx = (x[0] << 1) | x[1], ky = (y[0] << 1) | y[1];
  if(kx != ky) return kx < ky ? -1 : 1; return 0;
}

static double gpu_s = 0, cpu_cand_s = 0, prep_s = 0; static ll g_cand = 0, g_total = 0, g_retry = 0;
static int i0g, i1g; static u32 *bmk[2];

static void process_range(PR *prs, int lo, int hi, u32 *HA0, u32 *HA1, u32 *HB0, u32 *HB1, size_t *offA, size_t *offB, ull *s0v, ull *s1v, ull *W){
  u32 cap = 1u << 22;
  PInfo *pi = calloc(hi - lo, sizeof(PInfo));
  u32 p0 = (u32)P[i0g], p1 = (u32)P[i1g];
  for(int j = lo; j < hi; j++){ PInfo *x = &pi[j - lo]; PR *pr = &prs[j];
    x->nA = (u32)pr->nA; x->nB = (u32)pr->nB; x->offA = (u32)offA[j]; x->offB = (u32)offB[j];
    x->b00 = (u32)(pr->base[0][i0g] % p0); x->b01 = (u32)(pr->base[1][i0g] % p0); x->b10 = (u32)(pr->base[0][i1g] % p1); x->b11 = (u32)(pr->base[1][i1g] % p1);
    x->w0 = (u32)W[2 * j]; x->w0s = (u32)(((u128)W[2 * j] << 32) / p0); x->w1 = (u32)W[2 * j + 1]; x->w1s = (u32)(((u128)W[2 * j + 1] << 32) / p1); }
  u32 *out = malloc((size_t)cap * 16);
  size_t a0 = offA[lo], a1 = (hi < 0) ? 0 : offA[hi], b0 = offB[lo], b1 = offB[hi];
  for(int j = lo; j < hi; j++){ pi[j - lo].offA -= (u32)a0; pi[j - lo].offB -= (u32)b0; }
  long n = gpu_batch(hi - lo, pi, HA0 + a0, a1 - a0, HA1 + a0, HB0 + b0, b1 - b0, HB1 + b0, cap, out, &gpu_s);
  if(n == -1){ g_retry++; free(out); free(pi); if(hi - lo == 1){ fprintf(stderr, "candidate buffer overflow on single parent\n"); exit(10); }
    int mid = (lo + hi) / 2; process_range(prs, lo, mid, HA0, HA1, HB0, HB1, offA, offB, s0v, s1v, W); process_range(prs, mid, hi, HA0, HA1, HB0, HB1, offA, offB, s0v, s1v, W); return; }
  if(n < 0){ fprintf(stderr, "gpu failure\n"); exit(11); }
  double t0 = now_s();
  qsort(out, n, 16, cmpc); g_cand += n;
  int curj = -1, curdn = -1;
  for(long c = 0; c < n; c++){
    u32 *r = out + 4 * c; int j = lo + (int)r[0], dn = (int)r[1]; PR *pr = &prs[j];
    if(j != curj || dn != curdn){
      flush_bq();
      if(j != curj){ pidx_cur = pr->pidx; a_cur = pr->a; vb_cur = pr->vb; vc_cur = pr->vc; parent_init(); curj = j; }
      curdn = dn; nu_cur = pr->nu + dn * Lold; }
    ll ia = r[2], ib = r[3]; int ks[MAXS];
    decode(pr, 1, ia, ks); decode(pr, 0, ib, ks);
    for(int s = 0; s < pr->nslots; s++) for(int cc = 0; cc < pr->slots[s].m; cc++) cureps[pr->slots[s].pos + cc] = (cc < ks[s]) ? pr->slots[s].r + Lold : pr->slots[s].r;
    for(int i = 0; i < np; i++) ycur[i] = (pr->base[dn][i] + pr->HA[ia * np + i] + pr->HB[ib * np + i]) % P[i];
    process_child();
  }
  flush_bq();
  cpu_cand_s += now_s() - t0;
  free(out); free(pi);
}

int main(int argc, char **argv){
  if(argc < 3){ fprintf(stderr, "usage: lvlG cfg parents\n"); return 1; }
  int gmut = 0; { const char *e = getenv("GPU_MUTANT"); if(e) gmut = atoi(e); }
  double tstart = now_s();
  read_cfg(argv[1]); lazy_init(); batch_init();
  ng = 0; for(int i = 0; i < q; i++){ if(ng == 0 || gd[ng - 1] != digits[i]){ gd[ng] = digits[i]; gstart[ng] = i; gk[ng] = 1; ng++; } else gk[ng - 1]++; }
  ull *Kx[MAXP]; ll nKk[MAXP]; int ok[MAXP]; double acc[MAXP];
  for(int i = 0; i < np; i++){ ok[i] = 0; if(P[i] < (1ULL << 27) && build_K1(i, 400000, &Kx[i], &nKk[i])){ ok[i] = 1; acc[i] = (double)nKk[i] / (double)(P[i] - 1); } }
  i0g = -1; i1g = -1;
  for(int i = 0; i < np; i++) if(ok[i] && (i0g < 0 || acc[i] < acc[i0g])) i0g = i;
  if(i0g < 0){ fprintf(stderr, "no GPU key prime\n"); return 2; }
  for(int i = 0; i < np; i++) if(ok[i] && i != i0g && (i1g < 0 || acc[i] < acc[i1g])) i1g = i;
  if(i1g < 0) i1g = i0g;
  if(getenv("GPU_SMALLFIRST") && i1g != i0g && P[i1g] < P[i0g]){ int t = i0g; i0g = i1g; i1g = t; }
  u32 p0 = (u32)P[i0g], p1 = (u32)P[i1g];
  size_t w0 = (p0 >> 5) + 1, w1 = (p1 >> 5) + 1;
  bmk[0] = calloc(w0, 4); bmk[1] = calloc(w1, 4);
  for(int t = 0; t < 2; t++){ int ii = t ? i1g : i0g; u32 *bm = bmk[t];
    for(ll j = 0; j < nKk[ii]; j++){ if(gmut == 1 && t == 0 && (j & 1)) continue; ull x = Kx[ii][j]; bm[x >> 5] |= 1u << (x & 31); } }
  if(gpu_init(bmk[0], w0, bmk[1], w1, p0, p1)) return 3;
  FILE *pf = fopen(argv[2], "r"); if(!pf){ perror("parents"); return 1; }
  char line[4096]; int pidx = 0;
  enum { MAXB = 8192 }; PR *prs = calloc(MAXB, sizeof(PR));
  ull *Ws = malloc(sizeof(ull) * 2 * MAXB);
  int eof = 0;
  while(!eof){
    int nb = 0; double kids = 0; size_t totA = 0, totB = 0;
    size_t capA = 1 << 16, capB = 1 << 16;
    u32 *HA0 = malloc(4 * capA), *HA1 = malloc(4 * capA), *HB0 = malloc(4 * capB), *HB1 = malloc(4 * capB);
    size_t *offA = malloc(sizeof(size_t) * (MAXB + 1)), *offB = malloc(sizeof(size_t) * (MAXB + 1));
    double tp = now_s();
    while(nb < MAXB && kids < 6e8){
      if(!fgets(line, sizeof line, pf)){ eof = 1; break; }
      int a, nu; if(sscanf(line, "%d %d", &a, &nu) != 2) continue;
      PR *pr = &prs[nb];
      char *tok = strtok(line, " \n"); a = atoi(tok); tok = strtok(NULL, " \n"); nu = atoi(tok);
      for(int i = 0; i < q; i++){ tok = strtok(NULL, " \n"); parent_eps[i] = atoi(tok); }
      tok = strtok(NULL, " \n"); pr->vb = parse128(tok); tok = strtok(NULL, " \n"); pr->vc = parse128(tok);
      pr->a = a; pr->nu = nu; pr->pidx = pidx++;
      pr->nslots = 0; int pos = 0; double C0 = 1;
      for(int g = 0; g < ng; g++){
        int nd = 0; int dv[MAXQ], dm[MAXQ];
        for(int i = gstart[g]; i < gstart[g] + gk[g]; i++){ int r = parent_eps[i]; int f = -1; for(int j = 0; j < nd; j++) if(dv[j] == r) f = j; if(f < 0){ dv[nd] = r; dm[nd] = 1; nd++; } else dm[f]++; }
        for(int j = 0; j < nd; j++){ Slot *sl = &pr->slots[pr->nslots]; sl->d = gd[g]; sl->r = dv[j]; sl->m = dm[j]; sl->pos = pos; pos += dm[j]; C0 *= (dm[j] + 1); pr->nslots++; }
      }
      double target = sqrt(C0); if(target < 1) target = 1; double prodA = 1;
      for(int s = 0; s < pr->nslots; s++){ int rad = pr->slots[s].m + 1; if(prodA * rad <= target * 1.5){ pr->inA[s] = 1; prodA *= rad; } else pr->inA[s] = 0; }
      pr->nA = (ll)prodA; pr->nB = (ll)(C0 / prodA + 0.5);
      if(pr->nB > 30000000LL){ fprintf(stderr, "half too large\n"); return 4; }
      static ull contrib[MAXS][64][MAXP];
      for(int s = 0; s < pr->nslots; s++) for(int k = 0; k <= pr->slots[s].m; k++) for(int i = 0; i < np; i++){
        ull ds = (ull)(pr->slots[s].d - 1) * ((ull)(pr->slots[s].m - k) * (ull)POW10[i][pr->slots[s].r] + (ull)k * (ull)POW10[i][pr->slots[s].r + Lold]);
        contrib[s][k][i] = ds % P[i]; }
      pr->HA = malloc(sizeof(ull) * pr->nA * np); pr->HB = malloc(sizeof(ull) * pr->nB * np);
      fill(pr, 1, pr->HA, pr->nA, contrib); fill(pr, 0, pr->HB, pr->nB, contrib);
      for(int dn = 0; dn < 2; dn++) for(int i = 0; i < np; i++) pr->base[dn][i] = (ull)R[i][nu + dn * Lold];
      while(totA + pr->nA > capA){ capA *= 2; HA0 = realloc(HA0, 4 * capA); HA1 = realloc(HA1, 4 * capA); }
      while(totB + pr->nB > capB){ capB *= 2; HB0 = realloc(HB0, 4 * capB); HB1 = realloc(HB1, 4 * capB); }
      offA[nb] = totA; offB[nb] = totB;
      for(ll t = 0; t < pr->nA; t++){ HA0[totA + t] = (u32)pr->HA[t * np + i0g]; HA1[totA + t] = (u32)pr->HA[t * np + i1g]; }
      for(ll t = 0; t < pr->nB; t++){ HB0[totB + t] = (u32)pr->HB[t * np + i0g]; HB1[totB + t] = (u32)pr->HB[t * np + i1g]; }
      totA += pr->nA; totB += pr->nB;
      ull sv0 = mulmod(powmod(2, (ull)a, P[i0g]), mulmod(pw(3, (ll)mod128(pr->vb, (i128)(P[i0g] - 1)), P[i0g]), pw(7, (ll)mod128(pr->vc, (i128)(P[i0g] - 1)), P[i0g]), P[i0g]), P[i0g]);
      ull sv1 = mulmod(powmod(2, (ull)a, P[i1g]), mulmod(pw(3, (ll)mod128(pr->vb, (i128)(P[i1g] - 1)), P[i1g]), pw(7, (ll)mod128(pr->vc, (i128)(P[i1g] - 1)), P[i1g]), P[i1g]), P[i1g]);
      Ws[2 * nb] = invmod(sv0, P[i0g]); Ws[2 * nb + 1] = invmod(sv1, P[i1g]);
      kids += 2 * C0; g_total += (ll)(2 * C0 + 0.5); nb++;
    }
    offA[nb] = totA; offB[nb] = totB;
    prep_s += now_s() - tp;
    if(nb > 0) process_range(prs, 0, nb, HA0, HA1, HB0, HB1, offA, offB, NULL, NULL, Ws);
    for(int j = 0; j < nb; j++){ free(prs[j].HA); free(prs[j].HB); }
    free(HA0); free(HA1); free(HB0); free(HB1); free(offA); free(offB);
  }
  cnt_children = g_total;
  fprintf(stderr, "gpu_us %lld cpu_cand_us %lld prep_us %lld total_us %lld gcand %lld retry %lld ", (ll)(gpu_s * 1e6), (ll)(cpu_cand_s * 1e6), (ll)(prep_s * 1e6), (ll)((now_s() - tstart) * 1e6), g_cand, g_retry);
  fprintf(stderr, "p0 %llu p1 %llu parents %d children %lld zero %lld dead %lld tail-dead %lld open %lld exact %lld\n", P[i0g], P[i1g], pidx, cnt_children, cnt_zero, cnt_dead, cnt_tail_dead, cnt_open, cnt_exact);
  return 0;
}
