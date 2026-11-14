#!/bin/sh
# Paired 200-game evaluation on the same pinned targets and seed.
# Requires the local Fuseki service from docker compose up.
set -eu

restore() {
  docker compose run --rm --no-deps -T ingestion python -m app.ingestion >/dev/null
}
trap restore EXIT INT TERM

run_eval() {
  docker compose run --rm --no-deps -T \
    -v "$PWD/eval_results:/srv/backend/eval_results" \
    -v "$PWD/docs:/srv/backend/docs" "$@"
}

docker compose run --rm --no-deps -T -e SKIP_PATCHES=haki ingestion python -m app.ingestion >/dev/null
run_eval backend python -m app.evaluation --modes rule \
  --load-targets eval_results/targets-popularity.json --games 200 --seed 42 \
  --out docs/ontology-enrichment-before.json

restore
trap - EXIT INT TERM
run_eval backend python -m app.evaluation --modes rule \
  --load-targets eval_results/targets-popularity.json --games 200 --seed 42 \
  --out docs/ontology-enrichment-after.json

python3 - <<'PY'
import json
from pathlib import Path
for side, state in (("before", "omitted"), ("after", "applied")):
    path = Path(f"docs/ontology-enrichment-{side}.json")
    data = json.loads(path.read_text())
    data["paired_comparison"] = {
        "enrichment_patch": "haki",
        "patch_state": state,
        "targets_file": "eval_results/targets-popularity.json",
        "seed": 42,
        "games": 200,
    }
    path.write_text(json.dumps(data, indent=2) + "\n")
PY
