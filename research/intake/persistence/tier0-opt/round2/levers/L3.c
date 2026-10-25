// lvl12: level-12 pass of the antecedent-tree child enumeration, in C.
// Reads the flat config written by export_cfg.py, enumerates residue patterns (multiset of
// residues per digit group, n residue), applies the exact subgroup-membership test per
// ℓ-component, assembles the coset representative by CRT, splits by a, and runs the 10-adic
// tail test.  Prints to stdout:
//   OPEN  a nu e_1..e_q b c        (pattern consistent, n > K: Python lifts it)
//   EXACT a nu e_1..e_q b c Y      (y = Y is a candidate exact solution: Python verifies)
// and counts to stderr.  Everything that is not printed was killed by an exact test
// (y ≡ 0 mod p, w ∉ H, or an inconsistent tail).
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

typedef long long ll; typedef unsigned long long ull; typedef unsigned __int128 u128;
#define MAXP 8
#define MAXQ 40
#define MAXC 8
static int L, A, q, digits[MAXQ];
static int np; static ll P[MAXP], L2[MAXP], L3[MAXP], L7[MAXP]; static ll POW10[MAXP][64], R[MAXP][64]; static int *LOGT[MAXP];
static int nc; static int cn[MAXC], cidx[MAXC][MAXP]; static ll cmod[MAXC][MAXP], ccrt[MAXC]; static ll csize[MAXC];
static int *crep[MAXC];   // crep[c][index*3 + j] or -1
static ll N, G, U[3], U2[2][2]; static int KT[64];
static ull pow10u[19];
static int *CONTRIB[MAXC][MAXP];  // CONTRIB[c][i][log] = (log % m_i) * stride_i within component c, or NULL
static ll yst[MAXQ+1][MAXP];       // yst[k][i] = Σ over the first k placed digits of (d-1) 10^r, reduced mod P[i]
static ll D1[10][64][MAXP];        // D1[g][r][i] = (gd[g]-1) 10^r mod P[i]
// digit groups
static int ng, gd[10], gk[10];
static int eps[MAXQ];      // residues in group order
static ll cnt_pat=0, cnt_zero=0, cnt_pre=0, cnt_split=0, cnt_tail_dead=0, cnt_open=0, cnt_exact=0;

static inline __attribute__((always_inline)) ull mulmod(ull a, ull b, ull m){ if(m<=0xFFFFFFFFULL) return (a%m)*(b%m)%m; return (ull)(((u128)a*b)%m); }
static ll LAMK[19]; static ull *T3K[19], *T7K[19]; static ull P2A[64]; static int cntmg[10];
static ull powmod(ull b, ull e, ull m);
static ll gcdll(ll a, ll b){ while(b){ ll t=a%b; a=b; b=t; } return a; }
static void init_tail(void){
  for(int i=0;i<q;i++) cntmg[digits[i]]++;
  for(int a=0;a<=A && a<64;a++){ int K=KT[a]; if(K>18) K=18; if(K<1) continue; ull m=pow10u[K];
    P2A[a]=powmod(2,(ull)a,m);
    if(T3K[K]||LAMK[K]<0) continue;
    ll l2=K==1?1:(K==2?2:(1LL<<(K-2))), l5=4; for(int i=1;i<K;i++) l5*=5;
    ll lam=l2/gcdll(l2,l5)*l5;
    if(lam>65536){ LAMK[K]=-1; continue; }
    ull *t3=malloc(sizeof(ull)*lam), *t7=malloc(sizeof(ull)*lam); t3[0]=1%m; t7[0]=1%m;
    for(ll e=1;e<lam;e++){ t3[e]=mulmod(t3[e-1],3,m); t7[e]=mulmod(t7[e-1],7,m); }
    if(mulmod(t3[lam-1],3,m)!=1%m || mulmod(t7[lam-1],7,m)!=1%m){ LAMK[K]=-1; free(t3); free(t7); continue; }
    T3K[K]=t3; T7K[K]=t7; LAMK[K]=lam; }
}
static ull powmod(ull b, ull e, ull m){ ull r=1%m; b%=m; while(e){ if(e&1) r=mulmod(r,b,m); b=mulmod(b,b,m); e>>=1;} return r; }
static ull invmod(ull a, ull m){ // extended gcd
  long long t=0,nt=1; long long r=(long long)m, nr=(long long)(a%m);
  while(nr){ long long qq=r/nr; long long tmp=t-qq*nt; t=nt; nt=tmp; tmp=r-qq*nr; r=nr; nr=tmp; }
  if(t<0) t+= (long long)m; return (ull)t; }
static ull powmod_signed(ull base, ll e, ull m){ if(e>=0) return powmod(base,(ull)e,m); ull inv=invmod(base%m,m); return powmod(inv,(ull)(-e),m); }

static void read_cfg(const char* path){
  FILE* f=fopen(path,"r"); if(!f){perror("cfg"); exit(1);}
  if(fscanf(f,"%d %d %d",&L,&A,&q)!=3) exit(2);
  for(int i=0;i<q;i++) fscanf(f,"%d",&digits[i]);
  fscanf(f,"%d",&np);
  for(int i=0;i<np;i++){ fscanf(f,"%lld %lld %lld %lld",&P[i],&L2[i],&L3[i],&L7[i]);
    for(int j=0;j<L;j++) fscanf(f,"%lld",&POW10[i][j]);
    for(int j=0;j<L;j++) fscanf(f,"%lld",&R[i][j]);
    LOGT[i]=malloc(sizeof(int)*P[i]); for(ll j=0;j<P[i];j++) fscanf(f,"%d",&LOGT[i][j]); }
  fscanf(f,"%d",&nc);
  for(int c=0;c<nc;c++){ fscanf(f,"%d",&cn[c]); for(int j=0;j<cn[c];j++) fscanf(f,"%d",&cidx[c][j]);
    for(int j=0;j<cn[c];j++) fscanf(f,"%lld",&cmod[c][j]);
    ll hs; fscanf(f,"%lld %lld",&ccrt[c],&hs);
    csize[c]=1; for(int j=0;j<cn[c];j++) csize[c]*=cmod[c][j];
    crep[c]=malloc(sizeof(int)*3*csize[c]); for(ll i=0;i<3*csize[c];i++) crep[c][i]=-1;
    for(ll h=0;h<hs;h++){ ll key[MAXP]; int rep[3]; for(int j=0;j<cn[c];j++) fscanf(f,"%lld",&key[j]); for(int j=0;j<3;j++) fscanf(f,"%d",&rep[j]);
      ll idx=0; for(int j=0;j<cn[c];j++) idx=idx*cmod[c][j]+key[j];
      crep[c][idx*3]=rep[0]; crep[c][idx*3+1]=rep[1]; crep[c][idx*3+2]=rep[2]; } }
  fscanf(f,"%lld %lld %lld %lld %lld",&N,&G,&U[0],&U[1],&U[2]);
  fscanf(f,"%lld %lld %lld %lld",&U2[0][0],&U2[0][1],&U2[1][0],&U2[1][1]);
  for(int a=0;a<=A;a++) fscanf(f,"%d",&KT[a]);
  fclose(f);
  pow10u[0]=1; for(int i=1;i<19;i++) pow10u[i]=pow10u[i-1]*10ULL;
  for(int cc=0;cc<nc;cc++){ for(int i=0;i<np;i++) CONTRIB[cc][i]=NULL;
    ll stride=1; for(int j=cn[cc]-1;j>=0;j--){ int i=cidx[cc][j]; CONTRIB[cc][i]=malloc(sizeof(int)*(P[i]-1));
      for(ll lg=0;lg<P[i]-1;lg++) CONTRIB[cc][i][lg]=(int)((lg%cmod[cc][j])*stride); stride*=cmod[cc][j]; } }
  // groups
  ng=0; for(int i=0;i<q;i++){ if(ng==0||gd[ng-1]!=digits[i]){ gd[ng]=digits[i]; gk[ng]=1; ng++; } else gk[ng-1]++; }
}

static int pattern_has[10][64];   // multiplicity of (digit, residue) in the current pattern
static inline __attribute__((always_inline)) void tail_core(int a0, int nu, ll b, ll c, int K, ll lamc, ull m){
  ull Y;
  if(lamc>0){ ll lam=lamc; ll bm=b%lam; if(bm<0) bm+=lam; ll cm=c%lam; if(cm<0) cm+=lam;
    Y=mulmod(mulmod(P2A[a0], T3K[K][bm], m), T7K[K][cm], m); }
  else Y=mulmod(mulmod(powmod(2,(ull)a0,m), powmod_signed(3,b,m), m), powmod_signed(7,c,m), m);
  // digits of Y, zero-padded to K
  int dg[20]; ull t=Y; for(int i=0;i<K;i++){ dg[i]=(int)(t%10); t/=10; }
  // exact case: n = number of digits of Y
  int nY=0; { ull tt=Y; while(tt){nY++; tt/=10;} }
  int exact=0;
  if(Y>=10 && nY%L==nu%L){
    int have[10]={0}; int ok=1; int cntm[10]={0}; for(int i=0;i<q;i++) cntm[digits[i]]++;
    if(K<=L){
      for(int i=0;i<nY;i++){ int d=dg[i]; if(d==0){ok=0;break;} if(d==1) continue; have[d]++; if(have[d]>cntm[d]){ok=0;break;}
        if(pattern_has[d][i]<1){ok=0;break;} }
    } else {
    int used[10][64]; memset(used,0,sizeof used);
    for(int i=0;i<nY;i++){ int d=dg[i]; if(d==0){ok=0;break;} if(d==1) continue; have[d]++; if(have[d]>cntm[d]){ok=0;break;}
      if(++used[d][i%L] > pattern_has[d][i%L]){ok=0;break;} }
    }
    if(ok){ for(int d=2;d<=9;d++) if(have[d]!=cntm[d]) ok=0; }
    if(ok) exact=1;
  }
  // n > K case
  int open=1;
  if(K<=L){ int have[10]={0};
    for(int i=0;i<K;i++){ int d=dg[i]; if(d==0){open=0;break;} if(d==1) continue; have[d]++; if(have[d]>cntmg[d]){open=0;break;}
      if(pattern_has[d][i]<1){open=0;break;} }
  } else { int used[10][64]; memset(used,0,sizeof used); int cntm[10]={0}; for(int i=0;i<q;i++) cntm[digits[i]]++; int have[10]={0};
    for(int i=0;i<K;i++){ int d=dg[i]; if(d==0){open=0;break;} if(d==1) continue; have[d]++; if(have[d]>cntm[d]){open=0;break;}
      if(++used[d][i%L] > pattern_has[d][i%L]){open=0;break;} } }
  if(exact){ printf("EXACT %d %d",a0,nu); for(int i=0;i<q;i++) printf(" %d",eps[i]); printf(" %lld %lld %llu\n",b,c,Y); cnt_exact++; }
  if(open){ printf("OPEN %d %d",a0,nu); for(int i=0;i<q;i++) printf(" %d",eps[i]); printf(" %lld %lld\n",b,c); cnt_open++; }
  if(!exact && !open) cnt_tail_dead++;
}

static inline __attribute__((always_inline)) void tail_test(int a0, int nu, ll b, ll c){
  int K=KT[a0]; if(K>18) K=18;
  /* unreachable at level 12: K == 3 and np == 5 for every multiset (U2 and the prime set are fixed per level); the K < 1, generic-K and slow-path branches never run */
  if(K<1){
    printf("OPEN %d %d",a0,nu); for(int i=0;i<q;i++) printf(" %d",eps[i]); printf(" %lld %lld\n",b,c); cnt_open++; return; }
  if(K==3 && LAMK[3]==100) tail_core(a0,nu,b,c,3,100,1000ULL);
  else tail_core(a0,nu,b,c,K,LAMK[K],pow10u[K]);
}

static unsigned short DC[10][64][8];
static int pos;
static int fastp; static ull *ENT[MAXP]; static unsigned char *OKT[MAXC];
static void init_fast(void){
  fastp=(nc<=4);
  for(int c=0;c<nc && fastp;c++){ if(csize[c]>=65536) fastp=0;
    for(int i=0;i<np && fastp;i++) if(CONTRIB[c][i]) for(ll lg=0;lg<P[i]-1;lg++) if(CONTRIB[c][i][lg]<0||CONTRIB[c][i][lg]>=65536){ fastp=0; break; } }
  if(!fastp) return;
  for(int i=0;i<np;i++){ ENT[i]=calloc(P[i],sizeof(ull));
    for(ll y=1;y<P[i];y++){ ull e=0; for(int c=0;c<nc;c++) if(CONTRIB[c][i]) e|=(ull)(unsigned)CONTRIB[c][i][LOGT[i][y]]<<(16*c); ENT[i][y]=e; } }
  for(int c=0;c<nc;c++){ OKT[c]=malloc(csize[c]); for(ll k=0;k<csize[c];k++) OKT[c][k]=crep[c][k*3]>=0; }
}

// ---- syndrome tables: the prefilter accept test as a sum of per-prime table entries ----
#define MAXF 8
static int synok, nf, fld_c[MAXF], fld_o[MAXF], fld_off[MAXF], fld_w[MAXF], fld_E[MAXF], fld_a[MAXF][MAXP], zoff;
static unsigned short *SYN[MAXP], *SYN2[MAXP]; static unsigned char *P1; static unsigned synmask;
static int cmpint(ll a, ll b){ return a<b?-1:a>b; }
static void init_syn(void){
  synok=0; nf=0;
  if(!(fastp && np==5 && nc<=4)) return;
  for(int c=0;c<nc;c++){
    ll hs=0; for(ll k=0;k<csize[c];k++) hs+=(crep[c][k*3]>=0);
    if(hs==csize[c]) continue;
    int n=cn[c]; ll E=1; for(int j=0;j<n;j++){ ll m=cmod[c][j]; ll a=E,b=m; while(b){ll t=a%b;a=b;b=t;} E=E/a*m; }
    ll nh=0; static int hx[4096][MAXP]; if(hs>4096) return;
    for(ll k=0;k<csize[c];k++) if(crep[c][k*3]>=0){ ll t=k; for(int j=n-1;j>=0;j--){ hx[nh][j]=(int)(t%cmod[c][j]); t/=cmod[c][j]; } nh++; }
    static int ann[512][MAXP]; ll na=0; int a[MAXP]={0};
    for(ll code=0;code<csize[c];code++){ ll t=code; for(int j=n-1;j>=0;j--){ a[j]=(int)(t%cmod[c][j]); t/=cmod[c][j]; }
      int good=1; for(ll h=0;h<nh&&good;h++){ ll sum=0; for(int j=0;j<n;j++) sum+=(ll)a[j]*hx[h][j]*(E/cmod[c][j]); if(sum%E) good=0; }
      if(good){ if(na>=512) return; memcpy(ann[na],a,sizeof a); na++; } }
    if(na*hs!=csize[c]) return;
    static int span[512][MAXP]; ll ns=1; memset(span[0],0,sizeof span[0]);
    for(ll u=0;u<na && ns<na;u++){
      int in=0; for(ll w=0;w<ns&&!in;w++) if(!memcmp(span[w],ann[u],sizeof(int)*MAXP)) in=1;
      if(in) continue;
      if(nf>=MAXF) return;
      memcpy(fld_a[nf],ann[u],sizeof(int)*MAXP); fld_c[nf]=c; fld_E[nf]=(int)E;
      int o=1; { int x[MAXP]; memcpy(x,ann[u],sizeof x); for(;;){ int z=1; for(int j=0;j<n;j++) if(x[j]%cmod[c][j]) z=0; if(z) break; for(int j=0;j<n;j++) x[j]=(x[j]+ann[u][j])%cmod[c][j]; o++; } }
      fld_o[nf]=o; nf++;
      ll old=ns; for(ll w=0;w<old;w++) for(int mult=1;mult<o;mult++){ if(ns>=512) return; for(int j=0;j<n;j++) span[ns][j]=(int)(((ll)span[w][j]+(ll)mult*ann[u][j])%cmod[c][j]); ns++; }
      /* dedupe span */
      ll nn=0; for(ll w=0;w<ns;w++){ int dup=0; for(ll v=0;v<nn;v++) if(!memcmp(span[v],span[w],sizeof(int)*MAXP)) {dup=1;break;} if(!dup){ memcpy(span[nn],span[w],sizeof(int)*MAXP); nn++; } } ns=nn;
    }
    if(ns!=na) return;
  }
  /* per-prime contribution of field f at log lg */
  int bits=0;
  static int contrib_max[MAXF];
  for(int f=0;f<nf;f++){ int c=fld_c[f]; int n=cn[c]; ll tot=0;
    for(int i=0;i<np;i++){ int jj=-1; for(int j=0;j<n;j++) if(cidx[c][j]==i) jj=j; if(jj<0) continue; if(fld_a[f][jj]==0) continue; tot+=(fld_o[f]-1); }
    int w=1; while((1<<w)<=tot) w++; fld_w[f]=w; fld_off[f]=bits; bits+=w; contrib_max[f]=(int)tot; }
  zoff=bits; { int w=1; while((1<<w)<=np) w++; bits+=w; }
  if(bits>14) return;
  for(int i=0;i<np;i++){ SYN[i]=calloc(P[i],sizeof(unsigned short));
    for(ll y=0;y<P[i];y++){
      if(y==0){ SYN[i][0]=(unsigned short)(1u<<zoff); continue; }
      unsigned v=0; int lg=LOGT[i][y];
      for(int f=0;f<nf;f++){ int c=fld_c[f]; int n=cn[c]; int jj=-1; for(int j=0;j<n;j++) if(cidx[c][j]==i) jj=j; if(jj<0) continue;
        ll E=fld_E[f]; ll val=((ll)fld_a[f][jj]*(lg%cmod[c][jj])*(E/cmod[c][jj]))%E; ll unit=E/fld_o[f]; if(val%unit) return; val/=unit;
        v+=(unsigned)val<<fld_off[f]; }
      SYN[i][y]=(unsigned short)v; } }
  for(int i=0;i<np;i++){ SYN2[i]=malloc(2*P[i]*sizeof(unsigned short)); for(ll v=0;v<2*P[i];v++) SYN2[i][v]=SYN[i][v>=P[i]?v-P[i]:v]; }
  P1=calloc(1u<<bits,1); synmask=(1u<<bits)-1;
  for(unsigned S=0;S<(1u<<bits);S++){ int ok=((S>>zoff)==0); for(int f=0;f<nf&&ok;f++){ unsigned fv=(S>>fld_off[f])&((1u<<fld_w[f])-1); if(fv%fld_o[f]) ok=0; } P1[S]=ok; }
  /* exhaustive equivalence on every component index: P1 test == OKT test */
  for(int c=0;c<nc;c++){ int n=cn[c];
    for(ll k=0;k<csize[c];k++){ ll t=k; int x[MAXP]; for(int j=n-1;j>=0;j--){ x[j]=(int)(t%cmod[c][j]); t/=cmod[c][j]; }
      int pass=1; for(int f=0;f<nf;f++) if(fld_c[f]==c){ ll E=fld_E[f]; ll sum=0; for(int j=0;j<n;j++) sum+=(ll)fld_a[f][j]*x[j]*(E/cmod[c][j]); if(sum%E) pass=0; }
      if(pass!=(crep[c][k*3]>=0)) return; } }
  synok=1;
}

static inline __attribute__((always_inline)) int fast_filter(int nu, int npc, int ncc, ull* accp){
  const ll* ya=yst[pos];
  ull acc=0; int z=0;
  for(int i=0;i<npc;i++){ ll y=R[i][nu]+ya[i]; if(y>=P[i]) y-=P[i]; z|=(y==0); acc+=ENT[i][y]; }
  int ok=1; for(int c=0;c<ncc;c++) ok&=OKT[c][(acc>>(16*c))&0xFFFF];
  *accp=acc;
  if(z|!ok){ cnt_zero+=z; cnt_pre+=!z; return 1; }
  return 0;
}
static inline __attribute__((always_inline)) void finish(int nu, ull acc){
  ll v0=0,v1=0,v2=0;
  for(int c=0;c<nc;c++){ int* rp=&crep[c][((acc>>(16*c))&0xFFFF)*3]; v0+=ccrt[c]*rp[0]; v1+=ccrt[c]*rp[1]; v2+=ccrt[c]*rp[2]; }
  if(G==12){
    ll r=((v0%12)+12)%12;
    for(ll a0=r; a0<=A; a0+=12){ ll k=(a0-v0)/12; ll b=v1+k*U[1], c=v2+k*U[2]; cnt_split++; tail_test((int)a0,nu,b,c); }
    return;
  }
  ll r=((v0%G)+G)%G;
  for(ll a0=r; a0<=A; a0+=G){ ll k=(a0-v0)/G; ll b=v1+k*U[1], c=v2+k*U[2]; cnt_split++; tail_test((int)a0,nu,b,c); }
}
static void process(int nu){
  cnt_pat++;
  const ll* ya=yst[pos];
  ll v0=0,v1=0,v2=0;
  if(fastp){
    ull acc;
    if(np==5 && nc==4){ if(fast_filter(nu,5,4,&acc)) return; }
    else { if(fast_filter(nu,np,nc,&acc)) return; }
    finish(nu,acc); return;
  }
  int logs[MAXP];
  for(int i=0;i<np;i++){ ll y=R[i][nu]+ya[i]; if(y>=P[i]) y-=P[i]; if(y==0){cnt_zero++; return;} logs[i]=LOGT[i][y]; }
  for(int c=0;c<nc;c++){ ll idx=0; for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; idx+=CONTRIB[c][i][logs[i]]; }
    int* rp=&crep[c][idx*3]; if(rp[0]<0){cnt_pre++; return;} v0+=ccrt[c]*rp[0]; v1+=ccrt[c]*rp[1]; v2+=ccrt[c]*rp[2]; }
  ll r=((v0%G)+G)%G;
  for(ll a0=r; a0<=A; a0+=G){ ll k=(a0-v0)/G; ll b=v1+k*U[1], c=v2+k*U[2]; cnt_split++; tail_test((int)a0,nu,b,c); }
}

// enumerate multisets of residues per group
static int pos;  // index into eps
static inline __attribute__((always_inline)) void ystep(int g, int r, int npc){
  for(int i=0;i<npc;i++){ ll v=yst[pos][i]+D1[g][r][i]; yst[pos+1][i]=v>=P[i]?v-P[i]:v; }
}
// last digit: all residues r in [start,L) for the prefix held in yst[pos]
static void leaf5(int g, int start, int nu){
  const int dg=gd[g];
  unsigned yb[5]; for(int i=0;i<5;i++){ unsigned v=R[i][nu]+yst[pos][i]; yb[i]=v>=P[i]?v-P[i]:v; }
  const unsigned b0=yb[0],b1=yb[1],b2=yb[2],b3=yb[3],b4=yb[4];
  const unsigned short *s0=SYN2[0],*s1=SYN2[1],*s2=SYN2[2],*s3=SYN2[3],*s4=SYN2[4];
  const unsigned char *pt=P1; const int zo=zoff;
  const unsigned short (*Dc)[8]=DC[g];
  ll lz=0, lps=0;
  for(int r=start;r<L;r++){
    unsigned v0=b0+Dc[r][0], v1=b1+Dc[r][1], v2=b2+Dc[r][2], v3=b3+Dc[r][3], v4=b4+Dc[r][4];
    unsigned S=s0[v0]+s1[v1]+s2[v2]+s3[v3]+s4[v4];
    int ok=pt[S];
    lz+=(S>>zo)!=0;
    lps+=ok;
    if(ok){
      unsigned y0=v0>=P[0]?v0-P[0]:v0, y1=v1>=P[1]?v1-P[1]:v1, y2=v2>=P[2]?v2-P[2]:v2, y3=v3>=P[3]?v3-P[3]:v3, y4=v4>=P[4]?v4-P[4]:v4;
      ull acc=ENT[0][y0]+ENT[1][y1]+ENT[2][y2]+ENT[3][y3]+ENT[4][y4];
      eps[pos]=r; pattern_has[dg][r]++;
      finish(nu,acc);
      pattern_has[dg][r]--;
    }
  }
  cnt_pat+=L-start; cnt_zero+=lz; cnt_pre+=(L-start)-lz-lps;
}
static void rec_group(int g, int start, int left, int nu){
  if(g==ng){ process(nu); return; }
  if(synok && g==ng-1 && left==1){ leaf5(g,start,nu); return; }
  for(int r=start;r<L;r++){ eps[pos]=r; pattern_has[gd[g]][r]++;
    if(np==5) ystep(g,r,5); else ystep(g,r,np);
    pos++;
    if(left-1==0){ if(g+1<ng) rec_group(g+1,0,gk[g+1],nu); else process(nu); }
    else rec_group(g,r,left-1,nu);
    pos--; pattern_has[gd[g]][r]--; }
}

int main(int argc,char**argv){
  if(argc<2){fprintf(stderr,"usage: lvl12 cfg [nu_lo nu_hi]\n"); return 1;}
  read_cfg(argv[1]); init_tail(); init_fast(); init_syn();
  for(int i=0;i<np;i++){ for(int j=0;j<L;j++) R[i][j]=((R[i][j]%P[i])+P[i])%P[i];
    for(int g=0;g<ng;g++) for(int r=0;r<L;r++) D1[g][r][i]=(((ll)(gd[g]-1)*POW10[i][r])%P[i]+P[i])%P[i]; }
  for(int g=0;g<ng;g++) for(int r=0;r<L;r++) for(int i=0;i<np&&i<8;i++) DC[g][r][i]=(unsigned short)D1[g][r][i];
  int lo=0, hi=L; if(argc>=4){lo=atoi(argv[2]); hi=atoi(argv[3]);}
  for(int nu=lo; nu<hi; nu++){ pos=0; memset(pattern_has,0,sizeof pattern_has); memset(yst[0],0,sizeof yst[0]); rec_group(0,0,gk[0],nu); }
  fprintf(stderr,"patterns %lld zero %lld prefilter-dead %lld (a,pattern) %lld tail-dead %lld open %lld exact %lld\n",
    cnt_pat,cnt_zero,cnt_pre,cnt_split,cnt_tail_dead,cnt_open,cnt_exact);
  return 0;
}
