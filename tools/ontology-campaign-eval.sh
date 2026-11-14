#!/bin/sh
# Paired 200-game evaluation for one isolated campaign patch on the exact pinned
# target sample and seed used by the earlier enrichment evaluation. Usage:
#   sh tools/ontology-campaign-eval.sh 001
#   sh tools/ontology-campaign-eval.sh 002
#   sh tools/ontology-campaign-eval.sh 003
set -eu

batch="${1:-001}"
patch="campaign-batch-${batch}"
skip_other="${CAMPAIGN_SKIP_OTHER:-}"
skip_before="$patch"
if [ -n "$skip_other" ]; then
  skip_before="$patch,$skip_other"
fi
before="docs/ontology-campaign-batch-${batch}-before.json"
after="docs/ontology-campaign-batch-${batch}-after.json"

restore() {
  docker compose run --rm --no-deps -T -e SKIP_PATCHES="$skip_other" ingestion python -m app.ingestion
}
trap restore EXIT INT TERM

run_eval() {
  docker compose run --rm --no-deps -T \
    -v "$PWD/eval_results:/srv/backend/eval_results" \
    -v "$PWD/docs:/srv/backend/docs" "$@"
}

docker compose run --rm --no-deps -T -e SKIP_PATCHES="$skip_before" ingestion python -m app.ingestion
run_eval backend python -m app.evaluation --modes rule \
  --load-targets eval_results/targets-popularity.json --games 200 --seed 42 \
  --out "$before"

restore
trap - EXIT INT TERM
run_eval backend python -m app.evaluation --modes rule \
  --load-targets eval_results/targets-popularity.json --games 200 --seed 42 \
  --out "$after"

CAMPAIGN_BATCH="$batch" CAMPAIGN_PATCH="$patch" CAMPAIGN_SKIP_OTHER="$skip_other" python3 - <<'PY'
import os
import json
from pathlib import Path
batch = os.environ["CAMPAIGN_BATCH"]
patch = os.environ["CAMPAIGN_PATCH"]
skip_other = os.environ.get("CAMPAIGN_SKIP_OTHER", "")
for side, state in (("before", "omitted"), ("after", "applied")):
    path = Path(f"docs/ontology-campaign-batch-{batch}-{side}.json")
    data = json.loads(path.read_text())
    data["paired_comparison"] = {
        "enrichment_patch": patch,
        "patch_state": state,
        "targets_file": "eval_results/targets-popularity.json",
        "seed": 42,
        "games": 200,
        "additional_skipped_patches": [p for p in skip_other.split(",") if p],
    }
    path.write_text(json.dumps(data, indent=2) + "\n")
PY
