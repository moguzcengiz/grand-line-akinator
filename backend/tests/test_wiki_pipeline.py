"""Offline tests of the wiki infobox / category parser (no network, no Fuseki)."""
from app import wiki_pipeline as w

BOX = """{{Char Box
| name = X
| affiliation = [[Cross Guild]];{{Qref|name=a|chap=1|Text with [[Link|pipe]]; semi}}<br />[[Seven Warlords of the Sea|Warlords]] (former);{{Qref|name=b}}<br />[[Impel Down]] (formerly)
| occupation = [[Pirate]]; Cross Guild [[Officer]]; [[Baroque Works]] President (former); Proprietor of [[Rain Dinners]] (former)
| bounty = {{B}}1,965,000,000{{Qref|x}}<br />{{B}}81,000,000 (former)
}}
Text."""


def test_nested_template_and_params():
    name, p = w.find_template("{{Foo|a={{Bar|b=1|c=2}}|d=[[X|y]]}}", "foo")
    assert name == "Foo" and p == {"a": "{{Bar|b=1|c=2}}", "d": "[[X|y]]"}


def test_affiliation_current_vs_former_and_pipes():
    es = w.parse_entries(w.find_template(BOX, "char box")[1]["affiliation"])
    assert [(e["link"], e["former"]) for e in es] == [("Cross Guild", False), ("Seven Warlords of the Sea", True), ("Impel Down", True)]


def test_occupation_marker_does_not_leak_to_next_entry():
    es = w.parse_entries(w.find_template(BOX, "char box")[1]["occupation"])
    assert [(e["text"], e["former"]) for e in es] == [("Pirate", False), ("Cross Guild Officer", False),
                                                       ("Baroque Works President", True), ("Proprietor of Rain Dinners", True)]


def test_bounty_takes_highest_stated_number_and_unknown_is_none():
    assert w.parse_bounty(w.find_template(BOX, "char box")[1]["bounty"]) == 1_965_000_000
    assert w.parse_bounty("{{B}}Unknown") is None


def test_categories():
    p = {"title": "T", "categories": ["Male Characters", "Humans", "Swordsmen", "Pistol Users", "Observation Haki Users", "Worst Generation"]}
    e = w.extract_page(p, {}, "Character")
    assert e["gender"] == ["Male"] and e["race"] == ["Human"] and e["titles"] == ["Worst Generation"]
    assert e["fightingStyle"] == ["Pistol user", "Swordsman"]   # Haki users are not a weapon class
