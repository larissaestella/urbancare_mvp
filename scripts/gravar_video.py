#!/usr/bin/env python3
"""Grava o vídeo demonstrativo de 45 s da landing (docx Sprint 2, smoke test) dirigindo o painel com o Playwright.
Roteiro: Visão geral → alerta da Paulista → Enviar extra → Detalhe (relógio a 30× até o extra chegar, com corte na espera)\n→ histórico semanal → Publicidade. A rede não aparece com o relógio andando (a deriva do simulador contradiria a cena).
Pré-requisito: docker compose up; pip install playwright; ffmpeg. ALTERA o estado (despacho, relógio): no fim pausa e
recarrega o Demo. Uso: python3 scripts/gravar_video.py <pasta temporária> → apps/web/public/video/urbancare-45s.mp4"""
import json
import pathlib
import subprocess
import sys
import time
import urllib.request

API, WEB = "http://localhost:8000", "http://localhost:5173"
OUT = pathlib.Path(__file__).resolve().parents[1] / "apps/web/public/video/urbancare-45s.mp4"
W, H = 1440, 810


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or "null")


def reset():
    call("POST", "/sim/clock", {"paused": True})
    time.sleep(3)  # leituras do sim em voo entram antes do reset, não depois
    call("POST", "/sim/scenario/demo")
    time.sleep(2)


# cursor e legenda desenhados na página: o vídeo do Playwright não mostra o mouse
OVERLAY = """
addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.id = '__cursor';
  c.style.cssText = 'position:fixed;z-index:99999;width:22px;height:22px;margin:-11px 0 0 -11px;border-radius:50%;' +
    'background:rgba(255,210,0,.85);border:2px solid #16181b;pointer-events:none;left:-40px;top:-40px;transition:transform .12s';
  document.body.appendChild(c);
  addEventListener('mousemove', e => { c.style.left = e.clientX + 'px'; c.style.top = e.clientY + 'px'; });
  addEventListener('mousedown', () => c.style.transform = 'scale(.6)');
  addEventListener('mouseup', () => c.style.transform = 'scale(1)');
  const k = document.createElement('div');
  k.id = '__caption';
  k.style.cssText = 'position:fixed;z-index:99998;left:50%;bottom:28px;transform:translateX(-50%);max-width:1000px;' +
    'background:#16181b;color:#fff;border-top:4px solid #ffd200;border-radius:3px;padding:14px 22px;' +
    'font:600 22px/1.3 "Barlow Semi Condensed",Barlow,sans-serif;text-align:center;opacity:0;transition:opacity .3s';
  document.body.appendChild(k);
});
"""


def caption(pg, text):
    pg.evaluate("t => { const k = document.getElementById('__caption'); k.textContent = t; k.style.opacity = t ? 1 : 0; }", text)


def move_click(pg, loc, click=True):
    box = loc.bounding_box()
    pg.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=25)
    time.sleep(0.3)
    if click:
        loc.click()


def main(tmp):
    from playwright.sync_api import sync_playwright, expect
    reset()
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        ctx = b.new_context(viewport={"width": W, "height": H}, record_video_dir=tmp, record_video_size={"width": W, "height": H})
        ctx.add_init_script(OVERLAY)
        pg = ctx.new_page()
        pg.goto(WEB + "/")
        expect(pg.locator(".kpi-strip")).to_contain_text("1.284")
        pg.mouse.move(W / 2, H / 2)
        t0 = time.monotonic()  # início útil do vídeo (corta o carregamento)

        caption(pg, "Contagem anônima em 142 pontos de ônibus: só números saem do ponto, nenhuma imagem")
        time.sleep(4.5)
        caption(pg, "Av. Paulista: 26 pessoas e 17 min de espera — acima do limite de 20 há mais de 5 min")
        move_click(pg, pg.locator(".alert-row", has_text="Av. Paulista, 1578"), click=False)
        time.sleep(3.5)
        caption(pg, "O sistema sugere 1 ônibus extra da garagem — o operador envia com um clique")
        move_click(pg, pg.locator(".alert-row", has_text="Av. Paulista, 1578").get_by_role("button", name="Enviar extra"))
        time.sleep(1.2)
        move_click(pg, pg.get_by_role("button", name="Confirmar envio"))
        expect(pg.get_by_role("status")).to_contain_text("Ônibus extra enviado")
        time.sleep(2.5)

        caption(pg, "Extra a caminho: o ponto é acompanhado ao vivo")
        pg.goto(WEB + "/pontos/SP-0412")
        caption(pg, "Extra a caminho: o ponto é acompanhado ao vivo")
        expect(pg.locator(".dt-stats")).to_contain_text("26")
        time.sleep(2.5)
        caption(pg, "Simulação acelerada: o extra chega e a fila do ponto esvazia")
        call("POST", "/sim/clock", {"paused": False})
        w0 = time.monotonic() - t0
        expect(pg.locator(".title-plate .pill--critico")).to_have_count(0, timeout=40000)
        arr = time.monotonic() - t0
        time.sleep(3)
        call("POST", "/sim/clock", {"paused": True})
        cut = (w0 + 3, arr - 1.5)  # trecho de espera que sai na edição
        kept = lambda: time.monotonic() - t0 - (cut[1] - cut[0])

        caption(pg, "Histórico do ponto por dia, semana e mês")
        plate = pg.locator(".plate", has_text="Lotação ao longo do tempo")
        for _ in range(8):
            pg.mouse.wheel(0, 60); time.sleep(0.05)
        plate.scroll_into_view_if_needed()
        time.sleep(0.8)
        move_click(pg, plate.get_by_role("button", name="Semanal"))
        time.sleep(3.5)

        pg.goto(WEB + "/publicidade")
        caption(pg, "A mesma contagem vira audiência medida para os painéis de mídia")
        time.sleep(3)
        for _ in range(10):
            pg.mouse.wheel(0, 40); time.sleep(0.08)
        time.sleep(max(1.0, 42 - kept()))
        caption(pg, "UrbanCare — solicite o piloto gratuito")
        time.sleep(3.5)
        total = time.monotonic() - t0
        video = pg.video.path()
        ctx.close()
        b.close()
    reset()
    off = max(0.0, _duration(video) - total)  # o vídeo começa antes de t0 (carregamento)
    a, c = off + cut[0], off + cut[1]
    graph = (f"[0:v]trim=start={off:.2f}:end={a:.2f},setpts=PTS-STARTPTS[v0];"
             f"[0:v]trim=start={c:.2f},setpts=PTS-STARTPTS[v1];[v0][v1]concat=n=2:v=1[v]")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-filter_complex", graph, "-map", "[v]", "-t", "45",
                    "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-an", str(OUT)],
                   check=True)
    print(f"ok: {OUT} ({_duration(str(OUT)):.1f} s; roteiro {total:.1f} s)")


def _duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True, check=True).stdout)


if __name__ == "__main__":
    main(sys.argv[1])
