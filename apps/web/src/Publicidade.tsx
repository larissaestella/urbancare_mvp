import { useEffect, useState } from "react";
import { NAV, go } from "./Overview";
import { call } from "./api";
import { reportUrl } from "./Relatorio";
import { Button, KpiStrip, Plate, Segmented, Sidebar, StatusShape } from "./ui";
import "./overview.css";
import "./publicidade.css";
import { allPanels, DATES, DAYS, HEAT, HEAT_TOTAL, JULY_TOTAL, MONTH_TOTAL, MONTH_WEEKS, PEAK_INDEX, RANKING, RANK_WEEK, SLOTS, WEEK_TOTAL, colSum, dayPeople, delta, mil, pct, resumo, slotPeople, type Periodo } from "./audiencia";

/* Audiência dos painéis (render 03). Semanal é verbatim do render: o protótipo não mede exposição ao anúncio nem tem campanhas.
   Exportar baixa o CSV do período escolhido; o relatório auditado abre o PDF da campanha (/relatorios/ver);
   compartilhar copia o link desse relatório (PLANO §8.6). */
const RANGES: Periodo[] = ["Diária", "Semanal", "Mensal"];
type Range = Periodo;

function kpis(range: Range, day: number) {
  if (range === "Semanal") return null;
  const r = resumo(range, day);
  if (range === "Diária") {
    const peak = colSum(day) >= HEAT_TOTAL / 7;
    return [
      { label: "Pessoas expostas aos anúncios", value: mil(r.people), delta: `${delta(pct(r.people, WEEK_TOTAL / 7))} vs. média diária da semana`, tone: peak ? "pos" : "neg" },
      { label: "Tempo médio de exposição", value: r.exposure, delta: "por pessoa no ponto", tone: "neutral" },
      { label: "Audiência qualificada", value: r.qualified, delta: "ficaram ≥ 30s de frente ao painel", tone: "warn" },
      { label: "CPM sugerido (auditado)", value: r.cpm, delta: peak ? "dia de pico · faixa premium" : "fora do pico", tone: "info" },
    ] as const;
  }
  return [
    { label: "Pessoas expostas aos anúncios", value: mil(r.people), delta: `${delta(pct(r.people, JULY_TOTAL))} vs. julho`, tone: "pos" },
    { label: "Tempo médio de exposição", value: r.exposure, delta: "por pessoa no ponto", tone: "neutral" },
    { label: "Audiência qualificada", value: r.qualified, delta: "ficaram ≥ 30s de frente ao painel", tone: "warn" },
    { label: "CPM sugerido (auditado)", value: r.cpm, delta: "▲ vs. R$ 9,00 estimado hoje", tone: "info" },
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
  const [todos, setTodos] = useState(false);

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
            <Button onClick={() => { exportCsv(range, day); setToast(`Relatório ${range.toLowerCase()} exportado em CSV.`); }}>Exportar relatório ↓</Button>
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
          <Plate title="Ranking de painéis" right={<button className="band-link pb-link" onClick={() => setTodos(true)}>Ver todos →</button>}>
            <Ranking scale={scale} />
          </Plate>
        </div>
        <div className="pb-bottom">
          <Campaign onAction={(what) => {
            const url = reportUrl("campanha", "Comprovação de campanha · Marca Aurora", "Marca Aurora", what === "pdf");
            if (what === "pdf") return void window.open(url, "_blank");
            navigator.clipboard?.writeText(location.origin + url).catch(() => {});
            setToast("Link do relatório auditado copiado — pronto para enviar à Marca Aurora.");
          }} />
          <Plate title="Como a venda do anúncio muda"><Compare /></Plate>
        </div>
      </main>
      {todos && <AllPanels scale={scale} period={META[range](day).split(" · ").pop()!} onClose={() => setTodos(false)} />}
      {toast && <div className="toast toast--info" role="status"><StatusShape status="normal" color="var(--info-blue-on-ink)" />{toast}</div>}
    </div>
  );
}

/** CSV do período (separador ";" e vírgula decimal, como o Excel em pt-BR abre direto). */
function exportCsv(range: Range, day: number) {
  const scale = range === "Diária" ? dayPeople(day) / WEEK_TOTAL : range === "Mensal" ? MONTH_TOTAL / WEEK_TOTAL : 1;
  const period = META[range](day).split(" · ").pop()!;
  const r = resumo(range, day);
  const by: readonly (readonly [string, number])[] = range === "Diária" ? SLOTS.map((s, i) => [s, slotPeople(day)[i]] as const)
    : range === "Semanal" ? DAYS.map((d, c) => [d, dayPeople(c)] as const) : MONTH_WEEKS;
  const lines = [
    ["UrbanFlow · Audiência dos painéis", period], [],
    ["Pessoas expostas", Math.round(r.people)], ["Tempo médio de exposição", r.exposure], ["Audiência qualificada", r.qualified], ["CPM sugerido", r.cpm], [],
    [range === "Diária" ? "Faixa horária" : range === "Semanal" ? "Dia" : "Semana", "Pessoas"], ...by.map(([l, v]) => [l, Math.round(v)]), [],
    ["Painel", "Pessoas", "Tempo médio", "CPM sugerido"], ...RANKING.map(([n, , t, c], i) => [n, Math.round(RANK_WEEK[i] * scale), t, c]), [],
    ["Dados ilustrativos — simulação para validação (Sprint 2)."],
  ];
  const csv = "\ufeff" + lines.map((l) => l.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(";")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  a.download = `urbanflow-audiencia-${range.toLowerCase()}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

function AllPanels({ scale, period, onClose }: { scale: number; period: string; onClose: () => void }) {
  const [names, setNames] = useState<string[] | null>(null);
  useEffect(() => {
    call<{ name: string }[]>("GET", "/stops").then((r) => setNames(r.map((s) => s.name)), () => setNames([]));
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);
  const panels = names ? allPanels(names) : [];
  return (
    <div className="overlay" onClick={onClose}>
      <div className="dialog pb-all" role="dialog" aria-modal="true" aria-labelledby="pb-all-title" onClick={(e) => e.stopPropagation()}>
        <header className="dialog__band"><span className="dialog__mark" /><h2 id="pb-all-title" className="t-title">Todos os painéis · {period}</h2>
          <button className="pb-all__close" aria-label="Fechar" onClick={onClose}>×</button></header>
        <div className="pb-all__body">
          <table className="pb-rank">
            <thead><tr><th>#</th><th>Painel</th><th>Pessoas</th><th>Tempo méd.</th><th>CPM sug.</th></tr></thead>
            <tbody>{panels.map((p, i) => <tr key={`${p.name}-${i}`}><td>{i + 1}</td><td>{p.name}</td><td>{mil(p.week * scale)}</td><td>{p.time}</td><td>{p.cpm}</td></tr>)}</tbody>
          </table>
          {!names && <p className="pb-empty">Carregando painéis…</p>}
        </div>
      </div>
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

function Campaign({ onAction }: { onAction: (what: "pdf" | "share") => void }) {
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
        <Button onClick={() => onAction("pdf")}>Gerar relatório auditado (PDF)</Button>
        <Button variant="secondary" onClick={() => onAction("share")}>Compartilhar com a marca</Button>
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
