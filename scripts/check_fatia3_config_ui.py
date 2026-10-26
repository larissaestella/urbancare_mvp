#!/usr/bin/env python3
"""Aceitação da Fatia 3, item 4 (Configurações, Figma 06): conteúdo verbatim, seções colapsáveis, toggles, aviso de conta.
Pré-requisito: docker compose up; pip install playwright (usa o Chrome do sistema).
Uso: python3 scripts/check_fatia3_config_ui.py <pasta para os prints>"""
import sys
from playwright.sync_api import sync_playwright, expect
S = sys.argv[1]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width": 1440, "height": 1064})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto("http://localhost:5173/")
    pg.get_by_role("button", name="Configurações").click()
    expect(pg).to_have_url("http://localhost:5173/configuracoes")
    expect(pg.locator(".title-plate")).to_contain_text("Conta, aparência, idioma e região, regra de envio e segurança")
    heads = pg.locator(".cf-sec__head")
    expect(heads).to_have_count(6)
    expect(pg.locator('.cf-sec__head[aria-expanded="true"]')).to_have_count(2)
    expect(pg.get_by_label("E-mail")).to_have_value("carla.mendes@viasul.com.br")
    expect(pg.get_by_label("Cargo")).to_have_value("Gestora de operação")
    expect(pg.get_by_role("switch")).to_have_count(3)
    expect(pg.locator(".cf-foot")).to_contain_text("simulação para validação (Sprint 2)")
    pg.screenshot(path=f"{S}/configuracoes.png", full_page=True)
    print("ok: título, 6 seções (Conta e Aparência abertas), campos da conta, 3 toggles, rodapé §8.1")
    pg.get_by_role("button", name="Escuro").click()
    expect(heads.nth(1)).to_contain_text("Escuro · Confortável")
    print("ok: segmentado de tema atualiza o resumo")
    heads.nth(3).click()
    expect(pg.get_by_label("Limite de lotação")).to_have_value("20 pessoas")
    expect(pg.get_by_label("Tempo acima do limite")).to_have_value("5 min")
    pg.get_by_role("switch", name="Regra ativa").click()
    expect(heads.nth(3)).to_contain_text("Inativa")
    heads.nth(0).click()
    expect(pg.get_by_label("E-mail")).to_have_count(0)
    print("ok: seções abrem e fecham; regra mostra 20 pessoas / 5 min e o toggle reflete no resumo")
    heads.nth(4).click(); heads.nth(5).click()
    expect(pg.locator(".cf")).to_contain_text("Hoje, 18:40 · São Paulo")
    expect(pg.locator(".cf")).to_contain_text("Protótipo Sprint 2 · simulação")
    pg.screenshot(path=f"{S}/configuracoes-abertas.png", full_page=True)
    pg.get_by_role("button", name="Sair", exact=True).click()
    expect(pg.get_by_role("status")).to_contain_text("login real")
    print("ok: Segurança e Sobre abrem; Sair avisa que entra com o login real")
    print("erros de página:", errs)
    assert not errs
    b.close()
