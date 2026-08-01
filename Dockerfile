FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

COPY . .

RUN uv sync --frozen

ENV PYTHONPATH=/app/src

CMD ["uv","run","uvicorn","bridge_simulator.api.bridge_api:app","--host","0.0.0.0","--port","8001"]