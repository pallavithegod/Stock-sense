FROM python:3.13-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_ENV=production \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000 \
    DISABLE_STARTUP_NETWORK=True \
    OPEN_BROWSER=False

WORKDIR /app

RUN addgroup --system stocksense \
    && adduser --system --ingroup stocksense --home /app stocksense

COPY pyproject.toml README.md gunicorn.conf.py ./
COPY app.py ./
COPY backend ./backend
COPY scripts ./scripts

RUN python -m pip install --upgrade pip \
    && python -m pip install --no-cache-dir .

RUN mkdir -p /app/data /app/logs /app/cache /app/models \
    && chown -R stocksense:stocksense /app

USER stocksense

EXPOSE 5000
VOLUME ["/app/data", "/app/logs", "/app/cache", "/app/models"]

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD python -c "import os, urllib.request; port = os.environ.get('PORT') or os.environ.get('FLASK_PORT') or '5000'; urllib.request.urlopen(f'http://127.0.0.1:{port}/health/live', timeout=3).read()"

CMD ["gunicorn", "-c", "gunicorn.conf.py", "backend.wsgi:app"]
