t = open("lvl12_r2.c").read()

old_rec = t[t.index("// enumerate multisets of residues per group"):t.index("int main(")]
new_rec = '''#ifdef R2
static int y7st[MAXQ + 1]; static int s1total; static int r7tab[6]; static const int p7[6] = {1, 3, 2, 6, 4, 5};
static int inv7[7] = {0, 1, 4, 5, 2, 3, 6};
static ll cnt_r2_leaf = 0;
#endif
static int pos;
static inline __attribute__((always_inline)) void ystep(int g, int r, int npc){
  for(int i=0;i<npc;i++){ ll v=yst[pos][i]+D1[g][r][i]; yst[pos+1][i]=v>=P[i]?v-P[i]:v; }
}
static void rec_group(int g, int start, int left, int nu){
  if(g==ng){ process(nu); return; }
#ifdef R2
  if(g==ng-1 && left==1){
    int dm1=gd[g]-1; int part=y7st[pos]; int cand[2]; int nc2=0;
    if(dm1%7==0){ if(part==0) for(int r=start;r<L;r++){ cand[0]=r; eps[pos]=r; pattern_has[gd[g]][r]++; ystep(g,r,np); pos++; process(nu); pos--; pattern_has[gd[g]][r]--; } return; }
    int tgt=(7-part)%7; if(tgt==0) return;
    int want=(tgt*inv7[dm1%7])%7; int rho=-1; for(int k=0;k<6;k++) if(p7[k]==want) rho=k;
    for(int r=rho;r<L;r+=6){ if(r<start) continue; eps[pos]=r; pattern_has[gd[g]][r]++; ystep(g,r,np); pos++; process(nu); pos--; pattern_has[gd[g]][r]--; }
    return;
  }
#endif
  for(int r=start;r<L;r++){ eps[pos]=r; pattern_has[gd[g]][r]++;
    ystep(g,r,np);
#ifdef R2
    y7st[pos+1]=(y7st[pos]+(gd[g]-1)*p7[r%6])%7;
#endif
    pos++;
    if(left-1==0){ if(g+1<ng) rec_group(g+1,0,gk[g+1],nu); else process(nu); }
    else rec_group(g,r,left-1,nu);
    pos--; pattern_has[gd[g]][r]--; }
}

'''
t = t.replace(old_rec, new_rec)
t = t.replace("static int pos;  // index into eps\n", "")
t = t.replace("static int pos;\nstatic int fastp;", "static int fastp;")
old_main = "  for(int nu=lo; nu<hi; nu++){ pos=0; memset(pattern_has,0,sizeof pattern_has); memset(yst[0],0,sizeof yst[0]); rec_group(0,0,gk[0],nu); }"
new_main = '''#ifdef R2
  s1total=0; for(int i=0;i<q;i++) s1total+=digits[i]-1;
  r7tab[0]=0; for(int n=0;n<5;n++) r7tab[n+1]=(r7tab[n]*10+1)%7;
#endif
  for(int nu=lo; nu<hi; nu++){
#ifdef R2
    if((nu+s1total)%3!=0) continue;
    y7st[0]=r7tab[nu%6];
#endif
    pos=0; memset(pattern_has,0,sizeof pattern_has); memset(yst[0],0,sizeof yst[0]); rec_group(0,0,gk[0],nu); }'''
assert old_main in t
t = t.replace(old_main, new_main)
open("lvl12_r2.c", "w").write(t)
