static double M_rho = 1.0; static ull M_rng = 88172645463325252ULL; static ll M_sampled = 0, M_zero_p[MAXP], M_pfail[MAXP], M_cfail[MAXC], M_lfail[8], M_hist[1<<16], M_pass = 0;
static unsigned char* M_proj[MAXC][MAXP]; static FILE* M_dump = NULL; static ll M_dump_left = 0, M_dump_every = 1, M_dump_ctr = 0, M_pst = 1, M_pof = 0;
static inline ull m_next(void){ M_rng ^= M_rng<<13; M_rng ^= M_rng>>7; M_rng ^= M_rng<<17; return M_rng; }
static void meas_init(void){
  for(int c=0;c<nc;c++) for(int j=0;j<cn[c];j++) M_proj[c][j]=calloc((size_t)cmod[c][j],1);
  for(int c=0;c<nc;c++){
    if(!csparse[c]){ for(ull ix=0; ix<csize[c]; ix++) if(crep[c][ix*2]>=0){ ull t=ix; for(int j=cn[c]-1;j>=0;j--){ ull m=(ull)cmod[c][j]; M_proj[c][j][t%m]=1; t/=m; } } }
    else { for(ull h=0; h<hsz[c]; h++) if(hkeys[c][h]!=~0ULL){ ull t=hkeys[c][h]; for(int j=cn[c]-1;j>=0;j--){ ull m=(ull)cmod[c][j]; M_proj[c][j][t%m]=1; t/=m; } } }
  }
}
static void meas_env(void){
  const char*e=getenv("MEAS_RHO"); if(e) M_rho=atof(e);
  e=getenv("MEAS_SEED"); if(e) M_rng=strtoull(e,0,10)*2654435761ULL+88172645463325252ULL;
  e=getenv("MEAS_DUMPFILE"); if(e) M_dump=fopen(e,"w");
  e=getenv("MEAS_DUMPN"); if(e) M_dump_left=atoll(e);
  e=getenv("MEAS_DUMPEVERY"); if(e) M_dump_every=atoll(e);
  e=getenv("MEAS_PSTRIDE"); if(e) M_pst=atoll(e);
  e=getenv("MEAS_POFF"); if(e) M_pof=atoll(e);
}
static int meas_take_parent(int pidx){ return pidx % M_pst == M_pof; }
static void measure_child(void){
  cnt_children++;
  if(M_rho<1.0){ if((double)(m_next()>>11) * (1.0/9007199254740992.0) >= M_rho) return; }
  M_sampled++;
  ull y[MAXP]; int zero=0;
  for(int i=0;i<np;i++){ ull yy=ycur[i]%P[i]; if(yy==0){ M_zero_p[i]++; zero=1; } y[i]=yy; }
  if(zero){ cnt_zero++; return; }
  ull logs[MAXP]; for(int i=0;i<np;i++) logs[i]=dlog(i,y[i]);
  int pf[MAXP]; for(int i=0;i<np;i++) pf[i]=0;
  unsigned mask=0;
  for(int c=0;c<nc;c++){
    ull idx=0;
    for(int j=0;j<cn[c];j++){ int i=cidx[c][j]; ull m=(ull)cmod[c][j]; ull v=(ull)(((ll)(logs[i]%m)+(ll)m-bm[c][j])%(ll)m); idx=idx*m+v; if(!M_proj[c][j][v]) pf[i]=1; }
    int ok; if(!csparse[c]) ok = crep[c][idx*2]>=0; else ok = hfind(c,idx)!=NULL;
    if(!ok){ mask|=1u<<c; M_cfail[c]++; }
  }
  for(int j=0;j<nlin;j++){ int i=lidx[j]; ull m=(ull)lmod[j]; ll key=(ll)((((ll)(logs[i]%m)+(ll)m-bl[j])%(ll)m)); ll x1,x2; ll g=egcd(lg1[j],lg2[j],&x1,&x2); if(g<0){g=-g;} ll d=g; ll mq=lmod[j]; { ll a=d,b=mq; while(b){ll t=a%b;a=b;b=t;} d=a; } if(key%d){ mask|=1u<<(nc+j); M_lfail[j]++; pf[i]=1; } }
  for(int i=0;i<np;i++) if(pf[i]) M_pfail[i]++;
  M_hist[mask]++;
  if(M_dump && M_dump_left>0 && (++M_dump_ctr % M_dump_every)==0){ M_dump_left--; fprintf(M_dump,"D %d %d",pidx_cur,nu_cur); for(int i=0;i<q;i++) fprintf(M_dump," %d",cureps[i]); for(int i=0;i<np;i++) fprintf(M_dump," %llu",y[i]); fprintf(M_dump," %u\n",mask); }
  if(mask==0){ M_pass++; process_rest(y); }
}
static void meas_report(void){
  if(M_dump) fclose(M_dump);
  fprintf(stderr,"MEAS {\"children\":%lld,\"sampled\":%lld,\"rho\":%.17g,\"nc\":%d,\"nlin\":%d,\"np\":%d,\"zero_p\":[",cnt_children,M_sampled,M_rho,nc,nlin,np);
  for(int i=0;i<np;i++) fprintf(stderr,"%s%lld",i?",":"",M_zero_p[i]);
  fprintf(stderr,"],\"pfail\":["); for(int i=0;i<np;i++) fprintf(stderr,"%s%lld",i?",":"",M_pfail[i]);
  fprintf(stderr,"],\"cfail\":["); for(int c=0;c<nc;c++) fprintf(stderr,"%s%lld",c?",":"",M_cfail[c]);
  fprintf(stderr,"],\"lfail\":["); for(int j=0;j<nlin;j++) fprintf(stderr,"%s%lld",j?",":"",M_lfail[j]);
  fprintf(stderr,"],\"pass\":%lld,\"tail_dead\":%lld,\"open\":%lld,\"exact\":%lld,\"hist\":{",M_pass,cnt_tail_dead,cnt_open,cnt_exact);
  int first=1; for(int m=0;m<(1<<((nc+nlin)<16?(nc+nlin):16));m++) if(M_hist[m]){ fprintf(stderr,"%s\"%d\":%lld",first?"":",",m,M_hist[m]); first=0; }
  fprintf(stderr,"}}\n");
}
