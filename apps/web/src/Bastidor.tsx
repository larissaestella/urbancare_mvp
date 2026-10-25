import { useState } from "react";
import { call, simLabel, useSnapshot } from "./api";
import { Button, Plate, Segmented } from "./ui";

const MULTS = ["1×", "5×", "10×", "30×"] as const;

/** Modo bastidor: controles do relógio de simulação para quem opera a demo. Fora das telas de produto. */
export default function Bastidor() {
  const snap = useSnapshot();
  const [busy, setBusy] = useState(false);
  const clock = snap?.clock;
  const run = (fn: () => Promise<unknown>) => { setBusy(true); fn().finally(() => setBusy(false)); };
  return (
    <main style={{ maxWidth: 560, margin: "40px auto", padding: "0 16px" }}>
      <Plate title="Bastidor · relógio de simulação">
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <p className="t-metric">{clock ? `${simLabel(clock.sim_now)} · ${clock.paused ? "pausado" : `rodando a ${clock.multiplier}×`}` : "…"}</p>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <Button disabled={busy} onClick={() => run(() => call("POST", "/sim/scenario/demo"))}>Recarregar cenário Demo</Button>
            <Button variant="secondary" disabled={busy || !clock}
              onClick={() => run(() => call("POST", "/sim/clock", { paused: !clock!.paused }))}>{clock?.paused ? "Retomar" : "Pausar"}</Button>
          </div>
          <Segmented options={[...MULTS]} value={(MULTS.find((m) => parseFloat(m) === clock?.multiplier) ?? "1×")}
            onChange={(m) => run(() => call("POST", "/sim/clock", { multiplier: parseFloat(m) }))} />
          <p className="t-caption" style={{ color: "var(--ink-muted)" }}>
            A 30×, 1 min de parede = 30 min de sim (o extra chega em ~18 s). O Demo abre pausado em Seg 18:42; recarregar sempre volta ao estado do render.
          </p>
        </div>
      </Plate>
    </main>
  );
}
