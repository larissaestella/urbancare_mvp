#!/usr/bin/env python3
"""Aceitação da Fatia 3 (Detalhe do ponto SP-0412): dados do Demo, envio pela recomendação, navegação de volta.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia3_ui.py <pasta para os prints>"""
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
    pg.locator(".alert-row").get_by_role("link", name="Av. Paulista, 1578").click()
    expect(pg).to_have_url("http://localhost:5173/pontos/SP-0412")
    head = pg.locator(".dt-head")
    expect(head).to_contain_text("Av. Paulista, 1578 — sentido Consolação")
    expect(head).to_contain_text("Crítico")
    expect(head).to_contain_text("875A177H6450")
    expect(head).to_contain_text("Sensor SP-0412 (simulado)")
    stats = pg.locator(".dt-stats")
    expect(stats).to_contain_text("26acima do limite (20)")
    expect(stats).to_contain_text("17 min")
    expect(stats).to_contain_text("875A · 6 min")
    expect(pg.locator(".dt-scene")).to_contain_text("26 pessoas no ponto")
    pg.screenshot(path=f"{S}/detalhe.png")
    print("ok: cabeçalho, 26 pessoas, 17 min, crítico, 3 linhas")
    pg.get_by_role("button", name="Enviar para a garagem").click()
    dlg = pg.get_by_role("dialog")
    expect(dlg).to_contain_text("Enviar 1 ônibus extra na linha 875A?")
    dlg.get_by_role("button", name="Confirmar envio").click()
    expect(pg.get_by_role("status")).to_contain_text("Ônibus extra enviado na linha 875A")
    expect(pg.get_by_role("button", name="Extra a caminho")).to_be_visible(timeout=4000)
    pg.screenshot(path=f"{S}/detalhe-enviado.png")
    print("ok: recomendação -> diálogo -> toast -> extra a caminho")
    api("POST", "/sim/clock", {"multiplier": 30, "paused": False})
    expect(pg.locator(".dt-head")).not_to_contain_text("Crítico", timeout=40000)
    api("POST", "/sim/clock", {"paused": True})
    expect(pg.locator(".dt-stats")).to_contain_text("dentro do limite (20)")
    pg.screenshot(path=f"{S}/detalhe-chegou.png")
    print("ok: extra chegou, ponto saiu do crítico:", pg.locator(".dt-stats").inner_text().split("\n")[1])
    pg.get_by_role("button", name="Visão geral").click()
    expect(pg.locator(".kpi-cell").nth(3)).to_contain_text("13")
    expect(pg.locator(".alert-row", has_text="Av. Paulista, 1578")).to_have_count(0)
    print("ok: Visão geral com 13 extras e Paulista fora da lista")
    api("POST", "/sim/scenario/demo")
    print("erros de página:", errs)
    assert not errs
    b.close()
