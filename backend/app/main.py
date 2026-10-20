import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from . import config, graph, llm, service
from .schemas import AnswerRequest, GameView, GuessFeedback, StartRequest

app = FastAPI(title="Grand Line Akinator", version="1.0",
              description="Ontology-driven One Piece guessing game: Neo4j knowledge graph + information-gain question selection.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def _session(sid: str) -> service.Session:
    s = service.SESSIONS.get(sid)
    if not s:
        raise HTTPException(404, "unknown session")
    return s


@app.get("/api/health")
def health():
    try:
        graph.driver().verify_connectivity()
        n = graph.run("MATCH (e:Resource) WHERE e.category IS NOT NULL RETURN count(e) AS c")[0]["c"]
    except Exception as e:
        raise HTTPException(503, f"neo4j unavailable: {e}")
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
    rows = graph.run(
        "MATCH (e:Resource) WHERE e.category IN $cats AND ($q IS NULL OR toLower(e.name) CONTAINS toLower($q)) "
        "RETURN e.uri AS uri, e.local AS id, e.name AS name, e.category AS category ORDER BY e.name SKIP $o LIMIT $l",
        cats=[category] if category else config.CATEGORIES, q=q, o=offset, l=limit)
    return {"count": len(rows), "items": rows}


@app.get("/api/entities/{entity_id:path}")
def entity(entity_id: str):
    n = graph.run("MATCH (e:Resource) WHERE e.category IS NOT NULL AND (e.local = $i OR e.uri = $i) "
                  "RETURN e.uri AS uri, e.name AS name, e.category AS category, e.explicit_types AS explicit_types, "
                  "e.inferred_types AS inferred_types, properties(e) AS props", i=entity_id)
    if not n:
        raise HTTPException(404, "unknown entity")
    n = n[0]
    for k in ("explicit_types", "inferred_types", "name", "category", "uri", "local", "haki_known"):
        n["props"].pop(k, None)
    n["relations"] = graph.run("MATCH (e:Resource {uri:$u})-[r]->(t:Resource) RETURN type(r) AS rel, r.provenance AS provenance, t.name AS target, t.uri AS target_uri ORDER BY rel LIMIT 300", u=n["uri"])
    n["incoming"] = graph.run("MATCH (e:Resource {uri:$u})<-[r]-(t:Resource) RETURN type(r) AS rel, r.provenance AS provenance, t.name AS source, t.uri AS source_uri ORDER BY rel LIMIT 100", u=n["uri"])
    return n


@app.get("/api/ontology/stats")
def stats():
    rep = graph.run("MATCH (r:IngestionRun {id:'latest'}) RETURN r.report AS r")
    kb = service.get_kb()
    return {
        "ingestion": json.loads(rep[0]["r"]) if rep else None,
        "labels": graph.run("MATCH (n:Resource) UNWIND labels(n) AS l WITH l, count(*) AS n WHERE l <> 'Resource' RETURN l AS label, n ORDER BY n DESC LIMIT 40"),
        "relationships": graph.run("MATCH ()-[r]->() RETURN type(r) AS rel, r.provenance AS provenance, count(*) AS n ORDER BY n DESC"),
        "question_bank": {"rule_questions": len(kb.rule_questions), "total": len(kb.bank.questions), "build_seconds": kb.build_seconds},
        "reasoning_note": "OWL 2 RL subset via owlrl; not a full OWL 2 DL reasoner.",
    }


NOISY_RELS = ["MANGA_DEBUT", "ANIME_DEBUT", "ENGLISH_VOICE_ACTOR", "JAPANESE_VOICE_ACTOR", "LIVE_ACTION_PORTRAYED_BY",
              "DEVIL_FRUIT_USE_DEBUT_MANGA", "DEVIL_FRUIT_USE_DEBUT_ANIME", "DEVIL_FRUIT_DEBUT_MANGA", "DEVIL_FRUIT_DEBUT_ANIME"]


@app.get("/api/graph/neighborhood")
def neighborhood(id: str, limit: int = Query(40, ge=1, le=120), only_inferred: bool = False):
    """1-hop neighbourhood of any node, for the graph explorer. Inferred / curated edges are listed first."""
    center = graph.run("MATCH (n:Resource) WHERE n.uri = $i OR n.local = $i RETURN n.uri AS uri LIMIT 1", i=id)
    if not center:
        raise HTTPException(404, "unknown node")
    uri = center[0]["uri"]
    rows = graph.run(
        "MATCH (a:Resource {uri:$u})-[r]-(b:Resource) WHERE NOT type(r) IN $noisy AND ($inf = false OR r.provenance = 'inferred') "
        "RETURN startNode(r).uri AS s, endNode(r).uri AS t, type(r) AS rel, r.provenance AS provenance, b.uri AS other "
        "ORDER BY CASE r.provenance WHEN 'inferred' THEN 0 WHEN 'curated' THEN 1 ELSE 2 END, COALESCE(b.popularity, 0) DESC LIMIT $l",
        u=uri, noisy=NOISY_RELS, inf=only_inferred, l=limit)
    uris = list({uri, *[r["other"] for r in rows]})
    nodes = graph.run("MATCH (n:Resource) WHERE n.uri IN $us RETURN n.uri AS id, n.name AS name, n.category AS category, "
                      "[l IN labels(n) WHERE l <> 'Resource'] AS labels, n.inferred_types AS inferred_types, n.popularity AS popularity", us=uris)
    total = graph.run("MATCH (a:Resource {uri:$u})-[r]-() WHERE NOT type(r) IN $noisy RETURN count(r) AS c", u=uri, noisy=NOISY_RELS)[0]["c"]
    return {"center": uri, "nodes": nodes, "edges": [{"source": r["s"], "target": r["t"], "rel": r["rel"], "provenance": r["provenance"]} for r in rows],
            "total_edges": total}
