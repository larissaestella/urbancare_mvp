import { useEffect, useState } from "react";
import type { Status } from "./ui";

export type StopRow = { id: string; name: string; line: string; count: number; x: number | null; y: number | null;
  wait_min: number; enroute: boolean; status: Status };
export type Snapshot = {
  clock: { sim_now: string; multiplier: number; paused: boolean };
  overview: { people: number; avg_wait_min: number; wait_over_goal_min: number; goal_wait_min: number; stops_total: number;
    stops_in_alert: number; critical: number; attention: number; extras_today: number; vs_avg_pct: number | null };
  alerts: StopRow[];
  map: StopRow[];
  hourly: { hour: number; avg_4w: number; today: number | null }[];
};

export async function call<T = unknown>(method: string, path: string, body?: unknown): Promise<T> {
  const r = await fetch(`/api${path}`, { method, headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body) });
  if (!r.ok) throw new Error(`${method} ${path}: ${r.status}`);
  return r.json();
}

/** Snapshot ao vivo pelo /stream (SSE); se o SSE cair, polling de 2 s até ele voltar. */
export function useSnapshot(): Snapshot | null {
  const [snap, setSnap] = useState<Snapshot | null>(null);
  useEffect(() => {
    let poll: number | undefined;
    const es = new EventSource("/api/stream");
    es.addEventListener("snapshot", (e) => {
      window.clearInterval(poll);
      poll = undefined;
      setSnap(JSON.parse((e as MessageEvent).data));
    });
    es.onerror = () => {
      if (poll === undefined) poll = window.setInterval(() => call<Snapshot>("GET", "/snapshot").then(setSnap, () => {}), 2000);
    };
    return () => { es.close(); window.clearInterval(poll); };
  }, []);
  return snap;
}

const WEEKDAY = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"];

/** "Seg 18:42" a partir do ISO do relógio de sim (já em BRT), sem depender do fuso do navegador. */
export function simLabel(iso: string): string {
  return `${WEEKDAY[new Date(`${iso.slice(0, 10)}T12:00:00Z`).getUTCDay()]} ${iso.slice(11, 16)}`;
}

export const simHour = (iso: string) => Number(iso.slice(11, 13));
export const fmt = (n: number) => n.toLocaleString("pt-BR");

export type StopListRow = StopRow & { board_rate: number; alert_active: boolean };

/** Os 142 pontos (GET /stops), recarregados a cada 2 s; a lista de pontos e o mapa usam a mesma classificação da API. */
export function useStops(): StopListRow[] | null {
  const [rows, setRows] = useState<StopListRow[] | null>(null);
  useEffect(() => {
    const load = () => call<(StopListRow & { svg_x: number | null; svg_y: number | null })[]>("GET", "/stops")
      .then((r) => setRows(r.map((s) => ({ ...s, x: s.svg_x, y: s.svg_y }))), () => {});
    load();
    const t = window.setInterval(load, 2000);
    return () => window.clearInterval(t);
  }, []);
  return rows;
}

const MONITOR_KEY = "urbancare.monitorando";
const readMonitor = (): string[] => { try { return JSON.parse(localStorage.getItem(MONITOR_KEY) ?? "[]"); } catch { return []; } };

/** Pontos que o operador marcou para acompanhar (conveniência do navegador; não vai para a API). */
export function useMonitor(): [Set<string>, (id: string) => void] {
  const [ids, setIds] = useState(() => new Set(readMonitor()));
  const toggle = (id: string) => setIds((cur) => {
    const next = new Set(cur);
    if (next.has(id)) next.delete(id); else next.add(id);
    try { localStorage.setItem(MONITOR_KEY, JSON.stringify([...next])); } catch { /* sem armazenamento: vale só nesta tela */ }
    return next;
  });
  return [ids, toggle];
}
