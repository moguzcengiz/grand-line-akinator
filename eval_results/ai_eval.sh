#!/bin/sh
# AI-assisted planner vs rule-based policies on the SAME 12 pinned targets.  Every planner call has a hard deadline (llm.py), so this is bounded (~10 min).
cd "$(dirname "$0")/.." || exit 1
docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" backend timeout 1500 python -m app.evaluation --modes ig,adaptive,ai \
  --load-targets eval_results/targets-popularity.json --games 12 --ai-games 12 --out eval_results/ai_policy.json | grep -E "^(ig|adaptive|ai) " | cut -c1-120
echo "### DONE"
