"""Simulador de sensores: uma leitura por ponto a cada 30 s de tempo de simulação."""
import asyncio
import math
import os
import random
import time
from datetime import datetime, timedelta

import httpx

API = os.environ.get("API_URL", "http://localhost:8000")
TICK = timedelta(seconds=30)
MAX_CATCHUP = 5
# multiplicador de chegadas por hora do dia (picos 7-9h e 17-19h)
CURVE = [0.1, 0.05, 0.05, 0.05, 0.1, 0.3, 0.7, 1.4, 1.6, 1.1, 0.8, 0.8, 0.9, 0.8, 0.8, 0.9, 1.1, 1.5, 1.7, 1.3, 0.8, 0.5, 0.3, 0.2]


def poisson(rng: random.Random, lam: float) -> int:
    limit, k, p = math.exp(-lam), 0, 1.0
    while True:
        p *= rng.random()
        if p <= limit:
            return k
        k += 1


def floor_tick(t: datetime) -> datetime:
    return t - timedelta(seconds=t.second % 30, microseconds=t.microsecond)


async def main() -> None:
    rng = random.Random(7)
    async with httpx.AsyncClient(base_url=API, timeout=15, limits=httpx.Limits(max_connections=50)) as client:
        counts: dict[str, int] = {}
        rates: dict[str, tuple[float, float]] = {}
        steady: set[str] = set()  # Demo: lotação fixa até o despacho chegar

        async def reload() -> int:
            while True:
                try:
                    stops = (await client.get("/stops")).json()
                    break
                except httpx.HTTPError:
                    await asyncio.sleep(1)
            counts.clear(); rates.clear(); steady.clear()
            counts.update({s["id"]: s["count"] for s in stops})
            rates.update({s["id"]: (s["arrival_rate"], s["board_rate"]) for s in stops})
            steady.update(s["id"] for s in stops if s["steady"])
            return len(stops)

        n_stops = await reload()
        sem = asyncio.Semaphore(40)
        sent = failed = 0
        last_report = time.monotonic()
        next_tick = None
        print(f"sim: {n_stops} pontos", flush=True)

        async def emit(sid: str, ts: datetime) -> None:
            nonlocal sent, failed
            async with sem:
                try:
                    r = await client.post("/ingest/readings", json={"stop_id": sid, "ts": ts.isoformat(), "count": counts[sid]})
                    sent += r.status_code == 202
                    failed += r.status_code != 202
                except httpx.HTTPError:
                    failed += 1

        while True:
            try:
                poll = (await client.post("/sim/poll")).json()
            except httpx.HTTPError:
                await asyncio.sleep(1)
                continue
            now = datetime.fromisoformat(poll["clock"]["sim_now"])
            for cmd in poll["commands"]:
                if cmd["type"] == "reload":
                    await reload()
                    next_tick = floor_tick(now) + TICK  # o estado semeado já vale para T0: não aplica dinâmica nele
                    continue
                sid = cmd["stop_id"]
                if sid not in counts:
                    continue
                if cmd["type"] == "set_count":
                    counts[sid] = max(0, cmd["count"])
                elif cmd["type"] == "arrival":
                    counts[sid] = max(0, counts[sid] - cmd["boards"])
                    steady.discard(sid)
            if next_tick is None:  # início: o estado lido da API já vale para o instante atual
                next_tick = floor_tick(now) + TICK
            elif now < next_tick - 2 * TICK:  # salto para trás
                next_tick = floor_tick(now)
            steps = 0
            while next_tick <= now and steps < MAX_CATCHUP:
                dt_min = TICK.total_seconds() / 60
                mult = CURVE[next_tick.hour]
                for sid, (arr, brd) in rates.items():
                    if sid in steady:
                        continue
                    counts[sid] = max(0, counts[sid] + poisson(rng, arr * mult * dt_min) - round(brd * dt_min + rng.uniform(-0.3, 0.3)))
                await asyncio.gather(*(emit(sid, next_tick) for sid in counts))
                next_tick += TICK
                steps += 1
            if next_tick <= now:  # atrasado demais: pula para o presente
                next_tick = floor_tick(now) + TICK
            if time.monotonic() - last_report >= 10:
                print(f"sim: {sent / 10:.0f} leituras/s, falhas={failed}, sim_now={now:%a %H:%M:%S}", flush=True)
                sent = failed = 0
                last_report = time.monotonic()
            await asyncio.sleep(0.2)


asyncio.run(main())
