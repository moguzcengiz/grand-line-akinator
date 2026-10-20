# Ontology architecture, extensions and RDF → Neo4j mapping

## 1. Upstream ontology (verified, not assumed)
Source: <https://github.com/kalnassag/one-piece-ontology> (vendored unchanged in `ontology-src/`).
Namespace actually used by the data: `op: <http://kalnassag.com/onepiece#>`.
(The upstream `pipeline/entities_ingestion.py` uses `http://kalnassag.com/onepiece/` – a different namespace; ~16 Devil Fruit
individuals in the dataset also live there. We keep every URI verbatim.)

Loaded files: `onepiece-ontology.ttl` (schema, 337 triples), `one-piece-graph.ttl` (data, 33k triples), `OnePieceEntities-Base Model.ttl` (hand-curated Straw Hats, 842 triples).

Coverage (measured): 1,503 `op:Character`, 134 `op:DevilFruit`, 363 `op:Affiliation`, 665 `op:Occupation`.
Properties with real data: `affiliatesWith` (1.9k), `occupation` (2k), `statusOfCharacter`, `residence`, `placeOfOrigin`, `hasBloodType`, `height`, `age`, `hasFruitType` (134), `DevilFruitCurrentUser` (127), voice actors, debuts.
**Declared but empty**: `hasDevilFruit`, `race`, `inCrew`, `hasCrewMember`, `hasBounty` (only the 10-character base model uses them). **Missing entirely**: ships, Haki, pirate/marine/revolutionary typing, Ancient/Mythical Zoan.

## 2. Extensions (`ontology/extension.ttl`, namespace `opx: <http://kalnassag.com/onepiece-ext#>`)
| Need | Extension | OWL RL feature |
|---|---|---|
| Devil Fruit ownership | `DevilFruitCurrentUser owl:inverseOf op:hasDevilFruit` (the data only has fruit→user) | prp-inv |
| Pirate / Marine / Revolutionary / World Government affiliation | classes `opx:{Pirate,Marine,Revolutionary,WorldGovernment}Organization ⊑ op:Affiliation`; derived `opx:*AffiliatedCharacter` via `affiliatesWith someValuesFrom …` | cls-svf1 |
| Captain status | `op:occupation hasValue op:Captain / op:Pirate_Captain ⊑ opx:CaptainCharacter` | cls-hv2 |
| Devil Fruit user | `op:hasDevilFruit someValuesFrom op:DevilFruit ⊑ opx:DevilFruitUser` (fires on the *inferred* `hasDevilFruit`) | chained |
| Ancient / Mythical Zoan | `opx:AncientZoan`, `opx:MythicalZoan` (`subtypeOf op:Zoan`), `opx:hasFruitSubtype`; chain `hasFruitSubtype ∘ subtypeOf ⊑ op:hasFruitType` | prp-spo2 |
| Haki | `opx:hasHaki`, `opx:HakiType` (Armament, Observation, Conqueror's), derived `opx:HakiUser` | cls-svf1 |
| Ships | `opx:Ship`, `shipOwner`/`ownsShip` (inverse), `operatedBy`, `shipType`, `builtBy`, derived `opx:PirateShip`, `opx:ShipOwner` | cls-svf1, prp-inv |
| Species, roles, status, crew membership | **reused** from upstream (`race`, `occupation`, `statusOfCharacter`, `inCrew`) – no extension needed |

### Rule-derived typing (not LLM, not hand lists of characters) – `app/ontology.py::classify_affiliations`
* `*_Pirates` individuals of `op:Affiliation` → `PirateOrganization`, excluding names starting `Ally|Subordinate|Former|Fake|Prisoner|Retainer|Enemy|Member` and alliances.
* `Marines`, `Marine_Headquarters`, `*_Marine_Base` → Marine; `Revolutionary_Army`, `Freedom_Fighters` → Revolutionary; `World_Government`, `CP0`, `CP9`, `Seven_Warlords_of_the_Sea`, … → World Government. (Rules are heuristics; false negatives become *unknown*, never *false* – see §5.)

### Manually curated facts (`ontology/curated.ttl`) – the only hand-added lore
* **Haki** for 21 well-known characters (Luffy, Zoro, Shanks, Whitebeard, Big Mom, Kaido, Rayleigh, Roger, Sanji, Katakuri, Sakazuki, Borsalino, Garp, Doflamingo, Hancock, Law, Mihawk, Kid, Blackbeard, Crocodile, Jinbe, Kuzan). Only characters listed have a *known* Haki profile; everyone else is **unknown** (`haki_known` marker).
* **7 Ancient/Mythical Zoan fruits** (Phoenix, Daibutsu, Seiryu, Okuchi no Makami, Allosaurus, Brachiosaurus, Mammoth) with current users.
* **9 ships** (Going Merry, Thousand Sunny, Moby Dick, Red Force, Polar Tang, Oro Jackson, Queen Mama Chanter, Victoria Punk, Thriller Bark) with crew and owner; ship type only for Merry (caravel) and Polar Tang (submarine); builder only for Sunny (Franky) and Oro Jackson (Tom). Unrecorded facts stay absent = unknown.

## 3. Reasoning (RDFS + OWL 2 RL via `owlrl`) – and its limits
`owlrl.DeductiveClosure(OWLRL_Semantics)` runs over `base ∪ extension` (~35k triples, ~12 s). **This is not a full OWL 2 DL reasoner**; only the OWL 2 RL rule subset is applied.
Only triples whose predicate/class is domain-relevant are materialised (drops `owl:Thing`, reflexive `sameAs`, blank nodes).
Observed: 133 `hasDevilFruit`, 19 `previouslyHadDevilFruit`, 9 `ownsShip`, 7 `hasFruitType` (Ancient/Mythical → Zoan), ~1,100 inferred class memberships (e.g. 573 `PirateAffiliatedCharacter`, 124 `CaptainCharacter`, 22 `HakiUser`).

**Data-quality findings (details, numbers and per-subject decisions: [ONTOLOGY_AUDIT.md](ONTOLOGY_AUDIT.md)).**
1. `op:mangaDebut` / `op:animeDebut` are `owl:FunctionalProperty`, but 23 characters carry two values (the second is a later appearance mis-recorded as a debut). With the axiom kept OWL RL would **merge 48 pairs of different chapters/episodes via `owl:sameAs`**. The axiom is correct, the data is wrong, so the data is fixed in a patch layer (`ontology/patches/`) and the axiom is **kept**. SHACL (`ontology/shapes.ttl`, `sh:maxCount 1`) reports the original violations (23) and checks the patched graph (0).
2. `op:inCrew` has swapped domain/range (inverse of `hasCrewMember` with the same domain/range) - patched.
3. Five fruit-user links point at near-miss URIs (`Monkey_D._Luffy`) - patched, so Blackbeard/Law/Ace get their fruits.
Upstream files are never edited; every patch is a pair of reviewable `*.remove.ttl` / `*.add.ttl` files.

### Reasoning example
```
explicit:  op:Gomu_Gomu_no_Mi  op:DevilFruitCurrentUser  op:Monkey_D_Luffy
extension: op:DevilFruitCurrentUser owl:inverseOf op:hasDevilFruit
inferred:  op:Monkey_D_Luffy   op:hasDevilFruit  op:Gomu_Gomu_no_Mi          (prp-inv)
inferred:  op:Monkey_D_Luffy   a opx:DevilFruitUser                          (cls-svf1)
explicit:  op:Monkey_D_Luffy   op:affiliatesWith op:Straw_Hat_Pirates ;  rule: Straw_Hat_Pirates a opx:PirateOrganization
inferred:  op:Monkey_D_Luffy   a opx:PirateAffiliatedCharacter               (cls-svf1)
```
The game's question *"Does your character possess a Devil Fruit?"* is answered from the inferred class label – without reasoning the graph could not answer it.

## 4. RDF → Neo4j mapping (`app/ingestion.py`)
| RDF | Neo4j |
|---|---|
| any URI in the op/opx namespaces | `(:Resource {uri, local, name, name_ja, category, explicit_types, inferred_types})` – URI is unique-constrained and never rewritten |
| `rdf:type C` | extra label `C` (local name). Types derived by OWL RL are labels too, listed in `inferred_types`. Inferred `Character/DevilFruit/Ship` types do **not** create labels (so a user typed only by an `rdfs:range` is not a game entity) |
| `rdfs:label @en` / `@ja` | `name` / `name_ja` (fallback: prettified local name) |
| datatype property | node property (`height`, `age` → numeric scalar = max value; others string or list). `opwikiurl`, `internalID`… dropped |
| `Chapter_N` / `Episode_N` | derived property `number` |
| object property `p` | relationship `UPPER_SNAKE(p)` with `predicate` (full URI) and `provenance` |
| provenance | `explicit` (upstream triple) · `curated` (our extension/curated files or rule output) · `inferred` (owlrl only) – an explicit/curated triple that is also derivable stays explicit/curated |
| category | `Ship` > `DevilFruit` > `Character` explicit class → `category` |

The ingestion wipes and rebuilds the graph (deterministic, idempotent), validates counts/provenance, and stores a JSON report in `(:IngestionRun {id:'latest'})`, exposed at `/api/ontology/stats`.

## 5. Explicit / inferred / unknown
Each (question, entity) cell is **True / False / Unknown**. Missing facts are *not* automatically false:
* `scope: closed` – the graph is assumed complete for this question (Devil Fruit ownership, ship owner, categories). Absence = False (documented closed-world assumption).
* `scope: rel:R` – known only if the entity has ≥ 1 `R` edge (e.g. a character with no listed affiliation is *unknown* for every affiliation question).
* `scope: prop:P` – known only if the node has property `P` (Haki profile, height, age).
* A category a question does not apply to is *false* ("a Devil Fruit is not in the Marines") except numeric questions, where it is unknown.

## 6. Popularity signal (derived, not upstream)
The ontology has no popularity data. `popularity` is the node degree (in+out relationships) computed after import - a proxy for "how much the wiki says about this entity". Sanity check: top characters by it are Monkey D. Luffy, Nico Robin, Roronoa Zoro, Sanji, Nami, Jinbe, Franky, Buggy. Fruits and ships inherit their user's/owner's degree (+ their own). It only feeds the game's prior; it is never shown as lore.
