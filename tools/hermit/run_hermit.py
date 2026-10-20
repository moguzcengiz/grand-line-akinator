import sys, warnings
from owlready2 import World, AllDifferent, sync_reasoner, OwlReadyInconsistentOntologyError, default_world
OP = "http://kalnassag.com/onepiece#"; OPX = "http://kalnassag.com/onepiece-ext#"
def scenario(file, title, setup):
    w = World()
    onto = w.get_ontology(f"file:///w/{file}").load()
    ind = lambda n: w[(OPX if n in ("AncientZoan", "MythicalZoan") else OP) + n]
    inds_in_play = sorted({i.name for i in onto.individuals() if i.name in ("Paramecia","Zoan","Logia","Special_Paramecia","Artificial_Zoan","AncientZoan","MythicalZoan")})
    with onto:
        setup(ind, inds_in_play)
        try:
            sync_reasoner([onto], infer_property_values=False, debug=0)
            extra = {n: sorted(x.name for x in ind(n).equivalent_to if hasattr(x, "name")) for n in inds_in_play if ind(n).equivalent_to}
            print(f"  {title:<62} CONSISTENT   inferred sameAs: {extra or '-'}")
        except OwlReadyInconsistentOntologyError:
            print(f"  {title:<62} INCONSISTENT")
for f in ("slice_upstream.owl", "slice_ext.owl"):
    print(f"\n== {f}  (individuals typed DevilFruitType via range/assertion: see mkslice output)")
    scenario(f, "S1 as-is (no distinctness axioms in the ontology)", lambda ind, n: None)
    scenario(f, "S2 Special_Paramecia differentFrom Paramecia and Zoan", lambda ind, n: setattr(ind("Special_Paramecia"), "differentFrom", [ind("Paramecia"), ind("Zoan")]))
    scenario(f, "S3 AllDifferent(Paramecia, Zoan, Logia) only", lambda ind, n: AllDifferent([ind("Paramecia"), ind("Zoan"), ind("Logia")]))
    scenario(f, "S4 AllDifferent(every type individual used in the data)", lambda ind, n: AllDifferent([ind(x) for x in n]))
