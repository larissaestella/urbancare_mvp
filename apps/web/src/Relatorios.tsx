import { useEffect, useState } from "react";
import { NAV, go } from "./Overview";
import { Button, HighlightPill, KpiStrip, LockIcon, OkPill, Plate, Sidebar, StatusShape, TitlePlate, Toggle } from "./ui";
import checkList from "./assets/check-list.svg";
import checkToast from "./assets/check-toast.svg";
import "./overview.css";
import "./relatorios.css";

/* Relatórios (Figma 05, nó 32:111; toast do nó 10:212). Texto verbatim do Figma; rótulo de dados segue §8.1.
   "Gerar relatório" mostra o toast do Figma; "Baixar PDF" avisa que o arquivo entra com os dados do piloto. */
const RECENTES = [
  ["Comprovação de campanha · Marca Aurora", "Marca Aurora", "17/08 – 13/09", "Auditado"],
  ["Operação semanal · Via Sul", "Concessionária Via Sul", "24/08 – 30/08", "Auditado"],
  ["Audiência semanal · 38 painéis", "Mídia OOH", "24/08 – 30/08", "Auditado"],
  ["Envios automáticos · agosto", "Concessionária Via Sul", "01/08 – 31/08", "Em geração"],
  ["SLA de atendimento · agosto", "Gestão pública (fiscalização)", "01/08 – 31/08", "Rascunho"],
];
const AGENDA = [
  ["Operação semanal · Via Sul", "Toda segunda, 07h · envio para a concessionária"],
  ["Audiência semanal · Mídia OOH", "Toda segunda, 08h · 38 painéis"],
  ["Comprovação de campanha", "Ao fim de cada campanha · envio à marca"],
  ["SLA mensal · gestão pública", "Dia 1, 09h · qualidade do atendimento por linha"],
];
const CONTEUDO = [
  "Pessoas por ponto e faixa horária",
  "Tempo de espera e tempo de exposição ao anúncio",
  "Envios automáticos e km rodado ocioso",
  "Impressões entregues vs. contratadas",
];

type Toast = { kind: "report" } | { kind: "info"; text: string };

export default function Relatorios() {
  const [toast, setToast] = useState<Toast | null>(null);
  const [agenda, setAgenda] = useState([true, true, true, false]);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  return (
    <div className="app">
      <Sidebar items={NAV} active="Relatórios" onNavigate={go} />
      <main className="ov">
        <TitlePlate title="Relatórios" meta="Relatórios periódicos para concessionárias, anunciantes e gestão pública"
          right={<Button onClick={() => setToast({ kind: "report" })}>Gerar relatório</Button>} />
        <KpiStrip cells={[
          { label: "Relatórios gerados no mês", value: "14", delta: "3 a mais que julho", tone: "pos" },
          { label: "Auditados", value: "11", delta: "de 14 no mês", tone: "neutral" },
          { label: "Enviados às marcas", value: "6", delta: "2 campanhas em veiculação", tone: "neutral" },
          { label: "Próximo envio automático", value: "Seg 07h", delta: "Operação semanal · Via Sul", tone: "neutral" },
        ]} />
        <Plate title="Relatórios recentes" right={<span className="rl-band-note">Agosto</span>}>
          <table className="rl-table">
            <thead><tr><th>Relatório</th><th>Destinatário</th><th>Período</th><th>Status</th><th /></tr></thead>
            <tbody>
              {RECENTES.map(([name, to, period, status]) => (
                <tr key={name}>
                  <td>{name}</td><td>{to}</td><td>{period}</td>
                  <td>{status === "Auditado" ? <OkPill>{status}</OkPill> : <HighlightPill>{status}</HighlightPill>}</td>
                  <td><Button variant="secondary" onClick={() => setToast({ kind: "info", text: "O PDF do relatório entra com os dados reais do piloto." })}>Baixar PDF</Button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Plate>
        <div className="rl-row">
          <Plate title="Agendamentos">
            <ul className="rl-agenda">
              {AGENDA.map(([title, when], i) => (
                <li key={title}>
                  <div><strong>{title}</strong><span>{when}</span></div>
                  <Toggle on={agenda[i]} label={title} onChange={(v) => setAgenda((a) => a.map((x, j) => (j === i ? v : x)))} />
                </li>
              ))}
            </ul>
          </Plate>
          <Plate title="Conteúdo dos relatórios">
            <ul className="rl-content">
              {CONTEUDO.map((c) => <li key={c}><img src={checkList} alt="" />{c}</li>)}
            </ul>
            <p className="rl-privacy"><LockIcon />Nenhuma imagem — só números agregados</p>
            <p className="rl-foot">Dados ilustrativos — simulação para validação (Sprint 2).</p>
          </Plate>
        </div>
      </main>
      {toast?.kind === "report" && (
        <div className="rl-toast" role="status">
          <span className="rl-toast__badge"><img src={checkToast} alt="" /></span>
          <div><strong>Relatório gerado</strong><span>PDF auditado da campanha pronto para enviar à marca</span></div>
        </div>
      )}
      {toast?.kind === "info" && (
        <div className="toast rl-toast--info" role="status"><StatusShape status="normal" color="var(--info-blue-on-ink)" />{toast.text}</div>
      )}
    </div>
  );
}
