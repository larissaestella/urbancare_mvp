#!/usr/bin/env python3
"""Aceitação da Fatia 3, item 3 (Frota, Figma 04): conteúdo verbatim, relógio da simulação (§8.3), rodapé §8.1, navegação.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia3_frota_ui.py <pasta para os prints>"""
import sys
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1064})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:5173/")
    pg.get_by_role("button", name="Frota").click()
    expect(pg).to_have_url("http://localhost:5173/frota")
    expect(pg.locator(".title-plate")).to_contain_text("Concessionária Via Sul · 4 garagens · 186 ônibus em operação")
    expect(pg.locator(".ov__clock")).to_be_visible()
    expect(pg.locator(".title-plate")).not_to_contain_text("31/08")
    kpi = pg.locator(".kpi-strip")
    for t in ["186", "3 extras em rota agora", "9 concluídos · 3 a caminho", "−9%", "8 min", "do alerta à chegada do extra"]:
        expect(kpi).to_contain_text(t)
    expect(pg.locator(".fr-envios li")).to_have_count(5)
    expect(pg.locator(".fr-envios li").first).to_contain_text("Garagem Vila Mariana → Av. Paulista, 1578")
    expect(pg.locator(".fr-envios .pill--destaque")).to_have_count(3)
    expect(pg.locator(".fr-envios .pill--normal")).to_have_count(2)
    expect(pg.locator(".fr-garagens tbody tr")).to_have_count(4)
    expect(pg.locator(".fr-occ__track i.is-over")).to_have_count(1)
    expect(pg.locator(".fr-occ__msg")).to_contain_text("Linha 875A acima do limite de conforto")
    expect(pg.locator(".fr-km__col")).to_have_count(4)
    expect(pg.locator(".fr-foot")).to_contain_text("simulação para validação (Sprint 2)")
    pg.locator(".kpi-strip").wait_for()
    pg.screenshot(path=f"{S}/frota.png")
    print("ok: título, relógio §8.3, KPIs, envios, garagens, ocupação, km ocioso, rodapé §8.1")
    pg.get_by_role("button", name="Visão geral").click()
    expect(pg.locator(".kpi-strip")).to_be_visible()
    print("ok: volta à Visão geral")
    print("erros de página:", errs)
    assert not errs
    b.close()
