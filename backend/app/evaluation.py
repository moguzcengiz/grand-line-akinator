"""Reproducible evaluation: simulated games against known entities with fixed seeds.

    python -m app.evaluation --games 100 --seed 42 --pool rich --modes random,rule,ai --ai-games 20

Simulated player answers from the knowledge graph: TRUE->yes, FALSE->no, UNKNOWN->"don't know" (optionally with
--noise: a fraction of definite answers is softened to probably / probably_not).
"""
import argparse
import json
import random
import statistics
import time
from pathlib import Path

import numpy as np

from . import config, service
from .questions import omission_prone

# name -> (mode, strategy, exploration).  "rule"/"ig" = the old deterministic information-gain policy (baseline).
STRATEGIES = {"random": ("rule", "random", "off"), "rule": ("rule", "info_gain", "off"), "ig": ("rule", "info_gain", "off"),
              "adaptive_det": ("rule", "adaptive", "off"), "adaptive": ("rule", "adaptive", "medium"), "ai": ("ai", "adaptive", "medium")}


def simulated_answer(truth: int, rng: random.Random, noise: float, mismatch: float = 0.0, omission: float = 0.0) -> str:
    """truth: KB value.  noise: share of definite answers softened to probably / probably_not (an unsure player).
    mismatch: share of KNOWN cells where the player's real-world answer differs from the graph (knowledge gaps, wording, memory)."""
    if truth == -1:
        return "dont_know"
    if mismatch and rng.random() < mismatch:
        truth = 1 - truth
    if omission and truth == 0 and rng.random() < omission:     # the fact is true in the real world but missing from the graph
        truth = 1
    a = "yes" if truth == 1 else "no"
    if noise and rng.random() < noise:
        return "probably" if truth == 1 else "probably_not"
    return a


def play(kb, target_idx: int, mode: str, strategy: str, rng: random.Random, noise: float, seed: int | None = None, exploration: str = "off", mismatch: float = 0.0, omission: float = 0.0) -> dict:
    sess = service.start(mode, strategy, register=False, seed=seed, exploration=exploration)
    if strategy == "random":
        sess.state.rng = rng
    answers, guesses, first_guess, first_q = [], 0, None, None
    while True:                                   # like a real player: a wrong guess -> "not quite" -> the game keeps asking (max 3 guesses)
        while sess.status == "asking" and sess.current:
            best = sess.current["best"]
            # omissions only exist where a graph FALSE just means "not listed" (never for a question about another category)
            q = kb.bank.questions[best["index"]]
            truth = int(kb.bank.truth[best["index"], target_idx])
            if truth == 0 and omission and omission_prone(q) and kb.entities[target_idx]["category"] in {p.start for p in q.spec.paths}:
                # a missing fact is missing for every re-wording of it: one draw per (target, group of questions the ontology says are the
                # same, implications.same), so "Pirate?" and "affiliated with a pirate crew?" agree
                imp = kb.bank.imp
                key = min(imp.ctx[None].same[best["index"]] | {best["index"]}) if imp is not None else best["index"]
                truth = int(random.Random(f"{target_idx}|{key}").random() < omission)
            a = simulated_answer(truth, rng, noise, mismatch)
            answers.append(a)
            service.answer(sess, a, None)
        guess = sess.prediction_idx if sess.prediction_idx is not None else sess.state.top(1)[0][0]
        guesses += 1
        if first_guess is None:
            first_guess, first_q = guess, len(answers)
        if guess == target_idx or guesses >= 3 or sess.status != "guessing":
            break
        service.feedback(sess, False)
    pred = first_guess
    llm = sess.llm
    return {"target": kb.entities[target_idx]["name"], "predicted": kb.entities[pred]["name"], "correct": pred == target_idx,
            "questions": first_q, "total_questions": len(answers), "found_within_3": guess == target_idx, "guesses": guesses, "unknown_answers": answers.count("dont_know"), "select_ms": sess.select_ms,
            "asked": [a["index"] for a in sess.state.asked], "llm_totals": sess.llm_totals, "llm_proposed": llm.proposed if llm else 0, "llm_accepted": llm.accepted if llm else 0,
            "llm_used": bool(llm and llm.used)}


def pool(kb, kind: str, rng: random.Random, n: int, dist: str = "uniform", load: list[str] | None = None) -> tuple[list[int], dict]:
    """Target pool defined from the GRAPH only (never from the question bank, so it is stable across code changes):
    all = every entity; documented = graph popularity >= 12 (about 430 entities: well-described characters, fruits, ships)."""
    T = kb.bank.truth
    unique_cols = {}
    for j in range(T.shape[1]):
        unique_cols.setdefault(T[:, j].tobytes(), []).append(j)
    identifiable = {j for cols in unique_cols.values() if len(cols) == 1 for j in cols}
    idxs = [j for j in range(T.shape[1]) if kind == "all" or kb.entities[j]["popularity"] >= 12]
    meta = {"pool": kind, "pool_size": len(idxs), "identifiable_fraction": round(sum(j in identifiable for j in idxs) / max(len(idxs), 1), 3), "target_dist": dist}
    if load is not None:                                   # pinned targets: identical conditions across code/data versions
        by_name = {e["name"]: i for i, e in enumerate(kb.entities)}
        return [by_name[nm] for nm in load[:n]], {**meta, "targets": "loaded"}
    if dist == "popularity":                               # humans mostly think of well-known entities
        w = np.array([1.0 + kb.entities[j]["popularity"] for j in idxs])
        picked = list(dict.fromkeys(rng.choices(idxs, weights=w, k=n * 4)))[:n]
    else:
        picked = rng.sample(idxs, min(n, len(idxs)))
    return picked, meta


def summarize(games: list[dict]) -> dict:
    qs = [g["questions"] for g in games]                      # questions until the FIRST guess
    ms = [m for g in games for m in g["select_ms"]]
    tot = {"calls": 0, "cache_hits": 0, "failures": 0, "proposed": 0, "accepted": 0, "rejected": {}}
    for g in games:
        t = g.get("llm_totals") or {}
        for k in ("calls", "cache_hits", "failures", "proposed", "accepted"):
            tot[k] += t.get(k, 0)
        for k, v in (t.get("rejected") or {}).items():
            tot["rejected"][k] = tot["rejected"].get(k, 0) + v
    proposed = tot["proposed"]
    total_q = sum(g["total_questions"] for g in games)
    return {
        "games": len(games),
        "top1_accuracy": round(sum(g["correct"] for g in games) / len(games), 3),
        "avg_questions": round(statistics.mean(qs), 2), "median_questions": statistics.median(qs),
        "found_within_3_guesses": round(sum(g["found_within_3"] for g in games) / len(games), 3),
        "avg_total_questions_with_retries": round(statistics.mean(g["total_questions"] for g in games), 2),
        "unknown_answer_rate": round(sum(g["unknown_answers"] for g in games) / max(total_q, 1), 3),
        "question_validity_rate": round(tot["accepted"] / proposed, 3) if proposed else 1.0,
        "llm_proposals": proposed, "llm_totals": tot, "llm_calls_ok": sum(g["llm_used"] for g in games),
        "latency_ms_mean": round(statistics.mean(ms), 1) if ms else 0, "latency_ms_p95": round(float(np.percentile(ms, 95)), 1) if ms else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--games", type=int, default=100)
    ap.add_argument("--ai-games", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pool", choices=["all", "documented"], default="documented")
    ap.add_argument("--save-targets", help="write the sampled target names to this json file")
    ap.add_argument("--load-targets", help="replay exactly these targets (identical conditions)")
    ap.add_argument("--target-dist", choices=["uniform", "popularity"], default="uniform")
    ap.add_argument("--noise", type=float, default=0.0)
    ap.add_argument("--omission", type=float, default=0.0, help="share of 'not listed' graph FALSEs that are actually true (incomplete lists)")
    ap.add_argument("--mismatch", type=float, default=0.0, help="share of known cells where the simulated player disagrees with the graph")
    ap.add_argument("--modes", default="random,rule,ai")
    ap.add_argument("--out", default="eval_results/results.json")
    args = ap.parse_args()
    kb = service.get_kb()
    results = {"args": vars(args), "kb": {"entities": len(kb.uris), "questions": len(kb.rule_questions)}, "patches_applied": config.APPLY_PATCHES}
    for name in args.modes.split(","):
        mode, strategy, exploration = STRATEGIES[name]
        n = args.ai_games if name == "ai" else args.games
        rng = random.Random(args.seed)
        loaded = json.loads(Path(args.load_targets).read_text()) if args.load_targets else None
        targets, meta = pool(kb, args.pool, rng, n, args.target_dist, loaded)
        meta["games_requested"] = n
        if len(targets) < meta["games_requested"]:
            print(f"WARNING: only {len(targets)} distinct targets available for {meta['games_requested']} requested games")
        if args.save_targets and name == args.modes.split(",")[0]:
            Path(args.save_targets).write_text(json.dumps([kb.entities[t]["name"] for t in targets]))
        t0 = time.time()
        games = [play(kb, t, mode, strategy, random.Random(args.seed + i), args.noise, seed=args.seed + i, exploration=exploration, mismatch=args.mismatch, omission=args.omission) for i, t in enumerate(targets)]
        results[name] = {**summarize(games), **meta, "wall_seconds": round(time.time() - t0, 1), "sample": [{k: v for k, v in g.items() if k != "asked"} for g in games[:5]]}
        print(name, json.dumps({k: v for k, v in results[name].items() if k != "sample"}))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(results, indent=2))
    print("\n| strategy | top-1 | avg Q | median Q | unknown-rate | validity | latency ms (mean/p95) |\n|---|---|---|---|---|---|---|")
    for name in args.modes.split(","):
        r = results[name]
        print(f"| {name} | {r['top1_accuracy']:.0%} | {r['avg_questions']} | {r['median_questions']} | {r['unknown_answer_rate']:.0%} | {r['question_validity_rate']:.0%} | {r['latency_ms_mean']}/{r['latency_ms_p95']} |")


if __name__ == "__main__":
    main()
