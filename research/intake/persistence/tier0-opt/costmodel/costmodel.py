import sys,json,math,collections
import os
HERE=os.path.dirname(os.path.abspath(__file__))
RATES=json.load(open(os.path.join(HERE,'rates.json')))['fits']
POST=json.load(open(os.path.join(HERE,'post_fit.json')))

# measured unit costs, P-core, host load ~10 (see ab_result.json, abN_result.json, stage_runs.jsonl)
UNIT=dict(t12_ref=46e-9, t12_opt=10e-9,
          tN24=6.1e-6, tN48=24.5e-6, tN96=78e-6,
          t_desc=25e-6,                 # Python descent per level-12 survivor
          py_fixed12=0.07, py_fixed48=0.4, py_fixed96=0.7,   # Python per-equation setup by deepest level reached
          dc_case=POST['deepcut']['s_per_case'])
E_SPEED=0.6   # E-core speed relative to P-core (taskpolicy -b A/B: 0.57-0.65 ref, 0.48-0.57 opt)

def rate(name,q,cap=None):
    f=RATES[name]; v=math.exp(f['ln_at_q']+f['slope']*(q-f['intercept_at_q']))
    return min(v,cap) if cap else v

def sand_depth(k): return max(2,math.ceil((11.5+13.9*k-24)/48))
def dc_cases(k):
    reps=POST['deepcut']['reps_per_pat']
    return reps*POST['deepcut']['cases_rep_at_k6']*math.exp(POST['deepcut']['cases_rep_ln_slope']*(k-6))
def sand_secs(k):
    a,b,c=POST['sandwich_lnsec']; return math.exp(a+b*k+c*sand_depth(k))

def eq_work(M,npat,open_mode='registered',actual=None):
    q=len(M)
    if actual:
        sv12,n24,n48,n96,opn=actual
    else:
        sv12=npat*rate('sv12',q,0.2); n24=sv12*rate('n24',q)
        sv24=n24*rate('s24',q); n48=sv24*rate('n48',q); sv48=n48*rate('s48',q); n96=sv48*rate('n96',q)
        opn=npat*(1e-8 if open_mode=='registered' else rate('open',q))
    return dict(q=q,npat=npat,sv12=sv12,n24=n24,n48=n48,n96=n96,open=opn)

def eq_stage_seconds(w,u=UNIT,t12=None):
    t12=t12 if t12 is not None else u['t12_ref']
    k=w['q']
    py=w['sv12']*u['t_desc']+u['py_fixed12']+(u['py_fixed48'] if w['n48']>0.5 or w['n24']>50 else 0)+(u['py_fixed96'] if w['n96']>0.5 else 0)
    surv_sand=w['open']*0.06
    return dict(lvl12=w['npat']*t12, lvl24=w['n24']*u['tN24'], lvl48=w['n48']*u['tN48'], lvl96=w['n96']*u['tN96'], py=py,
                lemmaC=w['open']*dc_cases(k)*u['dc_case'], sandwich=surv_sand*sand_secs(k))
