#!/bin/zsh
# usage: gate.sh <tag> <binary> [a|b|c|all]
# Builds per-tag scratch copies of tier0-opt/ and tier0/ with <binary> installed as lvl12 and runs the gate parts.
R=/private/tmp/persist-lvl12-r2
tag=$1; bin=$2; part=${3:-all}
export PATH=$R/shim:$PATH
G=$R/gates/$tag; L=$R/logs
mkdir -p $G $L
if [ ! -d $G/tier0-opt ]; then
  rsync -a --exclude golden_raw $R/gate/tier0-opt/ $G/tier0-opt/
  rsync -a $R/gate/tier0/ $G/tier0/
  mkdir -p $G/scratch
  for f in check_golden.sh golden_run.sh; do
    sed -i '' -e "s#^PY=.*#PY=$R/shim/python3#" -e "s#^cd /Users.*tier0-opt#cd $G/tier0-opt#" $G/tier0-opt/$f
  done
  sed -i '' -e "s#/private/tmp/persist-opt-scratch#$G/scratch#g" $G/tier0-opt/c_oracle.py $G/tier0-opt/run_c.py
  sed -i '' -e "s#chk_\$tag 4#chk_\$tag ${NC:-4}#" -e "s#eq6.jsonl 4#eq6.jsonl ${NC:-4}#" $G/tier0-opt/check_golden.sh
fi
cp $bin $G/tier0-opt/lvl12; cp $bin $G/tier0/lvl12
chmod +x $G/tier0-opt/lvl12 $G/tier0/lvl12

if [ $part = a -o $part = all ]; then
  cd $G/tier0-opt; rm -rf chk_$tag chk_${tag}_n
  { echo "== gate a: tag=$tag bin=$bin sha=$(shasum -a 256 $bin | cut -c1-16) load=$(uptime | sed 's/.*averages: //')";
    ./check_golden.sh $tag; } > $L/${tag}_a.log 2>&1
  tail -12 $L/${tag}_a.log
fi
if [ $part = b -o $part = all ]; then
  cd $G/tier0
  { echo "== gate b: tag=$tag bin=$bin load=$(uptime | sed 's/.*averages: //')";
    nice -n 10 python3 difftest.py 72 98,189,294,1161216;
    nice -n 10 python3 difftest.py 10800 11519532122112; } > $L/${tag}_b.log 2>&1
  tail -5 $L/${tag}_b.log
fi
if [ $part = c -o $part = all ]; then
  cd $G/tier0
  nice -n 10 python3 $R/vertex_hash.py $G/tier0/lvl12 14336 $L/${tag}_c.json 4 > $L/${tag}_c.log 2>&1
  tail -3 $L/${tag}_c.log
fi
