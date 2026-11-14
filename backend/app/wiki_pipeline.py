"""One Piece Fandom wiki -> ontology patch.  Three separately runnable stages (stdlib + rdflib only):

    python -m app.wiki_pipeline fetch    # Fuseki targets -> work/source-cache/wiki/*.json (network, 1 req/s, cached)
    python -m app.wiki_pipeline extract  # cache -> work/wiki-extracted.json (offline)
    python -m app.wiki_pipeline emit     # work/wiki-extracted.json -> ontology/patches/wiki-attributes.add.ttl (offline)

Source: https://onepiece.fandom.com (CC-BY-SA).  Only values the page states are extracted; nothing is inferred or guessed.
"""
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "work/source-cache/wiki"
TARGETS = CACHE / "targets.json"
EXTRACTED = ROOT / "work/wiki-extracted.json"
PATCH = ROOT / "ontology/patches/wiki-attributes.add.ttl"
API = "https://onepiece.fandom.com/api.php"
OPN = "http://kalnassag.com/onepiece#"
MIN_POP = 12


# ---------------------------------------------------------------- fetch
def sparql_targets(endpoint: str) -> list[dict]:
    q = """PREFIX a:<http://kalnassag.com/akinator#> SELECT ?s ?n ?c ?p ?w WHERE { GRAPH <urn:akinator:game> {
      ?s a:popularity ?p ; a:category ?c ; a:name ?n . OPTIONAL { ?s a:opwikiID ?w }
      FILTER(?p >= %d && ?c IN ("Character","DevilFruit")) } }""" % MIN_POP
    req = urllib.request.Request(endpoint + "?" + urllib.parse.urlencode({"query": q}),
                                 headers={"Accept": "application/sparql-results+json"})
    rows = json.load(urllib.request.urlopen(req, timeout=60))["results"]["bindings"]
    return sorted(({"uri": r["s"]["value"], "name": r["n"]["value"], "category": r["c"]["value"],
                    "popularity": int(r["p"]["value"]), "wikiId": r.get("w", {}).get("value")} for r in rows),
                  key=lambda t: t["uri"])


def _title(t: dict) -> str:
    return (t["wikiId"] or t["uri"].rsplit("#", 1)[-1]).replace("_", " ")


def _api(params: dict) -> dict:
    """Cached GET; at most one network request per second."""
    key = hashlib.sha1(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16]
    f = CACHE / f"{key}.json"
    if f.exists():
        return json.loads(f.read_text())
    time.sleep(1.0)
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "research-script/1.0"})
    data = json.load(urllib.request.urlopen(req, timeout=60))   # HTTPError (e.g. 403) propagates: stop, do not work around
    f.write_text(json.dumps({"params": params, "response": data}))
    return {"params": params, "response": data}


HAS_BOX = re.compile(r"\{\{\s*(char|devil fruit) box", re.I)


def fetch(endpoint: str):
    CACHE.mkdir(parents=True, exist_ok=True)
    targets = sparql_targets(endpoint)
    TARGETS.write_text(json.dumps(targets, indent=1))
    titles = sorted({_title(t) for t in targets})
    print(f"{len(targets)} targets, {len(titles)} titles")
    for i in range(0, len(titles), 50):
        params = {"action": "query", "format": "json", "formatversion": "2", "redirects": "1",
                  "titles": "|".join(titles[i:i + 50]), "prop": "revisions|categories",
                  "rvprop": "ids", "rvslots": "main", "cllimit": "max"}
        # revision content is limited to 1 page per request when combined?  No: <=50 is allowed; continuation handles the rest.
        params["rvprop"] = "ids|content"
        cont = {}
        while True:
            r = _api({**params, **cont})["response"]
            if "continue" not in r:
                break
            cont = r["continue"]
        print(f"batch {i // 50 + 1} done", flush=True)
    # big pages keep the infobox inside a "{{X Tabs Top}}" template: fetch those templates (wikitext only)
    pages, _ = load_cache()
    tpl = sorted({m.group(1).strip() for p in pages.values() if not HAS_BOX.search(p.get("wikitext", ""))
                  for m in re.finditer(r"\{\{\s*([^|{}\n]*Tabs Top)\s*[|}]", p.get("wikitext", ""))})
    print(f"{len(tpl)} infobox templates to fetch")
    for i in range(0, len(tpl), 50):
        _api({"action": "query", "format": "json", "formatversion": "2", "prop": "revisions", "rvprop": "ids|content",
              "rvslots": "main", "titles": "|".join("Template:" + t for t in tpl[i:i + 50])})


def load_cache() -> dict:
    """{title: {"title","revid","wikitext","categories":[...]}} merged over continuations; plus redirects map {from: to}."""
    pages, redirects = {}, {}
    for f in sorted(CACHE.glob("*.json")):
        if f.name == TARGETS.name:
            continue
        r = json.loads(f.read_text())["response"]
        q = r.get("query", {})
        for rd in q.get("redirects", []):
            redirects[rd["from"]] = rd["to"]
        for n in q.get("normalized", []):
            redirects.setdefault(n["from"], n["to"])
        for p in q.get("pages", []):
            if p.get("missing"):
                continue
            d = pages.setdefault(p["title"], {"title": p["title"], "pageid": p.get("pageid"), "categories": []})
            if p.get("revisions"):
                rv = p["revisions"][0]
                d["revid"] = rv["revid"]
                d["wikitext"] = rv["slots"]["main"]["content"]
            d["categories"] += [c["title"].removeprefix("Category:") for c in p.get("categories", [])]
    return pages, redirects


# ---------------------------------------------------------------- wikitext parsing
def _split_top(s: str, sep: str) -> list[str]:
    """Split on sep outside [[..]] and {{..}}."""
    out, cur, depth_b, depth_t, i = [], [], 0, 0, 0
    while i < len(s):
        two = s[i:i + 2]
        if two == "[[": depth_b += 1; cur.append(two); i += 2; continue
        if two == "]]": depth_b -= 1; cur.append(two); i += 2; continue
        if two == "{{": depth_t += 1; cur.append(two); i += 2; continue
        if two == "}}": depth_t -= 1; cur.append(two); i += 2; continue
        if s[i] == sep and depth_b <= 0 and depth_t <= 0:
            out.append("".join(cur)); cur = []
        else:
            cur.append(s[i])
        i += 1
    out.append("".join(cur))
    return out


def find_template(text: str, name_re: str):
    """(name, {param: raw value}) of the first top-level-or-nested template whose name matches name_re, else None."""
    for m in re.finditer(r"\{\{\s*(" + name_re + r")\s*(?=[|\n}])", text, re.I):
        i, depth = m.start(), 0
        for j in range(i, len(text) - 1):
            two = text[j:j + 2]
            if two == "{{": depth += 1
            elif two == "}}":
                depth -= 1
                if depth == 0:
                    body = text[i + 2:j]
                    parts = _split_top(body, "|")
                    params = {}
                    for part in parts[1:]:
                        if "=" in part:
                            k, v = part.split("=", 1)
                            params[k.strip().lower()] = v.strip()
                    return parts[0].strip(), params
        return None
    return None


def strip_templates(s: str) -> str:
    """Remove every {{...}} (nested ok): refs (Qref), {{B}}, {{Nihongo}} ... carry no value we use."""
    out, depth, i = [], 0, 0
    while i < len(s):
        if s[i:i + 2] == "{{": depth += 1; i += 2; continue
        if s[i:i + 2] == "}}" and depth: depth -= 1; i += 2; continue
        if not depth: out.append(s[i])
        i += 1
    return "".join(out)


def _clean(s: str) -> str:
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", s, flags=re.S | re.I)
    return strip_templates(s)


def links_of(s: str) -> list[str]:
    """Targets of [[Target|label]] / [[Target]] links, '#section' stripped, files/categories skipped."""
    out = []
    for m in re.finditer(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]", s):
        t = m.group(1).strip()
        if not re.match(r"(File|Image|Category|Media):", t, re.I):
            out.append(t.replace("_", " "))
    return out


def strip_markup(s: str) -> str:
    s = _clean(s)
    s = re.sub(r"\[\[([^\]|]*\|)?([^\]]*)\]\]", r"\2", s)
    s = re.sub(r"<br\s*/?>", "; ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"'{2,}", "", s).strip()


FORMER = re.compile(r"\(\s*(former|formerly|ex-?)\b[^)]*\)", re.I)


def parse_entries(raw: str) -> list[dict]:
    """Split an infobox list field (affiliation / occupation) on '<br>', newlines and top-level ';'.  Each entry:
    {"text": plain text without the marker, "link": first [[link]] target or None, "former": entry carries "(former)"/"(formerly)"}.
    The marker is only honoured inside the entry it follows, never carried to the next one."""
    raw = _clean(raw)
    out = []
    for chunk in re.split(r"<br\s*/?>|\n", raw):
        for part in _split_top(chunk, ";"):
            part = part.strip(" *,\t")
            if not part:
                continue
            former = bool(FORMER.search(part))
            part = FORMER.sub("", part)
            text = re.sub(r"\s+", " ", re.sub(r"\(([^)]*)\)", "", strip_markup(part))).strip(" ,;")
            ls = links_of(part)
            if text:
                out.append({"text": text, "link": ls[0] if ls else None, "former": former})
    return out


def parse_bounty(raw: str):
    """Highest number the field states (None when it states none, e.g. 'Unknown')."""
    nums = [int(x.replace(",", "")) for x in re.findall(r"\d[\d,]{3,}", _clean_keep_b(raw))]
    return max(nums) if nums else None


def _clean_keep_b(raw: str) -> str:
    return strip_templates(re.sub(r"<ref[^>]*?/>|<ref[^>]*>.*?</ref>", "", raw, flags=re.S | re.I))


# ---------------------------------------------------------------- category vocabulary (the wiki's own category names)
GENDER = {"Male Characters": "Male", "Female Characters": "Female"}
RACE = {"Humans": "Human", "Fish-Men": "Fish-Man", "Giants": "Giant", "Mink Tribe": "Mink", "Dwarves": "Dwarf", "Merfolk": "Merfolk",
        "Cyborgs": "Cyborg", "Human Hybrids": "Human hybrid", "Modified Humans": "Modified human", "Long Arm Tribe": "Long Arm",
        "Long Leg Tribe": "Long Leg", "Lunarians": "Lunarian", "Three-Eyed Tribe": "Three-Eye", "Snakeneck Tribe": "Snakeneck",
        "Oni": "Oni", "Skypieans": "Skypiean", "Birkans": "Birkan", "Zombies": "Zombie"}
TITLE = {"Four Emperors", "Seven Warlords of the Sea", "Worst Generation", "Super Rookies", "Pirate Admirals", "Tobiroppo",
         "Ten Titanic Captains", "Nine Red Scabbards", "Clan of D.", "Kings", "Princes", "Princesses", "Rulers", "Daimyo",
         "Marine Admirals", "Marine Vice Admirals", "Revolutionary Army Commanders", "Whitebeard Pirates Division Commanders",
         "Shinuchi", "Gorgon Sisters", "Deities"}
STYLE_ROLE = {"Swordsmen": "Swordsman", "Snipers": "Sniper", "Martial Artists": "Martial artist", "Archers": "Archer",
              "Axemen": "Axeman", "Polearm Wielders": "Polearm wielder", "Fighters Who Use Animals": "Fighter who uses animals",
              "Fighters Who Use Technology": "Fighter who uses technology", "Fighters Who Use Weapons": "Fighter who uses weapons",
              "Fish-Man Karate Users": "Fish-Man Karate user"}
NOT_WEAPON = re.compile(r"Haki|Devil Fruit|Six Powers|Voice of All|Mythical|Awakened|Ancient|Logia|Paramecia|Zoan", re.I)


def style_of(cat: str):
    if cat in STYLE_ROLE:
        return STYLE_ROLE[cat]
    if cat.endswith(" Users") and not NOT_WEAPON.search(cat):
        return cat[:-len("Users")] + "user"
    return None


def bounty_tier(n: int) -> str:
    return "1 billion or more" if n >= 10**9 else "100 million to under 1 billion" if n >= 10**8 else "under 100 million"


# ---------------------------------------------------------------- extract
def infobox(p: dict, pages: dict):
    """Char Box / Devil Fruit Box params; big pages keep it in the '{{X Tabs Top}}' template."""
    txt = p.get("wikitext", "")
    if not HAS_BOX.search(txt):
        m = re.search(r"\{\{\s*([^|{}\n]*Tabs Top)\s*[|}]", txt)
        txt = pages.get("Template:" + m.group(1).strip(), {}).get("wikitext", "") if m else ""
    return find_template(txt, r"char box|devil fruit box")


def extract_page(p: dict, pages: dict, category: str) -> dict:
    cats = p["categories"]
    out = {"page": p["title"], "revid": p.get("revid"), "categories": cats}
    box = infobox(p, pages)
    out["infobox"] = box[0] if box else None
    params = box[1] if box else {}
    if category == "Character":
        g = sorted({GENDER[c] for c in cats if c in GENDER})
        if g: out["gender"] = g
        r = sorted({RACE[c] for c in cats if c in RACE})
        if r: out["race"] = r
        st = sorted({style_of(c) for c in cats if style_of(c)})
        if st: out["fightingStyle"] = st
        ti = sorted(c for c in cats if c in TITLE)
        if ti: out["titles"] = ti
        for field in ("affiliation", "occupation"):
            if field in params:
                es = parse_entries(params[field])
                if es: out[field] = es
        if "bounty" in params:
            b = parse_bounty(params["bounty"])
            if b: out["bounty"] = b
    else:
        for k in ("type", "meaning"):
            if k in params: out["df_" + k] = strip_markup(params[k])
    return out


def extract():
    pages, red = load_cache()
    res = {}
    unmatched = []
    for t in json.loads(TARGETS.read_text()):
        n = _title(t); n = red.get(n, n); n = red.get(n, n)
        p = pages.get(n)
        if not p or "wikitext" not in p:
            unmatched.append(t["name"]); continue
        res[t["uri"]] = {"name": t["name"], "category": t["category"], **extract_page(p, pages, t["category"])}
    EXTRACTED.write_text(json.dumps({"unmatched": unmatched, "entities": res}, indent=1, ensure_ascii=False))
    print(f"{len(res)} extracted, {len(unmatched)} unmatched: {unmatched[:15]}")


# ---------------------------------------------------------------- emit
OPX_NS = "http://kalnassag.com/onepiece-ext#"


def _slug(s: str) -> str:
    return re.sub(r"[^0-9A-Za-z]+", "_", s).strip("_")


def _lit(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"@en'


def emit():
    from . import config
    from .ontology import load_sources, OP
    from rdflib import RDF, URIRef
    config.SKIP_PATCHES = set(config.SKIP_PATCHES) | {"wiki-attributes"}     # the graph WITHOUT this patch: what was already recorded
    base, ext = load_sources()
    g = base + ext
    has_race = {str(x) for x in g.subjects(OP.race, None)}                  # op:race is functional: an already recorded race wins (Sanji, Jinbe)
    data = json.loads(EXTRACTED.read_text())["entities"]
    nodes: dict[str, tuple[str, str]] = {}          # curie -> (class curie, label)
    facts: dict[str, dict[str, list[str]]] = {}     # entity curie -> prop -> [value curies]
    skipped = {"gender_multi": 0, "race_multi": 0}

    def add(ent, prop, val):
        v = facts.setdefault(ent, {}).setdefault(prop, [])
        if val not in v: v.append(val)

    def node(cls, label, existing=None):
        if existing is not None: return existing
        c = f"opx:{cls}_{_slug(label)}"
        nodes[c] = (f"opx:{cls}", label)
        return c

    def reuse(label, cls):
        """existing op: node of the right type with exactly this local name, else None."""
        from rdflib import URIRef
        iri = OPN + label.replace(" ", "_")
        if not re.fullmatch(r"[^\s<>\"{}|\\^`]+", iri):
            return None
        return f"<{iri}>" if (URIRef(iri), RDF.type, OP[cls]) in g else None

    for uri, e in sorted(data.items()):
        if e["category"] != "Character": continue
        ent = f"<{uri}>"
        if "gender" in e:
            if len(e["gender"]) == 1: add(ent, "opx:gender", node("Gender", e["gender"][0]))
            else: skipped["gender_multi"] += 1
        if "race" in e and uri not in has_race:
            if len(e["race"]) == 1:
                r = e["race"][0]
                add(ent, "op:race", {"Human": "op:Human", "Giant": "op:Giant", "Fish-Man": "op:Fishman"}.get(r) or node("Race", r))
            else: skipped["race_multi"] += 1
        for s in e.get("fightingStyle", []): add(ent, "opx:fightingStyle", node("FightingStyle", s))
        for t in e.get("titles", []): add(ent, "opx:hasTitle", node("Title", t))
        for field, cls, nm in (("affiliation", "Affiliation", "Affiliation"), ("occupation", "Occupation", "Occupation")):
            for en in e.get(field, []):
                label = en["link"] if (field == "affiliation" and en["link"]) else en["text"]
                ex = reuse(label, cls)
                if ex is None and (URIRef(OPN + label.replace(" ", "_")), None, None) in g:
                    continue   # the name is a node of another kind (a place, a person): never retype it
                v = node(nm, label, ex)
                add(ent, ("opx:formerOccupation" if en["former"] else "opx:currentOccupation") if field == "occupation"
                    else ("opx:formerAffiliation" if en["former"] else "opx:currentAffiliation"), v)
        if "bounty" in e: add(ent, "opx:bountyTier", node("BountyTier", bounty_tier(e["bounty"])))
    # one record per source page
    src = {}
    for uri, e in sorted(data.items()):
        if f"<{uri}>" in facts:
            src[f"<{uri}>"] = e
    L = ["# Attributes extracted from the One Piece Fandom wiki (https://onepiece.fandom.com, text CC-BY-SA 3.0) by app.wiki_pipeline.",
         "# Generated: python -m app.wiki_pipeline emit.  Only values a page states (infobox / category membership) are asserted; absence stays unknown.",
         "# current/former affiliation and occupation are ADDITIVE to the timeless op:affiliatesWith / op:occupation edges, which are untouched.",
         "@prefix op: <http://kalnassag.com/onepiece#> .", "@prefix opx: <http://kalnassag.com/onepiece-ext#> .",
         "@prefix owl: <http://www.w3.org/2002/07/owl#> .", "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
         "@prefix dct: <http://purl.org/dc/terms/> .", "", "# ---- schema"]
    props = [("gender", "Gender", "gender", True), ("fightingStyle", "FightingStyle", "fighting style / weapon class", False),
             ("hasTitle", "Title", "title or group (Emperor, Warlord, Worst Generation ...)", False),
             ("currentAffiliation", "Affiliation", "current affiliation", False), ("formerAffiliation", "Affiliation", "former affiliation", False),
             ("currentOccupation", "Occupation", "current occupation", False), ("formerOccupation", "Occupation", "former occupation", False),
             ("bountyTier", "BountyTier", "highest bounty", True)]
    for cls, lab in (("Gender", "gender"), ("FightingStyle", "fighting style"), ("Title", "title"), ("BountyTier", "bounty tier")):
        L.append(f'opx:{cls} a owl:Class ; rdfs:label "{lab}"@en .')
    L.append("opx:Gender a opx:ClosedEnumeration .   # Male and Female are different values (owl:differentFrom pairs are generated at load)")
    L.append('opx:WikiPage a owl:Class ; rdfs:label "wiki source page"@en .')
    for p, rng, lab, fn in props:
        L.append(f'opx:{p} a owl:ObjectProperty{" , owl:FunctionalProperty" if fn else ""} ; rdfs:domain op:Character ; rdfs:range opx:{rng} ; rdfs:label "{lab}"@en .')
    L.append('opx:wikiSource a owl:ObjectProperty ; rdfs:range opx:WikiPage ; rdfs:comment "Page the wiki-derived facts of this entity were read from."@en .')
    L.append("opx:revisionId a owl:DatatypeProperty .")
    L += ["", "# ---- value nodes"]
    for c, (cls, label) in sorted(nodes.items()):
        t = {"Race": "op:Race", "Affiliation": "op:Affiliation", "Occupation": "op:Occupation"}.get(cls.split(":")[1], cls)
        L.append(f"{c} a {t} ; rdfs:label {_lit(label)} .")
    L += ["", "# ---- facts"]
    for ent in sorted(facts):
        L.append(ent + " " + " ;\n    ".join(f"{p} " + ", ".join(vs) for p, vs in sorted(facts[ent].items())) + " .")
    L += ["", "# ---- provenance: one record per source page"]
    for ent, e in sorted(src.items()):
        page = "https://onepiece.fandom.com/wiki/" + urllib.parse.quote(e["page"].replace(" ", "_"), safe="_(),.'-:!")
        L.append(f'{ent} opx:wikiSource <{page}> .')
        L.append(f'<{page}> a opx:WikiPage ; rdfs:label {_lit(e["page"])} ; opx:revisionId {e["revid"]} ; dct:license <https://creativecommons.org/licenses/by-sa/3.0/> .')
    PATCH.write_text("\n".join(L) + "\n")
    cov = {p: (sum(1 for f in facts.values() if p in f), len({v for f in facts.values() for v in f.get(p, [])})) for p in
           sorted({p for f in facts.values() for p in f})}
    print(json.dumps({"entities": len(facts), "skipped": skipped, "coverage(entities, distinct values)": cov}, indent=1))


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else ""
    if stage == "fetch":
        fetch(sys.argv[2] if len(sys.argv) > 2 else "http://localhost:3031/ds/sparql")
    elif stage == "extract":
        extract()
    elif stage == "emit":
        emit()
    else:
        sys.exit(__doc__)
