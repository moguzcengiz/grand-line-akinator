"""Pure-numpy game engine: three-valued knowledge matrix, probabilistic updates, expected information gain.

No Neo4j / FastAPI imports -> fully unit-testable.
"""
import random
from dataclasses import dataclass, field

import numpy as np

from . import config

ANSWERS = ["yes", "probably", "dont_know", "probably_not", "no"]
TRUE, FALSE, UNKNOWN = 1, 0, -1

# P(answer | KB truth value of the fact).  Rows sum to 1; column order = ANSWERS = yes, probably, dont_know, probably_not, no.
#
# calibrated (default) - what the answers MEAN:
#   yes / no            strong evidence (a definite answer can still be a mistake: 2% mass on the opposite).
#   probably            "could well be yes": TRUE candidates are favoured 1.7x over FALSE ones (0.15 vs 0.09) - the FALSE ones are NOT eliminated,
#                       even after several soft answers (0.6^3 = 22% survive).  "probably not" is its mirror image.
#   don't know          carries NO information: the same likelihood for every candidate (0.04), whatever the graph says.
#   KB-unknown fact     "not stated in the graph" = it can be either: the row is the 50/50 mixture of TRUE and FALSE (see unknown_prior_true),
#                       so neither yes nor no eliminates the entity.
LEGACY_LIKELIHOOD = {TRUE: [0.82, 0.10, 0.03, 0.03, 0.02], FALSE: [0.02, 0.03, 0.03, 0.10, 0.82]}
CALIBRATED_LIKELIHOOD = {TRUE: [0.70, 0.15, 0.04, 0.09, 0.02], FALSE: [0.02, 0.09, 0.04, 0.15, 0.70]}


def likelihood_table() -> dict:
    return LEGACY_LIKELIHOOD if config.ANSWER_MODEL == "legacy" else CALIBRATED_LIKELIHOOD


DEFAULT_LIKELIHOOD = CALIBRATED_LIKELIHOOD


def likelihood_matrix(unknown_prior_true: float = 0.5, table=None) -> np.ndarray:
    """3x5 matrix, row order: TRUE, FALSE, UNKNOWN."""
    t = table or likelihood_table()
    u = [unknown_prior_true * a + (1 - unknown_prior_true) * b for a, b in zip(t[TRUE], t[FALSE])]
    return np.array([t[TRUE], t[FALSE], u], dtype=float)


def likelihood_tensor(unknown_prior_true: np.ndarray, table=None, false_reliability: np.ndarray | None = None) -> np.ndarray:
    """(Q,3,5): per-question likelihoods, rows TRUE / FALSE / UNKNOWN.
    UNKNOWN: P(fact is true | KB has no record) = unknown_prior_true (0.5 = "can be either").
    FALSE:   a graph FALSE that only means "absent from an incomplete list" is true with probability 1 - false_reliability, so its row is the
             mixture r * FALSE_row + (1 - r) * TRUE_row (r = 1 reproduces the old closed-world behaviour)."""
    t = table or likelihood_table()
    T, F = np.array(t[TRUE]), np.array(t[FALSE])
    p = np.asarray(unknown_prior_true, dtype=float)
    r = np.ones_like(p) if false_reliability is None else np.asarray(false_reliability, dtype=float)
    unknown = p[:, None] * T[None, :] + (1 - p)[:, None] * F[None, :]
    false_row = r[:, None] * F[None, :] + (1 - r)[:, None] * T[None, :]
    true_row = np.broadcast_to(T, (len(p), 5))
    return np.stack([true_row, false_row, unknown], axis=1)


def _row(truth: np.ndarray) -> np.ndarray:
    """Map truth values {1,0,-1} to likelihood-matrix row indices {0,1,2}."""
    return np.where(truth == TRUE, 0, np.where(truth == FALSE, 1, 2))


@dataclass
class Bank:
    """Entities x questions knowledge base. truth[q, e] in {1, 0, -1}."""
    entity_uris: list[str]
    questions: list = field(default_factory=list)
    truth: np.ndarray = None
    index: dict = field(default_factory=dict)
    unknown_prior: list = field(default_factory=list)   # P(true | unknown) per question
    false_rel: list = field(default_factory=list)       # P(graph FALSE is really false) per question
    prior: np.ndarray | None = None          # None = uniform
    families: list = field(default_factory=list)
    topics: list = field(default_factory=list)

    def __post_init__(self):
        if self.truth is None:
            self.truth = np.zeros((0, len(self.entity_uris)), dtype=np.int8)

    def add(self, question, truth_row: np.ndarray) -> int:
        if question.id in self.index:
            return self.index[question.id]
        from .questions import false_reliability, family, topic, unknown_prior_true
        self.false_rel.append(false_reliability(question))
        self.families.append(family(question))
        self.topics.append(topic(question))
        self.unknown_prior.append(unknown_prior_true(question))
        self.index[question.id] = len(self.questions)
        self.questions.append(question)
        self.truth = np.vstack([self.truth, truth_row.astype(np.int8)[None, :]])
        return self.index[question.id]


def expected_info_gain(w: np.ndarray, truth: np.ndarray, L: np.ndarray, gamma: float = 1.0):
    """Vectorised expected entropy reduction for every question row of `truth`.

    w: normalised candidate weights (E,).  L: (Q,3,5) per-question likelihoods (or one shared (3,5) matrix).
    Returns (score, ig, coverage, p_true, p_false, p_unknown), each shape (Q,).
    IG = H(w) - sum_a P(a) H(w | a), exact under the answer model (5 answers incl. "don't know").
    score = IG * coverage**gamma where coverage = 1 - P(unknown): low-coverage questions are penalised.
    """
    if L.ndim == 2:
        L = np.broadcast_to(L, (truth.shape[0],) + L.shape)
    wlogw = np.where(w > 0, w * np.log(np.where(w > 0, w, 1)), 0.0)
    H = -wlogw.sum()
    masks = [truth == TRUE, truth == FALSE, truth == UNKNOWN]
    P = np.stack([(m * w).sum(1) for m in masks], 1)           # (Q,3) mass per truth class
    S = np.stack([(m * wlogw).sum(1) for m in masks], 1)       # (Q,3) sum w log w per truth class
    exp_post = np.zeros(truth.shape[0])
    for a in range(L.shape[2]):
        la = L[:, :, a]                                         # (Q,3)
        mass = (P * la).sum(1)                                  # P(answer a)
        xlogx = (la * S + P * la * np.log(la)).sum(1)           # sum x log x with x = w * likelihood
        with np.errstate(divide="ignore", invalid="ignore"):
            h_a = np.where(mass > 0, np.log(np.where(mass > 0, mass, 1)) - xlogx / np.where(mass > 0, mass, 1), 0.0)
        exp_post += mass * h_a
    ig = np.maximum(H - exp_post, 0.0)
    coverage = 1.0 - P[:, 2]
    return ig * coverage ** gamma, ig, coverage, P[:, 0], P[:, 1], P[:, 2]


class GameState:
    """One game: candidate weights, asked questions, answers, prediction state."""

    def __init__(self, bank: Bank, likelihood: np.ndarray | None = None, rng: random.Random | None = None):
        self.bank = bank
        self.L_override = likelihood            # a shared (3,5) matrix, mainly for tests
        self.w = bank.prior / bank.prior.sum() if bank.prior is not None else np.ones(len(bank.entity_uris)) / len(bank.entity_uris)
        self.prior0 = self.w.copy()
        self.asked: list[dict] = []
        self.asked_ids: set[str] = set()
        self.rng = rng or random.Random()
        self.last_phase = "discovery"                                    # see policy.phase_of (hysteresis)
        self.rejected: list[int] = []                                    # entity indices ruled out by guess feedback
        self.guesses = 0

    def _L(self, idx):
        if self.L_override is not None:
            return self.L_override
        return likelihood_tensor(np.array([self.bank.unknown_prior[i] for i in idx]), false_reliability=np.array([self.bank.false_rel[i] for i in idx]))

    # ---- ranking
    def rank(self, extra_exclude=(), family_max: int | None = None) -> list[dict]:
        used: dict = {}
        for a in self.asked:
            f = self.bank.families[a["index"]]
            used[f] = used.get(f, 0) + 1
        idx = [i for i, q in enumerate(self.bank.questions) if q.id not in self.asked_ids and q.id not in extra_exclude
               and used.get(self.bank.families[i], 0) < (config.FAMILY_MAX if family_max is None else family_max)]
        if not idx:
            return []
        score, ig, cov, pt, pf, pu = expected_info_gain(self.w, self.bank.truth[idx], self._L(idx), config.COVERAGE_GAMMA)
        # diminishing returns for asking the same kind of question again and again
        score = score * np.array([config.FAMILY_DECAY ** used.get(self.bank.families[i], 0) for i in idx])
        order = np.argsort(-score)
        return [{"index": idx[j], "score": float(score[j]), "info_gain": float(ig[j]), "coverage": float(cov[j]),
                 "p_yes": float(pt[j]), "p_no": float(pf[j]), "p_unknown": float(pu[j])} for j in order]

    def pick(self, strategy: str = "info_gain", ranked: list[dict] | None = None) -> dict | None:
        ranked = ranked if ranked is not None else self.rank()
        informative = [r for r in ranked if r["info_gain"] > 1e-6]
        if not informative:
            return None
        if strategy == "random":                                       # evaluation baseline: any question that splits the candidates
            return self.rng.choice(informative)
        return informative[0]

    # ---- update
    def answer(self, q_index: int, answer: str):
        a = ANSWERS.index(answer)
        rows = _row(self.bank.truth[q_index])
        L = self._L([q_index])[0] if self.L_override is None else self.L_override
        factor = L[rows, a].astype(float)
        factor, contra = self._discount_correlated_contradictions(q_index, a, rows, factor, L)
        before = self.w.copy()
        self.w = self.w * factor
        s = self.w.sum()
        if s <= 0:                                                     # every candidate contradicted: restart from the prior
            self.w = self.prior0.copy()
        else:
            self.w /= s
        q = self.bank.questions[q_index]
        self.asked.append({"question_id": q.id, "answer": answer, "index": q_index, "factor": factor, "contra": contra})
        self.asked_ids.add(q.id)
        return before

    def _discount_correlated_contradictions(self, q_index, a, rows, factor, L):
        """One missing / wrong graph fact often contradicts the player in several RELATED questions (captain / pirate captain / pirate role ...).
        Only 'not listed' style questions (false_rel below the definite level) are discounted; definite facts (category, life status) keep their full weight."""
        yes_like, no_like = a in (0, 1), a in (3, 4)
        truth = self.bank.truth[q_index]
        soft = self.bank.false_rel[q_index] < config.DEFINITE_RELIABILITY - 1e-9
        if not soft or not (yes_like or no_like):
            return factor, np.zeros(len(factor), dtype=bool)
        contra = (truth == FALSE) if yes_like else (truth == TRUE)
        if not contra.any() or not self.asked:
            return factor, contra
        from .policy import weighted_phi
        prev = [x for x in self.asked if x.get("contra") is not None and x["contra"].any()]
        if prev:
            phi = weighted_phi(self.bank.truth[[x["index"] for x in prev]], self.bank.truth[q_index], self.prior0)
            k = np.zeros(len(factor))
            for x, ph in zip(prev, phi):
                if ph >= config.RELATED_PHI:
                    k += x["contra"]
            ref = L[0 if yes_like else 1, a]                         # likelihood of a candidate that agrees with the answer
            ratio = np.clip(factor / ref, 1e-9, 1.0)
            discounted = ref * ratio ** (config.CONTRADICTION_DISCOUNT ** k)
            factor = np.where(contra & (k > 0), discounted, factor)
        return factor, contra

    def reject(self, entity_index: int):
        self.rejected.append(entity_index)
        self.w[entity_index] = 0
        s = self.w.sum()
        self.w = self.w / s if s > 0 else np.ones_like(self.w) / len(self.w)
        self.guesses += 1

    # ---- readout
    def top(self, k=5) -> list[tuple[int, float]]:
        order = np.argsort(-self.w)[:k]
        return [(int(i), float(self.w[i])) for i in order]

    def remaining(self) -> int:
        return int((self.w >= self.w.max() * config.REMAINING_RATIO).sum())

    def should_guess(self) -> bool:
        n = len(self.asked)
        if n < config.MIN_QUESTIONS:
            return False
        return self.w.max() >= config.STOP_CONFIDENCE or n >= config.MAX_QUESTIONS or self.remaining() <= 1
