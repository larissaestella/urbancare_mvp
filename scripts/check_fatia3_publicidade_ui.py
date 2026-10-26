#!/usr/bin/env python3
"""Aceitação da Fatia 3, item 2 (Publicidade, render 03): conteúdo verbatim, navegação pela sidebar, botões com aviso honesto.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia3_publicidade_ui.py <pasta para os prints>"""
import sys
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    ctx = b.new_context(viewport={"width": 1440, "height": 1064}, accept_downloads=True)
    ctx.add_init_script("window.print = () => { window.__printed = true }")
    pg = ctx.new_page()
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
    with pg.expect_popup() as pop:
        pg.get_by_role("button", name="Gerar relatório auditado (PDF)").click()
    expect(pop.value.locator(".rp-head")).to_contain_text("Comprovação de campanha · Marca Aurora")
    pop.value.wait_for_function("window.__printed === true")
    pop.value.close()
    pg.get_by_role("button", name="Compartilhar com a marca").click()
    expect(pg.get_by_role("status")).to_contain_text("Link do relatório auditado copiado")
    with pg.expect_download() as dl:
        pg.get_by_role("button", name="Exportar relatório ↓").click()
    csv = open(dl.value.path(), encoding="utf-8-sig").read()
    assert dl.value.suggested_filename == "urbanflow-audiencia-semanal.csv", dl.value.suggested_filename
    assert '"Pessoas expostas";"412000"' in csv and '"Av. Paulista, 1578";"28400"' in csv, csv[:300]
    print("ok: relatório auditado abre o PDF da campanha; compartilhar copia o link; Exportar baixa o CSV semanal")
    pg.get_by_role("button", name="Mensal").click()
    expect(pg.locator(".title-plate")).to_contain_text("agosto (03/08 – 30/08)")
    expect(pg.locator(".kpi-strip")).to_contain_text("1,47 mi")
    expect(pg.locator(".kpi-strip")).to_contain_text("▲ 14% vs. julho")
    expect(pg.locator(".pb-bars__row")).to_have_count(4)
    expect(pg.locator(".pb-bars__row").nth(3)).to_contain_text("412,0 mil")
    pg.screenshot(path=f"{S}/publicidade-mensal.png")
    pg.get_by_role("button", name="Diária").click()
    expect(pg.locator(".title-plate")).to_contain_text("sex 28/08")
    expect(pg.locator(".pb-bars__row")).to_have_count(6)
    pg.get_by_role("group", name="Dia da semana").get_by_role("button", name="Dom").click()
    expect(pg.locator(".title-plate")).to_contain_text("dom 30/08")
    expect(pg.locator(".kpi-strip")).to_contain_text("vs. média diária da semana")
    pg.screenshot(path=f"{S}/publicidade-diaria.png")
    pg.get_by_role("button", name="Semanal").click()
    expect(pg.locator(".kpi-strip")).to_contain_text("412 mil")
    expect(pg.locator(".pb-rank tbody tr").first).to_contain_text("28,4 mil")
    print("ok: Mensal (4 semanas, 1,47 mi) e Diária (seletor de dia) com números derivados da semana; Semanal intacta")
    pg.get_by_role("button", name="Visão geral").click()
    expect(pg.locator(".kpi-strip")).to_be_visible()
    print("ok: volta à Visão geral")
    print("erros de página:", errs)
    assert not errs
    b.close()
