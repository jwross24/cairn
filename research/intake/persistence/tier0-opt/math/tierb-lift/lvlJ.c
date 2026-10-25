#include <math.h>
#define main lvlN_orig_main
#include "../../../tier0/lvlN.c"
#undef main

#define MAXS 64
typedef struct { int d, r, m, pos; } Slot;
static Slot slots[MAXS]; static int nslots;
static int jp0 = -1, jp1 = -1;
static ull *Kx, *Ky; static ll nK;
static int mutant = 0;
static ll jc_total = 0, jc_probe = 0, jc_cand = 0, jc_build = 0;

static ull pw(ull b, ll e, ull p){ ll m = (ll)(p - 1); e %= m; if(e < 0) e += m; return powmod(b, (ull)e, p); }

static int build_K(int i0, int i1, ll limit, ull **ox, ull **oy, ll *on){
  ull g[2][2];
  for(int v = 0; v < 2; v++){
    g[v][0] = mulmod(pw(3, Uold[v][0], P[i0]), pw(7, Uold[v][1], P[i0]), P[i0]);
    g[v][1] = mulmod(pw(3, Uold[v][0], P[i1]), pw(7, Uold[v][1], P[i1]), P[i1]);
  }
  ull hs = 1; while(hs < (ull)(4 * limit)) hs <<= 1;
  ull *tab = malloc(sizeof(ull) * hs); for(ull i = 0; i < hs; i++) tab[i] = ~0ULL;
  ull *qx = malloc(sizeof(ull) * limit), *qy = malloc(sizeof(ull) * limit); ll n = 0;
  ull key0 = 1 * P[i1] + 1; tab[(key0 * 11400714819323198485ULL) & (hs - 1)] = key0; qx[0] = 1; qy[0] = 1; n = 1;
  for(ll h = 0; h < n; h++){
    for(int v = 0; v < 2; v++){
      ull x = mulmod(qx[h], g[v][0], P[i0]), y = mulmod(qy[h], g[v][1], P[i1]); ull key = x * P[i1] + y;
      ull s = (key * 11400714819323198485ULL) & (hs - 1); int found = 0;
      while(tab[s] != ~0ULL){ if(tab[s] == key){ found = 1; break; } s = (s + 1) & (hs - 1); }
      if(found) continue;
      if(n >= limit){ free(tab); free(qx); free(qy); return 0; }
      tab[s] = key; qx[n] = x; qy[n] = y; n++;
    }
  }
  free(tab); *ox = qx; *oy = qy; *on = n; return 1;
}

static int dvals_[MAXS], dmult_[MAXS];
static ull *HA, *HB; static ll nA, nB;
static int inA[MAXS];
static ll *head, *nxt; static ull hsB;

static void fill_half(int want, ull *H, ll cnt, ull contrib[MAXS][64][MAXP]){
  int idxs[MAXS], ns = 0;
  for(int s = 0; s < nslots; s++) if(inA[s] == want) idxs[ns++] = s;
  for(ll t = 0; t < cnt; t++){
    ll rest = t; ull acc[MAXP]; for(int i = 0; i < np; i++) acc[i] = 0;
    for(int u = 0; u < ns; u++){ int s = idxs[u]; int rad = slots[s].m + 1; int k = (int)(rest % rad); rest /= rad;
      for(int i = 0; i < np; i++) acc[i] += contrib[s][k][i]; }
    for(int i = 0; i < np; i++) H[t * np + i] = acc[i] % P[i];
  }
}

static void decode_half(int want, ll t, int *ks){
  ll rest = t;
  for(int s = 0; s < nslots; s++) if(inA[s] == want){ int rad = slots[s].m + 1; ks[s] = (int)(rest % rad); rest /= rad; }
}

static ull contrib_[MAXS][64][MAXP];

#define MAXSETS 16
static int nsets, sp0[MAXSETS], sp1[MAXSETS]; static ll sK[MAXSETS]; static ull *sKx[MAXSETS], *sKy[MAXSETS]; static double sacc[MAXSETS];
static double w_probe = 20, w_cand = 100, w_build = 10;

static int build_K1(int i0, ll limit, ull **ox, ull **oy, ll *on){
  ull g[2];
  for(int v = 0; v < 2; v++) g[v] = mulmod(pw(3, Uold[v][0], P[i0]), pw(7, Uold[v][1], P[i0]), P[i0]);
  ull *qx = malloc(sizeof(ull) * limit); ll n = 1; qx[0] = 1;
  ull hs = 1; while(hs < (ull)(4 * limit)) hs <<= 1;
  char *seen = calloc(hs, 1); (void)seen;
  ull *tab = malloc(sizeof(ull) * hs); for(ull i = 0; i < hs; i++) tab[i] = ~0ULL;
  tab[(1ULL * 11400714819323198485ULL) & (hs - 1)] = 1;
  for(ll h = 0; h < n; h++) for(int v = 0; v < 2; v++){
    ull x = mulmod(qx[h], g[v], P[i0]); ull s = (x * 11400714819323198485ULL) & (hs - 1); int found = 0;
    while(tab[s] != ~0ULL){ if(tab[s] == x){ found = 1; break; } s = (s + 1) & (hs - 1); }
    if(found) continue;
    if(n >= limit){ free(tab); free(qx); free(seen); return 0; }
    tab[s] = x; qx[n++] = x;
  }
  free(tab); free(seen); *ox = qx; *oy = calloc(n, sizeof(ull)); *on = n; return 1;
}

int main(int argc, char **argv){
  if(argc < 3){ fprintf(stderr, "usage: lvlJ cfg parents\n"); return 1; }
  const char *me = getenv("JOIN_MUTANT"); if(me) mutant = atoi(me);
  const char *fs = getenv("JOIN_FORCE_SET"); int force = fs ? atoi(fs) : -1;
  const char *wp = getenv("JOIN_WP"); if(wp) w_probe = atof(wp);
  const char *wc = getenv("JOIN_WC"); if(wc) w_cand = atof(wc);
  read_cfg(argv[1]); lazy_init(); batch_init();
  ng = 0; for(int i = 0; i < q; i++){ if(ng == 0 || gd[ng - 1] != digits[i]){ gd[ng] = digits[i]; gstart[ng] = i; gk[ng] = 1; ng++; } else gk[ng - 1]++; }
  nsets = 0; ll maxK = 1;
  for(int i = 0; i < np; i++){
    ull *x, *y; ll n;
    if(build_K1(i, 400000, &x, &y, &n)){ sp0[nsets] = i; sp1[nsets] = -1; sK[nsets] = n; sKx[nsets] = x; sKy[nsets] = y; sacc[nsets] = (double)n / (double)(P[i] - 1); nsets++; if(n > maxK) maxK = n; }
  }
  if(np >= 3) for(int i = 0; i < np; i++) for(int j = i + 1; j < np; j++){
    ull *x, *y; ll n;
    if(build_K(i, j, 400000, &x, &y, &n)){ sp0[nsets] = i; sp1[nsets] = j; sK[nsets] = n; sKx[nsets] = x; sKy[nsets] = y; sacc[nsets] = (double)n / ((double)(P[i] - 1) * (double)(P[j] - 1)); nsets++; if(n > maxK) maxK = n; }
  }
  if(nsets == 0){ fprintf(stderr, "no usable key set (np=%d)\n", np); return 2; }
  FILE *pf = fopen(argv[2], "r"); if(!pf){ perror("parents"); return 1; }
  char line[4096]; int pidx = 0;
  ull *Tp0 = malloc(sizeof(ull) * maxK), *Tp1 = malloc(sizeof(ull) * maxK);
  ll setuse[MAXSETS]; for(int i = 0; i < MAXSETS; i++) setuse[i] = 0;
  while(fgets(line, sizeof line, pf)){
    int a, nu; if(sscanf(line, "%d %d", &a, &nu) != 2) continue;
    char *tok = strtok(line, " \n"); a = atoi(tok); tok = strtok(NULL, " \n"); nu = atoi(tok);
    for(int i = 0; i < q; i++){ tok = strtok(NULL, " \n"); parent_eps[i] = atoi(tok); }
    tok = strtok(NULL, " \n"); vb_cur = parse128(tok); tok = strtok(NULL, " \n"); vc_cur = parse128(tok);
    pidx_cur = pidx; a_cur = a; parent_init();

    nslots = 0; int pos = 0; double C0 = 1;
    for(int g = 0; g < ng; g++){
      int nd = 0; int dv[MAXQ], dm[MAXQ];
      for(int i = gstart[g]; i < gstart[g] + gk[g]; i++){ int r = parent_eps[i]; int f = -1; for(int j = 0; j < nd; j++) if(dv[j] == r) f = j; if(f < 0){ dv[nd] = r; dm[nd] = 1; nd++; } else dm[f]++; }
      for(int j = 0; j < nd; j++){ slots[nslots].d = gd[g]; slots[nslots].r = dv[j]; slots[nslots].m = dm[j]; slots[nslots].pos = pos; pos += dm[j]; C0 *= (dm[j] + 1); nslots++; }
    }
    int bs = 0; double bestc = 1e300;
    for(int s = 0; s < nsets; s++){
      double K = (double)sK[s]; double na = sqrt(C0 / K); if(na < 1) na = 1;
      double cost = w_probe * na * K + w_build * (na + C0 / na) + w_cand * C0 * sacc[s];
      if(cost < bestc){ bestc = cost; bs = s; }
    }
    if(force >= 0 && force < nsets) bs = force;
    setuse[bs]++;
    jp0 = sp0[bs]; jp1 = sp1[bs]; Kx = sKx[bs]; Ky = sKy[bs]; nK = sK[bs];
    ull p0 = P[jp0], p1 = jp1 >= 0 ? P[jp1] : 1;
    double target = sqrt(C0 / (double)nK); if(target < 1) target = 1;
    double prodA = 1; nA = 1;
    for(int s = 0; s < nslots; s++){ int rad = slots[s].m + 1; if(prodA * rad <= target * 1.5){ inA[s] = 1; prodA *= rad; } else inA[s] = 0; }
    nA = (ll)prodA; nB = (ll)(C0 / prodA + 0.5);
    if(nB > 30000000LL){ fprintf(stderr, "half too large: %lld\n", nB); return 3; }
    for(int s = 0; s < nslots; s++) for(int k = 0; k <= slots[s].m; k++) for(int i = 0; i < np; i++){
      ull ds = (ull)(slots[s].d - 1) * ((ull)(slots[s].m - k) * (ull)POW10[i][slots[s].r] + (ull)k * (ull)POW10[i][slots[s].r + Lold]);
      contrib_[s][k][i] = ds % P[i]; }
    HA = realloc(HA, sizeof(ull) * nA * np); HB = realloc(HB, sizeof(ull) * nB * np);
    fill_half(1, HA, nA, contrib_); fill_half(0, HB, nB, contrib_);
    hsB = 1; while(hsB < (ull)(2 * nB)) hsB <<= 1;
    head = realloc(head, sizeof(ll) * hsB); nxt = realloc(nxt, sizeof(ll) * nB);
    for(ull h = 0; h < hsB; h++) head[h] = -1;
    for(ll t = 0; t < nB; t++){ ull key = HB[t * np + jp0] * p1 + (jp1 >= 0 ? HB[t * np + jp1] : 0); ull h = (key * 11400714819323198485ULL) & (hsB - 1); nxt[t] = head[h]; head[h] = t; }
    jc_build += nA + nB;

    ull s0 = powmod(2, (ull)a, p0), s1 = jp1 >= 0 ? powmod(2, (ull)a, p1) : 0;
    if(mutant == 2){ s0 = 1; if(jp1 >= 0) s1 = 1; }
    s0 = mulmod(s0, mulmod(pw(3, (ll)mod128(vb_cur, (i128)(p0 - 1)), p0), pw(7, (ll)mod128(vc_cur, (i128)(p0 - 1)), p0), p0), p0);
    if(jp1 >= 0) s1 = mulmod(s1, mulmod(pw(3, (ll)mod128(vb_cur, (i128)(p1 - 1)), p1), pw(7, (ll)mod128(vc_cur, (i128)(p1 - 1)), p1), p1), p1);
    ll nT = 0;
    for(ll j = 0; j < nK; j++){ if(mutant == 1 && j % 8 == 3) continue; Tp0[nT] = mulmod(s0, Kx[j], p0); Tp1[nT] = jp1 >= 0 ? mulmod(s1, Ky[j], p1) : 0; nT++; }

    for(int dn = 0; dn < 2; dn++){
      nu_cur = nu + dn * Lold; jc_total += (ll)(C0 + 0.5);
      ull base[MAXP]; for(int i = 0; i < np; i++) base[i] = (ull)R[i][nu_cur];
      for(ll ia = 0; ia < nA; ia++){
        ull *av = &HA[ia * np];
        for(ll j = 0; j < nT; j++){
          ull x = Tp0[j] + 2 * p0 - base[jp0] - av[jp0]; x -= (x >= p0) * p0; x -= (x >= p0) * p0;
          ull y = 0;
          if(jp1 >= 0){ y = Tp1[j] + 2 * p1 - base[jp1] - av[jp1]; y -= (y >= p1) * p1; y -= (y >= p1) * p1; }
          ull key = x * p1 + y; ull h = (key * 11400714819323198485ULL) & (hsB - 1);
          jc_probe++;
          for(ll t = head[h]; t >= 0; t = nxt[t]){
            if(HB[t * np + jp0] != x || (jp1 >= 0 && HB[t * np + jp1] != y)) continue;
            jc_cand++;
            int ks[MAXS]; decode_half(1, ia, ks); decode_half(0, t, ks);
            for(int s = 0; s < nslots; s++) for(int c = 0; c < slots[s].m; c++) cureps[slots[s].pos + c] = (c < ks[s]) ? slots[s].r + Lold : slots[s].r;
            for(int i = 0; i < np; i++) ycur[i] = (base[i] + av[i] + HB[t * np + i]) % P[i];
            process_child();
          }
        }
      }
      flush_bq();
    }
    pidx++;
  }
  cnt_children = jc_total;
  fprintf(stderr, "parents %d children %lld zero %lld dead %lld tail-dead %lld open %lld exact %lld probes %lld cands %lld built %lld nsets %d", pidx, cnt_children, cnt_zero, cnt_dead, cnt_tail_dead, cnt_open, cnt_exact, jc_probe, jc_cand, jc_build, nsets);
  for(int s = 0; s < nsets; s++) fprintf(stderr, " set%d_%d_%d_K%lld_used %lld", s, sp0[s], sp1[s], sK[s], setuse[s]);
  fprintf(stderr, "\n");
  return 0;
}
