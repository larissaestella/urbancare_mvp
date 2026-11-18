import { useEffect, useState } from "react";
import { call, fmt } from "./api";
import { CTA } from "./Landing";
import { KpiStrip, LivePill, Plate, TitlePlate } from "./ui";
import "./landing.css";

type Counts = { visits: number; clicks: number; leads: number; ctr: number | null };
type Metrics = { A: Counts; B: Counts; total: Counts; goal_ctr: number; goal_leads: number;
  recent: { variant: "A" | "B"; company: string; size: number; email: string; created_at: string }[] };

const pct = (x: number | null) => (x === null ? "—" : `${(x * 100).toFixed(1).replace(".", ",")}%`);

/** Smoke test: visitas, cliques no CTA, conversão (cliques ÷ visitas) vs. meta de 15% e leads vs. meta de 3, por variante. */
export default function Conversao() {
  const [m, setM] = useState<Metrics | null>(null);
  useEffect(() => {
    const load = () => call<Metrics>("GET", "/landing/metrics").then(setM, () => {});
    load();
    const t = window.setInterval(load, 2000);
    return () => window.clearInterval(t);
  }, []);

  return (
    <main className="cv">
      <TitlePlate title="Smoke test · conversão da landing" meta={`Meta: conversão no CTA ≥ 15% · ≥ 3 leads em 7 dias`} right={<LivePill />} />
      {m ? <Body m={m} /> : <p className="cv__empty">Carregando…</p>}
    </main>
  );
}

function Body({ m }: { m: Metrics }) {
  const t = m.total;
  const hit = t.ctr !== null && t.ctr >= m.goal_ctr;
  return (
    <>
      <KpiStrip cells={[
        { label: "Visitas", value: fmt(t.visits), delta: "visitantes únicos", tone: "neutral" },
        { label: "Cliques no CTA", value: fmt(t.clicks), delta: "visitantes que clicaram", tone: "neutral" },
        { label: "Conversão no CTA", value: pct(t.ctr), tone: t.ctr === null ? "neutral" : hit ? "pos" : "neg",
          delta: t.ctr === null ? "sem visitas ainda" : `${hit ? "▲ acima" : "▼ abaixo"} da meta (15%)` },
        { label: "Leads", value: `${t.leads} / ${m.goal_leads}`, tone: t.leads >= m.goal_leads ? "pos" : "warn",
          delta: t.leads >= m.goal_leads ? "meta de leads atingida" : `faltam ${m.goal_leads - t.leads} para a meta` },
      ]} />
      <Plate title="Teste A/B do CTA">
        <table>
          <thead><tr className="t-overline"><th>Variante</th><th>Texto do botão</th><th className="num">Visitas</th><th className="num">Cliques</th>
            <th className="num">Conversão</th><th className="num">Leads</th></tr></thead>
          <tbody>
            {(["A", "B"] as const).map((v) => (
              <tr key={v}><td className="t-metric">{v}</td><td className="t-body-strong">{CTA[v]}</td><td className="num">{m[v].visits}</td>
                <td className="num">{m[v].clicks}</td><td className="num t-body-strong">{pct(m[v].ctr)}</td><td className="num">{m[v].leads}</td></tr>
            ))}
          </tbody>
        </table>
      </Plate>
      <Plate title="Leads recentes">
        {m.recent.length === 0 ? <p className="cv__empty">Nenhum lead ainda.</p> : (
          <table>
            <thead><tr className="t-overline"><th>Empresa</th><th className="num">Linhas / pontos</th><th>E-mail corporativo</th><th>Variante</th><th>Recebido</th></tr></thead>
            <tbody>
              {m.recent.map((l) => (
                <tr key={`${l.email}-${l.created_at}`}><td className="t-body-strong">{l.company}</td><td className="num">{fmt(l.size)}</td><td>{l.email}</td>
                  <td>{l.variant}</td><td>{new Date(l.created_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}</td></tr>
              ))}
            </tbody>
          </table>
        )}
      </Plate>
    </>
  );
}
