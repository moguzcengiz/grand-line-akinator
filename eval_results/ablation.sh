#!/bin/sh
# 2x2 ablation on PINNED targets (same names, same seeds, same 200 games each):
#   ontology patches {off,on}  x  unknown-handling {legacy closed-world, strict open-world}
# Ends by restoring the shipped graph (patches on).  Takes ~5 min.
run()  { docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" "$@"; }
for patches in 0 1; do
  docker compose run --rm -e APPLY_PATCHES=$patches ingestion > /dev/null 2>&1 || echo "ingestion failed for patches=$patches"
  for strict in 0 1; do for t in popularity uniform; do
    printf "patches=%s strict_unknown=%s targets=%s " $patches $strict $t
    run -e APPLY_PATCHES=$patches -e STRICT_UNKNOWN=$strict backend python -m app.evaluation --modes rule --load-targets eval_results/targets-$t.json --out eval_results/ablation_p${patches}_s${strict}_$t.json | grep "^rule" \
      | python3 -c "import sys,json; d=json.loads(sys.stdin.read().split(' ',1)[1]); print(d['games'],'games top1',d['top1_accuracy'],'avgQ',d['avg_questions'],'medQ',d['median_questions'],'unk',d['unknown_answer_rate'],'identifiable',d['identifiable_fraction'])"
  done; done
done
docker compose run --rm ingestion > /dev/null 2>&1 && echo "restored shipped graph (patches on)"
