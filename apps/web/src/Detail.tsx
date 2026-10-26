import { useEffect, useState } from "react";
import { call, simLabel, useSnapshot, type StopRow } from "./api";
import { ConfirmDialog, ETA_MIN, GARAGE, NAV, go } from "./Overview";
import { Button, LineChip, LivePill, Plate, Segmented, Sidebar, StatusPill, StatusShape } from "./ui";
import "./overview.css";
import "./detail.css";

/* Detalhe do ponto (render 02). Ao vivo: lotação, espera, status e extra a caminho (snapshot). O resto é verbatim do render:
   não há modelo de permanência, de próximo ônibus nem histórico semanal/mensal no protótipo. */
const STOP = "SP-0412";
const TITLE = "Av. Paulista, 1578 — sentido Consolação";
const LINES = ["875A", "177H", "6450"]; // o seed só liga a 875A (ela é a linha do alerta na Visão geral)
const LIMIT = 20, GOAL = 8, SCALE = 30;
const NEXT_BUS = { line: "875A", min: 6, headway: 12, load: 82 }; // às 18:42; depois repete a cada 12 min de sim
const DWELL = [["0-2 min", 18], ["2-5 min", 34], ["5-10 min", 27], ["10-15 min", 14], ["15+ min", 7]] as const;
// pessoas no ponto a cada 15 min, 14:00 → 18:30 (render 02); o ponto final é a lotação ao vivo
const HISTORY = [8, 9, 11, 10, 9, 12, 14, 16, 15, 13, 12, 11, 10, 11, 13, 15, 19, 23, 25];
const T0_MIN = 18 * 60 + 42;

export default function Detail() {
  const snap = useSnapshot();
  const [confirm, setConfirm] = useState(false);
  const [ignored, setIgnored] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const stop = snap?.map.find((s) => s.id === STOP);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  async function send(s: StopRow) {
    setConfirm(false);
    try {
      await call("POST", "/dispatches", { stop_id: s.id });
      setToast(`Ônibus extra enviado na linha ${s.line} · chega em ${ETA_MIN} min em ${s.name}`);
    } catch {
      setToast("Não foi possível enviar o extra. Tente de novo.");
    }
  }

  return (
    <div className="app">
      <Sidebar items={NAV} active="Pontos de ônibus" onNavigate={go} />
      <main className="ov">
        <header className="title-plate dt-head">
          <div>
            <nav className="dt-crumb"><a href="/">Pontos de ônibus</a> / <span>{STOP}</span></nav>
            <div className="dt-head__title">
              <h1 className="t-display">{TITLE}</h1>
              {stop && <StatusPill status={stop.status} />}
            </div>
            <p className="title-plate__meta dt-head__meta">
              Linhas {LINES.map((l) => <LineChip key={l} line={l} />)} · Sensor {STOP} (simulado)
            </p>
          </div>
          <div className="ov__head"><LivePill />{snap && <span className="ov__clock">{simLabel(snap.clock.sim_now)}</span>}</div>
        </header>
        {snap && stop ? (
          <>
            <div className="dt-top">
              <Plate title="Detecção no ponto" right={<span className="dt-band-note">Processado na borda · frame descartado</span>}>
                <Scene count={stop.count} wait={stop.wait_min} time={snap.clock.sim_now.slice(11, 19)} />
                <SceneLegend />
              </Plate>
              <div className="dt-side">
                <Stats stop={stop} simNow={snap.clock.sim_now} />
                <Recommendation stop={stop} ignored={ignored} onSend={() => setConfirm(true)} onIgnore={() => setIgnored(true)} />
              </div>
            </div>
            <div className="dt-bottom">
              <Plate title="Tempo de permanência no ponto — hoje"><Dwell /></Plate>
              <LoadPlate count={stop.count} simNow={snap.clock.sim_now} />
            </div>
          </>
        ) : <p className="ov__loading">Conectando ao ponto…</p>}
      </main>
      {confirm && stop && <ConfirmDialog stop={stop} onCancel={() => setConfirm(false)} onConfirm={() => send(stop)} />}
      {toast && <div className="toast" role="status"><StatusShape status="normal" color="var(--status-green-on-ink)" />{toast}</div>}
    </div>
  );
}

const minuteOf = (iso: string) => Number(iso.slice(11, 13)) * 60 + Number(iso.slice(14, 16));

function Stats({ stop, simNow }: { stop: StopRow; simNow: string }) {
  const over = stop.count > LIMIT;
  const late = stop.wait_min > GOAL;
  const elapsed = Math.max(0, minuteOf(simNow) - T0_MIN);
  const bus = NEXT_BUS.min - (elapsed % NEXT_BUS.headway);
  const next = bus > 0 ? bus : bus + NEXT_BUS.headway;
  return (
    <div className="dt-stats">
      <div className="dt-stat">
        <div className="t-overline">Pessoas agora</div>
        <div className="dt-stat__row"><span className="dt-stat__value">{stop.count}</span>
          <span className={over ? "is-neg" : "is-pos"}>{over ? "acima" : "dentro"} do limite ({LIMIT})</span></div>
        <div className="dt-bar" aria-hidden="true">
          <span className={over ? "is-over" : ""} style={{ width: `${Math.min(stop.count / SCALE, 1) * 100}%` }} />
          <i style={{ left: `${(LIMIT / SCALE) * 100}%` }} />
        </div>
      </div>
      <div className="dt-stat">
        <div className="t-overline">Tempo médio de espera</div>
        <div className="dt-stat__row"><span className="dt-stat__value">{stop.wait_min} min</span>
          <span className={late ? "is-warn" : "is-pos"}>meta: {GOAL} min</span></div>
      </div>
      <div className="dt-stat">
        <div className="t-overline">Próximo ônibus</div>
        <div className="dt-stat__row"><span className="dt-stat__value">{NEXT_BUS.line} · {next} min</span>
          <span className="is-quiet">lotação estimada {NEXT_BUS.load}%</span></div>
      </div>
    </div>
  );
}

function Recommendation({ stop, ignored, onSend, onIgnore }: { stop: StopRow; ignored: boolean; onSend: () => void; onIgnore: () => void }) {
  const active = stop.status === "critico" && !ignored;
  return (
    <Plate title="Recomendação do sistema" critical={active && !stop.enroute}>
      {stop.enroute ? (
        <>
          <p className="dt-rec">Ônibus extra a caminho na linha {stop.line} a partir da {GARAGE} (ETA {ETA_MIN} min)</p>
          <div className="dt-rec__actions"><Button variant="secondary" disabled>Extra a caminho</Button></div>
        </>
      ) : active ? (
        <>
          <p className="dt-rec">Enviar 1 ônibus extra na linha {stop.line} a partir da {GARAGE} (ETA {ETA_MIN} min)</p>
          <div className="dt-rec__actions">
            <Button onClick={onSend}>Enviar para a garagem</Button>
            <Button variant="secondary" onClick={onIgnore}>Ignorar</Button>
          </div>
        </>
      ) : <p className="dt-rec dt-rec--quiet">{ignored && stop.status === "critico" ? "Recomendação ignorada." : "Lotação dentro do limite. Nenhuma ação recomendada."}</p>}
    </Plate>
  );
}

/* Cena ilustrativa da detecção (620 × 386 do render): ao vivo só a contagem, o horário e quantas figuras aparecem (até 8).
   Fora do pico (dentro do limite) nenhum tempo marcado passa da espera atual. */
const TAGGED = [{ id: "a", min: 3, x: 125 }, { id: "b", min: 14, x: 173 }, { id: "c", min: 6, x: 226 }, { id: "d", min: 17, x: 272 }, { id: "e", min: 2, x: 326 }];
const UNTAGGED = [38, 377, 595];

function Person({ x }: { x: number }) {
  return <g fill="#7b7e84"><circle cx={x} cy={206} r={11} /><rect x={x - 17} y={222} width={34} height={90} rx={12} /></g>;
}

function Scene({ count, wait, time }: { count: number; wait: number; time: string }) {
  const over = count > LIMIT;
  const tagged = TAGGED.slice(0, count).map((p) => (over ? p : { ...p, min: Math.min(p.min, Math.max(wait, 1)) }));
  const untagged = UNTAGGED.slice(0, Math.max(0, count - TAGGED.length));
  return (
    <svg className="dt-scene" viewBox="0 0 620 386" role="img" aria-label={`Detecção no ponto: ${count} pessoas, IDs temporários`}>
      <rect width="620" height="386" fill="#2b2d31" />
      <rect y="308" width="620" height="78" fill="#3a3d42" />
      <line x1="0" x2="620" y1="308" y2="308" stroke="#55585e" strokeWidth="2" />
      <rect x="39" y="100" width="542" height="12" fill="#55585e" />
      <rect x="58" y="112" width="5" height="196" fill="#55585e" /><rect x="557" y="112" width="5" height="196" fill="#55585e" />
      <rect x="87" y="261" width="291" height="8" fill="#55585e" />
      {untagged.map((x) => <Person key={x} x={x} />)}
      {tagged.map((p) => {
        const c = p.min >= 10 ? "var(--signal-yellow)" : "#5fd39a";
        return (
          <g key={p.id}>
            <Person x={p.x} />
            <rect x={p.x - 22} y={170} width={44} height={150} fill="none" stroke={c} strokeWidth="2" />
            <rect x={p.x - 22} y={156} width={44} height={16} fill={c} />
            <text x={p.x} y={168} className="dt-scene__tag">#{p.id} · {p.min}m</text>
          </g>
        );
      })}
      <rect x="408" y="142" width="134" height="168" fill="var(--sptrans-blue)" stroke="#8db6f0" strokeWidth="2" />
      <text x="475" y="230" className="dt-scene__ad">ANÚNCIO</text>
      <g transform="translate(12 12)">
        <rect width="138" height="28" rx="2" fill="var(--totem-ink)" />
        <circle cx="14" cy="14" r="4" fill="#fff" />
        <text x="26" y="18" className="dt-scene__cam">{STOP} · {time}</text>
      </g>
      <g transform="translate(459 12)">
        <rect width="149" height="30" rx="2" fill={over ? "var(--status-red)" : "var(--totem-ink)"} />
        <rect x="10" y="11" width="8" height="8" fill={over ? "#fff" : "var(--status-green-on-ink)"} />
        <text x="24" y="20" className="dt-scene__count">{count} {count === 1 ? "pessoa" : "pessoas"} no ponto</text>
      </g>
    </svg>
  );
}

function SceneLegend() {
  return (
    <div className="dt-scene-legend">
      <span><i className="sq sq--green" />Aguardando &lt; 10 min</span>
      <span><i className="sq sq--yellow" />Aguardando ≥ 10 min</span>
      <span className="dt-scene-legend__note">IDs temporários — sem reconhecimento facial</span>
    </div>
  );
}

/* Barras de permanência (render 02): verde até 10 min, amarelo a partir de 10. */
function Dwell() {
  const W = 508, BASE = 150, TOP = 26, max = 34, bw = 64, step = W / DWELL.length;
  return (
    <>
      <p className="dt-sub">Quanto tempo cada pessoa ficou esperando (base para espera e exposição ao anúncio)</p>
      <svg className="dt-chart" viewBox={`0 0 ${W} 180`} role="img" aria-label="Distribuição do tempo de permanência hoje">
        {DWELL.map(([label, pct], i) => {
          const h = (pct / max) * (BASE - TOP), x = i * step + (step - bw) / 2;
          return (
            <g key={label}>
              <rect x={x} y={BASE - h} width={bw} height={h} fill={i < 3 ? "var(--status-green)" : "var(--signal-yellow)"}
                stroke={i < 3 ? "none" : "var(--totem-ink)"} strokeWidth="1.5" />
              <text x={x + bw / 2} y={BASE - h - 8} className="dt-chart__pct">{pct}%</text>
              <text x={x + bw / 2} y={174} className="dt-chart__x">{label}</text>
            </g>
          );
        })}
        <line x1="0" x2={W} y1={BASE} y2={BASE} stroke="var(--totem-ink)" strokeWidth="2" />
      </svg>
    </>
  );
}

const RANGES = ["Diária", "Semanal", "Mensal"] as const;

function LoadPlate({ count, simNow }: { count: number; simNow: string }) {
  const [range, setRange] = useState<(typeof RANGES)[number]>("Diária");
  return (
    <Plate title="Lotação ao longo do tempo" right={<Segmented options={[...RANGES]} value={range} onChange={setRange} />}>
      {range === "Diária" ? <LoadCurve count={count} now={Math.max(minuteOf(simNow), T0_MIN)} />
        : <p className="dt-sub dt-sub--empty">Histórico {range.toLowerCase()} entra com os dados reais do piloto.</p>}
    </Plate>
  );
}

/** Lotação a cada 15 min desde 14h; o trecho acima do limite fica em vermelho (recorte do mesmo traço). */
function LoadCurve({ count, now }: { count: number; now: number }) {
  const W = 508, BASE = 150, TOP = 12, max = 30, start = 14 * 60;
  const pts = [...HISTORY.map((v, i) => [start + 15 * i, v] as const), [now, count] as const];
  const x = (m: number) => ((m - start) / (now - start)) * W;
  const y = (v: number) => BASE - (v / max) * (BASE - TOP);
  const line = pts.map(([m, v]) => `${x(m)},${y(v)}`).join(" ");
  const [lx, ly] = [x(now), y(count)];
  return (
    <>
      <p className="dt-sub">Pessoas no ponto a cada 15 min · linha tracejada = limite de {LIMIT}</p>
      <svg className="dt-chart" viewBox={`0 0 ${W} 180`} role="img" aria-label={`Lotação desde 14h; agora ${count} pessoas`}>
        <defs><clipPath id="over"><rect x="0" y="0" width={W} height={y(LIMIT)} /></clipPath></defs>
        {[10, 30].map((v) => <line key={v} x1="0" x2={W} y1={y(v)} y2={y(v)} stroke="var(--concrete-rule)" />)}
        <polygon points={`0,${BASE} ${line} ${W},${BASE}`} fill="var(--concrete-raised)" />
        <polyline points={line} fill="none" stroke="var(--totem-ink)" strokeWidth="2" />
        <polyline points={line} fill="none" stroke="var(--status-red)" strokeWidth="2.5" clipPath="url(#over)" />
        <line x1="0" x2={W} y1={y(LIMIT)} y2={y(LIMIT)} stroke="var(--status-red)" strokeWidth="1.5" strokeDasharray="6 4" />
        <rect x="0" y={y(LIMIT) - 21} width="48" height="16" fill="var(--status-red)" />
        <text x="5" y={y(LIMIT) - 9} className="dt-chart__limit">limite {LIMIT}</text>
        <circle cx={lx - 4} cy={ly} r="5" fill={count > LIMIT ? "var(--status-red)" : "var(--totem-ink)"} stroke="#fff" strokeWidth="1.5" />
        <line x1="0" x2={W} y1={BASE} y2={BASE} stroke="var(--concrete-rule)" />
        {[14, 15, 16, 17, 18].map((h) => (
          <text key={h} x={Math.min(Math.max(x(h * 60), 10), W - 10)} y={174} className={`dt-chart__x${h === 18 ? " dt-chart__x--now" : ""}`}>{h}h</text>
        ))}
      </svg>
    </>
  );
}
