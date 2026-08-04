# Runtime del chat A/B. Se construye desde una release ya instalada y
# verificada por hash en el host; la imagen no clona el repositorio ni trae
# credenciales. No incluye los PDF de fuente: el runtime necesita el caso v3 y
# las páginas verbatim derivadas, no los originales.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/srv/chat/src \
    UV_PROJECT_ENVIRONMENT=/srv/venv \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv==0.9.7 \
    && useradd --system --uid 10001 --home-dir /srv --shell /usr/sbin/nologin chat

WORKDIR /srv/chat

# Las dependencias se resuelven desde el lock, no desde el rango del
# `pyproject.toml`: el runtime desplegado tiene que ser el que se probó.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY . /srv/chat

USER 10001:10001
EXPOSE 8000

# Un solo proceso: la cuota y el anti-replay viven en memoria y repartirlos
# entre workers los volvería decorativos.
CMD ["/srv/venv/bin/uvicorn", "api.main:app", \
     "--host", "0.0.0.0", "--port", "8000", "--workers", "1", \
     "--timeout-graceful-shutdown", "20"]
