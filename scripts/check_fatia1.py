#!/usr/bin/env python3
"""Aceitação da Fatia 1 (backend): cenário Demo reproduzível e fluxo alerta -> enviar extra -> lotação cai.
Pré-requisito: docker compose up. Uso: python3 scripts/check_fatia1.py"""
import json
import time
import urllib.request

API = "http://localhost:8000"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or "null")


def wait(cond, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        v = cond()
        if v:
            return v
        time.sleep(0.5)
    raise SystemExit(f"FALHOU: {what} (timeout {timeout}s)")


def stop(sid):
    return next(s for s in call("GET", "/stops") if s["id"] == sid)


r = call("POST", "/sim/scenario/demo")
assert r["clock"]["paused"] and r["clock"]["sim_now"].startswith("2026-08-31T18:42"), r["clock"]
time.sleep(2)  # dá tempo ao sim de recarregar; relógio pausado: nada pode mudar
o = call("GET", "/overview")
want = dict(people=1284, stops_total=142, stops_in_alert=7, critical=3, attention=4, extras_today=12, wait_over_goal_min=3)
assert all(o[k] == v for k, v in want.items()) and round(o["avg_wait_min"]) == 11, o
p = stop("SP-0412")
assert p["count"] == 26 and round(p["count"] / p["board_rate"]) == 17
assert len([a for a in call("GET", "/alerts") if a["closed_at"] is None]) == 3
print("ok: Demo em Seg 18:42 pausado:", o)

call("POST", "/sim/clock", {"multiplier": 30, "paused": False})
time.sleep(4)  # ~2 min de sim: pontos em alerta seguem fixos
o2 = call("GET", "/overview")
assert o2["critical"] == 3 and stop("SP-0412")["count"] == 26, "ponto crítico drenou sozinho"
print("ok: alertas se mantêm com o relógio andando")

d = call("POST", "/dispatches", {"stop_id": "SP-0412"})
assert call("GET", "/overview")["extras_today"] == 13
wait(lambda: next((x for x in call("GET", "/dispatches") if x["id"] == d["id"] and x["status"] == "chegou"), None), 30, "despacho chegou")
wait(lambda: stop("SP-0412")["count"] <= 10, 10, "lotação caiu")
wait(lambda: next((a for a in call("GET", "/alerts") if a["stop_id"] == "SP-0412" and a["closed_at"]), None), 15, "alerta fechado")
print("ok: extra enviado, lotação caiu para", stop("SP-0412")["count"], "e o alerta fechou. FATIA 1 (backend) APROVADA")
call("POST", "/sim/scenario/demo")  # deixa o Demo pronto para a próxima abertura
