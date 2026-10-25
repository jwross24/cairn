import sys,json
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from scenarios import *
SC={
 'S1 ref engines, sweep driver':dict(t12=46e-9,driver='sweep'),
 'S2 opt lvl12 (10 ns), sweep driver':dict(t12=10e-9,driver='sweep'),
 'S3 opt lvl12, pool driver':dict(t12=10e-9),
 'S4 lvl12 8 ns, pool':dict(t12=8e-9),
 'S5 lvl12 3 ns, pool':dict(t12=3e-9),
 'S6 GPU 1e10/s, pool':dict(gpu=1e10),
 'S7 GPU + lvlN x10':dict(gpu=1e10,lvlN_x=10),
 'S8 GPU + lvlN x100':dict(gpu=1e10,lvlN_x=100),
 'S9 GPU + lvlN x100 + C Lemma C/sandwich x100':dict(gpu=1e10,lvlN_x=100,post_x=100),
 'S10 S9, lvlN x1000':dict(gpu=1e10,lvlN_x=1000,post_x=100),
}
res={}
for mode,q14 in (('registered',1.0),('fitted',1.0),('registered',8.4),('fitted',8.4)):
    rows=eq_rows(mode)
    for name,sc0 in SC.items():
        sc=dict(sc0,q14_x=q14)
        tab=stage_table(rows,sc)
        keys=('lvl12','lvl24','lvl48','lvl96','py','lemmaC','sandwich')
        stg={k:sum(st[k] for _,_,_,st in tab) for k in keys}; stg['gpu']=sum(st.get('gpu',0) for _,_,_,st in tab)
        row=dict(stage_Pcore_s=stg)
        if sc.get('driver')=='sweep':
            a,b=sweep_driver(tab,sc); row['makespan_h']=(a+b)/3600; row['lift_phase_h']=a/3600
        else:
            fin,busy,tot,g=pool_sim(tab,sc); row['makespan_h']=fin/3600; row['capacity_bound_h']=tot/CAP/3600; row['gpu_h']=g/3600
        row['stage_wall_h']={k:(v/CAP/3600 if k!='gpu' else v/3600) for k,v in stg.items()}
        row['bottleneck']=max(row['stage_wall_h'],key=row['stage_wall_h'].get)
        res[mode+('|anchored_x8.4' if q14!=1.0 else '')+' | '+name]=row
        print(mode[:3],'anch' if q14!=1.0 else 'fit ',name,'| makespan %.3g h'%row['makespan_h'],'| bottleneck',row['bottleneck'],{k:'%.2g'%v for k,v in row['stage_wall_h'].items()},flush=True)
json.dump(res,open('scenario_results.json','w'),indent=1)
