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
static i128 N; static ll Uold[2][2], Unew[2][2]; static int KT[64];
static ull pow10u[19];

static ull mulmod(ull a, ull b, ull m){ return (ull)(((u128)a*b)%m); }
static ull powmod(ull b, ull e, ull m){ ull r=1%m; b%=m; while(e){ if(e&1) r=mulmod(r,b,m); b=mulmod(b,b,m); e>>=1;} return r; }
static ll egcd(ll a, ll b, ll*x, ll*y){ if(b==0){*x=1;*y=0;return a;} ll x1,y1; ll g=egcd(b,a%b,&x1,&y1); *x=y1; *y=x1-(a/b)*y1; return g; }
static ull invmod(ull a, ull m){ ll x,y; ll g=egcd((ll)(a%m),(ll)m,&x,&y); if(g!=1 && g!=-1){ fprintf(stderr,"no inverse\n"); exit(3);} x%= (ll)m; if(x<0) x+=m; return (ull)x; }
static i128 parse128(const char* s){ i128 v=0; int neg=0; if(*s=='-'){neg=1;s++;} while(*s>='0'&&*s<='9'){ v=v*10+(*s-'0'); s++; } return neg?-v:v; }
static void print128(i128 v){ char buf[64]; int n=0; int neg=v<0; u128 u=neg?(u128)(-v):(u128)v; if(u==0) buf[n++]='0'; while(u){ buf[n++]='0'+(int)(u%10); u/=10; } if(neg) putchar('-'); while(n) putchar(buf[--n]); }

// ---- Pohlig–Hellman with per-prime-factor BSGS tables
typedef struct { ull q; int e; ull gamma; ull m; ull *keys; ull *vals; ull hsize; } PHF;
static PHF phf[MAXP][MAXF];
static void hins(PHF* f, ull key, ull val){ ull h=(key*11400714819323198485ULL)%f->hsize; while(f->keys[h]!=~0ULL) h=(h+1)%f->hsize; f->keys[h]=key; f->vals[h]=val; }
static int hget(PHF* f, ull key, ull* val){ ull h=(key*11400714819323198485ULL)%f->hsize; while(f->keys[h]!=~0ULL){ if(f->keys[h]==key){*val=f->vals[h]; return 1;} h=(h+1)%f->hsize; } return 0; }
static void ph_init(int i){
  ull p=P[i], n=p-1;
  for(int j=0;j<nf[i];j++){ PHF* f=&phf[i][j]; f->q=FQ[i][j]; f->e=FE[i][j]; ull qe=1; for(int k=0;k<f->e;k++) qe*=f->q;
    ull gi=powmod(G[i], n/qe, p); f->gamma=powmod(gi, qe/f->q, p);  // order q
    ull m=1; while(m*m<f->q) m++; f->m=m; f->hsize=4*m+16; f->keys=malloc(sizeof(ull)*f->hsize); f->vals=malloc(sizeof(ull)*f->hsize);
    for(ull h=0;h<f->hsize;h++) f->keys[h]=~0ULL;
    ull cur=1; for(ull jj=0;jj<m;jj++){ ull dummy; if(!hget(f,cur,&dummy)) hins(f,cur,jj); cur=mulmod(cur,f->gamma,p); } }
}
static ull bsgs(PHF* f, ull h, ull p){ // x in [0,q) with gamma^x = h
  ull m=f->m; ull ginv_m=powmod(invmod(f->gamma,p), m, p); ull cur=h;
  for(ull i=0;i<m+1;i++){ ull jv; if(hget(f,cur,&jv)) return (i*m+jv)%f->q; cur=mulmod(cur,ginv_m,p); }
  fprintf(stderr,"bsgs failed\n"); exit(4);
}
static ull dlog(int i, ull h){
  if(LOGT[i]) return (ull)LOGT[i][h];
  ull p=P[i], n=p-1; ull x=0, M=1;
  for(int j=0;j<nf[i];j++){ PHF* f=&phf[i][j]; ull qe=1; for(int k=0;k<f->e;k++) qe*=f->q;
    ull gq=powmod(G[i], n/qe, p), hq=powmod(h, n/qe, p); ull xq=0, qk=1;
    for(int k=0;k<f->e;k++){ ull hk=powmod(mulmod(hq, powmod(invmod(gq,p), xq, p), p), qe/(qk*f->q), p); ull dk=bsgs(f,hk,p); xq+=dk*qk; qk*=f->q; }
    // CRT x ≡ xq (mod qe)
    ull t=((i128)(xq%qe) - (i128)(x%qe) + qe)%qe; t=mulmod(t, invmod(M%qe,qe), qe); x+=M*t; M*=qe; }
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
  for(int a=0;a<=A;a++) fscanf(f,"%d",&KT[a]);
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

static void process_child(void){
  cnt_children++;
  ull logs[MAXP];
  for(int i=0;i<np;i++){ i128 y=R[i][nu_cur]; for(int j=0;j<q;j++) y+=(i128)(digits[j]-1)*POW10[i][cureps[j]]; y%= (i128)P[i]; if(y==0){cnt_zero++; return;} logs[i]=dlog(i,(ull)y); }
  // adjusted targets: w_p - a*l2 - vb*l3 - vc*l7  (mod p-1)
  ull adj[MAXP];
  for(int i=0;i<np;i++){ i128 m=(i128)(P[i]-1); i128 v=(i128)logs[i] - (i128)a_cur*L2[i] - mod128(vb_cur,m)*L3[i] - mod128(vc_cur,m)*L7[i]; adj[i]=(ull)mod128(v,m); }
  i128 t1=0,t2=0;
  for(int c=0;c<nc;c++){ ull idx=0; for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; idx=idx*(ull)cmod[c][j]+(ull)(adj[i]%(ull)cmod[c][j]); }
    int* rp; if(!csparse[c]){ rp=&crep[c][idx*2]; if(rp[0]<0){cnt_dead++; return;} } else { rp=hfind(c,idx); if(!rp){cnt_dead++; return;} }
    t1+=ccrt[c]*rp[0]; t2+=ccrt[c]*rp[1]; }
  for(int j=0;j<nlin;j++){ ll key=(ll)(adj[lidx[j]]%lmod[j]); ll x1,x2; ll g=egcd(lg1[j],lg2[j],&x1,&x2); if(g<0){g=-g;x1=-x1;x2=-x2;}
    ll d=g, m=lmod[j]; { ll a=d,b=m; while(b){ll t=a%b;a=b;b=t;} d=a; }
    if(key%d){cnt_dead++; return;} ll f=key/d, mm=m/d; ll s=0; if(mm>1){ ll gi=(g/d)%mm; if(gi<0) gi+=mm; s=(ll)mulmod((ull)(f%mm),(ull)invmod((ull)gi,(ull)mm),(ull)mm); }
    t1+=mulmod128(lcrt[j], (i128)x1*s, N); t2+=mulmod128(lcrt[j], (i128)x2*s, N); }
  t1=mod128(t1,N); t2=mod128(t2,N);
  tail_test(t1,t2);
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
    for(int c=0;c<m;c++){ int rr = (c<k)? r+Lold : r; cureps[pos+c]=rr; pattern_has[d][rr]++; }
    rec_dist(g,di+1,pos+m);
    for(int c=0;c<m;c++){ int rr = (c<k)? r+Lold : r; pattern_has[d][rr]--; }
  }
}

int main(int argc,char**argv){
  if(argc<3){fprintf(stderr,"usage: lvlN cfg parents\n"); return 1;}
  read_cfg(argv[1]);
  ng=0; for(int i=0;i<q;i++){ if(ng==0||gd[ng-1]!=digits[i]){ gd[ng]=digits[i]; gstart[ng]=i; gk[ng]=1; ng++; } else gk[ng-1]++; }
  FILE* pf=fopen(argv[2],"r"); if(!pf){perror("parents"); return 1;}
  char line[4096]; int pidx=0;
  while(fgets(line,sizeof line,pf)){
    char* s=line; int a,nu; if(sscanf(s,"%d %d",&a,&nu)!=2) continue;
    // tokenize
    char* tok=strtok(line," \n"); a=atoi(tok); tok=strtok(NULL," \n"); nu=atoi(tok);
    for(int i=0;i<q;i++){ tok=strtok(NULL," \n"); parent_eps[i]=atoi(tok); }
    tok=strtok(NULL," \n"); vb_cur=parse128(tok); tok=strtok(NULL," \n"); vc_cur=parse128(tok);
    pidx_cur=pidx; a_cur=a;
    for(int dn=0;dn<2;dn++){ nu_cur=nu+dn*Lold; memset(pattern_has,0,sizeof pattern_has); rec_groups(0,0); }
    pidx++;
  }
  fprintf(stderr,"parents %d children %lld zero %lld dead %lld tail-dead %lld open %lld exact %lld\n",pidx,cnt_children,cnt_zero,cnt_dead,cnt_tail_dead,cnt_open,cnt_exact);
  return 0;
}
