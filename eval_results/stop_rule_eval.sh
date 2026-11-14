#!/bin/sh
# Stop rule: how many questions can be saved by guessing earlier, at what accuracy?  Calibrated answer model, pinned targets, rule-based.
cd "$(dirname "$0")/.." || exit 1
row() { python3 -c "
import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1])
print(f\"top1 {d['top1_accuracy']:.1%} | <=3 guesses {d['found_within_3_guesses']:.1%} | avg Q to 1st guess {d['avg_questions']} | incl. retries {d['avg_total_questions_with_retries']}\")"; }
for om in 0 0.2; do for fl in 0 0.02 0.05 0.10; do
  printf "omission=%-4s IG_FLOOR=%-5s " $om $fl
  docker compose run --rm --no-deps -T -e IG_FLOOR=$fl -v "$PWD/eval_results:/srv/backend/eval_results" backend timeout 600 python -m app.evaluation --modes adaptive \
    --load-targets eval_results/targets-popularity.json --games 200 --omission $om --out eval_results/stop_o${om}_f${fl}.json | grep "^adaptive " | row
done; done
echo "### DONE"
