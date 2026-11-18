# Imagem única para o Render: front (build do Vite) + API + simulador. Local: use docker compose.
FROM node:22-alpine AS web
WORKDIR /web
COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY apps/web/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*
COPY apps/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY apps/api/scripts/install_ocr_model.py scripts/install_ocr_model.py
RUN python scripts/install_ocr_model.py --output /usr/local/share/tessdata-best
COPY apps/api/ ./
COPY apps/sim/sim.py ./sim.py
COPY --from=web /web/dist /srv/static
ENV TESSDATA_BEST_DIR=/usr/local/share/tessdata-best \
    TMPDIR=/dev/shm \
    STATIC_DIR=/srv/static \
    PORT=8000 \
    RUN_SIM=1
CMD ["sh", "-c", "if [ \"$RUN_SIM\" = 1 ]; then (until python -c \"import urllib.request as u; u.urlopen('http://localhost:'+'$PORT'+'/api/health')\" 2>/dev/null; do sleep 2; done; API_URL=http://localhost:$PORT/api exec python -u sim.py) & fi; exec uvicorn app.site:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'"]
