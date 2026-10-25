#!/bin/zsh
# gate.sh <overlay-dir> <label> [gate args...]
P=/Users/jwross/Documents/cairn/research/intake/persistence
OV=$1; LABEL=$2; shift 2
GATE_PY_OVERLAY=$OV nice -n 10 uv run --no-project --with gmpy2 --with sympy python /private/tmp/persist-pydesc/gatev2x/gatev2.py --lvl12 $P/tier0/lvl12 --lvlN $P/tier0/lvlN --work /private/tmp/persist-gatev2/work-pydesc-$LABEL --out /private/tmp/persist-pydesc/logs/gate_$LABEL "$@" > /private/tmp/persist-pydesc/logs/gate_$LABEL.out 2>&1
echo "gate rc=$?" >> /private/tmp/persist-pydesc/logs/gate_$LABEL.out
