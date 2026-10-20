# Adaptive question policy - investigation, design, measured results

All numbers are produced by the scripts in `eval_results/` (`policy_eval.sh`, `ai_eval.sh`, `final_eval.sh`) on **identical pinned targets** (`targets-popularity.json`, 200 popular entities) and identical seeds. Raw JSON is next to them.

## 1. Why games felt repetitive (investigation of the previous implementation)
| finding | evidence |
|---|---|
| The opening was deterministic. `GameState.pick()` returned `ranked[0]` (argmax expected information gain) on a fixed prior. | 200 games -> 1 distinct opening ("Is your character affiliated with a pirate crew?"), 0 seed dependence |
| Information gain alone happily asks near-duplicate questions, because each one is still informative *given the posterior*. | 72% of old-policy sessions contain at least one pair of questions with \|phi\| >= 0.9 (equivalent answers over all entities); 2.2% of all asked pairs |
| Generic questions dominate: category / affiliation / role questions have the highest IG for a broad prior. | opening + first 8 topics: only 4.1 distinct topics on average |
| Only a soft family decay existed; no notion of topic, phase, wording or answer-equivalence. | `engine.rank()` |

Ontology correctness, SHACL and the three-valued semantics were left untouched (and extended, see section 5).

## 2. Policy (`app/policy.py`)
`score(q) = sum_c W[phase][c] * minmax_c(q)` over **valid** questions only.

| component | meaning |
|---|---|
| info | expected information gain (exact under the answer model, unchanged) |
| coverage | 1 - P(unknown): how much of the candidate mass can actually answer |
| novelty | 1 - max \|phi\| with every asked question (prior-weighted, known cells only): semantic duplicates |
| diversity | `0.5^(# of the last 4 questions on the same topic)` |
| specificity | closeness of the question's yes-mass to a phase target (0.5 / 0.75 / 0.9) |
| repetition | `0.7^(# asked questions of the same family)` (+ hard cap of 3 per family) |
| complexity | 1 - hops/alternatives/conjunction burden |

Every component is min-max normalised over the valid set before weighting. **Valid** = information gain >= 35% of the best *and* \|phi\| < 0.97 with all asked questions. A question with no discriminative value, or a re-worded duplicate, is therefore never selectable, whatever the temperature.

**Selection.** Softmax over the top-k (k = 5) of `score / T`, T = 0.06 by default, with one seeded `random.Random` per session (`/api/game/start {"seed": 7}` reproduces a game). `policy: "deterministic"` or exploration `off` = argmax. Exploration `low|medium|high` = T 0.03 / 0.06 / 0.15.

**Phases** are derived from the posterior, not the question number: *deduction* when <= 20 candidates remain or the top candidate has >= 30% or the entropy fell below 30% of the start; *discovery* while entropy is >= 70% of the start and no favourite exists; otherwise *investigation*. The label has hysteresis so it does not flicker when a contradictory answer widens the posterior: discovery is never re-entered and deduction is left only when the pool has really re-opened (more than 60 candidates or an entropy fraction above 0.66). Each phase has its own weight vector (info 0.40 / 0.50 / 0.70; diversity 0.20 / 0.10 / 0.00).

## 3. Were the weights tested? (`policy_sweep.json`, 100 games, T = 0 unless noted)
<!-- BEGIN:sweep -->
| variant | top-1 | avg Q | distinct topics in first 8 | sessions with equivalent pair |
|---|---|---|---|---|
| full policy | 80.0% | 12.9 | 4.66 | 13.0% |
| - info | 77.0% | 14.1 | 5.19 | 10.0% |
| - coverage | 83.0% | 12.9 | 4.79 | 13.0% |
| - novelty | 82.0% | 12.8 | 4.69 | 15.0% |
| - diversity | 78.0% | 12.7 | 4.03 | 8.0% |
| - specificity | 81.0% | 13.0 | 4.67 | 14.0% |
| - repetition | 78.0% | 12.9 | 4.59 | 12.0% |
| - complexity | 80.0% | 13.0 | 4.67 | 13.0% |

| T | top-1 | <=3 guesses | avg Q | distinct openings | opening entropy |
|---|---|---|---|---|---|
| 0.0 | 80.0% | 90.0% | 12.9 | 1 | 0 b |
| 0.03 | 83.0% | 90.0% | 12.9 | 3 | 0.96 b |
| 0.06 | 82.0% | 89.0% | 12.8 | 5 | 1.54 b |
| 0.1 | 78.0% | 88.0% | 12.8 | 5 | 1.99 b |
| 0.2 | 75.0% | 87.0% | 13.1 | 5 | 2.22 b |
| 0.4 | 73.0% | 82.0% | 13.6 | 5 | 2.25 b |
<!-- END:sweep -->

Honest reading: with 100 games the standard error of top-1 is ~4 points, so **no ablation changes accuracy significantly**. The components do what they are for on their own metric: removing *info* lengthens games by 1.2 questions, removing *diversity* cuts topic variety (4.7 -> 4.0), removing *novelty* raises equivalent pairs. Removing *coverage* looks slightly better (83%, within noise); it stays because the spec asks for known-answer coverage and the effect is not significant. The weights were not tuned beyond this.

Temperature grid and the component ablation above are in the same generated block (`policy_sweep.json`).

T = 0.06 is the largest temperature that keeps accuracy; larger values only add entropy to the same 5 openings (cap: top-k = 5, log2 5 = 2.32 bits) and cost accuracy.
A per-phase temperature scale (exploration high at the start, off at the end; `policy_phase_sweep.json`) raised opening entropy from 1.6 to 2.1-2.3 bits but lowered top-1 from 74.0% to 70.0-72.5% (n = 200), so it was **not** adopted (`PHASE_TEMP_SCALE` stays 1/1/1).

<!-- BEGIN:phase -->
| temperature scale (discovery, investigation, deduction) | top-1 | <=3 guesses | avg Q | opening entropy |
|---|---|---|---|---|
| (1, 1, 1) | 74.0% | 83.5% | 13.6 | 1.6 b |
| (2, 1, 0) | 70.0% | 82.5% | 13.7 | 2.06 b |
| (2.5, 1, 0) | 71.5% | 83.0% | 14.1 | 2.14 b |
| (2.5, 1, 0.5) | 71.5% | 83.0% | 14.1 | 2.14 b |
| (4, 1, 0) | 70.5% | 84.5% | 14.0 | 2.25 b |
| (4, 0.5, 0) | 72.5% | 84.5% | 14.0 | 2.25 b |
| (6, 0.5, 0) | 70.0% | 82.5% | 13.9 | 2.28 b |
<!-- END:phase -->

## 4. Adaptive vs deterministic - identical targets and seeds (200 games, `policy_eval.json`)
<!-- BEGIN:main -->
| policy | top-1 | <=3 guesses | avg Q | median Q | distinct openings | opening entropy | topics in first 8 | repeated family | equivalent-pair rate | sessions with equivalent pair | unknown answers | latency mean / p95 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| random (baseline) | 27.0% | 44.0% | 29.5 | 30 | 112 | 6.62 b | 4.83 | 0.367 | 1.11% | 96.0% | 8.3% | 0.5 / 1 ms |
| deterministic IG (previous) | 72.0% | 86.5% | 18.7 | 15 | 1 | 0 b | 4.13 | 0.234 | 2.16% | 72.0% | 11.4% | 0.7 / 1 ms |
| adaptive, T = 0 | 72.5% | 83.5% | 13.7 | 12 | 1 | 0 b | 4.67 | 0.277 | 0.15% | 13.0% | 5.6% | 1.6 / 3 ms |
| **adaptive, T = 0.06 (default)** | 74.0% | 83.5% | 13.6 | 12 | 5 | 1.6 b | 4.71 | 0.299 | 0.18% | 16.0% | 5.4% | 1.6 / 3 ms |

Openings of the adaptive policy (top 4 of 5): “Is your character affiliated with a pirate crew?” 107; “Is it a living character?” 62; “Is it a character?” 22; “Does it have the role or occupation "Pirate"?” 5. The deterministic policy opened with “Is your character affiliated with a pirate crew?” in 200 of 200 games.

**Same target, 10 seeds, 20 targets:**

| policy | top-1 | <=3 guesses | avg Q | distinct openings per target | question-set distance between seeds | equivalent-pair rate |
|---|---|---|---|---|---|---|
| deterministic IG | 85.0% | 95.0% | 15.6 | 1 | 0.0 | 1.75% |
| adaptive | 84.5% | 95.0% | 12.6 | 3.15 | 0.457 | 0.31% |
<!-- END:main -->

Conclusions that the data supports: variety did not reduce top-1 accuracy (74.0% vs 72.0% over 200 games, 84.5% vs 85.0% over 200 variety games; both inside the noise) and games got ~5 questions shorter (18.7 -> 13.6). **The cause of the shortening was not isolated**: removing the novelty component does not lengthen games (12.8 vs 12.9 questions), so it must not be attributed to duplicate avoidance; the old policy additionally multiplied information gain by coverage and had no phase logic, and the sweep only shows that removing *info* costs 1.2 questions. **What it does not support:** the share of games found within 3 guesses is 3 points lower in the 200-game run (83.5% vs 86.5%; not significant at n = 200, equal in the variety run). Opening variety is real but bounded: five broad questions, not dozens - the policy refuses to open with a weak question.

## 5. Richer question grammar (`app/questions.py`)
Operators (all validated against the live schema, all compile to parameterised Cypher, all have an explicit True / False / Unknown evaluation):
| operator | example question | unknown handling |
|---|---|---|
| class membership (OWL-inferred label) | "Is your character affiliated with the World Government?" | scope `rel:AFFILIATES_WITH` |
| property existence | "Has your character eaten a Devil Fruit?" | `positive`: absence = unknown |
| relation to a known entity | "Does it have a connection to the Straw Hat Pirates?" | per-category scopes |
| inverse relation | "Did the person who ate it ever own a ship?" (`dir: in`) | `positive` |
| multi-hop with class condition | "Was it eaten by a captain?" (fruit -> user -> `CaptainCharacter`) | `last:rel:OCCUPATION`: known only if the user's occupation is recorded |
| sub-class | "Does your character possess a Mythical Zoan Devil Fruit, or is it one?" | `positive` (curated subtypes only) |
| conjunction (`mode: all`, Kleene AND) | "Is your character the captain of a pirate crew?" | FALSE only if a conjunct is known FALSE; one UNKNOWN conjunct keeps UNKNOWN |
| cardinality (`count >= n`) | accepted by the grammar | **never FALSE**: allowed only with scope `positive`; `closed` is rejected unless the relation is in `COMPLETE_RELS`, which is empty because no relation is established as complete; the rule generator emits none |

New scopes `path`, `last:rel:R`, `last:prop:P` were added after a test showed that a fruit's *user* without a recorded occupation had made "eaten by a captain?" FALSE - a violation of the open-world rule that is now covered by `test_fruit_user_questions_stay_unknown_when_the_users_facts_are_missing`.

## 6. LLM planner (`app/llm.py`, `service._ai_plan`)
Input: phase, recent topics, last answer, operators, schema, candidate summary (names are only used for wording), already-asked questions and the top-4 questions *by policy score*. Output (pydantic): paraphrases, <= 3 new question specs, a <= 90 character reaction. The model never writes Cypher and never chooses the question.
Every proposal is rejected when: outside the live schema or malformed (*unsupported*), no entity can be TRUE (*unanswerable*), two question marks / "or" alternatives (*ambiguous*), \|phi\| >= 0.97 with any banked question (*redundant*), information gain below half the median of the current top questions (*low-value*), or its text names a current candidate (*leaks-candidate*). Reasons are counted per game (developer view). Accepted questions still have to win on the policy score.
Caches: wording per question id (`_PARA_CACHE`), whole planner replies per (phase, offered question ids) (`_REPLY_CACHE`), accepted question specs persist in the bank. A cache hit costs no API call; the contextual reaction then falls back to the deterministic template.

### AI planner: what is and is not established
**Not established: an accuracy or cost benefit of the AI planner.** The only complete 12-game run (policy code before the fixes below) gave top-1 75.0% (previous policy), 58.3% (adaptive, rule-based), 83.3% (adaptive + planner) on the same 12 targets - differences of 1-3 games are noise, so this run supports no ranking. A second, instrumented 12-game run (also before the fixes) showed why the planner was unreliable: **179 planner calls, 138 failed**, 112 proposed questions of which 23 were accepted; rejected: 62 redundant (the rule bank already contains them), 12 low-value, 10 unsupported, 4 unanswerable, 1 ambiguous; mean planner latency 19 s because of stalled calls.
Causes observed in a live per-turn trace, and fixed afterwards: (1) a single malformed proposal (a path without `cond`) made `LLMReply` validation fail and discarded the whole reply - now each item is parsed on its own (`llm.parse_reply`); (2) a stalled connection blocked a turn for ~33 minutes - now there is a connect/read timeout, a hard wall-clock deadline, and a circuit breaker that skips the planner for 3 turns after 2 failures; Neo4j queries got a 60 s limit and keep-alive. Unit tests cover the tolerant parser and the deadline (`tests/test_policy.py`). The breakdown of the 138 failures was not recorded per cause, so it must not be attributed to these two alone.
**The re-run after the fixes did not finish**: two attempts stalled when the host machine slept (half-dead TCP connections; container uptime of hours for a ~10 minute job). Treat the AI mode as functionally verified (live trace: first call 3.6 s, later turns served from the cache in ~20 ms, rule-based fallback on any failure) but **not benchmarked**; `eval_results/ai_eval.sh` reproduces the measurement on a stable machine.

