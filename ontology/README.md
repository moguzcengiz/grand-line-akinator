# Ontology layer

Everything this project adds on top of the upstream ontology, which is vendored unchanged in [`../ontology-src/`](../ontology-src)
([kalnassag/one-piece-ontology](https://github.com/kalnassag/one-piece-ontology), MIT). Details: [docs/ONTOLOGY.md](../docs/ONTOLOGY.md).

| Path | What it is |
|---|---|
| `extension.ttl` | extra classes, properties and OWL 2 RL axioms (inverse, someValuesFrom, hasValue, property chain) |
| `curated.ttl` | hand-curated data the upstream lacks: ships, Haki profiles, Ancient/Mythical Zoan fruits |
| `shapes.ttl` | SHACL shapes checked at ingestion |
| `patches/<name>.add.ttl`, `patches/<name>.remove.ttl` | reviewable corrections and additions applied on load; the upstream files are never edited |
| `patches/wiki-attributes.add.ttl` | gender, race, fighting style, titles, bounty tier, current/former affiliation and occupation (`python -m app.wiki_pipeline`) |
| `patches/debut-arc.add.ttl` | debut arc, saga and before/after the timeskip (`python -m app.arcs`) |
| `story-arcs.json` | the 33-arc / 11-saga table behind the story-time patch |

A patch can be left out with `SKIP_PATCHES=<name>,<name>`; `APPLY_PATCHES=0` loads the upstream graph alone.

Data in `patches/wiki-attributes.add.ttl`, `patches/debut-arc.add.ttl` and `story-arcs.json` is derived from the
[One Piece Wiki](https://onepiece.fandom.com) and is available under CC BY-SA; each entity records its source page and revision.
