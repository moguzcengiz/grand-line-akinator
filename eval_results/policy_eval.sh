#!/bin/sh
# Adaptive vs deterministic policy.  Identical pinned targets (eval_results/targets-popularity.json) and identical seeds.  ~10 min.
run() { docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" "$@"; }
echo "### A. sweep: temperature grid + component ablation (100 games)"
run backend python -m app.policy_eval --sweep --games 100 --out eval_results/policy_sweep.json
echo "### B. main comparison (200 games, then 20 targets x 10 seeds)"
run backend python -m app.policy_eval --games 200 --out eval_results/policy_eval.json
echo "### DONE"
