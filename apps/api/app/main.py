import asyncio
import json
import os
from collections import deque
from contextlib import asynccontextmanager
from typing import Annotated
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi import Path as PathParam
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError

from . import address_extraction, citizen, demo, dispatch, landing, overview, seed
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


@app.post("/address/extract")
async def extract_document_address(request: Request):
    """Recebe a fotografia no corpo da requisição; não persiste nem registra seu conteúdo."""
    content_type = request.headers.get("content-type", "").split(";", 1)[0].lower()
    if content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(415, "Envie uma imagem JPEG, PNG ou WEBP.")
    chunks = bytearray()
    async for chunk in request.stream():
        if len(chunks) + len(chunk) > address_extraction.MAX_IMAGE_BYTES:
            raise HTTPException(413, "A imagem excede o limite de 10 MB.")
        chunks.extend(chunk)
    try:
        return await run_in_threadpool(address_extraction.extract_address, bytes(chunks))
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except TimeoutError as error:
        raise HTTPException(504, "A leitura excedeu o tempo limite. Tente uma foto mais nítida.") from error
    except address_extraction.OCREngineError as error:
        raise HTTPException(503, "O serviço de OCR está indisponível.") from error


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
            if row["last_ts"] is not None and r.ts <= row["last_ts"]:
                return {"accepted": True}  # repetida, fora de ordem ou de antes de um reset: não mexe na lotação
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
            await conn.execute(demo.LOCK_STATE)
            await conn.execute("TRUNCATE readings, alerts, dispatches")
            await conn.execute("UPDATE stop_state SET last_ts = NULL, over_since = NULL, alert_active = false")
    commands.clear()


@app.post("/sim/scenario/demo")
async def scenario_demo(request: Request):
    """Reinicia sempre no cenário Demo: trunca, semeia, relógio em T0 e pausado, sim recarrega."""
    clock.pause()
    clock.jump(demo.T0)  # antes do load: um /sim/poll no meio não pode avançar despachos com a hora antiga
    async with request.app.state.pool.connection() as conn:
        await demo.load(conn)
    commands.clear()
    commands.append({"type": "reload"})
    return {"clock": clock.snapshot(), "overview": await get_overview(request)}


async def overview_of(conn, rows: list[dict]) -> dict:
    now = clock.now()  # relógio já está em BRT
    cur = await conn.execute(
        "SELECT count(*) AS n FROM dispatches WHERE (created_at AT TIME ZONE 'America/Sao_Paulo')::date = %s", (now.date(),))
    extras = (await cur.fetchone())["n"]
    cur = await conn.execute("SELECT avg_4w FROM hourly_network WHERE hour = %s", (now.hour,))
    avg = await cur.fetchone()
    return overview.compute(rows, extras, avg and avg["avg_4w"])


@app.get("/overview")
async def get_overview(request: Request):
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("SELECT st.count, s.board_rate, st.alert_active FROM stop_state st JOIN stops s ON s.id = st.stop_id")
        return await overview_of(conn, await cur.fetchall())


ALERT_ROWS = 4


@app.get("/snapshot")
async def get_snapshot(request: Request):
    """Tudo o que a Visão geral mostra, num só objeto: é o que o /stream envia a cada segundo."""
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            "SELECT s.id, s.name, s.board_rate, s.svg_x, s.svg_y, st.count, st.alert_active, "
            "(SELECT min(line_id) FROM stop_lines sl WHERE sl.stop_id = s.id) AS line, "
            "EXISTS (SELECT 1 FROM dispatches d WHERE d.stop_id = s.id AND d.status = %s) AS enroute "
            "FROM stops s JOIN stop_state st ON st.stop_id = s.id", (dispatch.A_CAMINHO,))
        rows = await cur.fetchall()
        ov = await overview_of(conn, rows)
        cur = await conn.execute("SELECT hour, avg_4w, today FROM hourly_network ORDER BY hour")
        hours = await cur.fetchall()
    stops = [dict(id=r["id"], name=r["name"], line=r["line"], count=r["count"], x=r["svg_x"], y=r["svg_y"],
                  wait_min=round(overview.stop_wait(r["count"], r["board_rate"])), enroute=r["enroute"],
                  status=overview.status(r["count"], r["alert_active"])) for r in rows]
    rank = {"critico": 0, "atencao": 1}
    alerts = sorted((s for s in stops if s["status"] in rank), key=lambda s: (rank[s["status"]], -s["count"]))
    return {"clock": clock.snapshot(), "overview": ov, "alerts": alerts[:ALERT_ROWS],
            "map": [s for s in stops if s["x"] is not None], "hourly": hours}


@app.get("/stream")
async def stream(request: Request):
    """SSE: um evento "snapshot" por segundo de parede (leituras, alertas, despachos e relógio juntos)."""
    async def events():
        while not await request.is_disconnected():
            snap = await get_snapshot(request)
            yield f"event: snapshot\ndata: {json.dumps(snap, default=str)}\n\n"
            await asyncio.sleep(1)
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


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


async def _stop_rows(conn) -> list[dict]:
    cur = await conn.execute(
            "SELECT s.id, s.name, s.arrival_rate, s.board_rate, s.steady, s.svg_x, s.svg_y, st.count, st.alert_active, "
            "(SELECT min(line_id) FROM stop_lines sl WHERE sl.stop_id = s.id) AS line, "
            "EXISTS (SELECT 1 FROM dispatches d WHERE d.stop_id = s.id AND d.status = %s) AS enroute "
            "FROM stops s JOIN stop_state st ON st.stop_id = s.id ORDER BY s.id", (dispatch.A_CAMINHO,))
    rows = await cur.fetchall()
    return [dict(r, wait_min=round(overview.stop_wait(r["count"], r["board_rate"])),
                 status=overview.status(r["count"], r["alert_active"])) for r in rows]


@app.get("/stops")
async def list_stops(request: Request):
    """Os 142 pontos (o simulador lê as taxas daqui); line/enroute/wait_min/status servem à lista de pontos do front."""
    async with request.app.state.pool.connection() as conn:
        return await _stop_rows(conn)


Visitor = Annotated[str, PathParam(pattern=citizen.VISITOR_PATTERN)]
NEARBY_KEYS = ("id", "name", "line", "count", "wait_min", "status", "enroute")


def _with_nearby(row: dict, stops: list[dict]) -> dict:
    nearby = citizen.nearby_stops(row["street"], row["number"], stops)
    return {**{k: row[k] for k in ("id", *citizen.FIELDS)}, "confirmed_at": row["confirmed_at"],
            "nearby_stops": [{k: s[k] for k in NEARBY_KEYS} for s in nearby]}


@app.get("/citizens/{visitor}/addresses")
async def list_citizen_addresses(visitor: Visitor, request: Request):
    """Endereços confirmados deste titular, cada um com os pontos monitorados da mesma via."""
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            "SELECT * FROM citizen_addresses WHERE visitor = %s ORDER BY confirmed_at DESC, id DESC", (visitor,))
        rows = await cur.fetchall()
        stops = await _stop_rows(conn) if rows else []
    return [_with_nearby(r, stops) for r in rows]


@app.post("/citizens/{visitor}/addresses", status_code=201)
async def save_citizen_address(visitor: Visitor, body: citizen.CitizenAddressIn, request: Request):
    """Grava o endereço confirmado e devolve os pontos monitorados da mesma via."""
    values = tuple(getattr(body, f) for f in citizen.FIELDS)
    async with request.app.state.pool.connection() as conn, conn.transaction():
        await conn.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (visitor,))
        cur = await conn.execute(
            "SELECT count(*) AS n, count(*) FILTER (WHERE street=%s AND number=%s AND complement=%s "
            "AND postal_code=%s) AS same FROM citizen_addresses WHERE visitor = %s",
            (body.street, body.number, body.complement, body.postal_code, visitor))
        existing = await cur.fetchone()
        if existing["n"] >= citizen.MAX_ADDRESSES and not existing["same"]:
            raise HTTPException(409, f"Limite de {citizen.MAX_ADDRESSES} endereços. Exclua um para cadastrar outro.")
        cur = await conn.execute(
            f"INSERT INTO citizen_addresses(visitor, {', '.join(citizen.FIELDS)}) "
            f"VALUES (%s{', %s' * len(citizen.FIELDS)}) "
            "ON CONFLICT (visitor, street, number, complement, postal_code) DO UPDATE SET "
            + ", ".join(f"{f}=EXCLUDED.{f}" for f in citizen.FIELDS) + ", confirmed_at=now() RETURNING *",
            (visitor, *values))
        row = await cur.fetchone()
        stops = await _stop_rows(conn)
    return _with_nearby(row, stops)


@app.delete("/citizens/{visitor}/addresses/{address_id}")
async def delete_citizen_address(visitor: Visitor, address_id: int, request: Request):
    """Direito de eliminação (LGPD art. 18): o titular apaga um endereço seu."""
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            "DELETE FROM citizen_addresses WHERE visitor = %s AND id = %s", (visitor, address_id))
    if not cur.rowcount:
        raise HTTPException(404, "Endereço não encontrado.")
    return {"deleted": 1}


@app.delete("/citizens/{visitor}/addresses")
async def delete_all_citizen_addresses(visitor: Visitor, request: Request):
    """Apaga todos os endereços do titular."""
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute("DELETE FROM citizen_addresses WHERE visitor = %s", (visitor,))
    return {"deleted": cur.rowcount}


@app.post("/landing/events", status_code=202)
async def landing_event(e: landing.EventIn, request: Request):
    async with request.app.state.pool.connection() as conn:
        await conn.execute("INSERT INTO events(visitor, variant, kind) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
                           (e.visitor, e.variant, e.kind))
    return {"accepted": True}


@app.post("/leads", status_code=201)
async def create_lead(lead: landing.LeadIn, request: Request):
    """Um lead por visitante e variante: reenviar o formulário atualiza o cadastro em vez de duplicar."""
    async with request.app.state.pool.connection() as conn:
        await conn.execute(
            "INSERT INTO leads(visitor, variant, company, size, email) VALUES (%s, %s, %s, %s, %s) "
            "ON CONFLICT (visitor, variant) DO UPDATE SET company=EXCLUDED.company, size=EXCLUDED.size, "
            "email=EXCLUDED.email, created_at=now()",
            (lead.visitor, lead.variant, lead.company, lead.size, lead.email))
    return {"accepted": True}


@app.get("/landing/metrics")
async def landing_metrics(request: Request):
    async with request.app.state.pool.connection() as conn:
        cur = await conn.execute(
            "SELECT v.variant, "
            "(SELECT count(*) FROM events e WHERE e.variant = v.variant AND e.kind = 'visit') AS visits, "
            "(SELECT count(*) FROM events e WHERE e.variant = v.variant AND e.kind = 'click') AS clicks, "
            "(SELECT count(*) FROM leads l WHERE l.variant = v.variant) AS leads "
            "FROM (VALUES ('A'), ('B')) AS v(variant)")
        m = landing.metrics(await cur.fetchall())
        cur = await conn.execute("SELECT variant, company, size, email, created_at FROM leads ORDER BY created_at DESC LIMIT 20")
        m["recent"] = await cur.fetchall()
    return m


@app.delete("/landing/data")
async def landing_reset(request: Request):
    """Só pelo bastidor: zera visitas, cliques e leads. O cenário Demo não mexe nestas tabelas."""
    async with request.app.state.pool.connection() as conn:
        await conn.execute("TRUNCATE events, leads")
    return {"ok": True}
