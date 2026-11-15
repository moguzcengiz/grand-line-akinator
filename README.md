# Grand Line Akinator

Ontology-driven Akinator for One Piece (characters, Devil Fruits, ships). Questions are generated from a **Apache Jena Fuseki (RDF/SPARQL) knowledge graph built from
[kalnassag/one-piece-ontology](https://github.com/kalnassag/one-piece-ontology)**, selected by **expected information gain**, and every prediction is explained with graph facts.
Stack: FastAPI · Apache Jena Fuseki 5 (TDB2) · RDFLib + owlrl · Together AI (optional) · React/TS/Vite/Tailwind · Docker Compose.

## Run
```bash
cp .env.example .env          # set TOGETHER_API_KEY and FUSEKI_PASSWORD (never commit .env)
docker compose up --build -d  # fuseki -> ingestion (one-shot) -> backend -> frontend  (~90 s cold)
```
| | URL |
|---|---|
| Frontend | http://localhost:3000 |
| API + Swagger | http://localhost:8000 · http://localhost:8000/docs |
| Fuseki (SPARQL UI / endpoint `/ds/sparql`) | http://localhost:3030 (reads are open; writes need user `admin` + `FUSEKI_PASSWORD`) |

If 3000/8000 are taken on your machine set `FRONTEND_PORT` / `BACKEND_PORT` (and `FUSEKI_PORT` for 3030) in `.env`.
Re-run ingestion any time (idempotent): `docker compose run --rm backend python -m app.ingestion`
Fuseki data lives in the named volume `fuseki_data`. Without a Together key the app still works (rule-based; AI mode falls back per turn).

## Repository layout
| Path | Contents |
|---|---|
| [`backend/`](backend/README.md) | FastAPI service: ingestion, question bank, game engine, AI planner, evaluation |
| [`frontend/`](frontend/README.md) | React + TypeScript UI |
| [`ontology/`](ontology/README.md) | this project's ontology layer: extension axioms, curated data, SHACL shapes, patches |
| `ontology-src/` | the upstream ontology, vendored unchanged |
| `fuseki/` | Apache Jena Fuseki configuration |
| `docs/` | architecture, ontology, policy and audit reports |
| `eval_results/` | evaluation scripts and pinned target lists |

## How the upstream ontology is integrated and extended
Full details: [docs/ONTOLOGY.md](docs/ONTOLOGY.md) · architecture diagram: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
* The repo is vendored unchanged in `ontology-src/`; its schema + 33k-triple dataset + the hand-curated Straw Hat model are parsed with RDFLib. All URIs are preserved.
* Gaps found by inspection (no ships, no Haki, `hasDevilFruit` declared but empty, no pirate/marine typing, no Ancient/Mythical Zoan) are filled by `ontology/extension.ttl` (OWL RL-friendly axioms: inverse, someValuesFrom, hasValue, property chain) and clearly-labelled curated data and patches (22 original Haki profiles plus 3 evidence-backed profiles, 7 fruits, 9 ships). See the [enrichment audit](docs/ONTOLOGY_ENRICHMENT_AUDIT.md), [sources](docs/ONTOLOGY_ENRICHMENT_SOURCES.md), and [measured report](docs/ONTOLOGY_ENRICHMENT_REPORT.md).
* `owlrl` materialises inferences (OWL 2 RL only — **not** full OWL 2 DL). Edges carry `provenance = explicit | curated | inferred`; the game reads the graph closed-world (see Known limitations).
* Data-quality audit ([docs/ONTOLOGY_AUDIT.md](docs/ONTOLOGY_AUDIT.md)): upstream debut data violates its own `owl:FunctionalProperty` axioms (OWL RL would merge 48 chapter/episode pairs), `op:inCrew` has swapped domain/range, and 5 fruit-user links have near-miss URIs. All fixed in a reviewable patch layer (`ontology/patches/`), axioms kept, SHACL (`ontology/shapes.ttl`) validates at ingestion. `python -m app.audit` reproduces the before/after numbers.
* **Wiki attributes** (`python -m app.wiki_pipeline fetch|extract|emit`): gender, race, fighting style, titles, bounty tier and *current vs former* affiliation and occupation for 1,402 of the 1,514 characters, read from the infobox and categories of the [One Piece Wiki](https://onepiece.fandom.com) (text CC-BY-SA; page URL and revision id are stored per entity). Output: `ontology/patches/wiki-attributes.add.ttl`.
* **Story time** (`python -m app.arcs`): debut arc, debut saga and before/after the timeskip for 1,452 characters, derived from the existing debut chapters and a 33-arc / 11-saga table (`ontology/story-arcs.json`, same wiki). Output: `ontology/patches/debut-arc.add.ttl`.
* Graph: 7.2k nodes, 27.4k edges (13.3k explicit, 13.1k curated, 1.0k inferred), 1,514 characters / 151 Devil Fruits / 9 ships, 380 questions.

## Gameplay
No two voyages need to start alike: an adaptive, multi-objective **question policy** (docs/POLICY.md) scores every graph-grounded question on information gain, known-answer coverage, novelty (semantic duplicates are never asked), topic diversity, specificity, repetition and complexity, then samples among the top 5 with a seeded softmax. The game moves through three phases - *Scouting the seas* (broad), *Following the trail* (specific), *Closing in* (separating the last suspects) - chosen from the candidate entropy and confidence. Normal players never see candidate names, probabilities or queries (developer view only); they get a progress meter, short reactions, a dramatic reveal, wrong-guess recovery, an undo button and a voyage summary.
```
Q1  Is it a living character?                                  Yes
Q2  Has your character eaten a Devil Fruit?                    No    (closed world: no recorded fruit = no)
Q3  Is your character affiliated with a pirate crew?           Yes   (OWL-inferred class PirateAffiliatedCharacter)
Q4  Did we first meet it after the timeskip?                   No    (story time, from the debut chapter)
Q5  Is your character the captain of a pirate crew?            No    (conjunction: captain AND pirate)
Q6  Does it originate from East Blue?                          Yes
Q7  Does it have the role or occupation "Senior Officer"?      Yes
Q8  Is your character a Fighter who uses technology?           No    (wiki attribute)
Q9  Does it have a connection to Ninja-Pirate-Mink-Samurai Alliance?   Yes
Q10 Is your character one of the Worst Generation?             Yes   (wiki attribute)
Prediction: Roronoa Zoro, with the graph path behind every answer and which facts were inferred by OWL RL.
```
When a game is lost the player is asked **"Who was it?"**; every finished game is appended to `work/player-feedback/games.jsonl` (nothing about the player is stored) and `docker compose exec backend python -m app.feedback_report` ranks where players and the graph disagree (candidate missing or wrong facts) and which revealed names are not in the graph.
`POST /api/game/start {"mode":"rule","seed":7}` replays the same game; `"policy":"deterministic"` is the old argmax policy. Add `?dev=true` to any game endpoint for the developer payload.

## API
`POST /api/game/start` · `GET /api/game/{id}` · `POST /api/game/{id}/answer` (`yes|probably|dont_know|probably_not|no`) · `POST /api/game/{id}/undo` · `POST /api/game/{id}/guess-feedback` · `POST /api/game/{id}/reveal` · `GET /api/entities` · `GET /api/entities/{id}` · `GET /api/graph/neighborhood` · `GET /api/ontology/stats` · `GET /api/health`.

## Tests and evaluation
```bash
docker compose run --rm --no-deps backend python -m pytest -q tests          # unit + integration (integration needs the running fuseki service)
./eval_results/policy_eval.sh     # the results table below, ~10 min
./eval_results/final_eval.sh      # ontology-patch x unknown-handling ablation, baselines (previous deterministic policy), ~10 min
./eval_results/ai_eval.sh         # AI-assisted planner on pinned targets, ~10 min
docker compose run --rm ingestion python -m app.audit                        # ontology audit (before/after reasoning, SHACL); also docs/ONTOLOGY_AUDIT.md
```
Simulated players answer from the graph (true -> yes, false -> no, unknown -> "don't know"). The player model is conservative: a real player knows that Zoro has no Devil Fruit and says "no" where the simulator says "don't know".

### Results (all measured; 200 pinned popular targets, identical seeds)
Full tables and caveats: **docs/POLICY.md** (policy), **docs/ONTOLOGY_AUDIT.md** (ontology), **docs/FINAL_REPORT.md** (everything, with the exact reproduction commands).

| policy | top-1 | found within 3 guesses | avg questions | distinct openings | sessions with a semantically equivalent question pair |
|---|---|---|---|---|---|
| random questions | 15.0% | 36.0% | 19.6 | - | 9% |
| deterministic information gain | 92.5% | 100% | 11.9 | **1** | 10% |
| **adaptive policy (default)** | 92.0% | 100% | 12.0 | **5** | 7% |

The adaptive policy matches the deterministic one on accuracy and length while opening in 5 different ways; replaying 20 targets with 10 seeds each gives 95.0% for both, with question sets that differ between seeds by a Jaccard distance of 0.54. Every miss in the 200 games is a pair the graph cannot tell apart (see limitations).

How the result was reached, same 200 targets (adaptive policy): open world 72.5% top-1 / 24.0 questions -> closed world 79.5% / 13.1 -> closed world + wiki attributes + story time 92.5% / 12.0. With a simulated player who disagrees with the graph (15% missing facts, 20% soft answers): 51% -> 56% -> 78%.

The table was measured when 353 popular characters had wiki attributes; after the pipeline ran for all characters the same 200 targets give 93.0% top-1 / 100% within 3 guesses / 12.0 questions.

Beyond the popular targets (adaptive policy, simulated player):

| target group | top-1 | found within 3 guesses | avg questions | indistinguishable from another entity |
|---|---|---|---|---|
| 300 characters drawn uniformly from all 1,514 | 69.3% | 82.7% | 17.2 | 32% (58% before the full wiki run, 76% before any wiki data) |
| all 151 Devil Fruits | 76.8% | 98.0% | 13.2 | 35% |

### AI planner (optional, `mode: "ai"`)
Each turn an LLM sees the remaining suspects and every earlier question with the player's answer, and proposes new questions; a proposal is only used after it is validated against the graph. Same 20 pinned targets, same seeds:

| | rule-based | AI planner (`MiniMaxAI/MiniMax-M3.1-Flash`) |
|---|---|---|
| top-1 | 95% | 95% |
| avg questions | 11.65 | 11.10 |
| LLM questions asked per game | 0 | 3.85 |
| time per turn (mean / p95) | 9 ms / 21 ms | 2.1 s / 4.6 s |

The 0.55-question difference is within the noise of 20 games (per-target differences range from -4 to +3), so no claim is made that the planner shortens the game. The room is small in any case: a target needs 9.7 bits on average and the rule-based game already finishes in 12.0 questions. Of 421 proposals 75 were accepted; 223 were rejected as duplicates of questions already in the bank, because the planner can only combine relations the graph already has.

An offline experiment points to where an LLM does help: when the game ends unsure, letting the LLM read the wiki text of the last five suspects and ask three questions raised top-1 on 300 uniformly drawn characters from 69% to 83% (45 wrong guesses fixed, 3 right ones broken). The player in that experiment is a second LLM call that sees only the target's page, and the feature is not part of the game yet.

## Known limitations
* Ships (9), Haki profiles (25 after the sourced patch) and Ancient/Mythical fruits (7) are curated demo data; upstream has none. Un-curated characters have unknown Haki.
* **32% of the characters and 35% of the Devil Fruits give the same answer to every question as some other entity**, so the game can only guess among them: minor characters whose wiki page states little, and Devil Fruits, which have no ability data.
* Wiki attributes are *unknown* (not false) for the 112 characters without a usable wiki page. Family relations and Devil Fruit abilities are not structured on the wiki and were not extracted. The debut arc is the first appearance on the page, which is not always where a fan remembers meeting the character.
* **Closed world by default** (`CLOSED_WORLD=1`): a fact the graph does not record is FALSE (Zoro has not eaten a Devil Fruit), so every answer splits the candidates cleanly. Only life status "Unknown" and missing Haki profiles stay unknown. A "not listed" FALSE is still soft evidence (`ABSENCE_RELIABILITY=0.90`), so a player who disagrees with an incomplete graph is down-weighted, not eliminated. `CLOSED_WORLD=0` restores the old open world (unrecorded = unknown).
* The default prior is popularity-weighted (degree proxy, docs/ONTOLOGY.md section 6); `PRIOR=uniform` restores the uniform MVP prior (-3 points top-1, +1.6 questions).
* Removed on purpose as low-quality trivia: voice-actor, blood-type, chapter/episode-debut, height and age questions.
* Cardinality questions exist in the grammar but are never generated: no relation is established as complete.
* The AI planner costs one LLM round-trip per uncached turn (about 2 s); sessions live in memory (lost on backend restart).
* The Chrome extension was unavailable during development; the React UI was verified with a headless Playwright run in Docker (screenshots in `docs/screenshots/`).

## Next
Ordered by measured effect: (1) Devil Fruit abilities from page text (31 of the 35 fruit misses are indistinguishable pairs); (2) restrict the playable pool to entities the graph can identify (a third of the characters are minor figures it cannot); (3) play with real people and read `app.feedback_report` (every number here comes from a simulated player); (4) rewrite the generated question texts and prefer questions a fan can answer (saga before arc).

## License and credits
Code: MIT (see [LICENSE](LICENSE)). The upstream ontology in `ontology-src/` is by Kareem Alnassag, MIT (`ontology-src/LICENSE`). Data derived from the [One Piece Wiki](https://onepiece.fandom.com) (`ontology/patches/wiki-attributes.add.ttl`, `ontology/patches/debut-arc.add.ttl`, `ontology/story-arcs.json`) is CC BY-SA. One Piece is the work of Eiichiro Oda; this is an unofficial fan and study project.
