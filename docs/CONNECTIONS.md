# Ontology connections

Every relationship type in the Fuseki graph (after patches + OWL RL), produced by a live count over `?a ?p ?b . ?p g:relType ?rel` (the counts below were taken on the previous Neo4j store; the ingested graph is identical).
**Used** = feeds the question bank. Generic questions come only from the `SWEEP_RELS` whitelist in `backend/app/questions.py`; dedicated questions are built by hand in the same file.
Anything not listed as used is never asked about.

Summary: 50 relationship types, 18 used, 32 ignored.

| relation | used? | why | source -> target | edges | subjects | targets | provenance |
|---|---|---|---|---|---|---|---|
| `AFFILATES_WITH` | no | TYPO of AFFILIATES_WITH (1 edge) | Character -> Affiliation | 1 | 1 | 1 | explicit |
| `AFFILIATES_WITH` | **yes** | dedicated: organisation / OWL classes (Pirate, Marine, ...) | Character -> Affiliation | 1720 | 1168 | 284 | explicit |
|  |  |  | Character -> Location | 121 | 117 | 37 | explicit |
|  |  |  | Character -> Character | 69 | 67 | 42 | explicit |
|  |  |  | Character -> PirateCrew | 12 | 12 | 1 | explicit |
| `ANIME_DEBUT` | no | trivia (episode number) | Character -> AnimeEpisode | 1347 | 1347 | 467 | explicit |
| `ARC_END_ANIME` | no | story structure | (other) -> AnimeEpisode | 3 | 3 | 3 | explicit |
| `ARC_END_MANGA` | no | story structure | (other) -> MangaIssue | 3 | 3 | 3 | explicit |
| `ARC_START_ANIME` | no | story structure | (other) -> AnimeEpisode | 3 | 3 | 3 | explicit |
| `ARC_START_MANGA` | no | story structure | (other) -> MangaIssue | 3 | 3 | 3 | explicit |
| `ATE_DEVIL_FRUIT` | **yes** | indirect: DevilFruitEater class (OWL) | Character -> DevilFruit | 140 | 139 | 130 | inferred |
|  |  |  | (other) -> DevilFruit | 13 | 13 | 13 | inferred |
| `BROADER_OCCUPATION` | no | occupation hierarchy (3 edges) | (other) -> Occupation | 3 | 2 | 2 | curated |
| `BUILT_BY` | **yes** | sweep: shipwright | Ship -> Character | 2 | 2 | 2 | curated |
| `CITIZEN_OF` | no | 1 edge | Character -> Location | 1 | 1 | 1 | explicit |
| `CONTAINS_ARC` | no | story structure | (other) -> Arc | 5 | 1 | 5 | explicit |
| `DEVIL_FRUIT_CURRENT_USER` | **yes** | dedicated: fruit -> eater (35 questions) | DevilFruit -> Character | 124 | 124 | 123 | explicit,curated |
|  |  |  | DevilFruit -> DevilFruitUser | 10 | 10 | 10 | explicit |
| `DEVIL_FRUIT_DEBUT_ANIME` | no | trivia | DevilFruit -> AnimeEpisode | 17 | 16 | 14 | explicit |
| `DEVIL_FRUIT_DEBUT_MANGA` | no | trivia | DevilFruit -> MangaIssue | 36 | 35 | 24 | explicit |
| `DEVIL_FRUIT_PREVIOUS_USER` | **yes** | dedicated: previous owner | DevilFruit -> Character | 16 | 16 | 16 | explicit,curated |
|  |  |  | DevilFruit -> DevilFruitEater | 3 | 3 | 3 | explicit |
| `DEVIL_FRUIT_USE_DEBUT_ANIME` | no | trivia | DevilFruit -> AnimeEpisode | 83 | 77 | 75 | explicit |
|  |  |  | DevilFruit -> ? | 46 | 46 | 39 | explicit |
| `DEVIL_FRUIT_USE_DEBUT_MANGA` | no | trivia | DevilFruit -> MangaIssue | 88 | 84 | 71 | explicit |
|  |  |  | DevilFruit -> ? | 55 | 54 | 50 | explicit |
| `ENGLISH_VOICE_ACTOR` | no | trivia + bad targets (Status/Affiliation) | Character -> ? | 1301 | 1032 | 673 | explicit |
|  |  |  | Character -> Person | 5 | 5 | 1 | explicit |
|  |  |  | Character -> Status | 4 | 4 | 1 | explicit |
|  |  |  | Character -> Affiliation | 3 | 3 | 1 | explicit |
|  |  |  | Character -> AnimeEpisode | 1 | 1 | 1 | explicit |
| `FOUNDER` | no | 1 edge | (other) -> Character | 1 | 1 | 1 | explicit |
| `GIVEN_AFTER` | no | bounty detail | (other) -> Arc | 30 | 30 | 8 | explicit |
| `GIVEN_TO` | no | bounty detail | (other) -> Character | 27 | 27 | 7 | explicit |
| `HASDEVIL_FRUIT` | no | TYPO of HAS_DEVIL_FRUIT (1 edge) | Character -> DevilFruit | 1 | 1 | 1 | explicit |
| `HAS_BLOOD_TYPE` | no | trivia | Character -> BloodType | 407 | 407 | 6 | explicit |
| `HAS_BOUNTY` | no | bounty nodes are per-arc (10 characters) | Character -> Bounty | 38 | 10 | 38 | explicit |
| `HAS_CREW_MEMBER` | no | inverse of IN_CREW | (other) -> Character | 10 | 1 | 10 | explicit |
| `HAS_DEVIL_FRUIT` | **yes** | dedicated: character -> fruit (2 hops) | Character -> DevilFruit | 124 | 123 | 124 | inferred,explicit |
|  |  |  | (other) -> DevilFruit | 10 | 10 | 10 | inferred |
| `HAS_FRUIT_SUBTYPE` | **yes** | dedicated: Ancient / Mythical Zoan | DevilFruit -> DevilFruitType | 7 | 7 | 2 | curated |
| `HAS_FRUIT_TYPE` | **yes** | dedicated: Paramecia / Zoan / Logia | DevilFruit -> DevilFruitType | 141 | 141 | 5 | explicit,inferred |
| `HAS_HAKI` | **yes** | indirect: HakiUser class (OWL) | Character -> HakiType | 47 | 22 | 3 | curated |
| `HEADQUARTER` | no | 1 edge | (other) -> ? | 1 | 1 | 1 | explicit |
| `IN_CREW` | no | 10 edges, single crew; AFFILIATES_WITH covers it | Character -> PirateCrew | 10 | 10 | 1 | explicit |
| `JAPANESE_VOICE_ACTOR` | no | trivia + bad targets (Status/Affiliation) | Character -> ? | 1152 | 1034 | 559 | explicit |
|  |  |  | Character -> Status | 17 | 17 | 1 | explicit |
|  |  |  | Character -> Affiliation | 9 | 9 | 1 | explicit |
|  |  |  | Character -> AnimeEpisode | 1 | 1 | 1 | explicit |
| `LATER_ANIME_APPEARANCE` | no | trivia | Character -> AnimeEpisode | 11 | 11 | 11 | curated |
| `LATER_MANGA_APPEARANCE` | no | trivia | Character -> MangaIssue | 12 | 12 | 12 | curated |
| `LIVE_ACTION_PORTRAYED_BY` | no | trivia | Character -> ? | 90 | 79 | 90 | explicit |
| `LOCATED_IN` | no | between places | (other) -> Location | 3 | 3 | 3 | explicit |
| `LOCATION` | no | 1 edge | (other) -> Location | 1 | 1 | 1 | explicit |
| `MANGA_DEBUT` | no | trivia (chapter number) | Character -> MangaIssue | 1461 | 1461 | 514 | explicit |
| `OCCUPATION` | **yes** | sweep: role (support >= 12) | Character -> Occupation | 2227 | 1243 | 669 | explicit,inferred |
|  |  |  | Character -> Character | 24 | 24 | 1 | explicit |
|  |  |  | Character -> Affiliation | 3 | 3 | 1 | explicit |
| `OPERATED_BY` | **yes** | dedicated: ship -> crew | Ship -> Affiliation | 7 | 7 | 7 | curated |
|  |  |  | Ship -> PirateCrew | 2 | 2 | 1 | curated |
| `OWNS_SHIP` | **yes** | dedicated: fruit eater owned a ship | Character -> Ship | 9 | 8 | 9 | inferred |
| `PLACE_OF_ORIGIN` | **yes** | sweep: origin (support >= 15) | Character -> Location | 581 | 576 | 24 | explicit |
| `PREVIOUSLY_HAD_DEVIL_FRUIT` | no | inverse of DEVIL_FRUIT_PREVIOUS_USER | Character -> DevilFruit | 16 | 16 | 16 | inferred |
|  |  |  | (other) -> DevilFruit | 3 | 3 | 3 | inferred |
| `RACE` | **yes** | sweep: race | Character -> Race | 10 | 10 | 3 | explicit |
| `RESIDENCE` | **yes** | sweep: residence (support >= 15) | Character -> Location | 819 | 698 | 250 | explicit |
|  |  |  | Character -> Character | 4 | 4 | 1 | explicit |
| `SHIP_OWNER` | **yes** | sweep: ship owner | Ship -> Character | 9 | 9 | 8 | curated |
| `SHIP_TYPE` | **yes** | sweep: ship type | Ship -> ShipType | 2 | 2 | 2 | curated |
| `STATUS_OF_CHARACTER` | **yes** | sweep: alive / deceased | Character -> Status | 1496 | 1489 | 5 | explicit |
| `SUBTYPE_OF` | no | schema (fruit subtype) | (other) -> DevilFruitType | 2 | 2 | 1 | curated |

## Data issues seen while listing

* `AFFILATES_WITH`, `HASDEVIL_FRUIT`: typo'd duplicates of real relations (1 edge each), candidates for `ontology/patches/`.
* `OCCUPATION -> King` points to the **character** node King (24 edges): the occupation and the Beasts Pirates member share one URI.
* `ENGLISH_/JAPANESE_VOICE_ACTOR` edges to Status / Affiliation nodes: scraper column shift. Harmless because voice actors are not asked about.
* `AFFILIATES_WITH -> Location` (Impel Down, Ryugu Kingdom, ...) and `-> Character` (Caesar Clown, ...): the organisation question only takes organisation-typed targets, so these never become questions.
* `RACE`: only 10 edges, so "Is it of the Human race?" is UNKNOWN for almost everyone.
