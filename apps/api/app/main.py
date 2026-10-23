import json
import os
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from . import demo, dispatch, overview, seed
from .clock import SimClock
from .rules import StopState, evaluate

MAX_BODY = 300  # bytes
clock = SimClock()
commands: deque = deque()  # fila API -> simulador (set_count, arrival)


class Reading(BaseModel):
    model_config = ConfigDict(extra="forbid")
    stop_id: str
    ts: AwareDatetime
    count: int = Field(ge=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool = AsyncConnectionPool(os.environ["DATABASE_URL"], min_size=2, max_size=12,
                               kwargs={"row_factory": dict_row, "autocommit": True}, open=False)
    await pool.open()
    async with pool.connection() as conn:
        await conn.execute((Path(__file__).parent / "schema.sql").read_text())
        if await seed.run(conn):  # banco novo: abre no cenário Demo, relógio pausado em T0
            await demo.load(conn)
            clock.jump(demo.T0)
            clock.pause()
        else:
            cur = await conn.execute("SELECT max(last_ts) AS t FROM stop_state")
            last = (await cur.fetchone())["t"]
            if last is not None:  # reinício da API: o tempo de sim continua para frente, nunca volta
                clock.jump(last)
    app.state.pool = pool
    yield
    await pool.close()


app = FastAPI(title="UrbanFlow API", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/ingest/readings", status_code=202)
async def ingest(request: Request):
    raw = await request.body()
    if len(raw) > MAX_BODY:
        raise HTTPException(413, "corpo acima de 300 B")
    try:
        r = Reading.model_validate_json(raw)
    except ValidationError as e:
        raise HTTPException(422, json.loads(e.json(include_url=False, include_context=False, include_input=False)))
    async with request.app.state.pool.connection() as conn:
        async with conn.transaction():
            cur = await conn.execute(
                "SELECT last_ts, over_since, alert_active FROM stop_state WHERE stop_id = %s FOR UPDATE", (r.stop_id,))
            row = await cur.fetchone()
            if row is None:
                raise HTTPException(404, "ponto desconhecido")
            await conn.execute("INSERT INTO readings(stop_id, ts, count) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                               (r.stop_id, r.ts, r.count))
            new, event = evaluate(StopState(row["last_ts"], row["over_since"], row["alert_active"]), r.count, r.ts)
            await conn.execute(
                "UPDATE stop_state SET count=%s, last_ts=%s, over_since=%s, alert_active=%s WHERE stop_id=%s",
                (r.count, new.last_ts, new.over_since, new.alert_active, r.stop_id))
            if event == "open":
                await conn.execute(
                    "INSERT INTO alerts(stop_id, over_since, opened_at, peak) VALUES (%s, %s, %s, %s)",
                    (r.stop_id, new.over_since, r.ts, r.count))
            elif event == "close":
                await conn.execute("UPDATE alerts SET closed_at=%s WHERE stop_id=%s AND closed_at IS NULL", (r.ts, r.stop_id))
            elif new.alert_active:
                await conn.execute("UPDATE alerts SET peak=GREATEST(peak, %s) WHERE stop_id=%s AND closed_at IS NULL",
                                   (r.count, r.stop_id))
    return {"accepted": True}


class ClockUpdate(BaseModel):
    multiplier: float | None = None
    paused: bool | None = None
    jump_to: AwareDatetime | None = None


async def reset_scenario(pool) -> None:
    """Zera o histórico de simulação para o tempo poder voltar. O seed do cenário Demo (Fatia 1) entra aqui."""
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute("TRUNCATE readings, alerts, dispatches")
            await conn.execute("UPDATE stop_state SET last_ts = NULL, over_since = NULL, alert_active = false")
    commands.clear()


@app.post("/sim/scenario/demo")
async def scenario_demo(request: Request):
    """Reinicia sempre no cenário Demo: trunca, semeia, relógio em T0 e pausado, sim recarrega."""
    clock.pause()
    async with request.app.state.pool.connection() as conn:
        await demo.load(conn)
    clock.jump(demo.T0)
    commands.clear()
    commands.append({"type": "reload"})
    return {"clock": clock.snapshot(), "overview": await get_overview(request)}


@app.get("/overview")
async def get_overview(request: Request):
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("SELECT st.count, s.board_rate, st.alert_active FROM stop_state st JOIN stops s ON s.id = st.stop_id")
        rows = await cur.fetchall()
        day = clock.now().date()  # relógio já está em BRT
        cur = await conn.execute(
            "SELECT count(*) AS n FROM dispatches WHERE (created_at AT TIME ZONE 'America/Sao_Paulo')::date = %s", (day,))
        extras = (await cur.fetchone())["n"]
    return overview.compute(rows, extras)


@app.get("/sim/clock")
async def get_clock():
    return clock.snapshot()


@app.post("/sim/clock")
async def set_clock(u: ClockUpdate, request: Request):
    try:
        if u.multiplier is not None:
            clock.set_multiplier(u.multiplier)
    except ValueError as e:
        raise HTTPException(422, str(e))
    if u.jump_to is not None:
        if u.jump_to < clock.now():
            await reset_scenario(request.app.state.pool)  # salto para trás = reinício de cenário
        clock.jump(u.jump_to)
    if u.paused is True:
        clock.pause()
    elif u.paused is False:
        clock.resume()
    return clock.snapshot()


class Inject(BaseModel):
    stop_id: str
    count: int


@app.post("/sim/inject", status_code=202)
async def inject(i: Inject):
    commands.append({"type": "set_count", "stop_id": i.stop_id, "count": i.count})
    return {"queued": True}


async def advance_dispatches(conn, sim_now: datetime) -> None:
    cur = await conn.execute("SELECT id, stop_id, arrive_at, status, boards FROM dispatches WHERE status = %s",
                             (dispatch.A_CAMINHO,))
    for d in await cur.fetchall():
        if dispatch.next_status(d["status"], d["arrive_at"], sim_now) == dispatch.CHEGOU:
            await conn.execute("UPDATE dispatches SET status=%s WHERE id=%s", (dispatch.CHEGOU, d["id"]))
            await conn.execute("UPDATE stops SET steady=false WHERE id=%s", (d["stop_id"],))
            commands.append({"type": "arrival", "dispatch_id": d["id"], "stop_id": d["stop_id"], "boards": d["boards"]})


@app.post("/sim/poll")
async def poll(request: Request):
    """Chamado só pelo simulador: relógio + comandos pendentes."""
    async with request.app.state.pool.connection() as conn:
        await advance_dispatches(conn, clock.now())
    out = []
    while commands:
        out.append(commands.popleft())
    return {"clock": clock.snapshot(), "commands": out}


class DispatchIn(BaseModel):
    stop_id: str
    garage_id: str = "GAR-VM"


@app.post("/dispatches", status_code=201)
async def create_dispatch(d: DispatchIn, request: Request):
    now = clock.now()
    async with request.app.state.pool.connection() as conn:
        try:
            cur = await conn.execute(
                "INSERT INTO dispatches(stop_id, garage_id, created_at, arrive_at, status, boards) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING *",
                (d.stop_id, d.garage_id, now, dispatch.arrival_time(now), dispatch.A_CAMINHO, dispatch.BOARDS))
        except Exception:
            raise HTTPException(422, "ponto ou garagem desconhecidos")
        return await cur.fetchone()


@app.get("/dispatches")
async def list_dispatches(request: Request):
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("SELECT * FROM dispatches ORDER BY id DESC LIMIT 100")
        return await cur.fetchall()


@app.get("/alerts")
async def list_alerts(request: Request):
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("SELECT * FROM alerts ORDER BY id DESC LIMIT 100")
        return await cur.fetchall()


@app.get("/stops")
async def list_stops(request: Request):
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            "SELECT s.id, s.name, s.arrival_rate, s.board_rate, s.steady, s.svg_x, s.svg_y, st.count, st.alert_active "
            "FROM stops s JOIN stop_state st ON st.stop_id = s.id ORDER BY s.id")
        return await cur.fetchall()
