import sys, os, json, time, traceback
pipe, y, sp, Mj = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), json.loads(sys.argv[4])
sys.path.insert(0, pipe)
os.chdir(pipe)
t0 = time.time()
out = dict(y=y, found=False, lost=None, open=None, levels=None, secs=None)
try:
    from run_c import run
    r = run(sp, tuple(Mj), [y], ncores=1)
    out['found'] = y in r['solutions']
    out['open'] = len(r['open'])
    out['levels'] = [(l[0], l[2], l[3]) for l in r['levels']]
except AssertionError as e:
    out['lost'] = 'AssertionError: ' + str(e)[:300]
except BaseException as e:
    out['lost'] = 'error: ' + ''.join(traceback.format_exception_only(type(e), e))[:300]
out['secs'] = round(time.time() - t0, 1)
print('PLANT ' + json.dumps(out))
