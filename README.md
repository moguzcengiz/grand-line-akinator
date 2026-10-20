# Grand Line Akinator

Ontology-driven Akinator for One Piece (characters, Devil Fruits, ships). Questions are generated from a **Neo4j knowledge graph built from
[kalnassag/one-piece-ontology](https://github.com/kalnassag/one-piece-ontology)**, selected by **expected information gain**, and every prediction is explained with graph facts.
Stack: FastAPI · Neo4j 5 Community · RDFLib + owlrl · Together AI (optional) · React/TS/Vite/Tailwind · Docker Compose.

## Run
```bash
cp .env.example .env          # set TOGETHER_API_KEY and NEO4J_PASSWORD (never commit .env)
docker compose up --build -d  # neo4j -> ingestion (one-shot) -> backend -> frontend  (~90 s cold)
```
| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000 · http://localhost:8000/docs |
| Neo4j Browser | http://localhost:7474 (user `neo4j`, password from `.env`) |

If 3000/8000 are taken on your machine set `FRONTEND_PORT` / `BACKEND_PORT` in `.env`.
Re-run ingestion any time (idempotent): `docker compose run --rm backend python -m app.ingestion`
Neo4j data lives in the named volume `neo4j_data`. Without a Together key the app still works (rule-based; AI mode falls back per turn).

## How the upstream ontology is integrated and extended
Full details: [docs/ONTOLOGY.md](docs/ONTOLOGY.md) · architecture diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* The repo is vendored unchanged in `ontology-src/`; its schema + 33k-triple dataset + the hand-curated Straw Hat model are parsed with RDFLib. All URIs are preserved.
* Gaps found by inspection (no ships, no Haki, `hasDevilFruit` declared but empty, no pirate/marine typing, no Ancient/Mythical Zoan) are filled by `ontology/extension.ttl` (OWL RL-friendly axioms: inverse, someValuesFrom, hasValue, property chain) and a small clearly-labelled `ontology/curated.ttl` (21 Haki profiles, 7 fruits, 9 ships).
* `owlrl` materialises inferences (OWL 2 RL only — **not** full OWL 2 DL). Edges carry `provenance = explicit | curated | inferred`; missing facts are *unknown*, not false.
* Data-quality audit ([docs/ONTOLOGY_AUDIT.md](docs/ONTOLOGY_AUDIT.md)): upstream debut data violates its own `owl:FunctionalProperty` axioms (OWL RL would merge 48 chapter/episode pairs), `op:inCrew` has swapped domain/range, and 5 fruit-user links have near-miss URIs. All fixed in a reviewable patch layer (`ontology/patches/`), axioms kept, SHACL (`ontology/shapes.ttl`) validates at ingestion. `python -m app.audit` reproduces the before/after numbers.
* Graph: 5.4k nodes, 13.7k edges (13.5k explicit, 85 curated, 168 inferred), 1,503 characters / 141 Devil Fruits / 9 ships.

## Gameplay
No two voyages need to start alike: an adaptive, multi-objective **question policy** (docs/POLICY.md) scores every graph-grounded question on information gain, known-answer coverage, novelty (semantic duplicates are never asked), topic diversity, specificity, repetition and complexity, then samples among the top 5 with a seeded softmax. The game moves through three phases - *Scouting the seas* (broad), *Following the trail* (specific), *Closing in* (separating the last suspects) - chosen from the candidate entropy and confidence. Normal players never see candidate names, probabilities or queries (developer view only); they get a progress meter, short reactions, a dramatic reveal, wrong-guess recovery, an undo button and a voyage summary.
```
Q1  Is your character affiliated with a pirate crew?             Yes   (OWL-inferred class PirateAffiliatedCharacter)
Q2  Does it have the role or occupation "Pirate"?                Yes
Q3  Is your character the captain of a pirate crew?              Yes   (conjunction: captain AND pirate, Kleene AND)
Q4  Has your character eaten a Devil Fruit?                   Yes   (OWL-inferred class DevilFruitUser)
Q5  Does it have the role or occupation "Prisoner"?              Yes
Prediction: Monkey D. Luffy, with the graph path behind every answer and which facts were inferred by OWL RL.
```
`POST /api/game/start {"mode":"rule","seed":7}` replays the same game; `"policy":"deterministic"` is the old argmax policy. Add `?dev=true` to any game endpoint for the developer payload.

## API
`POST /api/game/start` · `GET /api/game/{id}` · `POST /api/game/{id}/answer` (`yes|probably|dont_know|probably_not|no`) · `POST /api/game/{id}/undo` · `POST /api/game/{id}/guess-feedback` · `GET /api/entities` · `GET /api/entities/{id}` · `GET /api/graph/neighborhood` · `GET /api/ontology/stats` · `GET /api/health`.

## Tests and evaluation
```bash
docker compose run --rm --no-deps backend python -m pytest -q tests          # unit + integration (integration needs the running neo4j service)
./eval_results/final_eval.sh      # ontology-patch x unknown-handling ablation, baselines (previous deterministic policy), ~10 min
./eval_results/policy_eval.sh     # adaptive vs deterministic policy: accuracy, variety, redundancy, weight/temperature sweep, ~10 min
./eval_results/ai_eval.sh         # AI-assisted planner on the same 12 targets, ~10 min
docker compose run --rm ingestion python -m app.audit                        # ontology audit (before/after reasoning, SHACL); also docs/ONTOLOGY_AUDIT.md
```
Simulated players answer from the graph (true -> yes, false -> no, unknown -> "don't know"). The player model is conservative: a real player knows that Zoro has no Devil Fruit and says "no" where the simulator says "don't know".

### Results (all measured; 200 pinned popular targets, identical seeds)
Full tables and caveats: **docs/POLICY.md** (policy), **docs/ONTOLOGY_AUDIT.md** (ontology), **docs/FINAL_REPORT.md** (everything, with the exact reproduction commands).

| policy | top-1 | found within 3 guesses | avg questions | distinct openings | sessions with a semantically equivalent question pair |
|---|---|---|---|---|---|
| random questions | 27.0% | 44.0% | 29.5 | - | 96% |
| previous deterministic information gain | 72.0% | 86.5% | 18.7 | **1** | **72%** |
| **adaptive policy (default)** | **74.0%** | 83.5% | **13.6** | **5** | **16%** |

Variety did not lower top-1 accuracy (74.0% vs 72.0%; and 84.5% vs 85.0% when the same 20 targets are replayed with 10 seeds each, where question sets differ between seeds by a Jaccard distance of 0.46). The share found within 3 guesses is 3 points lower in the 200-game run (not significant at this sample size). Opening variety is bounded: five broad questions, because weak questions are never selectable.

**AI planner:** functionally verified (graph-validated proposals, caching, deadline, circuit breaker, rule-based fallback) but **not benchmarked**: the only complete 12-game run predates robustness fixes and the re-runs stalled when the host machine slept. No accuracy or cost claim is made for it (details: docs/POLICY.md).

## Known limitations
* Ships (9), Haki (21 characters) and Ancient/Mythical fruits (7) are hand-curated demo data; upstream has none. Un-curated characters have unknown Haki.
* **38% of the documented entities (62% are uniquely identifiable) share identical known facts with another entity**, so no question can separate them and the game can only guess among the twins; Devil Fruits are the hardest group (no ability data in the ontology).
* Unknown facts are never false. Devil Fruit ownership, ships and fruit-user facts are open-world (`positive` / `path` / `last:` scopes); this costs 3-7 points of top-1 versus the old closed-world shortcut (ablation in docs/FINAL_REPORT.md) and raises "don't know" answers in the simulator (partly a simulator artefact, see above).
* The default prior is popularity-weighted (degree proxy, docs/ONTOLOGY.md section 6); `PRIOR=uniform` restores the uniform MVP prior (-3 points top-1, +1.6 questions).
* Removed on purpose as low-quality trivia: voice-actor, blood-type, chapter/episode-debut, height and age questions.
* Cardinality questions exist in the grammar but are never generated: no relation is established as complete.
* The AI planner costs one LLM round-trip per uncached turn (about 3-8 s); sessions live in memory (lost on backend restart).
* The Chrome extension was unavailable during development; the React UI was verified with a headless Playwright run in Docker (screenshots in `docs/screenshots/`).
