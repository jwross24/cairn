// lvlN: C lift pass from level L_old to L_new.
// Reads the config from export_level.py and a parent file of lines
//    a nu e_1..e_q b c          (residues mod L_old; (b,c) the parent's coset representative)
// For each parent, enumerates the deduplicated children (n residue and each digit residue lifted
// by 0 or L_old; equal digits at equal residues are a multiset), computes the new primes'
// residues, discrete logs (table or Pohlig–Hellman), the ℓ-component lookup relative to the parent
// lattice, assembles the coefficient vector t by CRT (as __int128, reduced mod N), and runs the
// 10-adic tail test at the new K.  Prints
//    OPEN  pidx a nu e_1..e_q t1 t2
//    EXACT pidx a nu e_1..e_q t1 t2 Y
// where (b',c') = (b,c) + t·U_old is formed by the caller in big integers.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <stdint.h>

typedef long long ll; typedef unsigned long long ull; typedef __int128 i128; typedef unsigned __int128 u128;
#define MAXP 12
#define MAXQ 40
#define MAXC 24
#define MAXF 10
static int Lold, Lnew, A, q, digits[MAXQ];
static int np; static ull P[MAXP], G[MAXP]; static ll L2[MAXP], L3[MAXP], L7[MAXP]; static ll POW10[MAXP][128], R[MAXP][128];
static int nf[MAXP]; static ull FQ[MAXP][MAXF]; static int FE[MAXP][MAXF]; static int *LOGT[MAXP];
static int nc; static int cn[MAXC], cidx[MAXC][MAXP]; static ll cmod[MAXC][MAXP]; static i128 ccrt[MAXC]; static ull csize[MAXC]; static int *crep[MAXC];
// sparse component tables (image much smaller than the group): open addressing on the mixed-radix key
static int csparse[MAXC]; static ull *hkeys[MAXC]; static int *hrep[MAXC]; static ull hsz[MAXC];
static void hput(int c, ull key, int r0, int r1){ ull h=(key*11400714819323198485ULL)%hsz[c]; while(hkeys[c][h]!=~0ULL) h=(h+1)%hsz[c]; hkeys[c][h]=key; hrep[c][2*h]=r0; hrep[c][2*h+1]=r1; }
static int* hfind(int c, ull key){ ull h=(key*11400714819323198485ULL)%hsz[c]; while(hkeys[c][h]!=~0ULL){ if(hkeys[c][h]==key) return &hrep[c][2*h]; h=(h+1)%hsz[c]; } return NULL; }
static int nlin; static int lidx[8]; static ll lmod[8], lg1[8], lg2[8]; static i128 lcrt[8];
static i128 N; static ll Uold[2][2], Unew[2][2]; static int KT[512];
static ull pow10u[19];

static ull mulmod(ull a, ull b, ull m){ return (ull)(((u128)a*b)%m); }
static ull powmod(ull b, ull e, ull m){ ull r=1%m; b%=m; while(e){ if(e&1) r=mulmod(r,b,m); b=mulmod(b,b,m); e>>=1;} return r; }
static ll egcd(ll a, ll b, ll*x, ll*y){ if(b==0){*x=1;*y=0;return a;} ll x1,y1; ll g=egcd(b,a%b,&x1,&y1); *x=y1; *y=x1-(a/b)*y1; return g; }
static ull invmod(ull a, ull m){ ll x,y; ll g=egcd((ll)(a%m),(ll)m,&x,&y); if(g!=1 && g!=-1){ fprintf(stderr,"no inverse\n"); exit(3);} x%= (ll)m; if(x<0) x+=m; return (ull)x; }
static i128 parse128(const char* s){ i128 v=0; int neg=0; if(*s=='-'){neg=1;s++;} while(*s>='0'&&*s<='9'){ v=v*10+(*s-'0'); s++; } return neg?-v:v; }
static void print128(i128 v){ char buf[64]; int n=0; int neg=v<0; u128 u=neg?(u128)(-v):(u128)v; if(u==0) buf[n++]='0'; while(u){ buf[n++]='0'+(int)(u%10); u/=10; } if(neg) putchar('-'); while(n) putchar(buf[--n]); }

// ---- Pohlig–Hellman: per-prime-factor subgroup tables (direct lookup) with a BSGS/digit fallback for large q^e
typedef struct { ull q; int e; ull qe; ull cof; ull crtc; ull gamma; ull m; ull *keys; ull *vals; ull hsize; ull ginv_m; ull gqinv; int direct; ull *tk; unsigned *tv; ull tmask; ull gj; } PHF;
#define TBL_MAX (1ULL<<22)
static PHF phf[MAXP][MAXF];
static ull mn[MAXP], mr2[MAXP], mone[MAXP];
static inline ull redc(u128 T, ull p, ull ninv){ ull m=(ull)T*ninv; ull t=(ull)((T+(u128)m*p)>>64); return t>=p?t-p:t; }
static ull memo_hq; static int memo_i=-1, memo_f=-1;
static ull powmod_mont(int i, ull b, ull e){
  ull p=P[i], ni=mn[i]; ull x=redc((u128)b*mr2[i],p,ni), r=mone[i];
  while(e){ if(e&1) r=redc((u128)r*x,p,ni); e>>=1; if(e) x=redc((u128)x*x,p,ni); }
  return redc((u128)r,p,ni);
}
static void mont_init(int i){ ull p=P[i]; if(!(p&1)||p>=(1ULL<<63)){ fprintf(stderr,"montgomery needs odd p<2^63\n"); exit(9);}
  ull inv=p; for(int k=0;k<6;k++) inv*=2-p*inv; mn[i]=-inv; ull r1=(ull)((((u128)1)<<64)%p); mone[i]=r1; mr2[i]=(ull)(((u128)r1*r1)%p); }
static void hins(PHF* f, ull key, ull val){ ull h=(key*11400714819323198485ULL)%f->hsize; while(f->keys[h]!=~0ULL) h=(h+1)%f->hsize; f->keys[h]=key; f->vals[h]=val; }
static int hget(PHF* f, ull key, ull* val){ ull h=(key*11400714819323198485ULL)%f->hsize; while(f->keys[h]!=~0ULL){ if(f->keys[h]==key){*val=f->vals[h]; return 1;} h=(h+1)%f->hsize; } return 0; }
static inline ull thash(ull key, ull mask){ return ((key*11400714819323198485ULL)>>20)&mask; }
static void ph_init(int i){
  ull p=P[i], n=p-1; mont_init(i);
  for(int j=0;j<nf[i];j++){ PHF* f=&phf[i][j]; f->q=FQ[i][j]; f->e=FE[i][j]; ull qe=1; for(int k=0;k<f->e;k++) qe*=f->q;
    f->qe=qe; f->cof=n/qe; f->crtc=(ull)(((u128)f->cof*invmod(f->cof%qe,qe))%n);
    ull gi=powmod(G[i], n/qe, p); f->gj=gi;
    if(qe<=TBL_MAX){ f->direct=1; ull sz=1; while(sz<2*qe) sz<<=1; f->tmask=sz-1; f->tk=malloc(sizeof(ull)*sz); f->tv=malloc(sizeof(unsigned)*sz);
      for(ull h=0;h<sz;h++) f->tk[h]=~0ULL;
      ull cur=1; for(ull k=0;k<qe;k++){ ull h=thash(cur,f->tmask); while(f->tk[h]!=~0ULL){ if(f->tk[h]==cur){ fprintf(stderr,"ph_init: generator order < q^e (p=%llu q=%llu)\n",p,f->q); exit(6);} h=(h+1)&f->tmask; } f->tk[h]=cur; f->tv[h]=(unsigned)k; cur=mulmod(cur,gi,p); }
      if(cur!=1){ fprintf(stderr,"ph_init: generator order != q^e\n"); exit(6);} continue; }
    f->direct=0;
    f->gamma=powmod(gi, qe/f->q, p);
    ull m=1; while(m*m<f->q) m++; f->m=m; f->hsize=4*m+16; f->keys=malloc(sizeof(ull)*f->hsize); f->vals=malloc(sizeof(ull)*f->hsize);
    for(ull h=0;h<f->hsize;h++) f->keys[h]=~0ULL;
    ull cur=1; for(ull jj=0;jj<m;jj++){ ull dummy; if(!hget(f,cur,&dummy)) hins(f,cur,jj); cur=mulmod(cur,f->gamma,p); }
    f->ginv_m=powmod(invmod(f->gamma,p), m, p); f->gqinv=invmod(gi,p); }
}
static ull bsgs(PHF* f, ull h, ull p){
  ull m=f->m; ull ginv_m=f->ginv_m; ull cur=h;
  for(ull i=0;i<m+1;i++){ ull jv; if(hget(f,cur,&jv)) return (i*m+jv)%f->q; cur=mulmod(cur,ginv_m,p); }
  fprintf(stderr,"bsgs failed\n"); exit(4);
}
static ull factor_log(int i, int j, ull h){
  ull p=P[i]; PHF* f=&phf[i][j];
  ull hq=(memo_i==i&&memo_f==j)?memo_hq:powmod_mont(i, h, f->cof);
  if(f->direct){ ull k=thash(hq,f->tmask); while(f->tk[k]!=~0ULL){ if(f->tk[k]==hq) return f->tv[k]; k=(k+1)&f->tmask; } fprintf(stderr,"subgroup lookup failed p=%llu\n",p); exit(4); }
  ull qe=f->qe, xq=0, qk=1;
  for(int k=0;k<f->e;k++){ ull hk=powmod(mulmod(hq, powmod(f->gqinv, xq, p), p), qe/(qk*f->q), p); ull dk=bsgs(f,hk,p); xq+=dk*qk; qk*=f->q; }
  return xq;
}
static ull dlog(int i, ull h){
  if(LOGT[i]) return (ull)LOGT[i][h];
  ull p=P[i], n=p-1; u128 acc=0;
  for(int j=0;j<nf[i];j++){ ull xq=factor_log(i,j,h); acc+=(u128)xq*phf[i][j].crtc; }
  ull x=(ull)(acc%n);
  if(powmod(G[i],x,p)!=h%p){ fprintf(stderr,"dlog verify failed p=%llu\n",p); exit(5); }
  return x;
}

static void read_cfg(const char* path){
  FILE* f=fopen(path,"r"); if(!f){perror("cfg"); exit(1);}
  char buf[128];
  fscanf(f,"%d %d %d %d",&Lold,&Lnew,&A,&q); for(int i=0;i<q;i++) fscanf(f,"%d",&digits[i]);
  fscanf(f,"%d",&np);
  for(int i=0;i<np;i++){ fscanf(f,"%llu %lld %lld %lld %llu %d",&P[i],&L2[i],&L3[i],&L7[i],&G[i],&nf[i]);
    for(int j=0;j<nf[i];j++) fscanf(f,"%llu %d",&FQ[i][j],&FE[i][j]);
    for(int j=0;j<Lnew;j++) fscanf(f,"%lld",&POW10[i][j]); for(int j=0;j<Lnew;j++) fscanf(f,"%lld",&R[i][j]);
    int has; fscanf(f,"%d",&has); if(has){ LOGT[i]=malloc(sizeof(int)*P[i]); for(ull j=0;j<P[i];j++) fscanf(f,"%d",&LOGT[i][j]); } else { LOGT[i]=NULL; ph_init(i); } }
  fscanf(f,"%d",&nc);
  for(int c=0;c<nc;c++){ fscanf(f,"%d",&cn[c]); for(int j=0;j<cn[c];j++) fscanf(f,"%d",&cidx[c][j]); for(int j=0;j<cn[c];j++) fscanf(f,"%lld",&cmod[c][j]);
    fscanf(f,"%s",buf); ccrt[c]=parse128(buf); ll hs; fscanf(f,"%lld",&hs);
    csize[c]=1; for(int j=0;j<cn[c];j++) csize[c]*=(ull)cmod[c][j];
    csparse[c]= csize[c] > (1ULL<<26);
    if(!csparse[c]){ crep[c]=malloc(sizeof(int)*2*csize[c]); for(ull i=0;i<2*csize[c];i++) crep[c][i]=-1; }
    else { hsz[c]=(ull)hs*4+64; hkeys[c]=malloc(sizeof(ull)*hsz[c]); hrep[c]=malloc(sizeof(int)*2*hsz[c]); for(ull i=0;i<hsz[c];i++) hkeys[c][i]=~0ULL; }
    for(ll h=0;h<hs;h++){ ll key[MAXP]; int rep[2]; for(int j=0;j<cn[c];j++) fscanf(f,"%lld",&key[j]); fscanf(f,"%d %d",&rep[0],&rep[1]);
      ull idx=0; for(int j=0;j<cn[c];j++) idx=idx*(ull)cmod[c][j]+(ull)key[j];
      if(!csparse[c]){ crep[c][idx*2]=rep[0]; crep[c][idx*2+1]=rep[1]; } else hput(c,idx,rep[0],rep[1]); } }
  fscanf(f,"%s",buf); N=parse128(buf);
  fscanf(f,"%d",&nlin); for(int j=0;j<nlin;j++){ fscanf(f,"%d %lld %lld %lld %s",&lidx[j],&lmod[j],&lg1[j],&lg2[j],buf); lcrt[j]=parse128(buf); }
  fscanf(f,"%lld %lld %lld %lld",&Uold[0][0],&Uold[0][1],&Uold[1][0],&Uold[1][1]);
  fscanf(f,"%lld %lld %lld %lld",&Unew[0][0],&Unew[0][1],&Unew[1][0],&Unew[1][1]);
  if(A>=512){ fprintf(stderr,"A=%d exceeds KT capacity\n",A); exit(12);} for(int a=0;a<=A;a++) fscanf(f,"%d",&KT[a]);
  fclose(f);
  pow10u[0]=1; for(int i=1;i<19;i++) pow10u[i]=pow10u[i-1]*10ULL;
}

static ll cnt_children=0, cnt_zero=0, cnt_dead=0, cnt_tail_dead=0, cnt_open=0, cnt_exact=0;
static int pattern_has[10][128];
static int cureps[MAXQ];
static int pidx_cur, a_cur, nu_cur; static i128 vb_cur, vc_cur;

static i128 mod128(i128 x, i128 m){ x%=m; if(x<0) x+=m; return x; }
static i128 mulmod128(i128 a, i128 b, i128 m){ // (a*b) mod m without overflow, m < 2^126
  a=mod128(a,m); b=mod128(b,m); i128 r=0;
  while(b){ if(b&1){ r+=a; if(r>=m) r-=m; } a<<=1; if(a>=m) a-=m; b>>=1; }
  return r; }

static void emit(const char* kind, i128 t1, i128 t2, ull Y){
  printf("%s %d %d %d",kind,pidx_cur,a_cur,nu_cur); for(int i=0;i<q;i++) printf(" %d",cureps[i]);
  putchar(' '); print128(t1); putchar(' '); print128(t2); if(Y) printf(" %llu",Y); putchar('\n');
}

static void tail_test(i128 t1, i128 t2){
  memset(pattern_has,0,sizeof pattern_has); for(int j=0;j<q;j++) pattern_has[digits[j]][cureps[j]]++;
  int K=KT[a_cur]; if(K>18) K=18;
  if(K<1){ emit("OPEN",t1,t2,0); cnt_open++; return; }
  ull m=pow10u[K];
  // b' = vb + t1*Uold[0][0] + t2*Uold[1][0], mod lam where 3^lam ≡ 1 mod 10^K  (lam = lcm(4*5^(K-1), 2^(K-2)))
  ull l5=4; for(int i=1;i<K;i++) l5*=5; ull l2=K>=3?(1ULL<<(K-2)):1; ull lam=l5/ (l5%l2==0?l2: 1) ; // lcm
  { ull a=l5,b=l2; while(b){ull t=a%b;a=b;b=t;} lam=l5/a*l2; }
  i128 LM=(i128)lam;
  i128 bb=mod128( mod128(vb_cur,LM) + mod128(t1,LM)*mod128((i128)Uold[0][0],LM) + mod128(t2,LM)*mod128((i128)Uold[1][0],LM), LM);
  i128 cc=mod128( mod128(vc_cur,LM) + mod128(t1,LM)*mod128((i128)Uold[0][1],LM) + mod128(t2,LM)*mod128((i128)Uold[1][1],LM), LM);
  ull Y=mulmod(mulmod(powmod(2,(ull)a_cur,m), powmod(3,(ull)bb,m), m), powmod(7,(ull)cc,m), m);
  int dg[20]; ull t=Y; for(int i=0;i<K;i++){ dg[i]=(int)(t%10); t/=10; }
  int nY=0; { ull tt=Y; while(tt){nY++; tt/=10;} }
  int cntm[10]={0}; for(int i=0;i<q;i++) cntm[digits[i]]++;
  int exact=0;
  if(Y>=10 && nY%Lnew==nu_cur%Lnew){ int have[10]={0}; int ok=1; int used[10][128]; memset(used,0,sizeof used);
    for(int i=0;i<nY;i++){ int d=dg[i]; if(d==0){ok=0;break;} if(d==1) continue; have[d]++; if(have[d]>cntm[d]){ok=0;break;} if(++used[d][i%Lnew]>pattern_has[d][i%Lnew]){ok=0;break;} }
    if(ok){ for(int d=2;d<=9;d++) if(have[d]!=cntm[d]) ok=0; } if(ok) exact=1; }
  int open=1; { int used[10][128]; memset(used,0,sizeof used); int have[10]={0};
    for(int i=0;i<K;i++){ int d=dg[i]; if(d==0){open=0;break;} if(d==1) continue; have[d]++; if(have[d]>cntm[d]){open=0;break;} if(++used[d][i%Lnew]>pattern_has[d][i%Lnew]){open=0;break;} } }
  if(exact){ emit("EXACT",t1,t2,Y); cnt_exact++; }
  if(open){ emit("OPEN",t1,t2,0); cnt_open++; }
  if(!exact&&!open) cnt_tail_dead++;
}

static unsigned char* cpm[MAXC]; static int ccheap[MAXC][MAXP]; static ull ycur[MAXP]; static int eager_verify=0;
static int cfac[MAXC][MAXP];            // factor index of (component, slot) in its prime, -1 for a table prime
static int lfac[8];                      // same for the linear components
static int corder[MAXC], ncorder;       // component evaluation order: table-only first
static ll bm[MAXC][MAXP]; static ll bl[8];   // parent-dependent offsets reduced mod the component modulus
static void lazy_init(void){
  for(int i=0;i<np;i++){ if(P[i]>(~0ULL>>1)/(1+8ULL*(ull)q)){ fprintf(stderr,"u64 bound violated: p=%llu q=%d\n",P[i],q); exit(8);}
    for(int k=0;k<Lnew;k++) if(R[i][k]<0||(ull)R[i][k]>=P[i]||POW10[i][k]<0||(ull)POW10[i][k]>=P[i]){ fprintf(stderr,"R/POW10 out of [0,p)\n"); exit(8);} }
  const char* e=getenv("LVLN_EAGER_VERIFY"); eager_verify=(e&&*e&&*e!='0');
  for(int c=0;c<nc;c++) for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; cfac[c][j]=-1; if(LOGT[i]) continue;
    for(int f=0;f<nf[i];f++) if(phf[i][f].qe==(ull)cmod[c][j]) cfac[c][j]=f;
    if(cfac[c][j]<0){ fprintf(stderr,"component modulus %lld is not a prime-power factor of p-1 (p=%llu)\n",cmod[c][j],P[i]); exit(7);} }
  for(int j=0;j<nlin;j++){ int i=lidx[j]; lfac[j]=-1; if(LOGT[i]) continue;
    for(int f=0;f<nf[i];f++) if(phf[i][f].qe==(ull)lmod[j]) lfac[j]=f;
    if(lfac[j]<0){ fprintf(stderr,"linear modulus %lld is not a prime-power factor of p-1 (p=%llu)\n",lmod[j],P[i]); exit(7);} }
  for(int c=0;c<nc;c++){ cpm[c]=NULL; int nch=0,nex=0; ull cs=1; for(int j=0;j<cn[c];j++){ ccheap[c][j]=(cfac[c][j]<0); if(ccheap[c][j]){ nch++; cs*=(ull)cmod[c][j]; if(cs>(1ULL<<24)) cs=(1ULL<<24)+1; } else nex++; }
    if(nch==0||nex==0||cs>(1ULL<<24)) continue;
    cpm[c]=calloc(cs,1);
    #define MARK(ixv) { ull ixx=(ixv); ull ck=0, mul=1; for(int j=cn[c]-1;j>=0;j--){ ull m=(ull)cmod[c][j]; ull dgt=ixx%m; ixx/=m; if(ccheap[c][j]){ ck+=dgt*mul; mul*=m; } } cpm[c][ck]=1; }
    if(!csparse[c]){ for(ull ix=0;ix<csize[c];ix++) if(crep[c][ix*2]>=0) MARK(ix) }
    else { for(ull h=0;h<hsz[c];h++) if(hkeys[c][h]!=~0ULL) MARK(hkeys[c][h]) } }
  int cost[MAXC]; for(int c=0;c<nc;c++){ cost[c]=0; for(int j=0;j<cn[c];j++) if(cfac[c][j]>=0) cost[c]++; }
  ncorder=0; for(int k=0;k<=MAXP;k++) for(int c=0;c<nc;c++) if(cost[c]==k) corder[ncorder++]=c;
}
static void parent_init(void){
  for(int i=0;i<np;i++){ i128 m=(i128)(P[i]-1);
    i128 X=(i128)a_cur*L2[i] + mod128(vb_cur,m)*L3[i] + mod128(vc_cur,m)*L7[i];
    for(int c=0;c<nc;c++) for(int j=0;j<cn[c];j++) if(cidx[c][j]==i) bm[c][j]=(ll)mod128(X,(i128)cmod[c][j]);
    for(int j=0;j<nlin;j++) if(lidx[j]==i) bl[j]=(ll)mod128(X,(i128)lmod[j]); }
}

static void process_rest(const ull* y){
  ull logs[MAXP];
  if(eager_verify) for(int i=0;i<np;i++) logs[i]=dlog(i,y[i]);
  else for(int i=0;i<np;i++) if(LOGT[i]) logs[i]=(ull)LOGT[i][y[i]];
  int* rps[MAXC];
  for(int k=0;k<ncorder;k++){ int c=corder[k]; ull idx=0; ull v[MAXP];
    if(cpm[c]){ ull ck=0, mul=1; for(int j=cn[c]-1;j>=0;j--) if(ccheap[c][j]){ int i=cidx[c][j]; ull m=(ull)cmod[c][j]; ull lg=logs[i]%m; ull vv=(ull)(((ll)lg+(ll)m-bm[c][j])%(ll)m); v[j]=vv; ck+=vv*mul; mul*=m; }
      if(!cpm[c][ck]){cnt_dead++; return;} }
    for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; ull m=(ull)cmod[c][j]; ull lg;
      if(cpm[c]&&ccheap[c][j]){ idx=idx*m+v[j]; continue; }
      if(eager_verify||LOGT[i]) lg=logs[i]%m; else lg=factor_log(i,cfac[c][j],y[i]);
      idx=idx*m+(ull)(((ll)lg+(ll)m-bm[c][j])%(ll)m); }
    int* rp; if(!csparse[c]){ rp=&crep[c][idx*2]; if(rp[0]<0){cnt_dead++; return;} } else { rp=hfind(c,idx); if(!rp){cnt_dead++; return;} }
    rps[c]=rp; }
  i128 t1=0,t2=0;
  for(int c=0;c<nc;c++){ t1+=ccrt[c]*rps[c][0]; t2+=ccrt[c]*rps[c][1]; }
  for(int j=0;j<nlin;j++){ int i=lidx[j]; ull m=(ull)lmod[j]; ull lg;
    if(eager_verify||LOGT[i]) lg=logs[i]%m; else lg=factor_log(i,lfac[j],y[i]);
    ll key=(ll)((((ll)lg+(ll)m-bl[j])%(ll)m)); ll x1,x2; ll g=egcd(lg1[j],lg2[j],&x1,&x2); if(g<0){g=-g;x1=-x1;x2=-x2;}
    ll d=g, mq=lmod[j]; { ll a=d,b=mq; while(b){ll t=a%b;a=b;b=t;} d=a; }
    if(key%d){cnt_dead++; return;} ll f=key/d, mm=mq/d; ll s=0; if(mm>1){ ll gi=(g/d)%mm; if(gi<0) gi+=mm; s=(ll)mulmod((ull)(f%mm),(ull)invmod((ull)gi,(ull)mm),(ull)mm); }
    t1+=mulmod128(lcrt[j], (i128)x1*s, N); t2+=mulmod128(lcrt[j], (i128)x2*s, N); }
  if(!eager_verify) for(int i=0;i<np;i++) if(!LOGT[i]) (void)dlog(i,y[i]);
  t1=mod128(t1,N); t2=mod128(t2,N);
  tail_test(t1,t2);
}


static int bi0=-1, bf0=-1, bc0=-1;
typedef struct { ull y[MAXP]; int eps[MAXQ]; } QC;
#define BQ 4
static QC bq[BQ]; static int nbq=0;
static void powmod_mont_n(int i, const ull* b, int n, ull e, ull* out){
  ull p=P[i], ni=mn[i], x[BQ], r[BQ];
  for(int l=0;l<BQ;l++){ ull bb=b[l<n?l:0]; x[l]=redc((u128)bb*mr2[i],p,ni); r[l]=mone[i]; }
  while(e){ if(e&1){ for(int l=0;l<BQ;l++) r[l]=redc((u128)r[l]*x[l],p,ni); } e>>=1; if(e){ for(int l=0;l<BQ;l++) x[l]=redc((u128)x[l]*x[l],p,ni); } }
  for(int l=0;l<n;l++) out[l]=redc((u128)r[l],p,ni);
}
static void batch_init(void){
  if(eager_verify) return;
  for(int k=0;k<ncorder;k++){ int c=corder[k]; for(int j=0;j<cn[c];j++) if(cfac[c][j]>=0){ int i=cidx[c][j]; if(!phf[i][cfac[c][j]].direct) return; bi0=i; bf0=cfac[c][j]; bc0=k; return; } }
}
static void flush_bq(void){
  if(!nbq) return;
  int saved[MAXQ]; memcpy(saved,cureps,sizeof(int)*q);
  ull bs[BQ], hb[BQ]; for(int l=0;l<nbq;l++) bs[l]=bq[l].y[bi0];
  powmod_mont_n(bi0,bs,nbq,phf[bi0][bf0].cof,hb);
  for(int l=0;l<nbq;l++){ memcpy(cureps,bq[l].eps,sizeof(int)*q); memo_i=bi0; memo_f=bf0; memo_hq=hb[l]; process_rest(bq[l].y); memo_i=-1; }
  nbq=0; memcpy(cureps,saved,sizeof(int)*q);
}
static void process_child(void){
  cnt_children++;
  ull y[MAXP];
  for(int i=0;i<np;i++){ ull yy=ycur[i]%P[i]; if(yy==0){cnt_zero++; return;} y[i]=yy; }
  if(bi0<0){ process_rest(y); return; }
  ull logs[MAXP]; for(int i=0;i<np;i++) if(LOGT[i]) logs[i]=(ull)LOGT[i][y[i]];
  for(int k=0;k<=bc0;k++){ int c=corder[k];
    if(k<bc0){ ull idx=0; for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; ull m=(ull)cmod[c][j]; idx=idx*m+(ull)(((ll)(logs[i]%m)+(ll)m-bm[c][j])%(ll)m); }
      if(!csparse[c]){ if(crep[c][idx*2]<0){cnt_dead++; return;} } else if(!hfind(c,idx)){cnt_dead++; return;} }
    else if(cpm[c]){ ull ck=0, mul=1; for(int j=cn[c]-1;j>=0;j--) if(ccheap[c][j]){ int i=cidx[c][j]; ull m=(ull)cmod[c][j]; ull vv=(ull)(((ll)(logs[i]%m)+(ll)m-bm[c][j])%(ll)m); ck+=vv*mul; mul*=m; }
      if(!cpm[c][ck]){cnt_dead++; return;} } }
  memcpy(bq[nbq].y,y,sizeof(ull)*np); memcpy(bq[nbq].eps,cureps,sizeof(int)*q); if(++nbq==BQ) flush_bq();
}

// enumerate children: per digit group, residues grouped by value with multiplicity; choose k lifted
static int ng, gstart[10], gk[10], gd[10];
static int dvals[MAXQ], dmult[MAXQ], ndist;   // distinct residue values of the current group
static void rec_dist(int g, int di, int pos);
static void rec_groups(int g, int pos){
  if(g==ng){ process_child(); return; }
  // distinct residues of group g from the parent's eps
  ndist=0; for(int i=gstart[g]; i<gstart[g]+gk[g]; i++){ int r=cureps[i]; (void)r; }
  rec_dist(g,0,pos);
}
static int parent_eps[MAXQ];
static void rec_dist(int g, int di, int pos){
  // build distinct list lazily at di==0
  static int dv[10][MAXQ], dm[10][MAXQ], nd[10];
  if(di==0){ nd[g]=0; for(int i=gstart[g]; i<gstart[g]+gk[g]; i++){ int r=parent_eps[i]; int f=-1; for(int j=0;j<nd[g];j++) if(dv[g][j]==r) f=j; if(f<0){ dv[g][nd[g]]=r; dm[g][nd[g]]=1; nd[g]++; } else dm[g][f]++; } }
  if(di==nd[g]){ rec_groups(g+1,pos); return; }
  int r=dv[g][di], m=dm[g][di], d=gd[g];
  for(int k=0;k<=m;k++){ // k copies lifted
    for(int c=0;c<m;c++){ int rr = (c<k)? r+Lold : r; cureps[pos+c]=rr; }
    { ull dsum[MAXP]; for(int i=0;i<np;i++){ ull ds=(ull)(d-1)*((ull)(m-k)*(ull)POW10[i][r]+(ull)k*(ull)POW10[i][r+Lold]); dsum[i]=ds; ycur[i]+=ds; }
      rec_dist(g,di+1,pos+m);
      for(int i=0;i<np;i++) ycur[i]-=dsum[i]; }
  }
}

// ---- level-12 -> 24 join: meet-in-the-middle on one or two key primes ----
// A child's residue at a key prime p is a sum of independent per-slot contributions. It can survive only if that residue
// lies in the parent's coset image (the subgroup K generated by the Uold columns, times the parent's 2^a 3^b 7^c), the
// membership test process_rest applies first. The slot space is split into halves A and B and only pairs whose key-prime
// residues meet reach process_child. A parent whose half would exceed JOIN_HALF_MAX takes the plain enumeration.
#define MAXS 64
typedef struct { int d, r, m, pos; } Slot;
static Slot slots[MAXS]; static int nslots;
static ull *Kx, *Ky; static ll nK;
static ll jc_total = 0, plain_children = 0;
static ull *HA, *HB; static ll nA, nB;
static int inA[MAXS];
static ll *jhead, *jnxt; static ull hsB;
static ull contrib_[MAXS][64][MAXP];
#define MAXSETS 16
static int nsets, sp0[MAXSETS], sp1[MAXSETS]; static ll sK[MAXSETS]; static ull *sKx[MAXSETS], *sKy[MAXSETS]; static double sacc[MAXSETS];
#define W_PROBE 20.0
#define W_CAND 100.0
#define W_BUILD 10.0
#define JOIN_KLIMIT 400000
#define JOIN_HALF_MAX 30000000LL
#define HASHMUL 11400714819323198485ULL
#ifdef JOIN_MUTANTS
static int mutant = 0, force_set = -1;
#endif

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
  ull key0 = 1 * P[i1] + 1; tab[(key0 * HASHMUL) & (hs - 1)] = key0; qx[0] = 1; qy[0] = 1; n = 1;
  for(ll h = 0; h < n; h++){
    for(int v = 0; v < 2; v++){
      ull x = mulmod(qx[h], g[v][0], P[i0]), y = mulmod(qy[h], g[v][1], P[i1]); ull key = x * P[i1] + y;
      ull s = (key * HASHMUL) & (hs - 1); int found = 0;
      while(tab[s] != ~0ULL){ if(tab[s] == key){ found = 1; break; } s = (s + 1) & (hs - 1); }
      if(found) continue;
      if(n >= limit){ free(tab); free(qx); free(qy); return 0; }
      tab[s] = key; qx[n] = x; qy[n] = y; n++;
    }
  }
  free(tab); *ox = qx; *oy = qy; *on = n; return 1;
}

static int build_K1(int i0, ll limit, ull **ox, ull **oy, ll *on){
  ull g[2];
  for(int v = 0; v < 2; v++) g[v] = mulmod(pw(3, Uold[v][0], P[i0]), pw(7, Uold[v][1], P[i0]), P[i0]);
  ull *qx = malloc(sizeof(ull) * limit); ll n = 1; qx[0] = 1;
  ull hs = 1; while(hs < (ull)(4 * limit)) hs <<= 1;
  ull *tab = malloc(sizeof(ull) * hs); for(ull i = 0; i < hs; i++) tab[i] = ~0ULL;
  tab[(1ULL * HASHMUL) & (hs - 1)] = 1;
  for(ll h = 0; h < n; h++) for(int v = 0; v < 2; v++){
    ull x = mulmod(qx[h], g[v], P[i0]); ull s = (x * HASHMUL) & (hs - 1); int found = 0;
    while(tab[s] != ~0ULL){ if(tab[s] == x){ found = 1; break; } s = (s + 1) & (hs - 1); }
    if(found) continue;
    if(n >= limit){ free(tab); free(qx); return 0; }
    tab[s] = x; qx[n++] = x;
  }
  free(tab); *ox = qx; *oy = calloc(n, sizeof(ull)); *on = n; return 1;
}

static void fill_half(int want, ull *H, ll cnt){
  int idxs[MAXS], ns = 0;
  for(int s = 0; s < nslots; s++) if(inA[s] == want) idxs[ns++] = s;
  for(ll t = 0; t < cnt; t++){
    ll rest = t; ull acc[MAXP]; for(int i = 0; i < np; i++) acc[i] = 0;
    for(int u = 0; u < ns; u++){ int s = idxs[u]; int rad = slots[s].m + 1; int k = (int)(rest % rad); rest /= rad;
      for(int i = 0; i < np; i++) acc[i] += contrib_[s][k][i]; }
    for(int i = 0; i < np; i++) H[t * np + i] = acc[i] % P[i];
  }
}

static void decode_half(int want, ll t, int *ks){
  ll rest = t;
  for(int s = 0; s < nslots; s++) if(inA[s] == want){ int rad = slots[s].m + 1; ks[s] = (int)(rest % rad); rest /= rad; }
}

static int join_setup(void){
#ifdef JOIN_MUTANTS
  { const char *me = getenv("JOIN_MUTANT"); if(me) mutant = atoi(me); const char *fs = getenv("JOIN_FORCE_SET"); if(fs) force_set = atoi(fs); }
#endif
  nsets = 0;
  for(int i = 0; i < np; i++){
    ull *x, *y; ll n;
    if(build_K1(i, JOIN_KLIMIT, &x, &y, &n)){ sp0[nsets] = i; sp1[nsets] = -1; sK[nsets] = n; sKx[nsets] = x; sKy[nsets] = y; sacc[nsets] = (double)n / (double)(P[i] - 1); nsets++; }
  }
  if(np >= 3) for(int i = 0; i < np; i++) for(int j = i + 1; j < np; j++){
    ull *x, *y; ll n;
    if(build_K(i, j, JOIN_KLIMIT, &x, &y, &n)){ sp0[nsets] = i; sp1[nsets] = j; sK[nsets] = n; sKx[nsets] = x; sKy[nsets] = y; sacc[nsets] = (double)n / ((double)(P[i] - 1) * (double)(P[j] - 1)); nsets++; }
  }
  return nsets > 0;
}

static void plain_parent(int nu){
  ll before = cnt_children;
  for(int dn = 0; dn < 2; dn++){ nu_cur = nu + dn * Lold; for(int i = 0; i < np; i++) ycur[i] = (ull)R[i][nu_cur]; rec_groups(0, 0); flush_bq(); }
  plain_children += cnt_children - before;
}

static int join_run(const char *parents_path){
  ll maxK = 1; for(int s = 0; s < nsets; s++) if(sK[s] > maxK) maxK = sK[s];
  FILE *pf = fopen(parents_path, "r"); if(!pf){ perror("parents"); return 1; }
  char line[4096]; int pidx = 0;
  ull *Tp0 = malloc(sizeof(ull) * maxK), *Tp1 = malloc(sizeof(ull) * maxK);
  while(fgets(line, sizeof line, pf)){
    int a, nu; if(sscanf(line, "%d %d", &a, &nu) != 2) continue;
    char *tok = strtok(line, " \n"); a = atoi(tok); tok = strtok(NULL, " \n"); nu = atoi(tok);
    for(int i = 0; i < q; i++){ tok = strtok(NULL, " \n"); parent_eps[i] = atoi(tok); }
    tok = strtok(NULL, " \n"); vb_cur = parse128(tok); tok = strtok(NULL, " \n"); vc_cur = parse128(tok);
    pidx_cur = pidx; a_cur = a; parent_init();

    nslots = 0; int pos = 0; double C0 = 1; int overflow = 0;
    for(int g = 0; g < ng; g++){
      int nd = 0; int dv[MAXQ], dm[MAXQ];
      for(int i = gstart[g]; i < gstart[g] + gk[g]; i++){ int r = parent_eps[i]; int f = -1; for(int j = 0; j < nd; j++) if(dv[j] == r) f = j; if(f < 0){ dv[nd] = r; dm[nd] = 1; nd++; } else dm[f]++; }
      for(int j = 0; j < nd; j++){ if(nslots >= MAXS){ overflow = 1; break; } slots[nslots].d = gd[g]; slots[nslots].r = dv[j]; slots[nslots].m = dm[j]; slots[nslots].pos = pos; pos += dm[j]; C0 *= (dm[j] + 1); nslots++; }
    }
    if(overflow){ plain_parent(nu); pidx++; continue; }
    int bs = 0; double bestc = 1e300;
    for(int s = 0; s < nsets; s++){
      double K = (double)sK[s]; double na = sqrt(C0 / K); if(na < 1) na = 1;
      double cost = W_PROBE * na * K + W_BUILD * (na + C0 / na) + W_CAND * C0 * sacc[s];
      if(cost < bestc){ bestc = cost; bs = s; }
    }
#ifdef JOIN_MUTANTS
    if(force_set >= 0 && force_set < nsets) bs = force_set;
#endif
    int jp0 = sp0[bs], jp1 = sp1[bs]; Kx = sKx[bs]; Ky = sKy[bs]; nK = sK[bs];
    ull p0 = P[jp0], p1 = jp1 >= 0 ? P[jp1] : 1;
    double target = sqrt(C0 / (double)nK); if(target < 1) target = 1;
    double prodA = 1;
    for(int s = 0; s < nslots; s++){ int rad = slots[s].m + 1; if(prodA * rad <= target * 1.5){ inA[s] = 1; prodA *= rad; } else inA[s] = 0; }
    nA = (ll)prodA; nB = (ll)(C0 / prodA + 0.5);
    if(nB > JOIN_HALF_MAX){ plain_parent(nu); pidx++; continue; }
    for(int s = 0; s < nslots; s++) for(int k = 0; k <= slots[s].m; k++) for(int i = 0; i < np; i++){
      ull ds = (ull)(slots[s].d - 1) * ((ull)(slots[s].m - k) * (ull)POW10[i][slots[s].r] + (ull)k * (ull)POW10[i][slots[s].r + Lold]);
      contrib_[s][k][i] = ds % P[i]; }
    HA = realloc(HA, sizeof(ull) * nA * np); HB = realloc(HB, sizeof(ull) * nB * np);
    fill_half(1, HA, nA); fill_half(0, HB, nB);
    hsB = 1; while(hsB < (ull)(2 * nB)) hsB <<= 1;
    jhead = realloc(jhead, sizeof(ll) * hsB); jnxt = realloc(jnxt, sizeof(ll) * nB);
    for(ull h = 0; h < hsB; h++) jhead[h] = -1;
    for(ll t = 0; t < nB; t++){ ull key = HB[t * np + jp0] * p1 + (jp1 >= 0 ? HB[t * np + jp1] : 0); ull h = (key * HASHMUL) & (hsB - 1); jnxt[t] = jhead[h]; jhead[h] = t; }

    ull s0 = powmod(2, (ull)a, p0), s1 = jp1 >= 0 ? powmod(2, (ull)a, p1) : 0;
#ifdef JOIN_MUTANTS
    if(mutant == 2){ s0 = 1; if(jp1 >= 0) s1 = 1; }
#endif
    s0 = mulmod(s0, mulmod(pw(3, (ll)mod128(vb_cur, (i128)(p0 - 1)), p0), pw(7, (ll)mod128(vc_cur, (i128)(p0 - 1)), p0), p0), p0);
    if(jp1 >= 0) s1 = mulmod(s1, mulmod(pw(3, (ll)mod128(vb_cur, (i128)(p1 - 1)), p1), pw(7, (ll)mod128(vc_cur, (i128)(p1 - 1)), p1), p1), p1);
    ll nT = 0;
    for(ll j = 0; j < nK; j++){
#ifdef JOIN_MUTANTS
      if(mutant == 3 && (j & 1)) continue;
#endif
      Tp0[nT] = mulmod(s0, Kx[j], p0); Tp1[nT] = jp1 >= 0 ? mulmod(s1, Ky[j], p1) : 0; nT++; }

    for(int dn = 0; dn < 2; dn++){
      nu_cur = nu + dn * Lold; jc_total += (ll)(C0 + 0.5);
      ull base[MAXP]; for(int i = 0; i < np; i++) base[i] = (ull)R[i][nu_cur];
      for(ll ia = 0; ia < nA; ia++){
        ull *av = &HA[ia * np];
        for(ll j = 0; j < nT; j++){
          ull x = Tp0[j] + 2 * p0 - base[jp0] - av[jp0]; x -= (x >= p0) * p0; x -= (x >= p0) * p0;
          ull y = 0;
          if(jp1 >= 0){ y = Tp1[j] + 2 * p1 - base[jp1] - av[jp1]; y -= (y >= p1) * p1; y -= (y >= p1) * p1; }
          ull key = x * p1 + y; ull h = (key * HASHMUL) & (hsB - 1);
          for(ll t = jhead[h]; t >= 0; t = jnxt[t]){
            if(HB[t * np + jp0] != x || (jp1 >= 0 && HB[t * np + jp1] != y)) continue;
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
  cnt_children = jc_total + plain_children;
  fprintf(stderr,"parents %d children %lld zero %lld dead %lld tail-dead %lld open %lld exact %lld\n",pidx,cnt_children,cnt_zero,cnt_dead,cnt_tail_dead,cnt_open,cnt_exact);
  return 0;
}

int main(int argc,char**argv){
  if(argc<3){fprintf(stderr,"usage: lvlN cfg parents\n"); return 1;}
  read_cfg(argv[1]); lazy_init(); batch_init();
  ng=0; for(int i=0;i<q;i++){ if(ng==0||gd[ng-1]!=digits[i]){ gd[ng]=digits[i]; gstart[ng]=i; gk[ng]=1; ng++; } else gk[ng-1]++; }
  if(Lold==12 && Lnew==24 && join_setup()) return join_run(argv[2]);
  FILE* pf=fopen(argv[2],"r"); if(!pf){perror("parents"); return 1;}
  char line[4096]; int pidx=0;
  while(fgets(line,sizeof line,pf)){
    char* s=line; int a,nu; if(sscanf(s,"%d %d",&a,&nu)!=2) continue;
    // tokenize
    char* tok=strtok(line," \n"); a=atoi(tok); tok=strtok(NULL," \n"); nu=atoi(tok);
    for(int i=0;i<q;i++){ tok=strtok(NULL," \n"); parent_eps[i]=atoi(tok); }
    tok=strtok(NULL," \n"); vb_cur=parse128(tok); tok=strtok(NULL," \n"); vc_cur=parse128(tok);
    pidx_cur=pidx; a_cur=a; parent_init();
    for(int dn=0;dn<2;dn++){ nu_cur=nu+dn*Lold; for(int i=0;i<np;i++) ycur[i]=(ull)R[i][nu_cur]; rec_groups(0,0); flush_bq(); }
    pidx++;
  }
  fprintf(stderr,"parents %d children %lld zero %lld dead %lld tail-dead %lld open %lld exact %lld\n",pidx,cnt_children,cnt_zero,cnt_dead,cnt_tail_dead,cnt_open,cnt_exact);
  return 0;
}
