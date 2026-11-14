#!/bin/sh
# Everything that backs docs/POLICY.md and the README results table (policy sweeps + comparison, then the AI planner). ~25 min.
cd "$(dirname "$0")/.." || exit 1
./eval_results/policy_eval.sh
docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" backend python -m app.policy_eval --sweep-phase --games 200 --out eval_results/policy_phase_sweep.json
./eval_results/ai_eval.sh
echo "### ALL DONE"
