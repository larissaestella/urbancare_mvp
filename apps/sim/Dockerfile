FROM python:3.12-slim
WORKDIR /srv
RUN pip install --no-cache-dir httpx==0.28.1
COPY sim.py .
CMD ["python", "-u", "sim.py"]
