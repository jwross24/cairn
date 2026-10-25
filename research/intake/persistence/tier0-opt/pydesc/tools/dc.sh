#!/bin/zsh
cd "$1" || exit 9
S=$(date +%s)
nice -n 10 uv run --no-project --with gmpy2 --with sympy python deepcut.py runall_final.jsonl --depth 1 > "$2" 2>&1
echo "rc=$? secs=$(( $(date +%s) - S ))" >> "$2"
