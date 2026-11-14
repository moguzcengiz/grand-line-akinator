"""Append-only, low-overhead JSONL timing for ontology campaign stages."""
from __future__ import annotations
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from . import config

PATH = config.ROOT / "work/research/performance.jsonl"
_LOCK = threading.Lock()

def record(stage: str, seconds: float, **fields):
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return
    PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
           "stage": stage, "seconds": round(float(seconds), 6), **fields}
    with _LOCK:
        with PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
