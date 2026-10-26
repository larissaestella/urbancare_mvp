import { simLabel, useSnapshot } from "./api";
import { NAV, go } from "./Overview";
import { HighlightPill, KpiStrip, LineChip, LivePill, OkPill, Plate, Sidebar, TitlePlate } from "./ui";
import limitLegend from "./assets/limit-legend.svg";
import limitLine from "./assets/limit-line.svg";
import "./overview.css";
import "./frota.css";

/* Frota (Figma 04, nó 32:110). Texto verbatim do Figma; só o relógio vem da simulação (§8.3) e o rótulo de dados segue §8.1.
   Os números são estáticos: o contador de extras da Visão geral é ao vivo e não conversa com esta tela. */
const ENVIOS = [
  { at: "18:42", line: "875A", route: "Garagem Vila Mariana → Av. Paulista, 1578", note: "ETA 9 min", done: false },
  { at: "18:31", line: "6450", route: "Garagem Santo Amaro → Terminal Sto. Amaro · Pl. 3", note: "ETA 6 min", done: false },
  { at: "18:24", line: "177H", route: "Garagem Pinheiros → R. da Consolação, 900", note: "ETA 4 min", done: false },
  { at: "17:58", line: "7272", route: "Garagem Pinheiros → Av. Rebouças, 1200", note: "chegou às 18:09", done: true },
  { at: "17:12", line: "875A", route: "Garagem Vila Mariana → Av. Paulista, 1578", note: "chegou às 17:21", done: true },
];
const GARAGENS = [["Vila Mariana", 6, 1], ["Santo Amaro", 4, 1], ["Pinheiros", 5, 1], ["Butantã", 3, 0]] as const;
const OCUPACAO = [["875A", 82], ["6450", 74], ["177H", 68], ["7272", 51]] as const;
const LIMITE = 80;
// altura em px no Figma (índice 100 → 104 px, cada ponto = 2,6 px); o eixo não começa em zero
const KM = [["Sem 1", 100, 104], ["Sem 2", 97, 96.2], ["Sem 3", 94, 88.4], ["Sem 4", 91, 80.6]] as const;

export default function Frota() {
  const snap = useSnapshot();
  return (
    <div className="app">
      <Sidebar items={NAV} active="Frota" onNavigate={go} />
      <main className="ov">
        <TitlePlate title="Frota" meta="Concessionária Via Sul · 4 garagens · 186 ônibus em operação"
          right={<div className="ov__head"><LivePill />{snap && <span className="ov__clock">{simLabel(snap.clock.sim_now)}</span>}</div>} />
        <KpiStrip cells={[
          { label: "Ônibus em operação", value: "186", delta: "3 extras em rota agora", tone: "neutral" },
          { label: "Ônibus extras enviados hoje", value: "12", delta: "9 concluídos · 3 a caminho", tone: "pos" },
          { label: "Km rodado ocioso no mês", value: "−9%", delta: "vs. mês anterior", tone: "pos" },
          { label: "Tempo médio até o ponto", value: "8 min", delta: "do alerta à chegada do extra", tone: "neutral" },
        ]} />
        <div className="fr-row">
          <Plate title="Envios de ônibus extra — hoje" right={<span className="fr-band-note">Últimos 5 de 12 envios</span>}>
            <ul className="fr-envios">
              {ENVIOS.map((e) => (
                <li key={e.at}>
                  <span className="fr-envios__at">{e.at}</span>
                  <div className="fr-envios__main">
                    <div className="fr-envios__route"><LineChip line={e.line} />{e.route}</div>
                    <span className="fr-envios__note">{e.note}</span>
                  </div>
                  {e.done ? <OkPill>Concluído</OkPill> : <HighlightPill>A caminho</HighlightPill>}
                </li>
              ))}
            </ul>
          </Plate>
          <Plate title="Garagens">
            <table className="fr-garagens">
              <thead><tr><th>Garagem</th><th>Disponíveis</th><th>Em rota</th></tr></thead>
              <tbody>{GARAGENS.map(([g, disp, rota]) => <tr key={g}><td>{g}</td><td>{disp}</td><td>{rota}</td></tr>)}</tbody>
            </table>
            <p className="fr-note">Envio sugerido sempre pela garagem mais próxima do ponto em alerta.</p>
          </Plate>
        </div>
        <div className="fr-row">
          <Plate title="Ocupação estimada por linha — agora"
            right={<span className="fr-band-note fr-legend"><img src={limitLegend} alt="" />limite de conforto {LIMITE}%</span>}>
            <div className="fr-occ" role="img" aria-label="Ocupação estimada por linha">
              {OCUPACAO.map(([line, pct]) => (
                <div className="fr-occ__row" key={line}>
                  <LineChip line={line} />
                  <span className="fr-occ__track"><i className={pct > LIMITE ? "is-over" : ""} style={{ width: `${pct}%` }} /></span>
                  <span className="fr-occ__pct">{pct}%</span>
                </div>
              ))}
              <img className="fr-occ__limit" src={limitLine} alt="" />
            </div>
            <p className="fr-occ__msg">Linha 875A acima do limite de conforto — próximo extra já a caminho.</p>
          </Plate>
          <Plate title="Km rodado ocioso — últimas 4 semanas">
            <p className="fr-note fr-note--top">Índice de km sem passageiros (semana 1 = 100)</p>
            <div className="fr-km" role="img" aria-label="Índice de km ocioso: 100, 97, 94, 91">
              {KM.map(([wk, v, h], i) => (
                <div key={wk} className="fr-km__col">
                  <div className="fr-km__plot"><b>{v}</b><i className={i === KM.length - 1 ? "is-last" : ""} style={{ height: h }} /></div>
                  <span>{wk}</span>
                </div>
              ))}
            </div>
            <p className="fr-km__total"><strong>−9%</strong><span>km ocioso no mês</span></p>
            <p className="fr-foot">Dados ilustrativos — simulação para validação (Sprint 2).</p>
          </Plate>
        </div>
      </main>
    </div>
  );
}
