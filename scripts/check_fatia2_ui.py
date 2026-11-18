#!/usr/bin/env python3
"""Aceitação da Fatia 2 (tela): landing A e B -> clique no CTA -> formulário -> lead -> vista de conversão.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema). ZERA as métricas da landing.
Uso: python3 scripts/check_fatia2_ui.py <pasta para os prints>"""
import json, sys, urllib.request
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
def api(m, p):
    return json.loads(urllib.request.urlopen(urllib.request.Request("http://localhost:8000" + p, method=m)).read())
api("DELETE", "/landing/data")
CTA = {"A": "QUERO SOLICITAR O PILOTO GRATUITO →", "B": "AGENDAR DEMONSTRAÇÃO TÉCNICA DO PAINEL CCO (15 MIN) →"}
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    errs = []
    for v in ("A", "B"):
        pg = b.new_context(viewport={"width": 1440, "height": 900}).new_page()  # contexto novo = visitante novo
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(f"http://localhost:5173/landing?v={v}")
        expect(pg.get_by_role("heading", level=1)).to_have_text("Reduza em até 9% os custos de frota ociosa com monitoramento IoT em tempo real")
        pg.screenshot(path=f"{S}/landing-{v}.png")
        pg.get_by_role("button", name=CTA[v]).click()
        if v == "A":
            pg.get_by_label("Empresa / concessionária").fill("Via Sul Transportes")
            pg.get_by_label("Quantidade estimada de linhas / pontos").fill("40")
            pg.get_by_label("E-mail corporativo").fill("cco@gmail.com")
            pg.get_by_role("button", name="Enviar").click()
            expect(pg.get_by_role("alert")).to_have_text("Use o e-mail corporativo.")
            pg.screenshot(path=f"{S}/form-A.png")
            pg.get_by_label("E-mail corporativo").fill("cco@viasul.com.br")
            pg.get_by_role("button", name="Enviar").click()
            expect(pg.get_by_role("status")).to_contain_text("instalação do lote piloto")
            pg.screenshot(path=f"{S}/done-A.png")
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto("http://localhost:5173/landing/metricas")
    expect(pg.locator(".kpi-cell").nth(2)).to_contain_text("100,0%")
    expect(pg.locator(".kpi-cell").nth(3)).to_contain_text("1 / 3")
    expect(pg.get_by_text("Via Sul Transportes")).to_be_visible()
    pg.screenshot(path=f"{S}/conversao.png", full_page=True)
    m = api("GET", "/landing/metrics")
    assert (m["A"]["visits"], m["A"]["clicks"], m["A"]["leads"], m["B"]["visits"], m["B"]["clicks"], m["B"]["leads"]) == (1, 1, 1, 1, 1, 0), m
    assert not errs, errs
    print("OK: Fatia 2 (tela) — A e B renderizam, e-mail gratuito barrado, lead aparece na conversão")
