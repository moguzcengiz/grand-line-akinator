# Ontology enrichment sources

All additions in ontology/patches/haki.add.ttl are positive canon assertions. Source records in that file are RDF reifications with the exact subject, predicate, value, URL, source type, manga reference, confidence, and temporal scope. The table below is the human-readable index. Existing upstream and earlier curated facts are not re-cited here; their provenance and correction history are described in docs/ONTOLOGY_AUDIT.md.

| Entity | Predicate / value | Evidence and source | Confidence / scope |
|---|---|---|---|
| op:Usopp | opx:hasHaki opx:ObservationHaki | [Usopp — abilities and powers](https://onepiece.fandom.com/wiki/Usopp/Abilities_and_Powers), citing chapter 758: Usopp perceives distant auras and pinpoints Sugar during Dressrosa. | High; canon fact, time-unspecified |
| op:Koby | opx:hasHaki opx:ObservationHaki | [Koby](https://onepiece.fandom.com/wiki/Koby), chapters 579 and 594: Koby senses presences/voices at Marineford; chapter 594 identifies the ability as Haki. | High; canon fact, time-unspecified |
| op:Koby | opx:hasHaki opx:ArmamentHaki | [Koby](https://onepiece.fandom.com/wiki/Koby), chapter 1088, volume 107, pages 14–15: Honesty Impact damages Pizarro's manifested stone hand; the character reference identifies Koby as an Armament user. | High; canon fact, time-unspecified |
| op:Yamato | opx:hasHaki opx:ConquerorsHaki | [Chapter 1024](https://onepiece.fandom.com/wiki/Chapter_1024) identifies Yamato's Supreme King Haki. | High; canon fact, time-unspecified |
| op:Yamato | opx:hasHaki opx:ArmamentHaki | [Yamato](https://onepiece.fandom.com/wiki/Yamato), manga-cited ability references including the clash with Ace and later combat. | High; canon fact, time-unspecified |
| op:Yamato | opx:hasHaki opx:ObservationHaki | [Yamato](https://onepiece.fandom.com/wiki/Yamato), manga-cited ability reference; the page identifies Yamato as a user of all three Haki types. | High; canon fact, time-unspecified |
| op:Charlotte_Katakuri | opx:hasHaki opx:ConquerorsHaki | [Chapter 893](https://onepiece.fandom.com/wiki/Chapter_893) explicitly describes Katakuri and Luffy releasing Supreme King Haki together. | High; canon fact, time-unspecified |

The reference pages summarize and cite manga events; they are not official publisher sources. Search also surfaced the official [ONE PIECE.com Yamato profile](https://one-piece.com/character/YAMATO/index.html), which confirms Yamato's Mythical Zoan fruit. That source supports the existing fruit classification but was not needed for any new Haki edge. No unsupported Haki abilities or speculative affiliations were added.

## Autonomous campaign batch 001

The first source-review batch covered 20 character entities selected from the pinned game-evaluation targets. The full per-entity review and source URLs are retained in `work/research/batch-001-results.json` and `work/research/agent_{a,b,c,d}/findings.json`. The batch adds only the following facts after comparing each proposal with both asserted and OWL-inferred graph statements:

| Entity | Predicate / value | Evidence | Confidence and scope |
|---|---|---|---|
| Caesar Clown | `op:temporaryAlias "Gangster Gastino"@en` | Chapter 858 shows Caesar using the disguise/name during the Whole Cake Island events. The chapter guide indexes the manga scene; the official VIZ chapter listing is recorded as chapter metadata, not as direct page-text evidence. [Chapter 858 guide](https://onepiece.fandom.com/wiki/Chapter_858), [VIZ chapter listing](https://www.viz.com/shonenjump/chapters/one-piece) | High; temporary alias, chapter 858. |
| Enel | `opx:hasHaki opx:ObservationHaki` | The [official Enel profile](https://one-piece.com/character/Eneru/index.html) says he uses Mantra. Chapter 597, p. 13, explicitly identifies Skypiea's Mantra with Observation Haki; the [official VIZ chapter record](https://www.viz.com/shonenjump/one-piece-chapter-597/chapter/11724) identifies the chapter, and the chapter reference provides the cited content. | High; canon ability, time unspecified. |
| Portgas D. Ace | `opx:hasHaki opx:ConquerorsHaki` | In chapter 587, pp. 8–9, child Ace knocks out Bluejam Pirates members while protecting Luffy; the chapter reference identifies the event as Supreme King Haki. The [official Ace profile](https://one-piece.com/character/ace/) confirms identity and epithet; [VIZ's official chapter 587 record](https://www.viz.com/shonenjump/one-piece-chapter-587/chapter/11713) confirms the source chapter. | High; manga-confirmed ability manifested in childhood, asserted without a negative or exclusivity claim. |

### Candidate checks that did not produce additions

The six proposed fruit-user relations for Caesar, Enel, Tama, Doflamingo, Toki, and Kuzan were already asserted on the fruit individuals (`DevilFruitCurrentUser` or `DevilFruitPreviousUser`). OWL inverse properties provide the corresponding character-side view. The other reviewed fruit relations for Robin, Perona, Ace, Brook, and Alvida were also already represented in the graph. They were not duplicated in the batch patch.

Several suggested names were already present as `op:epithet` or `op:temporaryAlias`, including Robin's “Devil Child,” Brook's “Soul King,” Mihawk's “Hawk Eyes” form, and Toki's “Amatsuki Toki” birth name. Mihawk's proposed Observation Haki remains a review item because the evidence in this pass was secondary and did not directly establish the manga panel. “O-Tsuru” remains a medium-confidence alias proposal pending stronger source confirmation.

The official Vegapunk profile states that he heads SSG, but this pass found no dedicated SSG individual or leadership predicate in the current schema; the organization assertion is held for schema review. Nojiko's adopted-sibling relationship to Nami is recorded as a relationship-model gap, explicitly not as `owl:sameAs`. Historical findings for Gan Fall, Aladdin, Arlong, Kuzan, and Toki are preserved in the batch record for a temporal-annotation pass; no legacy occupation or affiliation triple was silently reinterpreted.

## Autonomous campaign batch 002

Batch 002 reviewed the next 20 high-priority characters. Per-entity findings, official source URLs, confidence, and integration decisions are recorded in `work/research/batch-002-results.json`. Ten new assertions were integrated; all others were already represented, left unknown, or held for relationship/schema or temporal review.

| Entity | Predicate / value | Evidence | Confidence and scope |
|---|---|---|---|
| Clou D. Clover | `op:occupation op:Chief_Librarian` | The [official Clover profile](https://one-piece.com/character/Clover/index.html) identifies him as head/director of the Ohara Library (館長). The existing ontology has no Ohara Library individual, so no affiliation was invented. | High; occupation mapping to the closest existing term, dates unspecified. |
| Dorry | `op:hasBounty op:Dorry_Bounty`; amount `100000000` berries | The [official Dorry profile](https://one-piece.com/character/Dorry/index.html) lists 1億ベリー. The new record follows the existing `op:Bounty` / `op:bountyAmount` / `op:givenTo` pattern. | High; profile value, source does not date the bounty. |
| Catarina Devon | A new Devil Fruit individual for Inu Inu no Mi, Mythical Zoan, Model: Nine-Tailed Fox; current user Devon; Zoan type and Mythical Zoan subtype | The [official Devon profile](https://one-piece.com/character/Catalina_Devon/index.html) names the fruit and lists it under Devil Fruit. No matching fruit individual existed. The patch retains the official Japanese label and uses the existing class/type/subtype vocabulary. | High; official profile fact, English label not asserted. |

The rest of batch 002 confirmed existing aliases, occupations, affiliations, or birthdays. Fruit/Haki blanks remain unknown. The team held family facts (Belle-Mère and Nami/Nojiko, Buckingham Stussy and Weevil, Praline and Aladdin, Ginny and Bonney, Clover's brother) because the graph lacks suitable parent, foster-parent, sibling, or spouse predicates. Bomba's Tonta Corps leadership and explicit species classification also need schema review. Retired/former leadership and historical prisoner roles remain time-unspecified in legacy triples; the new temporal vocabulary was not applied without intervals. No unsupported negative fact or `owl:sameAs` relation was added.

## Campaign batch 003

- King, Dragon, and source-backed bounty/profile facts: [King](https://one-piece.com/character/King/index.html), [Izo](https://one-piece.com/character/izo/index.html), [Kuro](https://one-piece.com/character/Kuro/index.html), [Lafitte](https://one-piece.com/character/Lafitte/index.html), [Mont Blanc Cricket](https://one-piece.com/character/MontBlanc_Cricket/index.html), [Nami](https://one-piece.com/character/nami/index.html).
- Reviewed with no unsupported additions or held for schema/identity review: Hanzo, Hody Jones, Inuarashi, Karoo, Kikunojo, Koala, Kozuki Hiyori, Kozuki Oden, Kureha, Merry, Mohji, Mont Blanc Noland, Mozu, and Kiwi. Primary profile links are recorded in `work/research/batch-003-results.json`.
- Open questions include species vocabulary, family and mentor relationships, pet/control and ship-design relations, temporal roles, the combined Mozu & Kiwi identity, and conflicting Nami profile values. No missing edge was interpreted as a negative fact.

## Campaign batch 004

- Official profiles supporting additions: [Onimaru / Gyukimaru](https://one-piece.com/character/Gyukimaru/index.html), [Who's-Who](https://one-piece.com/character/whos_who/index.html), [Bentham](https://one-piece.com/character/Bon_Clay_Mr2/index.html), [Boa Hancock](https://one-piece.com/character/Boa_Hancock/index.html), [Buggy](https://one-piece.com/character/Buggy/index.html), [Orlumbus](https://one-piece.com/character/Orlumbus/index.html), and [Sai](https://one-piece.com/character/sai/index.html).
- Additional profile labels: [Nekomamushi](https://one-piece.com/character/Master_Nekomamushi/index.html) and [Orlumbus](https://one-piece.com/character/Orlumbus/index.html).
- Hancock identity reconciliation: [Hancock profile](https://one-piece.com/character/Boa_Hancock/index.html) identifies the Mero Mero no Mi, while [S-Snake profile](https://one-piece.com/character/S-Snake/index.html) says her ability is enabled by Green Blood. The scraper's combined “Boa Hancock; S-Snake (Artificial)” value had become one invalid URI; the remove patch documents and removes that single malformed statement, and the add patch asserts Hancock's user relation with provenance. S-Snake's copied-power semantics remain a schema gap.
- Other reviewed profiles: [Vivi](https://one-piece.com/character/Nefeltari_Vivi/index.html), [Oimo](https://one-piece.com/character/Oimo/index.html), [Piiman](https://one-piece.com/character/Pepper/index.html), [Shakuyaku](https://one-piece.com/character/Shakuyaku/index.html), [Shishilian](https://one-piece.com/character/Sicilian/index.html), [Ichiji](https://one-piece.com/character/Ichiji/index.html), [Yonji](https://one-piece.com/character/Yonji/index.html), [Wyper](https://one-piece.com/character/Wyper/index.html), and [Yazaemon index entry](https://one-piece.com/character/syllabary/index.html?category=Y&page=0&sort=asc). Unmodeled family, friendship, copied-power, Homie, and temporal relations remain open.

## Campaign batch 005

Each fact below has a separate reified provenance statement in `ontology/patches/campaign-batch-005.add.ttl`. The full 20-character review ledger, including no-change decisions and open questions, is `work/research/batch-005-results.json`.

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Caribou | `op:hasBounty op:Caribou_Bounty_Profile`; amount `210000000` | [Official Caribou profile](https://one-piece.com/character/Caribou/index.html) | High; profile amount, time unspecified. |
| Charlotte Cracker | `op:hasBounty op:Charlotte_Cracker_Bounty_Profile`; amount `860000000` | [Official Cracker profile](https://one-piece.com/character/Charlotte_Cracker/index.html) | High; profile amount, time unspecified. |
| Charlotte Daifuku | `op:hasBounty op:Charlotte_Daifuku_Bounty_Profile`; amount `300000000` | [Official Daifuku profile](https://one-piece.com/character/Charlotte_Daifuku/index.html) | High; profile amount, time unspecified. |
| Charlotte Smoothie | `op:hasBounty op:Charlotte_Smoothie_Bounty_Profile`; amount `932000000` | [Official Smoothie profile](https://one-piece.com/character/Charlotte_smoothies/index.html) | High; profile amount, time unspecified. |
| Diamante | former bounty record, amount `99000000`; `op:epithet "コロシアムの英雄"@ja` | [Official Diamante profile](https://one-piece.com/character/diamante/index.html) labels the bounty former (元) and identifies the epithet. | High; former bounty with no interval; no current amount inferred. |
| Jack | `op:hasBounty op:Jack_Bounty_Profile`; amount `1000000000` | [Official Jack profile](https://one-piece.com/character/Jack/index.html) | High; profile amount, time unspecified. |
| Drophy | `op:hasBounty op:Drophy_Bounty_Profile`; amount `14000000` | [Official Drophy profile](https://one-piece.com/character/Ms_Merry_Christmas/index.html) | High; profile amount, time unspecified. |
| Galdino | `op:hasBounty op:Galdino_Bounty_Profile`; amount `24000000` | [Official Galdino profile](https://one-piece.com/character/Galdino/index.html) | High; profile amount, time unspecified. |

The other twelve profile checks did not justify a new safe RDF fact. In particular, [Brûlée](https://one-piece.com/character/Brulee/index.html) and [Pudding](https://one-piece.com/character/Charlotte_Prin/index.html) have no bounty amount listed; this is unknown, not a negative bounty. Rocinante/Doflamingo kinship, Drophy/Galdino historical memberships, Leo's Tontatta Army command, and Issho's blindness/recruitment route need a better relation or temporal vocabulary. Pudding's voice-actor identity and Jabra's CP0 affiliation need source-history review. Jabra and Kaku fruit URI/label identities need reconciliation without creating duplicate fruit records.

The official [Gill Bastar editorial](https://one-piece.com/76842/index.html) confirms his Rocks Pirates membership but frames prior Horo-Horo use as a possibility; it does not establish a WANTED! bounty as an in-continuity fact. The existing previous-user edge remains a review item rather than being treated as verified or as contradicted. Issho's profile ([Fujitora](https://one-piece.com/character/fujitora/index.html)) identifies “Fujitora”/藤虎; the literal gloss “literally meaning Wisteria Tiger” remains flagged because it is stored as a temporary alias. No removal was made in this batch.

## Campaign batch 006

Every addition below has statement-level provenance in `ontology/patches/campaign-batch-006.add.ttl`; the complete 20-entity review ledger is `work/research/batch-006-results.json`.

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Marco | `op:hasBounty op:Marco_Bounty_Profile`; amount `1374000000` | [Official Marco profile](https://one-piece.com/character/marco/index.html) | High; profile amount, exact interval unspecified. |
| Mikita | `op:hasBounty op:Mikita_Bounty_Profile`; amount `7500000` | [Official Miss Valentine profile](https://one-piece.com/character/Ms_Valentine/index.html) | High; profile amount, exact interval unspecified. |
| Pekoms | `op:hasBounty op:Pekoms_Bounty_Profile`; amount `330000000`; Armament Haki | [Official Pekoms profile](https://one-piece.com/character/Pekoms/index.html) | High; profile amount and explicit ability. |
| Pica | Former bounty record; amount `99000000` | [Official Pica profile](https://one-piece.com/character/Pica/index.html) explicitly marks the amount former. | High; former amount, interval unspecified. |
| Scratchmen Apoo | `op:hasBounty op:Scratchmen_Apoo_Bounty_Profile`; amount `350000000` | [Official Law / Worst Generation profile](https://one-piece.com/character/law/index.html) lists Apoo and the amount in the Worst Generation roster. | High; profile amount. |
| Shanks | `op:hasBounty op:Shanks_Bounty_Profile`; amount `4048900000` | [Official Shanks profile](https://one-piece.com/character/Shanks/index.html) | High; profile amount. |
| Baron Tamago | `op:hasBounty op:Tamago_Bounty_Profile`; amount `429000000` | [Official Baron Tamago profile](https://one-piece.com/character/Baron_Tamago/index.html) | High; profile amount. |
| Trebol | Former bounty record; amount `99000000` | [Official Trebol profile](https://one-piece.com/character/trebol/index.html) explicitly marks the amount former. | High; former amount, interval unspecified. |
| Van Augur | `op:hasBounty op:Van_Augur_Bounty_Summit_War`; amount `64000000` | [Official Van Augur profile](https://one-piece.com/character/Van_Ogre/index.html) labels the figure as at the Summit War. | High; Summit War point-in-time, chapter/date unspecified. |
| X Drake | `op:hasBounty op:X_Drake_Bounty_Profile`; amount `222000000` | [Official X Drake profile](https://one-piece.com/character/X_Drake/index.html) | High; profile amount. |

The same official profile sources support 17 `opx:TemporalStatement` annotations for Rob Lucci, Shanks, Smoker, and X Drake. Current status means “current at the official-profile snapshot”; historical intervals are not dated. The four source links are [Lucci](https://one-piece.com/character/Rob_Lucci/index.html), [Shanks](https://one-piece.com/character/Shanks/index.html), [Smoker](https://one-piece.com/character/smoker/index.html), and [X Drake](https://one-piece.com/character/X_Drake/index.html). These annotations qualify existing legacy roles and affiliations; they do not add an unqualified fact.

The companion removal patch deletes four literals whose text explicitly identifies a VIZ/editorial translation rather than an in-world name: Mikita's “VIZ/4Kids: Ms. Valentine”, Pekoms's “Viz: Mystoms”, X Drake's “English version: Drie”, and Tsuru's “Viz: Great Advisor”. Existing in-world aliases and Japanese or official epithets remain. Each removal reason is also listed in `docs/ontology-enrichment-audit.json`.

## Campaign batch 007

Batch 007 covered eight characters and twelve Devil Fruit individuals. The complete per-entity review is `work/research/batch-007-results.json`.

| Entity | Verified delta | Evidence | Scope |
|---|---|---|---|
| Zala | Bounty `35000000` | [Official Zala profile](https://one-piece.com/character/Ms_Doublefinger/index.html) lists 35,000,000 berries and labels Baroque Works former. | Profile bounty; interval unspecified. |
| Edward Newgate | Bounty `5046000000` | [Official Edward Newgate profile](https://one-piece.com/character/edward_newgate/index.html) lists 5,046,000,000 berries. | Profile value; interval unspecified. |
| Kaidou | Bounty `4611100000` | [Official Kaidou profile](https://one-piece.com/character/Kaido/index.html) lists 4,611,100,000 berries and identifies the existing Seiryu fruit individual. | Profile value; interval unspecified. |
| Marshall D. Teach | Bounty `3996000000` | [Official Marshall D. Teach profile](https://one-piece.com/character/Marshall_D_Teech/index.html) lists 3,996,000,000 berries and both existing current fruit links. | Profile value; interval unspecified. |
| Trafalgar D. Water Law | Bounty `3000000000` | [Official Law profile](https://one-piece.com/character/law/index.html) lists 3,000,000,000 berries. | Profile value; interval unspecified. |
| Monkey D. Luffy | Replace the Gomu Gomu fruit's incorrect Paramecia type with Zoan + Mythical Zoan subtype; add the disclosed Japanese name as an RDF label. | [Official Luffy profile](https://one-piece.com/character/luffy/index.html) lists Gomu Gomu and Hito Hito, Mythical Zoan, Model Nika. The two names refer to the same existing fruit individual; no second fruit was created. | Current fruit classification; no chapter bound added. |

The additions carry statement-level provenance in `ontology/patches/campaign-batch-007.add.ttl`; `ontology/patches/campaign-batch-007.remove.ttl` documents the single classification correction. Twenty temporal annotations record profile-supported roles and memberships for Zala, Borsalino, Edward Newgate, Teach, Luffy, Sakazuki, and Law. `Current` refers to status at the official-profile snapshot; historical intervals remain unspecified.

For the other fruit records, official profiles corroborate these already-asserted user/fruit associations: [Gunko](https://one-piece.com/character/Saint_Manmayer_Gunko/index.html), [Charlotte Galette](https://one-piece.com/character/Charlotte_Galette/index.html), [Stussy](https://one-piece.com/character/Stussy/index.html), [Charlotte Cracker](https://one-piece.com/character/Charlotte_Cracker/index.html), [Baby 5](https://one-piece.com/character/baby5/index.html), [Inazuma](https://one-piece.com/character/Inazuma/index.html), [Sanjuan Wolf](https://one-piece.com/character/San_Juan_Wolf/index.html), [Shiki](https://one-piece.com/character/Shiki/index.html), [Caesar Clown](https://one-piece.com/character/caesar/index.html), [Viola](https://one-piece.com/character/violet_viola/index.html), and [Buffalo](https://one-piece.com/character/buffalo/index.html). The existing edges were not duplicated. No official profile confirming Charlotte Newshi as the Gocha-Gocha Fruit user was found; that existing assertion remains unchanged and open for review.

## Campaign batch 008

Batch 008 reviewed 20 Devil Fruit records. Each official character profile below identifies the current user and fruit; every corresponding current-user edge was already in the graph, so none was duplicated. Three profiles explicitly call their fruit Logia (Magu Magu, Mori Mori, Pika Pika); those existing type assertions agree. The other profiles identify the ability but do not explicitly state the ontology's broad type, so their type/subtype assertions were not promoted to source-confirmed facts or changed. No profile in this review establishes a previous user. These omissions remain unknown, not negative claims. The complete evidence ledger is `work/research/batch-008-results.json`.

| Fruit | Official current-user profile | Result |
|---|---|---|
| Hana Hana no Mi | [Nico Robin](https://one-piece.com/character/robin/) | Existing user link confirmed. |
| Hie Hie no Mi | [Kuzan](https://one-piece.com/character/kuzan/index.html) | Existing user link confirmed. |
| Hobi Hobi no Mi | [Sugar](https://one-piece.com/character/sugar/index.html) | Existing user link confirmed. |
| Ishi Ishi no Mi | [Pica](https://one-piece.com/character/Pica/index.html) | Existing user link confirmed. |
| Kame Kame no Mi | [Pekoms](https://one-piece.com/character/Pekoms/index.html) | Existing user link confirmed. |
| Kibi Kibi no Mi | [Tama](https://one-piece.com/character/Otama/) | Existing user link confirmed. |
| Kiro Kiro no Mi | [Mikita / Miss Valentine](https://one-piece.com/character/Ms_Valentine/index.html) | Existing user link confirmed. |
| Kobu Kobu no Mi | [Belo Betty](https://one-piece.com/character/Belo_Betty/index.html) | Existing user link confirmed. |
| Magu Magu no Mi | [Sakazuki](https://one-piece.com/character/Sakazuki/index.html) | Existing user link and Logia type confirmed. |
| Maki Maki no Mi | [Raizo](https://one-piece.com/character/Raizo/index.html) | Existing user link confirmed. |
| Mato Mato no Mi | [Vander Decken IX](https://one-piece.com/character/Vander_Decken/index.html) | Existing user link confirmed. |
| Memo Memo no Mi | [Charlotte Pudding](https://one-piece.com/character/Charlotte_Prin/index.html) | Existing user link confirmed. |
| Mira Mira no Mi | [Charlotte Brûlée](https://one-piece.com/character/Brulee/index.html) | Existing user link confirmed. |
| Mori Mori no Mi | [Aramaki](https://one-piece.com/character/Aramaki/index.html) | Existing user link and Logia type confirmed. |
| Noro Noro no Mi | [Foxy](https://one-piece.com/character/Foxy/index.html) | Existing user link confirmed. |
| Numa Numa no Mi | [Caribou](https://one-piece.com/character/Caribou/index.html) | Existing user link confirmed. |
| Oshi Oshi no Mi | [Morley](https://one-piece.com/character/Morley/index.html) | Existing user link confirmed. |
| Pamu Pamu no Mi | [Gladius](https://one-piece.com/character/Gladius/index.html) | Existing user link confirmed. |
| Pero Pero no Mi | [Charlotte Perospero](https://one-piece.com/character/perospero/index.html) | Existing user link confirmed. |
| Pika Pika no Mi | [Borsalino](https://one-piece.com/character/Borsalino/index.html) | Existing user link and Logia type confirmed. |

## Campaign batch 009

Batch 009 reviewed 20 Devil Fruit records against official character profiles. All 20 profiles support the existing current-user edge; no duplicate ownership triples were added. Bian's profile explicitly identifies the Mushi Mushi no Mi, Model Hornet, as Zoan, matching the existing type assertion. The other profiles did not explicitly establish the ontology's broad type. The reviewed profiles do not settle absent previous-user facts; those remain unknown. The full per-fruit ledger is `work/research/batch-009-results.json`.

| Fruit | Official profile | Review result |
|---|---|---|
| Poke Poke no Mi | [Marco / Whitebeard Pirates roster](https://one-piece.com/character/marco/index.html) | Blamenco association confirmed. |
| Riki Riki no Mi | [Doc Q / Blackbeard Pirates roster](https://one-piece.com/character/Doc_Q/index.html) | Jesus Burgess association confirmed. |
| Shibo Shibo no Mi | [Charlotte Smoothie](https://one-piece.com/character/Charlotte_smoothies/index.html) | Existing user link confirmed. |
| Shiku Shiku no Mi | [Doc Q](https://one-piece.com/character/Doc_Q/index.html) | Existing user link confirmed. |
| Shiro Shiro no Mi | [Capone Bege](https://one-piece.com/character/Capone_Bege/index.html) | Existing user link confirmed. |
| Tama Tama no Mi | [Baron Tamago](https://one-piece.com/character/Baron_Tamago/index.html) | Existing user link confirmed. |
| Ton Ton no Mi | [Machvise](https://one-piece.com/character/machvice/index.html) | Existing user link confirmed. |
| Tsutsu Tsutsu no Mi | [Urban](https://one-piece.com/character/72903/index.html) | Existing user link confirmed. |
| Uma Uma no Mi | [Pierre](https://one-piece.com/character/Pierre/index.html) | Existing user link confirmed. |
| Wara Wara no Mi | [Basil Hawkins](https://one-piece.com/character/hawkins/index.html) | Existing user link confirmed. |
| Woshu Woshu no Mi | [Tsuru](https://one-piece.com/character/Tsuru/index.html) | Existing user link confirmed. |
| Yami Yami no Mi | [Marshall D. Teach](https://one-piece.com/character/Marshall_D_Teech/index.html) | Current user confirmed. |
| Yomi Yomi no Mi | [Brook](https://one-piece.com/character/brook/index.html) | Existing user link confirmed. |
| Hebi Hebi no Mi, Model Anaconda | [Boa Sandersonia](https://one-piece.com/character/Boa_Sandersonia/index.html) | Existing user link confirmed. |
| Hebi Hebi no Mi, Model King Cobra | [Boa Marigold](https://one-piece.com/character/Boa_Marigold/index.html) | Existing user link confirmed. |
| Inu Inu no Mi, Model Dachshund | [Lassoo](https://one-piece.com/character/LASSOO/index.html) | Existing user link confirmed. |
| Mushi Mushi no Mi, Model Hornet | [Bian](https://one-piece.com/character/bian/index.html) | Existing user link and Zoan type confirmed. |
| Neko Neko no Mi, Model Leopard | [Rob Lucci](https://one-piece.com/character/Rob_Lucci/index.html) | Existing user link confirmed; malformed Japanese label corrected. |
| Ushi Ushi no Mi, Model Bison | [Dalton](https://one-piece.com/character/Dalton/index.html) | Existing user link confirmed; incomplete Japanese label corrected. |
| Gura Gura no Mi | [Teach](https://one-piece.com/character/Marshall_D_Teech/index.html), [Edward Newgate](https://one-piece.com/character/edward_newgate/index.html) | Current and previous users confirmed. |

The official Rob Lucci and Dalton profiles provide complete Japanese canonical fruit names. Batch 009 removes the incomplete scraped labels `ネコネコの実 モデル“”` and `ウシウシの実 モデル`, and adds `ネコネコの実 モデル 〝豹（レオパルド）〟` and `ウシウシの実 モデル 〝野牛（バイソン）〟`. Each corrected label has statement-level provenance in `ontology/patches/campaign-batch-009.add.ttl`; removal reasons are in the companion `.remove.ttl` patch. No current-user, fruit-type, or other fruit assertion was duplicated or changed.

## Campaign batch 010

Batch 010 reviewed nine Devil Fruits, six ships, and five characters. Official profiles confirm all nine existing current-user links. The profiles explicitly classify the Allosaurus, Phoenix, and Seiryu models as Ancient or Mythical Zoan, matching current type/subtype assertions. No type was promoted from a source that only names an ability. The complete per-entity findings are in `work/research/batch-010-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| Jiki Jiki no Mi | [Eustass Kid](https://one-piece.com/character/kid/index.html) | Current-user link confirmed. Prior-user John remains unverified here. |
| Mera Mera no Mi | [Sabo](https://one-piece.com/character/sabo/index.html), [Portgas D. Ace](https://one-piece.com/character/ace/index.html) | Current Sabo and previous Ace links confirmed. |
| Mochi Mochi no Mi | [Charlotte Linlin and the Big Mom Pirates roster](https://one-piece.com/character/CharlotteLinlin/index.html) | Katakuri current-user link confirmed; no previous user inferred. |
| Ope Ope no Mi | [Trafalgar Law](https://one-piece.com/character/law/index.html) | Current-user link confirmed. The placeholder previous-user node remains unverified. |
| Soru Soru no Mi | [Charlotte Linlin](https://one-piece.com/character/CharlotteLinlin/index.html) | Current-user link confirmed. Carmel's previous-user assertion remains pending direct verification. |
| Ryu Ryu no Mi, Model Allosaurus | [X Drake](https://one-piece.com/character/X_Drake/index.html) | User, Ancient Zoan type/subtype and model name confirmed; Japanese label added. |
| Tori Tori no Mi, Model Phoenix | [Marco](https://one-piece.com/character/marco/index.html) | User, Mythical Zoan type/subtype and model name confirmed; Japanese label added. |
| Uo Uo no Mi, Model Seiryu | [Kaido](https://one-piece.com/character/Kaido/index.html) | User, Mythical Zoan type/subtype and model name confirmed; Japanese label added. |
| Ushi Ushi no Mi, Model Giraffe | [Kaku](https://one-piece.com/character/Kaku/index.html) | User and model confirmed; incomplete Japanese label corrected. The broad type was not reclassified from this profile alone. |
| Queen Mama Chanter | [Official episode 924 synopsis](https://one-piece.com/anime/o5329/index.html) | Big Mom ship/owner association confirmed; ship type and time interval left unspecified. |
| Moby Dick | [Official product archive](https://one-piece.com/figure/o1593/index.html) | Whitebeard Pirates operator association confirmed; owner/type not promoted from this source. |
| Oro Jackson | [Tom profile](https://one-piece.com/character/Tom/index.html), [official ship entry](https://one-piece.com/figure/o6143/index.html) | Tom builder and Roger ship-owner links confirmed. |
| Red Force | [Official ship archive](https://one-piece.com/figure/o1643/index.html), [Shanks](https://one-piece.com/character/Shanks/index.html) | Shanks owner association confirmed; operator/type interval not inferred. |
| Going Merry | [Official Vivre Card revision history](https://one-piece.com/vivre/revision/index.html), [Straw Hat crew](https://one-piece.com/character/Mugiwarano_itimi/index.html) | Crew/operator association confirmed as historical at the profile snapshot; temporal annotation added without chapter bounds. Direct ownership semantics were not inferred. |
| Thousand Sunny | [Franky](https://one-piece.com/character/franky/index.html), [Straw Hat crew](https://one-piece.com/character/Mugiwarano_itimi/index.html), [Vivre Card revision](https://one-piece.com/vivre/revision/index.html) | Builder and crew/operator associations confirmed; temporal annotation marks current at the profile snapshot without chapter bounds. |
| Gaimon | [Official profile](https://one-piece.com/character/Gaimon/index.html) | Island and former-pirate/treasure-guard profile reviewed; no new assertion needed. |
| Judy | [Official profile](https://one-piece.com/character/Judy/index.html) | Sabaody Archipelago origin added as a specific location alongside the broader Grand Line value. The profile says she was shot but does not resolve death or recovery; existing status retained. |
| Egana | Official character-site exact-name search | No profile surfaced; existing statements remain unverified, not false. |
| Marumieta | Official character-site exact-name search | No profile surfaced; existing statements remain unverified, not false. |
| Oide | Official character-site exact-name search | No profile surfaced; existing statements remain unverified, not false. |

The add patch supplies four official Japanese model-name labels and Judy's specific origin, each with statement-level provenance. It replaces the incomplete Giraffe label `ウシウシの実 モデル“”` with `ウシウシの実 モデル 〝麒麟（ジラフ）〟`. Two temporal statement records qualify the existing Straw Hat operator links: Going Merry is historical and Thousand Sunny current at the Vivre Card profile snapshot; neither gets an invented chapter interval. These annotations do not change the timeless triples. Unverified prior-user claims and ship-owner/operator semantics remain explicitly open.

## Campaign batch 011

Batch 011 reviewed 20 characters and affiliation entities. Four source-backed assertions were added: Aswa–Arabasta Kingdom, Banchina–Syrup Village, Cowboy–Super Spot-Billed Duck Troops, and Cowboy's official Japanese label. The per-entity findings and open-world notes are in `work/research/batch-011-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| An Zengaīna | [Official profile](https://one-piece.com/character/Anzengaina/index.html) | Grand Line origin and January 31 birthday match existing values; prisoner description does not supply a new status fact. |
| Anjo | [Official profile](https://one-piece.com/character/Anjou/index.html) | January 1 birthday and Rogue Town profile location confirmed. Existing East Blue origin was not overwritten; the profile does not explicitly state birthplace. |
| Aswa | [Official profile](https://one-piece.com/character/Asuwa/index.html) | Arabasta Kingdom placement confirmed; affiliation added. Her parent relation to Koza is not modeled by the current predicates. |
| Banchina | [Official profile](https://one-piece.com/character/Banchina/index.html) | Syrup Village and December 17 birthday confirmed; village affiliation added. Her parent relation to Usopp remains unmodeled. |
| Batchee | [Official profile](https://one-piece.com/character/Batch/index.html) | Profile identifies Batchee as a fly and confirms July 1 birthday and East Blue origin; existing date and origin retained. Unknown status remains unknown. |
| Chimney | [Official Vivre Card listing](https://one-piece.com/vivre/info/index.html) | Character listing confirms this is an individual, not an affiliation; erroneous affiliation class removed. |
| Chouchou | [Official profile](https://one-piece.com/character/Chouchou/index.html) | Dog, Orange Town, and November 22 birthday match the existing character facts; erroneous affiliation class removed. |
| Cowboy | [Official profile](https://one-piece.com/character/Cowboy/index.html) | Official name カウボーイ and Super Spot-Billed Duck Troops affiliation confirmed. Removed four group-name values copied onto the character and linked him to the troop. |
| Pacifista | [Official profile](https://one-piece.com/character/Pacifista/index.html) | Described as a 689 cm human weapon developed by Vegapunk for the Navy, not an organization. Character and human-weapon occupation retained; erroneous affiliation type and rule-derived World Government organization classification removed. |
| Super Spot-Billed Duck Troops | [Official ONE PIECE animal-collection announcement](https://one-piece.com/news/82813/index.html), [Cowboy profile](https://one-piece.com/character/Cowboy/index.html) | A troop/group rather than an individual; retained its affiliation type and removed its erroneous character type. No unsupported member roster was added. |
| Ally, Anba, Azuki, Baburu, Biyo, Brontosaurus, O-Chōchō, Chōkyūmei-no Chōsuke, Colon | Official character-site exact-name/profile searches | Search did not independently surface an exact profile in this pass; existing assertions were not treated as false. |
| BellyOverview | Official character-site search; graph identity metadata | `opwikiID` points to a `Belly#Overview` fragment and the node has currency-like labels but no character details. Possible mistaken character typing remains unresolved; no type was removed without direct identity evidence. |

The type and copied-label removals are in `ontology/patches/campaign-batch-011.remove.ttl`; new facts have statement-level source provenance in the `.add.ttl` file. The rule-based World Government classifier no longer treats Pacifista as an organization. No `owl:sameAs` or negative facts were introduced.

## Campaign batch 012

Batch 012 performed a partial official-profile pass over 20 characters. No RDF patch was applied: the official material surfaced several identity/type questions but did not justify speculative identity splits or class changes. Findings are checkpointed in `work/research/batch-012-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| Crocus | [Official profile](https://one-piece.com/character/Crocus/index.html) | Birthday, former Roger Pirates role, and Lighthouse Keeper occupation reviewed. The extra `Affiliation` class on this individual remains a candidate modeling error. |
| Gedatsu | [Official profile](https://one-piece.com/character/Gedatsu/index.html) | Birthday, former Skypiea role, and Hot Spring Island foreman role reviewed. The extra `Affiliation` class remains a candidate error; role temporality needs cautious modeling. |
| Emet | [Official profile](https://one-piece.com/character/Emet/index.html), [official Egghead story summary](https://one-piece.com/story/egghead/index.html) | Iron Giant identity and activation during Egghead confirmed; current operational status remains unknown. |
| Domo-kun | [Official profile](https://one-piece.com/character/Domo_kun/index.html) | The profile identifies Domo-kun as an alien and calls Nnke-kun a companion. The combined graph node needs an identity/splitting review; no second entity was invented. |
| Cyrano and D.R. | [Official *MONSTERS* character announcement](https://one-piece.com/news/64503/index.html) | Confirms both as characters from Oda's *MONSTERS* one-shot adaptation. No transfer into main-series continuity or relationship inference was made. |
| Daidalos, Deigoro, Doran, Eiri, Elbow, Esta, Ettara Chaunkai, Fukumi, Furika, Gama Pyonnosuke, Genrin, George Black, Gimlet, Glutbunny | Official exact-name character-site searches | No exact official profiles surfaced in this pass. Existing facts remain unverified rather than false. Doran/Dolan spellings and George Black's Impel Down label remain open source-review items. |

Potential Affiliation-class errors, the combined Domo-kun/Nnke-kun node, the George Black label, and Doran/Dolan spelling are recorded as unresolved. This batch made no factual additions and preserved unknown status and historical statements.

## Campaign batch 013 (partial)

All 20 entities in campaign batch 013 received a first-pass partial source review. The patch adds a named record for Helmeppo's approximate Cross Guild bounty estimate, adds Island Eater's official birthday and origin, and records ten current/historical annotations for sourced roles and affiliations. It removes four erroneous `Affiliation` class assertions and both directions of a Hocker–Chouchou edge that had used `affiliatesWith` for pet ownership. No general ownership relation was invented. The patch and per-entity evidence ledger are `ontology/patches/campaign-batch-013.add.ttl`, `ontology/patches/campaign-batch-013.remove.ttl`, and `work/research/batch-013-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| Helmeppo | [Official profile](https://one-piece.com/character/Helmeppo/index.html) | Profile lists Headquarters rank 少佐 (represented by the existing Lieutenant Commander term), SWORD, and an approximate 100,000,000-berry Cross Guild bounty estimate. The named bounty record keeps the Cross Guild qualifier and does not assert a Government-issued bounty. Three affiliations/rank temporal annotations are current at the profile snapshot. |
| Hocker | [Official profile](https://one-piece.com/character/Hocker/index.html) | Identified as an individual pet-food shop owner and Chouchou's owner; source says he died three months before Luffy arrived. Existing deceased status and shop-owner occupation were retained and the role was marked historical. Both `affiliatesWith` directions between Hocker and Chouchou were removed because they model ownership as affiliation; owner-to-pet remains open pending a suitable predicate. |
| Iceburg | [Official profile](https://one-piece.com/character/Iceberg/index.html) | Current mayor of Water Seven and president of Galley-La Company, matching existing occupation/affiliation values; four temporal annotations record these profile-snapshot facts. Birthday and residence already match. |
| Johnny | [Official profile](https://one-piece.com/character/Jonny/index.html), [official Vivre Card listing](https://one-piece.com/vivre/info/index.html) | Identified as an individual; current fisherman and former bounty hunter roles match existing occupation values and were time-qualified. Birthday already matches. |
| Island Eater | [Official profile](https://one-piece.com/character/Island_Eater/index.html), [official volume 15 page](https://one-piece.com/comics/o15/index.html) | Identified as a giant goldfish. Added April 21 birth date and Little Garden coast as origin. The official volume summary says Dorry and Brogy defeated it; this wording was not used to change its existing status. |
| Jobo | [Official profile](https://one-piece.com/character/Jobo/index.html) | The official profile confirms the individual and provides descriptive characterization; it does not support an additional organization or occupation assertion. |
| Iscat | [Official character directory](https://one-piece.com/character/syllabary/index.html?category=&page=3&sort=asc), [official episode 1159 summary](https://one-piece.com/anime/80329/index.html) | The directory lists Iscat under Elbaf, and the episode summary depicts Iscat carrying the escaping Straw Hats. The current Elbaf category is not enough to select a precise relation in the ontology, so no new edge was added. |
| Kairo Kureyo | [Official profile](https://one-piece.com/character/CairoCreyo/index.html) | The profile says he was imprisoned in Impel Down Level 5 and completely froze. Existing status remains Unknown because this is a described past event and the ontology has no matching, temporally precise imprisonment predicate. |
| Gorobe, Han, Hana, Hara, Jugemu Jugemuko, Kashigami's Child, Kinbo | [Official character directory](https://one-piece.com/character/syllabary/index.html); relevant [episode 909](https://one-piece.com/anime/o5241/index.html), [916](https://one-piece.com/anime/o5299/index.html), [937](https://one-piece.com/anime/o5453/index.html), [955](https://one-piece.com/anime/o5617/index.html), [973](https://one-piece.com/anime/o5749/index.html), [188](https://one-piece.com/anime/188/index.html), and [904](https://one-piece.com/anime/o5181/index.html) summaries | Exact-name directory/profile checks and relevant episode summaries did not confirm additional individual facts for these minor characters. Existing status, residence, and relationship assertions remain unverified; no town-level claims were assigned to individuals. |
| Hilmungardr, Hinokizu, Jew Wall, Jörmungandr, Kakukaku | [Official character directory](https://one-piece.com/character/syllabary/index.html), [Episode 1115 summary](https://one-piece.com/anime/68212/index.html), [Episode 146 summary](https://one-piece.com/anime/146/index.html) | No direct profile was surfaced for these exact names. Episode 1115 confirms the burn-scar epithet is discussed without identifying the person. Jew Wall's preferred label conflicts with a likely person/artifact distinction; without an authoritative direct source, identity/type/labels remain open. No speculative merges or corrections were made. |

The record count includes partial source checks rather than full verification. Findings for all 20 are recorded in `work/research/batch-013-results.json`; unsupported identity, status, and relationship fields remain unknown. No identity merges or negative assertions were introduced. Batch 014 is now active; current entities and queue counts are in `docs/ONTOLOGY_CAMPAIGN_PROGRESS.md`.


## Campaign batch 014

All 20 batch entities received a first-pass official-source review. The source ledger is `work/research/batch-014-results.json`. Eight RDF facts were added: seven directly sourced facts and one modeled temporal inference. These include a named Devil Fruit individual and its Japanese label, type, subtype, and previous-user relation for Orochi’s Hebi Hebi no Mi, plus Baldimore as Kitton’s residence and a location with its Japanese label. Seven reified annotations qualify existing Kokoro and Koza occupations/affiliations and Kumadori's former CP9 affiliation. Four erroneous `Affiliation` class assertions were removed for Orochi, Koza, Kumadori, and Matsuge.

| Entity | Official source | Review result |
|---|---|---|
| Kurozumi Orochi | [Official profile](https://one-piece.com/character/Kurozumi_Orochi/index.html), [official episode 1075](https://one-piece.com/anime/63686/index.html) | Added the missing Yamata no Orochi fruit individual, its Japanese label, Zoan type, Mythical Zoan subtype, and a previous-user edge. The previous-user designation is a modeled inference from the official fruit profile, the official recap of Denjiro cutting Orochi down, and the graph’s existing deceased status; no current successor is asserted. Removed erroneous affiliation typing; birthday and Wano shogun role already existed. |
| Kitton | [Official profile](https://one-piece.com/character/kittonn/index.html) | Added Baldimore as a location and Kitton's residence there. |
| Kokoro | [Official profile](https://one-piece.com/character/kokoro/index.html) | Existing current stationmaster and former Tom's secretary roles were temporally qualified; other checked profile facts matched. |
| Koza | [Official profile](https://one-piece.com/character/Koza/index.html) | Removed erroneous affiliation typing; annotated environmental minister and Sand-Sand Clan leader roles current at the profile snapshot and rebellion leadership historical. Birthday and existing affiliations matched. |
| Kumadori | [Official profile](https://one-piece.com/character/Kumadori/index.html) | Removed erroneous affiliation typing and annotated CP9 membership historical, as the profile explicitly says former CP9. The separate CP0 edge is unresolved and retained. |
| Mocha | [Official profile](https://one-piece.com/character/mocha/index.html) | Birthday and laboratory-child description reviewed; no supported change identified. |
| Matsuge / Eyelashes | [Official profile](https://one-piece.com/character/Eyelashes/index.html), [official product archive](https://one-piece.com/figure/o715/index.html) | Removed erroneous affiliation typing. Membership remains unresolved: the profile header lists the duck troop, while official product copy calls Matsuge an applicant. |
| Motzel | [Official profile](https://one-piece.com/character/Mr_Motzel/index.html) | East Blue origin, birthday, and Baratie customer role match existing facts. |
| Moodie | [Official profile](https://one-piece.com/character/Moodie/index.html) | East Blue origin and birthday match; dining context with Fullbody reviewed. |
| Koito, Koiwa, Konbu, Kumagoro, Lady Tree, Makino's Child, Mario, Guppy Mermaid Quintuplets, MIKIO ITOO, Milo, Mosa-kō | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name profile searches | No direct exact-name profile surfaced in this pass. Current graph assertions were not treated as false; identity, relationship, residence, status, or spelling gaps remain unresolved per the entity ledger. |

These are partial checks: an official profile review does not independently verify every upstream field. No negative facts or identity merges were added. Batch 015 is active; queue and resumption state are in `docs/ONTOLOGY_CAMPAIGN_PROGRESS.md`.


## Campaign batch 015 (partial)

All 20 entities in batch 015 received a first-pass official-source review. Two organization edges were added from the official character directory, each with statement-level provenance. Twelve exact-name searches did not surface direct profiles; these are recorded as open search gaps, not negative facts. The per-entity evidence is checkpointed in `work/research/batch-015-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| Muginn | [Official syllabary directory](https://one-piece.com/character/syllabary/index.html?category=M&page=3&sort=asc) | Directory lists Muginn under organization Elbaf. Added `Muginn affiliatesWith Elbaph`; existing Land of Gods residence is a separate relation. |
| Mukkashimi Tower | [Official ONE PIECE.com column](https://one-piece.com/greg/o20150304_0361/index.html) | Official column identifies the named recurring Colosseum spectator and says Oda supplied the name in SBS volume 75. Existing Japanese label matches; English label and other metadata remain unverified. |
| Nika | [Luffy profile](https://one-piece.com/character/luffy/index.html), [official volume 104](https://one-piece.com/comics/o104/index.html) | Confirms Nika as the Devil Fruit model name. It does not verify the standalone node's individual identity, debut, or status; those remain open. |
| Octopako | [Official profile](https://one-piece.com/character/Octopako/index.html) | Birthday and Gyoverly Hills upbringing reviewed. The profile does not establish birthplace or current residence from that upbringing. |
| Pankuta Dakeyan | [Official profile](https://one-piece.com/character/Punkcootadakeyan/index.html) | Birthday and Grand Line origin match. The profile describes a new Impel Down prisoner; no incarceration edge was added. |
| Pinky | [Official profile](https://one-piece.com/character/Pinky_the_Strange_Bird/index.html) | Birthday, East Blue origin, and monstrous-bird description match the graph. |
| Piper | [Official syllabary directory](https://one-piece.com/character/syllabary/index.html?category=H&page=15&sort=desc) | Directory lists Piper under the New Giant Warrior Pirates; added the source-backed affiliation edge. |
| Nekozaemon | [Official ONE PIECE.com column](https://one-piece.com/greg/o20161005_0647/index.html) | Column identifies Nekozaemon as Kanjuro's cat creation and notes the anime voice actor. Identity reference reviewed; status and other metadata remain open. |
| Mouthto Mouthyan, Muti, Nakaiwa, Nanday, Needle God, Noriko, Oiwa, Oran, Rakuda, Renona Topakka, Roche Tomson, Roronoa Arashi | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Targeted exact-name searches restricted to the official character site did not surface direct profiles. This search limitation does not establish nonexistence or invalidate current facts; identity and metadata remain open pending a direct primary source. |

Batch 015 first-pass review is checkpointed. No fields were negated based on missing direct profiles.

## Campaign batch 016 (partial)

All 20 entities in batch 016 received first-pass source reviews. One unsupported deceased-status assertion was removed for Ryunosuke; no additions have been proposed yet; source findings are checkpointed in `work/research/batch-016-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| Russian | [Official ONE PIECE.com column](https://one-piece.com/greg/o20210916_1249/index.html), [official anime column](https://one-piece.com/greg/o20160120_0509/index.html) | Official columns discuss Russian in connection with Senor Pink and reference manga chapters 775 and anime episode 715. Relationship, status, and residence facts remain for direct review. |
| Ryunosuke | [Official episode 753 summary](https://one-piece.com/anime/o3013/index.html), [official dragon column](https://one-piece.com/62797/index.html) | Episode summary says the named dragon was Kanjuro's drawing brought to life and returned to the drawing after its role. Removed the unsupported `Deceased` status, leaving status unknown; the official column confirms its artificial wingless-dragon kind. |
| Samurai Batts | [Official profile](https://one-piece.com/character/Samurai_Bats/index.html) | Official profile confirms Grand Line origin, March 8 birthday, and a Kyuka Island association; existing origin and birthday match. No residence or affiliation was inferred from the header. |
| Shimotsuki Furiko | [Official Ushimaru profile](https://one-piece.com/character/Shimotsuki_Ushimaru/index.html) | Profile states Furiko is Ushimaru's older sister and Roronoa Zoro's grandmother. The ontology lacks a family predicate, so the sourced relation is held for schema review. |
| Tama | [Official O-Tama profile](https://one-piece.com/character/Otama/), [official character information](https://one-piece.com/figure/64822/index.html) | O-Tama's fruit, Wano locations, and birthday are confirmed, but legacy `op:Tama` has a Pet occupation and Sphinx residence and is distinct from `op:Kurozumi_Tama`. No fruit edge or merge is made until the URI identity is resolved. |
| Torasaburo | [Official ONE PIECE.com column](https://one-piece.com/greg/o20160309_0527/index.html) | Column discusses Torasaburo alongside Ryunosuke in its Kanjuro-artwork discussion and refers to their resting places. Identity reference reviewed; status and other metadata remain open. |
| Roxanne, Saikoro, Saki, Sapoten Graveyard Buried People, Shin Jaiya, Sig, Sind, Stomp, Suzume, Tera, Togare, Tokijiro, Uhho | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Targeted exact-name searches did not surface direct profiles. These are open research gaps, not negative facts; node identity and class questions remain unresolved for Sig, Stomp, and Sapoten Graveyard Buried People. |
| Trafalgar Lami | [Official episode 701 summary](https://one-piece.com/anime/o2795/index.html), [Law profile](https://one-piece.com/character/law/index.html) | Episode summary identifies Lami as Law's younger sister and describes the Flevance tragedy. The ontology has no family predicate, so no sibling edge or status assertion was added. |

Batch 016 first-pass review is checkpointed. Its open-source gaps and modeling questions remain recorded for follow-up; no search absence was converted into a negative fact.

## Campaign batch 017 (first-pass complete)

All 20 entities reserved in batch 017 received first-pass reviews. Eight have direct official-source reviews; twelve remain exact-name profile or identity gaps, recorded as open questions rather than negative facts. The patch removes two erroneous `Affiliation` class assertions and the unsupported exact age value for Zunesha. Findings are checkpointed in `work/research/batch-017-results.json`. The isolated patch comparison is -3 asserted / +2 inferred triples; its fixed 200-game paired comparison is unchanged (73.5% top-1, 92% within three, 23.8 average questions, 27 median, 22.3% unknown answers, 100% valid questions). Yosaku role timing and a Zunesha lower-bound age predicate remain modeling follow-ups.

| Entity | Official source | Review result |
|---|---|---|
| Agyo | [Official profile](https://one-piece.com/character/agyou/index.html) | Profile confirms the Corrida Colosseum fighter-lion identity, November 29 birthday, and defeat in Block D; existing character, affiliation, birthday, and debut assertions were reviewed. No new RDF assertion was needed. |
| Sora (comic hero) | [Official Episode 783 recap](https://one-piece.com/anime/o3093/index.html) | The recap identifies Sora as the hero of an in-world illustrated story based on real Marine heroes and opposing Germa. This supports the extension node’s fictional scope; no new facts were added. |
| Urbain / Urban | [Official Urban profile](https://one-piece.com/character/72903/index.html) | The official profile found is for Urban (ウルバン), a Vice Admiral with manga debut chapter 1089. The queued Urbain is labeled ユルバンさん / Yuruban-san and debuts in chapter 964; no profile facts were transferred and the URIs remain separate. |
| Wanda | [Official profile](https://one-piece.com/character/wanda/index.html) | Profile identifies Wanda as an individual Mink, King's Bird, and Musketeer; existing birthday, affiliations, and occupations reviewed. Removed the misapplied `Affiliation` type. |
| Yuki | [Official profile](https://one-piece.com/character/Yuki/index.html) | Confirms the Little Garden girl’s birthday and Grand Line origin, and identifies her question as the start of Dorry and Brogy’s duel. Existing debut and Unknown status were reviewed; current status remains unresolved. |
| Yu | [Official profile](https://one-piece.com/character/Yuu/index.html) | Confirms Loguetown residence and East Blue origin, July 19 birthday, and first-grade status. The school-age detail was not forced into an occupation predicate; existing triples were retained. |
| Yosaku | [Official profile](https://one-piece.com/character/Yosaku/index.html) | Birthday and bounty-hunter/fisherman roles match; profile describes becoming a fisherman with Johnny. Removed the misapplied `Affiliation` type. Temporal qualifiers for the role transition remain a modeling follow-up. |
| Zunesha | [Official profile](https://one-piece.com/character/Zunesha/index.html) | Profile confirms Zunesha is over 1,000 years old and carries Mokomo Dukedom. Removed the unsupported exact age of 1,000 because no lower-bound age predicate exists; other reviewed values were retained. |

| Uzu, Vegapants, Victoria Shiruton Doruyanaika, Waruno Furishiro, Willie Gallon, O-Yame, Zabo, Jack-in-the-Box Zombie, Rug Bear Zombie, Wall Zombie, Zururin, Aegir | [Official character directory](https://one-piece.com/character/syllabary/index.html), plus [Episode 342 recap](https://one-piece.com/anime/342/index.html) for the zombie setting | Targeted official-site exact-name searches did not surface direct profiles for these nodes. The official search surfaced Sabo, not Zabo, so those identities remain separate. Episode 342 supports only general animated objects in Hogback’s mansion, not the names or individual identities of the three queued zombie nodes. Existing assertions remain unresolved; no search absence was treated as falsity and no RDF change was made.

Batch 017 first-pass review is complete. Search gaps, identity ambiguities, and the two modeling follow-ups remain checkpointed; the batch patch and game comparison are validated.


## Campaign batch 018 (first-pass complete)

All 20 queued entities received an initial source review. Ten had an applicable official profile or editorial source; ten exact-name profile searches did not resolve identity. The latter remain explicit source gaps in `work/research/batch-018-results.json`, not negative evidence. Nine entities received source-backed graph changes in the isolated patch: Aisa (Mantra/Observation Haki), Akehende (Marines affiliation), Akumai (historical Baroque Works relation), Bekori (historical kingship and Sorbet affiliation), Bingo (historical priest and cooper roles), Bogard (Marines affiliation), Bongo (historical lumber-dealer role), Bulldog (historical kingship and Sorbet affiliation), and Bungo (historical arsonist role). Every change has statement-level provenance; temporal annotations preserve existing assertions and do not imply an unqualified present-day role.

| Entity | Official source | Review result |
|---|---|---|
| Aisa | [Official profile](https://one-piece.com/character/Aisa/index.html) | Profile confirms Mantra and presence sensing; canon terminology supports the Observation Haki mapping. Added the positive Haki relation. |
| Akehende | [Official profile](https://one-piece.com/character/Akehende/index.html) | Navy Headquarters Rear Admiral profile; added Marine affiliation, complementing the existing rank occupation. |
| Akudai Kanzaburo | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; identity and existing claims remain open. |
| Akumai | [Official profile](https://one-piece.com/character/Akumai/index.html) | Former Baroque Works member; annotated the existing affiliation as historical. |
| Aremo Ganmi | [Official ONE PIECE.com column](https://one-piece.com/greg/o20140423_0189/index.html) | Editorial source identifies the name as originating in SBS volume 73 and notes an anime appearance; no new graph fact was justified. |
| Asashichi | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; existing assertions remain open. |
| Asla | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; kept separate from similarly named Asura. |
| Atagoyama | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; existing assertions remain open. |
| Beak Remark | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; existing assertions remain open. |
| Beer VI | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; existing assertions remain open. |
| Bekori | [Official profile](https://one-piece.com/character/Bekori/index.html) | Identified as former King of Sorbet Kingdom and exiled; added kingdom affiliation and historical qualifiers to the existing kingship and new affiliation. No death/current-status claim was inferred. |
| Bimine | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; existing assertions remain open. |
| Bingo | [Official profile](https://one-piece.com/character/Bingou/index.html) | Profile calls him a former priest and cooper; added historical annotations to those existing occupations. |
| Birdy | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; did not infer identity from name resemblance or a Poseidon connection. |
| Bobomba | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; existing assertions remain open. |
| Bogard | [Official profile](https://one-piece.com/character/Bogard/index.html) | Navy Headquarters profile supports Marine affiliation; added the organization edge. |
| Bongo | [Official profile](https://one-piece.com/character/Bongo/index.html) | Profile identifies him as a former lumber dealer; annotated the existing occupation as historical. |
| Bulldog | [Official profile](https://one-piece.com/character/Bulldog/index.html) | Former Sorbet king and predecessor of Bekori; added Sorbet affiliation and historical kingship. No current office was inferred. |
| Bunbuku | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name search | No direct exact-name profile surfaced; identity and current graph facts remain open. |
| Bungo | [Official profile](https://one-piece.com/character/Bungo/index.html) | Profile identifies a former arsonist; annotated the existing occupation as historical. |

No absence in official search, unsupported English rendering, or ambiguous name was converted into a negative fact or entity merge. The source ledger records exact unresolved entities and evidence.

## Campaign batch 019 (first-pass complete)

All 20 entities received first-pass review: seven direct official profiles were found and 13 exact-name/profile searches remain open. The patch adds the Charlotte Gala–Big Mom Pirates affiliation, Chicken's Japanese profile alias, Conney's Sorbet Kingdom affiliation, and a historical qualifier on Clapp's enslaved role; it also removes Carmel's misapplied `Affiliation` class assertion. It preserves open-world semantics and leaves family relationships unmodeled where no suitable predicate exists. See `work/research/batch-019-results.json` for entity-level findings and unresolved searches.

| Entity | Official source | Review result |
|---|---|---|
| Bushon | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Targeted exact-name searches did not surface a direct profile; existing identity and assertions remain open. |
| Byron | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Targeted exact-name searches did not surface a direct profile; no assumptions were made about the legacy status, occupation, or Sabaody context. |
| Carmel | [Official Mother Carmel profile](https://one-piece.com/character/Mother_Carmel/index.html) | Official profile identifies her under Sheep House and confirms December 21 birthday. Removed the incorrect character-as-`Affiliation` class assertion; no other claim was removed based on profile silence. |
| Chappe | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing Caesar Clown affiliation and epithets remain open. |
| Charlotte De-Chat | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Exact-name Japanese and romanized profile searches did not surface a direct profile. Existing Charlotte Family affiliation and identity remain open. |
| Charlotte Gala | [Official profile](https://one-piece.com/character/Charlotte_Gala/index.html) | Official profile lists Big Mom Pirates and confirms September 29 birthday; added the missing Big Mom Pirates affiliation. |
| Charlotte Normande | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing family link, age, and debut assertions remain open. |
| Charlotte Wafers | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing family link, age, debut, and voice data remain open. |
| Charlotte Wiro | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; no name normalization or merge was inferred. |
| Chesskippa | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing labels, epithet, and occupation claims remain open. |
| Chichilisia | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing occupation and episode/chapter references remain open. |
| Chicken | [Official Madam Chicken profile](https://one-piece.com/character/Madam_Chicken/index.html) | Confirms February 8 birthday and names the Foosha fish-shop owner's wife as Chicken Aunt (チキンおばさん); added that alias to the matching Foosha URI. The husband relationship to Gyoru is recorded as a future schema question. |
| Chicory | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing affiliations, residence, and identity remain open. |
| Chihaya | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing Flower Capital residence and student role remain open. |
| Chuji | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; retained the existing pet occupation without assumptions about ownership. |
| Clapp | [Official profile](https://one-piece.com/character/Clapp/index.html) | Confirms Kuma's father, Buccaneer identity, and enslavement after Kuma's birth. Added historical annotation to the existing Slave occupation; father-child relationship remains unmodeled. |
| Cocox | [Official profile](https://one-piece.com/character/Kokox/index.html) | Confirms February 19 birthday, East Blue / Island of Rare Animals origin, and chicken-dog traits; existing graph facts match, so no delta. |
| Conney | [Official profile](https://one-piece.com/character/Conney/index.html) | Confirms Sorbet Kingdom queen dowager, May 21 birthday, and Bulldog's mother; added Sorbet Kingdom affiliation. Mother-child relation remains unmodeled. |
| Damask | [Official profile](https://one-piece.com/character/damask/index.html) | Confirms Dressrosa profile context, Pyromaniac epithet, fire-emitting mask, and Block D tournament entry. Existing occupation and debut were reviewed; no change was justified. |
| Demoni Aiyo | [Official character directory](https://one-piece.com/character/syllabary/index.html) | No direct exact-name profile surfaced; existing Dressrosa residence, occupation, and identity remain open. |

No absent profile search was treated as proof that an entity or graph assertion is false.

## Campaign batch 020 (first-pass complete)

All 20 reserved entities received first-pass reviews. Nine direct official profiles were found; 11 exact-name profile searches remain unresolved. The patch adds sourced affiliation/alias and bounty edges, temporal role qualifiers, and a class correction; its isolated change is +82 asserted / +31 inferred triples. No absent profile search was treated as negative evidence; the exact-name gaps are recorded in `work/research/batch-020-results.json`.

| Entity | Official source | Review result |
|---|---|---|
| Den | [Official profile](https://one-piece.com/character/Den/index.html) | Confirms Ryugu Kingdom context, shipwright and Sea Forest researcher occupations, birthday, and fish-man identity. Existing roles and Sea Forest residence match; added Ryugu Kingdom affiliation. |
| Dobby Ibadonbo | [Official profile](https://one-piece.com/character/DobbyIvadonbo/index.html) | Identifies the Impel Down inmate as held on Ace's floor; existing Prisoner of Impel Down occupation matches. Present status remains unknown. |
| Doha Ittanka II | [Official profile](https://one-piece.com/character/Do_haittanka_nisei/index.html) | Identifies a Level 6 Impel Down prisoner with a grudge against Whitebeard; existing prison occupation matches. No present-status assertion was added. |
| Dragon Number Thirteen | [Official profile](https://one-piece.com/character/Dragon_No13/index.html) | Confirms artificial origin, Punk Hazard origin, June 3 birthday, and guardian role. Existing residence, occupation, birthday, and status were reviewed; no change. |
| Francois | [Official profile](https://one-piece.com/character/Fransoir/index.html) | Confirms Newkama Land prisoner context; existing affiliation and debut assertions reviewed. |
| Fugetsu Omusubi | [Official profile](https://one-piece.com/character/Fugetsu_Omusubi/index.html) | Confirms former Kibi daimyo role 20 years ago, June 30 birthday, and capture by the Beast Pirates. Added Wano affiliation and historical annotation to the existing Daimyo occupation. |
| Gol D. Roger | [Official profile](https://one-piece.com/character/Gold_Roger/index.html) | Confirms 5,564,800,000 berry bounty, birthday, former crew captaincy, execution, and Pirate King epithet. Added a bounty record and removed the misapplied `Affiliation` class assertion. |
| Gyoru | [Official profile](https://one-piece.com/character/Gyoru/index.html) | Confirms March 7 birthday and identifies him as the Foosha fish-shop husband of Chicken Aunt. Existing birthday, origin, occupation, and residence match; spouse relation remains unmodeled. |
| Ham Burger | [Official profile](https://one-piece.com/character/King_Ham_Burger/index.html) | Confirms Ballywood kingship and July 20 birthday; existing residence and occupation match. |

Unresolved exact-name searches: Dragon Number Twenty-One, Eikon, Fen Bock, Fugetsu Kisaburo, Gattenshochinosukeo, Ginko, Ginnosuke, Giro Chintaro, Googly-Eyed, Grabar, and Hanafuda. Their existing facts remain open; no negative fact or identity merge is inferred.


## Campaign batch 021 (first-pass complete)

| Entity | Official source | Review result |
|---|---|---|
| Haredas | [Official profile](https://one-piece.com/character/Haredasu/index.html) | Identifies Weatheria and its climate-science role; added the missing Weatheria affiliation. |
| Heracles | [Official Japanese profile](https://one-piece.com/character/Hercules/index.html) | Resolves the Japanese profile ヘラクレス to Heracles and lists Boin Archipelago; added the missing affiliation. Existing residence, birthday and occupations were retained. |
| Hiriluk | [Official profile](https://one-piece.com/character/Dr_Hiriluk/index.html) | Places Dr. Hiriluk under Drum Kingdom and confirms January 12 birthday; added the kingdom affiliation, distinct from his Drum Island residence. |
| Jean Ango | [Official profile](https://one-piece.com/character/jeanango/index.html) | Confirms bounty hunter, sniper combat role, epithet, and August 14 birthday; all were already represented, so no RDF change. |
| Hanji, Happa Yamao, Haritsu Kendiyo, Herb, Hiroshi, Home, Honner, Hyoutauros, Inoichibannosuke, Inukai, Isa, Ishigo Shitemanna, Isuka, Jean Goen, Kamekichi, Kanezenny | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name searches | No direct exact-name official profile surfaced in this focused search; existing data remains open and was not treated as false. |

Batch 021 adds three source-backed affiliation edges. No negative facts or identity merges were inferred from missing profiles.

## Campaign batch 022 (first-pass complete)

| Entity | Official source | Review result |
|---|---|---|
| Komachiyo | [Official editorial column](https://one-piece.com/greg/o20210811_1245/index.html) | Describes Tama befriending Komachiyo with dango. The current graph already links them; the source does not establish ownership or formal organization membership, so no additional edge was asserted. |
| Kozuki Moria | [Official editorial column](https://one-piece.com/75622/index.html) | Discusses a possible Kozuki-clan/Wano connection but explicitly leaves it uncertain. No affiliation, origin change, or identity reconciliation was applied. |
| Kappa, Kasa, Kashigami, Katsuzo, Kazenbo, Keith, Kirinkodanuki, Kirintauros, Kisegawa, Kobe, Kotetsu, Kumae, Kuni, Kurokoma, Kurotsuru, Kyukyu, Lines, Lionbuta | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name searches | No direct exact-name official profile surfaced in this pass; existing claims remain open-world unknowns. |

All 20 entities received a first-pass review. There was no RDF delta for batch 022 and therefore no separate gameplay comparison was needed. The exact entity-level search notes are in `work/research/batch-022-results.json`.

## Campaign batch 023 (first-pass complete)

All 20 exact-name official profile searches remained unresolved in this focused pass. The official editorial discussion of Mummy disease raises it as a possibility only, so no property was added. No RDF delta was justified. Entity-level search notes are in `work/research/batch-023-results.json`.

## Campaign batch 024 (first-pass complete; late source follow-ups included)

| Entity | Official source | Review result |
|---|---|---|
| Pagaya | [Official profile](https://one-piece.com/character/Pagaya/index.html) | Confirms Skypiea context and Angel Beach residence, plus the existing birthday. Added Skypiea affiliation and the Angel Beach location/residence. |
| Pound | [Official profile](https://one-piece.com/character/Pound/index.html) | Confirms his past in Totto Land after Linlin abandoned him and his later reunion with his daughters. Added a historically qualified Totto Land residence; family predicates remain outside the current schema. |
| Portgas D. Rouge | [Official profile](https://one-piece.com/character/Portgaz_D_Rouge/index.html) | Confirms Baterilla context and her 20-month pregnancy to protect Ace. Added the official-profile Baterilla association without assigning an unsupported time interval. |
| Mornin (late follow-up) | [Official profile](https://one-piece.com/character/mornin/index.html) | Confirms Syrup Village association and October 15 birthday; the birthday already existed. Added the missing Syrup Village affiliation. |
| Rimoshifu Killingham (late follow-up) | [Official character directory](https://one-piece.com/character/syllabary/index.html?category=R&page=2&sort=asc) | Lists his Ryu Ryu no Mi, Mythical Zoan, Model: Kirin, and Knights of God affiliation. Added the missing fruit individual, classification, labels, and current-user relation. |
| Norinosuke, Nyasha, Nyornyo Nyarmani, Outlook III, Pandaman, Pandawomanmi, Pandora, Papaneel, Pascia, Potsun, Pudos, Raccoon, Recycle-Wan, Ririka, Roji, Roronoa Pinzoro | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name searches | No direct exact-name official profile surfaced in this pass; existing facts remain open-world unknowns. |

The isolated patch `ontology/patches/campaign-batch-024.add.ttl` also contains the two late follow-ups. Entity-level records are in `work/research/batch-024-results.json` and `work/research/ontology-followups-2026-10-29.json`.

## Campaign batch 025 (first-pass complete)

| Entity | Official source | Review result |
|---|---|---|
| S-Bear | [Official profile](https://one-piece.com/character/S-Bear/index.html) | Confirms Seraphim affiliation and Paw-Paw ability supplied through Green Blood; the affiliation was already present. The profile does not justify treating the copied ability as ordinary Devil Fruit ownership. |
| S-Hawk | [Official profile](https://one-piece.com/character/S-Hawk/index.html) | Confirms Seraphim affiliation and Dice-Dice ability supplied through Green Blood; the affiliation was already present. |
| S-Shark | [Official profile](https://one-piece.com/character/S-Shark/index.html) | Confirms Seraphim affiliation and Swim-Swim ability supplied through Green Blood; the affiliation was already present. |
| S-Snake | [Official profile](https://one-piece.com/character/S-Snake/index.html) | Confirms Seraphim affiliation and Love-Love ability supplied through Green Blood; the affiliation was already present. Ownership is not inferred from ability use. |
| Shimotsuki Ushimaru | [Official profile](https://one-piece.com/character/Shimotsuki_Ushimaru/index.html) | Identifies him as former daimyo of Ringo in Wano. Added Wano affiliation; existing Ringo residence retained. |
| Shimotsuki Yasuie | [Official profile](https://one-piece.com/character/Shimotuki_yasuie/index.html) | Identifies him as former daimyo of Hakumai in Wano. Added Wano affiliation; existing Hakumai and Ebisu Town residences retained. |
| Shelly | [Official profile](https://one-piece.com/character/Sherry/index.html) | Identifies Shelly as an Uma living on Long Ring Long Land. Added the residence, typed the previously untyped place as a Location, and added its English and Japanese labels. The October 31 birthday was already represented. |
| Royder, Sam, Sapi, Sarfunkel, Satchels Maffey, Scales, Sea Boar, Sennorikyuru, Serizawa, Seto, Shanba, Shin Detamaruka, Smoothy | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name searches | No direct exact-name profile surfaced in this pass. These thirteen gaps remain unknown, not negative evidence. |

The isolated patch `ontology/patches/campaign-batch-025.add.ttl` contains six sourced facts with statement-level provenance. The profile review also surfaced the need for a relation that distinguishes Green Blood copied powers from Devil Fruit ownership; no ownership edges were added. Full per-entity notes are in `work/research/batch-025-results.json`.

## Campaign batch 026 (first-pass complete)

| Entity | Official source | Review result |
|---|---|---|
| Sterry | [Official profile](https://one-piece.com/character/Stelly/index.html) | Confirms current kingship of Goa Kingdom and existing birthday, occupation, and residence. Added the missing Goa Kingdom affiliation. |
| Taco / King Tacos | [Official profile](https://one-piece.com/character/King_Tacos/index.html) | Confirms Shishano Kingdom kingship and existing birthday. Added the affiliation; typed and labeled the kingdom as an affiliation. |
| Sukoshiba Kanishitoru | [Official character directory](https://one-piece.com/character/syllabary/index.html?category=S&page=6&sort=asc) | Lists him under Impel Down, consistent with his existing guard occupation. Added the missing affiliation. |
| Tamachibi | [Official profile](https://one-piece.com/character/Tamachibi/index.html) | Confirms Sakura Kingdom and Cocoa Weed on Drum Island as place of origin. Added the affiliation and specific origin, and typed/labeled Cocoa Weed. The legacy combined residence URI remains unresolved rather than being merged by name. |
| Spector | [Official profile](https://one-piece.com/character/Spectre/index.html) | Identifies him as a Tropical Hotel employee in Mock Town. Added the sourced Hotel employee occupation; the legacy `Hotel_owner` claim remains unresolved because the profile does not establish whether he owns a different hotel. |
| Splash and Splatter | [Official profile](https://one-piece.com/character/Splash_Splatter/index.html) | Confirms the twin pirates' joint name and existing January 18 birthday. Added the official Japanese joint label and removed an import-mangled English label; the combined entity was retained. |
| Suke | [Official profile](https://one-piece.com/character/Suke_san/index.html) | Confirms the already represented Kyoshiro Family affiliation. No RDF change. |
| Terry | [Official profile](https://one-piece.com/character/Terry/index.html) | Confirms the existing Mock Town context; its bar-owner detail does not map to a safe relation beyond the existing occupation and residence. |
| Stealth Black | [Official item](https://one-piece.com/news/o20210705_12737/index.html) | Confirms Germa 66 No. 3 and use as Sanji's raid suit. The affiliation already exists; the suit-to-wearer relation is not represented and was left open. |
| O-Some, Sugamichi and Warazane, Sukune, Tabuhachiro, O-Taka, Tarara, Tegata Ringana, Tell, Tomatito, Tomozō, Tonjiru | [Official character directory](https://one-piece.com/character/syllabary/index.html) and exact-name searches | No direct source surfaced for these eleven entities in this pass; existing facts remain open-world unknowns. |

The additive patch has statement-level provenance for all new facts; the correction patch records removal of the unsupported owner role and malformed label. Per-entity findings are in `work/research/batch-026-results.json`.

### Campaign batch 027

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Tonjit | Added residence at Long Ring Long Land; official profile groups him under that location and describes his long stay after his nomadic companions moved on. | [Official Tonjit profile](https://one-piece.com/character/Tonjit/index.html) | High; official profile snapshot |
| Urashima | Added Wano affiliation; his Flower Capital residence and sumo wrestler occupation already existed. | [Official Urashima profile](https://one-piece.com/character/Urashima/index.html) | High; official profile snapshot |
| Wapol | Official profile confirms existing fruit, birthday, kingship, and former Drum Kingdom role; both kingdom affiliations retained as historically compatible. | [Official Wapol profile](https://one-piece.com/character/Wapol/index.html) | High; profile snapshot; includes historical role |
| Vegapunk satellites | Official Egghead overview identifies Atlas, Edison, Lilith, Pythagoras, Shaka, and York as six divisions of Vegapunk’s personality. The ontology lacks a satellite-of relation, so no new relation was asserted; existing affiliations were not reinterpreted. | [Official Egghead story overview](https://one-piece.com/story/egghead/index.html) | High; story reference |

The other 13 entries in batch 027 remain unresolved after exact-name profile searches. Those gaps indicate limits of discovery in this pass, not evidence against the upstream assertions.

### Campaign batch 028

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Yoshimoto | Added Arabasta affiliation from the official profile for Yoshimoto-san, whose restaurant-owner role and Alabasta debut match the ontology entity. | [Official Yoshimoto profile](https://one-piece.com/character/Yoshimoto/index.html) | High; official profile snapshot |
| Albion | Added a named Bounty record for the official 92 million berry amount; existing epithet and birthday remain unchanged. | [Official Albion profile](https://one-piece.com/character/Albion/index.html) | High; official profile snapshot |
| Abdullah | Official profile confirms the Ideo Pirates and Straw Hat Grand Fleet affiliations already present. | [Official Abdullah profile](https://one-piece.com/character/abdullah/index.html) | High; official profile snapshot |
| Yokozuna | Official profile confirms the Water Seven setting already represented by residence and Tom's Workers affiliation. | [Official Yokozuna profile](https://one-piece.com/character/Yokozuna/index.html) | High; official profile snapshot |
| A.O. and Agsilly | Official Whitebeard subordinate listing confirms already represented subordinate/ally relations. | [Official Whitebeard subordinate listing](https://one-piece.com/character/Squad/index.html) | High; official character listing |
| Wellington | An official editorial reference was reviewed but did not establish a new usable ontology assertion. | [Official editorial, chapter 763](https://one-piece.com/greg/o20141203_0315/index.html) | No change; editorial reference |

The other 13 batch entries remain unresolved after targeted exact-name searches. The separate Wano Ikkaku entry was not conflated with the official Heart Pirates character Ikkaku; similarly named entities remain distinct without direct identity evidence.

### Campaign batch 029

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Amazon | Added historical status for Gatekeeper of Skypiea and current status for Ticket Saleswoman; both occupation values already existed. | [Official Amazon profile](https://one-piece.com/character/Amazon/index.html) | High; current/former wording explicit, exact intervals unspecified |
| Attach | Added a historical qualifier to the existing Marine affiliation based on an official editorial stating he was dismissed after the Paramount War. No World Economic Journal affiliation was added because the same editorial treats the later identity as uncertain. | [Official editorial on episode 882](https://one-piece.com/greg/o20190828_1061/index.html) | Medium; editorial source, end after Paramount War, exact interval unspecified |
| Alpha | Official profile confirms CP8 affiliation and sister relation to Kalifa; affiliation exists, while the ontology has no family predicate. | [Official Alpha profile](https://one-piece.com/character/Alpha/index.html) | High; official profile snapshot |
| Amadob | Confirms existing Whitebeard subordinate affiliation and June 20 birthday. | [Official Amadob profile](https://one-piece.com/character/Amadobu/index.html) | High; official profile snapshot |
| Andre | Confirms existing Whitebeard subordinate affiliation and May 19 birthday. | [Official Andre profile](https://one-piece.com/character/Andre/index.html) | High; official profile snapshot |
| Aphelandra | Confirms existing Amazon Lily warrior role and birthday. | [Official Aphelandra profile](https://one-piece.com/character/Aphelandra/index.html) | High; official profile snapshot |
| Arthur | Confirms existing Whitebeard subordinate affiliation. | [Official Arthur profile](https://one-piece.com/character/Arthur/index.html) | High; official profile snapshot |
| Atmos | Confirms existing 13th Division Commander role and Whitebeard Pirates affiliation. | [Official Atmos profile](https://one-piece.com/character/atmos/index.html) | High; official profile snapshot |
| Babanuki | Confirms Beasts Pirates Headliner, Zou SMILE, and Prisoner Mine warden; no Devil Fruit ownership was inferred. | [Official Babanuki profile](https://one-piece.com/character/Babanuki/index.html) | High; official profile snapshot |
| Bacura | Confirms existing Amazon Lily executioner role and birthday. | [Official Bacura profile](https://one-piece.com/character/Bacura/index.html) | High; official profile snapshot |
| Banchi | Confirms former Baroque Works association and West Blue origin, already represented. | [Official Banchi profile](https://one-piece.com/character/Bunchi/index.html) | High; official profile snapshot |

Nine exact-name searches remain unresolved in this batch. The historical Marine affiliation for Attach uses an official site's editorial commentary rather than a direct character profile, so it is marked medium confidence and does not assert a new current employer.


### Campaign batch 030

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Bartholomew Kuma | Corrected the Nikyu Nikyu no Mi current-user object from a malformed URI combining Kuma and S-Bear to Kuma. Added Kuma's former 296 million berry bounty as a named Bounty record and marked the bounty relation historical. | [Official Kuma profile](https://one-piece.com/character/Bartholomew_Kuma/index.html); [official S-Bear profile](https://one-piece.com/character/S-Bear/index.html) | High; former bounty, exact interval unspecified. S-Bear's profile describes Green Blood ability use, not fruit ownership. |
| Other 19 batch entries | Exact-name official directory/profile searches did not surface a direct source in this pass. These are discovery gaps, not negative findings; current assertions remain open-world unknowns. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no facts removed. Per-entity findings: `work/research/batch-030-results.json`. |

The malformed assertion removed by `ontology/patches/campaign-batch-030.remove.ttl` was the single Nikyu Nikyu no Mi current-user triple whose object URI concatenated Bartholomew Kuma and S-Bear. It was removed because the malformed URI conflated two entities; the corrected affirmative Kuma link is supported by the official profile.

### Campaign batch 031

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Bepo | Official profile lists 1,500 berries; named Bounty record added. Heart Pirates/navigator/birthday facts already present. | [Official Bepo profile](https://one-piece.com/character/Bepo/index.html) | High; profile snapshot |
| Black Maria | Official profile confirms Kumo Kumo no Mi, Ancient Zoan, Model Rosamygale Grauvogeli, and 480 million berries; fruit model identity and bounty record added. | [Official Black Maria profile](https://one-piece.com/character/blackmaria/index.html) | High; profile snapshot |
| Bluejam | Official profile lists 14.3 million berries; named Bounty record added. Existing captain/crew/birthday facts match; character status remains unknown. | [Official Bluejam profile](https://one-piece.com/character/Bluegem/index.html) | High; profile snapshot |
| Bobby Funk | Official profile lists 36 million berries; named Bounty record added. Existing Mogaro Kingdom and birthday facts match; family relation is not modeled. | [Official Bobby Funk profile](https://one-piece.com/character/bobby_funk/index.html) | High; profile snapshot |
| Big Pan, Bishamon, Bizarre, Bjorn, Blenheim, Blondie, Bluefan, Blue Gilly | Direct official profiles or directory entries confirm existing affiliations, residence, occupations, and/or birthdays; no duplicate assertions added. | [Big Pan](https://one-piece.com/character/Big_Pan/index.html), [Bishamon](https://one-piece.com/character/Bishamon/index.html), [Bizarre](https://one-piece.com/character/Bizaaro/index.html), [official directory](https://one-piece.com/character/syllabary/index.html?category=&page=13&sort=desc), [Blenheim](https://one-piece.com/character/brenheim/index.html), [Blondie](https://one-piece.com/character/Blondie/index.html), [Bluefan](https://one-piece.com/character/Bluefan/index.html), [Blue Gilly](https://one-piece.com/character/blue_gilly/index.html) | High; official source snapshots |
| Other eight entities | Exact-name searches did not surface direct profiles in this pass. Existing assertions remain unknown rather than rejected. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no facts removed |

Per-entity findings: `work/research/batch-031-results.json`; research notes: `work/research/batch-031-notes.md`.


### Campaign batch 033

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Cavendish | Added his official-profile-listed 330 million berry bounty as a named Bounty record. His Beautiful Pirates captain role, Grand Fleet affiliation, and birthday were already represented. | [Official Cavendish profile](https://one-piece.com/character/cavendish/index.html) | High; profile snapshot, no explicit current/former bounty qualifier |
| Chadros Higelyges (Brownbeard) | Added his official-profile-listed 80.06 million berry bounty as a named Bounty record. Existing Brownbeard Pirates, Centaur Patrol Unit, and birthday facts match. | [Official Brownbeard profile](https://one-piece.com/character/brownbeard/index.html) | High; profile snapshot, no explicit current/former bounty qualifier |
| Candre | Official profile confirms Marine Headquarters affiliation and that he is Andre's twin brother. No kinship predicate exists in the ontology; no generic relation or identity assertion was added. | [Official Candre profile](https://one-piece.com/character/kandore/index.html) | High; official profile snapshot |
| Cands, Candy, Capone Pez, Capote, Carne, Chabo, Cerberus, Charlotte Amande, Charlotte Anana | Official profiles confirm existing affiliations, roles, birthdays, age, residence, or source-specific details. Capone Pez's parentage and Charlotte Amande/Anana's family positions are not modeled. Carne currently works aboard the Nasugashira iron-grill ship, but there is no suitable works-aboard predicate; existing Baratie affiliation remains. | [Cands](https://one-piece.com/character/Cans/index.html), [Candy](https://one-piece.com/character/Candy/index.html), [Capone Pez](https://one-piece.com/character/Capone_Petz/index.html), [Capote](https://one-piece.com/character/Capote/index.html), [Carne](https://one-piece.com/character/Carne/index.html), [Chabo](https://one-piece.com/character/Chabo/index.html), [Cerberus](https://one-piece.com/character/Cerberus/index.html), [Amande](https://one-piece.com/character/Charlotte_amande/index.html), [Anana](https://one-piece.com/character/Charlotte_Anana/index.html) | High; official profile snapshots; Carne's ship assignment is current per profile |
| Charlotte Akimeg and Charlotte Allmeg | Official anime episode synopsis depicts Allmeg as a combined form involving Akimeg; existing Big Mom/Charlotte affiliations are retained. No fusion predicate is available, and the finding is anime-specific. | [Official episode 875 synopsis](https://one-piece.com/anime/o4977/index.html) | High; anime episode 875 depiction |
| Cancer, Catacombo, Caucasusman, Cezar, Chao, Chap | Targeted official exact-name searches did not surface direct profiles in this pass. These are discovery gaps, not negative findings; existing graph facts remain unknown rather than rejected. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no facts removed |

Per-entity findings: `work/research/batch-033-results.json`. Patch: `ontology/patches/campaign-batch-033.add.ttl`.


### Campaign batch 034

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Charlotte Chiffon | Official profile confirms current Fire Tank Pirates affiliation, birthday, marriage to Bege, twin relation to Lola, and Charlotte daughter ordinal. Existing affiliation and birthday match; kinship/order are not modeled. | [Official Chiffon profile](https://one-piece.com/character/Charlotte_chiffon/index.html) | High; profile snapshot |
| Charlotte Compote | Official profile confirms Big Mom Pirates affiliation, October 15 birthday, and eldest-daughter ordinal. Existing birthday, affiliation, Fruit Minister occupation, and residence match. | [Official Compote profile](https://one-piece.com/character/Charlotte_Compote/index.html) | High; profile snapshot |
| Charlotte Custard | Official profile confirms Big Mom Pirates affiliation and sixth-daughter ordinal. Existing age and birthday are not stated by the profile and remain unverified, not contradicted. | [Official Custard profile](https://one-piece.com/character/Charlotte_Custard/index.html) | High for listed facts; age/birthday unresolved |
| Charlotte Broyé | Official profile confirms Big Mom Pirates affiliation, December 26 birthday, ninth-daughter ordinal, and Minister of Meringue role on Milenge Island. Existing modeled details match. | [Official Broyé profile](https://one-piece.com/character/Charlotte_broyer/index.html) | High; profile snapshot |
| Charlotte Anglais, Bavarois, Brownie, Cabaletta, Cadenza, Cinnamon, Citron, Counter | Official SBS, directory, or editorial material confirms existing birthdays, crew listing, or family grouping. No new RDF relation was added; sibling and family-order predicates are absent. | [Official SBS birthday list](https://one-piece.com/sbs/index.html), [official birthday announcement](https://one-piece.com/news/o20180904_7839/index.html), [official family roundup](https://one-piece.com/greg/o20180730_0895/index.html) | High for direct SBS/directory facts; medium for editorial summary; relation scopes vary |
| Charlotte Basskarte, Dacquoise | Official editorial commentary treats the Charlotte-family affiliation as uncertain/speculative. Existing assertions were retained pending primary-source confirmation. | [Official family roundup](https://one-piece.com/greg/o20180730_0895/index.html), [official episode-834 commentary](https://one-piece.com/greg/o20180822_0925/index.html) | Uncertain; no facts removed |
| Charlotte Angel, Basans, Chiboust, Compo, Cornstarch | Targeted direct official profile searches did not surface a corroborating entry in this pass. Existing assertions remain open-world unknowns. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no facts removed |
| Charlotte Decuplets | Official editorial material describes the group as five sons and five daughters; it does not identify the ten individuals separately. The group URI was retained. | [Official family roundup](https://one-piece.com/greg/o20180730_0895/index.html) | Medium; group-level editorial summary |

No RDF patch was warranted in batch 034. Per-entity findings: `work/research/batch-034-results.json`.


The patch adds five Black Maria fruit assertions and four bounty records with four assertions each (21 factual assertions total), each with a matching statement-level provenance record. The isolated patch comparison is +210 asserted / +75 inferred triples. The paired 200-game evaluation is unchanged on 482 candidates and seed 42 (73.5% top-1, 91.5% within three, 23.85 average questions, 27 median, 22.3% unknown answers, 100% validity). The full audit snapshot through batch 030 predates this patch.

### Campaign batch 032

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Brogy | Added the official 100 million berry bounty as a named Bounty record, with statement-level provenance. Existing Giant Warrior Pirates captain and birthday details match. | [Official Brogy profile](https://one-piece.com/character/Broggy/index.html) | High; official profile snapshot |
| Bonk Punch, Boo, Braham, Brandnew, Brew, Briscola, Building Snake, Camie | Official profiles confirm existing affiliations, rank, occupation, or profile details; no duplicates added. Brandnew’s other rank was not qualified as historical without evidence for a transition; Briscola’s SMILE is not treated as natural Devil Fruit ownership. | [Bonk Punch](https://one-piece.com/character/Bonk_Punch/index.html), [Boo](https://one-piece.com/character/boo/index.html), [Braham](https://one-piece.com/character/Braham/index.html), [Brandnew](https://one-piece.com/character/Brandnew/index.html), [Brew](https://one-piece.com/character/Brew/index.html), [Briscola](https://one-piece.com/character/burisukora/index.html), [Building Snake](https://one-piece.com/character/Building_Snake/index.html), [Camie](https://one-piece.com/character/Camie/index.html) | High; official profile snapshots |
| Other eleven entities | Exact-name searches did not surface direct profiles in this pass. Existing assertions remain unknown rather than rejected. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no facts removed |

The patch adds four factual triples and four matching provenance statements (+40 asserted / +11 inferred). Patched SHACL has zero violations or warnings, with no functional-property drops. The paired evaluation is unchanged on 482 candidates and seed 42 (73.5% top-1, 91.5% within three, 23.85 average questions, 27 median, 22.3% unknown answers, 100% validity). Per-entity results: `work/research/batch-032-results.json`; research notes: `work/research/batch-032-notes.md`.

## Campaign batch 035 — Charlotte-family source review

Official-site editorial roundup, Greg-sensei’s SUPER One Piece Course #100 (2018-07-30), [“All in the Family: Pt. 3”](https://one-piece.com/greg/o20180730_0897/index.html), covers the known Charlotte family and cites manga chapters and volumes through Whole Cake Island. It identifies Flampe as the 36th daughter, Joconde as the 27th daughter, Lola as the 23rd daughter and child of Linlin and Pound, and the twin pairing Lola–Chiffon. It lists Joscarpone as the 29th daughter and Mascarpone as the 34th son, explicitly describing them as twins. Dosmarche appears among sons of unknown ordinal. The roundup places Dolce, Dragée, Laurin, and Marnier among “Possible Named” offspring, so these are not confirmations of family status. The earlier official roundup, [“All in the Family: Pt. 2”](https://one-piece.com/greg/o20170517_0737/index.html), calls Dolce and Dragée “? Sons” and reiterates Lola/Chiffon family details.

Official anime commentary provides identity-quality caveats: [episode 834 commentary](https://one-piece.com/greg/o20180822_0927/index.html) identifies Marnier and Laurin as Big Mom Pirates while explicitly saying their family membership is uncertain; it also notes uncertainty about Dacquoise and Mobil, outside this batch. [Episode 839 commentary](https://one-piece.com/greg/o20180927_0945/index.html) calls Kanten and High-Fat potential family additions, while separately confirming Bassquarte (outside this batch). [Episode 835 commentary](https://one-piece.com/greg/o20180829_0931/index.html) explicitly confirms Dosmarche as a Charlotte-family member.

No kinship or ordinal facts were added because the graph lacks a suitable family relationship or birth-order predicate. The combined Charlotte_Dolce_and_Dragée URI is recorded as a modeling review item because the official roundup names two sons, but this evidence alone does not specify their individually attributable properties. Nine exact-name searches (Effilée, Fuyumeg, Hachée, Harumeg, Kato, Maple, Marble, Mash, Melise) did not find direct official entries; absence of a search result is not negative evidence. All per-entity outcomes and confidence labels are in `work/research/batch-035-results.json`.

## Campaign batch 036 — Charlotte-family source review and corrections

The official [Mont-d’Or character profile](https://one-piece.com/character/Montdor/index.html) identifies his Big Mom Pirates affiliation, Buku Buku no Mi ability, 120,000,000-berry bounty, April 23 birthday, and status as the Charlotte family's 19th son and Cheese Minister. The ontology already modeled the fruit and birthday information, but the fruit's `DevilFruitCurrentUser` pointed to a malformed slash-namespace URI instead of the existing `#Charlotte_Mont-dOr` character. The correction removes only that malformed object and links the fruit to the existing character URI. A named bounty record is added with statement-level provenance.

The official [Big Mom Pirates profile list](https://one-piece.com/character/CharlotteLinlin/index.html) lists Snack's 600,000,000-berry bounty. The official [Charlotte family roundup](https://one-piece.com/greg/o20180730_0897/index.html) identifies him as the 25th son and explicitly labels him a former Sweet Commander. The patch adds a named bounty record without guessing whether that amount is current or former. It adds a `Historical` temporal statement for the existing `occupation Sweet_Commander` assertion and leaves the unqualified triple intact, preserving the ontology's established additive temporal semantics. Official SBS entries for other batch members confirmed birthdays already present in the graph.

The same family roundup confirms the existing listings for Moscato (16th son), Nusstorte (12th son), Poire (19th daughter and Galette's twin), Raisin (33rd son), and Yuen (35th son); it names Myukuru as a daughter. The [official SBS birthday list](https://one-piece.com/sbs/index.html) confirms existing dates for Moscato, Myukuru, Noisette, Poire, Snack, and Yuen. [Noisette's official profile](https://one-piece.com/character/Charlotte_noisette/index.html) verifies his age, birthday, 15th-son status, finance minister role, and Kinko Island location.

The family roundup treats “Mobil” (distinct spelling from the graph's “Mobile”), Saint-Marc, Tablet, and Zuccotto as possible family members. These are not confirmations; the graph's existing family affiliations remain open review items. Seven exact-name searches remain unresolved: Mondée, Montb, Mozart, Nougat, Nutmeg, Panna, and Prim. The official roundup names “Nougo,” but no evidence establishes that this is an alias of the separate graph URI Charlotte_Nougat. Per-entity findings and the complete source URLs are in `work/research/batch-036-results.json`.

## Campaign batch 037 — cross-entity identity, affiliation, and bounty review

Official profiles for [Chess](https://one-piece.com/character/Chess/index.html) and [Kuromarimo](https://one-piece.com/character/Kuromarimo/index.html) list the Bliking Pirates and identify them as former Drum Kingdom officials. Their graph links instead pointed to a single concatenated affiliation URI. The patch replaces the shared bad links with separate Bliking Pirates and Drum Kingdom links and adds current/historical temporal records. The official [Wapol profile](https://one-piece.com/character/Wapol/index.html) says he fused Chess and Kuromarimo in his factory to create Chessmarimo; that distinct form is not owl:sameAs either constituent, and no crew membership is inferred for the form.

The official [Chew profile](https://one-piece.com/character/Choo/index.html) lists a 5.5 million berry bounty and says he was with the Sun Pirates before their dissolution, after which he acted with Arlong. The patch adds a named bounty and an additive historical qualifier for the existing Sun Pirates relationship. The official [episode 786 synopsis](https://one-piece.com/anime/o3105/index.html) places the Choco Police in Chocolat Town on Cacao Island; the previous location URI concatenated the town, island, and Totto Land. A distinct `Chocolat_Town` location now replaces that malformed residence target, while the existing Cacao Island affiliation remains.

Official profiles identify [Choi](https://one-piece.com/character/Choi/index.html) and [Colscon](https://one-piece.com/character/Collscon/index.html) as Whitebeard-affiliated pirates at the Summit War. Choi's graph already used the ally affiliation; the patch marks it historical. Colscon had been linked to the core Whitebeard Pirates crew, so the patch corrects the edge to the existing ally affiliation and marks it historical. Official profiles confirm [Concelot](https://one-piece.com/character/konsrot/index.html) belongs to Inuarashi's Musketeer Squad; his graph affiliation URI concatenated that squad with the Ninja-Pirate-Mink-Samurai Alliance. The patch replaces it with the directly supported squad link; the alliance component remains unknown, not false.

Other official profiles confirmed existing facts for [Chocolat](https://one-piece.com/character/Chocolat/index.html), [Chome](https://one-piece.com/character/Chome/index.html), [Cocoa](https://one-piece.com/character/cocoa/index.html), [Columbus](https://one-piece.com/character/Columbus/index.html), [Comil](https://one-piece.com/character/Komille/index.html), and [Conis](https://one-piece.com/character/Conis/index.html). The official [Law profile](https://one-piece.com/character/law/index.html) lists Clione among the Heart Pirates. Official editorial material names Chuchun but did not verify its Foxy affiliation. Five exact-name searches remain unresolved: Chiya, Cho, Chochinman, Coburn, and Compo. Full source scopes and confidence levels appear in `work/research/batch-037-results.json`.

### Campaign batch 038

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Coribou | Added a named Bounty record for the profile-listed 190,000,000 berries. The existing Caribou Pirates affiliation, captain role, and birthday match. The profile does not address the graph's additional Fake Straw Hat Crew edge, so it remains unresolved rather than removed. | [Official Coribou profile](https://one-piece.com/character/Coribou/index.html) | High; profile snapshot, no explicit current/former bounty qualifier |
| Curly Dadan | Added a named Bounty record for the profile-listed 7,800,000 berries. The profile also confirms Dadan Family affiliation, chief role, Mt. Colubo residence, and birthday. Its foster-parent description does not establish a safe decomposition of the graph's compound caretaker occupation URI. | [Official Curly Dadan profile](https://one-piece.com/character/Curry_Dadan/index.html) | High; profile snapshot, no explicit current/former bounty qualifier |
| Corgi, Cosette, Cosmos, Curiel, Dagama, Daifugo, Daigin, Daisy, Dalmatian, Daruma | Official profiles and the SBS birthday directory confirm corresponding existing affiliation, role, birthday, and/or ability facts. Cosmos also received an exact Amazon Lily origin edge while retaining the broader Calm Belt region. Daifugo's Scorpion SMILE is confirmed but is not represented as a distinct fruit individual because the ontology does not identify an individual SMILE fruit for this variant. Dalmatian's fruit name is not stated by the profile. | [Corgi](https://one-piece.com/character/Corgy/index.html), [Cosette](https://one-piece.com/character/Cozet/index.html), [Cosmos](https://one-piece.com/character/Cosmos/index.html), [Curiel](https://one-piece.com/character/creele/index.html), [Dagama](https://one-piece.com/character/Dagama/index.html), [Daifugo](https://one-piece.com/character/Daifugo/index.html), [Daigin](https://one-piece.com/character/Daigin/index.html), [Daisy](https://one-piece.com/character/Daisy/), [Dalmatian](https://one-piece.com/character/Dalmecia/index.html), [Daruma](https://one-piece.com/character/Daruma/index.html), [official SBS birthday directory](https://one-piece.com/sbs/index.html) | High; official profile/SBS snapshots |
| Cornelia, Cosmo, Cotton, Couran, Dachoman, Daddy Dee, Dago, Daikon | Exact-name official profile/directory searches did not surface direct supporting entries in this pass. Existing statements remain open-world unknowns. Cotton and Daikon have concatenated affiliation URIs that need source-backed decomposition; no edge was split or deleted. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no negative facts inferred |

Per-entity findings: `work/research/batch-038-results.json`. Patch: `ontology/patches/campaign-batch-038.add.ttl`.


### Campaign batch 039

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Daz Bonez | Added the official 75 million berry bounty, corrected the Supa Supa no Mi current-user edge from a malformed combined Daz/S-Hawk URI to Daz Bonez, and marked his Baroque Works affiliation historical. S-Hawk’s copied Green Blood ability is not treated as fruit ownership. | [Official Daz Bonez profile](https://one-piece.com/character/Daz_Bonez/index.html) | High; Baroque Works explicitly former; bounty profile snapshot |
| Decalvan Brothers | Replaced the subordinate classification with the official Whitebeard-allied pirate classification; did not split the group into individual members. | [Official Whitebeard/Squad profile](https://one-piece.com/character/Squad/index.html) | High; profile grouping, interval unspecified |
| Delacuaji | Replaced the subordinate classification with allied pirate and marked the Ace-rescue-era affiliation historical. | [Official Delacuaji profile](https://one-piece.com/character/Deluckahe/index.html) | High; historical Summit War affiliation |
| Dellinger | Added the official 15 million berry former bounty as a named Bounty record with a Historical qualifier. | [Official Dellinger profile](https://one-piece.com/character/dellinger/index.html) | High; explicitly former, interval unspecified |
| Demalo Black | Added the official 26 million berry bounty as a named Bounty record; the profile does not explicitly label it current or former. | [Official Demalo Black profile](https://one-piece.com/character/Demalo_Black/index.html) | High; profile snapshot, temporal status unspecified |
| Devil Dias | Added the official 60 million berry bounty and marked the slave occupation historical. His death status was not inferred. | [Official Devil Dias profile](https://one-piece.com/character/Devil_Dias/index.html) | High; past enslavement, bounty interval unspecified |
| Diez Barrels | Marked the existing Marines affiliation and Marine Officer occupation historical based on the official description “former Marine officer.” | [Official episode 704 synopsis](https://one-piece.com/anime/o2801/index.html) | High; former role, interval unspecified |
| Disco | Added Human Auction MC as a distinct occupation while retaining the existing auction-house owner occupation. | [Official Disco profile](https://one-piece.com/character/Mr_Disco/index.html) | High; profile snapshot |
| Denjiro, Diesel, Didit, Doberman, Dobon, Dogra | Official profiles or episode material confirmed existing facts; no duplicate assertions added. Identity and kinship details not represented by safe available predicates were left unchanged. | [Denjiro](https://one-piece.com/character/Denjiro/index.html), [episode 976](https://one-piece.com/anime/o5783/index.html), [episode 815](https://one-piece.com/anime/o4569/index.html), [Didit](https://one-piece.com/character/didit/index.html), [Doberman](https://one-piece.com/character/Doberman/index.html), [Dobon](https://one-piece.com/character/Dobon/index.html), [Dogra](https://one-piece.com/character/Dogura/index.html) | High; source-specific scope |
| Dashiteyaro, Davy D. Jones, Dirt Boss, Disc J, Dive, Dogya | Exact-name official-profile/directory searches did not surface direct entries in this pass. Existing assertions remain open-world unverified rather than contradicted. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; discovery gap |

The isolated patch contains 53 new factual assertions, each with statement-level provenance, including six historical annotations. See `ontology/patches/campaign-batch-039.add.ttl`, `ontology/patches/campaign-batch-039.remove.ttl`, and `work/research/batch-039-results.json`.


### Campaign batch 040

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Doll | Added the missing G-14 Base Leader occupation from her official profile; retained existing Marine Vice Admiral rank, G-14 affiliation, and residence. | [Official Doll profile](https://one-piece.com/character/Doll/index.html) | High; profile snapshot |
| Edward Weevil | Added the official 480 million berry former bounty as a named Bounty record and marked his existing Seven Warlords affiliation Historical. | [Official Edward Weevil profile](https://one-piece.com/character/Edward_Weevil/index.html) | High; both explicitly former, exact intervals unspecified |
| Donquixote Homing | Marked his existing World Government affiliation and World Noble occupation Historical; the official episode summary says he gave up Celestial Dragon status and chose ordinary life. | [Official episode 702 synopsis](https://one-piece.com/anime/o2797/index.html) | High; explicitly former status |
| Eddy | Marked the existing Bellamy Pirates affiliation Historical because the official Bellamy profile lists him under the former crew. | [Official Bellamy profile](https://one-piece.com/character/bellamy/index.html) | High; explicitly former crew |
| Doma, Domino, Donquixote Mjosgard, Dosun, Drug Peclo, Duval | Official profiles confirm existing affiliations, ranks/roles, birthdays, epithets, or other profile facts. Domino’s additional Head Jailer role, Drug Peclo’s Underworld role, and Duval’s Mafia/Slave Trader roles remain unverified rather than removed. | [Doma](https://one-piece.com/character/Doma/index.html), [Domino](https://one-piece.com/character/Domino/index.html), [Mjosgard](https://one-piece.com/character/Donquixote_Mjosgard/index.html), [Dosun](https://one-piece.com/character/Dosun/index.html), [Drug Peclo](https://one-piece.com/character/DrugPeclo/index.html), [Duval](https://one-piece.com/character/Duval/index.html) | High for listed source facts; unsupported graph details kept open |
| Donovan | Official Vivre Card correction index confirms Foxy Pirates affiliation; Shipwright role not confirmed in this pass. | [Official Vivre Card correction index](https://one-piece.com/vivre/revision/index.html) | High for affiliation; role unresolved |
| Donannoyo, Donquino, Doringo | Canon-reference search results cite chapter/episode appearances for the existing roles and affiliations, but direct official profile evidence was not found for all details. No RDF changes were made. | [Donannoyo reference](https://onepiece.fandom.com/wiki/Donannoyo), [Donquino reference](https://onepiece.fandom.com/wiki/Donquino), [Doringo reference](https://onepiece.fandom.com/wiki/Doringo) | Medium; secondary references citing canon chapters/episodes |
| Donquixote Shivercalero, Dotaku, Doubt Brothers, Draw, Drip, Ducky Bree | Exact-name official-profile/directory searches did not surface direct profiles. Existing graph claims remain open-world unverified, not contradicted. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; discovery gaps |

The isolated patch adds 33 factual assertions, each with statement-level provenance, including five Historical temporal annotations. Details: `work/research/batch-040-results.json`; patch: `ontology/patches/campaign-batch-040.add.ttl`.

### Campaign batch 041 — alphabetized source review

| Entity | Change or finding | Source | Confidence / temporal scope |
|---|---|---|---|
| Elmy, Epoida | Official profiles explicitly classify both as Whitebeard allied pirates. Replaced direct/subordinate Whitebeard Pirates organization links with the allied-pirate affiliation class. | [Elmy profile](https://one-piece.com/character/Elmy/index.html), [Epoida profile](https://one-piece.com/character/Epoida/index.html) | High; profile snapshot |
| Farul | Official profile lists both Beautiful Pirates and Straw Hat Grand Fleet, Cavendish’s horse, and August 29 birthday. Replaced malformed combined affiliation URI with two separate edges. | [Farul profile](https://one-piece.com/character/farul/index.html) | High; profile snapshot |
| Fisher Tiger | Added the official 230,000,000 berry bounty as a named Bounty record. The official profile says he had been enslaved at Mary Geoise and later died after refusing a transfusion, so the existing Slave occupation is qualified as Historical. Official volume summary also covers his liberation and formation of the Sun Pirates. | [Fisher Tiger profile](https://one-piece.com/character/Fisher_Tiger/index.html), [Volume 63: “Otohime and Tiger”](https://one-piece.com/comics/o63/index.html) | High; explicitly past enslavement, bounty/profile snapshot |
| Erik, Farafra | Official character profiles identify both as former Arabasta rebels. Added Historical annotations to the existing Rebel Army affiliation and Rebel occupation; assertions remain present. | [Eric/Erik profile](https://one-piece.com/character/Eric/index.html), [Farafra profile](https://one-piece.com/character/Falafra/index.html) | High; former rebel status, interval unspecified |
| Elizabello II, Enishida, Faust, Fishbonen, Flapper, Ethanbaron V. Nusjuro | Official profiles/roster pages confirm corresponding existing king/role, maid/birthday, crew/origin/birthday, Marine doctor, Tonta Corps and Grand Fleet/birthday, and Five Elders/Finance Warrior God facts. No duplicate facts added. Nusjuro’s older graph label “Co-Head of the World Government” and early anime debut remain unresolved against the current profile evidence. | [Elizabello II](https://one-piece.com/character/elizabello_ii/index.html), [Enishida/Genista](https://one-piece.com/character/Genista/index.html), [Faust](https://one-piece.com/character/Faust/index.html), [Dr. Fishbonen](https://one-piece.com/character/Drfish_bone/index.html), [Flapper](https://one-piece.com/character/flapper/index.html), [Nusjuro](https://one-piece.com/character/St_Ethanbaron_V_Nusjuro/index.html), [official character directory](https://one-piece.com/character/syllabary/index.html) | High for listed facts; open identity/timing review for Nusjuro |
| Emma | Official SBS is the source for her name; chapter/episode references identify the Kid Pirates member. The character’s fate after the Victoria Punk sank is not settled by this review, so status remains Unknown. | [Official SBS list](https://one-piece.com/sbs/index.html), [chapter 1071](https://www.viz.com/shonenjump/one-piece-chapter-1071/chapter/26077), [canon-reference summary](https://onepiece.fandom.com/wiki/Emma) | Medium; SBS Vol. 102 and chapter 1071 / episode 1112 |
| Erio, Eris, Estrid, Fillonce, Finamore | Exact-name direct official-profile searches did not surface usable profile evidence. Secondary canon-reference entries support the existing Roger Pirates / information broker, Davy Family and deceased status, Warland queen, Mermaid Café dancer, and Spade Pirates details with chapter/episode citations. Existing assertions were retained and not expanded. | [Erio](https://onepiece.fandom.com/wiki/Erio), [Eris](https://onepiece.fandom.com/wiki/Eris), [Estrid](https://onepiece.fandom.com/wiki/Estrid), [Fillonce](https://onepiece.fandom.com/wiki/Fillonce), [Finamore](https://onepiece.fandom.com/wiki/Finamore) | Medium; chapter-cited secondary references |
| Eggplant Soldier, Figarland Shamrock | Exact-name direct official-profile searches did not yield direct page evidence in this pass. Existing claims were retained as open-world unknowns. | [Official character directory](https://one-piece.com/character/syllabary/index.html) | Unresolved; no facts removed |

Per-entity research and source-confidence ledger: `work/research/batch-041-results.json`. The isolated RDF patch contains statement-level provenance for every factual addition and every temporal annotation.


## Campaign batch 042

| Entity | Evidence / decision | Source | Confidence / temporal scope |
|---|---|---|---|
| Forliewbs | Corrected core crew membership to Whitebeard allied-pirate affiliation; chapter references place him among the allied captains. | [Forliewbs profile with chapter citations](https://onepiece.fandom.com/wiki/Forliewbs), [Chapter 566](https://onepiece.fandom.com/wiki/Chapter_566) | High; Marineford alliance, historical scope unspecified |
| Fukurou | Official profile says “former CP9”; added a historical qualifier to the existing CP9 affiliation, retaining the unqualified edge. The profile does not settle the graph’s CP0 link. | [Official Fukurou profile](https://one-piece.com/character/Fukuro/index.html) | High for former CP9; exact interval unspecified |
| Fossa, Fuga, Fukaboshi, Gab, Gambo | Official profiles confirm current role/affiliation and profile fields already present. Fuga’s specific Horse SMILE is noted but not modeled as a new individual fruit because variant modeling is not consistent in the ontology. | [Fossa](https://one-piece.com/character/fossa/index.html), [Fuga](https://one-piece.com/character/Fuga/index.html), [Fukaboshi](https://one-piece.com/character/Fukaboshi/index.html), [Howling Gab](https://one-piece.com/character/Howling_Gabu/index.html), [Gambo](https://one-piece.com/character/Gambo/index.html) | High for profile facts; current profile snapshots |
| Footbianco, Forest Boss, Fourtricks, Fugar, Furrari, Fuza, Gaburu, Galaxy, Gally, Gambia | Secondary or official group/context sources were checked; existing assertions were retained where the source supported them. Gambia’s official organization references match existing affiliations. | [Franky Family](https://one-piece.com/character/Franky_Family/index.html), [Gedatsu](https://one-piece.com/character/Gedatsu/index.html), [Forliewbs/Marineford chapter citations](https://onepiece.fandom.com/wiki/Forliewbs), [Nagagutsu Kingdom](https://onepiece.fandom.com/wiki/Nagagutsu_Kingdom), [Gaburu](https://onepiece.fandom.com/wiki/Gaburu), [Galaxy](https://onepiece.fandom.com/wiki/Galaxy), [Gally](https://onepiece.fandom.com/wiki/Gally) | Medium; manga/chapter references as listed in batch results |
| Flare | Monsters one-shot identity and Gérard relationship retained; current status is not inferred from the one-shot’s separate chronology. | [Flare reference](https://onepiece.fandom.com/wiki/Flare) | Medium; chronology unresolved |
| Fullbody | Official profile’s rank header and body text conflict. Existing malformed/conflicting occupations are left unchanged pending source reconciliation. | [Official Fullbody profile](https://one-piece.com/character/Fullbody/index.html) | Unresolved |
| Gal | Exact-name search did not establish a reliable canonical identity; no RDF changes. | [Secondary Gal lookup](https://daddyjim.com/one-piece/character/Gal) | Unresolved |

The complete per-entity source URLs and decisions are recorded in `work/research/batch-042-results.json`.


## Campaign batch 043

| Entity | Evidence / decision | Source | Confidence / temporal scope |
|---|---|---|---|
| Gancho | Official profile confirms Tontatta Kingdom king identity; current facts match. | [Official Gancho profile](https://one-piece.com/character/gancho/index.html) | High; profile snapshot |
| Gatz | Official profile confirms Corrida Colosseum announcer and August 26 birthday; current facts match. | [Official Gatz profile](https://one-piece.com/character/Gats/index.html) | High; profile snapshot |
| Genzo | Official profile confirms Cocoyasi Village constable and June 17 birthday; current facts match. | [Official Genzo profile](https://one-piece.com/character/Genzo/index.html) | High; profile snapshot |
| Gerd | Official profile confirms Elbaph origin and former mercenary activity; chapter-referenced story identifies Buggy’s Delivery service before joining the New Giant Warrior Pirates. Added Elbaph origin and Historical qualifiers for existing Mercenary and Buggy’s Delivery facts. | [Official Gerd profile](https://one-piece.com/character/Gerd/index.html), [chapter-referenced profile](https://onepiece.fandom.com/wiki/Gerd) | High; profile origin; historical roles, exact interval unspecified |
| Gerotini | Chapter 1079 identifies captain of the Puddle Pirates in Red Hair’s allied fleet. Corrected core crew category to modeled allied affiliation and removed VIZ translation metadata from epithet. | [Gerotini profile with chapter citations](https://onepiece.fandom.com/wiki/Gerotini), [Chapter 1079](https://onepiece.fandom.com/wiki/Chapter_1079) | High; chapter 1079 |
| Giovanni | Official profile confirms Mokomo Dukedom, Inuarashi Musketeer role, origin and profile fields; existing facts match. | [Official Giovanni profile](https://one-piece.com/character/giovanni/index.html) | High; profile snapshot |
| Gazelleman, Genbo | Official profiles confirm existing affiliations and role facts; Gazelleman’s individual Gazelle SMILE remains a schema-level modeling gap. | [Gazelleman](https://one-piece.com/character/gazelleman/index.html), [Genbo](https://one-piece.com/character/Genbo/index.html) | High; profile snapshots |
| Gangaru, Ganryu, Garudan, George Mach, Giberson, Gig, Gina, Ginrummy, Gion, Gismonda, Glove | Chapter-cited or secondary references checked against current assertions; no additional facts were asserted. Gig’s individual status remains Unknown. | See per-entity source URLs in `work/research/batch-043-results.json` | Medium or unresolved where indicated in the ledger |
| Gatherine | No direct official profile surfaced for the exact name; current assertions retained without independent confirmation. | [Exact-name reference search](https://onepiece.fandom.com/wiki/Gatherine) | Unresolved |


## Campaign batch 044

| Entity | Evidence / decision | Source | Confidence / temporal scope |
|---|---|---|---|
| Goldberg | Official profile confirms New Giant Warrior Pirates, Straw Hat Grand Fleet, birthday, and cook role. Chapter 803 references identify the former Buggy’s Delivery mercenary service; split malformed affiliation, qualify former organization/role, add specific Elbaph origin. | [Official Goldberg profile](https://one-piece.com/character/GoldBerg/index.html), [Goldberg chapter references](https://onepiece.fandom.com/wiki/Goldberg), [Chapter 803](https://onepiece.fandom.com/wiki/Chapter_803) | High; current profile facts and historical service |
| Gotti | Official profile confirms Fire Tank Pirates, assassin role and 90,000,000-berry bounty; added a named bounty record and normalized concatenated occupation. | [Official Gotti profile](https://one-piece.com/character/Gotty/index.html) | High; official profile snapshot |
| Gyro | Official profile confirms captain of the Gyro Pirates, 73,000,000-berry bounty, and brief former New Fish-Man Pirates affiliation; split malformed URI and model the crew. Defeat is not treated as death. | [Official Gyro profile](https://one-piece.com/character/Gyro/index.html) | High; current crew/bounty and historical Fish-Man Island affiliation |
| Gyaro | Official profile explicitly describes him as a former Sun Pirates member and lists the Macro Pirates; added Historical qualifier to the existing Sun Pirates edge. | [Official Gyaro profile](https://one-piece.com/character/Gyaro/index.html) | High; explicitly former |
| Guernika | Official profile confirms CP0 agent, October 25 birthday, and death; existing facts match. | [Official Guernika profile](https://one-piece.com/character/Guernika/index.html) | High; deceased |
| Gyogyo | Official profile confirms Bonney Pirates membership and prior fisherman work; existing Bonney affiliation and fishmonger role retained. | [Official Gyogyo profile](https://one-piece.com/character/Gyogyo/index.html) | High; current profile snapshot |
| Goki, Gomorrah, Gonbe | Chapter-cited sources confirm Beasts Pirates Number identity, Gomorrah’s Franky Family/transport role, and Gonbe’s Shift Station/cat-actually-rabbit caption. Existing assertions retained; species/companion predicates are limited by the current model. | [Goki](https://onepiece.fandom.com/wiki/Goki), [Gomorrah](https://onepiece.fandom.com/wiki/Gomorrah), [Gonbe](https://www.grandlinearchives.com/characters/gonbe), [Shift Station](https://onepiece.fandom.com/wiki/Shift_Station) | Medium; chapter references in cited pages |
| Gode, Goldfish Princess, Goo, Gorilla, Gorishiro, Goro, Gram, Great Michael, Guillotine, Gurutaro, Gyoro/Nin/Bao | Focused searches did not surface direct or chapter-cited sources adequate to update these records. Current assertions remain unverified and unchanged. Gyoro/Nin/Bao may combine multiple zombie identities; no split was applied. | Sources and gaps listed per entity in `work/research/batch-044-results.json` | Unresolved or medium where explicitly recorded |

## Campaign batch 045

| Entity | Evidence / decision | Source | Confidence / temporal scope |
|---|---|---|---|
| Hack | Official profile confirms Revolutionary Army, canonical “Hundredth-Dan Hack,” Fish-Man Karate instructor, and Fish-Man Jujutsu practitioner. Split malformed occupation; removed the VIZ-tagged epithet literal. Replaced the concatenated residence value with the documented later Momoiro Island residence. | [Official Hack profile](https://one-piece.com/character/hack/index.html), [chapter-referenced profile](https://onepiece.fandom.com/wiki/Hack) | High for profile facts; medium for later residence |
| Hajrudin | Official profile confirms Elbaph origin and current crew roles. Chapter 803 material supports former Buggy’s Delivery service and mercenary work; marked the existing organization and occupation Historical. | [Official Hajrudin profile](https://one-piece.com/character/hajrudin/index.html), [Hajrudin chapter references](https://onepiece.fandom.com/wiki/Hajrudin), [Chapter 803](https://onepiece.fandom.com/wiki/Chapter_803) | High; former service before Grand Fleet membership |
| Hannyabal | Official profile confirms Chief Warden and birthday; chapter-referenced profile supports prior Vice Warden role. Added Historical qualifier to the existing Vice Warden occupation. | [Official Hannyabal profile](https://one-piece.com/character/Hannyabal/index.html), [Hannyabal reference](https://onepiece.fandom.com/wiki/Hannyabal) | High; Vice Warden before promotion |
| Hatchan | Chapter-referenced source distinguishes former Sun Pirates and Arlong Pirates membership, Pirate Officer role and Fish-Man District / Arlong Park residences from current Takoyaki 8 and takoyaki seller facts. Added Historical qualifiers to those five existing assertions. | [Hatchan profile and chapter citations](https://onepiece.fandom.com/wiki/Hatchan) | High for former crew/role; medium for residences |
| Hattori | Chapter-referenced source confirms former CP9 service and later CP0 relationship. Removed the Galley-La affiliation: Hattori accompanied Lucci while Lucci posed as a company worker, but was not himself a member. | [Hattori profile and chapter citations](https://onepiece.fandom.com/wiki/Hattori), [Chapter 323](https://onepiece.fandom.com/wiki/Chapter_323) | High for CP9/CP0 chronology; model gap remains for undercover association |
| Harald | Chapter-referenced sources confirm kingship and Devoted Blade of God service, then later promotion to full Knight of God. Replaced the concatenated occupation URI with distinct King of Elbaph and Devoted Blade roles; both are Historical. | [Harald chapter references](https://onepiece.fandom.com/wiki/Harald), [Chapter 1167](https://www.grandlinearchives.com/chapters/1167), [Chapter 1168](https://www.grandlinearchives.com/chapters/1168) | High; both roles ended before death, Devoted Blade ended before full Knight status |
| Hakowan, Hakugan, Hamburg, Hamlet, Hammond, Hangan, Hanger, Happygun, Hareji, Haruta, Hasami, Hatcha, Hatsume, Hawkman | Selected facts were reviewed where a source surfaced; exact-name source gaps and relationship-modeling questions remain open for the entries without direct source support. No unsupported facts were added. | Per-entity URLs and decisions in `work/research/batch-045-results.json` | Source gaps or modeling questions are explicitly recorded in the result ledger |

Per-entity findings and review scope are recorded in `work/research/batch-045-results.json`. The patch adds statement-level provenance for additions and temporal annotations; replaced assertions and the removed false Galley-La affiliation are listed in the companion removal patch.

## Campaign batch 046

| Entity | Evidence / decision | Source | Confidence / temporal scope |
|---|---|---|---|
| Higuma | Official profile confirms Higuma Bandits leader, November 18 birthday, and 8,000,000-berry bounty. Added the amount as a named Bounty record; existing role/status retained. | [Official Higuma profile](https://one-piece.com/character/Higuma/index.html) | High; official profile snapshot |
| Hibari | Official profile confirms Marine Headquarters rank, SWORD membership, January 18 birthday, and an approximate 200,000,000-berry Cross Guild bounty. Added a named record preserving that it is an estimate by Cross Guild, not a Government-issued bounty. | [Official Hibari profile](https://one-piece.com/character/Hibari/index.html) | High; approximate Cross Guild estimate |
| Hihimaru | Official profile identifies Wano and the “Raging Baboon of the Mountain”; chapter 911 locates it in Kuri and shows Tama taming it. Replaced a concatenated residence URI with Kuri and Wano Country, and marked prior Beast Pirates / alliance links Historical. | [Official Hihimaru profile](https://one-piece.com/character/Hihimaru/index.html), [Hihimaru chapter references](https://onepiece.fandom.com/wiki/Hihimaru), [Chapter 911](https://onepiece.fandom.com/wiki/Chapter_911) | High; chapter 911, historical crew links |
| Himuro | Chapter references identify former Mimawarigumi service under the Kurozumi Family before joining the Beasts Pirates; added Historical qualifier. | [Himuro references](https://onepiece.fandom.com/wiki/Himuro) | High; former service before Beasts Pirates |
| Hitsugisukan | Chapter-referenced sources identify him as former ruler of the Mokomo Dukedom before Inuarashi and Nekomamushi; added Historical qualifier. | [Hitsugisukan profile](https://www.grandlinearchives.com/characters/hitsugisukan), [Mokomo Dukedom references](https://onepiece.fandom.com/wiki/Mokomo_Dukedom) | High; before succession |
| Heat, Heppoko, Hera, Hildon, Hippie, Hiro Gomon | Official or chapter-referenced profiles confirm selected existing crew, role, and profile facts; no unsupported duplicate assertions added. Hera’s Homie origin has a schema gap; unknown status is retained. | [Heat](https://one-piece.com/character/Heat/index.html), [Heppoko / Peppoko / Poppoko](https://one-piece.com/character/Heppoko_Peppoko_Poppoko/index.html), [Hera](https://one-piece.com/character/Hera/index.html), [Hildon](https://one-piece.com/character/Hildon/index.html), [Hippie](https://onepiece.fandom.com/wiki/Hippie), [Hiro Gomon](https://onepiece.fandom.com/wiki/Hiro_Gomon) | High for official profile facts; medium where chapter-cited |
| Hewitt, Hidayu, Hikkomitsukumai, Hip, Hippan Natte, Hippo Gallant, Hiramera, Dr. Hō, Hocha | Focused searches did not surface evidence adequate to independently verify the selected existing claims. Assertions remain unchanged and gaps are listed per entity in the result ledger. | Per-entity records in `work/research/batch-046-results.json` | Unresolved; no negative claims inferred |

Per-entity findings are in `work/research/batch-046-results.json`. The add patch contains source-level provenance for bounty, residence, and temporal assertions; the malformed concatenated Hihimaru residence is recorded in the removal patch.

## Campaign batch 047

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Hoe | `op:occupation op:Pet`; remove malformed occupation and `affiliatesWith op:KingNeptune` | The [Hoe character reference](https://onepiece.fandom.com/wiki/Hoe) describes Hoe as Neptune's pet and transportation. `affiliatesWith` currently has no pet-owner semantics, so the King Neptune link is removed and retained as a modeling gap rather than asserted as organizational membership. | High for Pet; relation modeling unresolved |
| Holedem | `op:residence op:Bakura_Town`, `op:Wano_Country` | [Official episode 901 synopsis](https://one-piece.com/anime/o5163/index.html) places Holedem's actions in Bakura Town; the [official character profile](https://one-piece.com/character/holdem/index.html) identifies him within the Wano arc. The combined malformed place URI is removed. | High; Wano arc |
| Hotei | Historical Kurozumi Family and Mimawarigumi captain role | [Chapter 986](https://onepiece.fandom.com/wiki/Chapter_986) shows Hotei pledging the Mimawarigumi to Kaido after Orochi's fall; the [character reference](https://onepiece.fandom.com/wiki/Hotei) identifies his former Kurozumi Family service. | High; historical before transfer |
| Hyougoro | Split Udon/Wano residence; Historical prisoner, underworld boss, family and alliance associations; remove source-metadata epithet | The [official profile](https://one-piece.com/character/Hyougoro/index.html) confirms Hyougoro Family, the Flower epithet, prior underworld prominence and Udon imprisonment. The [chapter-referenced profile](https://onepiece.fandom.com/wiki/Hyougoro) documents release, former roles, and the disbanded alliance. | High for official-profile facts; medium for temporal relationship scope |
| Hyouzou | no graph delta | The [official profile](https://one-piece.com/character/Hyouzou/index.html) confirms New Fish-Man Pirates, assassin, merman species, and birthday; the chapter-referenced profile identifies swordsman and mercenary roles. Existing core facts were retained. | High; Fish-Man Island arc |
| Hublot | Add Whitebeard Pirates; mark Spade Pirates Historical | The [Hublot character reference](https://daddyjim.com/one-piece/character/Hublot) says the Spade Pirates joined Whitebeard's crew after Ace; the [official Ace profile](https://one-piece.com/character/ace/) supplies context but does not directly list Hublot. | Medium; secondary chapter-referenced support |
| Hotori and Kotori | identity/attribution held for review | The [Hotori chapter profile](https://www.grandlinearchives.com/characters/hotori) identifies Hotori and Kotori as distinct twins who share a sub-commander role. Existing combined ontology identity is not split in this batch. | Medium; Skypiea arc, modeling unresolved |
| Ida | Correct `Unknown` to `Deceased`, split roles, add Samuwanai origin and temporal scopes | The chapter-cited [Ida reference](https://onepiece.fandom.com/wiki/Ida) indexes chapters 1153–1154 for her origin, circus work, and bar role, and chapter 1168 for her death. | High; chapter 1168 confirms death |
| Hogback, Hoisassa, Holy, Hongo, Hop, Horseman, Hototogisu, House, Humphrey, Hustle, Ibiributsu, Ibusu | no graph delta | Focused searches did not locate sufficiently direct authoritative evidence for the selected existing claims. They remain unchanged and explicitly partial in `work/research/batch-047-results.json`; no absence was treated as a negative fact. | Unresolved; future source review |

The patch records provenance at assertion level in `ontology/patches/campaign-batch-047.add.ttl`; removed assertions and reasons are in the paired removal patch. The complete per-entity notes and source URLs are recorded in `work/research/batch-047-results.json`.

## Campaign batch 048

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Ideaman | Replace malformed `Staff_Officerof_Planning` with `Staff_Officer_of_Planning` | The [Ideaman chapter-referenced profile](https://onepiece.fandom.com/wiki/Ideaman) identifies the Krieg Pirates planning staff-officer role. The correction preserves the role while removing the malformed value. | Medium; character role |
| Ikkaku | Split Wano announcer into `op:Ikkaku_Wano`; mark Heart Pirates member's alliance association Historical | The [official Ikkaku profile](https://one-piece.com/character/ikkaku/index.html) identifies the Heart Pirates member. [Chapter 915](https://www.viz.com/shonenjump/one-piece-chapter-915/chapter/16843) and the [Wano announcer reference](https://onepiece.fandom.com/wiki/Ikkaku_(Wano)) identify a separate announcer, with distinct debut, voice actors, occupation, and residence. The combined source page and conflicting values are separated; the alliance later disbanded. | High for identity split and debuts; Wano announcer's alive status is an arc snapshot |
| Igaram | Historical Baroque Works affiliation and undercover roles | The [official profile](https://one-piece.com/character/Igaram/index.html) confirms Igaram was Alabasta's Royal Guard captain who infiltrated Baroque Works. Historical qualifiers distinguish that former cover period from his royal role. | High for affiliation; medium for mapping the two cover occupations |
| Inbi | Add `op:affiliatesWith op:Numbers` and define the Numbers affiliation | Chapter-referenced profiles identify Inbi as a Number within the [Beasts Pirates](https://onepiece.fandom.com/wiki/Beasts_Pirates). | Medium; Wano arc subgroup |
| Indigo | Correct current status from `Alive` to `Unknown` | The [official profile](https://one-piece.com/character/Indigo/index.html) and [VIZ's Chapter 0 notice](https://www.viz.com/blog/posts/special-one-piece-one-shot-1744) establish his historical Golden Lion Pirates story, but do not establish present-day survival. The manga-backed record therefore retains an open-world Unknown status; the separate Merveille residence interval remains unresolved. | Medium; present-day status Unknown |
| Inuppe | Replace malformed `Dog PenguinInuppe` label with `Dog Penguin` | The [official profile](https://one-piece.com/character/Inuppe/index.html) confirms the zombie's identity and Sanji shadow; the [chapter-referenced profile](https://onepiece.fandom.com/wiki/Inuppe) documents the English name. | Medium for English label; Thriller Bark arc |
| Ishilly | Add `op:occupation op:Dancer` | The chapter-cited [Ishilly source](https://www.grandlinearchives.com/characters/ishilly) reports that SBS volume 65 lists her among the Mermaid Café's top dancers. | High; SBS fact |
| Jacksonbanner | Mark Roger Pirates membership and Pirate/Musician roles Historical | The [chapter-referenced profile](https://onepiece.fandom.com/wiki/Jacksonbanner) cites chapter 967 for crew membership and SBS volume 112 for his musician role; chapter 968 records crew dissolution. | High; historical until dissolution |
| Ideo, Ikaros Much, Imu, Inhel, Ipponmatsu, Ipponume, Islewan, Itomimizu, Iwatobi, Iyan'eno Chinode, Jabari, Jaguar | No graph delta | Official profiles or chapter/SBS-referenced sources were checked against the selected graph facts. Existing values were retained; Jaguar's post-defeat fate and several individual life statuses remain Unknown where the story does not confirm them. Per-entity notes and sources are in `work/research/batch-048-results.json`. | Source review; unresolved facts remain unknown |

The add patch contains assertion-level provenance for the batch changes. The removal patch lists every legacy assertion removed, with the modeling reason in its comments and the corresponding source references in the add patch and batch ledger.


## Campaign batch 049

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Jaguar D. Saul | Split malformed combined occupation into Teacher and Vice Admiral; qualify Marine affiliation and Vice Admiral role Historical | The [official profile](https://one-piece.com/character/Jaguar_D_Saul/index.html) identifies his former Marine Headquarters vice admiral service and dismissal. Chapter 1134 in [official volume 112](https://one-piece.com/comics/75896/index.html) places Saul at the Walrus School; chapter-referenced profile describes him teaching history. | High; former service and present school role |
| Jaki | Add `op:affiliatesWith op:Numbers` | [Official profile](https://one-piece.com/character/jaki/index.html) identifies him as one of the Beasts Pirates Numbers. | High; Wano arc profile |
| Jango | Separate former Captain, First Mate, Dancer, Pirate, and Marine Seaman Recruit roles temporally; add former 9,000,000-berry bounty | [Official profile](https://one-piece.com/character/Django/index.html) gives the Marine Headquarters rank, former bounty, and former Black Cat Pirates service. The chapter-referenced [Jango profile](https://onepiece.fandom.com/wiki/Jango) documents First Mate, Captain, and Dancer roles. | High for official profile facts; medium for secondary role details |
| Jarul | Mark Giant Warrior Pirates and Captain/Pirate roles Historical; remove editorial `VIZ: Beardhill` epithet value | [Official Jarul profile](https://one-piece.com/character/Jarul/index.html) explicitly calls Jarul a former Giant Warrior Pirates captain. | High; former service |
| Jaygarcia Saturn | Mark Five Elders, World Nobles, Scientist and Warrior God of Science and Defense assertions Historical | The [official Saturn profile](https://one-piece.com/character/St_Jaygarcia_Saturn/index.html) documents the roles; [VIZ Chapter 1125](https://www.viz.com/shonenjump/one-piece-chapter-1125/chapter/44012) shows Saturn's death and Garling assuming his Elder position. Existing deceased status retained. | High; roles ended at death |
| Jean Bart | Mark prior pirate captain, Pirate, Slave, and Wano alliance link Historical; remove unsupported `his_own_crew` placeholder affiliation | [Official profile](https://one-piece.com/character/Jean_Bart/index.html) recounts his former captaincy, enslavement and current Heart Pirates membership. The [Pirate Alliance history](https://onepiece.fandom.com/wiki/Pirate_Alliance) cites chapter 1056 for the alliance ending. | High for profile; medium for alliance scope |
| Jean Noueilles | Mark New Fish-Man Pirates affiliation and related Pirate/Commander roles Historical | Chapter-referenced [profile](https://onepiece.fandom.com/wiki/Jean_Noueilles) cites chapters 617 and 635 and records the crew's later dissolution. | Medium; historical Fish-Man Island crew service |
| Jigoku Benten | Mark Beasts Pirates, Kurozumi Family, and Orochi Oniwabanshu links Historical | [Official profile](https://one-piece.com/character/Jigoku_Benten/index.html) identifies her in the Oniwabanshu; chapter-referenced [profile](https://onepiece.fandom.com/wiki/Jigoku_Benten) documents the Wano allegiance transfer and the end of the regime. | High for identity; medium for end-of-service scope |
| Jigoro | Mark Thriller Bark Pirates and General Zombie roles Historical | Chapter-referenced [profile](https://onepiece.fandom.com/wiki/Jigoro) documents the posthumous General Zombie role and number 850. | Medium; Thriller Bark arc |
| Jigra | Mark Underworld, Organ Dealing Assassination Group, and Organ Trader assertions Historical | Chapter-referenced [profile](https://onepiece.fandom.com/wiki/Jigra) documents his occupation and death during the tea party. | Medium; through death at Whole Cake Island |
| Jiron | Mark Baltigo residence Historical | [Official profile](https://one-piece.com/character/Jiron/index.html) confirms his Revolutionary Army North Army role; the chapter-referenced [Revolutionary Army history](https://onepiece.fandom.com/wiki/Revolutionary_Army) records the move from Baltigo to Momoiro Island. | Medium; before headquarters relocation |
| Jalmack, Jeep, Jeet, Jero, Jerry, Jibuemon, Jigokukamabuta Megatenpanchiro, Johanna, John Giant | No graph change after review | See each finding and source in `work/research/batch-049-results.json`. Unresolved modeling questions (Levely event vs affiliation, current/historical roles, and an inadequately supported family relation) are retained without adding a negative assertion. Official profiles for [John Giant](https://one-piece.com/character/John_Giant/index.html) and [Johanna's chapter-referenced page](https://onepiece.fandom.com/wiki/Johanna) support the reviewed records. | Partial source review; unresolved facts remain unknown |

The add patch has 524 RDF triples, including 39 statement-level provenance records and 31 temporal statement nodes. The removal patch records four source assertions and six now-unreferenced malformed vocabulary triples; per-removal reasons are in `work/research/batch-049-removal-reasons.json`. All 20 batch records are in `work/research/batch-049-results.json`.

## Campaign batch 050

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Jorul | Mark Giant Warrior Pirates membership and Pirate Captain occupation Historical | [Official profile](https://one-piece.com/character/Jorul/index.html) explicitly labels Jorul a former member and former captain. | High; historical service |
| Joy Boy | Add `opx:hasHaki opx:ConquerorsHaki` | [VIZ Chapter 1122](https://www.viz.com/shonenjump/one-piece-chapter-1122/chapter/43818) is the primary chapter source; a [chapter-referenced summary](https://onepiece.fandom.com/wiki/Chapter_1122) identifies the Haki Joy Boy sealed in Emet as Supreme King Haki. | High; historical Void Century ability, one stored portion |
| Juki | Add `op:affiliatesWith op:Numbers` | [Official profile](https://one-piece.com/character/juki/index.html) identifies Juki as one of the Beast Pirates Numbers. | High; Wano arc profile |
| Kadar | Replace malformed `MarinesG-2` affiliation with current Marines affiliation and historical G-2 service | [Official profile](https://one-piece.com/character/Kadal/index.html) says Kadar is a Marine Headquarters marine and formerly served at G-2 as a Rear Admiral. | High; current broad affiliation and historical branch service |
| Kalgara | Replace malformed English label with `Kalgara` | [Official profile](https://one-piece.com/character/Kalgara/index.html) gives the official identity spelling. | High; identity label |
| Kairiken | Remove Sabaody Archipelago from `affiliatesWith` | [Chapter-referenced profile](https://onepiece.fandom.com/wiki/Kairiken) describes him as a bounty hunter at Sabaody; that is a location appearance, not organizational membership. No replacement relation was asserted because the schema has no general appearance-location property. | Medium; chapter 498 and following appearance |

Other reviewed entities had no evidence-supported graph delta. Their partial source reviews and exact selected graph values are recorded in `work/research/batch-050-results.json`; four modeling or source questions remain in the batch unresolved file.

## Campaign batch 051

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Kaneshiro | Mark Sun Pirates and Arlong Pirates service, Pirate role, and prior residences Historical | [Chapter-referenced profile](https://onepiece.fandom.com/wiki/Kaneshiro) records his move from the Sun Pirates to Arlong and former residences; the [Arlong Pirates history](https://onepiece.fandom.com/wiki/Arlong_Pirates) documents defeat/arrest, and the [Sun Pirates history](https://onepiece.fandom.com/wiki/Sun_Pirates) documents the split. | High; historical crew/service periods |
| Kasagoba | Replace malformed label; preserve anime spelling as `op:alias "Kasagon"@en` | [Chapter-referenced profile](https://onepiece.fandom.com/wiki/Kasagoba) distinguishes manga name Kasagoba from anime rendering Kasagon and cites chapter 607. | High; adaptation-specific alias |
| Kashii | Split combined World Government/Giant Warrior Pirates affiliation, Pirate/Gate Guardian role, and residence URI | [Official profile](https://one-piece.com/character/Kashii/index.html) confirms Giant Warrior Pirates membership and 50 years guarding Enies Lobby's gate before rebelling. [Chapter-referenced profile](https://onepiece.fandom.com/wiki/Kashii) and [crew timeline](https://www.grandlinearchives.com/characters/kashii) establish former government service, later return to Elbaph, and the named places. | High for crew and former gate role; medium for residence intervals |
| Kawamatsu | Remove unsupported Daimyo occupation; qualify Highway Robber as Historical | The [official profile](https://one-piece.com/character/Kawamatsu/index.html) identifies Kawamatsu as a Kozuki retainer; [Chapter 953](https://onepiece.fandom.com/wiki/Chapter_953) identifies Ushimaru as the daimyo and describes Kawamatsu's temporary Gyukimaru disguise and weapon collection. | High; distinction between retainer and Ringo daimyo |
| Kazekage | Mark Beasts Pirates/Oniwabanshu service and related Ninja/Pirate roles Historical | Chapter-referenced [character](https://onepiece.fandom.com/wiki/Kazekage) and [organization histories](https://onepiece.fandom.com/wiki/Beasts_Pirates) support the Wano regime service, which ended with the regime's fall. | Medium; Wano period |
| Kebi | Mark Rebel Army, Sand-Sand Clan, and Rebel roles Historical | Chapter-referenced [Kebi profile](https://onepiece.fandom.com/wiki/Kebi) and [Alabasta rebellion history](https://onepiece.fandom.com/wiki/Alabasta_Rebel_Army) place the role in the resolved civil war. | Medium; Alabasta conflict |
| Kechatch | Mark Whitebeard Pirates affiliation Historical | The [Kechatch profile](https://onepiece.fandom.com/wiki/Kechatch) identifies his affiliation; the [Whitebeard Pirates history](https://onepiece.fandom.com/wiki/Whitebeard_Pirates) records the fleet's end. | Medium; historical allied-fleet service |
| Killer | Mark Wano alliance and Kamazo Assassin role Historical; remove person-as-affiliation link to Orochi | [Official profile](https://one-piece.com/character/killer/index.html) confirms Kid Pirates membership; [chapter 1056](https://onepiece.fandom.com/wiki/Chapter_1056) records the alliance's end. The source record does not establish Killer's later survival, so status remains Unknown. | High for alliance end; medium for time-limited Kamazo role |
| Kiev | Split composite occupation into Dismantler and Bounty Hunter | Chapter-referenced [Franky Family crew history](https://www.grandlinearchives.com/crews/franky-family) and [Kiev profile](https://onepiece.fandom.com/wiki/Kiev) support the two roles. | Medium; Franky Family role |
| Kinderella | Mark Miss Universe role Historical | The [official profile](https://one-piece.com/character/Kinderella/index.html) calls her a former Miss Universe and current Evil Black Drum Kingdom queen. | High; former title |

All 20 entities have partial source-review records in `work/research/batch-051-results.json`; four open questions are in `work/research/batch-051-unresolved.json`.


## Campaign batch 052

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Momonosuke | Correct age 1 to 8 and origin Grand Line to Wano Country; mark Wano alliance Historical | [Official profile](https://one-piece.com/character/Kouduki_momonosuke/index.html) states age 8 and origin Wano; the [alliance history](https://onepiece.fandom.com/wiki/Ninja-Pirate-Mink-Samurai_Alliance) says it disbanded after the Wano raid. | High for age/origin; medium for alliance end |
| Kong | Add current Commander-in-Chief role; mark Marines, Admiral, and Fleet Admiral assertions Historical | [Official profile](https://one-piece.com/character/Kong/index.html) identifies Kong as World Government Commander-in-Chief; the [chapter-referenced profile](https://onepiece.fandom.com/wiki/Kong) documents former Marine ranks and affiliation. | High; current office and prior Marine service |
| Sukiyaki | Mark Shogun role and Wano alliance affiliation Historical; split malformed residence into Amigasa Village and Flower Capital, qualifying the latter Historical | [Official profile](https://one-piece.com/character/Kozuki_Sukiyaki/) calls him the former Wano shogun and describes his Amigasa Village residence; [chapter-referenced profile](https://onepiece.fandom.com/wiki/Kouzuki_Sukiyaki) records former Flower Capital residence and the alliance's dissolution. | High for former office; medium for residence interval |
| Kinga, Kingdew | Mark Whitebeard Pirates service historical; mark Kingdew's 11th Division Commander role Historical | [Kinga](https://onepiece.fandom.com/wiki/Kinga) and [Kingdew](https://one-piece.com/character/kingdew/index.html) profiles establish their roles; the [Payback War](https://onepiece.fandom.com/wiki/Payback_War) ended with the Whitebeard Pirates disbanding. | High for role and crew end |
| Kotatsu, Kukai | Mark Spade Pirates ties Historical; add their later Whitebeard Pirates ties as Historical | The [Spade Pirates history](https://onepiece.fandom.com/wiki/Spade_Pirates) says the crew was integrated into Whitebeard's crew; [crew history](https://onepiece.fandom.com/wiki/Whitebeard_Pirates) lists former Spade crew members, and the [Payback War](https://onepiece.fandom.com/wiki/Payback_War) ended that organization. | Medium; former crew membership and later integration |
| Kojuro, Komane, Koshi Falcon | Mark the Wano alliance, Lulusia royalty/affiliation, and Beasts Pirates/Gifter records Historical | The [alliance history](https://onepiece.fandom.com/wiki/Ninja-Pirate-Mink-Samurai_Alliance), [Komane profile](https://daddyjim.ai/one-piece/character/Komane) and [Lulusia record](https://www.grandlinearchives.com/locations/lulusia), and [Koshi Falcon profile](https://onepiece.fandom.com/wiki/Koshi_Falcon) document the groups' endings. | Medium; former service and roles |
| Kumashi | Mark Thriller Bark affiliation and Perona's servant/Wild Zombie Commander-in-Chief roles Historical | The [chapter-referenced profile](https://onepiece.fandom.com/wiki/Kumashi) records his purification by Usopp. | High; roles ended at purification |
| Kumadori Yamanbako | Remove a mother-son relation misrepresented as `affiliatesWith` | The [Yamanbako profile](https://onepiece.fandom.com/wiki/Kumadori_Yamanbako) and [Kumadori profile](https://onepiece.fandom.com/wiki/Kumadori) identify their family relation. No kinship predicate exists, so no replacement edge was added. | High; modeling correction |

Other reviewed records are documented in `work/research/batch-052-results.json`; five remaining questions are in `work/research/batch-052-unresolved.json`. The patch files are `ontology/patches/campaign-batch-052.add.ttl` and `.remove.ttl`, with removal reasons in `work/research/batch-052-removal-reasons.json`.


## Campaign batch 053

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Kuroobi | Mark Sun Pirates, Arlong Pirates, Pirate Officer, Arlong Park, and Fish-Man District assertions Historical | The [character profile](https://onepiece.fandom.com/wiki/Kuroobi) records his former Sun Pirates period and Arlong Pirates service; the [Arlong Pirates record](https://onepiece.fandom.com/wiki/Arlong_Pirates) documents defeat and arrest. | High; former crew and residence periods. |
| Kurosawa | Mark Ninja-Pirate-Mink-Samurai Alliance affiliation Historical | The [profile](https://onepiece.fandom.com/wiki/Kurosawa) identifies the alliance service; the alliance's raid concluded and it disbanded. | High; ended alliance. |
| Kurozumi Higurashi | Add Kurozumi Family affiliation; replace Grand Line origin with Wano Country | [Official profile](https://one-piece.com/character/kurozumi_higurashi/index.html) identifies her under Wano and the Kurozumi family. | High; corrected origin and family identity. |
| Kyo | Mark Rocks Pirates affiliation Historical | [Kyo's profile](https://onepiece.fandom.com/wiki/Kyo) describes the crew's dissolution at God Valley; his own current status remains Unknown. | High; historical crew membership. |
| Kyros | Mark Corrida Coliseum affiliation and Gladiator role Historical | The [official Kyros profile](https://one-piece.com/character/Kyros/index.html) identifies his gladiator career; later service as Riku Royal Army captain remains separately represented. | High; former career. |
| Kyuin | Mark Donquixote Pirates and SMILE factory manager records Historical | [Kyuin's profile](https://onepiece.fandom.com/wiki/Kyuin) lists her former affiliation and factory role; the crew's defeat ended the operation. Her later pirate role is retained. | High; former crew and factory service. |
| Laboon | Mark Rumbar Pirates membership Historical; remove Crocus from `affiliatesWith` | The [Laboon profile](https://onepiece.fandom.com/wiki/Laboon) records his Rumbar Pirates membership and Crocus as caretaker; the predicates do not model caretaker/friendship. | High; membership and relationship type correction. |
| Lacroix and Lonz | Replace malformed `MarinesGiant_Squad` affiliation with separate Marines and Giant Squad links | [Lacroix](https://onepiece.fandom.com/wiki/Lacroix) and [Lonz](https://one-piecewiki.com/wiki/lonz/) profiles identify the two affiliations. | High; malformed source token corrected. |
| Lacuba | Remove `NA` affiliation; mark Captain and Slave roles Historical | The [official profile](https://one-piece.com/character/Lacuba/index.html) identifies him as a pirate auctioned at Sabaody; the [chapter-referenced profile](https://onepiece.fandom.com/wiki/Lacuba) records his former captaincy, enslavement, and later freedom. | High; missing-value sentinel removed and past roles qualified. |
| Lao G | Mark Donquixote Pirates affiliation and Pirate Officer role Historical | [Lao G's profile](https://onepiece.fandom.com/wiki/Lao_G) identifies his role in the Donquixote crew; the organization was disbanded after Dressrosa. | High; ended crew service. |
| Laskey | Mark CP9 affiliation and Cipher Pol Agent role Historical | [Laskey's profile](https://onepiece.fandom.com/wiki/Laskey) identifies him as a former CP9 agent; current status remains Unknown. | High; historical agency service. |
| Lemoncheese | Replace Levely affiliation and malformed composite occupation with Bestland Kingdom and Queen | [Lemoncheese's profile](https://onepiece.fandom.com/wiki/Lemoncheese) identifies her as queen of Bestland; Levely is an event, not an organization. | High; normalization of political office and affiliation. |
| Leonero | Mark Spade Pirates membership Historical; add Whitebeard Pirates affiliation with TimeUnspecified temporal status | [Leonero's profile](https://onepiece.fandom.com/wiki/Leonero) says the Spade crew was taken into Whitebeard's crew. The later end of Leonero's Whitebeard membership is not established. | High for integration; end date unresolved. |
| Lily | Mark Bellamy Pirates affiliation Historical | [Bellamy Pirates roster and history](https://onepiece.fandom.com/wiki/Bellamy_Pirates) identifies Lily and the crew's disbandment. | High; disbanded crew. |
| Linaria | Remove direct Red Hair Pirates membership; retain Night Butterfly Pirates captain affiliation | [Oda's SBS 108 information](https://gamepedia.jp/story/archives/3420) identifies her as Night Butterfly captain; the [crew profile](https://daddyjim.com/one-piece/group/Night-Butterfly-Pirates) describes it as an allied crew under the Red Hair banner. No allied-crew predicate exists, so no replacement relation was asserted. | High; crew identity confirmed, ally-relation schema gap retained. |
| Lindbergh | Mark Baltigo residence Historical | The [Revolutionary Army profile](https://onepiece.fandom.com/wiki/Revolutionary_Army) records the headquarters move from Baltigo to Momoiro Island and Lindbergh's current South Army command. | High; former base/residence. |
| Lip Doughty | Mark Fake Straw Hat affiliation and captaincy of his own crew Historical | [Lip's profile](https://onepiece.fandom.com/wiki/Lip_Doughty) describes his recruited status; the [Fake Straw Hat crew history](https://onepiece.fandom.com/wiki/Fake_Straw_Hat_Crew) records its disbandment. | Medium-high; former crew roles. |

Kunyun, Kyuji, Limejuice, and other reviewed assertions were retained where no evidence supported a correction. Kunyun's membership after the battle, Linaria's allied-crew relation, Leonero's later Whitebeard membership interval, and Giant Squad membership intervals are open questions.


## Campaign batch 054

| Entity | Predicate / value | Evidence | Confidence / scope |
|---|---|---|---|
| Lola (zombie) | Mark Thriller Bark affiliation and Wild Zombie role Historical | The [chapter-referenced profile](https://onepiece.fandom.com/wiki/Lola_%28Zombie%29) distinguishes this corpse from Charlotte Lola and records Moria removing the animating shadow in chapter 481. | High; temporary zombie state and affiliation ended. |
| Lu Feld | Remove MADS from `affiliatesWith`; keep sponsorship unresolved | [Chapter 1069's cover-story record](https://onepiece.fandom.com/wiki/Chapter_1069) identifies Lu Feld as MADS sponsor/financier, not as a scientist/member. The ontology has no sponsor predicate. | Medium-high; semantic correction, sponsorship relation needs modeling. |
| Maidy | Replace malformed `Ladys_maid` with Maid; split merged residence into Alubarna and Arabasta Kingdom | [Official profile](https://one-piece.com/character/Maidy/index.html) identifies her as an Alubarna Palace maid in Arabasta; [official Vivre Card revision](https://one-piece.com/vivre/revision/index.html) confirms kingdom affiliation. | High; current role and nested location values. |
| Macro | Mark Sun Pirates affiliation Historical | The [official profile](https://one-piece.com/character/Makuro/) calls Macro a former Sun Pirate; chapter 624 records the crew split and his formation of Macro Pirates. | High; former crew service, Macro Pirates retained current. |
| MAX Marx | Mark Roger Pirates affiliation Historical | The [official episode 969 synopsis](https://one-piece.com/anime/o5725/index.html) confirms Roger disbanded the crew; chapter 1158 supports Marx's Cook role. | High; former crew affiliation, status remains Unknown. |
| Mani | Mark Bellamy Pirates affiliation Historical | The [Mani profile](https://onepiece.fandom.com/wiki/Mani) and [crew history](https://onepiece.fandom.com/wiki/Bellamy_Pirates) cite the crew's dismissal/disbandment and Bellamy's later departure; Mani's status remains Unknown. | High; former crew affiliation only. |
| Manboshi | Replace malformed `Princeof_the_Ryugu_Kingdom` role with Prince | [Official profile](https://one-piece.com/character/Manboshi/index.html) identifies him as a Ryugu Kingdom prince. | High; corrected occupation token. |
| Manjaro | Mark Fake Straw Hat Crew affiliation Historical | [Chapter-referenced crew history](https://onepiece.fandom.com/wiki/Fake_Straw_Hat_Crew) records the exposure and dispersal at Sabaody; later impersonation of Kid Pirates is not membership. | High; past impostor crew only. |

All twenty reserved entities received partial reviews, including unchanged records and uncertainty notes; details are in `work/research/batch-054-results.json`. The removal ledger is `work/research/batch-054-removal-reasons.json`. Shared malformed occupation vocabulary was retained where other people still reference it and queued for their own review.
