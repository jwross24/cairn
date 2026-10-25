"""pycov_driver.py <srcdir> <mode> : exercise the replaced modules under coverage"""
import sys, os, runpy, io, contextlib
src, mode = sys.argv[1], sys.argv[2]
os.chdir(src); sys.path.insert(0, src)
def vertex(s, nc='2'):
    known = open(f'/private/tmp/persist-pydesc/known{s}.txt').read().strip()
    sys.argv = ['run_vertex_c.py', s, known, nc]
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        runpy.run_path('run_vertex_c.py', run_name='__main__')
if mode == 'eager':
    for s in ('72', '224', '14336'): vertex(s)
elif mode == 'noclift':
    for s in ('72', '224'): vertex(s, '1')
elif mode == 'deferred':
    for s in ('72', '224'): vertex(s, '1')
elif mode == 'trees':
    sys.argv = ['run_trees_c_v2.py', '/private/tmp/persist-pydesc/mini14336.zf', f'/private/tmp/persist-pydesc/gold/pycov_trees_{os.getpid()}.jsonl', '2', '1e30']
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        runpy.run_path('run_trees_c_v2.py', run_name='__main__')
elif mode == 'solve':
    import tier0v2
    for s in (6, 8, 12, 18, 72):
        for M in tier0v2.multisets(s):
            tier0v2.solve_equation(s, M, [], verbose=False)
