FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY README.md pyproject.toml ./
COPY ruvos_google_docs_mcp ./ruvos_google_docs_mcp

RUN pip install --upgrade pip && pip install .

# Cloud Run sets PORT (default 8080).
ENV HOST=0.0.0.0 \
    PORT=8080

EXPOSE 8080

CMD ["ruvos-google-docs-mcp"]
