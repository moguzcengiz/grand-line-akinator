#!/bin/sh
# Old closed-world answer model vs the calibrated one, on the SAME pinned targets, as the graph gets more incomplete.
#   omission = share of "not listed" graph FALSEs that are actually true (e.g. Shanks has no recorded Captain occupation);
#   noise    = share of definite answers softened to probably / probably not (an unsure player).
cd "$(dirname "$0")/.." || exit 1
row() { python3 -c "
import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1])
print(f\"top1 {d['top1_accuracy']:.1%} | <=3 guesses {d['found_within_3_guesses']:.1%} | avg Q {d['avg_questions']} | unknown answers {d['unknown_answer_rate']:.1%}\")"; }
for cond in "0 0" "0.2 0" "0.4 0" "0.2 0.3"; do
  set -- $cond
  for model in legacy calibrated; do
    printf "omission=%-4s noise=%-4s model=%-10s " $1 $2 $model
    docker compose run --rm --no-deps -T -e ANSWER_MODEL=$model -v "$PWD/eval_results:/srv/backend/eval_results" backend timeout 600 python -m app.evaluation --modes adaptive \
      --load-targets eval_results/targets-popularity.json --games 200 --omission $1 --noise $2 --out eval_results/omission_${model}_o$1_n$2.json | grep "^adaptive " | row
  done
done
echo "### DONE"
