#!/usr/bin/env python3
"""Aceitação da Fatia 0: leitura flui, alerta nasce após 5 min de sim, despacho derruba a lotação.
Pré-requisito: docker compose up. Uso: python3 scripts/check_fatia0.py"""
import json
import time
import urllib.request
from datetime import datetime

API = "http://localhost:8000"
STOP = "SP-0412"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or "null")


def stop_count():
    return next(s["count"] for s in call("GET", "/stops") if s["id"] == STOP)


def wait(cond, timeout, what):
    end = time.time() + timeout
    while time.time() < end:
        v = cond()
        if v:
            return v
        time.sleep(0.5)
    raise SystemExit(f"FALHOU: {what} (timeout {timeout}s)")


call("POST", "/sim/clock", {"multiplier": 30, "paused": False})
call("POST", "/sim/inject", {"stop_id": STOP, "count": 0})  # idempotência: começa de ponto limpo, sem alerta aberto
wait(lambda: not any(a["stop_id"] == STOP and a["closed_at"] is None for a in call("GET", "/alerts")), 20, "estado limpo")
t_inject = datetime.fromisoformat(call("GET", "/sim/clock")["sim_now"])
call("POST", "/sim/inject", {"stop_id": STOP, "count": 45})
wait(lambda: stop_count() >= 35, 10, "leituras fluindo com lotação injetada")
print("ok: leituras fluem, lotação injetada em", STOP)

alert = wait(lambda: next((a for a in call("GET", "/alerts") if a["stop_id"] == STOP and a["closed_at"] is None
                           and datetime.fromisoformat(a["opened_at"]) > t_inject), None), 40, "alerta aberto")
held = datetime.fromisoformat(alert["opened_at"]) - datetime.fromisoformat(alert["over_since"])
assert held.total_seconds() >= 300, f"alerta antes de 5 min de sim ({held})"
print(f"ok: alerta nasceu após {held.total_seconds():.0f} s de sim")

before = stop_count()
for n in range(1, 4):  # um extra leva 25; com pico de chegadas pode precisar de mais de um
    d = call("POST", "/dispatches", {"stop_id": STOP})
    wait(lambda: next((x for x in call("GET", "/dispatches") if x["id"] == d["id"] and x["status"] == "chegou"), None), 30, "despacho chegou")
    time.sleep(1.5)
    if stop_count() <= 20:
        break
assert stop_count() < before - 10, "lotação não caiu após chegada"
print(f"ok: {n} despacho(s) chegou(aram) e a lotação caiu de {before} para {stop_count()}")
wait(lambda: next((a for a in call("GET", "/alerts") if a["id"] == alert["id"] and a["closed_at"]), None), 15, "alerta fechado")
print("ok: alerta fechado. FATIA 0 (backend) APROVADA")
