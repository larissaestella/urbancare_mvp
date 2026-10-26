import { useEffect, useState } from "react";
import { NAV, go } from "./Overview";
import { Button, KpiStrip, Plate, Segmented, Sidebar, StatusShape } from "./ui";
import "./overview.css";
import "./publicidade.css";

/* Audiência dos painéis (render 03). Semanal é verbatim do render: o protótipo não mede exposição ao anúncio nem tem campanhas.
   Exportar, relatório auditado e compartilhar não geram nada; mostram aviso de que entram com os dados do piloto. */
const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
const SLOTS = ["06–09h", "09–12h", "12–15h", "15–18h", "18–21h", "21–24h"];
// tom 1–5 (--data-1 … --data-5) lido do render; só a faixa 18–21h de seg a qui traz o índice impresso
const HEAT = [
  [5, 5, 5, 5, 4, 2, 1],
  [3, 2, 2, 2, 3, 3, 2],
  [3, 3, 3, 3, 3, 4, 3],
  [4, 3, 4, 4, 4, 3, 2],
  [5, 5, 5, 5, 5, 3, 2],
  [1, 1, 1, 1, 3, 2, 1],
];
const PEAK_INDEX: Record<string, number> = { "4-0": 100, "4-1": 96, "4-2": 98, "4-3": 95 };
const RANKING = [
  ["Av. Paulista, 1578", "28,4 mil", "9m 10s", "R$ 18,90"],
  ["Terminal Sto. Amaro", "24,1 mil", "8m 30s", "R$ 16,40"],
  ["R. da Consolação, 900", "19,7 mil", "7m 55s", "R$ 14,80"],
  ["Av. Rebouças, 1200", "16,2 mil", "6m 20s", "R$ 12,10"],
  ["Av. Brig. Faria Lima, 2000", "14,9 mil", "5m 45s", "R$ 11,30"],
];
const RANGES = ["Diária", "Semanal", "Mensal"] as const;
type Range = (typeof RANGES)[number];
const PILOT = "entra com os dados reais do piloto.";

/* Diária e Mensal: ilustrativos (pedido do Rafael, 26/10), derivados dos números verbatim da semana.
   Cada dia leva a fatia da semana proporcional à soma da sua coluna no mapa de calor (os 7 dias somam 412 mil);
   o mês é a soma das 4 semanas de agosto, a última sendo a semana do render. */
const WEEK_TOTAL = 412_000;
const DATES = ["24/08", "25/08", "26/08", "27/08", "28/08", "29/08", "30/08"];
const colSum = (c: number) => HEAT.reduce((a, row) => a + row[c], 0);
const HEAT_TOTAL = DAYS.reduce((a, _, c) => a + colSum(c), 0);
const dayPeople = (c: number) => (WEEK_TOTAL * colSum(c)) / HEAT_TOTAL;
const slotPeople = (c: number) => SLOTS.map((_, r) => (dayPeople(c) * HEAT[r][c]) / colSum(c));
const MONTH_WEEKS = [["03–09/08", 338_000], ["10–16/08", 352_000], ["17–23/08", 368_000], ["24–30/08", WEEK_TOTAL]] as const;
const MONTH_TOTAL = MONTH_WEEKS.reduce((a, [, v]) => a + v, 0);
const JULY_TOTAL = 1_290_000;
const RANK_WEEK = [28_400, 24_100, 19_700, 16_200, 14_900];

export const mil = (n: number) => n >= 1_000_000
  ? `${(n / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} mi`
  : `${(n / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} mil`;
const pct = (a: number, b: number) => Math.round((a / b - 1) * 100);
const delta = (p: number) => `${p >= 0 ? "▲" : "▼"} ${Math.abs(p)}%`;

function kpis(range: Range, day: number) {
  if (range === "Semanal") return null;
  if (range === "Diária") {
    const share = colSum(day) / (HEAT_TOTAL / 7);
    return [
      { label: "Pessoas expostas aos anúncios", value: mil(dayPeople(day)), delta: `${delta(pct(dayPeople(day), WEEK_TOTAL / 7))} vs. média diária da semana`, tone: share >= 1 ? "pos" : "neg" },
      { label: "Tempo médio de exposição", value: share >= 1 ? "7m 55s" : "6m 50s", delta: "por pessoa no ponto", tone: "neutral" },
      { label: "Audiência qualificada", value: share >= 1 ? "70%" : "63%", delta: "ficaram ≥ 30s de frente ao painel", tone: "warn" },
      { label: "CPM sugerido (auditado)", value: share >= 1 ? "R$ 15,10" : "R$ 11,60", delta: share >= 1 ? "dia de pico · faixa premium" : "fora do pico", tone: "info" },
    ] as const;
  }
  return [
    { label: "Pessoas expostas aos anúncios", value: mil(MONTH_TOTAL), delta: `${delta(pct(MONTH_TOTAL, JULY_TOTAL))} vs. julho`, tone: "pos" },
    { label: "Tempo médio de exposição", value: "7m 25s", delta: "por pessoa no ponto", tone: "neutral" },
    { label: "Audiência qualificada", value: "66%", delta: "ficaram ≥ 30s de frente ao painel", tone: "warn" },
    { label: "CPM sugerido (auditado)", value: "R$ 13,80", delta: "▲ vs. R$ 9,00 estimado hoje", tone: "info" },
  ] as const;
}

const META: Record<Range, (day: number) => string> = {
  "Diária": (d) => `Mídia OOH · 38 painéis em pontos de ônibus · ${DAYS[d].toLowerCase()} ${DATES[d]}`,
  "Semanal": () => "Mídia OOH · 38 painéis em pontos de ônibus · semana 24/08 – 30/08",
  "Mensal": () => "Mídia OOH · 38 painéis em pontos de ônibus · agosto (03/08 – 30/08)",
};

export default function Publicidade() {
  const [range, setRange] = useState<Range>("Semanal");
  const [day, setDay] = useState(4); // sexta, o dia de maior audiência
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  const cells = kpis(range, day);
  const scale = range === "Diária" ? dayPeople(day) / WEEK_TOTAL : range === "Mensal" ? MONTH_TOTAL / WEEK_TOTAL : 1;
  return (
    <div className="app">
      <Sidebar items={NAV} active="Publicidade" onNavigate={go} />
      <main className="ov">
        <header className="title-plate">
          <div>
            <h1 className="t-display">Audiência dos painéis</h1>
            <p className="title-plate__meta">{META[range](day)}</p>
          </div>
          <div className="ov__head">
            <Segmented options={[...RANGES]} value={range} onChange={setRange} />
            <Button onClick={() => setToast(`Exportação do relatório ${PILOT}`)}>Exportar relatório ↓</Button>
          </div>
        </header>
        {cells ? <KpiStrip cells={[...cells]} /> : (
          <KpiStrip cells={[
            { label: "Pessoas expostas aos anúncios", value: "412 mil", delta: "▲ 12% vs. semana anterior", tone: "pos" },
            { label: "Tempo médio de exposição", value: "7m 40s", delta: "por pessoa no ponto", tone: "neutral" },
            { label: "Audiência qualificada", value: "68%", delta: "ficaram ≥ 30s de frente ao painel", tone: "warn" },
            { label: "CPM sugerido (auditado)", value: "R$ 14,20", delta: "▲ vs. R$ 9,00 estimado hoje", tone: "info" },
          ]} />
        )}
        <div className="pb-mid">
          {range === "Semanal" && <Plate title="Audiência por dia e faixa horária" right={<HeatLegend />}><Heatmap /></Plate>}
          {range === "Diária" && (
            <Plate title="Audiência por faixa horária" right={<DayPicker day={day} onChange={setDay} />}>
              <Bars bars={SLOTS.map((s, r) => [s, slotPeople(day)[r]] as const)} label={`Audiência por faixa horária, ${DAYS[day]} ${DATES[day]}`} />
              <p className="pb-heat__note">Melhor faixa do dia: {SLOTS[slotPeople(day).indexOf(Math.max(...slotPeople(day)))]}</p>
            </Plate>
          )}
          {range === "Mensal" && (
            <Plate title="Audiência por semana — agosto">
              <Bars bars={MONTH_WEEKS} label="Audiência por semana em agosto" />
              <p className="pb-heat__note">{delta(pct(WEEK_TOTAL, MONTH_WEEKS[0][1]))} da primeira para a última semana do mês</p>
            </Plate>
          )}
          <Plate title="Ranking de painéis" right={<button className="band-link pb-link" onClick={() => setToast(`A lista completa de painéis ${PILOT}`)}>Ver todos →</button>}>
            <Ranking scale={scale} />
          </Plate>
        </div>
        <div className="pb-bottom">
          <Campaign onAction={(what) => setToast(`${what} ${PILOT}`)} />
          <Plate title="Como a venda do anúncio muda"><Compare /></Plate>
        </div>
      </main>
      {toast && <div className="toast toast--info" role="status"><StatusShape status="normal" color="var(--info-blue-on-ink)" />{toast}</div>}
    </div>
  );
}

function DayPicker({ day, onChange }: { day: number; onChange: (d: number) => void }) {
  return (
    <span className="pb-days" role="group" aria-label="Dia da semana">
      {DAYS.map((d, i) => <button key={d} aria-pressed={i === day} onClick={() => onChange(i)}>{d}</button>)}
    </span>
  );
}

/** Barras horizontais de audiência (pessoas), na escala de cor dos dados. */
function Bars({ bars, label }: { bars: readonly (readonly [string, number])[]; label: string }) {
  const max = Math.max(...bars.map(([, v]) => v));
  return (
    <div className="pb-bars" role="img" aria-label={`${label}: ${bars.map(([l, v]) => `${l} ${mil(v)}`).join(", ")}`}>
      {bars.map(([l, v]) => (
        <div className="pb-bars__row" key={l}>
          <span className="pb-bars__label">{l}</span>
          <span className="pb-bars__track"><i style={{ width: `${(v / max) * 100}%`, background: `var(--data-${v === max ? 5 : 4})` }} /></span>
          <span className="pb-bars__value">{mil(v)}</span>
        </div>
      ))}
    </div>
  );
}

function HeatLegend() {
  return (
    <span className="pb-legend">menos{[1, 2, 3, 4, 5].map((n) => <i key={n} style={{ background: `var(--data-${n})` }} />)}mais</span>
  );
}

function Heatmap() {
  return (
    <>
      <table className="pb-heat" aria-label="Audiência por dia da semana e faixa horária">
        <thead><tr><th />{DAYS.map((d) => <th key={d} scope="col">{d}</th>)}</tr></thead>
        <tbody>
          {SLOTS.map((s, r) => (
            <tr key={s}>
              <th scope="row">{s}</th>
              {HEAT[r].map((v, c) => (
                <td key={c} className={v >= 4 ? "is-dark" : ""} style={{ background: `var(--data-${v})` }}>{PEAK_INDEX[`${r}-${c}`]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="pb-heat__note">Pico: dias úteis, 18–21h e 06–09h → faixas premium para precificação</p>
    </>
  );
}

function Ranking({ scale }: { scale: number }) {
  return (
    <table className="pb-rank">
      <thead><tr><th>Painel</th><th>Pessoas</th><th>Tempo méd.</th><th>CPM sug.</th></tr></thead>
      <tbody>
        {RANKING.map(([name, people, time, cpm], i) => (
          <tr key={name}><td>{name}</td><td>{scale === 1 ? people : mil(RANK_WEEK[i] * scale)}</td><td>{time}</td><td>{cpm}</td></tr>
        ))}
      </tbody>
    </table>
  );
}

function Campaign({ onAction }: { onAction: (what: string) => void }) {
  const live = <span className="pill pill--normal"><StatusShape status="normal" color="#fff" />Em veiculação</span>;
  return (
    <Plate title="Comprovação de campanha" right={live}>
      <p className="pb-camp__meta">Marca Aurora · Lançamento tênis · 12 painéis · 17/08 – 13/09</p>
      <div className="pb-camp__row"><span>Impressões entregues vs. contratadas</span><strong>336 mil / 300 mil · 112%</strong></div>
      <div className="pb-camp__bar" aria-hidden="true"><i style={{ left: `${(300 / 336) * 100}%` }} /></div>
      <div className="pb-camp__stats">
        <div><span className="t-metric">6m 50s</span><span>exposição média</span></div>
        <div><span className="t-metric">71%</span><span>audiência qualificada</span></div>
        <div><span className="t-metric">18–21h</span><span>melhor faixa</span></div>
      </div>
      <div className="pb-camp__actions">
        <Button onClick={() => onAction("O relatório auditado (PDF)")}>Gerar relatório auditado (PDF)</Button>
        <Button variant="secondary" onClick={() => onAction("O compartilhamento com a marca")}>Compartilhar com a marca</Button>
      </div>
    </Plate>
  );
}

function Compare() {
  return (
    <>
      <div className="pb-compare">
        <div>
          <div className="t-overline">Hoje (sem dados)</div>
          <ul className="pb-compare__today">
            <li>– Audiência estimada por contagem manual</li><li>– Preço fixo por painel</li><li>– Sem prova para a marca</li>
          </ul>
        </div>
        <div className="pb-compare__uf">
          <div className="t-overline">Com UrbanFlow</div>
          <ul>
            <li>Pessoas e tempo de exposição medidos</li><li>Preço por faixa horária (premium no pico)</li><li>Relatório auditado por campanha</li>
          </ul>
        </div>
      </div>
      <p className="pb-foot">Dados ilustrativos — simulação para validação (Sprint 2).</p>
    </>
  );
}
