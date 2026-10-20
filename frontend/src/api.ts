export type Mode = "rule" | "ai";
export type Answer = "yes" | "probably" | "dont_know" | "probably_not" | "no";

export interface QueryView { true_query: string; known_query: string; params: Record<string, unknown> }
export interface QuestionView {
  id: string; text: string; source: string; topic: string; original_text: string | null; queries: QueryView[];
  info_gain: number | null; score: number | null; coverage: number | null; p_yes: number | null; p_no: number | null; p_unknown: number | null;
}
export interface Candidate { uri: string; name: string; category: string; probability: number }
export interface Evidence { question: string; answer: string; lift: number; support: string; facts: string[]; kind: "supports" | "contradicts" | "neutral" }
export interface Prediction { uri: string; name: string; category: string; score: number; evidence: Evidence[]; inferred_facts: string[]; explanation: string }
export interface LLMInfo { used: boolean; fallback_reason: string | null; proposed: number; accepted: number; latency_ms: number | null; cached: boolean; rejected: Record<string, number> }
export interface Summary { questions: number; wrong_guesses: number; phases: Record<string, number>; biggest_clue: { question: string; answer: string; bits: number } | null }
export interface GameView {
  session_id: string; mode: Mode; status: "asking" | "guessing" | "won" | "lost";
  question_count: number; remaining_candidates: number; current_question: QuestionView | null; prediction: Prediction | null;
  history: { question: string; answer: string; phase: string }[]; top_candidates: Candidate[]; llm: LLMInfo | null;
  phase: "discovery" | "investigation" | "deduction"; phase_label: string; progress: number; reaction: string | null; guesses: number; summary: Summary | null; seed: number | null;
  debug: {
    policy?: { question: string; score: number; topic: string; info_gain: number; components: Record<string, number> }[];
    phase_metrics?: Record<string, number>; temperature?: number; seed?: number;
    ig_ranking: { question: string; info_gain: number; score: number; coverage: number; source: string }[];
    weights: { entropy_bits: number; max: number };
    top_candidate_facts: { rel: string; target: string; provenance: string }[]; bank_size: number;
  };
}

async function call<T>(path: string, body?: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, body === undefined ? undefined : { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  if (!r.ok) throw new Error(`${r.status}: ${(await r.json().catch(() => ({ detail: r.statusText }))).detail}`);
  return r.json();
}

let DEV = false;                       // developer view: the server only sends candidate identities / scores / queries when asked
export const setDev = (v: boolean) => { DEV = v; };
const q = () => `?dev=${DEV}`;

export const api = {
  start: (mode: Mode) => call<GameView>(`/game/start${q()}`, { mode }),
  get: (id: string) => call<GameView>(`/game/${id}${q()}`),
  answer: (id: string, answer: Answer, question_id: string) => call<GameView>(`/game/${id}/answer${q()}`, { answer, question_id }),
  undo: (id: string) => call<GameView>(`/game/${id}/undo${q()}`, {}),
  feedback: (id: string, correct: boolean) => call<GameView>(`/game/${id}/guess-feedback${q()}`, { correct }),
};
