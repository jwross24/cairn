#!/bin/sh
# usage: run_dual.sh <outdir> <A> <digits...>   runs two halves of the nu range
OUT=$1; A=$2; shift 2
Q=$#
cd "$(dirname "$0")"
nice -n 10 ./dual12 "$A" 0 6 "$Q" "$@" > "$OUT/dual_a.out" 2> "$OUT/dual_a.err" &
nice -n 10 ./dual12 "$A" 6 12 "$Q" "$@" > "$OUT/dual_b.out" 2> "$OUT/dual_b.err" &
wait
cat "$OUT/dual_a.out" "$OUT/dual_b.out" > "$OUT/dual.out"
