"""Summarise the player-feedback log: python -m app.feedback_report [dir]. Stdlib only."""
import json
import os
import sys
from collections import Counter


def load(d: str) -> list[dict]:
    rows = []
    try:
        for line in open(os.path.join(d, "games.jsonl"), encoding="utf-8"):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass                                           # a torn line must not hide the rest
    except FileNotFoundError:
        pass
    return rows


def report(rows: list[dict], top: int = 30) -> str:
    missing, wrong, unknown = Counter(), Counter(), Counter()
    for r in rows:
        who = (r.get("revealed") or {}).get("name")
        for d in r.get("disagreements") or []:
            key = (who, d["question"])
            if d["answer"] in ("yes", "probably") and d["graph"] in ("false", "unknown"):
                missing[key] += 1
            elif d["answer"] in ("no", "probably_not") and d["graph"] == "true":
                wrong[key] += 1
        if r.get("revealed") and "text" in r["revealed"]:
            unknown[r["revealed"]["text"].strip().casefold()] += 1
    out = [f"{len(rows)} log lines, {sum(1 for r in rows if r.get('revealed'))} reveals"]
    for title, c in (("Graph says no/unknown, players say yes (candidate missing facts)", missing),
                     ("Graph says yes, players say no (candidate wrong or outdated facts)", wrong)):
        out += ["", title] + [f"  {n:4d}  {e} | {q}" for (e, q), n in c.most_common(top)] + ([] if c else ["  (none)"])
    out += ["", "Revealed names matching no entity (candidate missing entities)"] + [f"  {n:4d}  {t}" for t, n in unknown.most_common(top)] + ([] if unknown else ["  (none)"])
    return "\n".join(out)


if __name__ == "__main__":
    print(report(load(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("FEEDBACK_DIR", "/data/player-feedback"))))
