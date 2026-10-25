// idea (e): counting DP over Z/p0 (p0 <= 127, one bit per residue) + backtracking that visits only partial assignments
// from which at least one completion lands on the key prime's allowed set; every leaf is a join-equivalent candidate.
// LANE2_E=1 enables; LANE2_EORD orders the slots (0 natural, 1 largest multiplicity first, 2 smallest first).
static ull key_target(int i);
static void e2_init_fwd(void);
static int e_mode = 0, e_ord = 0, e_set = -1;
static u128 Qs_[MAXS + 1];
static unsigned char e_ks[MAXS];
static ull e_y[MAXS + 1][MAXP];
static int e_jp, e_S, e_order[MAXS]; static int e_p; static u128 e_mask;
static ll e_leaves = 0, e_nodes = 0;

static void e_init(void){
  const char *e = getenv("LANE2_E"); e_mode = e ? atoi(e) : 0; if(e_mode > 2) e_mode = 0;
  const char *o = getenv("LANE2_EORD"); e_ord = o ? atoi(o) : 0;
  if(!e_mode) return;
  if(e_mode == 2){ e2_init_fwd(); return; }
  double best = 1e9; e_set = -1;
  for(int s = 0; s < nsets; s++) if(sp1[s] < 0 && P[sp0[s]] <= 127 && sacc[s] < best){ best = sacc[s]; e_set = s; }
  if(e_set < 0) e_mode = 0;
}

static inline u128 e_trans(u128 x, int d){
  d %= e_p; if(d < 0) d += e_p; if(!d) return x;
  return ((x << d) | (x >> (e_p - d))) & e_mask;
}

static void e_leaf(void){
  e_leaves++;
  ull *y = e_y[e_S];
  for(int i = 0; i < np; i++) if(y[i] == 0){ cnt_zero++; return; }
  cnt_children++;
  if(bi0 < 0){ for(int s = 0; s < nslots; s++) for(int c = 0; c < slots[s].m; c++) cureps[slots[s].pos + c] = (c < e_ks[s]) ? slots[s].r + Lold : slots[s].r; process_rest(y); return; }
  if(prefilter_dead(y)){ cnt_dead++; return; }
  memcpy(bq[nbq].y, y, sizeof(ull) * np); memcpy(bq[nbq].ks, e_ks, (size_t)nslots); bq[nbq].ia = -2; if(++nbq == BQ) flush_bq();
}

static void e_dfs(int d, int v){
  int s = e_order[d]; int m = slots[s].m; u128 Q = Qs_[d + 1];
  ull *yin = e_y[d], *yout = e_y[d + 1];
  int last = (d + 1 == e_S);
  for(int k = 0; k <= m; k++){
    int v2 = v + (int)contrib_[s][k][e_jp]; if(v2 >= e_p) v2 -= e_p;
    if(!((Q >> v2) & 1)) continue;
    for(int i = 0; i < np; i++){ ull t = yin[i] + contrib_[s][k][i]; t -= (t >= P[i]) * P[i]; yout[i] = t; }
    e_ks[s] = (unsigned char)k;
    if(last) e_leaf(); else e_dfs(d + 1, v2);
  }
}

static void e_parent(int nu, double C0){
  int es = e_set; e_jp = sp0[es]; e_p = (int)P[e_jp]; e_mask = (e_p == 128) ? ~(u128)0 : ((((u128)1) << e_p) - 1);
  e_S = nslots;
  for(int d = 0; d < nslots; d++) e_order[d] = d;
  if(e_ord){ for(int a = 0; a < nslots; a++) for(int b = a + 1; b < nslots; b++){ int ma = slots[e_order[a]].m, mb = slots[e_order[b]].m; if(e_ord == 1 ? mb > ma : mb < ma){ int t = e_order[a]; e_order[a] = e_order[b]; e_order[b] = t; } } }
  Kx = sKx[es]; nK = sK[es];
  ull s0 = key_target(e_jp);
  ull Tl[512]; ll nT = 0;
  for(ll j = 0; j < nK && nT < 512; j++){
#ifdef JOIN_MUTANTS
    if(mutant == 3 && (j & 1)) continue;
#endif
    Tl[nT++] = mm32_(s0, Kx[j], (ull)e_p); }
  for(int dn = 0; dn < 2; dn++){
    nu_cur = nu + dn * Lold; jc_total += (ll)(C0 + 0.5);
    ull base[MAXP]; for(int i = 0; i < np; i++) base[i] = (ull)R[i][nu_cur];
    u128 Q = 0; for(ll j = 0; j < nT; j++){ ll v = (ll)Tl[j] - (ll)base[e_jp]; v %= e_p; if(v < 0) v += e_p; Q |= ((u128)1) << v; }
    Qs_[e_S] = Q;
    for(int d = e_S - 1; d >= 0; d--){
      int s = e_order[d]; u128 acc = 0;
      for(int k = 0; k <= slots[s].m; k++) acc |= e_trans(Qs_[d + 1], -(int)contrib_[s][k][e_jp]);
      Qs_[d] = acc;
    }
    if(!(Qs_[0] & 1)) { flush_bq(); continue; }
    for(int i = 0; i < np; i++) e_y[0][i] = base[i];
    e_dfs(0, 0);
    flush_bq();
  }
}

// ---- LANE2_E=2: LIFT-ADDITIVE style DP over Z/(p0*p1) (73*137 = 10001 by CRT), bitset of M bits, cyclic shifts ----
#define EW 160
static int e2_M, e2_W, e2_set; static ull e2_c0, e2_c1;
static ull Q2_[MAXS + 1][EW];
static ull e2_tmp[EW], e2_tmp2[EW];
static inline int e2_crt(ull x, ull y){ ull v = (x * e2_c0 + y * e2_c1) % (ull)e2_M; return (int)v; }
static void e2_shl(ull *dst, const ull *src, int d){
  int ws = d >> 6, bs = d & 63;
  for(int i = e2_W - 1; i >= 0; i--){ ull v = 0; int j = i - ws; if(j >= 0){ v = src[j] << bs; if(bs && j >= 1) v |= src[j - 1] >> (64 - bs); } dst[i] = v; }
  int topbits = e2_M & 63; if(topbits) dst[e2_W - 1] &= (1ULL << topbits) - 1;
}
static void e2_shr(ull *dst, const ull *src, int r){
  int ws = r >> 6, bs = r & 63;
  for(int i = 0; i < e2_W; i++){ ull v = 0; int j = i + ws; if(j < e2_W){ v = src[j] >> bs; if(bs && j + 1 < e2_W) v |= src[j + 1] << (64 - bs); } dst[i] = v; }
}
static void e2_rotl_or(ull *acc, const ull *src, int d){
  d %= e2_M; if(d < 0) d += e2_M;
  if(d == 0){ for(int i = 0; i < e2_W; i++) acc[i] |= src[i]; return; }
  e2_shl(e2_tmp, src, d); e2_shr(e2_tmp2, src, e2_M - d);
  for(int i = 0; i < e2_W; i++) acc[i] |= e2_tmp[i] | e2_tmp2[i];
}
static void e2_init(void){
  e2_set = -1;
  for(int s = 0; s < nsets; s++) if(sp1[s] >= 0 && P[sp0[s]] * P[sp1[s]] <= (ull)EW * 64 && (e2_set < 0 || sacc[s] < sacc[e2_set])) e2_set = s;
  if(e2_set < 0){ e_mode = 0; return; }
  ull p0 = P[sp0[e2_set]], p1 = P[sp1[e2_set]]; e2_M = (int)(p0 * p1); e2_W = (e2_M + 63) / 64;
  ull i0 = 0, i1 = 0;
  for(ull a = 1; a < p0; a++) if((a * p1) % p0 == 1) i0 = a;
  for(ull a = 1; a < p1; a++) if((a * p0) % p1 == 1) i1 = a;
  e2_c0 = p1 * i0; e2_c1 = p0 * i1;
}
static void e2_dfs(int d, int v){
  int s = e_order[d]; int m = slots[s].m; const ull *Q = Q2_[d + 1];
  ull *yin = e_y[d], *yout = e_y[d + 1]; int last = (d + 1 == e_S);
  int j0 = sp0[e2_set], j1 = sp1[e2_set];
  for(int k = 0; k <= m; k++){
    int v2 = v + e2_crt(contrib_[s][k][j0], contrib_[s][k][j1]); if(v2 >= e2_M) v2 -= e2_M;
    if(!((Q[v2 >> 6] >> (v2 & 63)) & 1)) continue;
    for(int i = 0; i < np; i++){ ull t = yin[i] + contrib_[s][k][i]; t -= (t >= P[i]) * P[i]; yout[i] = t; }
    e_ks[s] = (unsigned char)k;
    if(last) e_leaf(); else e2_dfs(d + 1, v2);
  }
}
static void e2_parent(int nu, double C0){
  int es = e2_set; int j0 = sp0[es], j1 = sp1[es]; ull p0 = P[j0], p1 = P[j1];
  e_S = nslots; for(int d = 0; d < nslots; d++) e_order[d] = d;
  Kx = sKx[es]; Ky = sKy[es]; nK = sK[es];
  ull s0 = key_target(j0), s1 = key_target(j1);
  static ull TL0[1024], TL1[1024]; ll nT = 0;
  for(ll j = 0; j < nK && nT < 1024; j++){
#ifdef JOIN_MUTANTS
    if(mutant == 3 && (j & 1)) continue;
#endif
    TL0[nT] = mm32_(s0, Kx[j], p0); TL1[nT] = mm32_(s1, Ky[j], p1); nT++; }
  static int cc[MAXS][64];
  for(int s = 0; s < nslots; s++) for(int k = 0; k <= slots[s].m; k++) cc[s][k] = e2_crt(contrib_[s][k][j0], contrib_[s][k][j1]);
  for(int dn = 0; dn < 2; dn++){
    nu_cur = nu + dn * Lold; jc_total += (ll)(C0 + 0.5);
    ull base[MAXP]; for(int i = 0; i < np; i++) base[i] = (ull)R[i][nu_cur];
    int bcrt = e2_crt(base[j0], base[j1]); if(getenv("E2DBG")) fprintf(stderr,"M %d W %d c0 %llu c1 %llu bcrt %d nT %lld j0 %d j1 %d\n", e2_M,e2_W,e2_c0,e2_c1,bcrt,nT,j0,j1);
    ull *Q = Q2_[e_S]; for(int w = 0; w < e2_W; w++) Q[w] = 0;
    for(ll j = 0; j < nT; j++){ int t = e2_crt(TL0[j], TL1[j]) - bcrt; if(t < 0) t += e2_M; Q[t >> 6] |= 1ULL << (t & 63); }
    for(int d = e_S - 1; d >= 0; d--){
      int s = e_order[d]; ull *A = Q2_[d]; for(int w = 0; w < e2_W; w++) A[w] = 0;
      for(int k = 0; k <= slots[s].m; k++) e2_rotl_or(A, Q2_[d + 1], e2_M - cc[s][k]);
    }
    if(!(Q2_[0][0] & 1)){ flush_bq(); continue; }
    for(int i = 0; i < np; i++) e_y[0][i] = base[i];
    e2_dfs(0, 0);
    flush_bq();
  }
}

static void e2_init_fwd(void){ e2_init(); }
