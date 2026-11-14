"""Application service: knowledge base cache, game sessions, AI-mode question selection, explanations."""
import random
import re
import threading
import time
import uuid
from collections import OrderedDict

import numpy as np

from . import config, graph, llm, policy, questions as Q
from .engine import ANSWERS, Bank, GameState, expected_info_gain, likelihood_tensor

SEEN = {"yes": "Yes", "probably": "Probably", "dont_know": "Don't know", "probably_not": "Probably not", "no": "No"}
_lock = threading.Lock()


class KB:
    def __init__(self):
        rows = graph.run("SELECT ?uri ?name ?category (COALESCE(?pop, 0) AS ?popularity) WHERE { VALUES ?category { $c } ?uri g:category ?category . ?uri g:name ?name . "
                         "OPTIONAL { ?uri g:popularity ?pop } } ORDER BY ?uri", c=config.CATEGORIES)
        if not rows:
            raise RuntimeError("graph is empty - run `python -m app.ingestion`")
        self.entities = rows
        self.uris = [r["uri"] for r in rows]
        self.idx = {u: i for i, u in enumerate(self.uris)}
        self.cats = Q.category_uris()
        self.rels, self.labels = Q.allowed_identifiers()
        self.schema = Q.schema_summary()
        self.bank = Bank(self.uris)
        if config.PRIOR == "popularity":
            self.bank.prior = (1.0 + np.array([r["popularity"] for r in rows], dtype=float)) ** config.POPULARITY_ALPHA
        t0 = time.time()
        n_by_cat = {c: len(v) for c, v in self.cats.items()}
        self.rule_questions = Q.generate_rule_questions(n_by_cat)
        seen_rows: dict[bytes, str] = {}
        self.duplicates_dropped = 0
        # when two questions have identical answers keep the more natural one: plain category, then class / conjunction wording, then raw relation wording
        for q in sorted(self.rule_questions, key=lambda q: -1 if not q.spec.paths[0].steps and q.spec.paths[0].cond.kind == "exists" else 0 if q.spec.mode == "all" or q.spec.paths[0].cond.kind == "label" else 1):
            row = self.truth_row(q.spec)
            # two questions with identical answers for every entity are the same question in different words
            if row.tobytes() in seen_rows:
                self.duplicates_dropped += 1
                continue
            seen_rows[row.tobytes()] = q.id
            self.bank.add(q, row, self.na_row(q.spec))
        self.rule_questions = [q for q in self.rule_questions if q.id in self.bank.index]
        self.bank.categories = np.array([e["category"] for e in self.entities])
        self.bank.imp = self.implications()
        self.build_seconds = round(time.time() - t0, 1)

    def implications(self):
        """What each answer implies about the other questions, derived from the ontology (implications.py)."""
        from rdflib import OWL, RDF, RDFS, URIRef
        from .implications import derive
        tb = graph.graph_of("tbox")
        rel_preds: dict[str, set] = {}
        for r in graph.run("SELECT DISTINCT ?p ?rel WHERE { ?p g:relType ?rel }"):
            rel_preds.setdefault(r["rel"], set()).add(URIRef(r["p"]))
        classes = {}
        for c in sorted(set(tb.subjects(RDF.type, OWL.Class)) | set(tb.subjects(RDFS.subClassOf, None)) | set(tb.objects(None, RDF.type))):
            if isinstance(c, URIRef):
                classes.setdefault(graph.label_name(str(c)), c)
        return derive(self.bank.questions, tb, rel_preds, classes)

    def truth_row(self, spec: Q.QuerySpec) -> np.ndarray:
        t = Q.evaluate(spec, self.uris, self.cats)
        return np.array([t[u] for u in self.uris], dtype=np.int8)

    def na_row(self, spec: Q.QuerySpec) -> np.ndarray:
        """Entities of a category the question is not about (a Devil Fruit for an occupation question)."""
        starts = {p.start for p in spec.paths}
        return np.array([e["category"] not in starts for e in self.entities])

    def admit_llm_question(self, q: Q.Question, state: GameState, min_ig: float) -> tuple[int | None, str | None]:
        """Validate an LLM proposal against the live schema and the game: -> (bank index, None) or (None, reason).
        Rejects unsupported (outside the schema), unanswerable, ambiguous, redundant (same answers as an asked / banked question) and low-value questions."""
        if q.text.count("?") != 1 or re.search(r"\b(or|and/or)\b", q.text, re.I) and q.spec.mode == "any" and len(q.spec.paths) == 1:
            return None, "ambiguous"
        err = Q.validate_spec(q.spec, self.rels, self.labels)
        if err:
            return None, "unsupported"
        with _lock:
            known = self.bank.index.get(q.id)
        if known is not None:
            return known, None
        row = self.truth_row(q.spec)
        if (row == 1).sum() == 0 or ((row == 0).sum() == 0 and (row == -1).sum() == 0):
            return None, "unanswerable"
        phi = max([float(policy.weighted_phi(row[None, :], self.bank.truth[i], state.prior0)[0]) for i in range(len(self.bank.questions))] or [0.0])
        if phi >= config.EQUIV_PHI:
            return None, "redundant"
        L = likelihood_tensor(np.array([Q.unknown_prior_true(q)]), false_reliability=np.array([Q.false_reliability(q)]))
        na = self.na_row(q.spec)
        ig = float(expected_info_gain(state.w, row[None, :], L, na=na[None, :])[1][0])
        if ig < min_ig:
            return None, "low-value"
        with _lock:
            return self.bank.add(q, row, na), None

    def entity_facts(self, uri: str, limit=10) -> list[dict]:
        return graph.run("SELECT ?rel ?name ?uri ?provenance WHERE { GRAPH ?g { $u ?p ?uri } ?p g:relType ?rel . ?uri g:name ?name . "
                         'MINUS { VALUES ?rel { "MANGA_DEBUT" "ANIME_DEBUT" "ENGLISH_VOICE_ACTOR" "JAPANESE_VOICE_ACTOR" "LIVE_ACTION_PORTRAYED_BY" } } '
                         f'BIND(STRAFTER(STR(?g), "urn:akinator:") AS ?provenance) }} ORDER BY ?rel ?uri LIMIT {int(limit)}', u=graph.iri(uri))


EXPLORATION = {"off": 0.0, "low": 0.03, "medium": None, "high": 0.15}      # None -> config.TEMPERATURE


class Session:
    def __init__(self, kb: KB, mode: str, seed: int | None = None, exploration: str = "medium"):
        self.id = uuid.uuid4().hex[:12]
        self.kb, self.mode = kb, mode
        self.seed = seed if seed is not None else random.randrange(2**31)
        self.rng = random.Random(self.seed)                       # one reproducible stream per session
        self.temperature = EXPLORATION[exploration] if EXPLORATION[exploration] is not None else config.TEMPERATURE
        self.state = GameState(kb.bank, rng=self.rng)
        self.phase, self.phase_metrics, self.reaction = "discovery", {}, None
        self.status = "asking"
        self.current: dict | None = None
        self.llm = llm_off(mode)
        self.created = time.time()
        self.prediction_idx: int | None = None
        self.strategy = "adaptive"           # "info_gain" = deterministic baseline, "random" = evaluation baseline
        self.select_ms: list[int] = []
        self.llm_failures, self.llm_pause = 0, 0
        self.relaxed = False
        self.llm_totals = {"calls": 0, "cache_hits": 0, "failures": 0, "proposed": 0, "accepted": 0, "rejected": {}}   # cumulative over the game


def llm_off(mode):
    from .schemas import LLMInfo
    return LLMInfo(used=False) if mode == "ai" else None


SESSIONS: dict[str, Session] = {}
KB_INSTANCE: KB | None = None


def get_kb() -> KB:
    global KB_INSTANCE
    if KB_INSTANCE is None:
        graph.wait_ready(60)
        KB_INSTANCE = KB()
    return KB_INSTANCE


# ------------------------------------------------------------------ question selection
def _view(kb: KB, r: dict, text: str | None = None, original: str | None = None, dev: bool = False):
    from .schemas import QuestionView, QueryView
    q = kb.bank.questions[r["index"]]
    if not dev:                       # normal players never see graph queries, scores or probabilities
        return QuestionView(id=q.id, text=text or q.text, source=q.source if not original else "rule+llm", topic=kb.bank.topics[r["index"]])
    qv = []
    for p in q.spec.paths:
        tq, kq, params = Q.compile_path(p)
        qv.append(QueryView(true_query=tq, known_query=kq, params={k: v for k, v in params.items() if v is not None}))
    return QuestionView(id=q.id, text=text or q.text, source=q.source if not original else "rule+llm", original_text=original, topic=kb.bank.topics[r["index"]],
                        queries=qv, info_gain=r["info_gain"], score=r["score"], coverage=r["coverage"],
                        p_yes=r["p_yes"], p_no=r["p_no"], p_unknown=r["p_unknown"])


def _rank(sess: Session, allow_llm: bool, relax: bool = False) -> list[dict]:
    ranked = sess.state.rank(family_max=10 ** 6 if relax else None)
    bank = sess.kb.bank.questions
    # legacy only: one "don't know" used to remove EVERY question of the same family (e.g. all occupation questions)
    dk = set() if (relax or config.ANSWER_MODEL != "legacy") else {Q.family(bank[a["index"]]) for a in sess.state.asked if a["answer"] == "dont_know"}
    return [r for r in ranked if (allow_llm or bank[r["index"]].source != "llm") and Q.family(bank[r["index"]]) not in dk]


def select_question(sess: Session):
    t_start = time.time()
    try:
        return _select_question(sess)
    finally:
        sess.select_ms.append(int((time.time() - t_start) * 1000))


# LLM caches: wording per question id, and whole planner replies per (phase, offered questions) -> repeated game states cost no API call
_PARA_CACHE: "OrderedDict[str, str]" = OrderedDict()
_REPLY_CACHE: "OrderedDict[tuple, llm.LLMReply]" = OrderedDict()


def _cache_put(cache, key, value, limit=2000):
    cache[key] = value
    while len(cache) > limit:
        cache.popitem(last=False)


def _leaks(text: str, names: list[str]) -> bool:
    low = text.lower()
    return any(len(n) > 3 and n.lower() in low for n in names)


def _ai_plan(sess: Session, phase: str, offered_idx: list[int]) -> dict[str, str]:
    """One planner call (or cache hit). Mutates sess.llm; returns {question id: natural paraphrase}. The LLM only words / proposes - the
    graph-grounded engine still decides: every proposal is validated, evaluated against the graph and has to win on the policy score."""
    kb, st, info = sess.kb, sess.state, sess.llm
    paraphrase = {}
    if not llm.available():
        info.fallback_reason = "TOGETHER_API_KEY not set"
        return paraphrase
    if sess.llm_pause > 0:                                    # circuit breaker: the game must never wait on a sick network
        sess.llm_pause -= 1
        info.fallback_reason = "planner paused after repeated failures"
        return paraphrase
    t0 = time.time()
    try:
        offered = [kb.bank.questions[i] for i in offered_idx]
        key = (phase, tuple(sorted(q.id for q in offered)))
        reply = _REPLY_CACHE.get(key)
        info.cached = reply is not None
        top = st.top(20)
        names = [kb.entities[i]["name"] for i, _ in top]
        if reply is None:
            cands = [{"name": kb.entities[i]["name"], "category": kb.entities[i]["category"], "probability": round(p, 4), "facts": [
                {"rel": f["rel"], "target": f["name"], "uri": f["uri"]} for f in kb.entity_facts(kb.entities[i]["uri"])]} for i, p in top[:8]]
            recent = [kb.bank.topics[a["index"]] for a in st.asked[-6:]]
            last = ({"question": st.asked[-1].get("text") or kb.bank.questions[st.asked[-1]["index"]].text, "answer": SEEN[st.asked[-1]["answer"]]} if st.asked else None)
            reply = llm.ask(kb.schema, cands, [kb.bank.questions[a["index"]].text for a in st.asked], offered, phase=phase, recent_topics=recent, last_answer=last)
            _cache_put(_REPLY_CACHE, key, reply, 512)
        info.used = True
        sess.llm_failures = 0
        if reply.dropped:
            info.rejected["malformed"] = info.rejected.get("malformed", 0) + reply.dropped
        info.proposed = len(reply.new_questions)
        offered_ids = {q.id for q in offered}
        for pp in reply.paraphrases:
            if pp.id in offered_ids and not _leaks(pp.text, names):
                try:
                    paraphrase[pp.id] = _PARA_CACHE.get(pp.id) or Q.Question(id=pp.id, text=pp.text, spec=kb.bank.questions[kb.bank.index[pp.id]].spec).text
                    _cache_put(_PARA_CACHE, pp.id, paraphrase[pp.id])
                except Exception:
                    info.rejected["bad-wording"] = info.rejected.get("bad-wording", 0) + 1
        if reply.reaction and not info.cached and len(reply.reaction) <= 90 and not _leaks(reply.reaction, names):
            sess.reaction = reply.reaction.strip()
        min_ig = 0.5 * float(np.median([r["info_gain"] for r in _rank(sess, allow_llm=False)[:8]] or [0.0]))
        for nq in reply.new_questions:
            try:
                q = llm.to_question(nq)
            except Exception:
                info.rejected["unsupported"] = info.rejected.get("unsupported", 0) + 1
                continue
            if q.id in st.asked_ids:
                info.rejected["redundant"] = info.rejected.get("redundant", 0) + 1
                continue
            if _leaks(q.text, names):
                info.rejected["leaks-candidate"] = info.rejected.get("leaks-candidate", 0) + 1
                continue
            idx, why = kb.admit_llm_question(q, st, min_ig)
            if idx is None:
                info.rejected[why] = info.rejected.get(why, 0) + 1
            else:
                info.accepted += 1
    except Exception as e:                                          # network, auth, bad JSON ... -> rule-based fallback
        info.used = False
        info.fallback_reason = f"{type(e).__name__}: {str(e)[:160]}"
        sess.llm_failures += 1
        if sess.llm_failures >= 2:
            sess.llm_pause, sess.llm_failures = 3, 0
    info.latency_ms = int((time.time() - t0) * 1000)
    tot = sess.llm_totals
    tot["calls"] += 1
    tot["cache_hits"] += int(info.cached)
    tot["failures"] += int(not info.used)
    tot["proposed"] += info.proposed
    tot["accepted"] += info.accepted
    for k, v in info.rejected.items():
        tot["rejected"][k] = tot["rejected"].get(k, 0) + v
    return paraphrase


def _select_question(sess: Session):
    kb, st = sess.kb, sess.state
    ranked = _rank(sess, allow_llm=False)
    sess.llm = llm_off(sess.mode)
    paraphrase: dict[str, str] = {}
    adaptive = sess.strategy == "adaptive"
    phase, metrics = policy.phase_of(st)
    if sess.mode == "ai":
        pre = policy.score_questions(st, ranked, phase) if adaptive else []
        offered_idx = [x.index for x in pre[:4]] if pre else [r["index"] for r in ranked[:4]]
        paraphrase = _ai_plan(sess, phase, offered_idx) if offered_idx else {}
        ranked = _rank(sess, allow_llm=sess.llm.used)
    scored = []
    if adaptive:
        chosen, phase, scored, metrics = policy.choose(st, ranked, sess.rng, temperature=sess.temperature)
        best = chosen.ranked if chosen else None
    else:
        best = st.pick(sess.strategy, ranked)
    sess.relaxed = False
    if best is None and adaptive and st.guesses > 0:
        # The strict pool is dry (family caps, "don't know" exclusions, gates).  Relax them step by step instead of giving up:
        # a game must not end because we ran out of *allowed* questions while informative ones still exist.
        sess.relaxed = True
        ranked = _rank(sess, allow_llm=bool(sess.llm and sess.llm.used), relax=True)
        chosen, phase, scored, metrics = policy.choose(st, ranked, sess.rng, temperature=sess.temperature, relax=True)
        best = chosen.ranked if chosen else st.pick("info_gain", ranked)
    sess.phase, sess.phase_metrics = phase, metrics
    if best is None:
        sess.current = None
        return None
    q = kb.bank.questions[best["index"]]
    text = original = None
    if q.id in paraphrase:
        text, original = paraphrase[q.id], q.text
    sess.current = {"best": best, "text": text, "original": original, "ranked": ranked[:8], "scored": scored[:6]}
    return best


# ------------------------------------------------------------------ explanation
def _entity_path_facts(kb: KB, uri: str, spec: Q.QuerySpec, name: str = "") -> list[str]:
    facts = []
    for p in spec.paths:
        r = Q.explain_path(p, uri)
        if not r:
            continue
        hops = " ; ".join(f"{h['from']} —{h['type']} [{h['provenance']}]→ {h['to']}" for h in r["hops"])
        if p.cond.kind == "label":
            hops += (f"{name} " if not r["hops"] else " ⇒ ") + f"rdf:type {p.cond.label}" + (" (inferred by OWL RL)" if p.cond.label in (r.get("end_inferred") or []) else "")
        if p.cond.kind == "cmp" and r.get("value") is not None:
            hops += f" ({p.cond.prop} = {r['value']})"
        facts.append(hops)
    return facts


def explain(sess: Session, idx: int):
    from .schemas import Evidence, Prediction
    kb, st = sess.kb, sess.state
    e = kb.entities[idx]
    inf_types = [r["t"] for r in graph.run("SELECT ?t WHERE { $u g:inferredType ?t } ORDER BY ?t", u=graph.iri(e["uri"]))]
    inferred_edges = graph.run("SELECT ?rel ?name WHERE { GRAPH <urn:akinator:inferred> { $u ?p ?t } ?p g:relType ?rel . ?t g:name ?name } ORDER BY ?rel ?name", u=graph.iri(e["uri"]))
    ev = []
    for a in st.asked:
        q = kb.bank.questions[a["index"]]
        tv = int(kb.bank.truth[a["index"], idx])
        lift = float(a["factor"][idx] / max((a["before"] * a["factor"]).sum(), 1e-12))
        facts = _entity_path_facts(kb, e["uri"], q.spec, e["name"]) if tv == 1 else []
        if tv == 1:
            support = "graph fact found" if facts or all(p.cond.kind == "exists" and not p.steps for p in q.spec.paths) else "graph fact found (entity category)"
        elif tv == 0:
            support = ("graph has no such fact (not listed - weak evidence, the list may be incomplete)" if kb.bank.false_rel[a["index"]] < config.DEFINITE_RELIABILITY - 1e-9
                       else "graph has no such fact (counted as false)")
        else:
            support = "no recorded fact - UNKNOWN in the graph (not treated as false)"
        ans_yes = a["answer"] in ("yes", "probably")
        if a["answer"] == "dont_know" or tv == -1:
            kind = "neutral"
        elif (tv == 1) == ans_yes:
            kind = "supports"
        else:
            kind = "contradicts"
        ev.append(Evidence(question=a.get("text") or q.text, answer=SEEN[a["answer"]], lift=round(lift, 3), support=support, facts=facts, kind=kind))
    ev.sort(key=lambda x: -x.lift)
    inferred = [f"{e['name']} —{r['rel']} [inferred]→ {r['name']}" for r in inferred_edges]
    inferred += [f"{e['name']} rdf:type {t} [inferred by OWL RL]" for t in inf_types if t not in ("Resource",)]
    top_p = float(st.w[idx])
    strong = [x for x in ev if x.facts and x.kind == "supports"][:3]
    expl = ((f"{e['name']} ({e['category']}) was my last guess, and you said it was wrong. " if idx in st.rejected
             else f"{e['name']} ({e['category']}) is the most probable candidate with score {top_p:.1%}. ")
            + ("Key graph-backed evidence: " + "; ".join(f"“{x.question}” answered {x.answer} — {x.facts[0]}" for x in strong) + "." if strong
               else "The answers matched this entity better than every other candidate, but no multi-hop graph path was needed.")
            + (f" {len(inferred)} of its facts are inferred by OWL RL reasoning." if inferred else ""))
    return Prediction(uri=e["uri"], name=e["name"], category=e["category"], score=round(top_p, 4), evidence=ev, inferred_facts=inferred[:20], explanation=expl)


# ------------------------------------------------------------------ session API
def _summary(sess: Session) -> dict:
    asked = sess.state.asked
    phases: dict[str, int] = {}
    for a in asked:
        phases[a.get("phase", "?")] = phases.get(a.get("phase", "?"), 0) + 1
    best = max(asked, key=lambda a: a.get("bits", 0.0), default=None)
    clue = None
    if best and best.get("bits", 0) > 0.05:
        clue = {"question": best.get("text") or sess.kb.bank.questions[best["index"]].text, "answer": SEEN[best["answer"]], "bits": round(best["bits"], 2)}
    return {"questions": len(asked), "wrong_guesses": sess.state.guesses - (1 if sess.status == "lost" else 0) if sess.status != "won" else sess.state.guesses,
            "phases": phases, "biggest_clue": clue}


def view(sess: Session, dev: bool = False):
    from .schemas import GameView, Candidate
    kb, st = sess.kb, sess.state
    qv = pred = None
    if sess.status == "asking" and sess.current:
        qv = _view(kb, {**sess.current["best"]}, sess.current["text"], sess.current["original"], dev)
    if sess.status in ("guessing", "won", "lost") and sess.prediction_idx is not None:
        pred = explain(sess, sess.prediction_idx)
    h0 = max(policy.entropy_bits(st.prior0), 1e-9)
    progress = float(min(1.0, max(0.0, 1.0 - policy.entropy_bits(st.w) / h0)))
    cand, debug = [], {}
    if dev:                            # candidate identities, probabilities, scores and queries are developer-only
        cand = [Candidate(uri=kb.entities[i]["uri"], name=kb.entities[i]["name"], category=kb.entities[i]["category"], probability=round(p, 5)) for i, p in st.top(10)]
        debug = {
            "ig_ranking": [{"question": kb.bank.questions[r["index"]].text, "info_gain": round(r["info_gain"], 4), "score": round(r["score"], 4),
                            "coverage": round(r["coverage"], 3), "source": kb.bank.questions[r["index"]].source} for r in (sess.current or {}).get("ranked", [])],
            "policy": [{"question": kb.bank.questions[x.index].text, "score": round(x.score, 3), "topic": x.topic, "components": x.components,
                        "info_gain": round(x.info_gain, 3)} for x in (sess.current or {}).get("scored", [])],
            "phase_metrics": sess.phase_metrics, "temperature": sess.temperature, "seed": sess.seed,
            "weights": {"entropy_bits": policy.entropy_bits(st.w), "max": float(st.w.max())},
            "top_candidate_facts": [{"rel": f["rel"], "target": f["name"], "provenance": f["provenance"]} for f in kb.entity_facts(cand[0].uri, 25)] if cand else [],
            "bank_size": len(kb.bank.questions),
        }
    hist = [{"question": a.get("text") or kb.bank.questions[a["index"]].text, "answer": SEEN[a["answer"]], "phase": a.get("phase", "")} for a in st.asked]
    return GameView(session_id=sess.id, mode=sess.mode, status=sess.status, question_count=len(st.asked), remaining_candidates=st.remaining() if dev else 0,
                    current_question=qv, prediction=pred, history=hist, top_candidates=cand, llm=sess.llm if dev or sess.mode == "ai" else None, debug=debug,
                    phase=sess.phase, phase_label=policy.PHASE_LABEL[sess.phase], progress=round(progress, 3), reaction=sess.reaction,
                    guesses=st.guesses, summary=_summary(sess) if sess.status in ("won", "lost") else None, seed=sess.seed if dev else None)


def advance(sess: Session):
    st = sess.state
    if st.should_guess():
        sess.status, sess.prediction_idx, sess.current = "guessing", st.top(1)[0][0], None
        return
    best = select_question(sess)
    if best is None:                                                   # nothing informative left -> best guess
        sess.status, sess.prediction_idx = "guessing", st.top(1)[0][0]
        return
    # diminishing returns: the best remaining question tells us (almost) nothing and one candidate leads clearly -> stop asking
    if config.IG_FLOOR > 0 and len(st.asked) >= config.MIN_QUESTIONS and best["info_gain"] < config.IG_FLOOR and st.w.max() >= config.FLOOR_CONF:
        sess.status, sess.prediction_idx, sess.current = "guessing", st.top(1)[0][0], None


def start(mode: str, strategy: str = "info_gain", register: bool = True, seed: int | None = None, exploration: str = "medium") -> Session:
    sess = Session(get_kb(), mode, seed, exploration)
    sess.strategy = strategy
    if strategy == "random":
        sess.state.rng = sess.rng
    if register:
        SESSIONS[sess.id] = sess
    advance(sess)
    return sess


def _apply(sess: Session, state: GameState, index: int, ans: str, text: str | None):
    """Answer a question and record the phase it was asked in and the information it brought (bits)."""
    h_before = policy.entropy_bits(state.w)
    phase, _ = policy.phase_of(state, commit=True)
    before = state.answer(index, ans)
    state.asked[-1].update(before=before, text=text, phase=phase, bits=max(0.0, h_before - policy.entropy_bits(state.w)))
    return state.asked[-1]


def answer(sess: Session, ans: str, question_id: str | None):
    if sess.status != "asking" or not sess.current:
        raise ValueError("no open question")
    best = sess.current["best"]
    q = sess.kb.bank.questions[best["index"]]
    if question_id and question_id != q.id:
        raise ValueError("answer does not match the current question")
    entry = _apply(sess, sess.state, best["index"], ans, sess.current["text"] or q.text)
    sess.reaction = policy.reaction_for(ans, entry["bits"], entry["phase"], sess.state.remaining())
    advance(sess)


def feedback(sess: Session, correct: bool):
    if sess.status != "guessing":
        raise ValueError("no pending guess")
    if correct:
        sess.status = "won"
        return
    sess.state.reject(sess.prediction_idx)
    sess.reaction = "Not quite! Let me think again…"
    if sess.state.guesses >= 5 or sess.state.w.max() <= 0:
        sess.status = "lost"
        return
    sess.status, sess.prediction_idx = "asking", None
    # after a wrong guess keep playing until confident again; always ask at least one more question
    if select_question(sess) is None:                                  # nothing left to ask even after relaxing: offer the next best suspect
        sess.status, sess.prediction_idx = "guessing", sess.state.top(1)[0][0]


def undo(sess: Session):
    """Take back the last answer: replay all earlier answers on a fresh state (answers commute, so order is irrelevant)."""
    if sess.status not in ("asking", "guessing") or not sess.state.asked:
        raise ValueError("nothing to undo")
    old = sess.state
    new = GameState(sess.kb.bank, rng=sess.rng)
    for a in old.asked[:-1]:
        _apply(sess, new, a["index"], a["answer"], a.get("text"))
    for e in old.rejected:
        new.reject(e)
    sess.state, sess.status, sess.prediction_idx, sess.reaction = new, "asking", None, "Answer taken back."
    if select_question(sess) is None:
        sess.status, sess.prediction_idx = "guessing", new.top(1)[0][0]
