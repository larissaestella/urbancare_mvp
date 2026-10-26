#!/usr/bin/env python3
"""Aceitação da Fatia 3, item 4 (Relatórios, Figma 05 + toast 10:212): conteúdo verbatim, toast, aviso do PDF, toggles.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia3_relatorios_ui.py <pasta para os prints>"""
import sys
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1064})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:5173/")
    pg.get_by_role("button", name="Relatórios").click()
    expect(pg).to_have_url("http://localhost:5173/relatorios")
    expect(pg.locator(".title-plate")).to_contain_text("Relatórios periódicos para concessionárias, anunciantes e gestão pública")
    kpi = pg.locator(".kpi-strip")
    for t in ["14", "3 a mais que julho", "de 14 no mês", "2 campanhas em veiculação", "Seg 07h"]:
        expect(kpi).to_contain_text(t)
    rows = pg.locator(".rl-table tbody tr")
    expect(rows).to_have_count(5)
    expect(rows.first).to_contain_text("Comprovação de campanha · Marca Aurora")
    expect(pg.locator(".rl-table .pill--normal")).to_have_count(3)
    expect(pg.locator(".rl-table .pill--destaque")).to_have_count(2)
    sw = pg.get_by_role("switch")
    expect(sw).to_have_count(4)
    expect(sw.nth(3)).to_have_attribute("aria-checked", "false")
    expect(pg.locator(".rl-content li")).to_have_count(4)
    expect(pg.locator(".rl-foot")).to_contain_text("simulação para validação (Sprint 2)")
    pg.screenshot(path=f"{S}/relatorios.png")
    print("ok: título, KPIs, 5 relatórios recentes, agendamentos, conteúdo, rodapé §8.1")
    sw.nth(3).click()
    expect(sw.nth(3)).to_have_attribute("aria-checked", "true")
    print("ok: toggle de agendamento alterna")
    pg.get_by_role("button", name="Gerar relatório").click()
    expect(pg.locator(".rl-toast")).to_contain_text("Relatório gerado")
    expect(pg.locator(".rl-toast")).to_contain_text("PDF auditado da campanha pronto para enviar à marca")
    pg.screenshot(path=f"{S}/relatorios-toast.png")
    print("ok: Gerar relatório mostra o toast do Figma")
    rows.first.get_by_role("button", name="Baixar PDF").click()
    expect(pg.get_by_role("status")).to_contain_text("dados reais do piloto")
    print("ok: Baixar PDF avisa que entra com os dados do piloto")
    print("erros de página:", errs)
    assert not errs
    b.close()
