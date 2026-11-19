import { useEffect, useRef, useState } from "react";
import { NAV, go } from "./Overview";
import { TIPO, type Tipo } from "./Relatorio";
import { downloadReportPdf } from "./downloadReportPdf";
import { Button, HighlightPill, KpiStrip, LockIcon, OkPill, Plate, Segmented, Sidebar, StatusShape, TitlePlate, Toggle } from "./ui";
import checkList from "./assets/check-list.svg";
import checkToast from "./assets/check-toast.svg";
import "./overview.css";
import "./relatorios.css";

/* Relatórios (Figma 05, nó 32:111; toast do nó 10:212). Texto verbatim do Figma; rótulo de dados segue §8.1.
   "Gerar relatório" abre a escolha de tipo e destinatário, acrescenta a linha (Em geração → Auditado) e mostra o toast do Figma;
   "Baixar PDF" gera o arquivo diretamente no navegador a partir do relatório imprimível. */
type Row = { name: string; to: string; period: string; status: string; tipo: Tipo };
const RECENTES: Row[] = [
  { name: "Comprovação de campanha · Marca Aurora", to: "Marca Aurora", period: "17/08 – 13/09", status: "Auditado", tipo: "campanha" },
  { name: "Operação semanal · Via Sul", to: "Concessionária Via Sul", period: "24/08 – 30/08", status: "Auditado", tipo: "semanal" },
  { name: "Audiência semanal · 38 painéis", to: "Mídia OOH", period: "24/08 – 30/08", status: "Auditado", tipo: "semanal" },
  { name: "Envios automáticos · agosto", to: "Concessionária Via Sul", period: "01/08 – 31/08", status: "Em geração", tipo: "mensal" },
  { name: "SLA de atendimento · agosto", to: "Gestão pública (fiscalização)", period: "01/08 – 31/08", status: "Rascunho", tipo: "mensal" },
];
const TIPOS = { "Diário": "diario", "Semanal": "semanal", "Mensal": "mensal", "Campanha": "campanha" } as const;
type TipoLabel = keyof typeof TIPOS;
const DESTS = ["Concessionária Via Sul", "Mídia OOH", "Marca Aurora", "Gestão pública (fiscalização)"];
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

type Toast = { kind: "report"; text: string } | { kind: "info"; text: string };

export default function Relatorios() {
  const [toast, setToast] = useState<Toast | null>(null);
  const [agenda, setAgenda] = useState([true, true, true, false]);
  const [rows, setRows] = useState(RECENTES);
  const [dialog, setDialog] = useState(false);
  const [baixando, setBaixando] = useState(false);
  const novos = rows.length - RECENTES.length;
  const novosAuditados = rows.slice(0, novos).filter((r) => r.status === "Auditado").length;

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  function gerar(label: TipoLabel, to: string) {
    setDialog(false);
    const tipo = TIPOS[label];
    const row: Row = { name: `${TIPO[tipo].nome} · ${to}`, to, period: TIPO[tipo].periodo, status: "Em geração", tipo };
    setRows((rs) => [row, ...rs]);
    window.setTimeout(() => {
      setRows((rs) => rs.map((r) => (r === row ? { ...r, status: "Auditado" } : r)));
      setToast({ kind: "report", text: tipo === "campanha" ? "PDF auditado da campanha pronto para enviar à marca" : `PDF auditado pronto para enviar a ${to}` });
    }, 2500);
  }

  async function baixar(r: Row) {
    if (r.status !== "Auditado") return setToast({ kind: "info", text: `“${r.name}” ainda está ${r.status === "Rascunho" ? "em rascunho" : "em geração"}; o PDF sai quando for auditado.` });
    setBaixando(true);
    try {
      await downloadReportPdf(r.tipo, r.name, r.to);
      setToast({ kind: "info", text: `PDF baixado: ${r.name}` });
    } catch (error) {
      setToast({
        kind: "info",
        text: error instanceof Error ? `Não foi possível baixar o PDF: ${error.message}` : "Não foi possível baixar o PDF.",
      });
    } finally {
      setBaixando(false);
    }
  }

  return (
    <div className="app">
      <Sidebar items={NAV} active="Relatórios" onNavigate={go} />
      <main className="ov">
        <TitlePlate title="Relatórios" meta="Relatórios periódicos para concessionárias, anunciantes e gestão pública"
          right={<Button onClick={() => setDialog(true)}>Gerar relatório</Button>} />
        <KpiStrip cells={[
          { label: "Relatórios gerados no mês", value: String(14 + novos), delta: `${3 + novos} a mais que julho`, tone: "pos" },
          { label: "Auditados", value: String(11 + novosAuditados), delta: `de ${14 + novos} no mês`, tone: "neutral" },
          { label: "Enviados às marcas", value: "6", delta: "2 campanhas em veiculação", tone: "neutral" },
          { label: "Próximo envio automático", value: "Seg 07h", delta: "Operação semanal · Via Sul", tone: "neutral" },
        ]} />
        <Plate title="Relatórios recentes" right={<span className="rl-band-note">Agosto</span>}>
          <table className="rl-table">
            <thead><tr><th>Relatório</th><th>Destinatário</th><th>Período</th><th>Status</th><th /></tr></thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={`${r.name}-${i}`}>
                  <td>{r.name}</td><td>{r.to}</td><td>{r.period}</td>
                  <td>{r.status === "Auditado" ? <OkPill>{r.status}</OkPill> : <HighlightPill>{r.status}</HighlightPill>}</td>
                  <td><Button variant="secondary" disabled={baixando} onClick={() => baixar(r)}>{baixando ? "Preparando PDF…" : "Baixar PDF"}</Button></td>
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
      {dialog && <GerarDialog onCancel={() => setDialog(false)} onConfirm={gerar} />}
      {toast?.kind === "report" && (
        <div className="rl-toast" role="status">
          <span className="rl-toast__badge"><img src={checkToast} alt="" /></span>
          <div><strong>Relatório gerado</strong><span>{toast.text}</span></div>
        </div>
      )}
      {toast?.kind === "info" && (
        <div className="toast rl-toast--info" role="status"><StatusShape status="normal" color="var(--info-blue-on-ink)" />{toast.text}</div>
      )}
    </div>
  );
}

function GerarDialog({ onCancel, onConfirm }: { onCancel: () => void; onConfirm: (t: TipoLabel, to: string) => void }) {
  const [tipo, setTipo] = useState<TipoLabel>("Semanal");
  const [to, setTo] = useState(DESTS[0]);
  const ok = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    ok.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onCancel();
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onCancel]);
  return (
    <div className="overlay" onClick={onCancel}>
      <div className="dialog rl-dialog" role="dialog" aria-modal="true" aria-labelledby="gr-title" onClick={(e) => e.stopPropagation()}>
        <div className="dialog__band"><span className="dialog__mark" /><h2 id="gr-title" className="t-title">Gerar relatório</h2></div>
        <div className="dialog__body">
          <div className="rl-field"><span>Tipo</span>
            <Segmented options={Object.keys(TIPOS) as TipoLabel[]} value={tipo} onChange={setTipo} />
          </div>
          <label className="rl-field"><span>Destinatário</span>
            <select value={to} onChange={(e) => setTo(e.target.value)}>{DESTS.map((d) => <option key={d}>{d}</option>)}</select>
          </label>
          <p>Período: {TIPO[TIPOS[tipo]].periodo}. O relatório é auditado e fica na lista para baixar em PDF.</p>
          <div className="dialog__actions">
            <Button variant="secondary" onClick={onCancel}>Cancelar</Button>
            <Button ref={ok} onClick={() => onConfirm(tipo, to)}>Gerar</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
