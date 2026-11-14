import json
from types import SimpleNamespace as NS

import numpy as np

from app import feedback_report, service
from app.questions import Cond, Path, QuerySpec, Question


def _q(i):
    return Question(id=f"q{i}", text=f"Question {i}?", spec=QuerySpec(paths=[Path(start="Character", cond=Cond(kind="exists"))]))


def _sess():
    bank = NS(questions=[_q(0), _q(1), _q(2), _q(3)], truth=np.array([[1, 0], [0, 1], [-1, 0], [1, 1]], dtype=np.int8))
    kb = NS(bank=bank, idx={"u:luffy": 0, "u:zoro": 1}, entities=[{"uri": "u:luffy", "name": "Luffy"}, {"uri": "u:zoro", "name": "Zoro"}])
    asked = [{"index": 0, "answer": "yes"}, {"index": 1, "answer": "yes"}, {"index": 2, "answer": "no"}, {"index": 3, "answer": "dont_know"}]
    return NS(kb=kb, seed=7, mode="rule", state=NS(asked=asked, rejected=[1]), prediction_idx=None, status="lost", revealed=False)


def test_disagreements_log_shape_and_report(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "FEEDBACK_DIR", str(tmp_path))
    s = _sess()
    service.reveal(s, "luffy")                       # case-insensitive resolve
    s2 = _sess(); s2.revealed = False
    service.reveal(s2, "Gol D. Nobody")              # unknown -> free text
    lines = [json.loads(x) for x in (tmp_path / "games.jsonl").read_text().splitlines()]
    a, b = lines
    assert set(a) == {"ts", "seed", "mode", "status", "asked", "guesses", "revealed", "disagreements"}
    assert a["status"] == "revealed" and a["revealed"] == {"uri": "u:luffy", "name": "Luffy"} and a["guesses"] == ["Zoro"]
    # Luffy: q0 true/yes ok; q1 false/yes -> disagreement; q2 unknown/no -> disagreement; q3 dont_know skipped
    assert [(d["question_id"], d["graph"]) for d in a["disagreements"]] == [("q1", "false"), ("q2", "unknown")]
    assert b["revealed"] == {"text": "Gol D. Nobody"} and b["disagreements"] is None
    txt = feedback_report.report(feedback_report.load(str(tmp_path)))
    assert "Luffy | Question 1?" in txt and "gol d. nobody" in txt
