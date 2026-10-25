#include <stdio.h>
typedef unsigned long long ull; typedef unsigned __int128 u128;
static ull cnt_ge_p, cnt_calls;
static inline ull redc_ref(u128 T, ull p, ull ninv){ ull m=(ull)T*ninv; ull t=(ull)((T+(u128)m*p)>>64); return t>=p?t-p:t; }
static inline ull redc_mut(u128 T, ull p, ull ninv){ ull m=(ull)T*ninv; ull t=(ull)((T+(u128)m*p)>>64); cnt_calls++; if(t>=p) cnt_ge_p++; return t; }
static ull powmod(ull b, ull e, ull m){ ull r=1%m; b%=m; while(e){ if(e&1) r=(ull)(((u128)r*b)%m); b=(ull)(((u128)b*b)%m); e>>=1;} return r; }
#define PM(NAME,REDC) static ull NAME(ull p, ull ni, ull r2, ull one, ull b, ull e){ ull x=REDC((u128)b*r2,p,ni), r=one; while(e){ if(e&1) r=REDC((u128)r*x,p,ni); e>>=1; if(e) x=REDC((u128)x*x,p,ni); } return REDC((u128)r,p,ni); }
PM(pm_ref,redc_ref) PM(pm_mut,redc_mut)
int main(){ ull ps[]={73,137,99990001ULL,17,5882353ULL,9999999900000001ULL,97,353,449,641,1409,69857,206209,66554101249ULL,75118313082913ULL}; int n=sizeof ps/sizeof *ps;
 ull s=88172645463325252ULL; long bad=0,tot=0;
 for(int k=0;k<n;k++){ ull p=ps[k]; ull inv=p; for(int i=0;i<6;i++) inv*=2-p*inv; ull ni=-inv; ull r1=(ull)((((u128)1)<<64)%p); ull r2=(ull)(((u128)r1*r1)%p);
  for(int t=0;t<2000000;t++){ s^=s<<13; s^=s>>7; s^=s<<17; ull b=1+s%(p-1); s^=s<<13; s^=s>>7; s^=s<<17; ull e=(t&1)?s%p:(s>>(10+t%50));
   ull a=pm_ref(p,ni,r2,r1,b,e), c=pm_mut(p,ni,r2,r1,b,e); if(a!=c||a!=powmod(b,e,p)) bad++; tot++; } }
 printf("pre-subtraction value >= p reached in %llu of %llu redc calls; powmod outputs differing between ref and no-subtraction redc: %ld of %ld\n",cnt_ge_p,cnt_calls,bad,tot); return bad!=0; }
