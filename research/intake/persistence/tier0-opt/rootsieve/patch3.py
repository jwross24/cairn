p = "rs.c"
t = open(p).read()
old = """int main(int argc, char **argv) {
  if (argc < 6) {"""
new = """static void check_mode(void) {
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
    if (dead) { printf("rank %d dead %d\\n", rk, dead); continue; }
    ll r = ((v0 % 12) + 12) % 12;
    printf("rank %d", rk);
    for (ll a0 = r; a0 <= A; a0 += 12) {
      ll k = (a0 - v0) / 12; ll b = v1 + k * U[1], c = v2 + k * U[2];
      int keep = lattice_keep(need_b0, need_c0, b, c);
      int K = KT[a0]; if (K > 18) K = 18;
      int fl = (K == 3 && LAMK[3] == 100) ? tail_flags((int)a0, b, c, 3, 100, 1000ULL) : tail_flags((int)a0, b, c, K, LAMK[K], pow10u[K]);
      printf(" | %lld %d %d", a0, keep, (fl & 2) != 0);
    }
    printf("\\n");
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
  if (argc < 6) {"""
assert old in t
t = t.replace(old, new)
open(p, "w").write(t)
