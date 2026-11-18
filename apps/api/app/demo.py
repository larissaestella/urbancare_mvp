"""Cenário Demo: seed calibrado contra overview.compute (1.284 pessoas, 11 min, 7/142 em alerta, 12 extras)."""
import random
from datetime import timedelta

from .clock import DEMO_START as T0
from .dispatch import A_CAMINHO, ETA_MIN, BOARDS, CHEGOU
from .seed import FIXED_STOPS

PEOPLE = 1284
AVG_WAIT = 11.0
PEAK_CURVE = 1.7  # CURVE[18] do simulador
# (stop_id, lotação, espera em min): 3 críticos do render + Rebouças; os outros 3 em atenção vêm dos fillers
CRITICAL = [("SP-0412", 26, 17), ("SP-0071", 24, 15), ("SP-0233", 22, 14)]
ATTENTION = [("SP-0587", 18, 12)]
EXTRA_ATTENTION = [(17, 11), (16, 12), (15, 10)]  # abaixo de Rebouças (18): ela fica em 4º na lista, como no render
CRIT_OVER_MIN = {"SP-0412": 9, "SP-0071": 7, "SP-0233": 6}  # há quanto tempo está acima de 20
ENROUTE_STOP = "SP-0233"
# ingest trava stop_state antes de readings; o reset segue a mesma ordem para não dar deadlock
LOCK_STATE = "LOCK TABLE stop_state IN EXCLUSIVE MODE"
# posições no mapa estilizado (0-100), medidas no render 01: 3 críticos, 3 atenção (o 3º extra fica fora do recorte), 8 normais
MAP_XY = {"SP-0412": (14, 20), "SP-0233": (40, 55), "SP-0071": (86, 55), "SP-0587": (76, 36)}
EXTRA_XY = [(66, 20), (14, 80)]
NORMAL_XY = [(40, 20), (51, 20), (6, 39), (54, 39), (27, 55), (31, 81), (66, 81), (92, 81)]
# histórico horário da rede (4 semanas, só a média) para o gráfico e o "+18% vs. média do horário"
CURVE = [0.1, 0.05, 0.05, 0.05, 0.1, 0.3, 0.7, 1.4, 1.6, 1.1, 0.8, 0.8, 0.9, 0.8, 0.8, 0.9, 1.1, 1.5, 1.7, 1.3, 0.8, 0.5, 0.3, 0.2]  # = sim
VS_AVG = 0.18
HOURS = range(5, 23)


def build(stop_ids: list[str], seed: int = 11) -> dict:
    """Constrói por ponto: count, board_rate, arrival_rate, steady, over_since (min), map xy. Sem solver."""
    rng = random.Random(seed)
    fixed = {sid: (c, w) for sid, c, w in CRITICAL + ATTENTION}
    others = [s for s in sorted(stop_ids) if s not in fixed]
    extra_attn = dict(zip(others[:3], EXTRA_ATTENTION))
    fillers = others[3:]
    hot = {**fixed, **{sid: cw for sid, cw in extra_attn.items()}}
    rest = PEOPLE - sum(c for c, _ in hot.values())
    counts = {sid: rng.randint(5, 12) for sid in fillers}
    diff = rest - sum(counts.values())
    while diff:  # ajusta ±1 em pontos sorteados, mantendo 3..14 (abaixo da faixa de atenção)
        sid = rng.choice(fillers)
        step = 1 if diff > 0 else -1
        if 3 <= counts[sid] + step <= 14:
            counts[sid] += step
            diff -= step
    waits = {sid: rng.uniform(9.5, 11.9) for sid in fillers}
    need = AVG_WAIT * PEOPLE - sum(c * w for c, w in hot.values())  # Σ lotação×espera exigida dos fillers
    k = need / sum(counts[s] * waits[s] for s in fillers)
    out = {}
    for sid, (c, w) in hot.items():
        out[sid] = dict(count=c, board_rate=c / w, steady=True)
    for sid in fillers:
        out[sid] = dict(count=counts[sid], board_rate=counts[sid] / (waits[sid] * k), steady=False)
    for sid, d in out.items():
        d["arrival_rate"] = d["board_rate"] * 0.95 / PEAK_CURVE  # no pico da tarde o ponto drena de leve
        d["over_min"] = CRIT_OVER_MIN.get(sid)
    for sid, xy in [*zip(fillers, NORMAL_XY), *MAP_XY.items(), *zip(extra_attn, EXTRA_XY)]:
        out[sid]["xy"] = xy
    return out


def hourly(seed: int = 18) -> list[tuple[int, int, int | None]]:
    """(hora, média 4 semanas, hoje) de 05h a 22h. Média das 18h = 1.284 / 1,18; hoje só até 17h (18h é o ao vivo)."""
    rng = random.Random(seed)
    avg18 = round(PEOPLE / (1 + VS_AVG))
    return [(h, round(avg18 * CURVE[h] / PEAK_CURVE), round(avg18 * CURVE[h] / PEAK_CURVE * rng.uniform(1.04, 1.16)) if h < T0.hour else None)
            for h in HOURS]


async def load(conn) -> None:
    """Zera a simulação e grava o estado do render em T0 (a chamada pausa o relógio e manda o sim recarregar)."""
    cur = await conn.execute("SELECT id FROM stops")
    ids = [r["id"] for r in await cur.fetchall()]
    d = build(ids)
    async with conn.transaction():
        await conn.execute(LOCK_STATE)
        await conn.execute("TRUNCATE readings, alerts, dispatches, hourly_network")
        async with conn.cursor() as c:
            await c.executemany("INSERT INTO hourly_network(hour, avg_4w, today) VALUES (%s,%s,%s)", hourly())
            await c.executemany(
                "UPDATE stops SET arrival_rate=%s, board_rate=%s, steady=%s, svg_x=%s, svg_y=%s WHERE id=%s",
                [(v["arrival_rate"], v["board_rate"], v["steady"], *(v.get("xy") or (None, None)), sid) for sid, v in d.items()])
            await c.executemany(
                "INSERT INTO stop_state(stop_id, count, last_ts, over_since, alert_active) VALUES (%s,%s,%s,%s,%s) "
                "ON CONFLICT (stop_id) DO UPDATE SET count=EXCLUDED.count, last_ts=EXCLUDED.last_ts, "
                "over_since=EXCLUDED.over_since, alert_active=EXCLUDED.alert_active",
                [(sid, v["count"], T0, T0 - timedelta(minutes=v["over_min"]) if v["over_min"] else None, bool(v["over_min"]))
                 for sid, v in d.items()])
            await c.executemany("INSERT INTO readings(stop_id, ts, count) VALUES (%s,%s,%s)",
                                [(sid, T0, v["count"]) for sid, v in d.items()])
            await c.executemany(
                "INSERT INTO alerts(stop_id, over_since, opened_at, peak) VALUES (%s,%s,%s,%s)",
                [(sid, T0 - timedelta(minutes=m), T0 - timedelta(minutes=m - 5), d[sid]["count"] + 2)
                 for sid, m in CRIT_OVER_MIN.items()])
            normais = [s for s in sorted(d) if not d[s]["steady"]][:11]  # 11 extras já chegaram hoje
            rows = [(s, "GAR-VM", T0.replace(hour=6 + i, minute=10 + 3 * i), T0.replace(hour=6, minute=19 + 3 * i) + timedelta(hours=i),
                     CHEGOU, BOARDS) for i, s in enumerate(normais)]
            rows.append((ENROUTE_STOP, "GAR-VM", T0, T0 + timedelta(minutes=ETA_MIN), A_CAMINHO, BOARDS))
            await c.executemany(
                "INSERT INTO dispatches(stop_id, garage_id, created_at, arrive_at, status, boards) VALUES (%s,%s,%s,%s,%s,%s)", rows)
