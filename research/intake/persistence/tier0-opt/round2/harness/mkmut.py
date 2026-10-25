import subprocess, sys
src=open('work/L9.c').read()
M=[
("m01_skip_9901_lookup","SIMD filter drops the p=9901 lookup","    a0=vaddq_u16(a0,vld1q_u16(p4)); a1=vaddq_u16(a1,vld1q_u16(p4+4));\n","    ;\n"),
("m02_skip_37_lookup","SIMD filter drops the p=37 lookup (zero flag only)","    a0=vaddq_u16(a0,vld1q_u16(p2)); a1=vaddq_u16(a1,vld1q_u16(p2+4));\n","    ;\n"),
("m03_lane_offset","upper-half lane load offset 4->3","vld1q_u16(p0+4)","vld1q_u16(p0+3)"),
("m04_movemask_shift","upper-half movemask shift 4->3","movemask8(ok1)<<4","movemask8(ok1)<<3"),
("m05_valid_mask","valid mask admits residue start-1","unsigned valid=0xFFFu & ~((1u<<start)-1u);","unsigned valid=0xFFFu & ~((1u<<(start?start-1:0))-1u);"),
("m06_zero_count_unmasked","zero count ignores valid mask","int zc=__builtin_popcount(zm&valid);","int zc=__builtin_popcount(zm);"),
("m07_c_field_accept","Z5 field accepts 6 instead of 5","VC5=vdupq_n_u16(5)","VC5=vdupq_n_u16(6)"),
("m08_no_final_flush","final queue flush removed","if(q8) flushq(nu); }","}"),
("m09_queue_advance","queue skips single-survivor batches","nq+=(m!=0);","nq+=(m>1);"),
("m10_amask_leaf","leaf residue 0 omitted from allowed-digit mask","unsigned am0=rc->am[0]|(r==0?bit:0)","unsigned am0=rc->am[0]"),
("m11_tmax","a0 trip count short by one","tmax=A/12+1;","tmax=A/12;"),
("m12_feas_count","digit-count feasibility off by one","if(cn_[d]>cntmg[d]) ok=0;","if(cn_[d]>cntmg[d]+1) ok=0;"),
("m13_cr_v2_mod","v2 residue mod 99","ll x2=((ll)ccrt[c]*crep[c][k*3+2])%100; if(x2<0) x2+=100;","ll x2=((ll)ccrt[c]*crep[c][k*3+2])%99; if(x2<0) x2+=99;"),
("m14_pt16_index","3^b table index shifted","PT16[a][bm]=(unsigned short)((P2A[a]*T3K[3][bm])%1000);","PT16[a][bm]=(unsigned short)((P2A[a]*T3K[3][(bm+1)%100])%1000);"),
("m15_alive_eps","alive replay writes wrong last residue","eps[q-1]=r;","eps[q-1]=0;"),
("m16_kk","k mod 100 off by one","unsigned kk=(a0+1200u-v0m)/12u;\n    unsigned bm=(v1m+kk*(unsigned)U1m)%100u, cm=(v2m+kk*(unsigned)U2m)%100u;\n    unsigned Y=((unsigned)PT16[valid?a0:0][bm]*(unsigned)t7[cm])%1000u;\n    unsigned al=FEAS[Y] & (am0","unsigned kk=(a0+1200u-v0m+12u)/12u;\n    unsigned bm=(v1m+kk*(unsigned)U1m)%100u, cm=(v2m+kk*(unsigned)U2m)%100u;\n    unsigned Y=((unsigned)PT16[valid?a0:0][bm]*(unsigned)t7[cm])%1000u;\n    unsigned al=FEAS[Y] & (am0"),
("m17_zero_mask","zero-flag bits dropped from the pass mask","  mp|=zmask;\n","  mp|=0;\n"),
("m18_c_test_off","order-5 field test skipped","ok0=vandq_u16(ok0,t0); ok1=vandq_u16(ok1,t1);","ok0=ok0; ok1=ok1;"),
("m19_ent32_decode","component index decode uses 242","q2=q1/243u, q3=q2/3125u;\n  unsigned i0=acc&511u, i1=q1-q2*243u, i2=q2-q3*3125u, i3=q3;\n  unsigned w=CR32[0][i0]+CR32[1][i1]+CR32[2][i2]+CR32[3][i3];\n  unsigned v0m=(w&0x1FFFu)%1200u, v1m=((w>>13)&0x1FFu)%100u, v2m=(w>>22)%100u;\n  unsigned r=v0m%12u;\n  const ull *t7=T7K[3];\n  int ns=0, nd=0, anyal=0;\n  for(int t=0;t<tmax;t++){\n    unsigned a0=r+12u*t; int valid=a0<=(unsigned)A;\n    unsigned kk=(a0+1200u-v0m+12u)/12u" if False else "static inline __attribute__((always_inline)) int finish5m(unsigned acc, unsigned am0, unsigned am1, unsigned am2){\n  unsigned q1=acc>>9, q2=q1/243u","static inline __attribute__((always_inline)) int finish5m(unsigned acc, unsigned am0, unsigned am1, unsigned am2){\n  unsigned q1=acc>>9, q2=q1/242u"),
("m20_survivor_branch_cond","tail-dead counted for invalid a0","ns+=valid; nd+=valid&~al; anyal|=valid&al;\n  }\n  if(anyal) return 1;","ns+=valid; nd+=~al&1u; anyal|=valid&al;\n  }\n  if(anyal) return 1;"),
]
import json
out=[]
for name,desc,old,new in M:
    if src.count(old)<1: print("MISSING",name); continue
    s=src.replace(old,new,1 if name not in('m02_skip_37_lookup',) else 1)
    assert s!=src
    open(f'mut/{name}.c','w').write(s)
    r=subprocess.run(['cc','-O3','-march=native','-w','-o',f'mut/{name}',f'mut/{name}.c'],capture_output=True,text=True)
    print(name,'built' if r.returncode==0 else r.stderr[:200])
    out.append(dict(name=name,desc=desc))
json.dump(out,open('mut/list.json','w'),indent=1)
