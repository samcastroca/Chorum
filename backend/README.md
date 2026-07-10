# Chorum — Backend

Backend FastAPI y motor de orquestación multi-agente de Chorum.

> **Fase 0**: solo bootstrap (endpoint `/health`). La lógica de negocio llega en las fases
> siguientes del [plan de desarrollo](../PLAN_DESARROLLO.md).

## Requisitos

- Python 3.12
- [`uv`](https://docs.astral.sh/uv/) (gestor de paquetes/entorno)

## Comandos

```bash
uv sync                      # instalar dependencias (crea .venv)
uv run uvicorn app.main:app --reload   # servir en http://localhost:8000
uv run pytest                # tests
uv run ruff check .          # lint
uv run ruff format .         # formato
uv run mypy .                # type checking
```

Verificá el bootstrap: `curl http://localhost:8000/health` → `{"status":"ok"}`.

## Estructura

```
app/
  main.py     # bootstrap FastAPI (/health)
  config.py   # settings desde entorno (.env)
  core/       # motor de orquestación + checkpointing   (Fase 1)
  api/        # routers HTTP/WebSocket                    (Fase 2+)
  models/     # ModelProvider (Ollama/Anthropic/OpenAI)   (Fase 6)
  tools/      # tools + sandbox + logging de red          (Fase 7)
  policy/     # PolicyEngine (modo air-gap)               (Fase 8)
  evals/      # runner de evals                           (Fase 10)
  db/         # SQLModel + Alembic                        (Fase 2)
tests/
```
