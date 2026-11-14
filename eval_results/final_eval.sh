#!/bin/sh
# Every number in README / docs/FINAL_REPORT.md comes from this script (run from the repo root, ~10 min).
run() { docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" "$@"; }
row() { python3 -c "
import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1])
print(f\"{d['games']} games | top1 {d['top1_accuracy']:.1%} | found<=3 guesses {d['found_within_3_guesses']:.1%} | avgQ to 1st guess {d['avg_questions']} | median {d['median_questions']} | avgQ incl. retries {d['avg_total_questions_with_retries']} | unknown-ans {d['unknown_answer_rate']:.1%} | validity {d['question_validity_rate']:.0%} | latency {d['latency_ms_mean']}/{d['latency_ms_p95']} ms | identifiable {d['identifiable_fraction']}\")"; }
echo "### 0. pin targets from the shipped graph"
docker compose run --rm ingestion > /dev/null 2>&1
run backend python -m app.evaluation --games 200 --seed 42 --modes rule --target-dist popularity --save-targets eval_results/targets-popularity.json --out /tmp/a.json > /dev/null
run backend python -m app.evaluation --games 200 --seed 43 --modes rule --target-dist uniform    --save-targets eval_results/targets-uniform.json    --out /tmp/a.json > /dev/null
echo "### 1. ablation: ontology patches {off,on} x unknown handling {legacy closed-world, strict open-world} (rule-based, popularity prior)"
for patches in 0 1; do
  docker compose run --rm -e APPLY_PATCHES=$patches ingestion > /dev/null 2>&1 || echo "ingestion failed for patches=$patches"
  for strict in 0 1; do for t in popularity uniform; do
    printf "patches=%s strict_unknown=%s targets=%-10s " $patches $strict $t
    run -e APPLY_PATCHES=$patches -e STRICT_UNKNOWN=$strict backend python -m app.evaluation --modes rule --load-targets eval_results/targets-$t.json --games 200 --out eval_results/ablation_p${patches}_s${strict}_$t.json | grep "^rule" | row
  done; done
done
docker compose run --rm ingestion > /dev/null 2>&1 && echo "(shipped graph restored: patches on)"
echo "### 2. shipped configuration vs baselines"
for t in popularity uniform; do
  printf "random      targets=%-10s " $t; run backend python -m app.evaluation --modes random --load-targets eval_results/targets-$t.json --games 200 --out eval_results/random_$t.json | grep "^random" | row
done
echo "### 3. uniform prior (spec MVP) vs popularity prior, shipped graph"
for t in popularity uniform; do
  printf "uniform-prior targets=%-10s " $t; run -e PRIOR=uniform backend python -m app.evaluation --modes rule --load-targets eval_results/targets-$t.json --games 200 --out eval_results/prior_uniform_$t.json | grep "^rule" | row
done
echo "### 4. AI-assisted vs rule-based on the SAME 12 popular targets"
run backend python -m app.evaluation --modes rule,ai --load-targets eval_results/targets-popularity.json --games 12 --ai-games 12 --out eval_results/ai.json | grep -E "^(rule|ai) " | while read -r name rest; do printf "%-5s" $name; echo "$name $rest" | row; done
echo "### DONE"
