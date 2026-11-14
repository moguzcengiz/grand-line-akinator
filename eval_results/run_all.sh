#!/bin/sh
# Reproduces every number in the README. Run from the repo root.
run() { docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" "$@"; }
for prior in uniform popularity; do for td in uniform popularity; do
  echo "### prior=$prior targets=$td"
  run -e PRIOR=$prior backend python -m app.evaluation --games 200 --seed 42 --pool rich --modes random,rule --target-dist $td --out eval_results/prior-${prior}_targets-${td}.json | grep -E "^\| (random|rule)"
done; done
echo "### AI-assisted (prior=popularity targets=popularity, 12 games)"
run -e PRIOR=popularity backend python -m app.evaluation --games 12 --ai-games 12 --seed 42 --pool rich --modes rule,ai --target-dist popularity --out eval_results/ai.json | grep -E "^\| (rule|ai)"
