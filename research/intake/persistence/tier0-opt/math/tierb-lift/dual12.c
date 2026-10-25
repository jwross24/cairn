#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <time.h>

typedef unsigned long long ull; typedef long long ll; typedef unsigned __int128 u128;
#define L 12
#define NB 9900
#define NC 900
static const ull Q = 5291005291ULL;
static int A, q, W, digs[40], cntd[10], mutant = 0;
static ull t3[NB], t7[NC], p2[64], pw10[20], Rn[L];
static unsigned char DS4[10000];
static ull Nmax; static unsigned char ok63[3][63]; static int vr[3][63], nvr[3]; static ull invQ63;
static ll steps = 0, digit_ok = 0, cvecs = 0, outs = 0, tail_dead = 0;
static ull mulm(ull a, ull b){ return (ull)(((u128)a * b) % Q); }
static ull powm(ull b, ull e, ull m){ ull r = 1 % m; b %= m; while(e){ if(e & 1) r = (u128)r * b % m; b = (u128)b * b % m; e >>= 1; } return r; }

static int cv[L];
static int xs[L][10];
static int cur_a, cur_nu; static ull cur_b, cur_c;

static void emit(void){
  printf("%d %d", cur_a, cur_nu);
  for(int d = 2; d <= 9; d++) for(int r = 0; r < L; r++) for(int t = 0; t < xs[r][d]; t++) printf(" %d", r);
  printf(" %llu %llu\n", cur_b, cur_c);
  outs++;
}

static int tail_ok(void){
  ull Y = powm(2, cur_a, 1000) * powm(3, cur_b, 1000) % 1000 * powm(7, cur_c, 1000) % 1000;
  int dg[3] = { (int)(Y % 10), (int)(Y / 10 % 10), (int)(Y / 100) };
  int have[10] = {0};
  for(int i = 0; i < 3; i++){
    int d = dg[i]; if(d == 0) return 0; if(d == 1) continue;
    have[d]++; if(have[d] > cntd[d]) return 0;
    if(xs[i][d] < 1) return 0;
  }
  return 1;
}

static int remd[10];
static void realize_rec(int r, int d, int rem);
static void realize_rec(int r, int d, int rem){
  if(d == 10){
    if(rem != 0) return;
    r++;
    if(r == L){ for(int e = 2; e <= 9; e++) if(remd[e]) return; if(mutant != 3 && !tail_ok()){ tail_dead++; return; } emit(); return; }
    for(int e = 2; e <= 9; e++) xs[r][e] = 0;
    realize_rec(r, 2, cv[r]);
    return;
  }
  int maxx = remd[d] < rem / (d - 1) ? remd[d] : rem / (d - 1);
  for(int x = 0; x <= maxx; x++){
    xs[r][d] = x; remd[d] -= x;
    realize_rec(r, d + 1, rem - x * (d - 1));
    remd[d] += x;
  }
  xs[r][d] = 0;
}

static void uncarry(int r, ull Nrem, int Wrem){
  if(r == L - 1){ if(Nrem == (ull)Wrem){ cv[r] = Wrem; cvecs++; for(int e = 2; e <= 9; e++) xs[0][e] = 0; for(int e = 2; e <= 9; e++) remd[e] = cntd[e]; realize_rec(0, 2, cv[0]); } return; }
  ull lo = Nrem % 10;
  for(ull c = lo; c <= (ull)Wrem && c <= Nrem; c += 10){ cv[r] = (int)c; uncarry(r + 1, (Nrem - c) / 10, Wrem - (int)c); }
}

int main(int argc, char **argv){
  if(argc < 6){ fprintf(stderr, "usage: dual12 A nu_lo nu_hi q d1..dq\n"); return 1; }
  A = atoi(argv[1]); int nu_lo = atoi(argv[2]), nu_hi = atoi(argv[3]); q = atoi(argv[4]);
  W = 0; for(int i = 0; i < q; i++){ digs[i] = atoi(argv[5 + i]); cntd[digs[i]]++; W += digs[i] - 1; }
  const char *mu = getenv("DUAL_MUTANT"); if(mu) mutant = atoi(mu);
  pw10[0] = 1; for(int i = 1; i < 20; i++) pw10[i] = pw10[i - 1] * 10;
  for(int n = 0; n < L; n++) Rn[n] = (pw10[n] - 1) / 9;
  if(powm(3, NB, Q) != 1 || powm(7, NC, Q) != 1){ fprintf(stderr, "lattice assumption violated\n"); return 2; }
  t3[0] = 1; for(int i = 1; i < NB; i++) t3[i] = mulm(t3[i - 1], 3);
  t7[0] = 1; for(int i = 1; i < NC; i++) t7[i] = mulm(t7[i - 1], 7);
  p2[0] = 1; for(int i = 1; i < 64; i++) p2[i] = mulm(p2[i - 1], 2);
  for(int i = 0; i < 10000; i++) DS4[i] = (unsigned char)(i % 10 + i / 10 % 10 + i / 100 % 10 + i / 1000);
  if((double)W * 1e11 >= 1e16){ fprintf(stderr, "W too large for 4-chunk digit sum\n"); return 4; }
  Nmax = (ull)W * pw10[L - 1];
  ull Qm63 = Q % 63; for(ull x = 1; x < 63; x++) if(x * Qm63 % 63 == 1) invQ63 = x;
  for(int nu = nu_lo; nu < nu_hi; nu++){
    int need_b0 = ((nu + W) % 3) != 0; if(mutant == 1) need_b0 = 0;
    ull R7 = Rn[nu] % 7;
    for(int r = 0; r < 63; r++){ int m9 = (r % 9) == (W % 9); int d7 = ((r % 7) + R7) % 7 == 0; ok63[0][r] = m9 && !d7; ok63[1][r] = m9 && d7; ok63[2][r] = m9; }
    for(int cl = 0; cl < 3; cl++){ nvr[cl] = 0; for(int r = 0; r < 63; r++) if(ok63[cl][r]) vr[cl][nvr[cl]++] = r; }
    for(int a = 0; a <= A; a++){
      for(int cls7 = 0; cls7 < 2; cls7++){
        int nbmax = need_b0 ? 1 : NB; int ncmax = cls7 ? NC : 1;
        if(mutant == 1 && !cls7) continue;
        for(int b = 0; b < nbmax; b++){
          ull hb = mulm(p2[a], t3[b]);
          for(int c = 0; c < ncmax; c++){
            ull h = mulm(hb, t7[c]);
            ull N0 = (h + Q - Rn[nu] % Q) % Q;
            cur_a = a; cur_nu = nu; cur_b = b; cur_c = c;
            ull r0 = N0 % 63;
            int cl = mutant == 1 ? 2 : cls7;
            for(int u = 0; u < nvr[cl]; u++){
              ull ms = ((vr[cl][u] + 63 - r0) % 63) * invQ63 % 63;
              if(mutant == 2 && ms == 0) ms = 63;
              for(ull m = ms; ; m += 63){
                ull N = N0 + m * Q; if(N > Nmax) break;
                steps++;
                int ds = DS4[N % 10000] + DS4[N / 10000 % 10000] + DS4[N / 100000000 % 10000] + DS4[N / 1000000000000ULL];
                if(ds > W) continue;
                digit_ok++;
                uncarry(0, N, W);
              }
            }
          }
        }
      }
    }
  }
  (void)Qm63;
  fprintf(stderr, "steps %lld digit_ok %lld cvecs %lld tail_dead %lld outs %lld\n", steps, digit_ok, cvecs, tail_dead, outs);
  return 0;
}
