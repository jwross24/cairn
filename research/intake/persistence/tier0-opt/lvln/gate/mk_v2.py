import os
s=open('/private/tmp/persist-lvln/v1/lvlN.c').read()
a=s.index("static void process_child(void){")
b=s.index("// enumerate children")
new=r'''static int eager_verify=0;
static int cfac[MAXC][MAXP];            // factor index of (component, slot) in its prime, -1 for a table prime
static int lfac[8];                      // same for the linear components
static int corder[MAXC], ncorder;       // component evaluation order: table-only first
static ll bm[MAXC][MAXP]; static ll bl[8];   // parent-dependent offsets reduced mod the component modulus
static void lazy_init(void){
  const char* e=getenv("LVLN_EAGER_VERIFY"); eager_verify=(e&&*e&&*e!='0');
  for(int c=0;c<nc;c++) for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; cfac[c][j]=-1; if(LOGT[i]) continue;
    for(int f=0;f<nf[i];f++) if(phf[i][f].qe==(ull)cmod[c][j]) cfac[c][j]=f;
    if(cfac[c][j]<0){ fprintf(stderr,"component modulus %lld is not a prime-power factor of p-1 (p=%llu)\n",cmod[c][j],P[i]); exit(7);} }
  for(int j=0;j<nlin;j++){ int i=lidx[j]; lfac[j]=-1; if(LOGT[i]) continue;
    for(int f=0;f<nf[i];f++) if(phf[i][f].qe==(ull)lmod[j]) lfac[j]=f;
    if(lfac[j]<0){ fprintf(stderr,"linear modulus %lld is not a prime-power factor of p-1 (p=%llu)\n",lmod[j],P[i]); exit(7);} }
  int cost[MAXC]; for(int c=0;c<nc;c++){ cost[c]=0; for(int j=0;j<cn[c];j++) if(cfac[c][j]>=0) cost[c]++; }
  ncorder=0; for(int k=0;k<=MAXP;k++) for(int c=0;c<nc;c++) if(cost[c]==k) corder[ncorder++]=c;
}
static void parent_init(void){
  for(int i=0;i<np;i++){ i128 m=(i128)(P[i]-1);
    i128 X=(i128)a_cur*L2[i] + mod128(vb_cur,m)*L3[i] + mod128(vc_cur,m)*L7[i];
    for(int c=0;c<nc;c++) for(int j=0;j<cn[c];j++) if(cidx[c][j]==i) bm[c][j]=(ll)mod128(X,(i128)cmod[c][j]);
    for(int j=0;j<nlin;j++) if(lidx[j]==i) bl[j]=(ll)mod128(X,(i128)lmod[j]); }
}

static void process_child(void){
  cnt_children++;
  ull y[MAXP], logs[MAXP];
  for(int i=0;i<np;i++){ i128 yy=R[i][nu_cur]; for(int j=0;j<q;j++) yy+=(i128)(digits[j]-1)*POW10[i][cureps[j]]; yy%= (i128)P[i]; if(yy==0){cnt_zero++; return;} y[i]=(ull)yy; }
  if(eager_verify) for(int i=0;i<np;i++) logs[i]=dlog(i,y[i]);
  else for(int i=0;i<np;i++) if(LOGT[i]) logs[i]=(ull)LOGT[i][y[i]];
  int* rps[MAXC];
  for(int k=0;k<ncorder;k++){ int c=corder[k]; ull idx=0;
    for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; ull m=(ull)cmod[c][j]; ull lg;
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

'''
s=s[:a]+new+s[b:]
s=s.replace("    pidx_cur=pidx; a_cur=a;\n","    pidx_cur=pidx; a_cur=a; parent_init();\n")
s=s.replace("  read_cfg(argv[1]);\n","  read_cfg(argv[1]); lazy_init();\n")
os.makedirs('/private/tmp/persist-lvln/v2',exist_ok=True)
open('/private/tmp/persist-lvln/v2/lvlN.c','w').write(s)
