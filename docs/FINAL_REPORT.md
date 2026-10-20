# Final report - Grand Line Akinator

Every number below is measured by a script in this repository (commands in section 6); nothing is estimated. "Previous policy" = the deterministic information-gain policy that existed before the adaptive policy.

## 1. Ontology quality (docs/ONTOLOGY_AUDIT.md)
| issue (upstream `kalnassag/one-piece-ontology`) | found | resolution |
|---|---|---|
| `mangaDebut` / `animeDebut` are `owl:FunctionalProperty` but 12 + 11 characters have two values (a later appearance recorded as a debut) | 23 conflicts | **data patch** `ontology/patches/debut.*.ttl`: source JSON decides (20/23), 3 flagged for review; later value kept as `opx:later*Appearance`; functional axioms **kept** |
| same axioms + data -> OWL RL merges chapters/episodes | **48** non-reflexive `owl:sameAs` (e.g. `Chapter_966 = Chapter_552`) and ~280 spurious derived triples | 0 after the patch; ingestion fails if one appears; earlier "19k sameAs" claim was reflexive triples and is corrected |
| `op:inCrew` inverse of `hasCrewMember` with the same domain/range | characters typed `PirateCrew`, crews typed `Character` | `ontology/patches/schema-increw.*.ttl` |
| fruit-user links to near-miss URIs (`Monkey_D._Luffy`, `Marshall_D._Teach`, ...) | 5 links; Blackbeard, Law (and Ace as previous user) had no fruit | `uri-reconcile` patch (unique normalised-name twin required) |
| `owl:oneOf` on `op:DevilFruitType` vs data | HermiT: consistent as published; **latent** inconsistency if the fruit types are asserted pairwise different (upstream alone, not caused by our extension) | not modified (no observed failure); documented; OWL RL derives nothing from it |
| Buzz, Gasparde, Honey Queen, Simon, A_certain_doctor, Unnamed_New_World_pirate | no reliable mapping | **left unresolved on purpose**; tests assert they are not guessed, not patched, not game entities |
| SHACL (`ontology/shapes.ttl`) | 23 violations on upstream + extension | **0** on the shipped graph; ingestion fails otherwise |

## 2. Reasoning results (OWL 2 RL via owlrl, not a full DL reasoner)
| scenario | time | inferred triples | domain-relevant inferred | non-reflexive sameAs |
|---|---|---|---|---|
| upstream as-is, axioms kept, no guard | 12.0 s | 38,783 | 1,565 | **48** |
| old workaround (drop all functional axioms) | 12.5 s | 38,458 | 1,289 | 0 (but `inCrew` mistyping left) |
| **shipped (patched, axioms kept)** | 12.7 s | 38,418 | 1,272 | **0** |
Graph: 5.4k nodes, 1,503 characters / 141 Devil Fruits / 9 ships; edges are `explicit`, `curated` or `inferred`. Every ingestion run checks 10 conditions (counts, inferred edges, no merges, no dropped axiom, SHACL clean).

## 3. Three-valued semantics (unknown is never false)
Scopes `positive`, `path`, `last:rel:R`, `last:prop:P`, `status`, `rel:R`, `prop:P`, `closed` decide when absence means UNKNOWN. Tests: characters without a recorded Devil Fruit are UNKNOWN (1,000+ characters), unknown ship builders / types / life status stay UNKNOWN, a fruit's user without a recorded occupation does not make "eaten by a captain?" FALSE, a conjunction with one unknown conjunct is UNKNOWN (Kleene AND), cardinality is never FALSE. Two violations were found *by these tests* and fixed (ship owner who ate a fruit; fruit-user facts).

## 4. Guessing performance
### 4a. Effect of the ontology corrections (previous deterministic policy, 200 pinned targets each; `final_eval.sh`)
| ontology patches | unknown handling | targets | top-1 | found <= 3 guesses | avg Q | unknown answers |
|---|---|---|---|---|---|---|
| off | legacy closed-world | popular | 75.0% | 90.0% | 16.3 | 3.7% |
| **on** | legacy closed-world | popular | 76.5% | 91.0% | 15.9 | 3.8% |
| off | strict open-world | popular | 72.0% | 85.0% | 17.2 | 9.3% |
| **on** | strict open-world | popular | 73.0% | 86.0% | 16.9 | 9.7% |
| off | legacy closed-world | uniform | 67.5% | 83.0% | 18.4 | 4.7% |
| **on** | legacy closed-world | uniform | 67.0% | 83.5% | 18.3 | 4.9% |
| off | strict open-world | uniform | 60.5% | 78.5% | 19.0 | 12.3% |
| **on** | strict open-world | uniform | 61.0% | 77.5% | 18.9 | 12.4% |
The corrections change top-1 by -0.5 to +1.5 points and questions by -0.4 to -0.1: **small and within the noise** (standard error ~3 points at n = 200); their value is correctness (no merged chapters, Blackbeard and Law have their fruits), not accuracy. Making unknown facts unknown instead of false costs 3-7 points and raises the unknown-answer rate about 2.5x in the simulator (a conservative player model, see README).
Priors (patched, strict): popularity prior 73.0% / 16.9 Q vs uniform prior 70.0% / 18.5 Q on popular targets (61.0% vs 58.5% on uniform targets). Random questions: 24.5% / 29.4 Q.

### 4b. Adaptive policy vs previous policy (same 200 targets, same seeds; `policy_eval.sh`, docs/POLICY.md)
| policy | top-1 | <=3 guesses | avg Q | median Q | distinct openings | opening entropy | topics in first 8 | sessions with equivalent question pair | unknown answers | latency |
|---|---|---|---|---|---|---|---|---|---|---|
| previous (deterministic IG) | 72.0% | 86.5% | 18.7 | 15 | 1 | 0 b | 4.13 | 72% | 11.4% | 0.7 ms |
| adaptive T = 0 | 72.5% | 83.5% | 13.7 | 12 | 1 | 0 b | 4.68 | 13% | 5.5% | 1.7 ms |
| **adaptive T = 0.06 (default)** | **74.0%** | 83.5% | **13.6** | 12 | **5** | **1.6 b** | **4.71** | **16%** | **5.4%** | 1.6 ms |
Same target, 10 seeds (20 targets): previous 85.0% / 15.6 Q / 1 opening; adaptive 84.5% / 12.6 Q / 3.2 openings per target, question-set distance between seeds 0.46.
Not supported by the data: that adaptive is better on "found within 3 guesses" (3 points lower, n.s.); that the shorter games are caused by duplicate avoidance (not isolated).

### AI planner: what is and is not established
**Not established: an accuracy or cost benefit of the AI planner.** The only complete 12-game run (policy code before the fixes below) gave top-1 75.0% (previous policy), 58.3% (adaptive, rule-based), 83.3% (adaptive + planner) on the same 12 targets - differences of 1-3 games are noise, so this run supports no ranking. A second, instrumented 12-game run (also before the fixes) showed why the planner was unreliable: **179 planner calls, 138 failed**, 112 proposed questions of which 23 were accepted; rejected: 62 redundant (the rule bank already contains them), 12 low-value, 10 unsupported, 4 unanswerable, 1 ambiguous; mean planner latency 19 s because of stalled calls.
Causes observed in a live per-turn trace, and fixed afterwards: (1) a single malformed proposal (a path without `cond`) made `LLMReply` validation fail and discarded the whole reply - now each item is parsed on its own (`llm.parse_reply`); (2) a stalled connection blocked a turn for ~33 minutes - now there is a connect/read timeout, a hard wall-clock deadline, and a circuit breaker that skips the planner for 3 turns after 2 failures; Neo4j queries got a 60 s limit and keep-alive. Unit tests cover the tolerant parser and the deadline (`tests/test_policy.py`). The breakdown of the 138 failures was not recorded per cause, so it must not be attributed to these two alone.
**The re-run after the fixes did not finish**: two attempts stalled when the host machine slept (half-dead TCP connections; container uptime of hours for a ~10 minute job). Treat the AI mode as functionally verified (live trace: first call 3.6 s, later turns served from the cache in ~20 ms, rule-based fallback on any failure) but **not benchmarked**; `eval_results/ai_eval.sh` reproduces the measurement on a stable machine.

## 5. Known limitations
* Curated demo data: 9 ships, Haki for 21 characters, 7 Ancient/Mythical fruits. Uncurated Haki is unknown.
* 38% of the documented entities share identical known facts with another entity (62% are uniquely identifiable); Devil Fruits are the hardest group (no ability data upstream).
* Simulated players are a conservative model; no human study was run.
* The opening variety is five broad questions; raising it costs accuracy (sweeps in docs/POLICY.md).
* OWL 2 RL only. The `oneOf` latent inconsistency and the namespace split (`/onepiece/` vs `#`, 25 URIs) remain in the upstream data.
* The three flagged debut decisions (Mr 7 manga+anime, Minatomo anime) need a human check against the wiki.
* Together AI calls are slow (3-8 s) and cached per (phase, offered questions); the app works without a key (rule-based).
* Chrome extension unavailable during development: the UI was verified with headless Playwright in Docker (screenshots in `docs/screenshots/`).

## 6. Reproduce everything (Docker only)
```bash
cp .env.example .env                      # set TOGETHER_API_KEY and NEO4J_PASSWORD (+ BACKEND_PORT/FRONTEND_PORT if 8000/3000 are taken)
docker compose up --build -d              # neo4j -> ingestion (RDF -> patches -> OWL RL -> SHACL -> Neo4j) -> backend -> frontend
docker compose ps                         # all healthy;  http://localhost:3000  (API docs :8000/docs, Neo4j browser :7474)

docker compose run --rm ingestion                                              # re-import (idempotent); fails on SHACL violation / merged entities
docker compose run --rm --no-deps backend python -m pytest -q tests            # unit + integration tests
docker compose run --rm --no-deps backend python -m app.audit                  # ontology audit: before/after reasoning, SHACL
python tools/hermit/mkslice.py && docker run --rm -v "$PWD/tools/hermit:/w" -w /w python:3.12-slim sh -c \
  "apt-get update -qq && apt-get install -y -qq --no-install-recommends default-jre-headless && pip install -q owlready2 && python run_hermit.py"
./eval_results/final_eval.sh              # patches x unknown-handling ablation + baselines (~10 min)
./eval_results/policy_eval.sh             # adaptive vs deterministic policy + sweeps (~10 min)
./eval_results/ai_eval.sh                 # AI-assisted planner on 12 targets (~10 min)
```
