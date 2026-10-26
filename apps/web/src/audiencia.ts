/* Audiência dos painéis: números verbatim do render 03 (semana 24/08 – 30/08) e os derivados ilustrativos
   (Diária/Mensal), compartilhados entre Publicidade e o relatório imprimível. */
export const DAYS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"];
export const SLOTS = ["06–09h", "09–12h", "12–15h", "15–18h", "18–21h", "21–24h"];
// tom 1–5 (--data-1 … --data-5) lido do render; só a faixa 18–21h de seg a qui traz o índice impresso
export const HEAT = [
  [5, 5, 5, 5, 4, 2, 1],
  [3, 2, 2, 2, 3, 3, 2],
  [3, 3, 3, 3, 3, 4, 3],
  [4, 3, 4, 4, 4, 3, 2],
  [5, 5, 5, 5, 5, 3, 2],
  [1, 1, 1, 1, 3, 2, 1],
];
export const PEAK_INDEX: Record<string, number> = { "4-0": 100, "4-1": 96, "4-2": 98, "4-3": 95 };
export const RANKING = [
  ["Av. Paulista, 1578", "28,4 mil", "9m 10s", "R$ 18,90"],
  ["Terminal Sto. Amaro", "24,1 mil", "8m 30s", "R$ 16,40"],
  ["R. da Consolação, 900", "19,7 mil", "7m 55s", "R$ 14,80"],
  ["Av. Rebouças, 1200", "16,2 mil", "6m 20s", "R$ 12,10"],
  ["Av. Brig. Faria Lima, 2000", "14,9 mil", "5m 45s", "R$ 11,30"],
];
/* Diária e Mensal: ilustrativos (pedido do Rafael, 26/10), derivados dos números verbatim da semana.
   Cada dia leva a fatia da semana proporcional à soma da sua coluna no mapa de calor (os 7 dias somam 412 mil);
   o mês é a soma das 4 semanas de agosto, a última sendo a semana do render. */
export const WEEK_TOTAL = 412_000;
export const DATES = ["24/08", "25/08", "26/08", "27/08", "28/08", "29/08", "30/08"];
export const colSum = (c: number) => HEAT.reduce((a, row) => a + row[c], 0);
export const HEAT_TOTAL = DAYS.reduce((a, _, c) => a + colSum(c), 0);
export const dayPeople = (c: number) => (WEEK_TOTAL * colSum(c)) / HEAT_TOTAL;
export const slotPeople = (c: number) => SLOTS.map((_, r) => (dayPeople(c) * HEAT[r][c]) / colSum(c));
export const MONTH_WEEKS = [["03–09/08", 338_000], ["10–16/08", 352_000], ["17–23/08", 368_000], ["24–30/08", WEEK_TOTAL]] as const;
export const MONTH_TOTAL = MONTH_WEEKS.reduce((a, [, v]) => a + v, 0);
export const JULY_TOTAL = 1_290_000;
export const RANK_WEEK = [28_400, 24_100, 19_700, 16_200, 14_900];

export const mil = (n: number) => n >= 1_000_000
  ? `${(n / 1_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 2 })} mi`
  : `${(n / 1000).toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 })} mil`;
export const pct = (a: number, b: number) => Math.round((a / b - 1) * 100);
export const delta = (p: number) => `${p >= 0 ? "▲" : "▼"} ${Math.abs(p)}%`;


export type Periodo = "Diária" | "Semanal" | "Mensal";
/** Resumo de audiência por período; Diária depende do dia (dia de pico ou não), Semanal é verbatim do render. */
export function resumo(p: Periodo, day = 4) {
  if (p === "Semanal") return { people: WEEK_TOTAL, exposure: "7m 40s", qualified: "68%", cpm: "R$ 14,20" };
  if (p === "Mensal") return { people: MONTH_TOTAL, exposure: "7m 25s", qualified: "66%", cpm: "R$ 13,80" };
  const peak = colSum(day) >= HEAT_TOTAL / 7;
  return { people: dayPeople(day), exposure: peak ? "7m 55s" : "6m 50s", qualified: peak ? "70%" : "63%", cpm: peak ? "R$ 15,10" : "R$ 11,60" };
}
