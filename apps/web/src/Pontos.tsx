import { useEffect, useState } from "react";
import { call, simLabel, useMonitor, useSnapshot, useStops, type StopListRow } from "./api";
import { ConfirmDialog, ETA_MIN, NAV, go } from "./Overview";
import { Button, LineChip, LivePill, Segmented, Sidebar, StatusPill, StatusShape, TitlePlate } from "./ui";
import "./overview.css";
import "./pontos.css";

/* Pontos de ônibus (sem render nem Figma; pedido do Rafael, PLANO §8.6): os 142 pontos ao vivo, com a mesma classificação
   e o mesmo envio de extra da Visão geral. Só o SP-0412 tem tela de detalhe. */
const FILTROS = ["Todos", "Em alerta", "Monitorando", "Normais"] as const;
const RANK = { critico: 0, atencao: 1, normal: 2 } as const;

export default function Pontos() {
  const snap = useSnapshot();
  const stops = useStops();
  const [monitor, toggleMonitor] = useMonitor();
  const [filtro, setFiltro] = useState<(typeof FILTROS)[number]>("Todos");
  const [busca, setBusca] = useState(() => new URLSearchParams(location.search).get("busca") ?? "");
  const [confirm, setConfirm] = useState<StopListRow | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!toast) return;
    const t = window.setTimeout(() => setToast(null), 5000);
    return () => window.clearTimeout(t);
  }, [toast]);

  async function send(stop: StopListRow) {
    setConfirm(null);
    try {
      await call("POST", "/dispatches", { stop_id: stop.id });
      setToast(`Ônibus extra enviado na linha ${stop.line} · chega em ${ETA_MIN} min em ${stop.name}`);
    } catch {
      setToast("Não foi possível enviar o extra. Tente de novo.");
    }
  }

  const q = busca.trim().toLowerCase();
  const rows = (stops ?? [])
    .filter((s) => filtro === "Todos" || (filtro === "Em alerta" ? s.status !== "normal" : filtro === "Normais" ? s.status === "normal" : monitor.has(s.id)))
    .filter((s) => !q || s.name.toLowerCase().includes(q) || s.id.toLowerCase().includes(q) || s.line?.toLowerCase().includes(q))
    .sort((a, b) => RANK[a.status] - RANK[b.status] || b.count - a.count);
  const alerta = stops?.filter((s) => s.status !== "normal").length ?? 0;

  return (
    <div className="app">
      <Sidebar items={NAV} active="Pontos de ônibus" onNavigate={go} />
      <main className="ov">
        <TitlePlate title="Pontos de ônibus" meta={`Concessionária Via Sul · ${stops?.length ?? 142} pontos monitorados · ${alerta} em alerta`}
          right={<div className="ov__head"><LivePill />{snap && <span className="ov__clock">{simLabel(snap.clock.sim_now)}</span>}</div>} />
        <div className="pt-bar">
          <Segmented options={[...FILTROS]} value={filtro} onChange={setFiltro} />
          <input className="pt-search" type="search" placeholder="Buscar por endereço, código ou linha" aria-label="Buscar ponto"
            value={busca} onChange={(e) => setBusca(e.target.value)} />
          <span className="pt-count">{rows.length} {rows.length === 1 ? "ponto" : "pontos"}</span>
        </div>
        <section className="plate">
          <table className="pt-table">
            <thead><tr><th>Ponto</th><th>Linha</th><th>Pessoas</th><th>Espera</th><th>Status</th><th /></tr></thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id}>
                  <td>
                    {s.id === "SP-0412" ? <a className="pt-name pt-name--link" href="/pontos/SP-0412">{s.name}</a> : <span className="pt-name">{s.name}</span>}
                    <span className="pt-id">{s.id}</span>
                  </td>
                  <td>{s.line && <LineChip line={s.line} />}</td>
                  <td className="pt-num">{s.count}</td>
                  <td className="pt-num">{s.wait_min} min</td>
                  <td>{s.enroute ? <span className="pill pill--destaque"><StatusShape status="normal" color="#fff" />Extra a caminho</span> : <StatusPill status={s.status} />}</td>
                  <td><div className="pt-actions">
                    {s.status === "critico" && !s.enroute && <Button onClick={() => setConfirm(s)}>Enviar extra</Button>}
                    <Button variant="secondary" aria-pressed={monitor.has(s.id)} onClick={() => toggleMonitor(s.id)}>
                      {monitor.has(s.id) ? "Monitorando" : "Monitorar"}
                    </Button>
                  </div></td>
                </tr>
              ))}
            </tbody>
          </table>
          {stops && rows.length === 0 && <p className="pt-empty">Nenhum ponto com esse filtro.</p>}
          {!stops && <p className="pt-empty">Conectando aos pontos…</p>}
        </section>
        <p className="pt-foot">Dados ilustrativos — simulação para validação (Sprint 2). Detalhe completo disponível para o SP-0412.</p>
      </main>
      {confirm && <ConfirmDialog stop={confirm} onCancel={() => setConfirm(null)} onConfirm={() => send(confirm)} />}
      {toast && <div className="toast" role="status"><StatusShape status="normal" color="var(--status-green-on-ink)" />{toast}</div>}
    </div>
  );
}
