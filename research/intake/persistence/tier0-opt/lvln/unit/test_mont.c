#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
typedef unsigned long long ull; typedef unsigned __int128 u128;
#define MAXP 12
static ull P[MAXP];
static ull mulmod(ull a, ull b, ull m){ return (ull)(((u128)a*b)%m); }
static ull powmod(ull b, ull e, ull m){ ull r=1%m; b%=m; while(e){ if(e&1) r=mulmod(r,b,m); b=mulmod(b,b,m); e>>=1;} return r; }
static ull memo_hq; static int memo_i=-1, memo_f=-1;
static ull mn[MAXP], mr2[MAXP], mone[MAXP];
static inline ull redc(u128 T, ull p, ull ninv){ ull m=(ull)T*ninv; ull t=(ull)((T+(u128)m*p)>>64); return t>=p?t-p:t; }
static ull powmod_mont(int i, ull b, ull e){
  ull p=P[i], ni=mn[i]; ull x=redc((u128)b*mr2[i],p,ni), r=mone[i];
  while(e){ if(e&1) r=redc((u128)r*x,p,ni); e>>=1; if(e) x=redc((u128)x*x,p,ni); }
  return redc((u128)r,p,ni);
}
static void mont_init(int i){ ull p=P[i]; ull inv=p; for(int k=0;k<6;k++) inv*=2-p*inv; mn[i]=-inv; ull r1=(ull)((((u128)1)<<64)%p); mone[i]=r1; mr2[i]=(ull)(((u128)r1*r1)%p); }

int main(){ ull ps[]={73,137,99990001ULL,17,5882353ULL,9999999900000001ULL,97,353,449,641,1409,69857,206209,66554101249ULL,75118313082913ULL}; int n=sizeof ps/sizeof *ps; ull s=88172645463325252ULL; long bad=0,tot=0;
 for(int k=0;k<n;k++){ P[0]=ps[k]; mont_init(0); for(int t=0;t<2000000;t++){ s^=s<<13; s^=s>>7; s^=s<<17; ull b=s%ps[k]; s^=s<<13; s^=s>>7; s^=s<<17; ull e=(t&1)?s%ps[k]:(s>>(10+t%50)); if(powmod_mont(0,b,e)!=powmod(b,e,ps[k])){ bad++; } tot++; } }
 printf("mont powmod: %ld mismatches of %ld\n",bad,tot); return bad!=0; }
