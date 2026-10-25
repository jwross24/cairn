"""rvm.py <srcdir> <s> <ncores> : run_vertex_c in-process with timing; prints one JSON line"""
import sys, os, time, json, runpy, resource, io, contextlib
src, s, nc = sys.argv[1], sys.argv[2], sys.argv[3]
known = open(f'/private/tmp/persist-pydesc/known{s}.txt').read().strip()
os.chdir(src); sys.path.insert(0, src)
sys.argv = ['run_vertex_c.py', s, known, nc]
l0 = os.getloadavg()[0]; t0 = time.perf_counter(); c0 = time.process_time(); r0 = resource.getrusage(resource.RUSAGE_CHILDREN)
with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    runpy.run_path('run_vertex_c.py', run_name='__main__')
wall = time.perf_counter() - t0; r1 = resource.getrusage(resource.RUSAGE_CHILDREN)
print(json.dumps(dict(src=os.path.basename(src), wall=round(wall, 3), self_cpu=round(time.process_time() - c0, 3),
                      child_cpu=round((r1.ru_utime + r1.ru_stime) - (r0.ru_utime + r0.ru_stime), 3), load0=round(l0, 2), load1=round(os.getloadavg()[0], 2), maxrss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20, 1))))
