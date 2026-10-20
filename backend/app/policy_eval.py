"""Adaptive vs deterministic question policy: accuracy, length, variety and redundancy on IDENTICAL targets and seeds.

    python -m app.policy_eval --games 200 --out eval_results/policy_eval.json         # main comparison
    python -m app.policy_eval --sweep --games 100 --out eval_results/policy_sweep.json  # weight ablation + temperature grid
"""
import argparse
import itertools
import json
import math
import random
import statistics
from collections import Counter
from pathlib import Path

import numpy as np

from . import config, policy, service
from .evaluation import STRATEGIES, play, summarize
from .policy import COMPONENTS, WEIGHTS
from .questions import family


def entropy_of(counts: Counter) -> float:
    n = sum(counts.values())
    return -sum(c / n * math.log2(c / n) for c in counts.values()) if n else 0.0


def session_metrics(kb, game: dict, phi_cache: dict) -> dict:
    asked = game["asked"]
    topics = [kb.bank.topics[i] for i in asked]
    fams = [kb.bank.families[i] for i in asked]
    repeat_family = sum(1 for k, f in enumerate(fams) if f in fams[:k])
    first8 = topics[:8]
    # semantically equivalent pairs: |phi| >= 0.9 on the (prior-weighted) answers of ALL entities
    equiv = 0
    for a, b in itertools.combinations(asked, 2):
        key = (min(a, b), max(a, b))
        if key not in phi_cache:
            phi_cache[key] = float(policy.weighted_phi(kb.bank.truth[a][None, :], kb.bank.truth[b], kb.bank.prior if kb.bank.prior is not None else np.ones(len(kb.uris)))[0])
        equiv += phi_cache[key] >= 0.9
    pairs = max(1, len(asked) * (len(asked) - 1) // 2)
    return {"distinct_topics_first8": len(set(first8)), "topic_entropy": entropy_of(Counter(topics)), "family_repeat_rate": repeat_family / max(1, len(asked)),
            "equivalent_pair_rate": equiv / pairs, "has_equivalent_pair": equiv > 0}


def run(kb, name: str, targets: list[int], seed0: int, noise: float = 0.0, seeds_per_target: int = 1) -> list[dict]:
    mode, strategy, expl = STRATEGIES[name]
    games = []
    for k, t in enumerate(targets):
        for s in range(seeds_per_target):
            seed = seed0 + k * 1000 + s
            g = play(kb, t, mode, strategy, random.Random(seed), noise, seed=seed, exploration=expl)
            g["target_idx"], g["seed"] = t, seed
            games.append(g)
    return games


def report(kb, name: str, games: list[dict]) -> dict:
    cache: dict = {}
    sm = [session_metrics(kb, g, cache) for g in games]
    openings = Counter(g["asked"][0] for g in games if g["asked"])
    by_target: dict[int, list[dict]] = {}
    for g in games:
        by_target.setdefault(g["target_idx"], []).append(g)
    jac, distinct_open = [], []
    for gs in by_target.values():
        distinct_open.append(len({g["asked"][0] for g in gs}))
        for a, b in itertools.combinations(gs, 2):
            A, B = set(a["asked"]), set(b["asked"])
            jac.append(1 - len(A & B) / max(1, len(A | B)))
    out = summarize([{k: v for k, v in g.items()} for g in games])
    out.update({
        "policy": name,
        "opening_distinct_overall": len(openings), "opening_entropy_bits": round(entropy_of(openings), 2),
        "opening_distinct_per_target": round(statistics.mean(distinct_open), 2) if distinct_open else 0,
        "same_target_question_set_distance": round(statistics.mean(jac), 3) if jac else 0.0,
        "distinct_topics_first8": round(statistics.mean(m["distinct_topics_first8"] for m in sm), 2),
        "topic_entropy_bits": round(statistics.mean(m["topic_entropy"] for m in sm), 2),
        "family_repeat_rate": round(statistics.mean(m["family_repeat_rate"] for m in sm), 3),
        "equivalent_pair_rate": round(statistics.mean(m["equivalent_pair_rate"] for m in sm), 4),
        "sessions_with_equivalent_pair": round(statistics.mean(m["has_equivalent_pair"] for m in sm), 3),
        "top_openings": [(kb.bank.questions[i].text, c) for i, c in openings.most_common(4)]})
    return out


def line(r: dict) -> str:
    return (f"{r['policy']:<22} top1 {r['top1_accuracy']:.1%} | <=3 guesses {r['found_within_3_guesses']:.1%} | avgQ {r['avg_questions']} med {r['median_questions']} | "
            f"openings {r['opening_distinct_overall']} (H={r['opening_entropy_bits']}b, {r['opening_distinct_per_target']}/target) | set-dist {r['same_target_question_set_distance']} | "
            f"topics@8 {r['distinct_topics_first8']} H={r['topic_entropy_bits']} | repeat-fam {r['family_repeat_rate']} equiv-pairs {r['equivalent_pair_rate']} ({r['sessions_with_equivalent_pair']:.0%} sess) | "
            f"unk {r['unknown_answer_rate']:.1%} | {r['latency_ms_mean']}/{r['latency_ms_p95']}ms")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=200)
    ap.add_argument("--targets", default="eval_results/targets-popularity.json")
    ap.add_argument("--seeds-per-target", type=int, default=1)
    ap.add_argument("--variety-targets", type=int, default=20)
    ap.add_argument("--variety-seeds", type=int, default=10)
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--sweep-phase", action="store_true", help="per-phase temperature scale grid")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="eval_results/policy_eval.json")
    a = ap.parse_args()
    kb = service.get_kb()
    by_name = {e["name"]: i for i, e in enumerate(kb.entities)}
    names = json.loads(Path(a.targets).read_text())
    targets = [by_name[n] for n in names[:a.games]]
    res: dict = {"games": len(targets), "targets_file": a.targets, "seed": a.seed}
    if a.sweep_phase:
        print("== per-phase temperature scale (discovery, investigation, deduction), base T =", config.TEMPERATURE)
        res["phase_scale"] = {}
        saved = dict(config.PHASE_TEMP_SCALE)
        for sc in ((1, 1, 1), (2, 1, 0), (2.5, 1, 0), (2.5, 1, 0.5), (4, 1, 0), (4, 0.5, 0), (6, 0.5, 0)):
            config.PHASE_TEMP_SCALE.update(dict(zip(("discovery", "investigation", "deduction"), sc)))
            r = report(kb, "adaptive", run(kb, "adaptive", targets, a.seed, seeds_per_target=a.seeds_per_target)); r["policy"] = str(sc); res["phase_scale"][str(sc)] = r; print(line(r))
        config.PHASE_TEMP_SCALE.update(saved)
    elif not a.sweep:
        print(f"== identical {len(targets)} targets, identical seeds")
        for name in ("random", "ig", "adaptive_det", "adaptive"):
            res[name] = report(kb, name, run(kb, name, targets, a.seed)); print(line(res[name]))
        vt = targets[:a.variety_targets]
        print(f"== same target, {a.variety_seeds} different seeds ({len(vt)} targets): does the sequence vary, and does it still find the target?")
        for name in ("ig", "adaptive"):
            res[f"variety_{name}"] = report(kb, name, run(kb, name, vt, a.seed, seeds_per_target=a.variety_seeds)); print(line(res[f"variety_{name}"]))
    else:
        print("== temperature grid (adaptive, identical targets/seeds)")
        saved_t = config.TEMPERATURE
        res["temperature"] = {}
        for T in (0.0, 0.03, 0.06, 0.10, 0.20, 0.40):
            config.TEMPERATURE = T
            r = report(kb, "adaptive", run(kb, "adaptive", targets, a.seed)); r["policy"] = f"T={T}"; res["temperature"][str(T)] = r; print(line(r))
        config.TEMPERATURE = 0.0
        print("== component ablation at T=0 (drop one component from every phase, renormalise)")
        res["ablation"] = {}
        full = {ph: dict(w) for ph, w in WEIGHTS.items()}
        for drop in [None] + COMPONENTS:
            for ph in WEIGHTS:
                w = dict(full[ph])
                if drop:
                    w[drop] = 0.0
                tot = sum(w.values()) or 1.0
                WEIGHTS[ph].update({c: v / tot for c, v in w.items()})
            r = report(kb, "adaptive_det", run(kb, "adaptive_det", targets, a.seed)); r["policy"] = f"-{drop}" if drop else "full"; res["ablation"][drop or "full"] = r; print(line(r))
        for ph in WEIGHTS:
            WEIGHTS[ph].update(full[ph])
        config.TEMPERATURE = saved_t
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2, default=str))


if __name__ == "__main__":
    main()
