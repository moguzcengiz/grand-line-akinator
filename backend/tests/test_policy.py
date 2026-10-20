"""Unit tests of the adaptive question policy and the richer question grammar (no Neo4j needed)."""
import json
import random
from collections import Counter

import numpy as np
import pytest
from pydantic import ValidationError

from app import config, policy
from app.engine import Bank, GameState
from app.questions import (COMPLETE_RELS, Cond, Path, Question, QuerySpec, Step, combine, compile_path, complexity, topic, validate_spec)


def mk(i, cat="Character", rel="AFFILIATES_WITH", kind="uri"):
    cond = Cond(kind="uri", uri=f"u{i}") if kind == "uri" else Cond(kind="exists")
    steps = [Step(rel=rel)] if kind == "uri" else []
    return Question(id=f"q{i}", text=f"Question number {i}?", spec=QuerySpec(paths=[Path(start=cat, steps=steps, cond=cond)]))


def bank_of(rows, rels=None):
    rows = np.array(rows, dtype=np.int8)
    b = Bank([f"e{j}" for j in range(rows.shape[1])])
    for i, r in enumerate(rows):
        b.add(mk(i, rel=(rels[i] if rels else "AFFILIATES_WITH")), r)
    return b


@pytest.fixture(autouse=True)
def _cfg(monkeypatch):
    monkeypatch.setattr(config, "FAMILY_MAX", 10 ** 6)
    monkeypatch.setattr(config, "GATE_REL", 0.35)
    monkeypatch.setattr(config, "TEMPERATURE", 0.06)


def random_bank(Q=40, E=120, seed=0):
    r = np.random.default_rng(seed)
    rels = list(r.choice(["AFFILIATES_WITH", "OCCUPATION", "RESIDENCE", "PLACE_OF_ORIGIN"], size=Q))
    return bank_of(r.integers(0, 2, size=(Q, E)), rels)


# ------------------------------------------------------------------ scoring
def test_components_are_normalised_and_weights_sum_to_one():
    for ph, w in policy.WEIGHTS.items():
        assert abs(sum(w.values()) - 1) < 1e-9, ph
    st = GameState(random_bank())
    sc = policy.score_questions(st, st.rank(), "discovery")
    assert sc
    for s in sc:
        assert all(0.0 <= v <= 1.0 for v in s.components.values())
        assert 0.0 <= s.score <= 1.0


def test_gate_never_offers_questions_without_discriminative_value():
    # q0 perfect split, q1 constant (no information), q2 almost constant, q3 all unknown
    rows = [[1] * 60 + [0] * 60, [1] * 120, [1] + [0] * 119, [-1] * 120]
    st = GameState(bank_of(rows))
    ids = {s.index for s in policy.score_questions(st, st.rank(), "discovery")}
    assert ids == {0}, "only the discriminative question may be selectable"


def test_semantic_duplicates_of_asked_questions_are_excluded():
    base = np.random.default_rng(3).integers(0, 2, size=120)
    rows = [base, base.copy(), 1 - base, np.random.default_rng(4).integers(0, 2, size=120)]    # q1 same, q2 negation (|phi| = 1), q3 independent
    st = GameState(bank_of(rows))
    st.answer(0, "yes")
    ids = {s.index for s in policy.score_questions(st, st.rank(), "investigation")}
    assert 1 not in ids and 2 not in ids and 3 in ids


def test_topic_diversity_prefers_a_fresh_topic():
    rng = np.random.default_rng(8)
    rows = [rng.integers(0, 2, size=200) for _ in range(6)]
    rels = ["AFFILIATES_WITH", "AFFILIATES_WITH", "AFFILIATES_WITH", "RESIDENCE", "RESIDENCE", "RESIDENCE"]
    rows[3], rows[4], rows[5] = rows[0].copy(), rows[1].copy(), rows[2].copy()          # twins with the same information, other topic
    rows[3][:5] ^= 1; rows[4][:5] ^= 1; rows[5][:5] ^= 1                                  # (slightly different so they are not duplicates)
    st = GameState(bank_of(rows, rels))
    st.answer(0, "yes"); st.answer(1, "no")                                                # two affiliation questions just asked
    sc = {s.index: s for s in policy.score_questions(st, st.rank(), "discovery")}
    assert 2 in sc and 5 in sc
    assert sc[5].components["diversity"] > sc[2].components["diversity"]
    assert sc[5].score > sc[2].score


# ------------------------------------------------------------------ stochastic selection
def test_seeded_sampling_is_reproducible_and_seeds_differ():
    st = GameState(random_bank())
    ranked = st.rank()
    runs = {}
    for seed in range(40):
        a = policy.choose(st, ranked, random.Random(seed))[0].index
        b = policy.choose(st, ranked, random.Random(seed))[0].index
        assert a == b, "same seed must give the same question"
        runs[seed] = a
    assert len(set(runs.values())) >= 2, "different seeds must be able to open differently"


def test_deterministic_mode_is_argmax():
    st = GameState(random_bank())
    ranked = st.rank()
    top = policy.score_questions(st, ranked, policy.phase_of(st)[0])[0].index
    for seed in range(10):
        assert policy.choose(st, ranked, random.Random(seed), temperature=0.0)[0].index == top


def test_strong_questions_are_more_likely_than_weak_ones_and_stay_inside_top_k():
    st = GameState(random_bank(seed=2))
    ranked = st.rank()
    scored = policy.score_questions(st, ranked, "discovery")
    k = config.TOP_K
    counts = Counter(policy.sample(scored, random.Random(i), 0.06, k).index for i in range(4000))
    topk = [s.index for s in scored[:k]]
    assert set(counts) <= set(topk), "never samples outside the top-k"
    assert counts[topk[0]] > counts[topk[-1]], "the strongest question must be sampled more often than the weakest of the top-k"
    assert all(counts[i] > 0 for i in topk) or scored[0].score - scored[k - 1].score > 0.1


def test_exploration_strength_controls_spread():
    st = GameState(random_bank(seed=5))
    scored = policy.score_questions(st, st.rank(), "discovery")
    spread = lambda T: len({policy.sample(scored, random.Random(i), T, 5).index for i in range(300)})
    assert spread(0.0) == 1 and spread(0.02) <= spread(0.3)


# ------------------------------------------------------------------ phases
def test_phase_depends_on_entropy_and_confidence_not_question_number():
    st = GameState(random_bank(Q=30, E=200, seed=1))
    assert policy.phase_of(st)[0] == "discovery"
    st.w = np.zeros_like(st.w); st.w[:5] = 0.2                                                   # five equally likely suspects left
    assert policy.phase_of(st)[0] == "deduction"
    st.w = np.zeros_like(st.w); st.w[0] = 0.5; st.w[1:] = 0.5 / (len(st.w) - 1)                  # one clear favourite
    assert policy.phase_of(st)[0] == "deduction"
    st.w = np.zeros_like(st.w); st.w[:90] = 1 / 90                                                # 90 of 200 left: still broad -> discovery
    assert policy.phase_of(st)[0] == "discovery"
    st.w = np.zeros_like(st.w); st.w[:25] = 1 / 25                                                # 25 of 200 left, no favourite -> investigation
    assert policy.phase_of(st)[0] == "investigation"


def test_phase_changes_weights_towards_information_late():
    assert policy.WEIGHTS["deduction"]["info"] > policy.WEIGHTS["discovery"]["info"]
    assert policy.WEIGHTS["discovery"]["diversity"] > policy.WEIGHTS["deduction"]["diversity"]


# ------------------------------------------------------------------ grammar
def test_kleene_logic_never_turns_unknown_into_false():
    assert combine([1, -1], "all") == -1 and combine([0, -1], "all") == 0 and combine([1, 1], "all") == 1
    assert combine([0, -1], "any") == -1 and combine([1, -1], "any") == 1 and combine([0, 0], "any") == 0


def test_conjunction_needs_same_category_and_two_conditions():
    a = Path(start="Character", cond=Cond(kind="label", label="CaptainCharacter"), scope="rel:OCCUPATION")
    b = Path(start="Ship", cond=Cond(kind="label", label="PirateShip"))
    assert validate_spec(QuerySpec(paths=[a], mode="all"), {"OCCUPATION"}, {"CaptainCharacter", "PirateShip"}) is not None
    assert validate_spec(QuerySpec(paths=[a, b], mode="all"), {"OCCUPATION"}, {"CaptainCharacter", "PirateShip"}) is not None
    assert validate_spec(QuerySpec(paths=[a, a.model_copy(update={"scope": "rel:X"})], mode="all"), {"OCCUPATION", "X"}, {"CaptainCharacter"}) is None


def test_cardinality_only_accepted_without_claiming_completeness():
    c = Cond(kind="count", op=">=", value=2)
    ok = Path(start="Character", steps=[Step(rel="AFFILIATES_WITH")], cond=c, scope="positive")
    bad = ok.model_copy(update={"scope": "closed"})
    assert validate_spec(QuerySpec(paths=[ok]), {"AFFILIATES_WITH"}, set()) is None
    assert "completeness" in validate_spec(QuerySpec(paths=[bad]), {"AFFILIATES_WITH"}, set())
    tq, kq, params = compile_path(ok)
    assert "COUNT {" in tq and kq == tq and params["v"] == 2            # absent -> unknown, never false
    assert COMPLETE_RELS == set(), "no relation is declared complete in the upstream data"
    with pytest.raises(ValueError):
        compile_path(Path(start="Character", cond=Cond(kind="count", op="<=", value=2), steps=[Step(rel="A")], scope="positive"))


def test_inverse_and_multi_hop_compile_to_parameterised_cypher():
    p = Path(start="DevilFruit", steps=[Step(rel="HAS_DEVIL_FRUIT", dir="in"), Step(rel="OWNS_SHIP")], cond=Cond(kind="exists"), scope="rel:DEVIL_FRUIT_CURRENT_USER")
    tq, kq, _ = compile_path(p)
    assert "<-[:`HAS_DEVIL_FRUIT`]-(n1)-[:`OWNS_SHIP`]->(n2)" in tq


def test_topic_and_complexity_helpers():
    q = Question(id="x", text="Is it a captain who ate a fruit?", spec=QuerySpec(mode="all", paths=[
        Path(start="Character", cond=Cond(kind="label", label="CaptainCharacter")), Path(start="Character", cond=Cond(kind="label", label="DevilFruitUser"))]))
    assert topic(q) == "combo" and complexity(q) > complexity(mk(1))
    assert topic(mk(1, rel="PLACE_OF_ORIGIN")) == "origin" and topic(mk(2, cat="Ship", kind="exists")) == "category"


def test_reactions_are_templated_and_never_empty():
    for ans in ("yes", "no", "dont_know", "probably"):
        for bits in (0.0, 0.8, 2.0):
            assert policy.reaction_for(ans, bits, "investigation", 100)


def test_phase_hysteresis_prevents_flicker():
    st = GameState(random_bank(Q=30, E=200, seed=1))
    st.w = np.zeros_like(st.w); st.w[:5] = 0.2
    assert policy.phase_of(st, commit=True)[0] == "deduction"
    st.w = np.zeros_like(st.w); st.w[:25] = 1 / 25                       # a contradictory answer widened the pool a little: stay in deduction
    assert policy.phase_of(st, commit=True)[0] == "deduction"
    st.w = np.zeros_like(st.w); st.w[:120] = 1 / 120                      # the pool genuinely re-opened -> back to investigation, never discovery
    assert policy.phase_of(st, commit=True)[0] == "investigation"
    st.w = np.ones_like(st.w) / len(st.w)
    assert policy.phase_of(st, commit=True)[0] == "investigation"         # discovery is not re-entered


# ------------------------------------------------------------------ LLM planner robustness (no network)
def test_tolerant_parser_drops_only_the_malformed_item():
    from app import llm
    good = {"text": "Is your character a captain?", "spec": {"paths": [{"start": "Character", "cond": {"kind": "label", "label": "CaptainCharacter"}}]}}
    bad = {"text": "Broken?", "spec": {"paths": [{"start": "Character", "scope": "closed"}]}}                     # path without cond
    raw = json.dumps({"paraphrases": [{"id": "q1", "text": "Does your hero sail under a pirate flag?"}, {"nope": 1}], "new_questions": [good, bad], "reaction": "Nice one!"})
    reply, dropped = llm.parse_reply("```json\n" + raw + "\n```")
    assert dropped == 2 and len(reply.new_questions) == 1 and len(reply.paraphrases) == 1 and reply.reaction == "Nice one!"


def test_planner_has_a_hard_deadline(monkeypatch):
    import time
    from app import llm
    monkeypatch.setattr(config, "LLM_TIMEOUT", 0.2)
    monkeypatch.setattr(llm, "DEADLINE_SLACK", 0.1)
    monkeypatch.setattr(llm, "_client", lambda: type("C", (), {"chat": type("Ch", (), {"completions": type("Co", (), {"create": staticmethod(lambda **k: time.sleep(3))})})})())
    t0 = time.time()
    with pytest.raises(TimeoutError):
        llm.ask({"relationships": [], "labels": [], "numeric_props": []}, [], [], [])
    assert time.time() - t0 < 2.5, "a stalled call must not block longer than the deadline"


def test_duplicate_of_a_dont_know_question_does_not_set_the_gate():
    """Regression: after 'don't know' to q0 its twin q1 kept the highest information gain and set the 35% bar, then was excluded as a
    duplicate - so every other question failed the gate and the pool looked empty (a third of all games hit this)."""
    perfect = np.array([1] * 100 + [0] * 100)
    rows = [perfect, perfect.copy(), np.array([1] * 6 + [0] * 194), np.array([1] * 3 + [0] * 197)]       # q2 / q3: far less informative
    st = GameState(bank_of(rows, ["AFFILIATES_WITH", "OCCUPATION", "RESIDENCE", "PLACE_OF_ORIGIN"]))
    ig = {r["index"]: r["info_gain"] for r in st.rank()}
    assert ig[2] < config.GATE_REL * ig[0], "setup: q2 must be below the gate when the twin is still counted"
    st.answer(0, "dont_know")                                                   # no information, q1 (identical) is now unaskable
    ids = {s.index for s in policy.score_questions(st, st.rank(), "investigation")}
    assert 1 not in ids and 2 in ids, "the best question that CAN be asked must set the bar"
