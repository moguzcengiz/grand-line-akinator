# owl:oneOf / DevilFruitType - does it make the ontology inconsistent under OWL 2 DL?

Axioms in the upstream schema (`ontology-src/ontology/onepiece-ontology.ttl`):
```
op:DevilFruitType owl:equivalentClass [ a owl:Class ; owl:oneOf ( op:Paramecia op:Zoan op:Logia ) ] .
op:hasFruitType   rdfs:range op:DevilFruitType .
```
Data / extension that use more values: `Special_Paramecia`, `Artificial_Zoan` (upstream data), `opx:AncientZoan`, `opx:MythicalZoan` (our extension).
No `owl:differentFrom`, `owl:AllDifferent` or `owl:disjointWith` exists anywhere, and OWL 2 has no unique-name assumption.

Reproduce (HermiT via owlready2 in a throw-away container; the application image is untouched):
```bash
python tools/hermit/mkslice.py        # writes slice_upstream.owl / slice_ext.owl (schema axioms + all hasFruitType data)
docker run --rm -v "$PWD/tools/hermit:/w" -w /w python:3.12-slim sh -c \
  "apt-get update -qq && apt-get install -y -qq --no-install-recommends default-jre-headless && pip install -q owlready2 && python run_hermit.py"
```
Result (see docs/ONTOLOGY_AUDIT.md section 3c).
