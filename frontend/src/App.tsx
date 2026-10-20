import { useEffect, useState } from "react";
import { Answer, GameView, Mode, api, setDev } from "./api";
import DevPanel from "./DevPanel";
import Explorer from "./Explorer";

const ANSWERS: { a: Answer; label: string; cls: string }[] = [
  { a: "yes", label: "Yes", cls: "btn-gold" },
  { a: "probably", label: "Probably", cls: "btn-ghost" },
  { a: "dont_know", label: "Don't know", cls: "btn-ghost" },
  { a: "probably_not", label: "Probably not", cls: "btn-ghost" },
  { a: "no", label: "No", cls: "btn-gold" },
];
const PROV: Record<string, string> = { explicit: "bg-emerald-200 text-emerald-900", curated: "bg-amber-200 text-amber-900", inferred: "bg-fuchsia-200 text-fuchsia-900" };
const TOPIC_ICON: Record<string, string> = { category: "🗺️", status: "💓", affiliation: "🏴‍☠️", role: "⚔️", origin: "🧭", fruit: "🍇", "fruit-user": "🍇", ship: "⚓", haki: "🌀", race: "🧬", physical: "📏", combo: "✨", other: "❓" };
const PHASE_COLOR: Record<string, string> = { discovery: "bg-sky-200 text-sky-900", investigation: "bg-amber-200 text-amber-900", deduction: "bg-rose-200 text-rose-900" };
const warmth = (p: number) => (p < 0.2 ? "The trail is cold…" : p < 0.45 ? "Getting warmer…" : p < 0.7 ? "Hot on the trail!" : "Almost there!");

function Landing({ onStart, busy }: { onStart: (m: Mode) => void; busy: boolean }) {
  const [mode, setMode] = useState<Mode>("rule");
  return (
    <div className="text-center pt-16 pb-10">
      <p className="tracking-[0.4em] text-gold-400 text-sm">ONTOLOGY-DRIVEN · KNOWLEDGE GRAPH · INFORMATION GAIN</p>
      <h1 className="font-display text-5xl md:text-7xl text-gold-300 mt-3 drop-shadow">Grand Line Akinator</h1>
      <p className="max-w-xl mx-auto mt-5 text-parchment-200">Think of a One Piece <b>character</b>, <b>Devil Fruit</b> or <b>ship</b> and keep it secret. Every question is generated from a knowledge graph — and no two voyages start the same way.</p>
      <div className="parchment max-w-md mx-auto mt-8 p-5 text-left">
        <h2 className="font-display font-bold text-xl mb-3">Choose your navigator</h2>
        {([["rule", "Rule-Based", "Questions compiled from ontology classes, properties and graph paths."], ["ai", "AI-Assisted", "Together AI words the questions and proposes new ones; the graph still decides."]] as const).map(([m, t, d]) => (
          <label key={m} className={`flex gap-3 p-2 rounded cursor-pointer border ${mode === m ? "border-gold-600 bg-parchment-200" : "border-transparent"}`}>
            <input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} className="mt-1.5" />
            <span><b className="font-display">{t}</b><br /><span className="text-sm">{d}</span></span>
          </label>
        ))}
        <button className="btn btn-gold w-full mt-4 text-lg" disabled={busy} onClick={() => onStart(mode)}>{busy ? "Hoisting the sails…" : "Set Sail ⚓"}</button>
      </div>
    </div>
  );
}

function Question({ g, onAnswer, onUndo, busy, wrongGuess }: { g: GameView; onAnswer: (a: Answer) => void; onUndo: () => void; busy: boolean; wrongGuess: string | null }) {
  const q = g.current_question!;
  return (
    <div className="max-w-2xl mx-auto">
      {wrongGuess && g.question_count > 0 && g.guesses > 0 && <div className="anim-fade mb-3 rounded-md border border-gold-600/50 bg-navy-800 px-4 py-2 text-center text-gold-300" data-testid="recovery">
        Not <b>{wrongGuess}</b>? No problem — I'm back on the trail (guess {g.guesses + 1} of 5).</div>}
      <div key={q.id} className="parchment anim-card p-6 md:p-8">
        <div className="flex justify-between items-center text-sm font-display">
          <span data-testid="counter">Question <b>{g.question_count + 1}</b></span>
          <span className={`chip !font-display ${PHASE_COLOR[g.phase]}`} data-testid="phase">{g.phase_label}</span>
        </div>
        <div className="mt-3 h-1.5 rounded bg-parchment-300/60 overflow-hidden" role="progressbar" aria-valuenow={Math.round(g.progress * 100)} aria-label="search progress">
          <div className="h-full bg-gradient-to-r from-gold-500 to-gold-300 transition-all duration-700" style={{ width: `${Math.max(4, g.progress * 100)}%` }} />
        </div>
        <p className="text-xs italic mt-1 opacity-70">{warmth(g.progress)}</p>
        <div className="flex gap-4 items-start mt-4 min-h-[5rem]">
          <span className="text-4xl" aria-hidden>{TOPIC_ICON[q.topic] ?? "❓"}</span>
          <p className="font-display text-2xl md:text-3xl" data-testid="question">{q.text}</p>
        </div>
        {q.original_text && <p className="text-xs opacity-60 mt-1">rule: {q.original_text}</p>}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mt-6">
          {ANSWERS.map((x) => <button key={x.a} className={`btn ${x.cls}`} disabled={busy} onClick={() => onAnswer(x.a)}>{x.label}</button>)}
        </div>
        <div className="flex justify-between items-center mt-4 text-sm">
          <button className="underline disabled:opacity-40" disabled={busy || g.question_count === 0} onClick={onUndo}>← Take back last answer</button>
          {g.history.length > 0 && <span className="italic opacity-70 truncate max-w-[55%]" title={g.history[g.history.length - 1].question}>last: {g.history[g.history.length - 1].answer}</span>}
        </div>
      </div>
      {g.reaction && <p key={`${g.question_count}-${g.reaction}`} className="anim-fade text-center mt-4 text-gold-300 italic" data-testid="reaction">“{g.reaction}”</p>}
      {busy && g.mode === "ai" && <p className="text-center mt-2 text-gold-300 anim-shimmer text-sm">The navigator is consulting the sea charts…</p>}
    </div>
  );
}

function Summary({ g, onRestart }: { g: GameView; onRestart: () => void }) {
  const s = g.summary!, total = Math.max(1, s.questions);
  return (
    <div className="parchment anim-fade p-6" data-testid="summary">
      <h2 className="font-display text-2xl font-bold mb-1">{g.status === "won" ? "Voyage log — target found!" : "Voyage log — the seas won this time"}</h2>
      <p className="text-sm opacity-80">{s.questions} questions · {s.wrong_guesses} wrong {s.wrong_guesses === 1 ? "guess" : "guesses"}</p>
      <div className="flex h-3 rounded overflow-hidden mt-3" title="questions per phase">
        {(["discovery", "investigation", "deduction"] as const).map((p) => s.phases[p] ? <div key={p} className={PHASE_COLOR[p].split(" ")[0]} style={{ width: `${(s.phases[p] / total) * 100}%` }} title={`${p}: ${s.phases[p]}`} /> : null)}
      </div>
      <p className="text-xs mt-1 opacity-70">{(["discovery", "investigation", "deduction"] as const).filter((p) => s.phases[p]).map((p) => `${p} ${s.phases[p]}`).join(" · ")}</p>
      {s.biggest_clue && <p className="mt-3 text-sm">🔑 <b>Decisive clue:</b> “{s.biggest_clue.question}” — you said <i>{s.biggest_clue.answer}</i>.</p>}
      <details className="mt-3 text-sm"><summary className="cursor-pointer font-display font-bold">Your answers</summary>
        <ol className="list-decimal ml-5 mt-1">{g.history.map((h, i) => <li key={i}>{h.question} — <i>{h.answer}</i></li>)}</ol></details>
      <button className="btn btn-gold mt-4" onClick={onRestart}>Play again</button>
    </div>
  );
}

function Wanted({ g, onFeedback, onRestart, onExplore, onUndo }: { g: GameView; onFeedback: (c: boolean) => void; onRestart: () => void; onExplore: (id: string) => void; onUndo: () => void }) {
  const p = g.prediction!;
  const [stage, setStage] = useState(0);               // 0 consulting · 1 poster drops · 2 name + buttons
  useEffect(() => {
    setStage(0);
    const t1 = setTimeout(() => setStage(1), 1100), t2 = setTimeout(() => setStage(2), 2000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [p.uri, g.guesses]);
  return (
    <div className="max-w-3xl mx-auto grid gap-6">
      {stage === 0 && <p className="text-center font-display text-2xl text-gold-300 anim-shimmer py-24" data-testid="consulting">The Log Pose is spinning… I think I know who you're hiding!</p>}
      {stage >= 1 && <div className="parchment anim-poster p-6 text-center border-4 border-double" data-testid="wanted">
        <p className="font-display text-5xl tracking-widest">WANTED</p>
        <div className="my-3 mx-auto w-48 h-48 border-4 border-ink/70 flex items-center justify-center bg-parchment-200 text-8xl">{p.category === "Ship" ? "⛵" : p.category === "DevilFruit" ? "🍇" : "🏴‍☠️"}</div>
        {stage >= 2 ? <>
          <p className="font-display text-3xl font-bold anim-fade" data-testid="prediction-name">{p.name}</p>
          <p className="font-display uppercase tracking-widest text-sm">{p.category === "DevilFruit" ? "Devil Fruit" : p.category}</p>
          <p className="mt-2 text-lg">Confidence <b>{(p.score * 100).toFixed(1)}%</b></p>
          {g.status === "guessing" && <div className="anim-fade"><div className="flex gap-3 justify-center mt-4"><button className="btn btn-gold" onClick={() => onFeedback(true)}>That's the one!</button><button className="btn btn-ghost" onClick={() => onFeedback(false)}>Not quite…</button></div>
            <button className="block mx-auto mt-3 underline text-sm" onClick={onUndo}>← I answered wrong, take back my last answer</button></div>}
          {g.status === "won" && <p className="mt-3 font-display text-xl anim-fade">The Grand Line has no secrets from us! 🎉</p>}
          <button className="btn btn-ghost mt-3 text-sm" onClick={() => onExplore(p.uri.split("#").pop()!)}>Show in knowledge graph</button>
        </> : <p className="font-display text-2xl mt-4 anim-shimmer">· · ·</p>}
      </div>}
      {stage >= 2 && g.summary && <Summary g={g} onRestart={onRestart} />}
      {stage >= 2 && <div className="parchment p-6 anim-fade" data-testid="explanation">
        <h2 className="font-display text-2xl font-bold mb-2">Why this entity?</h2>
        <p>{p.explanation}</p>
        <h3 className="font-display font-bold mt-4">Evidence from the knowledge graph</h3>
        <ul className="space-y-2 mt-1 text-sm">
          {p.evidence.filter((e) => e.kind === "supports" && e.facts.length > 0).map((e, i) => (
            <li key={i} className="border-l-4 border-gold-500 pl-3">
              <b>{e.question}</b> — you said <i>{e.answer}</i> <span className="opacity-60">(lift ×{e.lift})</span>
              {e.facts.map((f, j) => <div key={j} className="font-mono text-xs bg-parchment-200 rounded px-1 mt-0.5">{f.split(/(\[(?:explicit|curated|inferred)\])/).map((x, k) => { const m = x.match(/^\[(\w+)\]$/); return m ? <span key={k} className={`chip ${PROV[m[1]]}`}>{m[1]}</span> : x; })}</div>)}
            </li>
          ))}
        </ul>
        {(() => {
          const groups: [string, string, typeof p.evidence][] = [
            ["Also consistent (no matching fact expected)", "supports", p.evidence.filter((e) => e.kind === "supports" && e.facts.length === 0)],
            ["Answers that disagree with the graph", "contradicts", p.evidence.filter((e) => e.kind === "contradicts")],
            ["Skipped or unknown", "neutral", p.evidence.filter((e) => e.kind === "neutral")],
          ];
          return groups.filter(([, , l]) => l.length).map(([t, k, l]) => (
            <details key={k} className="mt-3 text-sm"><summary className="cursor-pointer font-display font-bold">{t} ({l.length})</summary>
              <ul className="list-disc ml-5 mt-1">{l.map((e, i) => <li key={i}>{e.question} — <i>{e.answer}</i> <span className="opacity-60">· {e.support}</span></li>)}</ul></details>
          ));
        })()}
        {p.inferred_facts.length > 0 && <><h3 className="font-display font-bold mt-4">Inferred by OWL RL reasoning</h3><ul className="text-sm list-disc ml-5">{p.inferred_facts.map((f, i) => <li key={i} className="font-mono text-xs">{f}</li>)}</ul></>}
      </div>}
      {g.status === "lost" && <button className="btn btn-gold" onClick={onRestart}>The seas defeated us — play again</button>}
    </div>
  );
}

export default function App() {
  const [g, setG] = useState<GameView | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [dev, setDevState] = useState(false);
  const [tab, setTab] = useState<"play" | "graph">("play");
  const [focus, setFocus] = useState<string | undefined>();
  const [wrongGuess, setWrongGuess] = useState<string | null>(null);

  const run = async (f: () => Promise<GameView>) => {
    setBusy(true); setErr(null);
    try { setG(await f()); } catch (e) { setErr(String(e)); } finally { setBusy(false); }
  };
  const toggleDev = async (v: boolean) => { setDev(v); setDevState(v); if (g) await run(() => api.get(g.session_id)); };

  return (
    <div className="max-w-5xl mx-auto px-4 pb-16">
      <header className="flex justify-between items-center py-4">
        <button className="font-display text-gold-300 text-xl" onClick={() => { setG(null); setTab("play"); setWrongGuess(null); }}>⚓ Grand Line Akinator</button>
        <nav className="flex gap-2">
          <button className={`btn ${tab === "play" ? "btn-gold" : "btn-ghost"} !py-1`} onClick={() => setTab("play")}>Play</button>
          <button className={`btn ${tab === "graph" ? "btn-gold" : "btn-ghost"} !py-1`} onClick={() => setTab("graph")}>Explore the graph</button>
        </nav>
        <label className="text-sm cursor-pointer"><input type="checkbox" checked={dev} onChange={(e) => toggleDev(e.target.checked)} /> developer view</label>
      </header>
      {tab === "graph" && <Explorer initial={focus} />}
      {tab === "play" && <>
        {err && <div className="bg-red-900/60 border border-red-500 rounded p-3 mb-4" role="alert">{err}</div>}
        {!g && <Landing busy={busy} onStart={(m) => { setWrongGuess(null); run(() => api.start(m)); }} />}
        {g && g.status === "asking" && g.current_question && (
          <Question g={g} busy={busy} wrongGuess={wrongGuess} onUndo={() => run(() => api.undo(g.session_id))} onAnswer={(a) => run(() => api.answer(g.session_id, a, g.current_question!.id))} />
        )}
        {g && g.status !== "asking" && g.prediction && <Wanted g={g} onUndo={() => run(() => api.undo(g.session_id))} onExplore={(id) => { setFocus(id); setTab("graph"); }} onRestart={() => { setG(null); setWrongGuess(null); }}
          onFeedback={(c) => { if (!c) setWrongGuess(g.prediction!.name); run(() => api.feedback(g.session_id, c)); }} />}
        {g && g.status === "lost" && !g.prediction && <div className="text-center"><p className="font-display text-2xl mb-3">We are out of ideas, captain.</p><button className="btn btn-gold" onClick={() => setG(null)}>Play again</button></div>}
        {g && dev && <DevPanel g={g} />}
      </>}
    </div>
  );
}
