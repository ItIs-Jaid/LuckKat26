# KB dashboard — minimal, local-first FastAPI image.
# No uv (deterministic pip from requirements.txt). Non-root. Reads KB_DB_PATH.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    KB_DB_PATH=/data/kb.db

WORKDIR /app

# Deps first for layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App (server + db + static). Tests are not shipped.
COPY server.py db.py ./
COPY static ./static

# Run as non-root; mount the NAS SQLite at /data (read-only in k8s).
RUN useradd -m -u 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port 8000"]
