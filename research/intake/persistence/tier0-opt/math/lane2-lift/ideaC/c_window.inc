// idea (c): 10-adic window before the residue test. The tail test reads the low K digits of 2^a 3^b' 7^c' with (b',c') = (b,c) + t.Uold; they depend on
// t only through a small number of classes (t1 mod T1p, t2 mod T2p). A class survives the window only if every non-1 digit d_i at position i < K is
// carried by an UNLIFTED child digit d_i at residue i. Slots with residue < K are moved to the front of the slot order (least significant digits of the
// A half), and an A-index whose window pattern leaves no viable class is skipped before any probe.
// LANE2_C=1 enables, LANE2_CMUT=1 plants an over-pruning mutant.
static int c_allzero = 0; static ll c_skipped_parents = 0; static int c_force = 0; static int c_mode = 0, c_mut = 0, c_active = 0;
static int c_nviable; static unsigned c_req[256]; static ll c_prodWA; static unsigned char *c_okw = NULL; static ll c_okw_cap = 0;
static int c_nwin; static int c_winslot[MAXS];
static ll c_skipped = 0, c_total_ia = 0, c_parents_dead = 0, c_parents = 0;
static ull *c_tab3[20], *c_tab7[20], c_lam[20]; static ull c_tab2[20][1024]; static int c_tab2_ok[20][1024];

static void c_init(void){ const char *e = getenv("LANE2_C"); c_mode = e && *e == '1' && Lold == 12; { const char *f = getenv("LANE2_CFORCE"); c_force = f && *f == '1'; } const char *m = getenv("LANE2_CMUT"); c_mut = m ? atoi(m) : 0; }

static ull c_gcd(ull a, ull b){ while(b){ ull t = a % b; a = b; b = t; } return a; }
static void c_tables(int K){
  if(c_tab3[K]) return;
  ull l5 = 4; for(int i = 1; i < K; i++) l5 *= 5; ull l2 = K >= 3 ? (1ULL << (K - 2)) : 1;
  ull lam = l5 / c_gcd(l5, l2) * l2; c_lam[K] = lam;
  ull M = 1; for(int i = 0; i < K; i++) M *= 10;
  c_tab3[K] = malloc(sizeof(ull) * lam); c_tab7[K] = malloc(sizeof(ull) * lam);
  ull x = 1 % M, y = 1 % M; for(ull e = 0; e < lam; e++){ c_tab3[K][e] = x; c_tab7[K][e] = y; x = x * 3 % M; y = y * 7 % M; }
}

static ll c_modl(i128 v, ull lam){ i128 r = v % (i128)lam; if(r < 0) r += lam; return (ll)r; }

static void c_prepare(void){
  c_active = 0; c_nwin = 0; c_parents++;
  if(!c_mode) return;
  int K = KT[a_cur]; if(K > 18) K = 18;
  if(K < 1 || K > 9) return;
  c_tables(K);
  ull lam = c_lam[K]; ull M = 1; for(int i = 0; i < K; i++) M *= 10;
  ull T1p = lam / c_gcd(lam, c_gcd((ull)llabs(Uold[0][0]) % lam, (ull)llabs(Uold[0][1]) % lam));
  ull T2p = lam / c_gcd(lam, c_gcd((ull)llabs(Uold[1][0]) % lam, (ull)llabs(Uold[1][1]) % lam));
  if(T1p * T2p > 4096) return;
  if(a_cur >= 1024) return;
  if(!c_tab2_ok[K][a_cur]){ c_tab2[K][a_cur] = powmod(2, (ull)a_cur, M); c_tab2_ok[K][a_cur] = 1; }
  ull y2 = c_tab2[K][a_cur];
  int cntm[10] = {0}; for(int i = 0; i < q; i++) cntm[digits[i]]++;
  int wslot[MAXS], nw = 0;
  for(int s = 0; s < nslots; s++) if(slots[s].r < K) wslot[nw++] = s;
  if(nw > 20) return;
  c_nviable = 0;
  for(ull t1 = 0; t1 < T1p; t1++) for(ull t2 = 0; t2 < T2p; t2++){
    ll bb = c_modl((i128)vb_cur + (i128)t1 * Uold[0][0] + (i128)t2 * Uold[1][0], lam);
    ll cc = c_modl((i128)vc_cur + (i128)t1 * Uold[0][1] + (i128)t2 * Uold[1][1], lam);
    ull Y = y2 * c_tab3[K][bb] % M * c_tab7[K][cc] % M;
    int dg[10]; ull tt = Y; int dead = 0; int have[10] = {0};
    for(int i = 0; i < K; i++){ dg[i] = (int)(tt % 10); tt /= 10; }
    unsigned req = 0;
    for(int i = 0; i < K && !dead; i++){
      int d = dg[i]; if(d == 0){ dead = 1; break; } if(d == 1) continue;
      have[d]++; if(have[d] > cntm[d]){ dead = 1; break; }
      int found = -1; for(int w = 0; w < nw; w++){ int s = wslot[w]; if(slots[s].d == d && slots[s].r == ((c_mut == 2) ? i + 1 : i)) found = w; }
      if(found < 0){ dead = 1; break; }
      req |= 1u << found;
    }
    if(dead) continue;
    if(c_nviable < 256) c_req[c_nviable++] = req; else return;
  }
  c_nwin = nw; for(int w = 0; w < nw; w++) c_winslot[w] = wslot[w];
  c_active = 1;
  if(c_nviable == 0) c_parents_dead++;
}

static void c_reorder_slots(void){
  if(!c_active) return;
  Slot tmp[MAXS]; int n = 0;
  int isw[MAXS]; for(int s = 0; s < nslots; s++) isw[s] = 0;
  for(int w = 0; w < c_nwin; w++) isw[c_winslot[w]] = 1;
  int newidx_of_w[20]; int wi = 0;
  for(int s = 0; s < nslots; s++) if(isw[s]){ tmp[n] = slots[s]; newidx_of_w[wi++] = n; n++; }
  for(int s = 0; s < nslots; s++) if(!isw[s]) tmp[n++] = slots[s];
  for(int s = 0; s < nslots; s++) slots[s] = tmp[s];
  for(int w = 0; w < c_nwin; w++) c_winslot[w] = newidx_of_w[w];
}

static void c_after_halves(void){
  c_prodWA = 1; c_allzero = 0;
  if(!c_active) return;
  int wa = 0; ll prod = 1; int wA[20];
  for(int w = 0; w < c_nwin; w++){ int s = c_winslot[w]; if(inA[s]){ wA[wa++] = w; prod *= slots[s].m + 1; } }
  c_prodWA = prod;
  if(c_okw_cap < prod){ c_okw = realloc(c_okw, (size_t)prod); c_okw_cap = prod; }
  for(ll idx = 0; idx < prod; idx++){
    unsigned avail = 0; for(int w = 0; w < c_nwin; w++) avail |= 1u << w;
    ll rest = idx;
    for(int u = 0; u < wa; u++){ int w = wA[u]; int s = c_winslot[w]; int rad = slots[s].m + 1; int k = (int)(rest % rad); rest /= rad; int av = (c_mut == 1) ? (k == 0) : (k < slots[s].m); if(!av) avail &= ~(1u << w); }
    int ok = 0; for(int c = 0; c < c_nviable; c++) if((c_req[c] & ~avail) == 0){ ok = 1; break; }
    c_okw[idx] = (unsigned char)ok;
  }
  c_allzero = 1; for(ll idx = 0; idx < prod; idx++) if(c_okw[idx]){ c_allzero = 0; break; }
}
