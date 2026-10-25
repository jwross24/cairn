import sys,csv,json,collections
import os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import scenarios as S
from costmodel import *
rows=[]
byv=collections.defaultdict(lambda: collections.Counter())
meta={}
for mode in ('registered','fitted'):
    for v in S.V:
        for e in v['eqs']:
            w=eq_work(tuple(e['M']),e['npat'],open_mode=mode)
            st=eq_stage_seconds(w)
            c=byv[(v['s'],mode)]
            for k,x in st.items(): c[k]+=x
            for k in ('npat','sv12','n24','n48','n96','open'): c[k]+=w[k]
            c['eqs']+=1; c['sandpat']+=w['open']*0.06
            c['qmax']=max(c['qmax'],len(e['M']))
            if mode=='registered' : meta[v['s']]=dict(tree=v['tree'],kmax=v['kmax'],done=v['vertex_done'])
hdr=['s','tree','kmax','vertex_done_at_build','eqs','patterns','pred_sv12','pred_children24','pred_children48','pred_children96','open96_registered','open96_fitted','sandwich_patterns_registered','sandwich_depth_kmax',
 'Pcore_h_lvl12_ref46ns','Pcore_h_lvl12_opt10ns','Pcore_h_lvl12_8ns','Pcore_h_lvl12_3ns','GPU_h_lvl12_1e10','Pcore_h_lift24_ref','Pcore_h_lift48_ref','Pcore_h_lift96_ref','Pcore_h_python_descent_setup','Pcore_h_lemmaC_py_reg','Pcore_h_sandwich_py_reg','Pcore_h_lemmaC_py_fit','Pcore_h_sandwich_py_fit','Pcore_h_total_opt_py_reg']
with open('per_vertex_model.csv','w',newline='') as f:
    wr=csv.writer(f); wr.writerow(hdr)
    for v in S.V:
        r=byv[(v['s'],'registered')]; ft=byv[(v['s'],'fitted')]; h=3600
        wr.writerow([v['s'],v['tree'],v['kmax'],v['vertex_done'],int(r['eqs']),'%.4g'%r['npat'],'%.4g'%r['sv12'],'%.4g'%r['n24'],'%.4g'%r['n48'],'%.4g'%r['n96'],'%.4g'%r['open'],'%.4g'%ft['open'],'%.4g'%r['sandpat'],sand_depth(v['kmax']),
          '%.4g'%(r['lvl12']/h),'%.4g'%(r['npat']*10e-9/h),'%.4g'%(r['npat']*8e-9/h),'%.4g'%(r['npat']*3e-9/h),'%.4g'%(r['npat']/1e10/h),'%.4g'%(r['lvl24']/h),'%.4g'%(r['lvl48']/h),'%.4g'%(r['lvl96']/h),'%.4g'%(r['py']/h),
          '%.4g'%(r['lemmaC']/h),'%.4g'%(r['sandwich']/h),'%.4g'%(ft['lemmaC']/h),'%.4g'%(ft['sandwich']/h),
          '%.4g'%((r['npat']*10e-9+r['lvl24']+r['lvl48']+r['lvl96']+r['py']+r['lemmaC']+r['sandwich'])/h)])
print('ok')
