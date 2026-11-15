# Backend

FastAPI service: loads the ontology into Apache Jena Fuseki, builds the question bank and runs the game.
Run it through Docker Compose from the repository root (see the [main README](../README.md)).

| Module (`app/`) | What it does |
|---|---|
| `ingestion.py`, `ontology.py`, `patching.py`, `validation.py` | RDF files + patches -> OWL 2 RL closure -> SHACL check -> Fuseki |
| `graph.py` | Fuseki client (SPARQL over HTTP) |
| `questions.py`, `implications.py` | question bank generated from the schema, compiled to SPARQL; which answers make which questions redundant |
| `engine.py`, `policy.py` | three-valued truth matrix, Bayesian update, information gain; adaptive question policy |
| `service.py`, `main.py`, `schemas.py` | game sessions and the HTTP API (`/docs` for Swagger) |
| `llm.py` | optional AI planner (Together AI); every proposal is validated against the graph |
| `wiki_pipeline.py`, `arcs.py` | build the wiki-attribute and story-time patches |
| `evaluation.py`, `policy_eval.py`, `audit.py`, `feedback_report.py` | simulated-player evaluation, ontology audit, player-feedback report |
| `ontology_campaign.py`, `ontology_sources.py`, `ontology_patch_gate.py`, `enrichment_audit.py`, `perf.py` | tooling of the earlier ontology-enrichment campaign |

```bash
docker compose run --rm --no-deps backend python -m pytest -q tests   # integration tests need the running fuseki service
docker compose run --rm backend python -m app.ingestion               # reload the graph (idempotent)
docker compose exec backend python -m app.evaluation --games 100 --modes random,rule
```

Configuration is read from environment variables; `app/config.py` lists every knob with its default.
