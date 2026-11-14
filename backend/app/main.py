import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config, graph, llm, service
from .schemas import AnswerRequest, GameView, GuessFeedback, RevealRequest, StartRequest

app = FastAPI(title="Grand Line Akinator", version="1.0",
              description="Ontology-driven One Piece guessing game: Apache Jena Fuseki knowledge graph (SPARQL) + information-gain question selection.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _session(sid: str) -> service.Session:
    s = service.SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "unknown session")
    return s


@app.get("/api/health")
def health():
    try:
        graph.ping()
        n = graph.run("SELECT (COUNT(?e) AS ?c) WHERE { ?e g:category ?cat }")[0]["c"]
    except Exception as e:
        raise HTTPException(503, f"fuseki unavailable: {e}")
    if n == 0:
        raise HTTPException(503, "graph empty: run the ingestion")
    return {"status": "ok", "entities": n, "together_configured": llm.available(), "kb_loaded": service.KB_INSTANCE is not None}


@app.on_event("startup")
def warm():
    try:
        service.get_kb()                     # build the question bank once; failures surface on /api/health
    except Exception as e:                    # pragma: no cover
        print("KB warm-up failed:", e)


@app.post("/api/game/start", response_model=GameView)
def start(req: StartRequest, dev: bool = False):
    sess = service.start(req.mode, "adaptive" if req.policy == "adaptive" else "info_gain", seed=req.seed,
                         exploration=req.exploration if req.policy == "adaptive" else "off")
    return service.view(sess, dev)


@app.get("/api/game/{session_id}", response_model=GameView)
def get_game(session_id: str, dev: bool = False):
    return service.view(_session(session_id), dev)


@app.post("/api/game/{session_id}/answer", response_model=GameView)
def answer(session_id: str, req: AnswerRequest, dev: bool = False):
    s = _session(session_id)
    try:
        service.answer(s, req.answer, req.question_id)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return service.view(s, dev)


@app.post("/api/game/{session_id}/guess-feedback", response_model=GameView)
def guess_feedback(session_id: str, req: GuessFeedback, dev: bool = False):
    s = _session(session_id)
    try:
        service.feedback(s, req.correct)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return service.view(s, dev)


@app.post("/api/game/{session_id}/reveal")
def reveal(session_id: str, req: RevealRequest):
    try:
        return service.reveal(_session(session_id), req.name)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.post("/api/game/{session_id}/undo", response_model=GameView)
def undo(session_id: str, dev: bool = False):
    s = _session(session_id)
    try:
        service.undo(s)
    except ValueError as e:
        raise HTTPException(409, str(e))
    return service.view(s, dev)


@app.get("/api/entities")
def entities(category: str | None = Query(None, pattern="^(Character|DevilFruit|Ship)$"), q: str | None = None,
             limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
    flt = "FILTER(CONTAINS(LCASE(?name), LCASE($q)))" if q is not None else ""
    rows = graph.run("SELECT ?uri ?id ?name ?category WHERE { VALUES ?category { $cats } ?uri g:category ?category . ?uri g:name ?name . ?uri g:local ?id . "
                     f"{flt} }} ORDER BY ?name ?uri OFFSET {int(offset)} LIMIT {int(limit)}", cats=[category] if category else config.CATEGORIES, q=q)
    return {"count": len(rows), "items": rows}


@app.get("/api/entities/{entity_id:path}")
def entity(entity_id: str):
    n = graph.run("SELECT ?uri ?name ?category WHERE { ?uri g:category ?category . ?uri g:name ?name . ?uri g:local ?local . FILTER(?local = $i || STR(?uri) = $i) } LIMIT 1", i=entity_id)
    if not n:
        raise HTTPException(404, "unknown entity")
    n = n[0]
    u = graph.iri(n["uri"])
    n["explicit_types"] = [r["t"] for r in graph.run("SELECT ?t WHERE { $u g:explicitType ?t } ORDER BY ?t", u=u)]
    n["inferred_types"] = [r["t"] for r in graph.run("SELECT ?t WHERE { $u g:inferredType ?t } ORDER BY ?t", u=u)]
    props: dict = {}
    for r in graph.run("SELECT ?k ?v WHERE { $u ?k ?v . FILTER(STRSTARTS(STR(?k), $ns)) } ORDER BY ?k ?v", u=u, ns=graph.G):
        props.setdefault(r["k"][len(graph.G):], []).append(r["v"])
    for k in ("explicitType", "inferredType", "label", "name", "category", "local", "haki_known"):
        props.pop(k, None)
    n["props"] = {k: v[0] if len(v) == 1 else sorted(v, key=str) for k, v in props.items()}
    prov = 'BIND(STRAFTER(STR(?g), "urn:akinator:") AS ?provenance)'
    n["relations"] = graph.run("SELECT DISTINCT ?rel ?provenance ?target ?target_uri WHERE { GRAPH ?g { $u ?p ?target_uri } ?p g:relType ?rel . ?target_uri g:name ?target . "
                               f"{prov} }} ORDER BY ?rel ?target_uri LIMIT 300", u=u)
    n["incoming"] = graph.run("SELECT DISTINCT ?rel ?provenance ?source ?source_uri WHERE { GRAPH ?g { ?source_uri ?p $u } ?p g:relType ?rel . ?source_uri g:name ?source . "
                              f"{prov} }} ORDER BY ?rel ?source_uri LIMIT 100", u=u)
    return n


@app.get("/api/ontology/stats")
def stats():
    rep = graph.run("SELECT ?r WHERE { <urn:akinator:run:latest> g:report ?r }")
    kb = service.get_kb()
    return {
        "ingestion": json.loads(rep[0]["r"]) if rep else None,
        "labels": graph.run("SELECT ?label (COUNT(*) AS ?n) WHERE { ?x g:label ?label } GROUP BY ?label ORDER BY DESC(?n) ?label LIMIT 40"),
        "relationships": graph.run("SELECT ?rel ?provenance (COUNT(*) AS ?n) WHERE { GRAPH ?g { ?a ?p ?b } ?p g:relType ?rel . "
                                   'BIND(STRAFTER(STR(?g), "urn:akinator:") AS ?provenance) } GROUP BY ?rel ?provenance ORDER BY DESC(?n) ?rel ?provenance'),
        "question_bank": {"rule_questions": len(kb.rule_questions), "total": len(kb.bank.questions), "build_seconds": kb.build_seconds},
        "reasoning_note": "OWL 2 RL subset via owlrl; not a full OWL 2 DL reasoner.",
    }


NOISY_RELS = ["MANGA_DEBUT", "ANIME_DEBUT", "ENGLISH_VOICE_ACTOR", "JAPANESE_VOICE_ACTOR", "LIVE_ACTION_PORTRAYED_BY",
              "DEVIL_FRUIT_USE_DEBUT_MANGA", "DEVIL_FRUIT_USE_DEBUT_ANIME", "DEVIL_FRUIT_DEBUT_MANGA", "DEVIL_FRUIT_DEBUT_ANIME"]


@app.get("/api/graph/neighborhood")
def neighborhood(id: str, limit: int = Query(40, ge=1, le=120), only_inferred: bool = False):
    """1-hop neighbourhood of any node, for the graph explorer. Inferred / curated edges are listed first."""
    center = graph.run("SELECT ?uri WHERE { ?uri g:name ?x . ?uri g:local ?l . FILTER(?l = $i || STR(?uri) = $i) } LIMIT 1", i=id)
    if not center:
        raise HTTPException(404, "unknown node")
    uri = center[0]["uri"]
    u = graph.iri(uri)
    inf = 'FILTER(?provenance = "inferred")' if only_inferred else ""
    rows = graph.run(
        "SELECT DISTINCT ?s ?t ?rel ?provenance ?other WHERE { "
        "{ GRAPH ?g { $u ?p ?other } BIND($u AS ?s) BIND(?other AS ?t) } UNION { GRAPH ?g { ?other ?p $u } BIND(?other AS ?s) BIND($u AS ?t) } "
        "?p g:relType ?rel . ?other g:name ?oname . MINUS { VALUES ?rel { $noisy } } "
        f'BIND(STRAFTER(STR(?g), "urn:akinator:") AS ?provenance) {inf} OPTIONAL {{ ?other g:popularity ?pop }} }} '
        'ORDER BY (IF(?provenance = "inferred", 0, IF(?provenance = "curated", 1, 2))) DESC(COALESCE(?pop, 0)) ?other ?rel '
        f"LIMIT {int(limit)}", u=u, noisy=NOISY_RELS)
    uris = [graph.iri(x) for x in {uri, *[r["other"] for r in rows]}]
    nodes = graph.run("SELECT ?id ?name ?category ?popularity WHERE { VALUES ?id { $us } ?id g:name ?name . OPTIONAL { ?id g:category ?category } "
                      "OPTIONAL { ?id g:popularity ?popularity } } ORDER BY ?id", us=uris)
    for kind, key in (("label", "labels"), ("inferredType", "inferred_types")):
        by: dict[str, list] = {}
        for r in graph.run(f"SELECT ?id ?v WHERE {{ VALUES ?id {{ $us }} ?id g:{kind} ?v }} ORDER BY ?v", us=uris):
            by.setdefault(r["id"], []).append(r["v"])
        for nd in nodes:
            nd[key] = by.get(nd["id"], [])
    total = graph.run("SELECT (COUNT(*) AS ?c) WHERE { { $u ?p ?o } UNION { ?o ?p $u } ?p g:relType ?rel . MINUS { VALUES ?rel { $noisy } } }", u=u, noisy=NOISY_RELS)[0]["c"]
    return {"center": uri, "nodes": nodes, "edges": [{"source": r["s"], "target": r["t"], "rel": r["rel"], "provenance": r["provenance"]} for r in rows],
            "total_edges": total}
