#!/usr/bin/env python3
"""Aceitação da Fatia 3, item 2 (Publicidade, render 03): conteúdo verbatim, navegação pela sidebar, botões com aviso honesto.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia3_publicidade_ui.py <pasta para os prints>"""
import sys
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1064})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:5173/")
    pg.get_by_role("button", name="Publicidade").click()
    expect(pg).to_have_url("http://localhost:5173/publicidade")
    expect(pg.locator(".title-plate")).to_contain_text("Mídia OOH · 38 painéis em pontos de ônibus · semana 24/08 – 30/08")
    expect(pg.get_by_role("button", name="Semanal")).to_have_attribute("aria-pressed", "true")
    kpi = pg.locator(".kpi-strip")
    for t in ["412 mil", "7m 40s", "68%", "R$ 14,20", "▲ vs. R$ 9,00 estimado hoje"]:
        expect(kpi).to_contain_text(t)
    expect(pg.locator(".pb-heat td")).to_have_count(42)
    expect(pg.locator(".pb-heat tbody tr").nth(4)).to_contain_text("100969895")
    expect(pg.locator(".pb-rank tbody tr")).to_have_count(5)
    expect(pg.locator(".pb-rank tbody tr").first).to_contain_text("Av. Paulista, 1578")
    expect(pg.locator(".pb-camp__row")).to_contain_text("336 mil / 300 mil · 112%")
    expect(pg.locator(".pb-foot")).to_contain_text("simulação para validação (Sprint 2)")
    pg.screenshot(path=f"{S}/publicidade.png")
    print("ok: título, KPIs, mapa de calor 6×7, ranking, campanha, rodapé §8.1")
    pg.get_by_role("button", name="Gerar relatório auditado (PDF)").click()
    expect(pg.get_by_role("status")).to_contain_text("dados reais do piloto")
    pg.get_by_role("button", name="Mensal").click()
    expect(pg.locator(".pb-empty")).to_contain_text("Audiência mensal entra com os dados reais do piloto.")
    print("ok: PDF e Mensal mostram aviso do piloto, sem gerar nada")
    pg.get_by_role("button", name="Visão geral").click()
    expect(pg.locator(".kpi-strip")).to_be_visible()
    print("ok: volta à Visão geral")
    print("erros de página:", errs)
    assert not errs
    b.close()
