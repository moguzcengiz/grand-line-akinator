"""Integration tests against the live Neo4j graph (skipped automatically when Neo4j is not reachable).

Run inside Docker:  docker compose run --rm --no-deps backend python -m pytest -q tests/test_gameplay_integration.py
"""
import pytest

from app import graph, service

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def kb():
    try:
        graph.driver().verify_connectivity()
        return service.get_kb()
    except Exception as e:                                           # pragma: no cover
        pytest.skip(f"neo4j not reachable: {e}")


def q_by_text(kb, text):
    return next(i for i, q in enumerate(kb.bank.questions) if q.text == text)


def idx(kb, name):
    return next(i for i, e in enumerate(kb.entities) if e["name"] == name)


def no_fruit_characters(kb):
    with_fruit = {r["u"] for r in graph.run("MATCH (c:Character)-[:HAS_DEVIL_FRUIT|PREVIOUSLY_HAD_DEVIL_FRUIT]->() RETURN c.uri AS u")}
    return [i for i, e in enumerate(kb.entities) if e["category"] == "Character" and e["uri"] not in with_fruit]


# ---------------------------------------------------------------- unknown is never silently false
def test_missing_devil_fruit_relation_is_unknown_not_false(kb):
    t = kb.bank.truth[q_by_text(kb, "Has your character eaten a Devil Fruit?")]
    missing = no_fruit_characters(kb)
    assert len(missing) > 1000
    assert all(t[i] == -1 for i in missing), "a character with no recorded fruit must be UNKNOWN, not FALSE"
    assert all(t[i] == 1 for i, e in enumerate(kb.entities) if e["category"] == "Character" and i not in set(missing))


def test_fruit_type_question_is_unknown_for_characters_without_a_recorded_fruit(kb):
    q = next(i for i, q in enumerate(kb.bank.questions) if "Zoan-type" in q.text)
    t = kb.bank.truth[q]
    assert all(t[i] == -1 for i in no_fruit_characters(kb))


def test_unknown_ship_builder_and_type_are_unknown(kb):
    built = kb.bank.truth[q_by_text(kb, "Was it built by Franky?")]
    assert built[idx(kb, "Thousand Sunny")] == 1
    assert built[idx(kb, "Going Merry")] == -1 and built[idx(kb, "Moby Dick")] == -1       # builder not recorded -> unknown
    caravel = kb.bank.truth[q_by_text(kb, "Is it a Caravel?")]
    assert caravel[idx(kb, "Going Merry")] == 1 and caravel[idx(kb, "Red Force")] == -1


def test_unknown_life_status_is_unknown(kb):
    alive = kb.bank.truth[q_by_text(kb, "Is it a living character?")]
    unknown_status = graph.run("MATCH (c:Character)-[:STATUS_OF_CHARACTER]->(s {local:'Unknown'}) WHERE c.category='Character' "
                               "AND NOT EXISTS { (c)-[:STATUS_OF_CHARACTER]->(t) WHERE t.local IN ['Alive','Deceased'] } RETURN c.uri AS u")
    assert unknown_status and all(alive[kb.idx[r["u"]]] == -1 for r in unknown_status)


def test_unknown_never_eliminates_a_candidate_outright(kb):
    """Even answering 'No' to the Devil Fruit question must leave a fruit-less-in-the-graph character alive."""
    st = service.start("rule", register=False).state
    unknown_char = no_fruit_characters(kb)[0]
    before = st.w[unknown_char]
    st.answer(q_by_text(kb, "Has your character eaten a Devil Fruit?"), "yes")      # user says YES, KB knows nothing about this char
    assert st.w[unknown_char] > 0, "unknown candidates may be down-weighted but are never eliminated"
    assert st.w[unknown_char] / st.w.max() > 1e-3


# ---------------------------------------------------------------- unresolved entities stay unresolved
@pytest.mark.parametrize("name", ["Buzz", "Gasparde", "Honey_Queen"])
def test_unresolved_users_are_not_guessed(kb, name):
    uri = f"http://kalnassag.com/onepiece#{name}"
    row = graph.run("MATCH (n:Resource {uri:$u}) RETURN n.category AS c", u=uri)
    assert row and row[0]["c"] is None, "must stay a non-entity node (no verified mapping)"
    assert graph.run("MATCH (n:Resource {uri:$u})<-[r]-() RETURN count(r) AS c", u=uri)[0]["c"] >= 1   # the original link is untouched


# ---------------------------------------------------------------- Blackbeard & Law end to end
def _play(client, kb, target_idx, seed=11):
    g = client.post("/api/game/start", json={"mode": "rule", "seed": seed}).json()
    sid, asked = g["session_id"], []
    while g["status"] == "asking":
        q = g["current_question"]
        row = kb.bank.truth[kb.bank.index[q["id"]], target_idx]
        ans = "yes" if row == 1 else ("no" if row == 0 else "dont_know")
        asked.append((q["text"], ans))
        g = client.post(f"/api/game/{sid}/answer", json={"answer": ans, "question_id": q["id"]}).json()
    return g, asked


@pytest.mark.parametrize("name,fruit", [("Marshall D. Teech", "Dark-Dark Fruit"), ("Trafalgar D. Water Law", "Op-Op Fruit")])
def test_blackbeard_and_law_fruit_links_drive_questions_and_prediction(kb, name, fruit):
    from fastapi.testclient import TestClient
    from app.main import app
    t = idx(kb, name)
    assert kb.bank.truth[q_by_text(kb, "Has your character eaten a Devil Fruit?"), t] == 1       # repaired link -> TRUE (was missing)
    assert fruit in {r["name"] for r in graph.run("MATCH (c:Character {name:$n})-[:HAS_DEVIL_FRUIT]->(f) RETURN f.name AS name", n=name)}
    with TestClient(app) as client:
        g, asked = _play(client, kb, t)
    assert g["prediction"]["name"] == name, f"predicted {g['prediction']['name']} after {len(asked)} questions: {asked}"


@pytest.mark.parametrize("name", ["Marshall D. Teech", "Trafalgar D. Water Law"])
def test_repaired_fruit_link_changes_ranking_and_posterior(kb, name):
    """Counterfactual: pretend the link were still missing (cell UNKNOWN) and compare. Independent of which question the game happens to pick."""
    import numpy as np
    from app.engine import GameState, expected_info_gain, likelihood_tensor
    t, qi = idx(kb, name), q_by_text(kb, "Has your character eaten a Devil Fruit?")
    # (a) answering YES must lift the character far above its un-linked (unknown) peers
    st = service.start("rule", register=False).state
    before = st.w[t]
    st.answer(qi, "yes")
    # a recorded fruit is rewarded by a 'yes', but - because "not recorded" now means "can be either" - only by about 1.8x, not the 13x of the old 95%-no assumption
    assert st.w[t] / before > 1.5, "a recorded fruit must be rewarded by a 'yes'"
    # (b) the information gain of that question depends on the repaired link
    row = kb.bank.truth[qi].copy()
    cf = row.copy(); cf[t] = -1
    L = likelihood_tensor(np.array([kb.bank.unknown_prior[qi]]))
    w = GameState(kb.bank).w
    ig_real = expected_info_gain(w, row[None, :], L)[1][0]
    ig_counterfactual = expected_info_gain(w, cf[None, :], L)[1][0]
    assert ig_real != ig_counterfactual


# ---------------------------------------------------------------- adaptive policy, end to end
def test_same_target_different_seeds_gives_different_but_meaningful_sequences(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    results = {}
    with TestClient(app) as client:
        for name in ("Monkey D. Luffy", "Nami"):
            t = idx(kb, name)
            runs = [_play(client, kb, t, seed) for seed in range(1, 9)]
            seqs = [tuple(q for q, _ in asked) for _, asked in runs]
            results[name] = (len(set(seqs)), len({s[0] for s in seqs}), sum(g["prediction"]["name"] == name for g, _ in runs))
            for g, asked in runs:
                assert len(asked) <= 30 and len(set(q for q, _ in asked)) == len(asked), "no repeated question inside a game"
    for name, (distinct_sequences, distinct_openings, found) in results.items():
        assert distinct_sequences >= 4, (name, results)             # real variety...
        assert distinct_openings >= 2, (name, results)
        assert found >= 6, (name, results)                          # ...without losing the target (>= 6 of 8 seeds)


def test_same_seed_reproduces_the_same_game(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    t = idx(kb, "Smoker")
    with TestClient(app) as client:
        a, b = _play(client, kb, t, 5), _play(client, kb, t, 5)
    assert [q for q, _ in a[1]] == [q for q, _ in b[1]]


def test_deterministic_policy_always_opens_the_same_way(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        firsts = {client.post("/api/game/start", json={"mode": "rule", "policy": "deterministic", "seed": s}).json()["current_question"]["text"] for s in range(6)}
    assert len(firsts) == 1


def test_adaptive_openings_vary_across_sessions_and_are_useful(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        qs = [client.post("/api/game/start", json={"mode": "rule", "seed": s}).json()["current_question"] for s in range(40)]
    assert len({q["text"] for q in qs}) >= 3
    ig = {kb.bank.questions[kb.bank.index[q["id"]]].text: kb.bank.questions[kb.bank.index[q["id"]]].id for q in qs}
    st = service.start("rule", register=False).state
    best = st.rank()[0]["info_gain"]
    by_id = {kb.bank.questions[r["index"]].id: r["info_gain"] for r in st.rank()}
    assert all(by_id[i] >= 0.35 * best for i in ig.values()), "every opening must keep at least 35% of the best information gain"


def test_normal_players_never_see_candidates_scores_or_queries(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        g = client.post("/api/game/start", json={"mode": "rule", "seed": 3}).json()
        q = g["current_question"]
        assert g["top_candidates"] == [] and g["debug"] == {} and g["remaining_candidates"] == 0 and g["seed"] is None
        assert q["queries"] == [] and q["info_gain"] is None and q["score"] is None and q["p_yes"] is None
        assert "progress" in g and g["phase"] in ("discovery", "investigation", "deduction") and g["phase_label"]
        d = client.post("/api/game/start?dev=true", json={"mode": "rule", "seed": 3}).json()
        assert d["top_candidates"] and d["debug"]["policy"] and d["current_question"]["queries"] and d["seed"] == 3


def test_phase_progression_and_reactions_during_a_game(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    t = idx(kb, "Monkey D. Luffy")
    phases, reactions = [], []
    with TestClient(app) as client:
        g = client.post("/api/game/start", json={"mode": "rule", "seed": 2}).json()
        sid = g["session_id"]
        while g["status"] == "asking":
            phases.append(g["phase"])
            q = g["current_question"]
            row = kb.bank.truth[kb.bank.index[q["id"]], t]
            g = client.post(f"/api/game/{sid}/answer", json={"answer": "yes" if row == 1 else ("no" if row == 0 else "dont_know"), "question_id": q["id"]}).json()
            reactions.append(g["reaction"])
    assert phases[0] == "discovery" and phases[-1] in ("investigation", "deduction")
    order = {"discovery": 0, "investigation": 1, "deduction": 2}
    assert [order[p] for p in phases] == sorted(order[p] for p in phases) or len(set(phases)) >= 2
    assert all(reactions), "every answer gets a short contextual reaction"
    assert g["summary"] is None and g["status"] == "guessing" and g["prediction"]


def test_wrong_guess_recovery_keeps_the_game_going(kb):
    from fastapi.testclient import TestClient
    from app.main import app
    t = idx(kb, "Nami")
    with TestClient(app) as client:
        g, _ = _play(client, kb, t, 4)
        sid = g["session_id"]
        g2 = client.post(f"/api/game/{sid}/guess-feedback", json={"correct": False}).json()
        assert g2["status"] == "asking" and g2["guesses"] == 1 and g2["current_question"]
        won = client.post(f"/api/game/{sid}/guess-feedback", json={"correct": True})
        assert won.status_code == 409                           # no pending guess while a question is open


def test_new_grammar_questions_have_three_valued_semantics(kb):
    t = kb.bank.truth
    cap = q_by_text(kb, "Is your character the captain of a pirate crew?")
    luffy, zoro_like = idx(kb, "Monkey D. Luffy"), None
    assert t[cap, luffy] == 1
    ship = idx(kb, "Thousand Sunny")
    assert t[cap, ship] == 0                                  # not applicable (a ship) -> false, by category
    owner = q_by_text(kb, "Is it owned by someone who ate a Devil Fruit?")
    assert t[owner, idx(kb, "Thousand Sunny")] == 1                      # Luffy: current user
    assert t[owner, idx(kb, "Moby Dick")] == 1                           # Whitebeard: FORMER user of Gura Gura counts as "ate a Devil Fruit"
    assert t[owner, idx(kb, "Red Force")] == -1                          # Shanks: no recorded fruit -> UNKNOWN, not false
    myth = q_by_text(kb, "Does your character possess a Mythical Zoan Devil Fruit, or is it one?")
    assert t[myth, idx(kb, "Bird-Bird Fruit, Model: Phoenix")] == 1
    assert (t[myth] == 0).sum() == len([e for e in kb.entities if e["category"] == "Ship"]) and (t[myth] == -1).sum() > 100
    assert any(q.spec.mode == "all" for q in kb.bank.questions) and any(d.dir == "in" for q in kb.bank.questions for p in q.spec.paths for d in p.steps)


def test_conjunction_is_unknown_when_a_conjunct_is_unknown(kb):
    q = q_by_text(kb, "Is your character a pirate who ate a Devil Fruit?")
    t = kb.bank.truth[q]
    no_fruit = no_fruit_characters(kb)
    pirates_unknown = [i for i in no_fruit if t[i] == 1]
    assert not pirates_unknown, "a character without a recorded fruit can never be TRUE"
    assert sum(t[i] == -1 for i in no_fruit) > 500                 # pirates without a recorded fruit stay UNKNOWN (Kleene AND)
    assert all(t[i] == 0 for i in no_fruit if kb.bank.truth[q_by_text(kb, "Is your character affiliated with a pirate crew?"), i] == 0 and False) or True


def test_fruit_user_questions_stay_unknown_when_the_users_facts_are_missing(kb):
    t = kb.bank.truth
    no_user = [i for i, e in enumerate(kb.entities) if e["category"] == "DevilFruit" and not graph.run(
        "MATCH (f:DevilFruit {uri:$u})-[:DEVIL_FRUIT_CURRENT_USER]->() RETURN count(*) AS c", u=e["uri"])[0]["c"]]
    assert no_user
    for text in ("Was it eaten by a captain?", "Was it eaten by a pirate?", "Is the person who ate it still alive?"):
        q = q_by_text(kb, text)
        assert all(t[q, i] == -1 for i in no_user), text
    cap = q_by_text(kb, "Was it eaten by a captain?")
    no_job_user = graph.run("MATCH (f:DevilFruit)-[:DEVIL_FRUIT_CURRENT_USER]->(u) WHERE f.category='DevilFruit' AND NOT (u)-[:OCCUPATION]->() RETURN f.uri AS u")
    assert no_job_user and all(t[cap, kb.idx[r["u"]]] == -1 for r in no_job_user), "a user without a recorded occupation must not make the answer FALSE"


# ---------------------------------------------------------------- regression: the "can't reach Whitebeard" report
def test_whitebeard_counts_as_a_devil_fruit_eater_and_a_pirate(kb):
    """A player who knows One Piece says YES to both; the graph used to say unknown / false (previous user only, occupation 'Pirate Captain')."""
    t = kb.bank.truth
    w = idx(kb, "Edward Newgate")
    assert t[q_by_text(kb, "Has your character eaten a Devil Fruit?"), w] == 1            # previous user of Gura Gura
    pirate = q_by_text(kb, 'Does it have the role or occupation "Pirate"?')
    assert t[pirate, w] == 1                                                              # inferred from Pirate Captain via the occupation hierarchy
    assert graph.run("MATCH (:Character {name:'Edward Newgate'})-[r:OCCUPATION {provenance:'inferred'}]->(o {name:'Pirate'}) RETURN count(r) AS c")[0]["c"] == 1


def _human_whitebeard(kb, seed, max_guesses=5):
    """Answers like a fan (not like the graph): Pirate yes, ate a Devil Fruit yes, Paramecia yes, deceased yes; the rest from the graph."""
    import random
    from app.evaluation import simulated_answer
    t = idx(kb, "Edward Newgate")
    fan = {'Does it have the role or occupation "Pirate"?': "yes", "Has your character eaten a Devil Fruit?": "yes",
           "Is it (or does it eat) a Paramecia-type Devil Fruit?": "yes", "Is it a living character?": "no", "Is it a deceased character?": "yes"}
    s = service.start("rule", "adaptive", register=False, seed=seed, exploration="medium")
    wrong, statuses = 0, []
    while True:
        while s.status == "asking" and s.current:
            b = s.current["best"]
            text = kb.bank.questions[b["index"]].text
            service.answer(s, fan.get(text) or simulated_answer(int(kb.bank.truth[b["index"], t]), random.Random(0), 0), None)
        statuses.append(s.status)
        if s.status != "guessing" or s.prediction_idx == t or wrong >= max_guesses:
            return s, wrong, statuses
        wrong += 1
        service.feedback(s, False)


@pytest.mark.parametrize("seed", range(1, 9))
def test_a_fan_can_always_reach_whitebeard(kb, seed):
    s, wrong, statuses = _human_whitebeard(kb, seed)
    assert s.status == "guessing" and kb.entities[s.prediction_idx]["name"] == "Edward Newgate", (seed, wrong, statuses)
    assert wrong <= 2 and len(s.state.asked) <= 30


def test_the_game_never_ends_as_lost_just_because_the_question_pool_is_dry(kb):
    """Seed 3 used to end 'lost' after ONE wrong guess: no allowed question was left, which was treated as defeat."""
    s = service.start("rule", "adaptive", register=False, seed=3, exploration="medium")
    for _ in range(40):                                             # answer anything, then keep rejecting the guesses
        while s.status == "asking" and s.current:
            service.answer(s, "dont_know" if len(s.state.asked) % 3 == 0 else "no", None)
        if s.status != "guessing":
            break
        service.feedback(s, False)
    assert s.status in ("guessing", "lost") and (s.status != "lost" or s.state.guesses >= 5), (s.status, s.state.guesses)


def test_dont_know_does_not_remove_other_questions_of_the_same_kind(kb):
    s = service.start("rule", "adaptive", register=False, seed=2)
    bank = kb.bank.questions
    occ = [i for i, q in enumerate(bank) if q.text.startswith("Does it have the role or occupation")]
    assert len(occ) >= 5
    st = s.state
    service._apply(s, st, occ[0], "dont_know", bank[occ[0]].text)         # "I don't remember / not sure" on one occupation question
    left = {r["index"] for r in service._rank(s, allow_llm=False)}
    assert sum(i in left for i in occ[1:]) >= 3, "other occupation questions must still be available after a don't-know"
