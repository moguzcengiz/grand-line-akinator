# Ontology enrichment audit

**Snapshot date:** 2026-10-29
**Scope:** all asserted category entities and selected gameplay predicates in the vendored upstream graph, extension, curated graph, and active patch layer. A persistent queue now enumerates every typed data individual across all three preserved project namespaces and separately tracks referenced untyped URIs. This remains a structural/completeness audit, not a claim that every One Piece fact or entity has been independently checked against sources.

## Method and evidence boundary

The audit loads the same RDF sources as ingestion and calculates per-entity coverage for character affiliation, occupation, Devil Fruit ownership, and Haki; fruit type, current and previous user, and subtype; and ship operator, owner, and type. It records the URI of every entity with no assertion for each predicate. These are **unknowns**, not negative facts. It also records explicit entity counts, asserted triples, SHACL results, OWL RL materialization counts, non-reflexive sameAs, functional property conflicts, untyped referenced URIs, duplicate labels, and inert inverse declarations.

Reproduce the snapshot from the repository root:

    PYTHONPATH=backend .venv/bin/python -m app.enrichment_audit

Machine-readable outputs:

- docs/ontology-enrichment-audit.json — before/after coverage for the new Haki patch plus structural and validation metrics.
- docs/ontology-enrichment-unresolved.json — entity URI lists for uncovered predicates and model-review items.

The counterfactual removes only ontology/patches/haki.add.ttl; earlier corrections remain applied. The audit does not scrape or infer canonical negatives from missing triples.

## Current model and game use

| Area | Current representation | Gameplay use / audit note |
|---|---|---|
| Character affiliations | op:affiliatesWith; classification rules in backend/app/ontology.py; derived pirate/Marine/Revolutionary/World Government labels | Organization questions and category conjunctions. The rule-based name classifier is convenient but merits source-backed review for every organization. |
| Occupations and ranks | op:occupation; a small opx:broaderOccupation hierarchy; additive opx:TemporalStatement records | Role questions still consume legacy triples. Temporal annotations are supported without changing those triples; rank facts without an annotation remain time-unspecified. |
| Fruit ownership | op:DevilFruitCurrentUser, inverse op:hasDevilFruit, op:DevilFruitPreviousUser and opx:previouslyHadDevilFruit | Direct ownership and “ever eaten” questions. Existing distinction between current and previous ownership is retained. |
| Fruit type | op:hasFruitType; opx:hasFruitSubtype for Ancient/Mythical Zoan and other subtypes | Type and subtype questions. The upstream owl:oneOf remains a latent modeling issue for full OWL DL users. |
| Haki | opx:hasHaki with three Haki individuals | Positive Haki questions; current known Haki profiles form a small partial dataset. Unlisted ability types remain unknown. |
| Ships | Nine curated opx:Ship individuals; operatedBy, shipOwner, builtBy, shipType, shipStatus | Ship and relationship questions. Ship coverage is demo-scale, not an exhaustive canon catalog. |
| Debuts and status | Functional debut properties; a single-valued character status with patches for malformed upstream data | Debuts are not generated as gameplay questions. Status preserves Unknown as distinct from missing and does not convert missing facts to false. |

Question rules are built in backend/app/questions.py; they use schema relationships, inferred labels, manually composed paths, and three-valued scopes. Open-world relations use positive/path scopes, so an absent affiliation, fruit link, ship link, or Haki link does not produce a negative answer.

## Findings

### Verified and corrected in this batch

The original curated Haki data recorded only Armament and Observation for Charlotte Katakuri, though he uses Conqueror's Haki in manga chapter 893. It also omitted known Haki profiles for Koby, Usopp, and Yamato. A separate additive patch records seven positive Haki edges: Koby (Armament and Observation), Usopp (Observation), Yamato (all three), and Katakuri (Conqueror's). The evidence, chapter references, source type, confidence, and time scope are recorded on reified RDF statement resources and in docs/ONTOLOGY_ENRICHMENT_SOURCES.md.

No negative Haki edges were added. Existing character and Haki coverage changes are reported in the JSON snapshot. The Haki facts are high-confidence manga-backed additions; English fan wiki pages are discovery/citation indexes, not primary canon.

### Verified additions from campaign batch 005

The official profiles support bounty records for Caribou (210,000,000), Charlotte Cracker (860,000,000), Charlotte Daifuku (300,000,000), Charlotte Smoothie (932,000,000), Diamante (former 99,000,000), Jack (1,000,000,000), Drophy (14,000,000), and Galdino (24,000,000). Diamante's profile also gives the Japanese epithet `コロシアムの英雄`. Each of these 33 factual triples has source-level provenance in `ontology/patches/campaign-batch-005.add.ttl`. No date or bounty interval was inferred; “former” is retained in Diamante's record name and provenance because the current bounty schema has no interval field.

The other 12 characters received source checks recorded in the campaign ledger. Family relations, Leo's battalion role, Issho's blindness and recruitment route, fruit identity inconsistencies, and Gill Bastar's tentative previous-fruit attribution remain open. An absent official-profile bounty remains unknown. No `owl:sameAs` or unsupported negative fact was added.

### Verified additions and corrections from campaign batch 006

Official character profiles support ten additional bounty records: Marco (1,374,000,000), Mikita (7,500,000), Pekoms (330,000,000), Pica (former 99,000,000), Scratchmen Apoo (350,000,000), Shanks (4,048,900,000), Baron Tamago (429,000,000), Trebol (former 99,000,000), Van Augur (64,000,000 at the Summit War), and X Drake (222,000,000). The patch preserves former and Summit War time qualifiers in record names and provenance. Pekoms's official profile also explicitly confirms Armament Haki.

Seventeen `opx:TemporalStatement` records annotate current or historical roles and crew affiliations for Rob Lucci, Shanks, Smoker, and X Drake. The source profiles do not provide chapter intervals, so none were inferred. These annotations do not create undated triples; the existing timeless assertions remain unchanged. Four literals explicitly labeled as VIZ/editorial translation metadata were removed from alias/epithet predicates: Mikita's VIZ/4Kids rendering, Pekoms's Viz rendering, X Drake's English rendering, and Tsuru's Viz translation. Their existing Japanese and in-world names were retained. The patch adds 644 net triples (648 additions and four removals) and 200 inferred triples, with zero patched SHACL violations, functional conflicts, non-reflexive equality inferences, or OWL RL clashes.

### Verified additions and corrections from campaign batch 007

Official character profiles support five previously absent bounty records: Zala (35,000,000), Edward Newgate (5,046,000,000), Kaidou (4,611,100,000), Marshall D. Teach (3,996,000,000), and Trafalgar D. Water Law (3,000,000,000). Luffy's official profile confirms his existing 3,000,000,000 record; it was not duplicated. Borsalino and Sakazuki profiles do not state bounty values, so none were added. Luffy's official profile also identifies the Gomu Gomu no Mi as the Hito Hito no Mi, Mythical Zoan Model Nika. The patch corrects the existing fruit's functional type from Paramecia to Zoan, adds the Mythical Zoan subtype and the Japanese disclosed model-name label, and retains the single existing fruit individual/current-user relation.

Twenty temporal annotations record profile-snapshot current and historical roles/affiliations for Zala, Borsalino, Edward Newgate, Teach, Luffy, Sakazuki, and Law. No validity intervals were inferred; the 20 statement records have provenance and do not add unqualified triples. Official profiles were also checked for 11 fruit entities; existing user links were retained without duplication. The Gocha-Gocha current-user edge remains unresolved because no official profile evidence was located. The patch adds 509 net asserted triples and 171 inferred triples, including five Bounty records. Its one removal corrects Luffy's contradictory old fruit-type assertion. Patched SHACL remains clean; OWL RL reports no clash, dropped functional axiom, or non-reflexive equality inference.

### Carried forward from the previous audit

The earlier patch set fixes debut cardinality errors without removing later appearances, repairs the swapped inCrew domain/range, reconciles only unambiguous punctuation variants in Devil Fruit user links, separates merged characters and ship twins, and corrects fruit subtype data. The original source remains unchanged. Full investigation and before/after OWL behavior are in docs/ONTOLOGY_AUDIT.md.

### Open structural and modeling findings

1. **Temporal organization and rank facts.** Membership and occupation assertions are largely timeless. The additive temporal model in ontology/patches/temporal-model.add.ttl distinguishes Current (relative to the ontology snapshot), Historical, and TimeUnspecified records, with optional validity chapter bounds. Batches 006–007 add 37 source-backed annotations but leave legacy assertions intact. More historical role and membership dates remain unreviewed.
2. **Closed fruit type enumeration.** The upstream owl:oneOf names only Paramecia, Zoan, and Logia, while subtypes are represented by additional terms. Existing OWL RL behavior and the latent OWL DL concern remain documented; the upstream axiom was not changed without an upstream-level decision.
3. **Inert rdfs:inverseOf.** The upstream hasBounty/givenTo inverse declaration uses the wrong vocabulary. These relationships are not used by the game and remain preserved pending a targeted schema patch and provenance.
4. **Namespace split and unresolved user URIs.** Slash and hash namespace variants are retained verbatim. Ambiguous placeholder user nodes remain unresolved rather than being guessed into Character identities.
5. **Coverage is incomplete by design.** Many characters have no recorded Haki, ship, or fruit relation; many are simply not documented for that predicate. The machine-readable report lists these IDs as coverage gaps, not false answers. The next source-backed work should prioritize closely competing candidates in the game evaluation harness.
6. **Duplicate names and labels.** Same-name characters and multiple labels are not merged automatically. URI identity and source mapping require individual evidence.

## Severity and priority

| Severity | Finding | Action |
|---|---|---|
| High | Unverified or ambiguous character-to-fruit/organization/ship edge | Keep unknown; add only with a direct source and provenance record. |
| High | Current/historical role ambiguity | Do not treat an undated rank or membership as current; design temporal representation before broad updates. |
| Medium | Haki and ship coverage gaps | Enrich selectively when a canonical manga/databook reference is available; prioritize game discrimination. |
| Medium | Inert inverse and closed enumeration schema issues | Preserve current upstream and patches; prepare reviewable schema corrections after checking downstream behavior. |
| Low | Long descriptions, aliases, or low-impact attributes | Defer unless they improve candidate discrimination or resolve an identity problem. |

## Completeness limits

The audit systematically enumerates all typed entities for the listed predicates, but external verification remains batch-limited. It does not claim full external fact-by-fact verification of all characters, fruits, crews, or ships. Unresolved records and complete gap URI lists are machine-readable in docs/ontology-enrichment-unresolved.json.

## Persistent campaign status

The current queue at `work/ontology-research-queue.jsonl` has **5,475 records**: 5,315 typed data individuals and 160 referenced untyped URI nodes tracked for identity review. The current typed population includes 1,514 Characters, 148 Devil Fruits, 96 bounty records, 9 Ships, and other typed individuals. The queue preserves asserted and inferred assertions separately; known fruit ownership through inverse properties is not labeled as a gap. Campaign batches 001–053 have first-pass partial review records for their reserved entities. Current statuses are 1,061 `reviewed_partial`, 94 `partially_verified`, 4,300 `pending`, and 20 `in_progress` in reserved batch 054 (`Little Oars Jr` through `Manjaro`). External fact-by-fact verification remains incomplete; missing relations remain unknown.

The first focused pass reviewed 20 characters selected from the pinned game-evaluation set. It produced three verified additions: Caesar's temporary alias, Enel's Observation Haki, and Ace's Conqueror's Haki. A further set of fruit, crew, and epithet proposals were already asserted or inferred; medium-confidence Mihawk/O-Tsuru proposals and schema gaps for SSG leadership and adopted-sibling relations were recorded without integration. The second pass reviewed another 20 characters and added 10 source-backed assertions across Clover's library role, Dorry's bounty record, and Catarina Devon's new Devil Fruit individual and classification. Unsupported family and leadership predicates remain held for schema review. Per-entity findings are in `work/research/batch-001-results.json` through `work/research/batch-012-results.json`; batch and event checkpoints are in `work/ontology-campaign-state.json` and `work/ontology-campaign-events.jsonl`.

The post-batch-011 repository suite reports **101 passed, 33 skipped** (live Fuseki integration cases). Batch 011's paired 200-game evaluation used a 478-candidate pool; top-1 moved from 73.0% to 73.5%, while within-three success (92.0%), average questions (23.8), median (27), unknown-answer rate (22.3%), and validity (100%) were unchanged. One pytest warning notes that `pytest.mark.integration` is not registered.

The latest corrected full graph snapshot, through campaign batch 030, has 39,590 asserted triples and 45,688 OWL RL inferred triples (Haki comparison before/after: 39,520 / 39,590 asserted; 45,662 / 45,688 inferred). Isolated patch comparisons for reviewed campaign batches are recorded in `docs/ontology-enrichment-audit.json`. Batch 011 adds 32 asserted / 19 inferred triples after also correcting a rule-derived Pacifista organization classification. Batch 012 reviewed 20 characters with no RDF delta. All 20 entities in batch 013 received first-pass partial reviews; its isolated patch adds 553 asserted / 113 inferred triples, including a Cross Guild bounty estimate, Island Eater birthday/origin, and ten temporal role records; it removes four character-as-affiliation types plus two misused owner edges. Twelve batch-013 entities retain unresolved identity, label, status, or profile gaps; these remain open-world unknowns. Batch 014 completed first-pass reviews for all 20 entities; batches 015–016 have since completed their first-pass reviews. The paired 200-game evaluation retained the 478-candidate pool and showed no change in top-1 accuracy (73.5%), within-three success (92.0%), average questions (23.8), median questions (27), unknown-answer rate (22.3%), or question validity (100%). Batch 008's 20 official profiles confirmed already-asserted current-user edges, with three also explicitly confirming their existing Logia type. Batch 009 confirmed 20 existing current-user associations and corrected two incomplete Japanese model-name labels. Batch 010 checked nine fruit current users and six ship records, added four complete Japanese model-name labels and Judy's specific origin, and added two provenance-backed temporal annotations for the Going Merry/Thousand Sunny operator links. Batch 007 increases bounty records from 65 to 70; batch 013 brings the total to 71. SHACL reports zero patched-graph violations (37 on the upstream graph); functional-property conflicts, non-reflexive `owl:sameAs` inferences, and OWL RL clashes remain zero. Missing relations remain unknown.


### Campaign batch 014 review findings

Official profile checks for Kurozumi Orochi, Koza, Kumadori, and Matsuge showed that each individual was also typed as `op:Affiliation`. The erroneous class assertions are removed in the batch 014 review patch, with the character types retained. Orochi's official profile also identifies a named Mythical Zoan for which no fruit individual existed; the patch supplies that fruit and its previous-user, type, subtype, and Japanese label assertions. The existing deceased-character/DevilFruitUser disjointness is preserved; the holder is modeled as historical, so the fruit relation does not imply a living current user. Kitton's official profile supplies the named residence Baldimore, which is added as a location. Existing Kokoro, Koza, and Kumadori roles/affiliations now have additive temporal annotations where the official text distinguishes current from former roles. These records do not rewrite the underlying timeless facts.

The affiliation edges for Kumadori–CP0 and Matsuge–Super Spot-Billed Duck Troops remain under review. The former CP9 profile text does not settle the separate CP0 edge. Matsuge's profile header lists the troop while official product copy calls him an applicant, so the graph does not treat the ambiguity as a negative membership fact. Eleven exact-name profile searches did not yield direct official profiles for the relevant obscure entries; those facts remain unverified rather than false. Entity-level evidence is listed in `work/research/batch-014-results.json` and linked in the source ledger.


The refreshed audit snapshot, including the batch 017 corrections, contains 38,322 asserted and 45,311 inferred triples. It reports zero patched-graph SHACL violations (37 on the upstream graph), zero OWL-RL clashes, zero non-reflexive `owl:sameAs` inferences, and zero dropped functional-property axioms. The batch 014 isolated counterfactual reports +421 asserted and +103 inferred triples, including one Devil Fruit. Batch 015 adds 20 asserted / 13 inferred triples from two directory-supported affiliation edges and their provenance. Batch 016 removes one asserted / two inferred triples by withdrawing Ryunosuke’s unsupported deceased status. The batch 016 paired comparison is unchanged on the fixed 200-game set: 73.5% top-1, 92% within three guesses, 23.8 average questions, 27 median, 22.3% unknown answers, and 100% valid questions. Batch 017 removes three asserted triples and changes the isolated inference count by +2; its paired 200-game comparison is unchanged at 73.5% top-1, 92% within three guesses, 23.8 average questions, 27 median, 22.3% unknown answers, and 100% valid questions. The batch 014 paired gameplay comparison also shows unchanged metrics on the pinned 200-game set; detailed outputs are `docs/ontology-campaign-batch-014-before.json` and `docs/ontology-campaign-batch-014-after.json`. Batch 017 outputs are `docs/ontology-campaign-batch-017-before.json` and `docs/ontology-campaign-batch-017-after.json`.


### Campaign batch 018 (first-pass complete)

All 20 reserved entities were reviewed. Official sources support changes for nine entities: four affiliation/Haki edges plus temporal annotations for historical membership or occupations. Ten exact-name profile searches remain unresolved; Aremo Ganmi has an editorial identity reference but no justified graph change. The source ledger and `work/research/batch-018-results.json` contain the per-entity decisions. Historical qualifiers do not rewrite timeless assertions, and missing facts remain unknown. The isolated patch adds 369 asserted and 92 inferred triples, including statement-level provenance resources; the latest full graph has 38,691 asserted / 45,403 inferred triples, zero patched SHACL violations, zero functional-property drops, zero OWL-RL clashes, and zero non-reflexive `sameAs` inferences. The isolated pre-patch counterfactual also has zero reasoning clashes. The paired 200-game evaluation is unchanged at 73.5% top-1, 92% within three, 23.8 average questions, 27 median, 22.3% unknown answers, and 100% valid questions.


The current checkpoint has batches 001–025 first-pass complete. The refreshed queue currently has 5,445 records total: 500 reviewed_partial, 52 partially_verified, 4,873 pending, and 20 in progress in active batch 026. The active entity URIs and next actions are maintained in `work/ontology-campaign-state.json`, `work/ontology-research-queue.jsonl`, and `docs/ONTOLOGY_CAMPAIGN_PROGRESS.md`.

### Campaign batch 019 (first-pass complete)

All 20 entities were reviewed; seven direct official profile sources were found and 13 exact-name searches remain unresolved. The patch adds three source-backed relationship/alias edges and a historical qualifier for Clapp's enslaved role, and removes one misapplied Carmel affiliation-class assertion. Its isolated delta is +52 asserted / +30 inferred triples. The refreshed full graph has 38,743 asserted / 45,433 inferred triples, zero patched SHACL violations, and no functional-property drops, OWL-RL clashes, or non-reflexive `sameAs` inferences. Paired 200-game metrics remain unchanged at 73.5% top-1, 92% within three, 23.8 average questions, 27 median, 22.3% unknown answers, and 100% valid questions. Parent-child facts noted by official profiles remain unmodeled because the current schema has no family predicate. The per-entity results are checkpointed in `work/research/batch-019-results.json`; batch-specific isolated graph metrics are recorded in the audit JSON.


Batch 021 (`batch-1793241409-20`) is recorded as first-pass complete. Queue status: 420 reviewed_partial, 46 partially_verified, zero in progress, and 4,972 pending out of 5,438 total records. Batch 021 findings and source gaps are in `work/research/batch-021-results.json`.


### Campaign batch 021 (first-pass complete)

All 20 queued characters received a focused first-pass review. Official character profiles confirmed missing affiliations for Haredas–Weatheria, Dr. Hiriluk–Drum Kingdom, and Heracles–Boin Archipelago. The official Jean Ango profile confirmed his bounty-hunter and sniper roles, epithet, and birthday; those facts were already represented. Sixteen exact-name searches remain unresolved and their current assertions remain unknown pending authoritative evidence. The isolated patch comparison is +30 asserted / +11 inferred triples. The full graph has 38,855 asserted / 45,475 inferred triples, zero patched SHACL violations or warnings, zero OWL-RL clashes, zero non-reflexive `owl:sameAs` inferences, and no dropped functional-property axioms. The source-backed additions are in `ontology/patches/campaign-batch-021.add.ttl`; entity-level findings are in `work/research/batch-021-results.json`. The 16 unresolved profile searches are also recorded in `docs/ontology-enrichment-unresolved.json`.

### Campaign batch 022 (first-pass complete)

All 20 entities received focused review. The official Komachiyo editorial note supports the already represented Tama relationship but does not establish ownership; the Moria editorial note explicitly leaves a possible Kozuki/Wano connection unresolved. Nineteen direct exact-name profile searches remain open. No RDF change was justified, and missing evidence remains unknown. Entity-level notes are in `work/research/batch-022-results.json`.

### Campaign batch 023 (first-pass complete)

The 20 reviewed characters had no direct exact-name official profiles surfaced in this pass. An official editorial note mentioned Mummy disease as speculation, not an established ability; it was not added. No RDF changes were justified, and the search gaps remain unknown. Details are in `work/research/batch-023-results.json`.


### Campaign batch 024 (first-pass complete)

The isolated patch comparison is +177 asserted / +62 inferred triples. It adds six source-backed relationship edges across the batch and late follow-ups, including a new model-specific Devil Fruit individual; two relationships carry historical qualifiers. Sixteen exact-name searches remain unresolved, preserving open-world unknowns. The paired 200-game evaluation is unchanged (73.0% top-1, 92.0% within three, 23.73 average questions, median 27, 22.3% unknown answers, 100% valid questions; pool 480, seed 42). The latest full graph has 39,032 asserted / 45,537 inferred triples with the Haki patch applied. Patched SHACL has 0 violations and 0 warnings (37 upstream violations); OWL RL has 0 clashes, 0 non-reflexive `sameAs` inferences, and no dropped functional-property axioms. Regression tests: 104 passed, 33 skipped. The entity-level review is `work/research/batch-024-results.json`; the patch is `ontology/patches/campaign-batch-024.add.ttl`.

### Campaign batch 025 (first-pass complete)

The isolated comparison is +60 asserted / +18 inferred triples from six profile-backed facts. Seven direct official profiles were reviewed, while thirteen exact-name searches remain unresolved. The current full graph contains 39,092 asserted / 45,555 inferred triples. Patched SHACL has zero violations and warnings (37 upstream violations); OWL RL has zero clashes, zero non-reflexive `sameAs` inferences, and no dropped functional-property axioms. In the paired 200-game evaluation, top-1 moved from 73.0% to 73.5%, within-three remained 91.5%, average questions moved from 23.71 to 23.85, and the candidate pool grew from 481 to 482 when the referenced location was typed (same targets, seed 42). Official Green Blood descriptions were recorded without treating copied abilities as Devil Fruit ownership.

**Current resumable checkpoint:** Batch 033 is reserved with 20 entities. The queue contains 5,447 records: 640 reviewed_partial, 56 partially_verified, 20 in_progress, 4,731 pending, and 160 referenced untyped URIs held for identity review. The full graph snapshot below is through batch 030; batches 031 and 032 postdate it. Batch results are first-pass partial reviews, not complete verification.


### Campaign batches 027–028

Batch 027 adds two source-backed positive facts: Tonjit's Long Ring Long Land residence and Urashima's Wano affiliation. Wapol's official profile preserves his two historical kingdom associations; the Egghead overview confirms six satellite identities but the schema has no satellite-of relation. Its paired 200-game evaluation is unchanged at 73.5% top-1, 91.5% within three, 23.85 average questions, median 27, 22.3% unknown answers, and 100% validity on 482 candidates.

Batch 028 adds Yoshimoto's Arabasta affiliation and Albion's 92 million berry bounty using the existing Bounty model. It confirms additional affiliations already represented and preserves the separate Wano Ikkaku entity without merging it with the Heart Pirates character. Its paired evaluation is also unchanged on the same 482-candidate set and seed 42. The corrected full graph audit completed through batch 030: 39,590 asserted / 45,688 inferred triples; 0 patched-graph SHACL violations or warnings (37 upstream violations); 0 OWL-RL clashes, 0 non-reflexive sameAs inferences, and no dropped functional-property axioms. Isolated batch deltas: 027 +20 asserted / +6 inferred; 028 +50 / +17; 029 +150 / +34; 030 +99 / +23. Batch 031 is newer than this snapshot.


The structural audit found 152 untyped referenced URI nodes in the loaded graph; 160 untyped URIs are separately queued for identity review because the campaign queue also retains discovery candidates and source context. These are URI-resolution issues, not negative facts.


### Campaign batch 031 isolated comparison

The batch-031 patch adds 21 source-backed assertions with 21 matching provenance records: four named bounty records and Black Maria's model-specific Ancient Zoan fruit. Its isolated delta is +210 asserted / +75 inferred triples. The patched graph has zero SHACL violations or warnings and no dropped functional-property axioms. The paired 200-game comparison is unchanged on 482 candidates (73.5% top-1, 91.5% within three, 23.85 average questions, 27 median, 22.3% unknown answers, 100% validity). This comparison postdates the full structural snapshot in `docs/ontology-enrichment-audit.json`, which covers batch 030.


### Campaign batch 032 isolated comparison

The Brogy bounty patch adds four factual triples and four source-provenance statements (+40 asserted / +11 inferred). Patched SHACL reports zero violations or warnings, with no functional-property drops. The paired 200-game comparison is unchanged on the 482-candidate pool (73.5% top-1, 91.5% within three, 23.85 average questions, 27 median, 22.3% unknown answers, 100% validity). This isolated comparison postdates the full structural snapshot through batch 030.


### Campaign batch 033 isolated comparison

The Cavendish and Chadros Higelyges bounty patch adds eight factual triples (two named Bounty records) with eight statement-level provenance records: +80 asserted / +26 inferred triples. The patched graph has zero SHACL violations and warnings, no functional-property conflicts, and no functional-property drops. The paired 200-game comparison is unchanged on the 482-candidate pool (73.5% top-1, 91.5% within three, 23.85 average questions, 27 median, 22.3% unknown answers, 100% validity). Full graph totals after batches 031–033 are 39,920 asserted / 45,800 inferred triples; the machine-readable full structural audit JSON still reports the earlier batch-030 checkpoint and should not be read as a batch-033 structural report.


### Campaign batch 034 source review

Twenty Charlotte-family records were reviewed; no patch was warranted. Official profiles and SBS/editorial sources confirmed existing facts for a subset, while five exact-name profile searches remain unresolved. The family-order and kinship gaps remain schema-review findings. Official editorial commentary treats the Charlotte Family affiliations for Basskarte and Dacquoise as uncertain; these graph assertions were preserved, not rejected. Custard's age and birthday remain unverified because her official profile does not state them. The campaign queue is now at 5,456 entities, including 159 untyped identity-review URIs. Details: `work/research/batch-034-results.json`.

## Campaign batch 035 — source and identity review

Batch 035 reviewed 20 Charlotte-associated entities against official-site family roundups and anime editorial commentary. It yielded six direct confirmations of already modeled identity/affiliation facts, five explicitly tentative family-membership cases, and nine unresolved exact-name searches. No RDF patch was made because the confirmed family-order and kinship facts have no suitable predicates in the current schema, and the tentative sources do not justify converting uncertain family membership into canonical facts. The paired Charlotte_Dolce_and_Dragée individual is a modeling review item: an official roundup names Dolce and Dragée as two sons but the ontology has one combined URI. No split was applied without individually attributable evidence. Current structural audit metrics remain those captured through batch 030; batch 035 itself changes no graph metrics. See `work/research/batch-035-results.json` and the corresponding source-ledger entry.

## Campaign batch 036 — verified fruit, bounty, and temporal corrections

Batch 036 reviewed 20 entities: nine existing facts were confirmed, four family-identity cases were explicitly tentative in official sources, and seven exact-name profile searches remained unresolved. The official Mont-d’Or profile revealed a malformed `DevilFruitCurrentUser` object URI and a missing bounty; the correction replaces only the malformed object and adds a named 120,000,000-berry bounty. Official sources list Snack's 600,000,000-berry bounty and describe his Sweet Commander role as former. A named bounty and an additive historical temporal statement were added without removing the legacy timeless role assertion. The isolated patch adds 139 asserted and 41 inferred triples; all 14 factual additions have matching statement-level provenance. Patched SHACL reports zero violations and warnings; functional conflicts, OWL RL clashes, non-reflexive `sameAs` inferences, and dropped functional-property axioms are all zero. The paired 200-game evaluation is unchanged on the same 482 targets and seed 42. Full structural audit JSON remains a batch-030 snapshot; the batch-036 validation includes patches through batch 036. See the batch result and source ledger for exact per-entity evidence.


Batch 036 paired evaluation emitted the same RDFLib/OWL-RL conversion diagnostics for existing `xsd:gMonthDay` literals on both sides; the patch adds no date literals, both evaluation runs completed successfully, and the measured metrics are identical.

## Campaign batch 037 — malformed affiliations and temporal facts

The patch corrects three concatenated entity references: the shared Chess/Kuromarimo affiliation, Concelot's Musketeer/Alliance affiliation, and Choco Police's town/island/region residence URI. It also corrects Colscon from core Whitebeard Pirates to the existing allied-pirate affiliation, adds Chew's profile-listed bounty and historical Sun Pirates relation, and adds historical qualifiers for Choi and Colscon. Current and historical records for Chess and Kuromarimo coexist with unqualified legacy relations, consistent with the additive temporal model. Chessmarimo remains distinct as a fused form and its organization is left unknown. Ten official-source findings confirm facts or identities already represented, six are corrections, and five exact-name searches are unresolved (plus one adjacent Kuromarimo record because the malformed IRI was shared). The patch adds 54 factual assertions with 54 statement-level source records, for +529 asserted / +109 inferred triples. SHACL, functional-property, OWL RL, and `sameAs` checks are clean; paired gameplay results are unchanged.

## Campaign batch 041 — alphabetized first-pass audit update

Batch 041 reviewed 20 records from Eggplant Soldier through Flapper against official character profiles, the official character directory and SBS index, and chapter/episode references. The changes address three confirmed relationship defects: Elmy and Epoida were linked as direct Whitebeard crew/subordinates despite official allied-pirate classifications, and Farul's Beautiful Pirates/Grand Fleet links were collapsed into a malformed combined IRI. Fisher Tiger received a named bounty record for 230,000,000 berries; his documented past enslavement is now qualified as Historical. Erik and Farafra's former Rebel Army memberships and Rebel occupations are also qualified Historical. Existing assertions remain alongside temporal annotations so the patch does not erase or silently reinterpret them.

The exact-name profile review remains incomplete for several characters. In particular, five entities rely on chapter-cited secondary reference pages rather than direct official profiles; exact-name primary-source checks also remain open for Eggplant Soldier and Figarland Shamrock. Emma's status remains Unknown because the reviewed material does not establish her individual fate after the Victoria Punk sank. Nusjuro's additional Co-Head role and Episode 151 anime debut remain unresolved against his current official profile. Erik's Sand-Sand Clan temporal scope remains open. These are tracked in `docs/ontology-enrichment-unresolved.json` and `work/research/batch-041-results.json`.

The RDF additions and temporal annotations have statement-level source provenance; the removal patch records the three replaced assertions and their reasons. Validation and paired game-evaluation results for this batch are maintained in `docs/ONTOLOGY_ENRICHMENT_REPORT.md` after the isolated comparison completes.


## Campaign batch 042 — affiliation and temporal review

Batch 042 reviewed 20 entities from Flare through Gambo. The source-backed corrections replace Forliewbs’s core Whitebeard Pirates affiliation with the existing Whitebeard allied-pirate category, supported by the Marineford allied-fleet chapter references. Fukurou’s existing CP9 membership receives an additive Historical temporal statement because the official profile calls him a former CP9 member; the CP9 triple is retained, and the separate CP0 assertion remains open. Fullbody’s official profile contains conflicting rank text, so no rank correction was made. Fuga’s specific Horse SMILE is recorded as a modeling gap because the graph does not consistently model individual SMILE variants. Gal’s canonical identity remains unresolved.

The 25-triple additions encode two reviewed facts and their provenance/temporal record; one mistaken Forliewbs affiliation triple is recorded in the removal patch. The Docker ingestion run completed with 0 SHACL violations/warnings, 0 OWL RL clashes, 0 non-reflexive `sameAs` inferences, and no dropped functional axioms. It reported 45,555 inferred triples total, 5,926 nodes, and 14,809 edges. The running service health check returned `status: ok` with 1,669 entities. Paired evaluation on the identical 482 targets, seed 42, and 200 games was unchanged: 73.5% top-1, 91.5% within three guesses, 23.85 average questions, median 27, 22.3% unknown answers, and 100% question validity. No gameplay improvement is claimed. Full tests passed: 106 passed, 33 skipped, one existing unknown `integration` mark warning.

The standalone full audit command was stopped after it spent several minutes recomputing historical counterfactual reasonings. The batch ingestion/validation and paired evaluation completed successfully; the broader structural audit JSON therefore remains at its earlier checkpoint. Per-entity evidence is in `work/research/batch-042-results.json`, and the patches are `ontology/patches/campaign-batch-042.add.ttl` and `.remove.ttl`.


## Campaign batch 043 — affiliation, origin, and temporal review

Batch 043 reviewed 20 entities from Gancho through Glove. The patch models Gerotini’s Puddle Pirates relationship to the Red Hair Pirates as an allied affiliation rather than core crew membership; the translation-specific VIZ “Frog-Toes Ribbitini” string is removed from epithet while the canonical “Ball Fingers” and Japanese epithet remain. Gerd receives the official profile’s specific Elbaph origin alongside the existing Grand Line origin, and the existing Buggy’s Delivery affiliation and Mercenary occupation are annotated Historical based on the cited cover-story record. Existing timeless facts remain available under the additive temporal model.

The patch adds 72 RDF triples with statement-level provenance and removes two assertions, with reasons recorded in the removal patch. Ingestion validation reports 0 SHACL violations/warnings, 0 OWL RL clashes, 0 non-reflexive `sameAs` inferences, and no dropped functional axioms. The paired 200-game evaluation on the same 482 targets and seed 42 remains unchanged: 73.5% top-1, 91.5% within three guesses, 23.85 average questions, median 27, 22.3% unknown answers, and 100% valid questions. No game-performance improvement is claimed. Entity-level findings are in `work/research/batch-043-results.json`; unresolved exact-name and relationship modeling notes are listed in `docs/ontology-enrichment-unresolved.json`.


## Campaign batch 044 — organizations, bounties, and temporal corrections

Batch 044 reviewed 20 entities from Gode through Gyro. Goldberg’s malformed combined affiliation was split into current Straw Hat Grand Fleet and historical Buggy’s Delivery edges; his Mercenary role is annotated Historical and the official Elbaph origin is added alongside Grand Line. Gotti’s malformed occupation URI was normalized to Assassin and Pirate, and his official 90,000,000-berry bounty was added as a named record. Gyro’s combined crew/affiliation URI was split into a named Gyro Pirates organization and a Historical New Fish-Man Pirates affiliation; his official 73,000,000-berry bounty was added. Gyaro’s former Sun Pirates membership is qualified Historical. Gode’s WT100 source-tag string was removed from the epithet field while “the Wise” remains. Four replaced assertions are recorded in the removal patch.

The patch adds 229 RDF triples with statement-level provenance and removes four assertions. Ingestion validation reports 0 SHACL violations/warnings, 0 OWL RL clashes, 0 non-reflexive `sameAs` inferences, and no dropped functional axioms. Paired 200-game evaluation on 482 fixed targets with seed 42 is unchanged at 73.5% top-1, 91.5% within three, 23.85 average questions, median 27, 22.3% unknown answers, and 100% question validity. No performance improvement is claimed. Exact-name evidence gaps and the combined Gyoro/Nin/Bao identity are preserved in the results ledger and unresolved file.

## Campaign batch 045 — malformed roles, affiliation history, and source gaps

Batch 045 reviewed 20 entities. Hack’s malformed occupation and residence URIs were corrected, official role terms and the documented later Momoiro Island residence were retained, and the VIZ-prefixed translation metadata was removed from the epithet field. Hajrudin’s specific Elbaph origin was added; former Buggy’s Delivery service and mercenary work were qualified Historical. Hannyabal’s former Vice Warden role and Hatchan’s former crew memberships, officer role, and residences received Historical qualifiers. Hattori’s former CP9 membership was qualified Historical and the false Galley-La membership removed because his presence was part of Lucci’s undercover identity. Harald’s concatenated occupation URI was split into King of Elbaph and Devoted Blade of God, both qualified Historical.

The add patch contains 238 RDF triples with statement-level provenance and the removal patch removes five assertions. Docker ingestion and patched-graph validation reported zero SHACL violations or warnings, zero OWL RL clashes, zero non-reflexive `sameAs` inferences, and no dropped functional axioms. The reasoner continues to emit the same upstream malformed `xsd:gMonthDay` conversion diagnostics. Paired evaluation on the fixed 482 targets, seed 42, and 200 games is unchanged: 73.5% top-1, 91.5% within three, 23.85 average questions, median 27, 22.3% unknown answers, and 100% question validity. No gameplay improvement is claimed. Focused source gaps for 11 entities, Hakowan’s pet/affiliation semantics, Hasami’s link/residence semantics, and Hattori’s undercover-role modeling are documented in `docs/ontology-enrichment-unresolved.json`.

See `work/research/batch-045-results.json` and `ontology/patches/campaign-batch-045.add.ttl` / `.remove.ttl` for entity findings and patch details.

## Campaign batch 046 — bounty records and historical relationships

Batch 046 reviewed 20 entities. Two missing bounty records were added: Higuma’s official 8,000,000-berry bounty and Hibari’s approximate 200,000,000-berry Cross Guild estimate, explicitly modeled as an estimate rather than a Government-issued bounty. Hihimaru’s concatenated residence URI was split into Kuri and Wano Country; its former Beast Pirates and alliance associations were qualified Historical. Himuro’s former Kurozumi Family/Mimawarigumi relation and Hitsugisukan’s former Mokomo Dukedom rulership were also qualified Historical. Other verified profile facts were retained without duplicate assertions.

The add patch contains 159 RDF triples with source provenance; the removal patch removes one malformed residence assertion. Docker ingestion and graph validation passed with zero SHACL violations or warnings, zero OWL RL clashes, zero non-reflexive `sameAs` inferences, and no dropped functional axioms. The existing upstream malformed `xsd:gMonthDay` conversion diagnostics remain. Paired 200-game evaluation on the fixed 482 targets, seed 42, was unchanged: 73.5% top-1, 91.5% within three, 23.85 average questions, median 27, 22.3% unknown answers, and 100% question validity. No performance improvement is claimed. Nine entity source gaps and Hera/Hihimaru relationship-modeling gaps are listed in `docs/ontology-enrichment-unresolved.json`.

Per-entity findings: `work/research/batch-046-results.json`; patch: `ontology/patches/campaign-batch-046.add.ttl` and `.remove.ttl`; paired outputs: `docs/ontology-campaign-batch-046-{before,after}.json`.


## Campaign batch 052 checkpoint

The reviewed patch contains 400 additions with 29 source statement records and 22 temporal statements, and removes four upstream assertions with documented reasons. Patched ingestion reports zero SHACL violations/warnings, zero OWL-RL clashes, zero non-reflexive `owl:sameAs` inferences, and no dropped functional axioms. The fixed 200-game paired evaluation is unchanged on the 496-candidate pool: 73% top-1, 91% within three, 23.88 average questions, median 27, 22.5% unknown answers, and 100% valid questions. Entity findings and five open questions are in `work/research/batch-052-results.json` and `work/research/batch-052-unresolved.json`.
The full regression suite passed: 106 passed, 33 skipped, with the existing unknown `integration` mark warning. Batch 053 is reserved; campaign progress lists its 20 entities.


## Latest campaign validation

Campaign batches 033–054 are tracked in `docs/ONTOLOGY_CAMPAIGN_PROGRESS.md`, with per-batch evidence and paired evaluation appended to `docs/ONTOLOGY_ENRICHMENT_REPORT.md`. Batch 054's exact patch and source ledger are `ontology/patches/campaign-batch-054.add.ttl`, `ontology/patches/campaign-batch-054.remove.ttl`, and `docs/ONTOLOGY_ENRICHMENT_SOURCES.md`. The current report preserves unknown status for unsourced intervals and notes that source review is partial across the full entity set.

## Campaign source review through batch 054

The persistent first-pass queue has partial review records for 1,081 entities and 95 additional partially verified records, out of 5,473 current queue entries. Batch 054 source-checked 20 entities in parallel five-entity research groups and integrated only reviewable evidence. Four sourced assertions were added, five malformed or semantically misleading triples were removed, and six former affiliations/roles were explicitly marked Historical. Shared malformed vocabulary terms remain where other characters still reference them; those remaining references are queued rather than silently deleted.

The updated pass identifies a modeling gap: Lu Feld sponsored MADS, but `affiliatesWith` can imply organizational membership and the current schema has no sponsorship relation. The MADS edge was removed and the fact retained as unresolved rather than modeled as membership. Other open items include Little Oars Jr.'s post-Marineford fate, Loki profile details not confirmed by the official profile, and shared malformed occupation terms used by Enishida, Fukaboshi, and Ryuboshi. Per-entity sources and actions are in `work/research/batch-054-results.json`; unresolved findings are in `work/research/batch-054-unresolved.json` and `docs/ontology-enrichment-unresolved.json`.
