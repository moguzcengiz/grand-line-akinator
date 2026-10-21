import random

import numpy as np

from app import config
from app.engine import ANSWERS, Bank, GameState, expected_info_gain, likelihood_matrix
from app.questions import Question, QuerySpec, Path, Cond


def q(i):
    return Question(id=f"q{i}", text=f"Question number {i}?", spec=QuerySpec(paths=[Path(start="Character", cond=Cond(kind="exists"))]))


def make_bank(truth):
    truth = np.array(truth, dtype=np.int8)
    b = Bank([f"e{j}" for j in range(truth.shape[1])])
    for i, row in enumerate(truth):
        b.add(q(i), row)
    return b


def brute_force_ig(w, truth_row, L):
    H = lambda p: -(p[p > 0] * np.log(p[p > 0])).sum()
    rows = np.where(truth_row == 1, 0, np.where(truth_row == 0, 1, 2))
    exp = 0.0
    for a in range(L.shape[1]):
        x = w * L[rows, a]
        m = x.sum()
        if m > 0:
            exp += m * H(x / m)
    return H(w) - exp


def test_likelihood_rows_sum_to_one():
    assert np.allclose(likelihood_matrix().sum(1), 1)


def test_vectorised_ig_matches_brute_force():
    rng = np.random.default_rng(0)
    truth = rng.integers(-1, 2, size=(12, 30))
    w = rng.random(30); w /= w.sum()
    L = likelihood_matrix(0.3)
    _, ig, *_ = expected_info_gain(w, truth, L, gamma=1.0)
    for i in range(12):
        assert abs(ig[i] - brute_force_ig(w, truth[i], L)) < 1e-9


def test_perfect_split_beats_useless_and_unknown_questions():
    n = 8
    truth = [[1] * 4 + [0] * 4,        # perfect split
             [1] * 8,                  # constant
             [-1] * 8,                 # all unknown: no information
             [1, 0, 0, 0, 0, 0, 0, 0]]  # lopsided
    st = GameState(make_bank(truth))
    ranked = st.rank()
    assert ranked[0]["index"] == 0
    by = {r["index"]: r for r in ranked}
    assert by[2]["info_gain"] < 1e-9 and by[1]["info_gain"] < 1e-9


def test_unknown_fact_is_not_false():
    # entity 0 has an UNKNOWN fact: answering "no" must not eliminate it as hard as a TRUE fact would
    st = GameState(make_bank([[-1, 1, 0, 0]]))
    st.answer(0, "no")
    assert st.w[0] > st.w[1] * 5 and st.w[0] > 0


def test_dont_know_is_neutral():
    st = GameState(make_bank([[1, 0, 0, -1]]))
    before = st.w.copy()
    st.answer(0, "dont_know")
    assert np.allclose(st.w, before)


def test_probably_is_softer_than_yes():
    a, b = GameState(make_bank([[1, 0]])), GameState(make_bank([[1, 0]]))
    a.answer(0, "yes"); b.answer(0, "probably")
    assert b.w[1] > a.w[1] > 0


def test_game_converges_on_target_and_avoids_repeats(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "FAMILY_MAX", 10**6)   # toy bank = one family
    rng = np.random.default_rng(1)
    E, Q = 64, 40
    truth = rng.integers(0, 2, size=(Q, E))
    st = GameState(make_bank(truth), rng=random.Random(0))
    target = 17
    seen = set()
    for _ in range(Q):
        best = st.pick("info_gain")
        if best is None:
            break
        qid = st.bank.questions[best["index"]].id
        assert qid not in seen
        seen.add(qid)
        st.answer(best["index"], "yes" if truth[best["index"], target] else "no")
    assert st.top(1)[0][0] == target or np.all(truth[:, st.top(1)[0][0]] == truth[:, target])


def test_reject_removes_candidate():
    st = GameState(make_bank([[1, 0, 0]]))
    st.reject(1)
    assert st.w[1] == 0 and abs(st.w.sum() - 1) < 1e-12


def test_random_baseline_only_picks_informative():
    st = GameState(make_bank([[1, 1, 1, 1], [1, 0, 1, 0], [-1, -1, -1, -1]]), rng=random.Random(3))
    for _ in range(20):
        assert st.pick("random")["index"] == 1


def test_family_hard_cap(monkeypatch):
    from app import config
    monkeypatch.setattr(config, "FAMILY_MAX", 2)
    st = GameState(make_bank([[1, 0, 1, 0, 1, 0], [1, 1, 0, 0, 1, 0], [0, 1, 1, 0, 0, 1], [1, 0, 0, 1, 0, 1]]))
    st.answer(0, "yes"); st.answer(1, "yes")           # all four share one family in this toy bank
    assert st.rank() == []


def test_replay_equals_original_state():
    """Undo replays earlier answers on a fresh state; answers commute so the result must equal the state before the last answer."""
    rng = np.random.default_rng(5)
    bank = make_bank(rng.integers(-1, 2, size=(12, 40)))
    a = GameState(bank)
    seq = [(0, "yes"), (3, "no"), (7, "probably"), (2, "dont_know")]
    for i, ans in seq:
        a.answer(i, ans)
    b = GameState(bank)
    for i, ans in seq[:-1]:
        b.answer(i, ans)
    c = GameState(bank)
    for i, ans in reversed(seq[:-1]):               # order must not matter
        c.answer(i, ans)
    assert np.allclose(b.w, c.w)


# ------------------------------------------------------------------ what the five answers MEAN (calibrated answer model)
def _rows(unknown_prior=0.5, legacy=False):
    from app import engine
    return engine.likelihood_tensor(np.array([unknown_prior]), table=engine.LEGACY_LIKELIHOOD if legacy else engine.CALIBRATED_LIKELIHOOD)[0]   # rows TRUE, FALSE, UNKNOWN


def test_rows_are_distributions():
    from app import engine
    for t in (engine.LEGACY_LIKELIHOOD, engine.CALIBRATED_LIKELIHOOD):
        assert all(abs(sum(r) - 1) < 1e-9 for r in t.values())


def test_probably_favours_but_never_eliminates_the_opposite():
    L = _rows()
    yes_, prob, dk, pn, no = range(5)
    assert L[1, prob] / L[0, prob] >= 0.55, "'probably' must keep the FALSE candidates alive (>= 55% of a TRUE candidate's weight)"
    assert L[0, pn] / L[1, pn] >= 0.55, "'probably not' must keep the TRUE candidates alive"
    assert L[1, prob] / L[0, prob] > 0.3 and L[1, prob] / L[0, prob] > _rows(legacy=True)[1, prob] / _rows(legacy=True)[0, prob], "softer than the old model"
    assert L[0, prob] > L[1, prob] and L[1, pn] > L[0, pn], "still points in the right direction"
    assert L[1, yes_] / L[0, yes_] < 0.05 and L[0, no] / L[1, no] < 0.05, "definite answers stay decisive"


def test_dont_know_carries_no_information_for_any_truth_value():
    for up in (0.05, 0.5, 0.95):
        L = _rows(up)
        assert abs(L[0, 2] - L[1, 2]) < 1e-12 and abs(L[0, 2] - L[2, 2]) < 1e-12


def test_not_stated_in_the_graph_can_be_either():
    L = _rows(0.5)
    assert abs(L[2, 0] - L[2, 4]) < 1e-12, "for an entity whose fact is missing, 'yes' and 'no' must weigh the same"
    assert abs(L[2, 1] - L[2, 3]) < 1e-12
    for j in (0, 1, 3, 4):
        assert L[2, j] >= 0.4 * max(L[0, j], L[1, j]) * 0.5, "an unknown entity is never nearly eliminated by one answer"
    assert L[2, 0] / L[0, 0] > 0.4 and L[2, 4] / L[1, 4] > 0.4, "vs the candidate the answer favours, unknown keeps >= 40%"


def test_every_question_uses_the_neutral_unknown_prior():
    from app.questions import unknown_prior_true
    from app.questions import Question, QuerySpec, Path, Cond
    q = Question(id="x", text="Has your character eaten a Devil Fruit?", spec=QuerySpec(paths=[Path(start="Character", cond=Cond(kind="label", label="DevilFruitEater"), scope="positive")]))
    assert unknown_prior_true(q) == 0.5


def test_several_soft_answers_do_not_eliminate_a_candidate():
    st = GameState(make_bank([[1, 0, -1], [1, 0, -1], [1, 0, -1]]))
    for q in range(3):
        st.answer(q, "probably")
    assert st.w[1] / st.w[0] > 0.15, "after three 'probably' the FALSE candidate keeps > 15% of the TRUE one"
    assert st.w[2] / st.w[0] > 0.4, "and an unknown candidate stays close"
    st2 = GameState(make_bank([[1, 0, -1], [1, 0, -1], [1, 0, -1]]))
    for q in range(3):
        st2.answer(q, "probably_not")
    assert st2.w[0] / st2.w[1] > 0.15


def test_dont_know_never_changes_any_weight():
    st = GameState(make_bank([[1, 0, -1, 1], [0, 1, -1, 0]]))
    before = st.w.copy()
    st.answer(0, "dont_know"); st.answer(1, "dont_know")
    assert np.allclose(st.w, before)


# ------------------------------------------------------------------ "not listed" is weak evidence, definite falsehoods stay definite
def test_a_not_listed_false_is_not_eliminated_by_a_definite_yes():
    from app import engine
    soft = engine.likelihood_tensor(np.array([0.5]), table=engine.CALIBRATED_LIKELIHOOD, false_reliability=np.array([0.8]))[0]
    firm = engine.likelihood_tensor(np.array([0.5]), table=engine.CALIBRATED_LIKELIHOOD, false_reliability=np.array([0.98]))[0]
    old = engine.likelihood_tensor(np.array([0.5]), table=engine.CALIBRATED_LIKELIHOOD)[0]
    assert abs(sum(soft[1]) - 1) < 1e-9
    assert soft[1, 0] / soft[0, 0] > 0.15, "Shanks (captain not listed) keeps > 15% of a listed captain's weight when the player says yes"
    assert firm[1, 0] / firm[0, 0] < 0.08 and old[1, 0] / old[0, 0] < 0.05, "definite falsehoods (category, life status) still eliminate"
    assert soft[1, 4] > soft[1, 0], "and a 'no' still favours the not-listed candidate over a 'yes' would"


def test_reliability_by_scope():
    from app.questions import Cond, Path, Question, QuerySpec, Step, false_reliability
    mk_ = lambda scope, steps=(): Question(id="x", text="Is it a thing?", spec=QuerySpec(paths=[Path(start="Character", steps=list(steps), cond=Cond(kind="uri", uri="u") if steps else Cond(kind="exists"), scope=scope)]))
    assert false_reliability(mk_("rel:OCCUPATION", [Step(rel="OCCUPATION")])) == config.ABSENCE_RELIABILITY
    assert false_reliability(mk_("path", [Step(rel="A")])) == config.ABSENCE_RELIABILITY
    assert false_reliability(mk_("closed")) == config.DEFINITE_RELIABILITY
    assert false_reliability(mk_("status", [Step(rel="STATUS_OF_CHARACTER")])) == config.DEFINITE_RELIABILITY


def test_a_listed_miss_costs_less_than_before_but_still_counts():
    soft = GameState(make_bank([[1, 0]]))
    soft.bank.false_rel[0] = 0.8
    soft.answer(0, "yes")
    firm = GameState(make_bank([[1, 0]]))
    firm.bank.false_rel[0] = 0.98
    firm.answer(0, "yes")
    assert soft.w[1] > firm.w[1] > 0 and soft.w[0] > soft.w[1]


# ------------------------------------------------------------------ one missing fact must not be punished once per related question
def _soft_bank(rows):
    b = make_bank(rows)
    b.false_rel = [config.ABSENCE_RELIABILITY] * len(rows)
    return b


def test_related_contradictions_are_discounted():
    base = np.array([1, 1, 0, 0, 0, 0, 0, 0] * 5)                                 # 'captain': candidate 2.. lack it
    related = [base, base.copy(), base.copy(), base.copy()]                        # four re-wordings of the same fact
    st = GameState(_soft_bank(related))
    target = 2                                                                      # the player's character: graph says FALSE, player says yes (omission)
    assert st.bank.truth[0, target] == 0
    ratios = []
    for q in range(4):
        before_ratio = st.w[target] / st.w[0]
        st.answer(q, "yes")
        ratios.append((st.w[target] / st.w[0]) / before_ratio)
    assert ratios[0] < ratios[1] < ratios[2] < ratios[3] <= 1.0, ratios            # each repeat costs less than the first
    assert np.prod(ratios) > ratios[0] ** 4 * 5, "four related contradictions cost far less than four independent ones"


def test_unrelated_contradictions_are_not_discounted():
    rng = np.random.default_rng(11)
    rows = [rng.integers(0, 2, size=200) for _ in range(3)]
    for r in rows:
        r[0], r[1] = 1, 0                                                           # entity 0 TRUE everywhere, entity 1 FALSE everywhere
    st = GameState(_soft_bank(rows))
    ratios = []
    for q in range(3):
        before = st.w[1] / st.w[0]
        st.answer(q, "yes")
        ratios.append((st.w[1] / st.w[0]) / before)
    assert max(ratios) - min(ratios) < 0.05, ratios                                 # independent evidence: every contradiction costs the same


def test_definite_questions_are_never_discounted():
    base = np.array([1, 0] * 20)
    b = make_bank([base, base.copy()])                                              # false_rel stays 0.98 (definite)
    st = GameState(b)
    first = st.w[1] / st.w[0]
    st.answer(0, "yes"); r1 = (st.w[1] / st.w[0]) / first
    mid = st.w[1] / st.w[0]
    st.answer(1, "yes"); r2 = (st.w[1] / st.w[0]) / mid
    assert abs(r1 - r2) < 1e-9


# ------------------------------------------------------------------ another category's FALSE is definite; re-worded questions are not repeated
def test_a_question_about_another_category_eliminates_definitely():
    # entity 0: a character with the role, 1: a character without it (not listed), 2: a Devil Fruit (has no roles at all)
    b = Bank(["c_yes", "c_no", "fruit"])
    b.add(q(0), np.array([1, 0, 0], dtype=np.int8), np.array([False, False, True]))
    b.false_rel = [config.ABSENCE_RELIABILITY]
    st = GameState(b)
    st.answer(0, "yes")
    assert st.w[1] > 4 * st.w[2], "a not-listed character survives a 'yes', a Devil Fruit does not (definite level, like category questions)"


def test_a_rejected_listed_fact_is_costly_but_not_fatal():
    # the user's Luffy game: Luffy led with 54% when "Prisoner?" (listed for him: Impel Down) got a "no" and dropped him to 4%
    st = GameState(_soft_bank([[1, 0]]))
    st.answer(0, "no")
    assert 0.1 < st.w[0] / st.w[1] < 0.5


def test_reworded_questions_are_not_asked_again():
    from app.questions import Cond, Path, QuerySpec, Question, Step
    mk_ = lambda i, *paths: Question(id=f"c{i}", text=f"Concept question {i}?", spec=QuerySpec(paths=list(paths), mode="all" if len(paths) > 1 else "any"))
    lab = lambda l: Path(start="Character", cond=Cond(kind="label", label=l), scope="rel:OCCUPATION")
    role = lambda r: Path(start="Character", steps=[Step(rel="OCCUPATION")], cond=Cond(kind="uri", uri=config.OP + r), scope="rel:OCCUPATION")
    qs = [mk_(0, lab("CaptainCharacter")), mk_(1, lab("CaptainCharacter"), lab("PirateAffiliatedCharacter")), mk_(2, role("Pirate_Captain")),
          mk_(3, lab("PirateAffiliatedCharacter")), mk_(4, role("Pirate_Officer"))]
    rng = np.random.default_rng(2)
    b = Bank([f"e{j}" for j in range(60)])
    for x in qs:
        b.add(x, rng.integers(0, 2, size=60).astype(np.int8))
    st = GameState(b)
    st.answer(1, "no")                                        # "captain of a pirate crew?" no: still unclear which part failed
    assert {r["index"] for r in st.rank()} == {0, 2, 3, 4}
    st.answer(0, "yes"); st.answer(3, "yes")                  # captain and pirate both answered
    assert {r["index"] for r in st.rank()} == {4}, "Pirate Captain is a re-wording now; Pirate Officer is a refinement"
