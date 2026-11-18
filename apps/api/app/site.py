"""Implantação em um único serviço (Render): a API fica em /api e o build do React é servido no resto.
Localmente o docker compose continua usando app.main:app e o proxy do Vite."""
import os
from pathlib import Path

from starlette.responses import FileResponse

from .main import app as api

STATIC = Path(os.environ.get("STATIC_DIR", "/srv/static")).resolve()


async def app(scope, receive, send):
    if scope["type"] == "lifespan":
        return await api(scope, receive, send)
    path = scope.get("path", "/")
    if path == "/api" or path.startswith("/api/"):
        inner = dict(scope, path=path[4:] or "/", root_path=scope.get("root_path", "") + "/api")
        return await api(inner, receive, send)
    if scope["type"] != "http":
        return
    target = (STATIC / path.lstrip("/")).resolve()
    if not target.is_relative_to(STATIC) or not target.is_file():
        target = STATIC / "index.html"  # rotas do front (/, /cadastro-endereco, /pontos/…) caem no SPA
    headers = {"cache-control": "public, max-age=31536000, immutable"} if "/assets/" in path else {}
    await FileResponse(target, headers=headers)(scope, receive, send)
