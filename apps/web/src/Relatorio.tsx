import { useEffect } from "react";
import { DATES, DAYS, MONTH_WEEKS, RANKING, RANK_WEEK, SLOTS, WEEK_TOTAL, dayPeople, mil, resumo, slotPeople, type Periodo } from "./audiencia";
import { LockIcon, OkPill } from "./ui";
import "./relatorio.css";

/* Relatório imprimível (/relatorios/ver). O PDF sai pelo "Salvar como PDF" da impressão do navegador, sem dependência nova.
   Seções = "Conteúdo dos relatórios" do Figma 05. Números ilustrativos derivados dos verbatim (PLANO §8.6):
   audiência de audiencia.ts; envios da semana somam 71 (o mês, 268); km ocioso e tempo até o ponto vêm da Frota. */
export type Tipo = "diario" | "semanal" | "mensal" | "campanha";
const DIA = 4; // sexta 28/08, o último dia útil fechado antes do relógio de sim (seg 31/08)

export const TIPO: Record<Tipo, { nome: string; periodo: string; audiencia: Periodo }> = {
  diario: { nome: "Relatório diário", periodo: `${DAYS[DIA]} ${DATES[DIA]}`, audiencia: "Diária" },
  semanal: { nome: "Relatório semanal", periodo: "24/08 – 30/08", audiencia: "Semanal" },
  mensal: { nome: "Relatório mensal", periodo: "agosto (03/08 – 30/08)", audiencia: "Mensal" },
  campanha: { nome: "Comprovação de campanha", periodo: "17/08 – 13/09 · entregue até 30/08", audiencia: "Semanal" },
};
const ENVIOS_SEMANA = [13, 12, 14, 13, 14, 4, 1]; // soma 71
const ENVIOS_MES = [["03–09/08", 61], ["10–16/08", 64], ["17–23/08", 72], ["24–30/08", 71]] as const; // soma 268
const OPS: Record<Exclude<Tipo, "campanha">, { espera: number; envios: number; km: string; kmNote: string }> = {
  diario: { espera: 9, envios: ENVIOS_SEMANA[DIA], km: "91", kmNote: "índice da semana (semana 1 = 100)" },
  semanal: { espera: 9, envios: ENVIOS_SEMANA.reduce((a, b) => a + b, 0), km: "91", kmNote: "índice (semana 1 = 100) · −3 vs. semana anterior" },
  mensal: { espera: 10, envios: ENVIOS_MES.reduce((a, [, v]) => a + v, 0), km: "−9%", kmNote: "vs. mês anterior" },
};
const CAMPANHA_SEMANAS = [["17–23/08", 161_000], ["24–30/08", 175_000]] as const; // soma 336 mil

export const reportUrl = (tipo: Tipo, titulo: string, dest: string, print = true) =>
  `/relatorios/ver?${new URLSearchParams({ tipo, titulo, dest, ...(print ? { print: "1" } : {}) })}`;

export default function Relatorio() {
  const q = new URLSearchParams(location.search);
  const tipo = (q.get("tipo") as Tipo) in TIPO ? (q.get("tipo") as Tipo) : "semanal";
  const t = TIPO[tipo];
  const titulo = q.get("titulo") || t.nome;
  const dest = q.get("dest") || "Concessionária Via Sul";

  useEffect(() => {
    document.title = `${titulo} · UrbanFlow`;
    if (q.get("print") === "1") window.setTimeout(() => window.print(), 400);
  }, []);

  return (
    <div className="rp">
      <div className="rp-actions">
        <a className="btn btn--secondary rp-actions__back" href="/relatorios">← Relatórios</a>
        <button className="btn btn--primary" onClick={() => window.print()}>Imprimir / salvar PDF</button>
      </div>
      <article className="rp-sheet">
        <header className="rp-head">
          <div className="rp-head__brand">UrbanFlow · {t.nome}</div>
          <h1 className="t-display">{titulo}</h1>
          <dl className="rp-meta">
            <div><dt>Destinatário</dt><dd>{dest}</dd></div>
            <div><dt>Período</dt><dd>{t.periodo}</dd></div>
            <div><dt>Gerado em</dt><dd>31/08 · 18:42</dd></div>
            <div><dt>Status</dt><dd><OkPill>Auditado</OkPill></dd></div>
          </dl>
        </header>
        {tipo === "campanha" ? <Campanha /> : <Operacao tipo={tipo} />}
        <footer className="rp-foot">
          <p className="rp-privacy"><LockIcon />Nenhuma imagem — só números agregados</p>
          <p>Dados ilustrativos — simulação para validação (Sprint 2).</p>
        </footer>
      </article>
    </div>
  );
}

function Operacao({ tipo }: { tipo: Exclude<Tipo, "campanha"> }) {
  const t = TIPO[tipo], ops = OPS[tipo], aud = resumo(t.audiencia, DIA);
  const scale = aud.people / WEEK_TOTAL;
  const faixas: readonly (readonly [string, number])[] = tipo === "diario" ? SLOTS.map((s, r) => [s, slotPeople(DIA)[r]] as const)
    : tipo === "semanal" ? DAYS.map((d, c) => [d, dayPeople(c)] as const) : MONTH_WEEKS;
  const envios: readonly (readonly [string, number])[] = tipo === "diario" ? [] : tipo === "semanal"
    ? DAYS.map((d, i) => [d, ENVIOS_SEMANA[i]] as const) : ENVIOS_MES;
  return (
    <>
      <Section n={1} title="Pessoas por ponto e faixa horária">
        <div className="rp-two">
          <table className="rp-table">
            <thead><tr><th>Ponto (top 5 de 38 painéis)</th><th>Pessoas</th></tr></thead>
            <tbody>{RANKING.map(([name], i) => <tr key={name}><td>{name}</td><td>{mil(RANK_WEEK[i] * scale)}</td></tr>)}</tbody>
          </table>
          <Bars title={tipo === "diario" ? "Por faixa horária" : tipo === "semanal" ? "Por dia" : "Por semana"} bars={faixas} fmt={mil} />
        </div>
      </Section>
      <Section n={2} title="Tempo de espera e tempo de exposição ao anúncio">
        <div className="rp-stats">
          <Stat value={`${ops.espera} min`} label={`espera média · meta 8 min (+${ops.espera - 8})`} />
          <Stat value={aud.exposure} label="exposição média ao anúncio" />
          <Stat value={aud.qualified} label="audiência qualificada (≥ 30s)" />
          <Stat value={mil(aud.people)} label="pessoas expostas" />
        </div>
      </Section>
      <Section n={3} title="Envios automáticos e km rodado ocioso">
        <div className="rp-stats">
          <Stat value={String(ops.envios)} label="ônibus extras enviados" />
          <Stat value="8 min" label="do alerta à chegada do extra" />
          <Stat value={ops.km} label={`km ocioso · ${ops.kmNote}`} />
        </div>
        {envios.length > 0 && <Bars title="Envios por período" bars={envios} fmt={String} />}
      </Section>
      <Section n={4} title="Impressões entregues vs. contratadas">
        <Impressoes />
      </Section>
    </>
  );
}

function Campanha() {
  return (
    <>
      <Section n={1} title="Impressões entregues vs. contratadas">
        <Impressoes />
        <Bars title="Impressões por semana" bars={CAMPANHA_SEMANAS} fmt={mil} />
      </Section>
      <Section n={2} title="Exposição e audiência">
        <div className="rp-stats">
          <Stat value="6m 50s" label="exposição média" />
          <Stat value="71%" label="audiência qualificada" />
          <Stat value="18–21h" label="melhor faixa" />
          <Stat value="12" label="painéis da campanha" />
        </div>
      </Section>
      <Section n={3} title="Painéis com mais audiência">
        <table className="rp-table">
          <thead><tr><th>Painel</th><th>Pessoas</th><th>Tempo méd.</th><th>CPM sug.</th></tr></thead>
          <tbody>{RANKING.map(([name, people, time, cpm]) => <tr key={name}><td>{name}</td><td>{people}</td><td>{time}</td><td>{cpm}</td></tr>)}</tbody>
        </table>
      </Section>
    </>
  );
}

function Impressoes() {
  return (
    <div className="rp-imp">
      <div className="rp-imp__row"><span>Marca Aurora · Lançamento tênis · 12 painéis</span><strong>336 mil / 300 mil · 112%</strong></div>
      <div className="rp-imp__bar" aria-hidden="true"><i style={{ left: `${(300 / 336) * 100}%` }} /></div>
    </div>
  );
}

function Section({ n, title, children }: { n: number; title: string; children: React.ReactNode }) {
  return (
    <section className="rp-sec">
      <h2 className="t-title rp-sec__title"><span>{n}</span>{title}</h2>
      {children}
    </section>
  );
}

const Stat = ({ value, label }: { value: string; label: string }) =>
  <div className="rp-stat"><strong>{value}</strong><span>{label}</span></div>;

function Bars({ title, bars, fmt }: { title: string; bars: readonly (readonly [string, number])[]; fmt: (n: number) => string }) {
  const max = Math.max(...bars.map(([, v]) => v));
  return (
    <div className="rp-bars">
      <div className="t-overline rp-bars__title">{title}</div>
      {bars.map(([l, v]) => (
        <div className="rp-bars__row" key={l}>
          <span>{l}</span><span className="rp-bars__track"><i style={{ width: `${(v / max) * 100}%` }} /></span><strong>{fmt(v)}</strong>
        </div>
      ))}
    </div>
  );
}
