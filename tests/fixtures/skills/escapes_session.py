import subprocess
import sys

BURN = """
import sys, time
start = time.process_time()
x = 0
while time.process_time() - start < 1.0:
    x += 1
open(sys.argv[1], "w").write(str(time.process_time() - start))
"""


def main():
    sys.stdin.read()
    scratch = sys.argv[1]
    subprocess.Popen([sys.executable, "-c", BURN, scratch + "/burned"], start_new_session=True)
    sys.stdout.write('{"status":"OK"}\n')
    return 0


if __name__ == "__main__":
    sys.exit(main())
