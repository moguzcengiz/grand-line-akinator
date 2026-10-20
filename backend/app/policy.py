"""Multi-objective question policy: score -> top-k -> seeded softmax sample.  Pure numpy (unit-testable, no Neo4j).

Replaces "always ask the argmax-information-gain question" (which made every game open identically) by

    score(q) = sum_c  W[phase][c] * norm_c(q)        c in  info, coverage, novelty, diversity, specificity, repetition, complexity

* every component is min-max normalised over the *valid* candidate questions before weighting (no component dominates by scale);
* valid = discriminative (information gain >= GATE_REL * best) and not a semantic duplicate of an asked question (|phi| < EQUIV_PHI);
  a question with no discriminative value is therefore never selectable, whatever the temperature;
* the question is sampled from the top-k by softmax(score / T) with a per-session seeded RNG; T = 0 (or deterministic mode) = argmax.
The phase (discovery / investigation / deduction) is derived from candidate entropy and confidence, not from the question number.
"""
import math
import random
from dataclasses import dataclass, field

import numpy as np

from . import config
from .questions import complexity, topic

COMPONENTS = ["info", "coverage", "novelty", "diversity", "specificity", "repetition", "complexity"]
PHASES = ["discovery", "investigation", "deduction"]
PHASE_LABEL = {"discovery": "Scouting the seas", "investigation": "Following the trail", "deduction": "Closing in"}
# the yes-mass a question should ideally have in each phase: broad questions first, sharply discriminating ones at the end
SPECIFICITY_TARGET = {"discovery": 0.5, "investigation": 0.75, "deduction": 0.9}

# Phase-dependent weights (each row sums to 1).  Defaults were chosen with app/policy_eval.py (ablation + temperature sweep), see docs/POLICY.md.
WEIGHTS: dict[str, dict[str, float]] = {
    "discovery":     {"info": 0.40, "coverage": 0.10, "novelty": 0.10, "diversity": 0.20, "specificity": 0.10, "repetition": 0.05, "complexity": 0.05},
    "investigation": {"info": 0.50, "coverage": 0.10, "novelty": 0.10, "diversity": 0.10, "specificity": 0.10, "repetition": 0.05, "complexity": 0.05},
    "deduction":     {"info": 0.70, "coverage": 0.10, "novelty": 0.10, "diversity": 0.00, "specificity": 0.05, "repetition": 0.05, "complexity": 0.00},
}


def entropy_bits(w: np.ndarray) -> float:
    p = w[w > 0]
    return float(-(p * np.log2(p)).sum())


_ORDER = {"discovery": 0, "investigation": 1, "deduction": 2}


def phase_of(state, commit: bool = False) -> tuple[str, dict]:
    """Phase from the posterior itself: remaining entropy fraction, top confidence and how many candidates are still alive.

    Hysteresis keeps the label from flickering when a contradictory answer widens the posterior: discovery is never re-entered, and
    deduction is only left when the candidate pool has really re-opened (three times the deduction size, or entropy fraction above 0.66)."""
    h0 = max(entropy_bits(state.prior0), 1e-9)
    frac = entropy_bits(state.w) / h0
    top, remaining = float(state.w.max()), state.remaining()
    metrics = {"entropy_fraction": round(frac, 3), "top_probability": round(top, 3), "remaining": remaining}
    if remaining <= config.DEDUCTION_REMAINING or top >= config.DEDUCTION_TOP_P or frac <= config.DEDUCTION_ENTROPY_FRAC:
        phase = "deduction"
    elif frac >= config.DISCOVERY_ENTROPY_FRAC and top < 0.10:
        phase = "discovery"
    else:
        phase = "investigation"
    prev = getattr(state, "last_phase", "discovery")
    if _ORDER[phase] < _ORDER[prev]:
        reopened = remaining > 3 * config.DEDUCTION_REMAINING or frac > 2.2 * config.DEDUCTION_ENTROPY_FRAC
        phase = prev if (prev == "investigation" or not reopened) else "investigation"
    if commit:
        state.last_phase = phase
    return phase, metrics


def weighted_phi(rows: np.ndarray, ref: np.ndarray, w: np.ndarray) -> np.ndarray:
    """|phi coefficient| between each candidate row (Q,E) and a reference row (E,), over entities where BOTH are known (weights w)."""
    known = (rows != -1) & (ref != -1)[None, :]
    wm = known * w[None, :]
    tot = wm.sum(1)
    a = (rows == 1)
    b = (ref == 1)[None, :]
    with np.errstate(divide="ignore", invalid="ignore"):
        pa, pb = (wm * a).sum(1) / tot, (wm * b).sum(1) / tot
        p11 = (wm * a * b).sum(1) / tot
        phi = (p11 - pa * pb) / np.sqrt(pa * (1 - pa) * pb * (1 - pb))
    return np.nan_to_num(np.abs(phi), nan=0.0, posinf=0.0)


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(x.min()), float(x.max())
    return np.full_like(x, 0.5, dtype=float) if hi - lo < 1e-12 else (x - lo) / (hi - lo)


@dataclass
class Scored:
    index: int
    score: float
    components: dict
    topic: str
    info_gain: float
    coverage: float
    p_yes: float
    p_no: float
    p_unknown: float
    ranked: dict = field(repr=False, default_factory=dict)


def score_questions(state, ranked: list[dict], phase: str, weights: dict | None = None, gate_rel: float | None = None, equiv: float | None = None) -> list[Scored]:
    """Score every informative, non-duplicate question. Returns Scored sorted by descending score."""
    bank = state.bank
    informative = [r for r in ranked if r["info_gain"] > 1e-6]
    if not informative:
        return []
    # 1) drop semantic duplicates of already asked questions FIRST: an equivalent of a "don't know"-ed question keeps its high information gain
    #    but can never be asked, so it must not set the bar for the gate (that used to leave NO question in ~1 of 3 games)
    asked_idx = [a["index"] for a in state.asked]
    idx_all = np.array([r["index"] for r in informative])
    max_phi_all = np.zeros(len(informative))
    for ai in asked_idx:
        max_phi_all = np.maximum(max_phi_all, weighted_phi(bank.truth[idx_all], bank.truth[ai], state.prior0))
    fresh = [(r, m) for r, m in zip(informative, max_phi_all) if m < (config.EQUIV_PHI if equiv is None else equiv)]
    if not fresh:
        return []
    # 2) only now compare with the best question that can actually be asked
    best_ig = max(r["info_gain"] for r, _ in fresh)
    kept = [(r, m) for r, m in fresh if r["info_gain"] >= (config.GATE_REL if gate_rel is None else gate_rel) * best_ig]
    valid = [r for r, _ in kept]
    max_phi = np.array([m for _, m in kept])

    recent = [bank.topics[a["index"]] for a in state.asked[-config.RECENT_WINDOW:]]
    fam_used: dict = {}
    for a in state.asked:
        f = bank.families[a["index"]]
        fam_used[f] = fam_used.get(f, 0) + 1
    target = SPECIFICITY_TARGET[phase]
    raw = {
        "info": np.array([r["info_gain"] for r in valid]),
        "coverage": np.array([r["coverage"] for r in valid]),
        "novelty": 1.0 - max_phi,
        "diversity": np.array([config.TOPIC_DECAY ** recent.count(bank.topics[r["index"]]) for r in valid]),
        "specificity": np.array([1.0 - abs((1.0 - r["p_yes"]) - target) for r in valid]),
        "repetition": np.array([config.FAMILY_DECAY ** fam_used.get(bank.families[r["index"]], 0) for r in valid]),
        "complexity": np.array([1.0 - min(1.0, complexity(bank.questions[r["index"]]) / 6.0) for r in valid]),
    }
    norm = {c: _minmax(v) for c, v in raw.items()}
    W = (weights or WEIGHTS)[phase]
    total = sum(norm[c] * W[c] for c in COMPONENTS)
    out = [Scored(index=r["index"], score=float(total[i]), components={c: round(float(norm[c][i]), 3) for c in COMPONENTS}, topic=bank.topics[r["index"]],
                  info_gain=r["info_gain"], coverage=r["coverage"], p_yes=r["p_yes"], p_no=r["p_no"], p_unknown=r["p_unknown"], ranked=r)
           for i, r in enumerate(valid)]
    out.sort(key=lambda s: -s.score)
    return out


def sample(scored: list[Scored], rng: random.Random, temperature: float, top_k: int) -> Scored:
    """Seeded softmax over the top-k.  temperature <= 0 -> argmax (deterministic mode)."""
    if temperature <= 0 or len(scored) == 1:
        return scored[0]
    cand = scored[:top_k]
    s = np.array([c.score for c in cand])
    p = np.exp((s - s.max()) / temperature)
    p /= p.sum()
    return cand[rng.choices(range(len(cand)), weights=p.tolist())[0]]


def choose(state, ranked: list[dict], rng: random.Random, temperature: float | None = None, top_k: int | None = None,
           weights: dict | None = None, relax: bool = False) -> tuple[Scored | None, str, list[Scored], dict]:
    """-> (chosen, phase, all scored, phase metrics).  relax=True widens the gates (last resort when nothing else is left to ask)."""
    phase, metrics = phase_of(state, commit=True)
    scored = score_questions(state, ranked, phase, weights, gate_rel=0.05 if relax else None, equiv=0.995 if relax else None)
    if not scored:
        return None, phase, [], metrics
    T = config.TEMPERATURE if temperature is None else temperature
    return sample(scored, rng, T * config.PHASE_TEMP_SCALE[phase], top_k or config.TOP_K), phase, scored, metrics


# ---------------------------------------------------------------- short contextual reactions (deterministic fallback; the LLM may replace them)
def reaction_for(answer: str, bits_gained: float, phase: str, remaining: int) -> str:
    if answer == "dont_know":
        return "No worries — let's try another angle."
    if bits_gained >= 1.5:
        return "Now that narrows things down a lot!"
    if bits_gained >= 0.6:
        return "Interesting… that rules out a good crowd."
    if phase == "deduction":
        return "Getting closer — only a few suspects left."
    if answer in ("probably", "probably_not"):
        return "A cautious answer — I'll weigh it carefully."
    return "Noted. The trail is still wide open."
