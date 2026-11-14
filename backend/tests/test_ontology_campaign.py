import json

from rdflib import Graph, URIRef, RDF, RDFS, OWL, Literal
from rdflib.namespace import XSD

from app import ontology_campaign as campaign
from app.ontology import OP, OPX, load_sources


def test_build_queue_captures_facts_aliases_and_open_world_gaps():
    graph = Graph()
    graph.add((OP.Luffy, RDF.type, OP.Character))
    graph.add((OP.Luffy, RDFS.label, Literal("Monkey D. Luffy")))
    graph.add((OP.Luffy, OP.affiliatesWith, OP.Straw_Hat_Pirates))
    graph.add((OP.Luffy, OP.alias, Literal("Straw Hat")))
    graph.add((OP.HiddenClass, RDF.type, OWL.Class))
    graph.add((OP.someProperty, RDF.type, OWL.ObjectProperty))
    graph.add((OP.Unresolved, OP.DevilFruitCurrentUser, OP.MysteryUser))
    slash_fruit = URIRef("http://kalnassag.com/onepiece/Hebi_Hebi_no_Mi,_Model:_Anaconda")
    graph.add((slash_fruit, RDF.type, OP.DevilFruit))
    graph.add((slash_fruit, RDFS.label, Literal("Snake-Snake Fruit, Model: Anaconda", lang="en")))

    rows = {row["entity_uri"]: row for row in campaign.build_queue(graph)}
    luffy = rows[str(OP.Luffy)]
    assert luffy["canonical_name"] == "Monkey D. Luffy"
    assert "Straw Hat" in luffy["aliases"]
    assert any(a["predicate_uri"] == str(OP.affiliatesWith) for a in luffy["assertions"])
    assert luffy["coverage_review"][str(OP.hasDevilFruit)]["asserted_positive_count"] == 0
    assert luffy["coverage_review"][str(OP.hasDevilFruit)]["evidence_status"] == "not_independently_reviewed"
    assert str(OP.HiddenClass) not in rows
    assert str(OP.someProperty) not in rows
    assert rows[str(OP.MysteryUser)]["identity_review_required"] is True
    assert rows[str(slash_fruit)]["canonical_name"] == "Snake-Snake Fruit, Model: Anaconda"


def test_queue_excludes_reified_provenance_statement_nodes():
    graph = Graph()
    entity = URIRef("http://kalnassag.com/onepiece#Clover")
    statement = URIRef("http://kalnassag.com/onepiece-ext#evidence1")
    graph.add((entity, RDF.type, OP.Character))
    graph.add((entity, RDFS.label, Literal("Clover", lang="en")))
    graph.add((statement, RDF.type, RDF.Statement))
    graph.add((statement, RDF.subject, entity))
    graph.add((statement, RDF.predicate, OP.occupation))
    graph.add((statement, RDF.object, OP.Chief_Librarian))

    rows = campaign.build_queue(graph)

    ids = {row["entity_uri"] for row in rows}
    assert str(entity) in ids
    assert str(statement) not in ids


def test_queue_excludes_temporal_statement_and_status_nodes():
    graph = Graph()
    entity = URIRef("http://kalnassag.com/onepiece#Smoker")
    temporal = URIRef("http://kalnassag.com/onepiece-ext#temporalSmokerRank")
    graph.add((entity, RDF.type, OP.Character))
    graph.add((entity, RDFS.label, Literal("Smoker", lang="en")))
    graph.add((temporal, RDF.type, OPX.TemporalStatement))
    graph.add((temporal, RDF.subject, entity))
    graph.add((temporal, RDF.predicate, OP.occupation))
    graph.add((temporal, RDF.object, OP.Vice_Admiral))
    graph.add((temporal, OPX.temporalStatus, OPX.Current))
    graph.add((OPX.Current, RDF.type, OPX.TemporalStatus))

    ids = {row["entity_uri"] for row in campaign.build_queue(graph)}

    assert str(entity) in ids
    assert str(temporal) not in ids
    assert str(OPX.Current) not in ids


def test_resume_is_idempotent_for_active_batch(tmp_path, monkeypatch):
    graph = Graph()
    for index in range(3):
        subject = OP[f"Character{index}"]
        graph.add((subject, RDF.type, OP.Character))
        graph.add((subject, RDFS.label, Literal(f"Character {index}")))
    monkeypatch.setattr(campaign, "WORK", tmp_path / "work")
    monkeypatch.setattr(campaign, "QUEUE", tmp_path / "work/queue.jsonl")
    monkeypatch.setattr(campaign, "STATE", tmp_path / "work/state.json")
    monkeypatch.setattr(campaign, "EVENTS", tmp_path / "work/events.jsonl")
    monkeypatch.setattr(campaign, "PROGRESS", tmp_path / "progress.md")
    monkeypatch.setattr(campaign, "load_sources", lambda: (graph, Graph()))

    first, _, _ = campaign.resume(batch_size=2)
    second, _, rows = campaign.resume(batch_size=2)
    assert second["batch_id"] == first["batch_id"]
    assert len([r for r in rows if r["status"] == "in_progress"]) == 2


def test_recorded_batch_closes_only_when_every_item_is_resolved(tmp_path, monkeypatch):
    graph = Graph()
    for index in range(2):
        subject = OP[f"Character{index}"]
        graph.add((subject, RDF.type, OP.Character))
        graph.add((subject, RDFS.label, Literal(f"Character {index}")))
    monkeypatch.setattr(campaign, "WORK", tmp_path / "work")
    monkeypatch.setattr(campaign, "QUEUE", tmp_path / "work/queue.jsonl")
    monkeypatch.setattr(campaign, "STATE", tmp_path / "work/state.json")
    monkeypatch.setattr(campaign, "EVENTS", tmp_path / "work/events.jsonl")
    monkeypatch.setattr(campaign, "PROGRESS", tmp_path / "progress.md")
    monkeypatch.setattr(campaign, "load_sources", lambda: (graph, Graph()))
    batch, _, _ = campaign.resume(batch_size=2)
    results = tmp_path / "results.json"
    results.write_text(json.dumps({"results": [
        {"entity_uri": uri, "status": "no_change", "findings": [], "source_urls": []}
        for uri in batch["entity_uris"]
    ]}))
    _, state, rows = campaign.record_results(results)
    assert state["active_batch"] is None
    by_uri = {row["entity_uri"]: row for row in rows}
    assert all(by_uri[uri]["status"] == "no_change" for uri in batch["entity_uris"])


def test_resume_preserves_active_batch_after_partial_review(tmp_path, monkeypatch):
    graph = Graph()
    for index in range(3):
        subject = OP[f"Character{index}"]
        graph.add((subject, RDF.type, OP.Character))
        graph.add((subject, RDFS.label, Literal(f"Character {index}")))
    monkeypatch.setattr(campaign, "WORK", tmp_path / "work")
    monkeypatch.setattr(campaign, "QUEUE", tmp_path / "work/queue.jsonl")
    monkeypatch.setattr(campaign, "STATE", tmp_path / "work/state.json")
    monkeypatch.setattr(campaign, "EVENTS", tmp_path / "work/events.jsonl")
    monkeypatch.setattr(campaign, "PROGRESS", tmp_path / "progress.md")
    monkeypatch.setattr(campaign, "load_sources", lambda: (graph, Graph()))
    batch, _, _ = campaign.resume(batch_size=2)

    results = tmp_path / "partial.json"
    results.write_text(json.dumps({"results": [{
        "entity_uri": batch["entity_uris"][0], "status": "reviewed_partial",
        "findings": [], "source_urls": []
    }]}))
    campaign.record_results(results)
    resumed, _, rows = campaign.resume(batch_size=2)

    assert resumed["batch_id"] == batch["batch_id"]
    assert len(resumed["entity_uris"]) == 2
    assert len([row for row in rows if row["status"] == "in_progress"]) == 1


def test_campaign_batch_001_contains_only_reviewed_deltas_with_provenance():
    base, ext = load_sources()
    graph = base + ext
    assert (OP.Caesar_Clown, OP.temporaryAlias, Literal("Gangster Gastino", lang="en")) in graph
    assert (OP.Enel, OPX.hasHaki, OPX.ObservationHaki) in graph
    assert (OP.Portgas_D_Ace, OPX.hasHaki, OPX.ConquerorsHaki) in graph
    # Fruit ownership findings were already present on fruit subjects; no duplicate
    # character-side assertions are introduced by this batch patch.
    assert (OP.Caesar_Clown, OP.hasDevilFruit, OP.Gasu_Gasu_no_Mi) not in graph
    assert (OP.Gasu_Gasu_no_Mi, OP.DevilFruitCurrentUser, OP.Caesar_Clown) in graph
    evidence = set(graph.subjects(RDF.type, RDF.Statement))
    campaign_evidence = {s for s in evidence if str(s).startswith(str(OPX) + "evidenceCampaign001")}
    assert len(campaign_evidence) == 3
    for statement in campaign_evidence:
        assert graph.value(statement, RDF.subject) is not None
        assert graph.value(statement, RDF.predicate) is not None
        assert graph.value(statement, RDF.object) is not None
        assert graph.value(statement, OPX.confidence) == Literal("high")


def test_campaign_batch_002_adds_only_source_backed_bounty_fruit_and_role_facts():
    base, ext = load_sources()
    graph = base + ext
    fruit = URIRef("http://kalnassag.com/onepiece/Inu_Inu_no_Mi,_Model:_Kyubi_no_Kitsune")
    assert (OP.Clou_D_Clover, OP.occupation, OP.Chief_Librarian) in graph
    assert (OP.Dorry, OP.hasBounty, OP.Dorry_Bounty) in graph
    assert (OP.Dorry_Bounty, RDF.type, OP.Bounty) in graph
    assert (OP.Dorry_Bounty, OP.bountyAmount, Literal(100000000)) in graph
    assert (OP.Dorry_Bounty, OP.givenTo, OP.Dorry) in graph
    assert (fruit, RDF.type, OP.DevilFruit) in graph
    assert (fruit, OP.DevilFruitCurrentUser, OP.Catarina_Devon) in graph
    assert (fruit, OP.hasFruitType, OP.Zoan) in graph
    assert (fruit, OPX.hasFruitSubtype, OPX.MythicalZoan) in graph
    evidence = {s for s in graph.subjects(RDF.type, RDF.Statement)
                if str(s).startswith(str(OPX) + "evidenceCampaign002")}
    assert len(evidence) == 10
    assert all(graph.value(s, OPX.confidence) == Literal("high") for s in evidence)


def test_campaign_batch_006_has_sourced_bounties_temporal_records_and_editorial_removals():
    base, ext = load_sources()
    graph = base + ext
    patch = Graph().parse(str(campaign.config.ROOT / "ontology/patches/campaign-batch-006.add.ttl"), format="turtle")
    bounty_values = {
        OP.Marco: 1_374_000_000, OP.Mikita: 7_500_000, OP.Pekoms: 330_000_000,
        OP.Pica: 99_000_000, OP.Scratchmen_Apoo: 350_000_000, OP.Shanks: 4_048_900_000,
        OP.Tamago: 429_000_000, OP.Trebol: 99_000_000, OP.Van_Augur: 64_000_000,
        OP.X_Drake: 222_000_000,
    }
    for character, amount in bounty_values.items():
        bounty = next(graph.objects(character, OP.hasBounty))
        assert graph.value(bounty, OP.bountyAmount) == Literal(amount)
        assert graph.value(bounty, OP.givenTo) == character
    assert (OP.Pekoms, OPX.hasHaki, OPX.ArmamentHaki) in graph
    temporal = {s for s in graph.subjects(RDF.type, OPX.TemporalStatement)
                if str(s).startswith(str(OPX) + "evidenceCampaign006")}
    assert len(temporal) == 17
    for statement in temporal:
        subject = graph.value(statement, RDF.subject)
        predicate = graph.value(statement, RDF.predicate)
        obj = graph.value(statement, RDF.object)
        # The temporal annotation does not duplicate or entail an undated fact;
        # legacy unqualified assertions remain present in the source graph.
        assert (subject, predicate, obj) not in patch
        assert (subject, predicate, obj) in graph
        status = graph.value(statement, OPX.temporalStatus)
        evidence = next(graph.subjects(RDF.subject, statement))
        assert graph.value(evidence, RDF.predicate) == OPX.temporalStatus
        assert graph.value(evidence, RDF.object) == status
        assert graph.value(evidence, OPX.confidence) == Literal("high")
    assert (OP.Mikita, OP.temporaryAlias, Literal('VIZ/4Kids: "Ms. Valentine"', lang="ja-latn")) not in graph
    assert (OP.Pekoms, OP.temporaryAlias, Literal('Viz: "Mystoms"', lang="ja-latn")) not in graph
    assert (OP.X_Drake, OP.temporaryAlias, Literal("English version: Drie", lang="ja-latn")) not in graph
    assert (OP.Tsuru, OP.epithet, Literal('Viz: "Great Advisor"', lang="ja-latn")) not in graph
    assert (OP.Mikita, OP.temporaryAlias, Literal("Miss Valentine", lang="en")) in graph
    assert (OP.Pekoms, OP.temporaryAlias, Literal("Nazoms", lang="en")) in graph


def test_campaign_batch_007_adds_verified_bounties_and_corrects_luffy_fruit_type():
    base, ext = load_sources()
    graph = base + ext
    bounties = {
        OP.Zala: 35_000_000, OP.Edward_Newgate: 5_046_000_000,
        OP.Kaidou: 4_611_100_000, OP.Marshall_D_Teach: 3_996_000_000,
        OP.Trafalgar_D_Water_Law: 3_000_000_000,
    }
    for character, amount in bounties.items():
        bounty = next(graph.objects(character, OP.hasBounty))
        assert graph.value(bounty, OP.bountyAmount) == Literal(amount)
        assert graph.value(bounty, OP.givenTo) == character
    assert (OP.Gomu_Gomu_no_Mi, OP.hasFruitType, OP.Paramecia) not in graph
    assert (OP.Gomu_Gomu_no_Mi, OP.hasFruitType, OP.Zoan) in graph
    assert (OP.Gomu_Gomu_no_Mi, OPX.hasFruitSubtype, OPX.MythicalZoan) in graph
    assert (OP.Gomu_Gomu_no_Mi, RDFS.label, Literal('ヒトヒトの実 幻獣種 モデル〝ニカ〟', lang="ja")) in graph
    temporal = {s for s in graph.subjects(RDF.type, OPX.TemporalStatement)
                if str(s).startswith(str(OPX) + "evidenceCampaign007")}
    assert len(temporal) == 20
    patch = Graph().parse(str(campaign.config.ROOT / "ontology/patches/campaign-batch-007.add.ttl"), format="turtle")
    for statement in temporal:
        triple = (graph.value(statement, RDF.subject), graph.value(statement, RDF.predicate),
                  graph.value(statement, RDF.object))
        assert triple in graph
        assert triple not in patch


def test_campaign_batch_009_repairs_model_labels_with_official_provenance():
    base, ext = load_sources()
    graph = base + ext
    leopard = URIRef("http://kalnassag.com/onepiece/Neko_Neko_no_Mi,_Model:_Leopard")
    bison = URIRef("http://kalnassag.com/onepiece/Ushi_Ushi_no_Mi,_Model:_Bison")
    leopard_label = Literal("ネコネコの実 モデル 〝豹（レオパルド）〟", lang="ja")
    bison_label = Literal("ウシウシの実 モデル 〝野牛（バイソン）〟", lang="ja")

    assert (leopard, RDFS.label, leopard_label) in graph
    assert (bison, RDFS.label, bison_label) in graph
    assert (leopard, RDFS.label, Literal("ネコネコの実 モデル“”", lang="ja")) not in graph
    assert (bison, RDFS.label, Literal("ウシウシの実 モデル", lang="ja")) not in graph
    assert (leopard, OP.DevilFruitCurrentUser, OP.Rob_Lucci) in graph
    assert (bison, OP.DevilFruitCurrentUser, OP.Dalton) in graph

    evidence = {s for s in graph.subjects(RDF.type, RDF.Statement)
                if str(s).startswith(str(OPX) + "evidenceCampaign009")}
    assert len(evidence) == 2
    assert all(graph.value(statement, OPX.confidence) == Literal("high") for statement in evidence)
    assert all(graph.value(statement, RDF.predicate) == RDFS.label for statement in evidence)


def test_campaign_batch_010_repairs_fruit_labels_and_records_origin_with_provenance():
    base, ext = load_sources()
    graph = base + ext
    x_drake_fruit = URIRef("http://kalnassag.com/onepiece-ext#Ryu_Ryu_no_Mi_Model_Allosaurus")
    marco_fruit = URIRef("http://kalnassag.com/onepiece-ext#Tori_Tori_no_Mi_Model_Phoenix")
    kaido_fruit = URIRef("http://kalnassag.com/onepiece-ext#Uo_Uo_no_Mi_Model_Seiryu")
    giraffe_fruit = URIRef("http://kalnassag.com/onepiece/Ushi_Ushi_no_Mi,_Model:_Giraffe")

    expected_labels = {
        x_drake_fruit: "リュウリュウの実 古代種 モデル 〝アロサウルス〟",
        marco_fruit: "トリトリの実 幻獣種 モデル 〝不死鳥(フェニックス)〟",
        kaido_fruit: "ウオウオの実 幻獣種 モデル 〝青龍〟",
        giraffe_fruit: "ウシウシの実 モデル 〝麒麟（ジラフ）〟",
    }
    for fruit, label in expected_labels.items():
        assert (fruit, RDFS.label, Literal(label, lang="ja")) in graph
    assert (giraffe_fruit, RDFS.label, Literal("ウシウシの実 モデル“”", lang="ja")) not in graph
    assert (OP.Judy, OP.placeOfOrigin, OP.Sabaody_Archipelago) in graph
    assert (x_drake_fruit, OP.DevilFruitCurrentUser, OP.X_Drake) in graph
    assert (marco_fruit, OP.DevilFruitCurrentUser, OP.Marco) in graph
    assert (kaido_fruit, OP.DevilFruitCurrentUser, OP.Kaidou) in graph

    evidence = {s for s in graph.subjects(RDF.type, RDF.Statement)
                if str(s).startswith(str(OPX) + "evidenceCampaign010")}
    assert len(evidence) == 7
    assert all(graph.value(statement, OPX.confidence) == Literal("high") for statement in evidence)

    temporal = {s for s in graph.subjects(RDF.type, OPX.TemporalStatement)
                if str(s).startswith(str(OPX) + "evidenceCampaign010")}
    assert len(temporal) == 2
    assert any(graph.value(s, OPX.temporalStatus) == OPX.Historical for s in temporal)
    assert any(graph.value(s, OPX.temporalStatus) == OPX.Current for s in temporal)
    assert (OP.Going_Merry, OPX.operatedBy, OP.Straw_Hat_Pirates) in graph
    assert (OPX.Thousand_Sunny, OPX.operatedBy, OP.Straw_Hat_Pirates) in graph


def test_campaign_batch_011_repairs_character_vs_affiliation_types_and_identity():
    base, ext = load_sources()
    graph = base + ext
    evidence_prefix = str(OPX) + "evidenceCampaign011"

    # Official profiles list these individual characters/weapons as entities, while
    # the Duck Troops are the group to which Cowboy belongs.
    for character in (OP.Chimney, OP.Chouchou, OP.Pacifista):
        assert (character, RDF.type, OP.Character) in graph
        assert (character, RDF.type, OP.Affiliation) not in graph
    assert (OP.Pacifista, RDF.type, OPX.WorldGovernmentOrganization) not in graph
    duck_troops = OP["Super_Spot-Billed_Duck_Troops"]
    assert (duck_troops, RDF.type, OP.Affiliation) in graph
    assert (duck_troops, RDF.type, OP.Character) not in graph

    assert (OP.Aswa, OP.affiliatesWith, OP.Arabasta_Kingdom) in graph
    assert (OP.Banchina, OP.affiliatesWith, OP.Syrup_Village) in graph
    assert (OP.Cowboy, OP.affiliatesWith, duck_troops) in graph
    assert (OP.Cowboy, RDFS.label, Literal("カウボーイ", lang="ja")) in graph
    assert (OP.Cowboy, OP.romanizedName, Literal("Chō Karugamo Butai", datatype=XSD.string)) not in graph
    assert (OP.Cowboy, RDFS.label, Literal("超カルガモ部隊", lang="ja")) not in graph

    evidence = {s for s in graph.subjects(RDF.type, RDF.Statement)
                if str(s).startswith(evidence_prefix)}
    assert len(evidence) == 4
    assert all(graph.value(statement, OPX.confidence) == Literal("high") for statement in evidence)


def test_campaign_batch_013_adds_sourced_facts_and_temporal_roles():
    base, ext = load_sources()
    graph = base + ext

    bounty = OP.Helmeppo_Cross_Guild_Bounty_Profile
    assert (OP.Helmeppo, OP.hasBounty, bounty) in graph
    assert (bounty, RDF.type, OP.Bounty) in graph
    assert (bounty, OP.bountyAmount, Literal(100_000_000, datatype=XSD.integer)) in graph
    assert (bounty, OP.givenTo, OP.Helmeppo) in graph
    assert (OP.Island_Eater, URIRef("http://schema.org/birthDate"),
            Literal("--04-21", datatype=XSD.gMonthDay)) in graph
    assert (OP.Island_Eater, OP.placeOfOrigin, OP.Little_Garden) in graph

    temporal = {s for s in graph.subjects(RDF.type, OPX.TemporalStatement)
                if str(s).startswith(str(OPX) + "Campaign013")}
    assert len(temporal) == 10
    assert any(graph.value(s, RDF.subject) == OP.Helmeppo
               and graph.value(s, RDF.object) == OP.Lieutenant_Commander
               and graph.value(s, OPX.temporalStatus) == OPX.Current for s in temporal)
    assert any(graph.value(s, RDF.subject) == OP.Johnny
               and graph.value(s, RDF.object) == OP.Bounty_Hunter
               and graph.value(s, OPX.temporalStatus) == OPX.Historical for s in temporal)
    assert any(graph.value(s, RDF.subject) == OP.Johnny
               and graph.value(s, RDF.object) == OP.Fisherman
               and graph.value(s, OPX.temporalStatus) == OPX.Current for s in temporal)

    evidence = {s for s in graph.subjects(RDF.type, RDF.Statement)
                if str(s).startswith(str(OPX) + "evidenceCampaign013")}
    assert len(evidence) == 56
    assert all(graph.value(s, OPX.confidence) == Literal("high")
               and graph.value(s, URIRef("http://www.w3.org/ns/prov#wasDerivedFrom")) is not None
               for s in evidence)


def test_campaign_batch_013_removes_misclassified_affiliations_and_hocker_relation():
    base, ext = load_sources()
    graph = base + ext
    for character in (OP.Helmeppo, OP.Hocker, OP.Iceburg, OP.Johnny):
        assert (character, RDF.type, OP.Character) in graph
        assert (character, RDF.type, OP.Affiliation) not in graph
    assert (OP.Hocker, OP.affiliatesWith, OP.Chouchou) not in graph
    assert (OP.Chouchou, OP.affiliatesWith, OP.Hocker) not in graph
    # Pet-to-person ownership is a sourced relationship but remains unasserted
    # until the ontology has a suitable predicate.

    from app.validation import shacl_report
    assert shacl_report(graph)["violations"] == 0
