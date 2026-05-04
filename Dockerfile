FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install -r /app/requirements.txt

COPY app /app/app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "import json,sys,urllib.request; data=json.loads(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read().decode()); sys.exit(0 if data.get('status') == 'ok' else 1)"

CMD ["python", "-m", "app.main"]
