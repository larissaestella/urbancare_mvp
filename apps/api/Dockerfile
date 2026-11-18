FROM python:3.12-slim
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/install_ocr_model.py scripts/install_ocr_model.py
RUN python scripts/install_ocr_model.py --output /usr/local/share/tessdata-best
COPY . .
ENV TESSDATA_BEST_DIR=/usr/local/share/tessdata-best
ENV TMPDIR=/dev/shm
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
