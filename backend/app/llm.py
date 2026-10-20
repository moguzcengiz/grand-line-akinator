"""Together AI (OpenAI-compatible) helper for AI-assisted mode.

The model never writes Cypher.  It returns JSON that is parsed into pydantic QuerySpec objects, validated against the
live schema whitelist and compiled by app.questions into parameterised Cypher.  Any failure -> caller falls back to rules.
"""
import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout

import httpx
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError

from . import config
from .questions import QuerySpec, Question, spec_id


class Paraphrase(BaseModel):
    id: str
    text: str


class NewQuestion(BaseModel):
    text: str
    spec: QuerySpec


class LLMReply(BaseModel):
    paraphrases: list[Paraphrase] = Field(default_factory=list)
    new_questions: list[NewQuestion] = Field(default_factory=list, max_length=4)
    reaction: str | None = None          # <= 90 chars, reacts to the player's last answer; never names a candidate
    dropped: int = 0                     # malformed items skipped by the tolerant parser


SYSTEM = """You are the question planner of an Akinator-style guessing game about One Piece, backed by a Neo4j knowledge graph.
You NEVER write Cypher and you NEVER decide which question is asked: the game engine validates and scores everything you return.
Answer with ONE JSON object: {"paraphrases":[{"id","text"}], "new_questions":[{"text","spec"}], "reaction": "..."}

paraphrases: rewrite each offered question as one natural, friendly yes/no question that fits the current game phase. Keep the meaning identical,
  including numeric thresholds and inclusiveness ("by chapter 612" means 612 or earlier). Do not mention any candidate name.
reaction: <= 90 characters, a playful reaction to the player's LAST answer. Never name or hint at a candidate.
new_questions (0-3): NEW yes/no questions that would split the current candidates, as a spec. Phases: discovery = broad, natural questions on a
  theme not used recently; investigation = specific relationships; deduction = questions that separate the few remaining candidates.
  spec = {"mode":"any|all","paths":[{"start":"Character|DevilFruit|Ship","steps":[{"rel":REL,"dir":"out|in"}],
    "cond":{"kind":"exists|uri|label|cmp|count","uri":..,"label":..,"prop":..,"op":"<=|>=","value":..},"scope":"closed|positive|rel:REL|prop:P"}]}
  operators: label = class membership incl. OWL-inferred classes; uri = relation to a known entity (exact URI, >=1 step); exists = property exists
  (>=1 step); cmp = numeric property (height, age, number); count = at least N matches (use scope positive, never closed); steps = multi-hop paths
  (max 2, dir "in" for inverse relations); mode "all" = conjunction of >=2 paths about the SAME start category; mode "any" = alternatives per category.
  Use scope "positive" when a missing fact must stay UNKNOWN (open world). Never treat a missing relationship as evidence of FALSE.
  Use ONLY relationship types, labels and URIs from the schema / candidate facts. Question text must be one question ending with '?'. Return JSON only."""


_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")
DEADLINE_SLACK = 3.0          # seconds on top of LLM_TIMEOUT before the call is abandoned


def _client() -> OpenAI:
    # separate connect / read limits: a bare float only bounds each socket operation and a stalled connection once blocked a game for ~33 minutes
    return OpenAI(api_key=config.TOGETHER_API_KEY, base_url=config.TOGETHER_BASE_URL, max_retries=0,
                  timeout=httpx.Timeout(config.LLM_TIMEOUT, connect=5.0, write=10.0, pool=5.0))


def parse_reply(raw: str) -> tuple[LLMReply, int]:
    """Tolerant parsing: every paraphrase / question is validated on its own, so one malformed item (e.g. a path without `cond`)
    costs that item only, not the whole reply.  Returns (reply, number of dropped items)."""
    start, end = raw.find("{"), raw.rfind("}")
    data = json.loads(raw[start:end + 1])
    dropped, paras, qs = 0, [], []
    for item in data.get("paraphrases") or []:
        try:
            paras.append(Paraphrase.model_validate(item))
        except ValidationError:
            dropped += 1
    for item in (data.get("new_questions") or [])[:4]:
        try:
            qs.append(NewQuestion.model_validate(item))
        except ValidationError:
            dropped += 1
    reaction = data.get("reaction")
    return LLMReply(paraphrases=paras, new_questions=qs, reaction=reaction if isinstance(reaction, str) else None), dropped


def available() -> bool:
    return bool(config.TOGETHER_API_KEY)


def ask(schema: dict, candidates: list[dict], asked: list[str], offered: list[Question], phase: str = "investigation",
        recent_topics: list[str] | None = None, last_answer: dict | None = None) -> LLMReply:
    """One chat completion. Raises on transport/parse/validation errors (caller handles fallback)."""
    user = {
        "phase": phase, "recent_topics": recent_topics or [], "last_answer": last_answer,
        "operators": ["exists", "uri", "label", "cmp", "count", "mode:any", "mode:all", "dir:in"],
        "schema": {"relationships": [f"{r['start']} -{r['rel']}-> ({r['n']})" for r in schema["relationships"][:40]],
                   "labels": [l["label"] for l in schema["labels"][:40]], "numeric_props": schema["numeric_props"]},
        "current_candidates": candidates,
        "already_asked": asked[-15:],
        "offered_questions_to_paraphrase": [{"id": q.id, "text": q.text} for q in offered],
    }
    def call():
        return _client().chat.completions.create(
            model=config.TOGETHER_MODEL, temperature=0.4, max_tokens=1000,
            response_format={"type": "json_object"},
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": json.dumps(user, ensure_ascii=False)}])
    try:                                                     # hard wall-clock deadline, whatever the network does
        resp = _POOL.submit(call).result(timeout=config.LLM_TIMEOUT + DEADLINE_SLACK)
    except FutureTimeout:
        raise TimeoutError(f"planner call exceeded {config.LLM_TIMEOUT + DEADLINE_SLACK:.0f}s")
    reply, dropped = parse_reply(resp.choices[0].message.content or "")
    reply.dropped = dropped
    return reply


def to_question(nq: NewQuestion) -> Question:
    return Question(id=spec_id(nq.spec), text=nq.text, spec=nq.spec, source="llm")
