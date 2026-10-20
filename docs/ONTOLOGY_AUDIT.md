# Ontology audit: inconsistencies found, causes and resolutions

Generated from `eval_results/audit.json` by `python -m app.audit` (reproducible; ~1 min). Nothing below is silently suppressed:
every problem is detected by code, reported at ingestion (`/api/ontology/stats` → `ingestion`), and guarded by tests (`tests/test_ontology_audit.py`).

## 1. `owl:FunctionalProperty` on `op:mangaDebut` / `op:animeDebut`
**What OWL does.** `op:animeDebut a owl:FunctionalProperty` + `Kaku animeDebut Episode_230, Episode_919` ⇒ an RL reasoner infers
`Episode_230 owl:sameAs Episode_919` (OWL has no unique-name assumption) and then propagates that equality.

**Investigation (not assumed).** `functional_conflicts()` found {'mangaDebut': 12, 'animeDebut': 11} (mangaDebut / animeDebut) violating subjects, each with exactly **two** values; `internalID` (the only other functional property) has none; there are no inverse-functional properties.
The processed source JSON (`data/processed/full-character-data-processed-2.json`) holds a *single* `Debut` per character, so the second value is not a source-specified debut:
it is a **later appearance recorded as a second debut** (e.g. Kaku: Chapter 323 = Water 7 debut, Chapter 927 falls in a much later arc). → **data error, not an axiom error**: "a debut is unique" is the correct model, so the axiom is kept.
In 20 of 23 cases the source JSON picks the value to keep; in 4 of those it is the *later* number (Bomba, Hack, Hera, Risky Brothers) - a naive "keep the earliest" rule would have been wrong, so the JSON is authoritative.
3 subjects (Mr 7 manga+anime, Minatomo anime) have no JSON value: the earliest value is kept and the case is flagged ⚠ for manual review.

**Resolution (patch layer, upstream untouched).** `ontology/patches/debut.{remove,add}.ttl`: the second value is removed from `op:*Debut` and re-attached as `opx:laterMangaAppearance` / `opx:laterAnimeAppearance` (curated provenance) - no fact is lost. The previous broad workaround (dropping *all* functional axioms) is gone.
`materialize()` still contains a guard: if some functional property is violated by future data, **only that property's** axiom is dropped from the reasoning copy, and it is reported (`functional_axioms_dropped_for_reasoning`) and fails ingestion validation.

| subject | property | upstream values | kept as debut | source JSON | decision basis |
|---|---|---|---|---|---|
| Bomba | mangaDebut | Chapter_652, Chapter_711 | **Chapter_711** | Chapter 711 | JSON |
| Cerberus | mangaDebut | Chapter_1137, Chapter_444 | **Chapter_444** | Chapter 444 | JSON |
| Ganryu | mangaDebut | Chapter_552, Chapter_966 | **Chapter_552** | Chapter 552 | JSON |
| Hack | mangaDebut | Chapter_391, Chapter_706 | **Chapter_706** | Chapter 706 | JSON |
| Hanji | mangaDebut | Chapter_929, Chapter_949 | **Chapter_929** | Chapter 929 | JSON |
| Hera | mangaDebut | Chapter_1011, Chapter_703 | **Chapter_1011** | Chapter 1011 | JSON |
| Ikkaku | mangaDebut | Chapter_810, Chapter_915 | **Chapter_810** | Chapter 810 | JSON |
| Kaku | mangaDebut | Chapter_323, Chapter_927 | **Chapter_323** | Chapter 323 | JSON |
| Macro | mangaDebut | Chapter_197, Chapter_437 | **Chapter_197** | Chapter 197 | JSON |
| Mr_7 | mangaDebut | Chapter_190, Chapter_205 | **Chapter_190** | — | ⚠ earliest kept, review |
| Risky_Brothers | mangaDebut | Chapter_451, Chapter_475 | **Chapter_475** | Chapter 475 | JSON |
| Sora | mangaDebut | Chapter_608, Chapter_825 | **Chapter_608** | Chapter 608 | JSON |
| Bomba | animeDebut | Episode_589, Episode_641 | **Episode_641** | Episode 641 | JSON |
| Ganryu | animeDebut | Episode_461, Episode_968 | **Episode_461** | Episode 461 | JSON |
| Hack | animeDebut | Episode_275, Episode_633 | **Episode_633** | Episode 633 | JSON |
| Hanji | animeDebut | Episode_922, Episode_947 | **Episode_922** | Episode 922 | JSON |
| Hera | animeDebut | Episode_1028, Episode_633 | **Episode_1028** | Episode 1028 | JSON |
| Ikkaku | animeDebut | Episode_757, Episode_902 | **Episode_757** | Episode 757 | JSON |
| Kaku | animeDebut | Episode_230, Episode_919 | **Episode_230** | Episode 230 | JSON |
| Minatomo | animeDebut | Episode_51, Episode_892 | **Episode_51** | — | ⚠ earliest kept, review |
| Mr_7 | animeDebut | Episode_116, Episode_124 | **Episode_116** | — | ⚠ earliest kept, review |
| Risky_Brothers | animeDebut | Episode_344, Episode_369 | **Episode_369** | Episode 369 | JSON |
| Sora | animeDebut | Episode_527, Episode_783 | **Episode_527** | Episode 527 | JSON |

### Reasoning statistics before / after
| scenario | time (s) | inferred triples | domain-relevant inferred | non-reflexive `owl:sameAs` | example merge |
|---|---|---|---|---|---|
| A. upstream as-is, axioms kept, no guard | 12.0 | 38783 | 1565 | **48** | Chapter_966 = Chapter_552, Episode_344 = Episode_369 |
| B. earlier workaround: drop ALL functional axioms | 12.5 | 38458 | 1289 | 0 | - |
| **C. shipped: data patched, axioms kept** | 12.7 | 38418 | 1272 | **0** | - |

**Correction of an earlier claim.** An earlier note said OWL RL produced "19k sameAs triples merging chapters". That number counted reflexive `x owl:sameAs x`
triples, which are harmless. The real damage in scenario A is **48 merges between different chapters/episodes** (e.g. `Chapter_966 = Chapter_552`) and
293 spurious domain-relevant triples derived from them (equality substitution into `animeDebut` / `mangaDebut`).

## 2. SHACL vs OWL
`ontology/shapes.ttl` (checked with pyshacl at ingestion and in tests): `sh:maxCount 1` on both debut properties and `internalID`, `sh:minCount 1 label` (warning), Devil Fruit type (warning).

| graph | SHACL violations | warnings |
|---|---|---|
| upstream + extension (before patch) | **23** (one per conflicting subject/property) | 7 |
| patched (shipped) | **0** | 7 |

The same intent, two behaviours: OWL **infers** that two chapters are the same thing; SHACL **reports** that the data breaks the constraint. Ingestion fails if SHACL finds a violation on the shipped graph.

## 3. Other inconsistencies found
| issue | count | detail | cause | resolution |
|---|---|---|---|---|
| rdfs:inverseOf used instead of owl:inverseOf | 1 | hasBounty↔givenTo | typo in upstream schema (rdfs has no inverseOf), so the axiom is inert | documented; hasBounty/givenTo carry only 38 triples and are not used by the game |
| two namespaces for the same ontology (…/onepiece/ vs …/onepiece#) | 25 | 25 URIs in the '/' namespace, 0 of them also exist with '#' | upstream pipeline script builds URIs with '/' | URIs preserved verbatim (requirement); fruits there are normal game entities via their explicit rdf:type |
| op:DevilFruitType is an owl:oneOf enumeration of 3 individuals but data/extension use more | 2 | Artificial_Zoan, Special_Paramecia (+ opx:AncientZoan, opx:MythicalZoan from our extension) | closed enumeration vs. open-world data; a full DL reasoner would be forced to merge them with Paramecia/Zoan/Logia | OWL RL has no rule that does this (verified: 0 sameAs); documented, extension stays RL-safe |
| individuals typed as Character only by rdfs:domain/range inference (never asserted) | 13 | A_certain_doctor, Buzz, Gasparde, Honey_Queen, Simon, Unnamed_New_World_pirate, http://kalnassag.com/onepiece/ | range of op:hasDevilFruit / domain axioms applied to wiki placeholder names | such nodes keep the inferred label but are NOT game entities (category needs an asserted type) |

### 3a. Swapped domain/range of `op:inCrew` (fixed - patch `schema-increw`)
Upstream declares `op:inCrew owl:inverseOf op:hasCrewMember` yet gives **both** `rdfs:domain PirateCrew; rdfs:range Character`. For inverse properties the domain/range must swap, and the comment of `inCrew` ("the crew to which this pirate belongs") agrees with the data (`<character> inCrew <crew>`).
Effect before the patch: OWL RL typed characters as `PirateCrew` and `Straw_Hat_Pirates` as a `Character` (11 mistyped nodes in scenario A/B, 0 after). Fixed in `ontology/patches/schema-increw.*.ttl`.

### 3b. Broken fruit-user links (fixed - patch `uri-reconcile`, generated)
Five links point at an untyped URI that differs from a real Character only by a dot, e.g. `Gomu_Gomu_no_Mi DevilFruitCurrentUser Monkey_D._Luffy` (character is `Monkey_D_Luffy`).
Blackbeard (Yami Yami + Gura Gura), Trafalgar Law (Ope Ope) and Ace (previous Mera Mera user) therefore had **no Devil Fruit** in the graph, so the game would answer "Does your character possess a Devil Fruit?" wrongly for them. The 4 characters are matched by normalised name (exactly one typed twin required) and the links re-pointed; remaining untyped users (Buzz, Gasparde, Honey Queen, Simon, `…;_S-Bear` annotated names…) have no unambiguous twin and are left as they are (listed in the table above, not guessed).

### 3c. `owl:oneOf` on `op:DevilFruitType` - is it a real OWL 2 DL inconsistency? (investigated with HermiT)
**Exact axioms** (upstream schema): `op:DevilFruitType owl:equivalentClass [ owl:oneOf (op:Paramecia op:Zoan op:Logia) ]` and `op:hasFruitType rdfs:range op:DevilFruitType`.
Data that use other values: `Special_Paramecia`, `Artificial_Zoan` (upstream, 2 fruits) and `opx:AncientZoan`, `opx:MythicalZoan` (our extension). No distinctness axiom (`differentFrom`, `AllDifferent`, `disjointWith`) exists anywhere, and OWL has no unique-name assumption.

**Reasoning by hand:** by the range axiom `Special_Paramecia` is a `DevilFruitType`, i.e. a member of the enumeration, i.e. *equal to one of* Paramecia / Zoan / Logia. Without distinctness that is a satisfiable disjunction, **not** a contradiction. It becomes a contradiction only if the individuals are declared pairwise different.

**Demonstration** (`tools/hermit/`, HermiT (bundled with owlready2; version not pinned), a minimal slice = these axioms + every `hasFruitType` assertion of the data; reproducible with the commands in `tools/hermit/README.md`):
| scenario | upstream only | upstream + our extension |
|---|---|---|
| S1 as-is | consistent | consistent |
| S2 `Special_Paramecia differentFrom Paramecia, Zoan` | consistent | consistent |
| S3 `AllDifferent(Paramecia, Zoan, Logia)` | consistent | consistent |
| S4 `AllDifferent(every type individual used in the data)` | **inconsistent** | **inconsistent** |

**Verdict:** as published the ontology is *consistent* under OWL 2 DL; there is a **latent** inconsistency that appears as soon as anyone asserts that the five (or seven) fruit types are different things - which is what a modeller would naturally add. It exists in the upstream ontology alone (the extension is not the cause). OWL 2 RL, which we use, has no rule that turns class membership of an enumeration into `owl:sameAs` (0 merges, verified at every ingestion). Not modified: there is no observed failure, and upstream must stay untouched without evidence; the recommended upstream fix is to replace the closed enumeration by an open class (`opx:` subtypes already do this) - listed as an open decision.
Note: the S2 run did not display the forced merge (`Special_Paramecia = Logia`); that entailment is argued by hand above, not demonstrated.

## 4. Decisions that stay open
* Choosing "JSON value = debut" presumes the processed JSON is right; the 3 flagged subjects need a human look at the wiki.
* The closed `owl:oneOf` on `op:DevilFruitType`: latent inconsistency, see 3c. Not changed (no observed failure).
* `Buzz`, `Gasparde`, `Honey_Queen`, `Simon`, `A_certain_doctor` and `Unnamed_New_World_pirate` stay **unresolved** untyped nodes: no reliable source maps them to a character, they are not game entities and are covered by `test_unresolved_users_are_not_guessed`.
* Namespace split `…/onepiece/` vs `…/onepiece#` is preserved verbatim (requirement), not normalised.
