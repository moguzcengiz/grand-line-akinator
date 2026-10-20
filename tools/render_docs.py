"""Render the measured tables of docs/POLICY.md, docs/FINAL_REPORT.md and README.md from eval_results/*.json (no hand-copied numbers).

    python tools/render_docs.py
Markers in the docs:  <!-- BEGIN:name -->  ...  <!-- END:name -->  are replaced.
"""
import json
import re
from pathlib import Path

R = Path("eval_results")
load = lambda f: json.loads((R / f).read_text()) if (R / f).exists() else None
pct = lambda x: f"{x * 100:.1f}%"
bits = lambda x: f"{abs(x):.2f}".rstrip("0").rstrip(".") + " b"


def row(r, extra=()):
    base = [pct(r["top1_accuracy"]), pct(r["found_within_3_guesses"]), f"{r['avg_questions']:.1f}", f"{r['median_questions']:g}"]
    return base + [str(x) for x in extra]


def main_table(d):
    names = {"random": "random (baseline)", "ig": "deterministic IG (previous)", "adaptive_det": "adaptive, T = 0", "adaptive": "**adaptive, T = 0.06 (default)**"}
    out = ["| policy | top-1 | <=3 guesses | avg Q | median Q | distinct openings | opening entropy | topics in first 8 | repeated family | equivalent-pair rate | sessions with equivalent pair | unknown answers | latency mean / p95 |", "|" + "---|" * 13]
    for k, label in names.items():
        r = d[k]
        out.append(f"| {label} | " + " | ".join(map(str, row(r) + [r["opening_distinct_overall"], bits(r['opening_entropy_bits']), r["distinct_topics_first8"], r["family_repeat_rate"],
                   f"{r['equivalent_pair_rate'] * 100:.2f}%", pct(r["sessions_with_equivalent_pair"]), pct(r["unknown_answer_rate"]), f"{r['latency_ms_mean']} / {r['latency_ms_p95']:g} ms"])) + " |")
    op = "; ".join(f"“{q}” {c}" for q, c in d["adaptive"]["top_openings"])
    v = (d["variety_ig"], d["variety_adaptive"])
    out += ["", f"Openings of the adaptive policy (top 4 of {d['adaptive']['opening_distinct_overall']}): {op}. The deterministic policy opened with “{d['ig']['top_openings'][0][0]}” in {d['ig']['top_openings'][0][1]} of {d['games']} games.", "",
            "**Same target, 10 seeds, 20 targets:**", "", "| policy | top-1 | <=3 guesses | avg Q | distinct openings per target | question-set distance between seeds | equivalent-pair rate |", "|---|---|---|---|---|---|---|"]
    for label, r in (("deterministic IG", v[0]), ("adaptive", v[1])):
        out.append(f"| {label} | {pct(r['top1_accuracy'])} | {pct(r['found_within_3_guesses'])} | {r['avg_questions']:.1f} | {r['opening_distinct_per_target']} | {r['same_target_question_set_distance']} | {r['equivalent_pair_rate'] * 100:.2f}% |")
    return "\n".join(out)


def sweep_tables(d):
    out = ["| variant | top-1 | avg Q | distinct topics in first 8 | sessions with equivalent pair |", "|---|---|---|---|---|"]
    for k, r in d["ablation"].items():
        out.append(f"| {'full policy' if k == 'full' else '- ' + k} | {pct(r['top1_accuracy'])} | {r['avg_questions']:.1f} | {r['distinct_topics_first8']} | {pct(r['sessions_with_equivalent_pair'])} |")
    out += ["", "| T | top-1 | <=3 guesses | avg Q | distinct openings | opening entropy |", "|---|---|---|---|---|---|"]
    for k, r in d["temperature"].items():
        out.append(f"| {k} | {pct(r['top1_accuracy'])} | {pct(r['found_within_3_guesses'])} | {r['avg_questions']:.1f} | {r['opening_distinct_overall']} | {bits(r['opening_entropy_bits'])} |")
    return "\n".join(out)


def phase_table(d):
    out = ["| temperature scale (discovery, investigation, deduction) | top-1 | <=3 guesses | avg Q | opening entropy |", "|---|---|---|---|---|"]
    for k, r in d["phase_scale"].items():
        out.append(f"| {k} | {pct(r['top1_accuracy'])} | {pct(r['found_within_3_guesses'])} | {r['avg_questions']:.1f} | {bits(r['opening_entropy_bits'])} |")
    return "\n".join(out)


def ai_table(d):
    names = {"ig": "deterministic IG (previous)", "adaptive": "adaptive, rule-based", "ai": "adaptive + Together AI planner"}
    out = ["| policy (same 12 targets) | top-1 | <=3 guesses | avg Q | median Q | LLM proposals | accepted | rejected (reason count) | planner calls | unknown answers | latency mean / p95 |", "|" + "---|" * 11]
    for k, label in names.items():
        r = d.get(k)
        if r:
            t = r.get("llm_totals") or {}
            rej = ", ".join(f"{k} {v}" for k, v in sorted((t.get("rejected") or {}).items(), key=lambda kv: -kv[1])) or "-"
            out.append(f"| {label} | " + " | ".join(map(str, row(r) + [t.get("proposed", 0) or "-", f"{t['accepted']} accepted ({pct(r['question_validity_rate'])})" if t.get("proposed") else "-", rej,
                                                                f"{t.get('calls', 0)} calls / {t.get('cache_hits', 0)} cached / {t.get('failures', 0)} failed" if t.get("calls") else "-", pct(r["unknown_answer_rate"]), f"{r['latency_ms_mean']} / {r['latency_ms_p95']:g} ms"])) + " |")
    return "\n".join(out)


def sub(text, name, body):
    pat = re.compile(rf"(<!-- BEGIN:{name} -->\n).*?(\n<!-- END:{name} -->)", re.S)
    return pat.sub(lambda m: m.group(1) + body + m.group(2), text) if pat.search(text) else text


def main():
    pe, sw, ph, ai = load("policy_eval.json"), load("policy_sweep.json"), load("policy_phase_sweep.json"), load("ai_policy.json")
    blocks = {}
    if pe: blocks["main"] = main_table(pe)
    if sw: blocks["sweep"] = sweep_tables(sw)
    if ph: blocks["phase"] = phase_table(ph)
    if ai: blocks["ai"] = ai_table(ai)
    for f in ("docs/POLICY.md", "docs/FINAL_REPORT.md", "README.md"):
        p = Path(f); t = p.read_text()
        for k, v in blocks.items():
            t = sub(t, k, v)
        p.write_text(t)
    print("rendered:", ", ".join(blocks))


if __name__ == "__main__":
    main()
