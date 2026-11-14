#!/bin/sh
# Paired 200-game evaluation on the same pinned targets and seeds.
# Requires the Fuseki service from docker compose up.
set -eu
restore() {
  docker compose run --rm --no-deps -T ingestion python -m app.ingestion >/dev/null
}
trap restore EXIT INT TERM

run_eval() {
  docker compose run --rm --no-deps -T -v "$PWD/eval_results:/srv/backend/eval_results" "$@"
}

docker compose run --rm --no-deps -T -e SKIP_PATCHES=haki ingestion python -m app.ingestion >/dev/null
run_eval backend python -m app.evaluation --modes rule --load-targets eval_results/targets-popularity.json --games 200 --seed 42 --out eval_results/ontology-enrichment-before.json

restore
trap - EXIT INT TERM
run_eval backend python -m app.evaluation --modes rule --load-targets eval_results/targets-popularity.json --games 200 --seed 42 --out eval_results/ontology-enrichment-after.json
