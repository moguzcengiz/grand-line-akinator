from typing import Any, Literal

from pydantic import BaseModel, Field

Mode = Literal["rule", "ai"]
Answer = Literal["yes", "probably", "dont_know", "probably_not", "no"]


class StartRequest(BaseModel):
    mode: Mode = "rule"
    policy: Literal["adaptive", "deterministic"] = "adaptive"
    exploration: Literal["off", "low", "medium", "high"] = "medium"
    seed: int | None = Field(None, description="Reproducible question sequence (adaptive policy)")


class AnswerRequest(BaseModel):
    answer: Answer
    question_id: str | None = Field(None, description="Optional guard: must match the question currently asked")


class GuessFeedback(BaseModel):
    correct: bool


class RevealRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)


class QueryView(BaseModel):
    true_query: str
    known_query: str
    params: dict[str, Any]


class QuestionView(BaseModel):
    id: str
    text: str
    source: str
    topic: str = ""
    original_text: str | None = None
    # developer-only (empty for normal players)
    queries: list[QueryView] = []
    info_gain: float | None = None
    score: float | None = None
    coverage: float | None = None
    p_yes: float | None = None
    p_no: float | None = None
    p_unknown: float | None = None


class Candidate(BaseModel):
    uri: str
    name: str
    category: str
    probability: float


class Evidence(BaseModel):
    question: str
    answer: str
    lift: float
    support: str
    facts: list[str]
    kind: Literal["supports", "contradicts", "neutral"] = "neutral"


class Prediction(BaseModel):
    uri: str
    name: str
    category: str
    score: float
    evidence: list[Evidence]
    inferred_facts: list[str]
    explanation: str


class LLMInfo(BaseModel):
    used: bool
    fallback_reason: str | None = None
    proposed: int = 0
    accepted: int = 0
    latency_ms: int | None = None
    cached: bool = False
    rejected: dict[str, int] = {}


class GameView(BaseModel):
    session_id: str
    mode: Mode
    status: Literal["asking", "guessing", "won", "lost"]
    question_count: int
    remaining_candidates: int
    current_question: QuestionView | None = None
    prediction: Prediction | None = None
    history: list[dict[str, str]]
    top_candidates: list[Candidate] = []
    llm: LLMInfo | None = None
    debug: dict[str, Any] = {}
    phase: str = "discovery"
    phase_label: str = ""
    progress: float = 0.0
    reaction: str | None = None
    guesses: int = 0
    summary: dict[str, Any] | None = None
    seed: int | None = None
