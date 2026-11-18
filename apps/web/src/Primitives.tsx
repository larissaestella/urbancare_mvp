import { useState } from "react";
import { Button, HighlightPill, KpiStrip, LineChip, LivePill, Plate, Segmented, Sidebar, StatusPill, TitlePlate, Toggle } from "./ui";

/** Página de conferência visual: lado a lado com docs/referencias/design-system.png */
export default function Primitives() {
  const [on, setOn] = useState(true);
  const [seg, setSeg] = useState("Hoje");
  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar items={["Visão geral", "Detalhe do ponto", "Publicidade", "Frota", "Relatórios", "Configurações"]} active="Visão geral" />
      <main style={{ flex: 1, padding: "32px 40px", display: "flex", flexDirection: "column", gap: 24 }}>
        <TitlePlate title="Visão geral" meta="Seg 18:42 · 142 pontos" right={<LivePill />} />
        <KpiStrip cells={[
          { label: "Pessoas nos pontos", value: "1.284", delta: "+18% vs. média do horário", tone: "warn" },
          { label: "Espera média", value: "11 min", delta: "+3 acima da meta 8", tone: "neg" },
          { label: "Pontos em alerta", value: "7/142", delta: "3 críticos, 4 atenção", tone: "neutral" },
          { label: "Extras hoje", value: "12", delta: "-9% km ocioso", tone: "pos" },
        ]} />
        <Plate title="Primitivas" right={<LivePill />}>
          <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
            <StatusPill status="normal" /><StatusPill status="atencao" /><StatusPill status="critico" /><HighlightPill>Destaque</HighlightPill>
            <LineChip line="875A" /><LineChip line="177H" /><LineChip line="6450" /><LineChip line="7272" />
            <Button>Enviar extra</Button><Button variant="secondary">Monitorar</Button>
            <Toggle on={on} onChange={setOn} label="Envio automático" />
            <Segmented options={["Hoje", "Semana", "Mês"]} value={seg} onChange={setSeg} />
          </div>
        </Plate>
        <Plate title="Recomendação" critical>
          <p>Av. Paulista, 1578: <LineChip line="875A" /> com 26 pessoas há mais de 5 min.</p>
        </Plate>
      </main>
    </div>
  );
}
