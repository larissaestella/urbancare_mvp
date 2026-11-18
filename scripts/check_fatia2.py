#!/usr/bin/env python3
"""Aceitação da Fatia 2 (backend): landing A/B, leads e métricas de conversão.
Pré-requisito: docker compose up. ZERA as métricas da landing. Uso: python3 scripts/check_fatia2.py"""
import json
import urllib.error
import urllib.request
import uuid

API = "http://localhost:8000"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or "null")


def status(method, path, body):
    try:
        call(method, path, body)
        return 200
    except urllib.error.HTTPError as e:
        return e.code


def event(visitor, variant, kind):
    call("POST", "/landing/events", {"visitor": visitor, "variant": variant, "kind": kind})


def lead(visitor, variant, **kw):
    return {"visitor": visitor, "variant": variant, "company": "Via Sul", "size": 40, "email": "cco@viasul.com.br", **kw}


call("DELETE", "/landing/data")
a1, a2, a3, b1 = (str(uuid.uuid4()) for _ in range(4))
for v in (a1, a1, a2, a3):  # a1 recarrega a página: conta uma visita só
    event(v, "A", "visit")
event(b1, "B", "visit")
event(a1, "A", "click")
event(a1, "A", "click")
event(b1, "B", "click")
call("POST", "/leads", lead(a1, "A"))
call("POST", "/leads", lead(a1, "A", size=55))  # reenvio atualiza, não duplica

assert status("POST", "/leads", lead(a2, "A", email="x@gmail.com")) == 422
assert status("POST", "/leads", lead(a2, "A", ip="1.2.3.4")) == 422
assert status("POST", "/landing/events", {"visitor": a2, "variant": "C", "kind": "visit"}) == 422

m = call("GET", "/landing/metrics")
assert {k: m["A"][k] for k in ("visits", "clicks", "leads")} == {"visits": 3, "clicks": 1, "leads": 1}, m["A"]
assert {k: m["B"][k] for k in ("visits", "clicks", "leads")} == {"visits": 1, "clicks": 1, "leads": 0}, m["B"]
assert abs(m["A"]["ctr"] - 1 / 3) < 1e-9 and m["B"]["ctr"] == 1 and m["total"]["ctr"] == 0.5, m
assert m["goal_ctr"] == 0.15 and m["goal_leads"] == 3
assert len(m["recent"]) == 1 and m["recent"][0]["size"] == 55 and set(m["recent"][0]) == {"variant", "company", "size", "email", "created_at"}

call("POST", "/sim/scenario/demo")  # recarregar o Demo não pode apagar leads
assert call("GET", "/landing/metrics")["total"]["leads"] == 1

call("DELETE", "/landing/data")
assert call("GET", "/landing/metrics")["total"] == {"visits": 0, "clicks": 0, "leads": 0, "ctr": None}
print("OK: Fatia 2 (backend) — visitas/cliques idempotentes, A/B separado, lead validado, Demo preserva leads")
