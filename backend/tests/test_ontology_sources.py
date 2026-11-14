import hashlib

from rdflib import Graph, RDF, RDFS, Literal

from app.ontology import OP
from app.ontology_sources import ProfileFacts, ProfileHeader, _extract_profile_document


def test_profile_parser_scopes_modern_profile_block_and_preserves_line_breaks():
    parser = ProfileFacts()
    parser.feed('''<div class="el-list-term" data-column="profile">
      <dl><dt><span>組織</span></dt><dd><p>クルー<br/>世代</p></dd></dl>
      </div><div class="el-list-term"><dl><dt>懸賞金</dt><dd>999</dd></dl></div>''')
    assert parser.rows == [("組織", "クルー\n世代")]


def test_profile_parser_supports_legacy_primary_profile_and_ignores_related_rows():
    parser = ProfileFacts()
    parser.feed('''<div class="el-list-term" data-txt-row="horizontal">
      <dl><dt>通称</dt><dd>旧名</dd></dl></div>
      <div class="el-list-term"><dl><dt>組織</dt><dd>別の人物の crew</dd></dl></div>''')
    assert parser.rows == [("通称", "旧名")]


def test_profile_parser_ignores_legacy_definition_lists_inside_related_character_cards():
    parser = ProfileFacts()
    parser.feed('''<main><section><h1>パート</h1><p>プロフィールの本文</p></section>
      <section><div class="el-card-block"><div class="el-list-term" data-txt-row="horizontal">
      <dl><dt>懸賞金</dt><dd>別人物の懸賞金</dd></dl>
      <dl><dt>悪魔の実</dt><dd>別人物の能力</dd></dl>
      </div></div></section></main>''')
    assert parser.rows == []


def test_profile_header_captures_only_primary_title_context():
    parser = ProfileHeader()
    parser.feed('''<div class="el-heading-lv1__container"><h1>パート</h1>
      <p>ボニー海賊団 / 船員</p></div>
      <div class="el-heading-lv2__container"><p>related crew heading</p></div>''')
    assert parser.paragraphs == ["ボニー海賊団 / 船員"]


def test_exact_extraction_requires_unique_character_and_value_matches():
    graph = Graph()
    graph.add((OP.Alpha, RDF.type, OP.Character))
    graph.add((OP.Alpha, RDFS.label, Literal("Alpha", lang="en")))
    graph.add((OP.Crew, RDF.type, OP.Affiliation))
    graph.add((OP.Crew, RDFS.label, Literal("クルー", lang="ja")))
    graph.add((OP.Fruit, RDF.type, OP.DevilFruit))
    graph.add((OP.Fruit, RDFS.label, Literal("実", lang="ja")))
    body = ("""<html><h1>\u30a2\u30eb\u30d5\u30a1</h1>
      <div class="el-list-term" data-column="profile">
      <dl><dt>\u7d44\u7e54</dt><dd>\u30af\u30eb\u30fc</dd></dl>
      <dl><dt>\u60aa\u9b54\u306e\u5b9f</dt><dd>\u5b9f</dd></dl></div></html>""").encode("utf-8")
    meta = {"sha256": hashlib.sha256(body).hexdigest(), "cache_hit": True}
    result = _extract_profile_document("https://one-piece.com/character/Alpha/index.html", body, meta,
                                       {"alpha": {OP.Alpha}}, {"クルー": {OP.Crew}, "実": {OP.Fruit}})
    assert result["match_status"] == "exact"
    assert result["entity_uri"] == str(OP.Alpha)
    assert all(f["source_url"] == result["url"] for f in result["facts"])
    assert all(f["evidence"]["document_sha256"] == meta["sha256"] for f in result["facts"])
    assert {f["object_or_literal"]["value"] for f in result["facts"]} == {str(OP.Crew), str(OP.Fruit)}


def test_embedded_name_match_is_queued_for_review_without_attaching_facts():
    graph = Graph()
    graph.add((OP.Manmayer_Gunko, RDF.type, OP.Character))
    graph.add((OP.Manmayer_Gunko, RDFS.label, Literal("軍子宮", lang="ja")))
    body = ("""<html><h1>マンマイヤー・軍子宮</h1>
      <div class="el-list-term" data-column="profile">
      <dl><dt>悪魔の実</dt><dd>アロアロの実</dd></dl>
      </div></html>""").encode("utf-8")
    meta = {"sha256": hashlib.sha256(body).hexdigest(), "cache_hit": True}
    result = _extract_profile_document(
        "https://one-piece.com/character/Saint_Manmayer_Gunko/index.html", body, meta,
        {"manmayergunko": {OP.Manmayer_Gunko}}, {"アロアロの実": {OP.Aro_Aro_no_Mi}})
    assert result["match_status"] == "review_required"
    assert result["entity_uri"] is None
    assert result["candidate_entity_uris"] == [str(OP.Manmayer_Gunko)]
    assert result["facts"][0]["entity_uri"] is None
    assert result["facts"][0]["extraction_status"] == "identity_review_required"


def test_conflicting_exact_slug_and_title_matches_are_routed_to_review():
    body = ('''<html><h1>ヴィンスモーク・ソラ</h1>
      <div class="el-list-term" data-column="profile">
      <dl><dt>組織</dt><dd>ジェルマ王国</dd></dl>
      </div></html>''').encode("utf-8")
    meta = {"sha256": hashlib.sha256(body).hexdigest(), "cache_hit": True}
    index = {"sora": {OP.Sora}, "ヴィンスモークソラ": {OP.Vinsmoke_Sora}}
    result = _extract_profile_document(
        "https://one-piece.com/character/sora/index.html", body, meta, index,
        {"ジェルマ王国": {OP.Germa_Kingdom}})

    assert result["match_status"] == "review_required"
    assert result["entity_uri"] is None
    assert set(result["candidate_entity_uris"]) == {str(OP.Sora), str(OP.Vinsmoke_Sora)}
    assert result["facts"][0]["entity_uri"] is None
    assert result["facts"][0]["extraction_status"] == "identity_review_required"


def test_source_cache_rejects_non_official_hosts():
    from app.ontology_sources import clean_url
    try:
        clean_url("https://example.com/character/Alpha/index.html")
    except ValueError:
        pass
    else:
        raise AssertionError("non-official source URL was accepted")
