import { useEffect, useRef, useState } from "react";
import { call, fmt, simHour, simLabel, useSnapshot, type Snapshot, type StopRow } from "./api";
import { Button, KpiStrip, LineChip, LivePill, Plate, Sidebar, StatusPill, StatusShape, TitlePlate, Toggle } from "./ui";
import "./overview.css";

export const NAV = ["Visão geral", "Pontos de ônibus", "Frota", "Publicidade", "Relatórios", "Configurações"];
const PAGES: Record<string, string> = { "Visão geral": "/", "Pontos de ônibus": "/pontos/SP-0412", "Publicidade": "/publicidade" };
export const go = (item: string) => PAGES[item] && location.assign(PAGES[item]);
export const GARAGE = "Garagem Vila Mariana";
export const ETA_MIN = 9; // = dispatch.ETA_MIN na API

export default function Overview() {
  const snap = useSnapshot();
  const [confirm, setConfirm] = useState<StopRow | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [auto, setAuto] = useState(true); // só exibe: a regra sugere, quem envia é o operador

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  async function send(stop: StopRow) {
    setConfirm(null);
    try {
      await call("POST", "/dispatches", { stop_id: stop.id });
      setToast(`Ônibus extra enviado na linha ${stop.line} · chega em ${ETA_MIN} min em ${stop.name}`);
    } catch {
      setToast("Não foi possível enviar o extra. Tente de novo.");
    }
  }

  return (
    <div className="app">
      <Sidebar items={NAV} active="Visão geral" onNavigate={go} />
      <main className="ov">
        <TitlePlate title="Visão geral da operação" meta="Concessionária Via Sul · 142 pontos monitorados"
          right={<div className="ov__head"><LivePill />{snap && <span className="ov__clock">{simLabel(snap.clock.sim_now)}</span>}<span className="avatar" aria-label="Perfil"><svg viewBox="0 0 36 36" aria-hidden="true"><circle cx="18" cy="14" r="6" fill="#fff" /><path d="M7 31a11 9 0 0 1 22 0z" fill="#fff" /></svg></span></div>} />
        {snap ? <Body snap={snap} onSend={setConfirm} auto={auto} setAuto={setAuto} /> : <p className="ov__loading">Conectando aos pontos…</p>}
      </main>
      {confirm && <ConfirmDialog stop={confirm} onCancel={() => setConfirm(null)} onConfirm={() => send(confirm)} />}
      {toast && <div className="toast" role="status"><StatusShape status="normal" color="var(--status-green-on-ink)" />{toast}</div>}
    </div>
  );
}

function Body({ snap, onSend, auto, setAuto }: { snap: Snapshot; onSend: (s: StopRow) => void; auto: boolean; setAuto: (v: boolean) => void }) {
  const o = snap.overview;
  const over = o.wait_over_goal_min;
  const vs = o.vs_avg_pct ?? 0;
  return (
    <>
      <KpiStrip cells={[
        { label: "Pessoas nos pontos agora", value: fmt(o.people), tone: vs > 0 ? "warn" : "pos",
          delta: `${vs >= 0 ? "▲" : "▼"} ${Math.abs(vs)}% vs. média do horário` },
        { label: "Tempo médio de espera", value: `${Math.round(o.avg_wait_min)} min`, tone: over > 0 ? "neg" : "pos",
          delta: over > 0 ? `▲ ${over} min acima da meta (${o.goal_wait_min} min)` : `▼ dentro da meta (${o.goal_wait_min} min)` },
        { label: "Pontos em alerta", value: `${o.stops_in_alert} / ${o.stops_total}`, tone: "info",
          delta: `${o.critical} críticos · ${o.attention} atenção` },
        { label: "Ônibus extras enviados hoje", value: String(o.extras_today), tone: "pos", delta: "▼ 9% km rodado ocioso" },
      ]} />
      <div className="ov__grid">
        <Plate title="Mapa de lotação em tempo real" right={<Legend />}><StopMap stops={snap.map} /></Plate>
        <Plate title="Pontos em alerta" right={<a className="band-link" href="#">Ver todos →</a>}>
          <ul className="alerts">{snap.alerts.map((s) => <AlertRow key={s.id} stop={s} onSend={onSend} />)}</ul>
        </Plate>
        <Plate title="Fluxo de pessoas por hora — hoje vs. média" right={<ChartLegend />}>
          <HourlyChart hourly={snap.hourly} hour={simHour(snap.clock.sim_now)} now={o.people} />
        </Plate>
        <Plate title="Regra de envio automático" right={<Toggle on={auto} onChange={setAuto} label="Regra de envio automático" />}>
          <AutoRule extras={o.extras_today} />
        </Plate>
      </div>
    </>
  );
}

function Legend() {
  return (
    <span className="legend">
      <span><StatusShape status="normal" color="var(--status-green)" />Normal</span>
      <span><StatusShape status="atencao" color="var(--signal-yellow)" />Atenção</span>
      <span><StatusShape status="critico" color="var(--status-red)" />Crítico</span>
    </span>
  );
}

function AlertRow({ stop, onSend }: { stop: StopRow; onSend: (s: StopRow) => void }) {
  return (
    <li className="alert-row">
      <div>
        <div className="alert-row__name">{stop.id === "SP-0412" ? <a className="t-metric-s alert-row__link" href="/pontos/SP-0412">{stop.name}</a> : <span className="t-metric-s">{stop.name}</span>}<StatusPill status={stop.status} /></div>
        <div className="alert-row__meta">Linha <LineChip line={stop.line} /> · {stop.count} pessoas · {stop.wait_min} min</div>
      </div>
      {stop.enroute ? <Button variant="secondary" disabled>Extra a caminho</Button>
        : stop.status === "critico" ? <Button onClick={() => onSend(stop)}>Enviar extra</Button>
        : <Button variant="secondary">Monitorar</Button>}
    </li>
  );
}

/* Mapa estilizado do recorte Paulista/Consolação/Rebouças: geometria desenhada a partir do render 01, sem projeção. */
const W = 656, H = 316;
const COLOR = { normal: "var(--status-green)", atencao: "var(--signal-yellow)", critico: "var(--status-red)" };

function StopMap({ stops }: { stops: StopRow[] }) {
  const [hover, setHover] = useState<string | null>(null);
  const tip = stops.find((s) => s.id === hover) ?? [...stops].sort((a, b) => b.count - a.count)[0];
  const px = (s: StopRow) => [(s.x! / 100) * W, (s.y! / 100) * H] as const;
  return (
    <div className="map">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Mapa de lotação dos pontos">
        <rect width={W} height={H} fill="var(--map-ground)" />
        <rect x="300" y="197" width="120" height="75" fill="var(--map-park)" />
        <rect x="470" y="268" width="80" height="40" fill="var(--map-park)" />
        <g stroke="#fff" strokeWidth="10" fill="none">
          {[62, 176, 256].map((y) => <line key={y} x1="0" y1={y} x2={W} y2={y} />)}
          {[92, 262, 432, 560].map((x) => <line key={x} x1={x} y1="0" x2={x} y2={H} />)}
          <line x1="0" y1="42" x2={W} y2="152" />
          <line x1="115" y1="0" x2="240" y2={H} />
        </g>
        <g className="map__label">
          <text x="128" y="55">AV. PAULISTA</text>
          <text transform="translate(278 300) rotate(-90)">R. DA CONSOLAÇÃO</text>
          <text transform="translate(468 220) rotate(17)">AV. REBOUÇAS</text>
        </g>
        {stops.map((s) => {
          const [x, y] = px(s);
          return (
            <g key={s.id} transform={`translate(${x} ${y})`} onMouseEnter={() => setHover(s.id)} onMouseLeave={() => setHover(null)}
              className="map__stop" tabIndex={0} onFocus={() => setHover(s.id)} aria-label={`${s.name}: ${s.count} pessoas`}>
              {s.status !== "normal" && <circle r="24" fill={COLOR[s.status]} opacity="0.3" />}
              {s.status === "critico" && <rect x="-8" y="-8" width="16" height="16" fill={COLOR.critico} stroke="#fff" strokeWidth="2" />}
              {s.status === "atencao" && <polygon points="0,-8 8,6 -8,6" fill={COLOR.atencao} stroke="var(--totem-ink)" strokeWidth="1.5" />}
              {s.status === "normal" && <circle r="7" fill={COLOR.normal} stroke="#fff" strokeWidth="2" />}
            </g>
          );
        })}
      </svg>
      {tip && (() => {
        const [x, y] = px(tip);
        return (
          <div className="map__tip" style={{ left: `${(x / W) * 100}%`, top: `${(y / H) * 100}%` }}>
            <strong>{tip.name}</strong>
            <span>{tip.count} pessoas · espera {tip.wait_min} min</span>
          </div>
        );
      })()}
    </div>
  );
}

function ChartLegend() {
  return <span className="legend"><span><i className="sw-today" />Hoje</span><span><i className="sw-avg" />Média (4 semanas)</span></span>;
}

const CW = 616, CH = 236, BASE = 210, TOP = 48;

/** Barras 05h–22h: horas fechadas (hoje), a atual ao vivo, as seguintes = previsão (média das 4 semanas). */
function HourlyChart({ hourly, hour, now }: { hourly: Snapshot["hourly"]; hour: number; now: number }) {
  const value = (h: Snapshot["hourly"][number]) => (h.hour === hour ? now : h.hour < hour ? h.today ?? h.avg_4w : h.avg_4w);
  const max = Math.max(...hourly.map((h) => Math.max(value(h), h.avg_4w))) * 1.05;
  const step = CW / hourly.length;
  const y = (v: number) => BASE - (v / max) * (BASE - TOP);
  const cx = (i: number) => i * step + step / 2;
  const iNow = hourly.findIndex((h) => h.hour === hour);
  return (
    <svg className="chart" viewBox={`0 0 ${CW} ${CH}`} role="img" aria-label="Fluxo de pessoas por hora, hoje e média de 4 semanas">
      {[0.33, 0.66, 1].map((f) => <line key={f} x1="0" x2={CW} y1={BASE - f * (BASE - TOP)} y2={BASE - f * (BASE - TOP)} stroke="var(--concrete-rule)" />)}
      <line x1="0" x2={CW} y1={BASE} y2={BASE} stroke="var(--totem-ink)" />
      {hourly.map((h, i) => {
        const v = value(h);
        const future = h.hour > hour;
        return (
          <g key={h.hour}>
            <rect x={cx(i) - 11} y={y(v)} width="22" height={BASE - y(v)} rx="1" fill={future ? "var(--concrete-rule)" : "var(--totem-ink)"} />
            {h.hour === hour && <rect x={cx(i) - 11} y={y(v) - 4} width="22" height="4" fill="var(--signal-yellow)" />}
            <text x={cx(i)} y={CH - 6} className={`chart__x${h.hour === hour ? " chart__x--now" : ""}`}>{String(h.hour).padStart(2, "0")}h</text>
          </g>
        );
      })}
      <polyline fill="none" stroke="var(--sptrans-blue)" strokeWidth="2" strokeDasharray="6 4"
        points={hourly.map((h, i) => `${cx(i)},${y(h.avg_4w)}`).join(" ")} />
      {iNow >= 0 && (
        <g>
          <line x1={cx(iNow) + step / 2} x2={cx(iNow) + step / 2} y1="4" y2={BASE} stroke="var(--ink-muted)" strokeDasharray="2 3" />
          <text x={cx(iNow) + step / 2 + 6} y="12" className="chart__forecast">PREVISÃO</text>
          <g transform={`translate(${cx(iNow)} ${y(now) - 14})`}>
            <rect x="-40" y="-17" width="80" height="20" fill="var(--signal-yellow)" />
            <text y="-3" className="chart__now">Agora · {fmt(now)}</text>
          </g>
        </g>
      )}
    </svg>
  );
}

function AutoRule({ extras }: { extras: number }) {
  return (
    <div className="rule">
      <div className="rule__flow">
        <span className="rule__tag">SE</span><p>Lotação do ponto &gt; 20 pessoas por mais de 5 min</p>
        <span className="rule__tag">ENTÃO</span><p>Alertar a garagem mais próxima e sugerir ônibus extra na linha com maior demanda</p>
      </div>
      <div className="rule__stats">
        <div><span className="t-metric">{extras}</span><span>disparos hoje</span></div>
        <div><span className="t-metric">−9%</span><span>km ocioso no mês</span></div>
        <div><span className="t-metric">4 min</span><span>ganho médio de espera</span></div>
      </div>
      <p className="rule__note">Dados ilustrativos — simulação para validação (Sprint 2).</p>
    </div>
  );
}

export function ConfirmDialog({ stop, onCancel, onConfirm }: { stop: StopRow; onCancel: () => void; onConfirm: () => void }) {
  const ok = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    ok.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onCancel]);
  return (
    <div className="overlay" onClick={onCancel}>
      <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="dlg-title" onClick={(e) => e.stopPropagation()}>
        <header className="dialog__band"><span className="dialog__mark" /><span className="t-title">Confirmar envio</span></header>
        <div className="dialog__body">
          <h2 id="dlg-title" className="t-heading">Enviar 1 ônibus extra na linha {stop.line}?</h2>
          <p>Saída: {GARAGE} → {stop.name}<br />ETA estimado: {ETA_MIN} min · lotação atual do ponto: {stop.count} pessoas</p>
          <div className="dialog__actions">
            <Button variant="secondary" onClick={onCancel}>Cancelar</Button>
            <Button ref={ok} onClick={onConfirm}>Confirmar envio</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
