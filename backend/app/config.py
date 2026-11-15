import os
from pathlib import Path

ROOT = Path(os.environ.get("ONTOLOGY_ROOT", Path(__file__).resolve().parents[2]))

FUSEKI_URL = os.environ.get("FUSEKI_URL", "http://localhost:3030")
FUSEKI_DATASET = os.environ.get("FUSEKI_DATASET", "ds")
FUSEKI_USER = os.environ.get("FUSEKI_USER", "admin")
FUSEKI_PASSWORD = os.environ.get("FUSEKI_PASSWORD", "")

TOGETHER_API_KEY = os.environ.get("TOGETHER_API_KEY", "")
TOGETHER_MODEL = os.environ.get("TOGETHER_MODEL", "MiniMaxAI/MiniMax-M3.1-Flash")
TOGETHER_BASE_URL = os.environ.get("TOGETHER_BASE_URL", "https://api.together.xyz/v1")
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "25"))

OP = "http://kalnassag.com/onepiece#"
OPX = "http://kalnassag.com/onepiece-ext#"

BASE_FILES = [
    "ontology-src/ontology/onepiece-ontology.ttl",
    "ontology-src/ontology/one-piece-graph.ttl",
    "ontology-src/ontology/OnePieceEntities-Base Model.ttl",
]
EXT_FILES = ["ontology/extension.ttl", "ontology/curated.ttl"]

# Game engine knobs (all overridable through env)
CATEGORIES = ["Character", "DevilFruit", "Ship"]
MIN_SUPPORT = int(os.environ.get("MIN_SUPPORT", "8"))
STOP_CONFIDENCE = float(os.environ.get("STOP_CONFIDENCE", "0.80"))
MAX_QUESTIONS = int(os.environ.get("MAX_QUESTIONS", "20"))
MIN_QUESTIONS = int(os.environ.get("MIN_QUESTIONS", "3"))
COVERAGE_GAMMA = float(os.environ.get("COVERAGE_GAMMA", "1.0"))
REMAINING_RATIO = float(os.environ.get("REMAINING_RATIO", "0.01"))
PRIOR = os.environ.get("PRIOR", "popularity")            # "uniform" | "popularity"
POPULARITY_ALPHA = float(os.environ.get("POPULARITY_ALPHA", "1.5"))
FAMILY_DECAY = float(os.environ.get("FAMILY_DECAY", "0.7"))  # score multiplier per earlier question of the same family
FAMILY_MAX = int(os.environ.get("FAMILY_MAX", "3"))               # hard cap of questions per family per game
APPLY_PATCHES = os.environ.get("APPLY_PATCHES", "1") == "1"       # "0" only for the before/after evaluation
SKIP_PATCHES = {name.strip() for name in os.environ.get("SKIP_PATCHES", "").split(",") if name.strip()}
POSITIVE_UNKNOWN_PRIOR = float(os.environ.get("POSITIVE_UNKNOWN_PRIOR", "0.05"))
# Closed world (default): what the graph does not record is FALSE, so every answer splits the candidates cleanly.  "0" = the old open world
# (unrecorded = UNKNOWN = 50/50), which kept ruled-out candidates alive and made the game re-ask the same thing in other words.
CLOSED_WORLD = os.environ.get("CLOSED_WORLD", "1") == "1"
STRICT_UNKNOWN = os.environ.get("STRICT_UNKNOWN", "1") == "1"        # "0" restores the old closed-world scopes (ablation only)

# ---- adaptive question policy (see app/policy.py, docs/POLICY.md)
TEMPERATURE = float(os.environ.get("POLICY_TEMPERATURE", "0.06"))     # 0 = deterministic argmax; larger = more exploration
TOP_K = int(os.environ.get("POLICY_TOP_K", "5"))
GATE_REL = float(os.environ.get("POLICY_GATE_REL", "0.35"))           # a question needs >= this fraction of the best information gain
EQUIV_PHI = float(os.environ.get("POLICY_EQUIV_PHI", "0.97"))         # |phi| above this with an asked question = same question, re-worded
RECENT_WINDOW = int(os.environ.get("POLICY_RECENT_WINDOW", "4"))
TOPIC_DECAY = float(os.environ.get("POLICY_TOPIC_DECAY", "0.5"))
DISCOVERY_ENTROPY_FRAC = float(os.environ.get("DISCOVERY_ENTROPY_FRAC", "0.70"))
DEDUCTION_ENTROPY_FRAC = float(os.environ.get("DEDUCTION_ENTROPY_FRAC", "0.30"))
DEDUCTION_REMAINING = int(os.environ.get("DEDUCTION_REMAINING", "20"))
DEDUCTION_TOP_P = float(os.environ.get("DEDUCTION_TOP_P", "0.30"))
# exploration is strongest while many suspects remain and switched off at the end (a wrong random pick costs most in deduction)
PHASE_TEMP_SCALE = {"discovery": float(os.environ.get("TEMP_SCALE_DISCOVERY", "1.0")), "investigation": float(os.environ.get("TEMP_SCALE_INVESTIGATION", "1.0")),
                    "deduction": float(os.environ.get("TEMP_SCALE_DEDUCTION", "1.0"))}

# ---- answer model (what "Probably" / "Don't know" mean).  "legacy" = the previous behaviour, kept only for the ablation.
ANSWER_MODEL = os.environ.get("ANSWER_MODEL", "calibrated")
# P(a graph FALSE is really false) for questions whose FALSE only means "not in the (incomplete) list": roles, residence, origin, affiliations ...
# (Shanks has no recorded Captain occupation.)  Category / status / fruit-type FALSEs stay at 0.98.  1.0 = old closed-world behaviour.
ABSENCE_RELIABILITY = float(os.environ.get("ABSENCE_RELIABILITY", "0.90"))
DEFINITE_RELIABILITY = 0.98
# P(a graph TRUE is really true / accepted by the player) on those same list questions (Luffy "Prisoner", Shanks "resides in Mary Geoise")
PRESENCE_RELIABILITY = float(os.environ.get("PRESENCE_RELIABILITY", "0.95"))
# Correlated contradictions: one missing fact (Shanks has no recorded Captain occupation) shows up in several related questions and must not be
# punished once per question.  The k-th contradiction of a candidate on RELATED questions (|phi| >= RELATED_PHI) is discounted to ratio^(DISCOUNT^k).
CONTRADICTION_DISCOUNT = float(os.environ.get("CONTRADICTION_DISCOUNT", "0.5"))
RELATED_PHI = float(os.environ.get("RELATED_PHI", "0.35"))

# Diminishing-returns stop: guess when the best remaining question is worth less than IG_FLOOR nats AND the leading candidate holds FLOOR_CONF of the mass
# (0 = off).  Measured with eval_results/stop_rule_eval.sh.
IG_FLOOR = float(os.environ.get("IG_FLOOR", "0.03"))
FLOOR_CONF = float(os.environ.get("FLOOR_CONF", "0.25"))
