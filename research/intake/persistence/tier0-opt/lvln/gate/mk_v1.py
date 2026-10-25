import os
s=open('/private/tmp/persist-lvln/base/lvlN.c').read()
a=s.index("// ---- Pohlig")
b=s.index("static void read_cfg")
new=r'''// ---- Pohlig–Hellman: per-prime-factor subgroup tables (direct lookup) with a BSGS/digit fallback for large q^e
typedef struct { ull q; int e; ull qe; ull cof; ull crtc; ull gamma; ull m; ull *keys; ull *vals; ull hsize; ull ginv_m; ull gqinv; int direct; ull *tk; unsigned *tv; ull tmask; ull gj; } PHF;
#define TBL_MAX (1ULL<<22)
static PHF phf[MAXP][MAXF];
static void hins(PHF* f, ull key, ull val){ ull h=(key*11400714819323198485ULL)%f->hsize; while(f->keys[h]!=~0ULL) h=(h+1)%f->hsize; f->keys[h]=key; f->vals[h]=val; }
static int hget(PHF* f, ull key, ull* val){ ull h=(key*11400714819323198485ULL)%f->hsize; while(f->keys[h]!=~0ULL){ if(f->keys[h]==key){*val=f->vals[h]; return 1;} h=(h+1)%f->hsize; } return 0; }
static inline ull thash(ull key, ull mask){ return ((key*11400714819323198485ULL)>>20)&mask; }
static void ph_init(int i){
  ull p=P[i], n=p-1;
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
  ull hq=powmod(h, f->cof, p);
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

'''
s=s[:a]+new+s[b:]
os.makedirs('/private/tmp/persist-lvln/v1',exist_ok=True)
open('/private/tmp/persist-lvln/v1/lvlN.c','w').write(s)
