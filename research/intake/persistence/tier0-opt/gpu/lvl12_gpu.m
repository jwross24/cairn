// lvl12_gpu: Metal implementation of the lvl12 contract (see tier0/lvl12.c).
// usage: lvl12_gpu cfg [nu_lo nu_hi]
// stdout: OPEN / EXACT records exactly as lvl12; stderr: the lvl12 counter line.
// env: LVL12_GPU_TIMING=1 prints a phase breakdown on stderr; LVL12_GPU_PLANT=1|2 plants a defect.
#import <Foundation/Foundation.h>
#import <Metal/Metal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <mach/mach_time.h>
#include <math.h>
#include "shader_src.h"

typedef long long ll; typedef unsigned long long ull;
#define MAXP 8
#define MAXQ 40
#define MAXC 8
static int L, A, q, digits[MAXQ];
static int np; static ll P[MAXP], L2[MAXP], L3[MAXP], L7[MAXP]; static ll POW10[MAXP][64], R[MAXP][64]; static int *LOGT[MAXP];
static int nc; static int cn[MAXC], cidx[MAXC][MAXP]; static ll cmod[MAXC][MAXP], ccrt[MAXC]; static ll csize[MAXC];
static int *crep[MAXC];
static ll N, G, U[3], U2[2][2]; static int KT[64];
static int *CONTRIB[MAXC][MAXP];
static int ng, gd[10], gk[10];

static void die(const char* m){ fprintf(stderr,"lvl12_gpu: %s\n",m); exit(4); }
static double now_s(void){ static mach_timebase_info_data_t tb; if(!tb.denom) mach_timebase_info(&tb); return (double)mach_absolute_time()*tb.numer/tb.denom*1e-9; }

static void read_cfg(const char* path){
  FILE* f=fopen(path,"r"); if(!f){perror("cfg"); exit(1);}
  if(fscanf(f,"%d %d %d",&L,&A,&q)!=3) exit(2);
  if(q>MAXQ||L>64) die("q or L too large");
  for(int i=0;i<q;i++) if(fscanf(f,"%d",&digits[i])!=1) exit(2);
  if(fscanf(f,"%d",&np)!=1||np>MAXP) exit(2);
  for(int i=0;i<np;i++){ if(fscanf(f,"%lld %lld %lld %lld",&P[i],&L2[i],&L3[i],&L7[i])!=4) exit(2);
    for(int j=0;j<L;j++) if(fscanf(f,"%lld",&POW10[i][j])!=1) exit(2);
    for(int j=0;j<L;j++) if(fscanf(f,"%lld",&R[i][j])!=1) exit(2);
    LOGT[i]=malloc(sizeof(int)*P[i]); for(ll j=0;j<P[i];j++) if(fscanf(f,"%d",&LOGT[i][j])!=1) exit(2); }
  if(fscanf(f,"%d",&nc)!=1||nc>MAXC) exit(2);
  for(int c=0;c<nc;c++){ if(fscanf(f,"%d",&cn[c])!=1) exit(2); for(int j=0;j<cn[c];j++) if(fscanf(f,"%d",&cidx[c][j])!=1) exit(2);
    for(int j=0;j<cn[c];j++) if(fscanf(f,"%lld",&cmod[c][j])!=1) exit(2);
    ll hs; if(fscanf(f,"%lld %lld",&ccrt[c],&hs)!=2) exit(2);
    csize[c]=1; for(int j=0;j<cn[c];j++) csize[c]*=cmod[c][j];
    crep[c]=malloc(sizeof(int)*3*csize[c]); for(ll i=0;i<3*csize[c];i++) crep[c][i]=-1;
    for(ll h=0;h<hs;h++){ ll key[MAXP]; int rep[3]; for(int j=0;j<cn[c];j++) if(fscanf(f,"%lld",&key[j])!=1) exit(2); for(int j=0;j<3;j++) if(fscanf(f,"%d",&rep[j])!=1) exit(2);
      ll idx=0; for(int j=0;j<cn[c];j++) idx=idx*cmod[c][j]+key[j];
      crep[c][idx*3]=rep[0]; crep[c][idx*3+1]=rep[1]; crep[c][idx*3+2]=rep[2]; } }
  if(fscanf(f,"%lld %lld %lld %lld %lld",&N,&G,&U[0],&U[1],&U[2])!=5) exit(2);
  if(fscanf(f,"%lld %lld %lld %lld",&U2[0][0],&U2[0][1],&U2[1][0],&U2[1][1])!=4) exit(2);
  for(int a=0;a<=A;a++) if(fscanf(f,"%d",&KT[a])!=1) exit(2);
  fclose(f);
  for(int cc=0;cc<nc;cc++){ for(int i=0;i<np;i++) CONTRIB[cc][i]=NULL;
    ll stride=1; for(int j=cn[cc]-1;j>=0;j--){ int i=cidx[cc][j]; CONTRIB[cc][i]=malloc(sizeof(int)*(P[i]-1));
      for(ll lg=0;lg<P[i]-1;lg++) CONTRIB[cc][i][lg]=(int)((lg%cmod[cc][j])*stride); stride*=cmod[cc][j]; } }
  ng=0; for(int i=0;i<q;i++){ if(ng==0||gd[ng-1]!=digits[i]){ gd[ng]=digits[i]; gk[ng]=1; ng++; } else gk[ng-1]++; }
}

static ll mod_nn(ll a, ll m){ a%=m; return a<0?a+m:a; }

static NSMutableString* list_u(const unsigned* v, int n){
  NSMutableString* s=[NSMutableString string]; for(int i=0;i<n;i++) [s appendFormat:@"%s%uu", i?",":"", v[i]]; return s; }

int main(int argc, char** argv){
  @autoreleasepool {
  double t_start=now_s();
  if(argc<2){ fprintf(stderr,"usage: lvl12_gpu cfg [nu_lo nu_hi]\n"); return 1; }
  read_cfg(argv[1]);
  int lo=0, hi=L; if(argc>=4){ lo=atoi(argv[2]); hi=atoi(argv[3]); }
  int plant = getenv("LVL12_GPU_PLANT") ? atoi(getenv("LVL12_GPU_PLANT")) : 0;
  int timing = getenv("LVL12_GPU_TIMING") != NULL;
  if(hi>L) hi=L; if(lo>=hi){ fprintf(stderr,"patterns 0 zero 0 prefilter-dead 0 (a,pattern) 0 tail-dead 0 open 0 exact 0\n"); return 0; }
  int NUN=hi-lo;

  for(int a=0;a<=A;a++) if(KT[a]!=3) die("unsupported: KT[a] != 3 (GPU tail is specialized to K == 3)");
  if(A>=64) die("A too large");
  { ull t=1; for(int i=0;i<100;i++) t=t*3%1000; if(t!=1) die("3^100 != 1 mod 1000"); t=1; for(int i=0;i<100;i++) t=t*7%1000; if(t!=1) die("7^100 != 1 mod 1000"); }
  if(np>6) die("np > 6");
  for(int i=0;i<np;i++) for(int j=0;j<L;j++){ R[i][j]=mod_nn(R[i][j],P[i]); POW10[i][j]=mod_nn(POW10[i][j],P[i]); }

  // bundles of two consecutive primes
  int NB=(np+1)/2; ll MB[3]={1,1,1}; int bp[3][2]={{-1,-1},{-1,-1},{-1,-1}};
  for(int b=0;b<NB;b++){ for(int t=0;t<2;t++){ int i=2*b+t; if(i<np){ bp[b][t]=i; MB[b]*=P[i]; } } }
  if(NB>3) die("NB > 3");
  for(int b=0;b<NB;b++) if(MB[b]>65535) die("bundle modulus too large");
  int *crt_map[3];
  for(int b=0;b<NB;b++){ crt_map[b]=malloc(sizeof(int)*MB[b]);
    ll p0=P[bp[b][0]], p1= bp[b][1]>=0 ? P[bp[b][1]] : 1;
    for(ll r=0;r<MB[b];r++) crt_map[b][(r%p0)*p1+(r%p1)]=(int)r; }
  #define BRES(b, y0, y1) (crt_map[b][((y0)%P[bp[b][0]])*(bp[b][1]>=0?P[bp[b][1]]:1) + (bp[b][1]>=0?((y1)%P[bp[b][1]]):0)])

  // group multiset tables
  int nG[10]; unsigned goff[10]; unsigned YTOT=0; unsigned char* gres[10]; unsigned short* yt[3];
  for(int g=0;g<ng;g++){
    ll n=1; for(int t=0;t<gk[g];t++) n=n*(L+t)/(t+1); // C(L+k-1,k)
    nG[g]=(int)n; goff[g]=YTOT; YTOT+=(unsigned)n;
  }
  if(ng>10) die("ng>10");
  for(int b=0;b<NB;b++) yt[b]=malloc(sizeof(unsigned short)*YTOT);
  unsigned char* gmask_all=malloc(YTOT);
  for(int g=0;g<ng;g++){
    int k=gk[g]; gres[g]=malloc((size_t)nG[g]*k);
    int seq[64]; for(int t=0;t<k;t++) seq[t]=0;
    for(int m=0;m<nG[g];m++){
      for(int t=0;t<k;t++) gres[g][(size_t)m*k+t]=(unsigned char)seq[t];
      ll yp[MAXP]; for(int i=0;i<np;i++){ ll s=0; for(int t=0;t<k;t++) s+=(ll)(gd[g]-1)*POW10[i][seq[t]]; yp[i]=s%P[i]; }
      for(int b=0;b<NB;b++){ ll y0=yp[bp[b][0]], y1= bp[b][1]>=0 ? yp[bp[b][1]] : 0; yt[b][goff[g]+m]=(unsigned short)BRES(b,y0,y1); }
      unsigned mk=0; for(int t=0;t<k;t++) if(seq[t]<3) mk|=1u<<seq[t];
      gmask_all[goff[g]+m]=(unsigned char)mk;
      int t=k-1; while(t>=0&&seq[t]==L-1) t--;
      if(t>=0){ seq[t]++; for(int u=t+1;u<k;u++) seq[u]=seq[t]; }
      else if(m!=nG[g]-1) die("multiset count mismatch");
    }
  }
  int inner=0; for(int g=1;g<ng;g++) if(nG[g]>nG[inner]) inner=g;
  ull outer_n=NUN; for(int g=0;g<ng;g++) if(g!=inner) outer_n*=(ull)nG[g];
  if(outer_n>0xFFFFFFF0ull) die("outer index space exceeds 32 bits");
  unsigned short* rtab=malloc(sizeof(unsigned short)*3*L);
  for(int b=0;b<NB;b++) for(int nu=0;nu<L;nu++){ ll y0=R[bp[b][0]][nu], y1= bp[b][1]>=0 ? R[bp[b][1]][nu] : 0; rtab[b*L+nu]=(unsigned short)BRES(b,y0,y1); }

  // components: trivial (all residues admitted) go to the tail-only lane set
  int cisf[MAXC]; int cpos[MAXC]; unsigned cmask[MAXC]; int fpos=0, tpos=0;
  for(int c=0;c<nc;c++){ int triv=1; for(ll k=0;k<csize[c];k++) if(crep[c][k*3]<0){ triv=0; break; } cisf[c]=!triv; }
  for(int c=0;c<nc;c++){ int w=0; while(((ll)1<<w) < csize[c]) w++; if(w<1) w=1;
    if(cisf[c]){ cpos[c]=fpos; fpos+=w; } else { cpos[c]=tpos; tpos+=w; } cmask[c]=(w>=32)?0xFFFFFFFFu:((1u<<w)-1u); }
  if(fpos>31) die("filter lanes exceed 31 bits");
  if(tpos>32) die("tail lanes exceed 32 bits");
  unsigned bmoff[MAXC]; unsigned bmwords=0;
  for(int c=0;c<nc;c++){ bmoff[c]=bmwords; if(cisf[c]) bmwords+=(unsigned)((csize[c]+31)/32); }
  if(bmwords==0) bmwords=1;
  unsigned* bm=calloc(bmwords,4);
  for(int c=0;c<nc;c++) if(cisf[c]) for(ll k=0;k<csize[c];k++) if(crep[c][k*3]>=0) bm[bmoff[c]+k/32]|=1u<<(k%32);
  if(plant==1){ for(int c=0;c<nc;c++) if(cisf[c]){ bm[bmoff[c]]^=1u; break; } }

  unsigned foff[3]={0,0,0}, toff[3]={0,0,0}; unsigned FT=0;
  for(int b=0;b<NB;b++){ foff[b]=FT; toff[b]=FT; FT+=(unsigned)MB[b]; }
  unsigned* filt=calloc(FT,4); unsigned* taill=calloc(FT,4);
  for(int b=0;b<NB;b++) for(ll r=0;r<MB[b];r++){
    unsigned fe=0, te=0;
    for(int t=0;t<2;t++){ int i=bp[b][t]; if(i<0) continue; ll y=r%P[i];
      if(y==0){ fe|=0x80000000u; continue; }
      for(int c=0;c<nc;c++) if(CONTRIB[c][i]){ unsigned v=(unsigned)CONTRIB[c][i][LOGT[i][y]];
        if(cisf[c]) fe+=v<<cpos[c]; else te+=v<<cpos[c]; } }
    filt[foff[b]+r]=fe; taill[toff[b]+r]=te; }
  // threadgroup residency
  int tgr[3]={0,0,0}; { int order[3]={0,1,2}; for(int x=0;x<NB;x++) for(int y=x+1;y<NB;y++) if(MB[order[y]]<MB[order[x]]){int t=order[x];order[x]=order[y];order[y]=t;}
    ll used=0; for(int x=0;x<NB;x++){ int b=order[x]; if(used+MB[b]*4<=20000){ tgr[b]=1; used+=MB[b]*4; } } }

  // tail tables
  unsigned rvoff[MAXC]; unsigned rvn=0; for(int c=0;c<nc;c++){ rvoff[c]=rvn; rvn+=(unsigned)(csize[c]*3); }
  long* rvt=calloc(rvn,8);
  unsigned char* rvm=calloc(rvn/3+1,1); unsigned rvmoff[MAXC]; { unsigned o=0; for(int c=0;c<nc;c++){ rvmoff[c]=o; o+=(unsigned)csize[c]; } }
  double bnd[3]={0,0,0};
  for(int c=0;c<nc;c++){ double mx[3]={0,0,0}; for(ll k=0;k<csize[c];k++) if(crep[c][k*3]>=0) for(int j=0;j<3;j++){ long v=(long)ccrt[c]*crep[c][k*3+j]; rvt[rvoff[c]+k*3+j]=v; if(fabs((double)v)>mx[j]) mx[j]=fabs((double)v);
      if(j==0) rvm[rvmoff[c]+k]=(unsigned char)(((v%G)+G)%G); }
    for(int j=0;j<3;j++) bnd[j]+=mx[j]; }
  double kb=(bnd[0]+A)/G+1; double bb1=bnd[1]+kb*fabs((double)U[1]), bb2=bnd[2]+kb*fabs((double)U[2]);
  int use32 = (bnd[0]<2e9 && bb1<2e9 && bb2<2e9 && !getenv("LVL12_GPU_FORCE64"));
  if(timing) fprintf(stderr,"tail bounds v0 %.3g b %.3g c %.3g -> %s\n",bnd[0],bb1,bb2,use32?"int32":"int64");
  if(use32){ int* r32=calloc(rvn,4); for(unsigned i=0;i<rvn;i++) r32[i]=(int)rvt[i]; free(rvt); rvt=(long*)r32; }
  size_t rvbytes=use32?rvn*4:rvn*8;
  if(G*1ll*255>0 && G>255) die("G too large for byte table");
  unsigned p2a[64]; { for(int a=0;a<=A;a++){ ull t=1; for(int i=0;i<a;i++) t=t*2%1000; p2a[a]=(unsigned)t; } }
  unsigned t3[100], t7[100]; { ull a=1,b=1; for(int e=0;e<100;e++){ t3[e]=(unsigned)a; t7[e]=(unsigned)b; a=a*3%1000; b=b*7%1000; } }
  unsigned cntm[10]={0}; for(int i=0;i<q;i++) cntm[digits[i]]++;
  unsigned ngr[10], goffu[10], gdig[10]; for(int g=0;g<ng;g++){ ngr[g]=(unsigned)nG[g]; goffu[g]=goff[g]; gdig[g]=(unsigned)gd[g]; }
  unsigned ucisf[MAXC], ucpos[MAXC], urvoff[MAXC]; for(int c=0;c<nc;c++){ ucisf[c]=cisf[c]; ucpos[c]=cpos[c]; urvoff[c]=rvoff[c]; }

  int TGSZ=getenv("LVL12_GPU_TGSZ")?atoi(getenv("LVL12_GPU_TGSZ")):256; int CH=getenv("LVL12_GPU_CH")?atoi(getenv("LVL12_GPU_CH")):1024; if(nG[inner]<CH) CH=nG[inner];
  int qcap=getenv("LVL12_GPU_QCAP")?atoi(getenv("LVL12_GPU_QCAP")):512; int jb=getenv("LVL12_GPU_JB")?atoi(getenv("LVL12_GPU_JB")):32;
  NSMutableString* defs=[NSMutableString string];
  #define DEF(...) [defs appendFormat:__VA_ARGS__]
  DEF(@"#define NG %d\n#define INNER %d\n#define NB %d\n#define NC %d\n#define L %d\n#define NUN %d\n#define NU_LO %d\n",ng,inner,NB,nc,L,NUN,lo);
  DEF(@"#define TGSZ %d\n#define CH %d\n#define NINNER %d\n#define YTOT %u\n#define OUTER_N %lluu\n",TGSZ,CH,nG[inner],YTOT,outer_n);
  for(int b=0;b<3;b++) DEF(@"#define MB%d %lldu\n#define TGR%d %d\n#define TGS%d %lld\n#define FOFF%d %uu\n#define TOFF%d %uu\n",b,MB[b],b,tgr[b],b,tgr[b]?MB[b]:1,b,foff[b],b,toff[b]);
  DEF(@"#define BMWORDS %u\n#define GG %lld\n#define AMAX %d\n#define U1 %lld\n#define U2 %lld\n#define ATAB %d\n#define RECCAP %d\n",bmwords,G,A,U[1],U[2],A+1,1<<20);
  DEF(@"#define QCAP %d\n#define JB %d\n#define PLANT %d\n#define NYOFF %d\n#define OPENSH %d\n",qcap,jb,plant,plant==2?1:0,plant==3?1:0);
  DEF(@"#define NGR_INIT %@\n#define GOFF_INIT %@\n#define GDIG_INIT %@\n#define CNTM_INIT %@\n",list_u(ngr,ng),list_u(goffu,ng),list_u(gdig,ng),list_u(cntm,10));
  DEF(@"#define CISF_INIT %@\n#define CPOS_INIT %@\n#define RVOFF_INIT %@\n#define LTYPE %s\n",list_u(ucisf,nc),list_u(ucpos,nc),list_u(urvoff,nc),use32?"int":"long");
  { unsigned rm[MAXC]; for(int c=0;c<nc;c++) rm[c]=rvmoff[c]; DEF(@"#define RVMOFF_INIT %@\n",list_u(rm,nc)); }
  { unsigned cm[MAXC], bo[MAXC]; for(int c=0;c<nc;c++){ cm[c]=cmask[c]; bo[c]=bmoff[c]; }
    DEF(@"#define CMASK_INIT %@\n#define BMOFF_INIT %@\n",list_u(cm,nc),list_u(bo,nc)); }
  DEF(@"#define P2A_INIT %@\n#define T3_INIT %@\n#define T7_INIT %@\n",list_u(p2a,A+1),list_u(t3,100),list_u(t7,100));
  if(getenv("LVL12_GPU_DEFS")) [defs appendFormat:@"%s\n",getenv("LVL12_GPU_DEFS")];
  NSString* src=[defs stringByAppendingString:[NSString stringWithUTF8String:SHADER_SRC]];

  id<MTLDevice> dev=MTLCreateSystemDefaultDevice(); if(!dev) die("no Metal device");
  NSError* err=nil; MTLCompileOptions* co=[MTLCompileOptions new];
  id<MTLLibrary> lib=[dev newLibraryWithSource:src options:co error:&err];
  if(!lib){ fprintf(stderr,"shader compile failed: %s\n",[[err localizedDescription] UTF8String]); return 5; }
  id<MTLFunction> fn=[lib newFunctionWithName:@"lvl12k"];
  id<MTLComputePipelineState> pso=[dev newComputePipelineStateWithFunction:fn error:&err];
  if(!pso){ fprintf(stderr,"pipeline failed: %s\n",[[err localizedDescription] UTF8String]); return 5; }
  if((int)pso.maxTotalThreadsPerThreadgroup<TGSZ){ fprintf(stderr,"maxTotalThreads %d < %d\n",(int)pso.maxTotalThreadsPerThreadgroup,TGSZ); return 5; }
  id<MTLCommandQueue> cq=[dev newCommandQueue];
  #define BUF(ptr,len) [dev newBufferWithBytes:(ptr) length:(len) options:MTLResourceStorageModeShared]
  id<MTLBuffer> bY=BUF(yt[0],1); // placeholder replaced below
  unsigned short* ycat=malloc(sizeof(unsigned short)*YTOT*NB);
  for(int b=0;b<NB;b++) memcpy(ycat+(size_t)b*YTOT,yt[b],sizeof(unsigned short)*YTOT);
  bY=BUF(ycat,sizeof(unsigned short)*YTOT*NB);
  id<MTLBuffer> bF=BUF(filt,FT*4), bT=BUF(taill,FT*4), bM=BUF(bm,bmwords*4), bR=BUF(rvt,rvbytes), bRvm=BUF(rvm,rvn/3+1), bG=BUF(gmask_all,YTOT), bRt=BUF(rtab,sizeof(unsigned short)*3*L);
  id<MTLBuffer> bC=[dev newBufferWithLength:64 options:MTLResourceStorageModeShared];
  id<MTLBuffer> bN=[dev newBufferWithLength:64 options:MTLResourceStorageModeShared];
  id<MTLBuffer> bRec=[dev newBufferWithLength:(size_t)(1<<20)*64 options:MTLResourceStorageModeShared];
  memset([bC contents],0,64); memset([bN contents],0,64);
  double t_setup=now_s()-t_start;

  int nchunks=(nG[inner]+CH-1)/CH;
  ull oblocks=(outer_n+TGSZ-1)/TGSZ;
  ull per_row=oblocks*(ull)TGSZ*(ull)CH;
  int rows_per_batch=(int)(1000000000ull/per_row); if(rows_per_batch<1) rows_per_batch=1;
  ull tot[7]={0}; double t_gpu=0, t_wall_k0=now_s();
  for(int c0=0;c0<nchunks;c0+=rows_per_batch){
    int rows=nchunks-c0<rows_per_batch?nchunks-c0:rows_per_batch;
    id<MTLCommandBuffer> cb=[cq commandBuffer]; id<MTLComputeCommandEncoder> en=[cb computeCommandEncoder];
    [en setComputePipelineState:pso];
    unsigned prm[2]={(unsigned)c0,0}; [en setBytes:prm length:8 atIndex:0];
    id<MTLBuffer> bufs[]={bY,bF,bT,bM,bR,bG,bRt,bC,bN,bRec,bRvm};
    for(int i=0;i<11;i++) [en setBuffer:bufs[i] offset:0 atIndex:1+i];
    [en dispatchThreadgroups:MTLSizeMake(oblocks,rows,1) threadsPerThreadgroup:MTLSizeMake(TGSZ,1,1)];
    [en endEncoding]; [cb commit]; [cb waitUntilCompleted];
    if(cb.status!=MTLCommandBufferStatusCompleted){ fprintf(stderr,"command buffer failed: %s\n",[[[cb error] localizedDescription] UTF8String]); return 6; }
    t_gpu+=cb.GPUEndTime-cb.GPUStartTime;
    unsigned* c=[bC contents]; for(int i=0;i<7;i++){ tot[i]+=c[i]; c[i]=0; }
  }
  double t_kernel_wall=now_s()-t_wall_k0;
  unsigned nrec=*(unsigned*)[bN contents];
  if(nrec>(1u<<20)){ fprintf(stderr,"record buffer overflow (%u)\n",nrec); return 7; }
  double t_o0=now_s();
  unsigned* rc=[bRec contents];
  FILE* out=stdout; static char obuf[1<<20]; setvbuf(out,obuf,_IOFBF,sizeof obuf);
  for(unsigned r=0;r<nrec;r++){
    unsigned* x=rc+(size_t)r*16; int a=x[0]&0xFF, nu=(x[0]>>8)&0xFF, ex=(x[0]>>16)&1, op=(x[0]>>17)&1;
    ll b=(ll)(((ull)x[12]<<32)|x[11]), c=(ll)(((ull)x[14]<<32)|x[13]);
    int eps[MAXQ]; int pos=0; for(int g=0;g<ng;g++){ for(int t=0;t<gk[g];t++) eps[pos++]=gres[g][(size_t)x[1+g]*gk[g]+t]; }
    if(ex){ fprintf(out,"EXACT %d %d",a,nu); for(int i=0;i<q;i++) fprintf(out," %d",eps[i]); fprintf(out," %lld %lld %u\n",b,c,x[15]); }
    if(op){ fprintf(out,"OPEN %d %d",a,nu); for(int i=0;i<q;i++) fprintf(out," %d",eps[i]); fprintf(out," %lld %lld\n",b,c); }
  }
  fflush(out);
  double t_out=now_s()-t_o0;
  fprintf(stderr,"patterns %llu zero %llu prefilter-dead %llu (a,pattern) %llu tail-dead %llu open %llu exact %llu\n",tot[0],tot[1],tot[2],tot[3],tot[4],tot[5],tot[6]);
  if(timing) fprintf(stderr,"gpu-timing setup %.4f kernel_gpu %.4f kernel_wall %.4f output %.4f records %u total %.4f patterns/s(kernel_gpu) %.4g patterns/s(total) %.4g\n",
     t_setup,t_gpu,t_kernel_wall,t_out,nrec,now_s()-t_start,(double)tot[0]/t_gpu,(double)tot[0]/(now_s()-t_start));
  return 0;
  }
}
