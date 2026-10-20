import { GameView } from "./api";

const PROV: Record<string, string> = { explicit: "bg-emerald-900 text-emerald-200", curated: "bg-amber-900 text-amber-200", inferred: "bg-fuchsia-900 text-fuchsia-200" };

export default function DevPanel({ g }: { g: GameView }) {
  const q = g.current_question;
  return (
    <div className="mt-6 rounded-lg border border-gold-600/40 bg-navy-900 p-4 text-sm grid gap-6 md:grid-cols-2" data-testid="dev-panel">
      <section>
        <h3 className="font-display text-gold-300 mb-2">Candidate distribution (top 10)</h3>
        {g.top_candidates.map((c) => (
          <div key={c.uri} className="flex items-center gap-2 mb-1">
            <span className="w-40 truncate" title={c.uri}>{c.name}</span>
            <div className="flex-1 bg-navy-800 h-3 rounded"><div className="bg-gold-400 h-3 rounded" style={{ width: `${Math.max(1, c.probability * 100)}%` }} /></div>
            <span className="w-14 text-right font-mono">{(c.probability * 100).toFixed(1)}%</span>
          </div>
        ))}
        <p className="mt-2 text-parchment-300">entropy: {g.debug.weights.entropy_bits.toFixed(2)} bits · question bank: {g.debug.bank_size}</p>
      </section>
      <section>
        <h3 className="font-display text-gold-300 mb-2">Information-gain ranking</h3>
        <table className="w-full text-xs"><thead className="text-parchment-300"><tr><th className="text-left">question</th><th>IG</th><th>cov.</th><th>src</th></tr></thead><tbody>
          {g.debug.ig_ranking.map((r, i) => (
            <tr key={i} className={i === 0 ? "text-gold-300" : ""}><td className="pr-2 py-0.5">{r.question}</td><td className="font-mono">{r.info_gain.toFixed(3)}</td><td className="font-mono">{r.coverage.toFixed(2)}</td><td>{r.source}</td></tr>
          ))}
        </tbody></table>
        {g.llm && <p className="mt-2 text-parchment-300">LLM: {g.llm.used ? `used${g.llm.cached ? " (cache hit)" : ""} · ${g.llm.accepted}/${g.llm.proposed} proposals accepted · rejected ${JSON.stringify(g.llm.rejected)} · ${g.llm.latency_ms}ms` : `not used (${g.llm.fallback_reason ?? "n/a"}) → rule-based fallback`}</p>}
      </section>
      {g.debug.policy && g.debug.policy.length > 0 && (
        <section className="md:col-span-2">
          <h3 className="font-display text-gold-300 mb-2">Adaptive policy · phase <b>{g.phase}</b> · T={g.debug.temperature} · seed {g.debug.seed} · {JSON.stringify(g.debug.phase_metrics)}</h3>
          <table className="w-full text-xs"><thead className="text-parchment-300"><tr><th className="text-left">question (top-k, sampled by softmax)</th><th>score</th><th>topic</th><th className="text-left">normalised components</th></tr></thead><tbody>
            {g.debug.policy.map((r, i) => (<tr key={i} className={r.question === q?.text || r.question === q?.original_text ? "text-gold-300" : ""}><td className="pr-2 py-0.5">{r.question}</td><td className="font-mono">{r.score.toFixed(3)}</td><td>{r.topic}</td>
              <td className="font-mono">{Object.entries(r.components).map(([k, v]) => `${k.slice(0, 4)}:${v.toFixed(2)}`).join(" ")}</td></tr>))}
          </tbody></table>
        </section>
      )}
      {q && q.queries.length > 0 && (
        <section className="md:col-span-2">
          <h3 className="font-display text-gold-300 mb-2">Selected graph query ({q.queries.length} path{q.queries.length > 1 ? "s" : ""}) · P(yes)={q.p_yes?.toFixed(2)} P(no)={q.p_no?.toFixed(2)} P(unknown)={q.p_unknown?.toFixed(2)}</h3>
          {q.queries.map((qq, i) => (
            <pre key={i} className="bg-navy-950 p-2 rounded mb-1 overflow-x-auto font-mono text-xs text-emerald-300 whitespace-pre-wrap">{qq.true_query}{"\n"}// params: {JSON.stringify(qq.params)}</pre>
          ))}
        </section>
      )}
      <section className="md:col-span-2">
        <h3 className="font-display text-gold-300 mb-2">Supporting RDF/OWL facts of the leading candidate ({g.top_candidates[0]?.name})</h3>
        <div className="flex flex-wrap gap-1">
          {g.debug.top_candidate_facts.map((f, i) => (<span key={i} className={`chip ${PROV[f.provenance] ?? "bg-navy-700"}`}>{f.rel} → {f.target} <em>[{f.provenance}]</em></span>))}
        </div>
      </section>
    </div>
  );
}
