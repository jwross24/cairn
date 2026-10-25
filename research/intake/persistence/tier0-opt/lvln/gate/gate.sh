#!/bin/bash
# usage: gate.sh <tag> <lvlN binary> <lvlN.c>
TAG=$1; BIN=$2; SRC=$3
R=/private/tmp/persist-lvln
G=$R/gate/$TAG
mkdir -p $G $R/pycache
rsync -a $R/base/ $G/
cp $BIN $G/lvlN; cp $SRC $G/lvlN.c
cd $G
echo "binary sha256 $(shasum -a 256 lvlN | cut -d' ' -f1)" > $R/logs/gate_$TAG.log
PY="uv run --no-project --with gmpy2 --with sympy python"
for args in "72 98,189,294,1161216" "10800 11519532122112" "224 784,2744,41472,71442,122472"; do
  nice -n 10 $PY $R/difftest2.py $args $R/pycache >> $R/logs/gate_$TAG.log 2>&1
done
nice -n 10 $PY $R/drive.py $G 14336 > $R/logs/g14336_$TAG.log 2>&1
until grep -q "^TOTAL" $R/logs/g14336_ref.log; do sleep 10; done
python3 $R/compare.py $R/logs/g14336_ref.log $R/logs/g14336_$TAG.log >> $R/logs/gate_$TAG.log 2>&1
echo "GATE DONE $TAG" >> $R/logs/gate_$TAG.log
