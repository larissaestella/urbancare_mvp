#!/usr/bin/env python3
"""Aceitação da profundidade (PLANO §8.6): lista de pontos, Monitorar, Ver todos, clique no mapa, 38 painéis.
Pré-requisito: docker compose up e cenário Demo carregado (POST /sim/scenario/demo); pip install playwright.
Uso: python3 scripts/check_profundidade_ui.py <pasta para os prints>"""
import sys
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1064})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:5173/")
    pg.evaluate("localStorage.removeItem('urbancare.monitorando')")
    pg.reload()
    row = pg.locator(".alert-row").filter(has=pg.get_by_role("button", name="Monitorar")).first
    name = row.locator(".t-metric-s").inner_text()
    row.get_by_role("button", name="Monitorar").click()
    expect(pg.locator(".alert-row", has_text=name).get_by_role("button", name="Monitorando")).to_have_attribute("aria-pressed", "true")
    print("ok: Monitorar alterna para Monitorando:", name)
    pg.get_by_role("link", name="Ver todos →").click()
    expect(pg).to_have_url("http://localhost:5173/pontos")
    expect(pg.locator(".pt-table tbody tr")).to_have_count(142)
    expect(pg.locator(".title-plate")).to_contain_text("142 pontos monitorados")
    pg.screenshot(path=f"{S}/pontos.png")
    pg.get_by_role("button", name="Monitorando", exact=True).first.wait_for()
    pg.locator(".pt-bar").get_by_role("button", name="Monitorando").click()
    expect(pg.locator(".pt-table tbody tr")).to_have_count(1)
    expect(pg.locator(".pt-table tbody tr")).to_contain_text(name)
    print("ok: lista com 142 pontos; filtro Monitorando mostra o ponto marcado na Visão geral")
    pg.locator(".pt-bar").get_by_role("button", name="Em alerta").click()
    n_alert = pg.locator(".pt-table tbody tr").count()
    expect(pg.locator(".title-plate")).to_contain_text(f"{n_alert} em alerta")
    pg.locator(".pt-bar").get_by_role("button", name="Todos").click()
    pg.get_by_label("Buscar ponto").fill("paulista, 1578")
    expect(pg.locator(".pt-table tbody tr")).to_have_count(1)
    pg.get_by_role("link", name="Av. Paulista, 1578").click()
    expect(pg).to_have_url("http://localhost:5173/pontos/SP-0412")
    pg.get_by_role("link", name="Pontos de ônibus").click()
    expect(pg).to_have_url("http://localhost:5173/pontos")
    print(f"ok: filtro Em alerta ({n_alert}), busca, link para o Detalhe e volta pelo breadcrumb")
    pg.goto("http://localhost:5173/")
    pg.locator(".map__stop[aria-label^='Av. Paulista, 1578']").click()
    expect(pg).to_have_url("http://localhost:5173/pontos/SP-0412")
    pg.goto("http://localhost:5173/")
    other = pg.locator(".map__stop:not([aria-label^='Av. Paulista, 1578'])").first
    other_name = other.get_attribute("aria-label").split(":")[0]
    other.click()
    pg.wait_for_url("**/pontos?busca=SP-*")
    expect(pg.locator(".pt-table tbody tr")).to_have_count(1)
    expect(pg.locator(".pt-table tbody tr")).to_contain_text(other_name)
    print("ok: clique no mapa: SP-0412 abre o Detalhe; outro ponto abre a lista filtrada:", other_name)
    pg.goto("http://localhost:5173/publicidade")
    pg.get_by_role("button", name="Ver todos →").click()
    dlg = pg.get_by_role("dialog")
    expect(dlg.locator("tbody tr")).to_have_count(38)
    expect(dlg.locator("tbody tr").first).to_contain_text("28,4 mil")
    pg.screenshot(path=f"{S}/publicidade-todos.png")
    pg.keyboard.press("Escape")
    expect(dlg).to_have_count(0)
    print("ok: Publicidade Ver todos lista os 38 painéis")
    pg.evaluate("localStorage.removeItem('urbancare.monitorando')")
    print("erros de página:", errs)
    assert not errs
    b.close()
