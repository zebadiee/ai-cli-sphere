FROM python:3.12-slim

RUN pip install --no-cache-dir requests jsonschema

RUN useradd -m ctuser
USER ctuser

WORKDIR /app

COPY . /app

CMD ["python", "/app/orchestrator.py"]
