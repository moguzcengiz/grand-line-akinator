# Ontology constraints: what is missing, what the data allows, and what the guessing engine can derive

Read-only audit (no `.ttl` or code changed). Every number below was measured with the script in [§5](#5-reproduction-script), on
upstream + `ontology/extension.ttl` + `ontology/curated.ttl` + the patch layer (`ontology/patches/*`). This is the same loading path as ingestion (`app.ontology.load_sources()`, then `materialize()`).
The union has 34,717 triples, 75,445 after OWL RL. Tools: rdflib, owlrl 7.6.2, pyshacl.

**Why the game asks pointless questions.** The schema has **no** disjointness axioms, **no** `owl:differentFrom` between enumeration values, and only three functional
properties (`mangaDebut`, `animeDebut`, `internalID`). So an OWL reasoner cannot conclude that *Alive* excludes *Deceased* or that a *Logia* is not a *Zoan*. The
engine also scores answers probabilistically: after "living? yes", the Deceased candidates are only down-weighted (likelihood 0.98, not 0), so "deceased?"
keeps a small but non-zero information gain and can still be picked. Redundancy is handled by hard-coded concept tags instead (`questions.py`: `_LABEL_CONCEPT`,
`_OCCUPATION_CONCEPT`, `concepts()`; `engine.py`: `covered_concepts()`) and by the answer-correlation threshold `EQUIV_PHI`.

## 1. Summary

Ranked by impact on pointless questions. "Violations" = entities in the current data that break the constraint (measured, see §2).

| # | Constraint | Kind | OWL / SHACL | Data violations | Recommendation |
|---|---|---|---|---|---|
| C1 | Character, DevilFruit, Ship are pairwise disjoint | class disjointness | `owl:AllDisjointClasses` (cax-adc, clash only) + SHACL `sh:not` | **0** (but 2 ships are duplicated as `op:Character`: `Going_Merry`, `Queen_Mama_Chanter`) | **Add.** Patch the 2 ship twins |
| C2 | A character has one status; Alive ⟂ Deceased | functional property + distinct values + hasValue classes | `owl:FunctionalProperty`, `owl:differentFrom`, `opx:LivingCharacter ⟂ opx:DeceasedCharacter`; SHACL `maxCount 1`, `sh:in` | **7** characters with 2 statuses (4 Alive+Deceased, 3 Alive+Unknown); **2** ships with status Destroyed/Active | **Add after a data patch.** Without the patch, the functional axiom merges Alive = Deceased = Unknown (all 1,487 status-bearing characters get all three statuses) |
| C3 | A Devil Fruit has exactly one base type; Paramecia, Zoan and Logia are distinct | functional property + distinct values + exactly-one | `owl:FunctionalProperty`, `owl:differentFrom`; SHACL `minCount 1 maxCount 1 sh:in` | **0** fruits with 2 types (after RL). **2** fruits use off-enumeration values (`Mochi_Mochi_no_Mi` → `Special_Paramecia`, `SMILE` → `Artificial_Zoan`). **7** curated fruits have no asserted type (only inferred `Zoan`) | **Add.** Patch the 2 fruits to base type + subtype |
| C4 | Fruit subtype is single-valued; Ancient ⟂ Mythical Zoan | functional + distinct | `owl:FunctionalProperty`, `owl:differentFrom` | 0 | **Add**; re-type the subtypes as `opx:DevilFruitSubtype` (avoids the `owl:oneOf` trap, ONTOLOGY_AUDIT §3c) |
| C5 | A dead character holds no Devil Fruit (the fruit is released on death) | class disjointness | `opx:DeceasedCharacter owl:disjointWith opx:DevilFruitUser` | 0 | **Add** (eating a fruit in the past, `DevilFruitEater`, stays compatible) |
| C6 | A fruit has at most one current user | functional / inverse-functional | `DevilFruitCurrentUser` functional, `hasDevilFruit` inverse-functional | 0 | **Add**. **Not** `hasDevilFruit` functional: Blackbeard has 2 fruits |
| C7 | The current user and a previous user of the same fruit are different people | property disjointness | `owl:propertyDisjointWith` (prp-pdw, clash only) | 0 | **Add** |
| C8 | Character is disjoint with the value classes (Status, DevilFruitType, HakiType, ShipType, BloodType, Race, MangaIssue, AnimeEpisode, Arc, Bounty, schema:Person); DevilFruit, Ship, Occupation, Location, Status and DevilFruitType are pairwise disjoint | class disjointness | `owl:disjointWith`, `owl:AllDisjointClasses` | 0 | **Add** (mostly a data-quality guard; low game impact) |
| C9 | Occupation hierarchy (rank ⇒ broader role) | sub-property chain / hasValue | `opx:broaderOccupation` + existing chain; `hasValue` ⊑ class | existing 3 links: 0. Marine ranks ⇒ MarineAffiliated: 0 counter-examples among 78 holders of 19 rank occupations (would newly classify 11). Bare `op:Admiral`: unusable, 10 holders incl. Marshall_D_Teach (upstream error: he is not an admiral) and Orlumbus (fleet title) | **Add a curated list** (no lexical automation: 269 lexical candidates, only 22 already hold in the data). Exclude `Admiral`; patch Teach |
| C10 | Single-valued facts: blood type, race, ship owner, operating crew, ship type, age | functional | `owl:FunctionalProperty` / SHACL `maxCount 1` | 0 / 0 / 0 / 0 / 0 / 0 | **Add** (`age`: SHACL only, it is a datatype value that changes over time) |
| C11 | Pirate / Marine / Revolutionary / World Government affiliations are disjoint | class disjointness | — | 9 / 4 / 13 / 1 / 2 / 1 overlapping pairs (Koby, X_Drake, Sabo, Nico_Robin, Crocodile…) | **Do not add**: real overlaps (defectors, Warlords). The engine must **not** exclude these |
| C12 | Character ⟂ Affiliation, Affiliation ⟂ Location, Character ⟂ Occupation, Character ⟂ Location, Affiliation ⟂ Occupation | class disjointness | — | 42 / 37 / 1 (`King`) / 1 (`Sphinx`) / 1 (`Criminal`) | **Drop** for now: URI punning in upstream (one URI used both as a person and as an affiliation, a place and a group…); fixing it needs URI splitting |
| C13 | `placeOfOrigin` single-valued | functional | — | 5 (all are nested places, e.g. Luffy: Foosha_Village + East_Blue) | **Drop**; instead `placeOfOrigin ∘ locatedIn ⊑ placeOfOrigin` (only 3 `locatedIn` triples exist today) |
| C14 | `height` single-valued | functional | — | 8 (pre/post time-skip, Luffy 91 cm vs 172 cm) | **Drop**; SHACL warning at most |
| C15 | `ageAtDeath` ⇒ Deceased | hasValue implication | — | 1 (`Brook`, died and was revived: legitimate) | **Drop** |
| C16 | Conqueror's Haki ⇒ Armament Haki | subclass | — | 0 in the 22 curated profiles | **Do not add** (not a canon rule; at most a soft prior) |
| S1 | Schema/data defects found on the way | domain / range / typos | see §2.12 | 4 typo predicates, ship status, `citizenOf` range intersection, 13 placeholder fruit users typed Character only by range | Patch (§2.12) |

Two tooling facts matter for any implementation:
* **owlrl 7.6.2 `owl:AllDifferent` is broken**: rule eq-diff2/3 (`OWLRL.py` around l. 416) loops `j in range(i+1, len-1)`, so pairs involving the **last** list member are never checked.
  Measured: `AllDifferent(A B C)` + functional `status A, B` → clash; `status A, C` → **no clash**; `status B, C` → **no clash**. Use pairwise `owl:differentFrom` (eq-diff1 works).
  `owl:AllDisjointClasses` (cax-adc) is fine.
* **owlrl reports clashes as triples `[] a err:ErrorMessage ; err:error "…"` on a blank node.** `materialize()` returns them in `inferred`, but `is_domain_triple()` drops
  blank-node subjects. So with disjointness axioms added today, **every clash would be silently discarded**. Ingestion must collect `ERRNS.error` and fail on it, as it already does for SHACL.

What owlrl does with each axiom kind (each verified with a minimal probe):

| axiom | owlrl rule | effect |
|---|---|---|
| `rdfs:subClassOf`, `subPropertyOf`, `propertyChainAxiom`, `hasValue`, `someValuesFrom` (sub-class side), `inverseOf`, domain/range | cax-sco, prp-spo1/2, cls-hv1/2, cls-svf1, prp-inv, prp-dom/rng | **derives** new triples (positive implications) |
| `owl:FunctionalProperty`, `InverseFunctionalProperty`, `maxCardinality 1` | prp-fp, prp-ifp, cls-maxc2 | **derives `owl:sameAs`** between the two values; a clash only if the values are `differentFrom` (eq-diff1). Without `differentFrom` the values are silently merged |
| `owl:disjointWith`, `AllDisjointClasses`, `complementOf` | cax-dw, cax-adc, cls-com | **clash only** (error message), derives nothing |
| `owl:propertyDisjointWith` | prp-pdw | clash only |
| `owl:differentFrom` | eq-diff1 | clash only (with sameAs) |
| `owl:AllDifferent` | eq-diff2/3 | clash only, **buggy** (see above) |
| `owl:oneOf` | cls-oo | only types the listed members; never closes the class (no "must be one of") |
| exactly-one / `minCardinality` / existential on the super-class side | none (not OWL 2 RL) | nothing; use SHACL `sh:minCount` |

## 2. Details per constraint

Prefixes: `op: <http://kalnassag.com/onepiece#>`, `opx: <http://kalnassag.com/onepiece-ext#>`, `schema: <http://schema.org/>`. The Turtle below is the proposal that was
measured. It belongs in `ontology/extension.ttl`, and the data fixes belong in new `ontology/patches/*.{remove,add}.ttl` pairs.

### 2.1 C1: game categories are disjoint
```turtle
[] a owl:AllDisjointClasses ; owl:members ( op:Character op:DevilFruit opx:Ship ) .
```
* Data: 0 entities typed with two of the three, asserted or after RL.
* **Hidden duplicates:** upstream types `op:Going_Merry` and `op:Queen_Mama_Chanter` as `op:Character` (with `animeDebut`, `height`, and status `Destroyed` / `Active`).
  `curated.ttl` creates separate `opx:Going_Merry` / `opx:Queen_Mama_Chanter` ships. The game therefore has a **character** "Going Merry" and a **ship** "Going Merry".
  The axiom does not catch this because the URIs differ. Patch:
  ```turtle
  # patches/ship-twins.remove.ttl
  op:Going_Merry a op:Character .            op:Going_Merry op:statusOfCharacter op:Destroyed .
  op:Queen_Mama_Chanter a op:Character .     op:Queen_Mama_Chanter op:statusOfCharacter op:Active .
  # patches/ship-twins.add.ttl  (keep the upstream facts, merge the two URIs)
  op:Going_Merry owl:sameAs opx:Going_Merry .  op:Queen_Mama_Chanter owl:sameAs opx:Queen_Mama_Chanter .
  ```
  After that patch, C1 turns any future such duplicate into a clash.
* Implications: `statusOfCharacter`, `occupation`, `affiliatesWith`, `hasDevilFruit`, `hasHaki` … have `rdfs:domain op:Character`, so **every** answered character fact
  (prp-dom) makes the entity a Character. With C1, "Is it a Devil Fruit?" / "Is it a ship?" become **false** after "living character? yes" or "pirate captain? yes".
  Likewise `hasFruitType` (domain DevilFruit) and `shipType` / `operatedBy` / `shipOwner` (domain Ship) rule out the other two categories.
* SHACL equivalent (data check, no inference):
  ```turtle
  opx:CategoryDisjointShape a sh:NodeShape ; sh:targetClass op:Character ;
      sh:not [ sh:or ( [ sh:class op:DevilFruit ] [ sh:class opx:Ship ] ) ] .
  ```
  0 violations.

### 2.2 C2: one status per character; Alive ⟂ Deceased
```turtle
op:statusOfCharacter a owl:FunctionalProperty .
op:Alive owl:differentFrom op:Deceased .
opx:LivingCharacter   owl:equivalentClass [ a owl:Restriction ; owl:onProperty op:statusOfCharacter ; owl:hasValue op:Alive ] .
opx:DeceasedCharacter owl:equivalentClass [ a owl:Restriction ; owl:onProperty op:statusOfCharacter ; owl:hasValue op:Deceased ] .
opx:LivingCharacter owl:disjointWith opx:DeceasedCharacter .
```
Status values in the data: Alive 1,185, Unknown 166, Deceased 143, Destroyed 1, Active 1. 14 characters have no status.

| scenario (owlrl over all data + proposed axioms) | clashes | new non-reflexive `sameAs` | status counts after closure |
|---|---|---|---|
| A. axioms as above, data unpatched | 1,619 | Alive = Deceased = Unknown | Alive / Deceased / Unknown: **1,487 each** (was 1,185 / 143 / 166) |
| B. same without the functional axiom | **4** (Cerberus, Hack, Mr_7, Risky_Brothers) | 0 | unchanged |
| C. axioms + status patch below | **0** | 0 | 1,181 / 139 / 163 |

Scenario A shows why `materialize()`'s guard (drop the functional axiom when the data violates it) is necessary. The status patch must come first.

Violators (7):

| character | statuses | note |
|---|---|---|
| Cerberus, Hack, Mr_7, Risky_Brothers | Alive + Deceased | all four are also in the 23 **double-debut** cases of ONTOLOGY_AUDIT §1 |
| Ganryu, Hera, Ikkaku | Alive + Unknown | same, also double-debut cases |

**Surprising:** all 7 double-status characters are among the 23 debut conflicts. Two conflicting debuts *and* two conflicting statuses on one URI point to **two different wiki
characters merged under one name**, not to "a later appearance recorded as a debut" (the explanation ONTOLOGY_AUDIT §1 gives for all 23). The debut decision for these 7 should be reviewed.
Patch proposal: remove `op:Unknown` where a real status exists (3 triples). For the 4 Alive+Deceased, remove both values (status becomes unknown) until the records are split.

On **`op:Unknown`**: it is an epistemic marker ("the wiki does not know"), not a state of the world, so it is deliberately **not** made `differentFrom` Alive. Today's engine
already treats it as unknown (`scope: status`). Cleaner: remove all 166 `statusOfCharacter op:Unknown` triples in a patch (absence = unknown). Also, `op:Unknown` is typed
`schema:Person` (it is reused as a voice-actor placeholder), which C8 would flag.
`Destroyed` / `Active` are ship states. Move them to a new `opx:shipStatus` (domain `opx:Ship`) with the C1 patch.

SHACL:
```turtle
opx:CharacterStatusShape a sh:NodeShape ; sh:targetClass op:Character ;
    sh:property [ sh:path op:statusOfCharacter ; sh:maxCount 1 ; sh:in ( op:Alive op:Deceased op:Unknown ) ] .
```
Measured: 7 `maxCount` violations (the list above) and 2 `sh:in` violations (Going_Merry `Destroyed`, Queen_Mama_Chanter `Active`).

### 2.3 C3 / C4: Devil Fruit type
```turtle
op:hasFruitType a owl:FunctionalProperty .
op:Paramecia owl:differentFrom op:Zoan, op:Logia .  op:Zoan owl:differentFrom op:Logia .
opx:hasFruitSubtype a owl:FunctionalProperty .
opx:AncientZoan owl:differentFrom opx:MythicalZoan .
# avoid the closed owl:oneOf on op:DevilFruitType (ONTOLOGY_AUDIT 3c): subtypes get their own class
opx:DevilFruitSubtype a owl:Class .   opx:hasFruitSubtype rdfs:range opx:DevilFruitSubtype .
opx:AncientZoan a opx:DevilFruitSubtype .  opx:MythicalZoan a opx:DevilFruitSubtype .   # instead of "a op:DevilFruitType"
```
* After RL: Paramecia 92, Zoan 31, Logia 16, Special_Paramecia 1, Artificial_Zoan 1 (141 fruits). **0** fruits with two types and **0** fruits without one.
  (The 7 curated Ancient/Mythical fruits get `Zoan` only through the `hasFruitSubtype ∘ subtypeOf` chain.)
* With the axioms: 0 clashes, 0 merges (scenario C).
* Off-enumeration values: **2** fruits. Patch so the base type stays in {Paramecia, Zoan, Logia} and the detail moves to the subtype:
  ```turtle
  # remove
  op:Mochi_Mochi_no_Mi op:hasFruitType op:Special_Paramecia .   op:SMILE op:hasFruitType op:Artificial_Zoan .
  # add
  opx:SpecialParamecia a opx:DevilFruitSubtype ; opx:subtypeOf op:Paramecia .
  opx:ArtificialZoan   a opx:DevilFruitSubtype ; opx:subtypeOf op:Zoan .
  op:Mochi_Mochi_no_Mi opx:hasFruitSubtype opx:SpecialParamecia .  op:SMILE opx:hasFruitSubtype opx:ArtificialZoan .
  ```
  The existing chain then derives `hasFruitType Paramecia` / `Zoan`. That also removes the latent `owl:oneOf` inconsistency of ONTOLOGY_AUDIT §3c.
* "Exactly one type" is **not expressible in OWL RL** (minCardinality is not RL). Use SHACL:
  ```turtle
  opx:FruitTypeExactlyOneShape a sh:NodeShape ; sh:targetClass op:DevilFruit ;
      sh:property [ sh:path op:hasFruitType ; sh:minCount 1 ; sh:maxCount 1 ; sh:in ( op:Paramecia op:Zoan op:Logia ) ] .
  ```
  On the asserted graph this reports 7 `minCount` violations (the 7 curated Ancient/Mythical fruits, which are typed only by inference) and 2 `sh:in` violations (the 2 fruits above).
  So either run this shape on the **reasoned** graph, or also state `op:hasFruitType op:Zoan` in `curated.ttl`.
* Fruit level only: "Logia? yes" ⇒ Zoan false and Paramecia false. Exactly-one (SHACL) adds: "Logia? no" and "Zoan? no" ⇒ Paramecia **true**.
* **Not** at character level: "Does your character eat a Logia?" yes does **not** exclude Paramecia, because `hasDevilFruit` is not functional (Marshall_D_Teach: Yami_Yami_no_Mi Logia +
  Gura_Gura_no_Mi Paramecia). The derivation in §3 gets this right automatically.

### 2.4 C5: dead characters hold no fruit
```turtle
opx:DeceasedCharacter owl:disjointWith opx:DevilFruitUser .
```
0 deceased current users (the 123 clashes in scenario A were all produced by the Alive = Deceased merge, and disappear in B and C). Ace and Whitebeard are `DevilFruitPreviousUser`, so they stay
`DevilFruitEater` and "Has your character eaten a Devil Fruit?" stays open. Implication: "deceased? yes" ⇒ "currently has a Devil Fruit / eats a Logia/Zoan/…" false.

### 2.5 C6 / C7: fruit ownership
```turtle
op:DevilFruitCurrentUser a owl:FunctionalProperty .          # 0 fruits with 2 current users
op:hasDevilFruit a owl:InverseFunctionalProperty .           # same fact seen from the character
op:DevilFruitCurrentUser owl:propertyDisjointWith op:DevilFruitPreviousUser .   # 0 violations
```
* `hasDevilFruit` must **not** be functional: 1 counter-example (Marshall_D_Teach, 2 fruits).
* `DevilFruitPreviousUser` has max 1 value per fruit in the data, but a fruit can canonically have many previous users, so it is not functional.
* 0 characters are the current user of one fruit and a previous user of another.
* 13 fruit users are untyped placeholders (`Buzz`, `Gasparde`, `Boa_Hancock;_S-Snake`, `Gifters;_Various_people`, …) that become `op:Character` only through `rdfs:range`
  (already in ONTOLOGY_AUDIT §3). With functional `DevilFruitCurrentUser`, a future second user would *merge* two people via `sameAs`, so keep the SHACL `maxCount 1` as the guard:
  ```turtle
  opx:FruitTypeExactlyOneShape sh:property [ sh:path op:DevilFruitCurrentUser ; sh:maxCount 1 ; sh:class op:Character ] .
  ```

### 2.6 C8: Character vs value classes
```turtle
op:Character owl:disjointWith op:Status, op:DevilFruitType, opx:HakiType, opx:ShipType, op:BloodType, op:Race,
    op:MangaIssue, op:AnimeEpisode, op:Arc, op:Bounty, schema:Person .
[] a owl:AllDisjointClasses ; owl:members ( op:DevilFruit opx:Ship op:Occupation op:Location op:Status op:DevilFruitType ) .
```
0 clashes after RL. `schema:Person` = voice actors / live-action actors (1,325 after RL), 0 overlap with Character.
Other punning found among value classes (not covered by the axioms above): `op:Unknown` is Status ∧ schema:Person, `Episode_8` is AnimeEpisode ∧ schema:Person, `NA` is Affiliation ∧ schema:Person,
and `Colleen_Clinkenbeard` is typed both `op:Person` and `schema:Person` (two Person classes exist). These are data-quality issues, not game issues.

### 2.7 C9: occupation hierarchy (positive implications)
Existing (curated.ttl + the chain `op:occupation owl:propertyChainAxiom (op:occupation opx:broaderOccupation)`): Pirate_Captain ⇒ Pirate and Captain, Pirate_Officer ⇒ Pirate.
Measured: 60 Pirate_Captain holders, **0** of them missing `CaptainCharacter` or `PirateAffiliatedCharacter`. Occupation Pirate ⇔ PirateAffiliatedCharacter (both 642) through the
`hasValue` pair in extension.ttl. Captain = CaptainCharacter (125).

Missing, proposed as a curated list (not lexical: 269 name-containment candidates, of which only 22 already hold in the data, and many are wrong, e.g. `Slave_trader → Slave`,
`Pretend_Pirate → Pirate`):
```turtle
# Marine ranks => Marine-affiliated (cls-hv2). 19 occupations: Marine_* , Vice_Admiral, Rear_Admiral, Fleet_Admiral
[ a owl:Restriction ; owl:onProperty op:occupation ; owl:hasValue op:Vice_Admiral ] rdfs:subClassOf opx:MarineAffiliatedCharacter .
# ... one line per rank (generate from the list in the script output) ...
op:Marine_Rear_Admiral opx:broaderOccupation op:Rear_Admiral .   # same pattern for rank synonyms
```
Measured: 78 holders of the 19 ranks. 11 of them are not yet MarineAffiliated (Akehende, Attach, Isuka, Kadar, Lacroix, Lines, Lonz, Momonga, Ripper, Stalker, Zotto): the axiom
would classify them; these are not violations. **Exclude bare `op:Admiral`**. Its 10 holders are Aramaki, Borsalino, Issho, Kong, Kuzan, Sakazuki, Sengoku (Marine admirals or
former admirals), Mont_Blanc_Noland (a Lvneel naval admiral, not a Marine), Orlumbus (admiral of the Yonta Maria fleet, a pirate title) and **Marshall_D_Teach**. Teach is **not** an admiral of
any kind: upstream `one-piece-graph.ttl` asserts `op:Marshall_D_Teach op:occupation op:Admiral, op:Apprentice, op:Emperor, op:Pirate, op:Warlord_of_the_Sea`, which is an upstream data
error and should be removed in a patch (`patches/teach-admiral.remove.ttl`). Even after that patch, bare `Admiral` cannot imply Marine (Orlumbus, Noland).
Open modelling decision: `Marine_Captain` (10 holders) is a rank, not a ship captain, and is not `CaptainCharacter` today. Decide what "Is your character a captain?" means before linking it.

### 2.8 C10: single-valued facts
```turtle
op:hasBloodType a owl:FunctionalProperty .  op:race a owl:FunctionalProperty .
opx:shipOwner a owl:FunctionalProperty .   opx:operatedBy a owl:FunctionalProperty .  opx:shipType a owl:FunctionalProperty .
opx:Caravel owl:differentFrom opx:Submarine .
# blood types / races also need their values pairwise differentFrom: mark the class once (opx:ClosedEnumeration) and generate them, see §3.3
```
Multi-valued subjects: hasBloodType 0, race 0 (only 10 characters have a race), shipOwner 0, operatedBy 0, shipType 0, age 0. The 6 blood-type values include
`BloodType_Bas_XAnd_XFKerville_F` (a mangled value: one character).

### 2.9 C11 / C12: disjointness that the data refutes (do not add)
| pair | overlap | examples |
|---|---|---|
| PirateAffiliated & MarineAffiliated | 9 | Bomba, Caesar_Clown, Diez_Barrels, Donquixote_Rosinante, Jango, Koby, Kuzan, Vergo, X_Drake |
| PirateAffiliated & RevolutionaryAffiliated | 4 | Koala, Morley, Nico_Robin, Sabo |
| PirateAffiliated & WorldGovernmentAffiliated | 13 | Boa_Hancock, Buggy, Crocodile, Doflamingo, Mihawk, Moria, Jinbe, Teach, Law, … |
| MarineAffiliated & RevolutionaryAffiliated | 1 | Monkey_D_Dragon |
| MarineAffiliated & WorldGovernmentAffiliated | 2 | Donquixote_Rosinante, Kong |
| RevolutionaryAffiliated & WorldGovernmentAffiliated | 1 | Bartholomew_Kuma |
| Character & Affiliation | 42 | Brook, Caesar_Clown, Crocus, Gol_D_Roger, Nico_Robin, … (people used as an affiliation target) |
| Affiliation & Location | 37 | Arabasta, Dressrosa, Water_7, Impel_Down, … |
| Character & Occupation / Location; Affiliation & Occupation | 1 / 1 / 1 | King, Sphinx, Criminal |

These are real (defectors, Warlords) or URI punning, so the affiliation questions must stay independent. "Pirate? yes" says nothing about "Marine?".

### 2.10 C13–C16: rejected or soft
* `placeOfOrigin`: 5 multi-valued (Jinbe: Fish_Man_Island + Grand_Line, Luffy: East_Blue + Foosha_Village, Nami, Chopper, Usopp). They are nested places, so the right axiom is
  `op:placeOfOrigin owl:propertyChainAxiom ( op:placeOfOrigin op:locatedIn )`, which needs `locatedIn` data (3 triples today).
* `height`: 8 multi-valued (time-skip). `ageAtDeath ⇒ Deceased`: 1 counter-example (Brook). Conqueror's ⇒ Armament: 0 counter-examples in 22 curated profiles, but not canon.

### 2.11 Implementation note: clashes must be surfaced
Add to `materialize()` / ingestion: `errors = [str(o) for o in work.objects(None, owlrl.Namespaces.ERRNS.error)]`, then report them and fail validation, as is done for SHACL.
Without this, C1–C8 detect nothing visible.

### 2.12 S1: schema / data defects found while enumerating
| defect | count | detail | fix |
|---|---|---|---|
| typo predicates | 4 | `op:hasdevilFruit` (Luffy), `op:affilatesWith` (Koby → Marines), `op:DevilFruitDebutManga` / `DevilFruitDebutAnime` (Gomu_Gomu_no_Mi; schema has lower-case `devilFruitDebut*`) | patch to the declared property. Koby is MarineAffiliated anyway via `Marines_Marine153rd_Branch` |
| `statusOfCharacter` used on ships | 2 | domain `op:Character` forces ships into Character | `opx:shipStatus` (C1 patch) |
| `citizenOf rdfs:range op:Kingdom, op:Island` | 1 use | two ranges = intersection, so `Goa_Kingdom` is inferred to be an Island | range `op:Location` (or `owl:unionOf`, not RL-derivable) |
| range not asserted on objects | e.g. 17/24 `devilFruitDebutManga` objects, 3/3 `arcEndAnime`, 6/670 occupations, 10/133 current users | harmless (prp-rng types them), but it is where punning comes from | none needed |
| `hasBounty rdfs:inverseOf` | 1 | already in ONTOLOGY_AUDIT §3 | — |

## 3. Question-level implications

### 3.1 Derivation (generic, no per-question code)
Every bank question is a fact pattern about the hidden entity `?x`. A `QuerySpec` path compiles to a basic graph pattern:
`start` → `?x a <Category>`, each step → `?n_i <predicate> ?n_{i+1}` (the predicate URI is stored on every imported relationship), `cond.uri` → the last node is that URI,
and `cond.label` → `?last a <Class>`. The ontology then answers three questions per pair (F, G), with F the answered fact:

| answer to F | G becomes | test (owlrl over **TBox only** + a fresh individual) |
|---|---|---|
| yes | **true** | `TBox + F(x) ⊨ G(x)`: one forward closure per F, then `ASK G` |
| yes | **false** | `TBox + F(x) + G(x)` produces a clash (disjointness, functional + differentFrom, propertyDisjointWith) |
| no | **false** | contrapositive: `YES(G) ⇒ F true` |
| no | **true** | only from closed enumerations (SHACL `minCount 1` + `sh:in`): if all other values are false, the last one is true (fruit base type). Not OWL RL |

Rules for composite questions (`mode: any` = OR of paths, `mode: all` = AND):
* AND yes ⇒ every conjunct yes; a conjunct no ⇒ AND no.
* OR no ⇒ every disjunct no; a disjunct yes ⇒ OR yes.
* OR yes / AND no ⇒ nothing (unless only one branch remains possible).

Existential nodes (`?f` in "eats a Logia") get a **fresh** node per fact, so two fruit facts never share a fruit. This is exactly why "eats Logia" and "eats Paramecia" are
*not* exclusive (Blackbeard), while "fruitType=Logia" and "fruitType=Paramecia" on the same fruit are.

Cost (measured): the TBox (upstream schema + extension + curated + proposal) is 694 triples, one closure takes about 0.3 s, and the 28-fact table below took about 110 s with full pairwise closures.
For a full bank (N questions), compute the N per-fact closures once. Then decide "false" without more closures by checking the union of two closures for a clash signature:
a pair of disjoint types, two `differentFrom` values of one functional property, or a pair of disjoint properties. That is set intersection over precomputed sets, done at bank-build time.
In-game, a question whose value is already decided by the hard yes/no answers so far is skipped (or its truth row is clamped). "Probably" answers should not trigger hard implications.

This replaces `_LABEL_CONCEPT` / `_OCCUPATION_CONCEPT` / `concepts()` / `covered_concepts()`, the hard-coded `("Alive", "Deceased")` status handling, and most of what `EQUIV_PHI` approximates
from answer correlations. The re-worded pirate/captain questions fall out of the hasValue/chain axioms, and the category questions fall out of domain + C1.

### 3.3 What is generic and what is still hand-written
The goal is **no per-question or per-value code in the engine**. Where knowledge still has to be stated, it is stated once in the ontology (declarative data), not in Python:

| piece | where it lives | per-question / per-value code? |
|---|---|---|
| implication derivation (§3.1): compile `QuerySpec` → pattern, closure, clash check | engine, ~50 lines, written once | **none**: it works for any question the generator or the LLM produces, including future relations |
| the `FACTS` dict in the script (§5) | test fixture only | a hand-picked sample to *demonstrate* the derivation; the engine would build facts from the bank's `QuerySpec`s instead |
| disjointness, functional, hasValue, chain axioms (C1–C10) | `extension.ttl` | one axiom per **class or property**, not per question |
| pairwise `owl:differentFrom` between enumeration values | `extension.ttl` | avoidable: mark the enumeration once (`op:Status a opx:ClosedEnumeration`) and generate the pairwise triples at load time with one generic SPARQL `CONSTRUCT { ?a owl:differentFrom ?b } WHERE { ?e a opx:ClosedEnumeration . ?a a ?e . ?b a ?e . FILTER(?a != ?b) }`. Needed only because owlrl's `owl:AllDifferent` is buggy |
| which ranks imply Marine, which occupation is broader than which (C9) | `curated.ttl` | yes, a **curated fact list**: this is world knowledge (Teach / Orlumbus show the names alone cannot be trusted), not engine logic |
| data fixes (status conflicts, ship twins, Teach's `Admiral`, typos) | `ontology/patches/` | per-fact by nature; reviewable remove/add pairs, as today |

So the engine needs no special cases. The remaining hand-written parts are ontology facts and patches, which can be reviewed, tested by SHACL, and which change no code.

### 3.2 Derived table (28 facts, TBox + proposed axioms)
Before the proposal: 46 "yes ⇒ true" and **0** "yes ⇒ false" pairs. After: 46 "yes ⇒ true" and **438** "yes ⇒ false" pairs (counted per ordered pair).
Abbreviations: *char-only* = {Captain(class), PirateAffiliated, MarineAffiliated, DevilFruitUser, DevilFruitEater, HakiUser, haki=Conquerors, occ=*, status=*, eats *};
*fruit-only* = {fruitType=*, fruitSub=*}; *ship-only* = {PirateShip, shipType=*}.

| answered YES | known TRUE | known FALSE |
|---|---|---|
| cat=Character | — | cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| cat=DevilFruit | — | cat=Character, cat=Ship, char-only, ship-only |
| cat=Ship | — | cat=Character, cat=DevilFruit, char-only, fruit-only |
| status=Alive | cat=Character | status=Deceased, cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| status=Deceased | cat=Character | status=Alive, DevilFruitUser, eats Paramecia/Logia/Zoan/MythicalZoan, cat=DevilFruit, cat=Ship, fruit-only, ship-only (DevilFruitEater stays open) |
| occ=Pirate_Captain | cat=Character, occ=Captain, occ=Pirate, Captain(class), PirateAffiliated | cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| occ=Pirate_Officer | cat=Character, occ=Pirate, PirateAffiliated | cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| occ=Pirate / PirateAffiliated | cat=Character, PirateAffiliated / occ=Pirate | cat=DevilFruit, cat=Ship, fruit-only, ship-only (**not** MarineAffiliated) |
| occ=Captain / Captain(class) | cat=Character, Captain(class) | cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| haki=Conquerors | cat=Character, HakiUser | cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| DevilFruitUser | cat=Character | status=Deceased, cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| eats Logia | cat=Character, DevilFruitUser, DevilFruitEater | status=Deceased, cat=DevilFruit, cat=Ship, fruit-only, ship-only (**not** eats Paramecia/Zoan) |
| eats MythicalZoan | cat=Character, DevilFruitUser, DevilFruitEater, eats Zoan | status=Deceased, cat=DevilFruit, cat=Ship, fruit-only, ship-only |
| fruitType=Logia | cat=DevilFruit | fruitType=Paramecia, fruitType=Zoan, fruitSub=*, cat=Character, cat=Ship, char-only, ship-only |
| fruitType=Zoan | cat=DevilFruit | fruitType=Paramecia, fruitType=Logia, cat=Character, cat=Ship, char-only, ship-only (fruitSub=* stays open) |
| fruitSub=MythicalZoan | cat=DevilFruit, fruitType=Zoan | fruitSub=AncientZoan, fruitType=Paramecia, fruitType=Logia, cat=Character, cat=Ship, char-only, ship-only |
| PirateShip | cat=Ship | cat=Character, cat=DevilFruit, char-only, fruit-only |
| shipType=Caravel | cat=Ship | shipType=Submarine, cat=Character, cat=DevilFruit, char-only, fruit-only |

| answered NO | known FALSE (contrapositive) |
|---|---|
| cat=Character | every char-only fact |
| cat=DevilFruit | every fruit-only fact |
| cat=Ship | every ship-only fact |
| occ=Pirate / PirateAffiliated | occ=Pirate_Captain, occ=Pirate_Officer, PirateAffiliated / occ=Pirate |
| occ=Captain / Captain(class) | occ=Pirate_Captain (+ Captain(class) / occ=Captain) |
| DevilFruitUser / DevilFruitEater | eats Paramecia/Logia/Zoan/MythicalZoan |
| HakiUser | haki=Conquerors |
| fruitType=Zoan / eats Zoan | fruitSub=Mythical/AncientZoan / eats MythicalZoan |
| status=Alive | — (status may be unknown; no closed-world exclusion) |

Machine-usable form (one entry of the JSON the script prints for every fact):
```json
"status=Deceased": {"yes_true": ["cat=Character"],
  "yes_false": ["DevilFruitUser", "PirateShip", "cat=DevilFruit", "cat=Ship", "eats Logia", "eats MythicalZoan", "eats Paramecia", "eats Zoan",
                "fruitSub=AncientZoan", "fruitSub=MythicalZoan", "fruitType=Logia", "fruitType=Paramecia", "fruitType=Zoan", "shipType=Caravel", "shipType=Submarine", "status=Alive"],
  "no_false": []}
```

## 4. Recommended order
1. Surface owlrl clashes in ingestion (§2.11). Without this nothing below is observable.
2. Patches: status conflicts (7), ship twins + ship status (2), fruit subtypes (2), typo predicates (4), Teach's `op:Admiral` occupation (1).
3. Axioms C1–C8, C10 (0 violations after step 2). SHACL shapes for exactly-one fruit type, status `maxCount`/`sh:in`, and category disjointness.
4. Curated Marine-rank list (C9).
5. Replace the concept tags with the derived implication table (§3), computed at bank-build time from the TBox.

## 5. Reproduction script
Read-only; prints sections [1]–[6]. Measured run: 295 s (of which the implication tables take 221 s).
`.venv/bin/python constraints_audit.py` (saved anywhere; it imports `backend/app` for the exact ingestion loading path and patch layer).

```python
"""Constraint audit for the One Piece ontology (read-only).  Run from anywhere:
    .venv/bin/python constraints_audit.py            (~2.5 min; repo root hard-coded in R)
Sections: [1] census  [2] cardinality / exclusivity checks  [3] class overlaps  [4] owlrl run with the proposed axioms
          [5] SHACL run with the proposed shapes  [6] generic implication table derived from the axioms."""
import itertools, json, os, re, sys, time
from collections import Counter, defaultdict
import owlrl
from pyshacl import validate
from rdflib import Graph, Namespace, OWL, RDF, RDFS, URIRef

R = "/Users/work/Desktop/ssw/"
sys.path.insert(0, R + "backend")
from app.ontology import load_sources, materialize, OP, OPX          # same loading + patch layer as ingestion

SDO = Namespace("http://schema.org/")
ERR = owlrl.Namespaces.ERRNS.error
L = lambda u: str(u).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
CLOSE = lambda g: owlrl.DeductiveClosure(owlrl.OWLRL_Semantics, axiomatic_triples=False, datatype_axioms=False).expand(g)

PROPOSED = """
@prefix op: <http://kalnassag.com/onepiece#> . @prefix opx: <http://kalnassag.com/onepiece-ext#> .
@prefix owl: <http://www.w3.org/2002/07/owl#> . @prefix schema: <http://schema.org/> .
[] a owl:AllDisjointClasses ; owl:members ( op:Character op:DevilFruit opx:Ship ) .
op:Character owl:disjointWith op:Status, op:DevilFruitType, opx:HakiType, opx:ShipType, op:BloodType, op:Race,
    op:MangaIssue, op:AnimeEpisode, op:Arc, op:Bounty, schema:Person .
[] a owl:AllDisjointClasses ; owl:members ( op:DevilFruit opx:Ship op:Occupation op:Location op:Status op:DevilFruitType ) .
op:statusOfCharacter a owl:FunctionalProperty .
op:Alive owl:differentFrom op:Deceased .
opx:LivingCharacter   owl:equivalentClass [ a owl:Restriction ; owl:onProperty op:statusOfCharacter ; owl:hasValue op:Alive ] .
opx:DeceasedCharacter owl:equivalentClass [ a owl:Restriction ; owl:onProperty op:statusOfCharacter ; owl:hasValue op:Deceased ] .
opx:LivingCharacter owl:disjointWith opx:DeceasedCharacter .
op:hasFruitType a owl:FunctionalProperty . opx:hasFruitSubtype a owl:FunctionalProperty .
op:Paramecia owl:differentFrom op:Zoan, op:Logia . op:Zoan owl:differentFrom op:Logia .
opx:AncientZoan owl:differentFrom opx:MythicalZoan .
op:DevilFruitCurrentUser a owl:FunctionalProperty . op:hasDevilFruit a owl:InverseFunctionalProperty .
op:DevilFruitCurrentUser owl:propertyDisjointWith op:DevilFruitPreviousUser .
opx:DeceasedCharacter owl:disjointWith opx:DevilFruitUser .
op:hasBloodType a owl:FunctionalProperty . op:race a owl:FunctionalProperty .
opx:shipOwner a owl:FunctionalProperty . opx:operatedBy a owl:FunctionalProperty . opx:shipType a owl:FunctionalProperty .
opx:Caravel owl:differentFrom opx:Submarine .
"""
SHAPES = """
@prefix sh: <http://www.w3.org/ns/shacl#> . @prefix op: <http://kalnassag.com/onepiece#> . @prefix opx: <http://kalnassag.com/onepiece-ext#> .
opx:FruitTypeExactlyOneShape a sh:NodeShape ; sh:targetClass op:DevilFruit ;
    sh:property [ sh:path op:hasFruitType ; sh:minCount 1 ; sh:maxCount 1 ; sh:in ( op:Paramecia op:Zoan op:Logia ) ] ;
    sh:property [ sh:path op:DevilFruitCurrentUser ; sh:maxCount 1 ; sh:class op:Character ] .
opx:CharacterStatusShape a sh:NodeShape ; sh:targetClass op:Character ;
    sh:property [ sh:path op:statusOfCharacter ; sh:maxCount 1 ; sh:in ( op:Alive op:Deceased op:Unknown ) ] ;
    sh:property [ sh:path op:hasBloodType ; sh:maxCount 1 ] ; sh:property [ sh:path op:race ; sh:maxCount 1 ] .
opx:ShipShape a sh:NodeShape ; sh:targetClass opx:Ship ; sh:property [ sh:path opx:shipOwner ; sh:maxCount 1 ] ;
    sh:property [ sh:path opx:operatedBy ; sh:maxCount 1 ] ; sh:property [ sh:path opx:shipType ; sh:maxCount 1 ] .
opx:CategoryDisjointShape a sh:NodeShape ; sh:targetClass op:Character ; sh:not [ sh:or ( [ sh:class op:DevilFruit ] [ sh:class opx:Ship ] ) ] .
"""


def multi(g, p):
    d = defaultdict(set)
    for s, _, o in g.triples((None, p, None)):
        d[s].add(o)
    return {s: v for s, v in d.items() if len(v) > 1}


def show(title, items, k=20):
    items = sorted(items, key=str)
    print(f"  {title}: {len(items)}" + (f"  {items[:k]}" if items else ""))


base, ext = load_sources()
U = base + ext
inf, dropped = materialize(U)
F = U + inf
print("[1] census  union triples", len(U), "| after OWL RL", len(F), "| functional axioms dropped:", dropped)
for c, n in Counter(o for o in U.objects(None, RDF.type) if not str(o).startswith((str(OWL), str(RDFS)))).most_common():
    print(f"    class {L(c):32} asserted {n:5}  after RL {len(set(F.subjects(RDF.type, c)))}")
for p, n in Counter(p for _, p, _ in U if p != RDF.type and not str(p).startswith((str(OWL), str(RDFS)))).most_common():
    per = defaultdict(set)
    for s, _, o in U.triples((None, p, None)):
        per[s].add(o)
    print(f"    prop  {L(p):28} {n:5} subj={len(per):5} max={max(map(len, per.values())):3} multi={sum(len(v) > 1 for v in per.values())}")

print("\n[2] exclusivity / cardinality")
print("  status values:", dict(Counter(L(o) for o in U.objects(None, OP.statusOfCharacter))))
show("characters with >1 status", [(L(s), sorted(map(L, v))) for s, v in multi(U, OP.statusOfCharacter).items()])
show("status on non-character-like nodes", [(L(s), L(o)) for s, o in U.subject_objects(OP.statusOfCharacter) if L(o) in ("Destroyed", "Active")])
print("  fruit types after RL:", dict(Counter(L(o) for o in F.objects(None, OP.hasFruitType))))
show("fruits with >1 type after RL", [L(s) for s in multi(F, OP.hasFruitType)])
show("characters with >1 current fruit", [(L(s), sorted(map(L, v))) for s, v in multi(F, OP.hasDevilFruit).items()])
show("fruits with >1 current user", [L(s) for s in multi(F, OP.DevilFruitCurrentUser)])
show("current user is also previous user of same fruit", [(L(f), L(u)) for f, u in F.subject_objects(OP.DevilFruitCurrentUser) if (f, OP.DevilFruitPreviousUser, u) in F])
show("deceased current users", [(L(f), L(u)) for f, u in F.subject_objects(OP.DevilFruitCurrentUser) if (u, OP.statusOfCharacter, OP.Deceased) in F])
show("ageAtDeath but not Deceased", [L(s) for s in U.subjects(OP.ageAtDeath, None) if (s, OP.statusOfCharacter, OP.Deceased) not in U])
for p in (OP.hasBloodType, OP.race, OP.placeOfOrigin, OP.height, OP.age, OPX.shipOwner, OPX.operatedBy, OPX.shipType):
    show(f"{L(p)} multi-valued", [(L(s), sorted(map(str if p == OP.height else L, v))) for s, v in multi(U, p).items()], 10)
show("typo predicates", [(L(p), L(s), L(o)) for s, p, o in U if L(p) in ("hasdevilFruit", "affilatesWith", "DevilFruitDebutManga", "DevilFruitDebutAnime")])

print("\n[3] class overlaps (asserted | after RL)")
TOP = [OP.Character, OP.DevilFruit, OPX.Ship, OP.Affiliation, OP.Occupation, OP.Location, OP.Status, OP.DevilFruitType, OP.Race, OPX.HakiType,
       OPX.ShipType, OP.BloodType, OP.MangaIssue, OP.AnimeEpisode, OP.Arc, OP.Bounty, SDO.Person, OP.Person, OP.PirateCrew, SDO.Organization, OP.Kingdom]
for a, b in itertools.combinations(TOP, 2):
    na = set(U.subjects(RDF.type, a)) & set(U.subjects(RDF.type, b))
    nf = set(F.subjects(RDF.type, a)) & set(F.subjects(RDF.type, b))
    if nf:
        print(f"    {L(a)} & {L(b)} ({b.split('/')[2]}): {len(na)} | {len(nf)}  {sorted(map(L, nf))[:8]}")
D = {k: set(F.subjects(RDF.type, OPX[k])) for k in ("PirateAffiliatedCharacter", "MarineAffiliatedCharacter", "RevolutionaryAffiliatedCharacter", "WorldGovernmentAffiliatedCharacter")}
for a, b in itertools.combinations(D, 2):
    show(f"{a} & {b}", list(map(L, D[a] & D[b])), 13)
show("op: twins of curated ships typed op:Character", [L(s) for s in F.subjects(RDF.type, OPX.Ship) if (OP[L(s)], RDF.type, OP.Character) in U])
occ = defaultdict(set)
for s, o in F.subject_objects(OP.occupation):
    occ[L(o)].add(s)
cands = [(x, y, len(occ[x]), len(occ[x] & occ[y])) for x in occ for i, j in ((i, j) for n in [len(x.split("_"))] for i in range(n) for j in range(i + 1, n + 1))
         for y in ["_".join(x.split("_")[i:j])] if y != x and y in occ and (i == 0 or j == len(x.split("_")))]
print(f"  lexical broader-occupation candidates: {len(cands)}; holders of X all hold Y: {sum(c[2] == c[3] for c in cands)}")
ranks = [o for o in occ if re.match(r"^(Marine_.*|Vice_Admiral|Rear_Admiral|Fleet_Admiral)$", o)]
h = set().union(*(occ[r] for r in ranks))
show(f"holders of {len(ranks)} Marine rank occupations ({len(h)}) not MarineAffiliated", list(map(L, h - D["MarineAffiliatedCharacter"])))
show("bare 'Admiral' holders", list(map(L, occ["Admiral"])))

print("\n[4] owlrl with proposed axioms")
P = Graph().parse(data=PROPOSED, format="turtle")
for label, prop, patch in (("A as proposed, unpatched data", P, False),
                           ("B without functional statusOfCharacter", P - Graph().parse(data="@prefix op: <http://kalnassag.com/onepiece#> . @prefix owl: <http://www.w3.org/2002/07/owl#> . op:statusOfCharacter a owl:FunctionalProperty .", format="turtle"), False),
                           ("C as proposed + simulated status patch", P, True)):
    work = U + prop
    if patch:
        for c in ("Ganryu", "Hera", "Ikkaku"):
            work.remove((OP[c], OP.statusOfCharacter, OP.Unknown))
        for c in ("Cerberus", "Hack", "Mr_7", "Risky_Brothers"):
            work.remove((OP[c], OP.statusOfCharacter, None))
    before = {v: len(set(work.subjects(OP.statusOfCharacter, OP[v]))) for v in ("Alive", "Deceased", "Unknown")}
    CLOSE(work)
    errs = [str(o) for o in work.objects(None, ERR)]
    kinds = Counter(re.sub(r"https?://\S+?[#/]([^\s,)/#]+)(?=[\s,)]|$)", r"\1", e).split(" have a common")[0].split(" on ")[0][:90] for e in errs)
    same = {(L(s), L(o)) for s, o in work.subject_objects(OWL.sameAs) if s != o and (s, OWL.sameAs, o) not in U}
    after = {v: len(set(work.subjects(OP.statusOfCharacter, OP[v]))) for v in before}
    print(f"  {label}: clashes={len(errs)} {dict(kinds)} new sameAs={sorted(same)} status counts {before} -> {after}")
    if label.startswith("B"):
        print("    ", sorted(L(e.split()[-1]) for e in errs))

print("\n[5] SHACL with proposed shapes (asserted graph)")
ok, rg, _ = validate(U, shacl_graph=Graph().parse(data=SHAPES, format="turtle"), inference="rdfs")
SH = Namespace("http://www.w3.org/ns/shacl#")
res = defaultdict(list)
for r in rg.subjects(RDF.type, SH.ValidationResult):
    res[(L(rg.value(r, SH.resultPath) or ""), L(rg.value(r, SH.sourceConstraintComponent)))].append((L(rg.value(r, SH.focusNode)), L(rg.value(r, SH.value) or "")))
print("  conforms:", ok)
for k, v in res.items():
    print(f"    {len(v):3} {k} {sorted(v)}")

print("\n[6] implication table derived from TBox + proposed axioms (fresh individual, owlrl)")
PFX = "PREFIX op: <http://kalnassag.com/onepiece#> PREFIX opx: <http://kalnassag.com/onepiece-ext#> "
FACTS = {
    "cat=Character": "?x a op:Character .", "cat=DevilFruit": "?x a op:DevilFruit .", "cat=Ship": "?x a opx:Ship .",
    "status=Alive": "?x op:statusOfCharacter op:Alive .", "status=Deceased": "?x op:statusOfCharacter op:Deceased .",
    "occ=Pirate_Captain": "?x op:occupation op:Pirate_Captain .", "occ=Captain": "?x op:occupation op:Captain .",
    "occ=Pirate": "?x op:occupation op:Pirate .", "occ=Pirate_Officer": "?x op:occupation op:Pirate_Officer .",
    "Captain(class)": "?x a opx:CaptainCharacter .", "PirateAffiliated": "?x a opx:PirateAffiliatedCharacter .",
    "MarineAffiliated": "?x a opx:MarineAffiliatedCharacter .", "DevilFruitUser": "?x a opx:DevilFruitUser .",
    "DevilFruitEater": "?x a opx:DevilFruitEater .", "HakiUser": "?x a opx:HakiUser .", "haki=Conquerors": "?x opx:hasHaki opx:ConquerorsHaki .",
    "fruitType=Paramecia": "?x op:hasFruitType op:Paramecia .", "fruitType=Zoan": "?x op:hasFruitType op:Zoan .", "fruitType=Logia": "?x op:hasFruitType op:Logia .",
    "fruitSub=MythicalZoan": "?x opx:hasFruitSubtype opx:MythicalZoan .", "fruitSub=AncientZoan": "?x opx:hasFruitSubtype opx:AncientZoan .",
    "eats Paramecia": "?x op:hasDevilFruit ?f . ?f op:hasFruitType op:Paramecia .", "eats Logia": "?x op:hasDevilFruit ?f . ?f op:hasFruitType op:Logia .",
    "eats Zoan": "?x op:hasDevilFruit ?f . ?f op:hasFruitType op:Zoan .", "eats MythicalZoan": "?x op:hasDevilFruit ?f . ?f opx:hasFruitSubtype opx:MythicalZoan .",
    "PirateShip": "?x a opx:PirateShip .", "shipType=Caravel": "?x opx:shipType opx:Caravel .", "shipType=Submarine": "?x opx:shipType opx:Submarine .",
}


def table(tbox):
    def clos(names):
        g = Graph()
        for t in tbox:
            g.add(t)
        for i, n in enumerate(names):          # a fresh ?f per asserted fact: one character may eat two fruits (Blackbeard)
            pat = FACTS[n].replace("?x", "<urn:q#x>").replace("?f", f"<urn:q#f{i}>")
            g.parse(data=PFX.replace("PREFIX ", "@prefix ").replace("> ", "> . ") + pat, format="turtle")
        CLOSE(g)
        return g, len(list(g.objects(None, ERR)))
    base_err = clos([])[1]
    names = list(FACTS)
    yt = {}
    for n in names:
        g = clos([n])[0]
        yt[n] = [m for m in names if m != n and g.query(PFX + "ASK {" + FACTS[m].replace("?x", "<urn:q#x>") + "}").askAnswer]
    yf = {n: [] for n in names}
    for a, b in itertools.combinations(names, 2):
        if b not in yt[a] and a not in yt[b] and clos([a, b])[1] > base_err:
            yf[a].append(b); yf[b].append(a)
    return {n: {"yes_true": yt[n], "yes_false": sorted(yf[n]), "no_false": [m for m in names if n in yt[m]]} for n in names}


TB = Graph()
for f in ("ontology-src/ontology/onepiece-ontology.ttl", "ontology/extension.ttl", "ontology/curated.ttl"):
    TB.parse(R + f)
t0 = time.time()
before, after = table(TB), table(TB + P)
print(f"  ({time.time() - t0:.0f}s) totals  yes=>true {sum(len(v['yes_true']) for v in before.values())} -> {sum(len(v['yes_true']) for v in after.values())}"
      f"   yes=>false {sum(len(v['yes_false']) for v in before.values())} -> {sum(len(v['yes_false']) for v in after.values())}")
print(json.dumps(after, indent=1))
```
