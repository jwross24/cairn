#!/bin/sh
cd "$(dirname "$0")"
export PYTHONDONTWRITEBYTECODE=1
until python3 gate.py; do sleep 60; done
echo "gate open $(date)" >> logs/post_driver.log
nice -n 10 cc -O2 -o dual12 dual12.c >> logs/post_driver.log 2>&1
nice -n 10 cc -O2 -o lvlJ lvlJ.c -lm >> logs/post_driver.log 2>&1
echo "dual suite $(date)" >> logs/post_driver.log
nice -n 10 python3 run_dual_suite.py > logs/dual_suite.jsonl 2>> logs/post_driver.log
echo "join suite 1 $(date)" >> logs/post_driver.log
nice -n 10 python3 run_join_suite.py >> logs/post_driver.log 2>&1
echo "h12d $(date)" >> logs/post_driver.log
./run_h12d.sh >> logs/post_driver.log 2>&1
echo "join suite 2 $(date)" >> logs/post_driver.log
nice -n 10 python3 run_join_suite.py >> logs/post_driver.log 2>&1
echo "done $(date)" >> logs/post_driver.log
