#!/bin/sh
# coverage-penalty sweep on pinned targets (documented pool, 200 games each)
run() { docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" "$@"; }
run backend python -m app.evaluation --games 200 --seed 42 --modes rule --target-dist popularity --save-targets eval_results/targets-popularity.json --out /tmp/a.json >/dev/null
run backend python -m app.evaluation --games 200 --seed 43 --modes rule --target-dist uniform    --save-targets eval_results/targets-uniform.json    --out /tmp/a.json >/dev/null
for g in 0 0.5 1; do for t in popularity uniform; do
  printf "gamma=%s targets=%s " $g $t
  run -e COVERAGE_GAMMA=$g backend python -m app.evaluation --modes rule --load-targets eval_results/targets-$t.json --out /tmp/b.json | grep "^rule" | python3 -c "import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1]); print(d['games'],'games top1',d['top1_accuracy'],'avgQ',d['avg_questions'],'medQ',d['median_questions'],'unk',d['unknown_answer_rate'])"
done; done
