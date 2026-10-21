import { useEffect, useRef, useState } from "react";
import { forceSimulation, forceLink, forceManyBody, forceCenter, forceCollide, SimulationNodeDatum } from "d3-force";

interface GNode extends SimulationNodeDatum { id: string; name: string; category: string | null; labels: string[]; inferred_types: string[] | null; popularity: number | null }
interface GEdge { source: string; target: string; rel: string; provenance: string }
interface Hood { center: string; nodes: GNode[]; edges: GEdge[]; total_edges: number }

const W = 900, H = 560;
const PROV_COLOR: Record<string, string> = { explicit: "#34d399", curated: "#fbbf24", inferred: "#e879f9" };
const CAT_COLOR: Record<string, string> = { Character: "#e3b94a", DevilFruit: "#a78bfa", Ship: "#60a5fa" };
const PRESETS = ["Monkey_D_Luffy", "Gomu_Gomu_no_Mi", "Bartholomew_Kuma", "Thousand_Sunny", "Charlotte_Linlin"];

export default function Explorer({ initial }: { initial?: string }) {
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<{ id: string; name: string; category: string }[]>([]);
  const [nodes, setNodes] = useState<GNode[]>([]);
  const [edges, setEdges] = useState<GEdge[]>([]);
  const [sel, setSel] = useState<GNode | null>(null);
  const [onlyInf, setOnlyInf] = useState(false);
  const [tick, setTick] = useState(0);
  const [trail, setTrail] = useState<string[]>([]);
  const [hint, setHint] = useState<string>("");
  const sim = useRef<ReturnType<typeof forceSimulation<GNode>> | null>(null);
  const nodesRef = useRef<GNode[]>([]);
  const edgesRef = useRef<GEdge[]>([]);
  // pan / zoom (k) of the whole graph, in viewBox units; drag = a node being moved or the background being panned
  const [view, setView] = useState({ x: 0, y: 0, k: 1 });
  const [full, setFull] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  const drag = useRef<{ node?: GNode; sx: number; sy: number; vx: number; vy: number; cx: number; cy: number; moved: boolean } | null>(null);

  const toSvg = (cx: number, cy: number) => new DOMPoint(cx, cy).matrixTransform(svgRef.current!.getScreenCTM()!.inverse());
  const zoomAt = (px: number, py: number, f: number) =>
    setView((v) => { const k = Math.min(5, Math.max(0.2, v.k * f)); return { k, x: px - ((px - v.x) * k) / v.k, y: py - ((py - v.y) * k) / v.k }; });

  useEffect(() => {
    const el = svgRef.current!;
    const onWheel = (e: WheelEvent) => { e.preventDefault(); const p = toSvg(e.clientX, e.clientY); zoomAt(p.x, p.y, Math.exp(-e.deltaY * 0.0015)); };
    const onFs = () => setFull(document.fullscreenElement === boxRef.current);
    el.addEventListener("wheel", onWheel, { passive: false });     // passive:false so the page does not scroll while zooming
    document.addEventListener("fullscreenchange", onFs);
    return () => { el.removeEventListener("wheel", onWheel); document.removeEventListener("fullscreenchange", onFs); };
  }, []);

  const down = (e: React.PointerEvent, node?: GNode) => {
    e.stopPropagation();
    svgRef.current!.setPointerCapture(e.pointerId);
    const p = toSvg(e.clientX, e.clientY);
    drag.current = { node, sx: p.x, sy: p.y, vx: view.x, vy: view.y, cx: e.clientX, cy: e.clientY, moved: false };
  };
  const move = (e: React.PointerEvent) => {
    const d = drag.current;
    if (!d) return;
    if (Math.hypot(e.clientX - d.cx, e.clientY - d.cy) > 4) d.moved = true;
    const p = toSvg(e.clientX, e.clientY);
    if (d.node) {
      d.node.fx = (p.x - view.x) / view.k; d.node.fy = (p.y - view.y) / view.k;
      sim.current?.alphaTarget(0.3).restart();
    } else setView((v) => ({ ...v, x: d.vx + p.x - d.sx, y: d.vy + p.y - d.sy }));
  };
  const up = () => {
    const d = drag.current;
    drag.current = null;
    if (!d?.node) return;
    d.node.fx = d.node.fy = null;
    sim.current?.alphaTarget(0);
    if (!d.moved) load(d.node.id, true);                           // a click without dragging still expands the node
  };
  const toggleFull = () => (document.fullscreenElement ? document.exitFullscreen() : boxRef.current?.requestFullscreen());

  const restart = () => {
    sim.current?.stop();
    const s = forceSimulation<GNode>(nodesRef.current)
      .force("link", forceLink<GNode, any>(edgesRef.current.map((e) => ({ ...e }))).id((d) => d.id).distance(110).strength(0.6))
      .force("charge", forceManyBody().strength(-380))
      .force("center", forceCenter(W / 2, H / 2))
      .force("collide", forceCollide(34))
      .on("tick", () => setTick((t) => t + 1));
    sim.current = s;
  };

  const load = async (id: string, expand: boolean) => {
    const r = await fetch(`/api/graph/neighborhood?id=${encodeURIComponent(id)}&only_inferred=${onlyInf}`);
    if (!r.ok) return;
    const d: Hood = await r.json();
    const jitter = (n: GNode): GNode => ({ ...n, x: W / 2 + (Math.random() - 0.5) * 60, y: H / 2 + (Math.random() - 0.5) * 60 });
    const known = new Set(expand ? nodesRef.current.map((n) => n.id) : []);
    nodesRef.current = [...(expand ? nodesRef.current : []), ...d.nodes.filter((n) => !known.has(n.id)).map(jitter)];
    const key = (e: GEdge) => `${e.source}|${e.rel}|${e.target}`;
    edgesRef.current = [...new Map([...(expand ? edgesRef.current : []), ...d.edges].map((e) => [key(e), e])).values()];
    setNodes([...nodesRef.current]); setEdges([...edgesRef.current]);
    setSel(nodesRef.current.find((n) => n.id === d.center) ?? null);
    setHint(d.total_edges > d.edges.length ? `showing ${d.edges.length} of ${d.total_edges} relations (inferred and curated first)` : "");
    setTrail((t) => (expand ? [...t, d.center] : [d.center]));
    if (!expand) setView({ x: 0, y: 0, k: 1 });
    restart();
  };

  useEffect(() => { load(initial ?? PRESETS[0], false); return () => { sim.current?.stop(); }; /* eslint-disable-next-line */ }, [initial]);
  useEffect(() => {
    if (q.length < 2) { setHits([]); return; }
    const t = setTimeout(async () => setHits((await (await fetch(`/api/entities?q=${encodeURIComponent(q)}&limit=8`)).json()).items), 200);
    return () => clearTimeout(t);
  }, [q]);

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const color = (n: GNode) => (n.category && CAT_COLOR[n.category]) || "#94a3b8";
  const short = (s: string) => (s.length > 18 ? s.slice(0, 17) + "…" : s);
  void tick;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_300px]" data-testid="explorer">
      <div>
        <div className="flex flex-wrap gap-2 items-center mb-3">
          <div className="relative">
            <input className="bg-navy-800 border border-gold-600/50 rounded px-3 py-1.5 w-64" placeholder="Search any character, fruit, ship…" value={q} onChange={(e) => setQ(e.target.value)} />
            {hits.length > 0 && <ul className="absolute z-10 mt-1 w-64 bg-navy-900 border border-gold-600/50 rounded shadow-xl">
              {hits.map((h) => <li key={h.id}><button className="w-full text-left px-3 py-1 hover:bg-navy-700" onClick={() => { setQ(""); setHits([]); load(h.id, false); }}>{h.name} <span className="text-xs opacity-60">{h.category}</span></button></li>)}
            </ul>}
          </div>
          {PRESETS.map((p) => <button key={p} className="btn btn-ghost !py-1 text-sm" onClick={() => load(p, false)}>{p.replace(/_/g, " ")}</button>)}
          <label className="text-sm cursor-pointer ml-auto"><input type="checkbox" checked={onlyInf} onChange={(e) => setOnlyInf(e.target.checked)} /> only OWL-inferred edges</label>
        </div>
        <div ref={boxRef} className={`relative ${full ? "h-screen bg-navy-900" : ""}`}>
        <div className="absolute top-2 right-2 z-10 flex gap-1">
          {([["+", "Zoom in", () => zoomAt(W / 2, H / 2, 1.3)], ["−", "Zoom out", () => zoomAt(W / 2, H / 2, 1 / 1.3)],
             ["⟲", "Reset view", () => setView({ x: 0, y: 0, k: 1 })], [full ? "✕" : "⛶", full ? "Exit full screen" : "Full screen", toggleFull]] as const).map(([t, label, fn]) =>
            <button key={label} title={label} aria-label={label} onClick={fn} className="w-8 h-8 rounded bg-navy-800/90 border border-gold-600/50 text-gold-300 hover:bg-navy-700">{t}</button>)}
        </div>
        <svg ref={svgRef} viewBox={`0 0 ${W} ${H}`} className={`w-full bg-navy-900 rounded-lg border border-gold-600/30 touch-none ${full ? "h-full" : ""} ${drag.current && !drag.current.node ? "cursor-grabbing" : "cursor-grab"}`}
          role="img" aria-label="knowledge graph neighbourhood" onPointerDown={(e) => down(e)} onPointerMove={move} onPointerUp={up} onPointerCancel={up}>
          <g transform={`translate(${view.x},${view.y}) scale(${view.k})`}>
          <defs>{Object.entries(PROV_COLOR).map(([k, c]) => <marker key={k} id={`arrow-${k}`} viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0L10 5L0 10z" fill={c} /></marker>)}</defs>
          {edges.map((e, i) => {
            const a = byId.get(e.source), b = byId.get(e.target);
            if (!a || !b || a.x === undefined || b.x === undefined) return null;
            const mx = (a.x + b.x!) / 2, my = (a.y! + b.y!) / 2;
            return <g key={i}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={PROV_COLOR[e.provenance] ?? "#64748b"} strokeWidth={e.provenance === "inferred" ? 2.5 : 1.5} strokeDasharray={e.provenance === "inferred" ? "6 4" : undefined} markerEnd={`url(#arrow-${e.provenance})`} opacity={0.85} />
              <text x={mx} y={my} fontSize="9" fill="#cbd5e1" textAnchor="middle" className="select-none">{e.rel.toLowerCase().replace(/_/g, " ")}</text></g>;
          })}
          {nodes.map((n) => (
            <g key={n.id} transform={`translate(${n.x ?? W / 2},${n.y ?? H / 2})`} className="cursor-pointer" onPointerDown={(e) => down(e, n)} onMouseEnter={() => setSel(n)}>
              <circle r={n.id === trail[trail.length - 1] ? 17 : 13} fill={color(n)} stroke={sel?.id === n.id ? "#fff" : "#08162b"} strokeWidth={2.5} />
              <text y={30} fontSize="11" textAnchor="middle" fill="#f6ecd2" className="select-none">{short(n.name)}</text>
            </g>
          ))}
          </g>
        </svg>
        </div>
        <div className="flex flex-wrap gap-4 text-xs mt-2 items-center">
          {Object.entries(PROV_COLOR).map(([k, c]) => <span key={k}><span className="inline-block w-5 h-0.5 align-middle mr-1" style={{ background: c }} />{k}</span>)}
          <span className="opacity-70">·</span>
          {Object.entries(CAT_COLOR).map(([k, c]) => <span key={k}><span className="inline-block w-3 h-3 rounded-full align-middle mr-1" style={{ background: c }} />{k}</span>)}
          <span className="opacity-60 ml-auto">click a node to expand its relations{hint && ` · ${hint}`}</span>
        </div>
      </div>
      <aside className="bg-navy-900 border border-gold-600/30 rounded-lg p-3 text-sm h-fit">
        {sel ? <>
          <h3 className="font-display text-gold-300 text-lg">{sel.name}</h3>
          <p className="text-xs opacity-60 break-all">{sel.id}</p>
          <p className="mt-2"><b>Types</b><br />{sel.labels.filter((l) => !(sel.inferred_types ?? []).includes(l)).map((l) => <span key={l} className="chip bg-emerald-900 text-emerald-200 mr-1">{l}</span>)}
            {(sel.inferred_types ?? []).map((l) => <span key={l} className="chip bg-fuchsia-900 text-fuchsia-200 mr-1" title="derived by OWL RL">{l} ⚡</span>)}</p>
          {sel.popularity != null && <p className="mt-2">Popularity (graph degree): <b>{sel.popularity}</b></p>}
        </> : <p className="opacity-70">Hover a node.</p>}
        {trail.length > 1 && <p className="mt-3 text-xs opacity-70"><b>Walk:</b> {trail.map((t) => t.split("#").pop()!.replace(/_/g, " ")).join(" → ")}</p>}
      </aside>
    </div>
  );
}
