import json,sys
sys.path.insert(0,'/Users/jwross/Documents/cairn/research/intake/persistence/tier0')
T='/Users/jwross/Documents/cairn/research/intake/persistence/tier0/'
def eqs(files=('trees_mac.jsonl.eqs.jsonl',)):
    out=[]
    for f in files:
        for l in open(T+f):
            try: out.append(json.loads(l))
            except Exception: pass
    return out
