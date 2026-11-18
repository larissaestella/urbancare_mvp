#!/usr/bin/env python3
"""Aceitação da Fatia 1 (tela): Enviar extra -> diálogo -> toast -> EXTRA A CAMINHO -> lotação cai, no navegador.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia1_ui.py <pasta para os prints>"""
import json, sys, urllib.request
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
def api(m, p, b=None):
    r = urllib.request.Request("http://localhost:8000" + p, method=m, data=json.dumps(b).encode() if b is not None else None,
                               headers={"content-type": "application/json"})
    return json.loads(urllib.request.urlopen(r).read())
api("POST", "/sim/scenario/demo")
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1064})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:5173/")
    row = pg.locator(".alert-row", has_text="Av. Paulista, 1578")
    row.get_by_role("button", name="Enviar extra").click()
    dlg = pg.get_by_role("dialog")
    expect(dlg).to_contain_text("Enviar 1 ônibus extra na linha 875A?")
    expect(dlg).to_contain_text("Saída: Garagem Vila Mariana → Av. Paulista, 1578")
    expect(dlg).to_contain_text("ETA estimado: 9 min · lotação atual do ponto: 26 pessoas")
    pg.screenshot(path=f"{S}/dialog.png")
    dlg.get_by_role("button", name="Confirmar envio").click()
    expect(pg.get_by_role("status")).to_contain_text("Ônibus extra enviado na linha 875A")
    expect(row.get_by_role("button", name="Extra a caminho")).to_be_visible(timeout=4000)
    expect(pg.locator(".kpi-cell").nth(3)).to_contain_text("13")
    pg.screenshot(path=f"{S}/sent.png")
    print("ok: diálogo, toast, extra a caminho, 13 extras")
    api("POST", "/sim/clock", {"multiplier": 30, "paused": False})
    expect(pg.locator(".alert-row", has_text="Av. Paulista, 1578")).to_have_count(0, timeout=40000)
    print("ok: lotação caiu e Paulista saiu da lista; KPI:", pg.locator(".kpi-cell").nth(2).inner_text().replace("\n", " "))
    pg.screenshot(path=f"{S}/after.png")
    api("POST", "/sim/scenario/demo")
    print("erros de página:", errs)
    b.close()
