"""Bootstrap de la aplicación FastAPI de Chorum.

Expone ``GET /health`` (liveness) y, desde la Fase 2, la API de grafos y ejecuciones bajo
``app/api/routes/``. El checkpointer de LangGraph se crea una sola vez en el ``lifespan`` y se
comparte entre requests (invariante 6): no hay ruta de ejecución sin checkpointing.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import executions, graphs
from app.config import get_settings
from app.core import close_checkpointer, create_checkpointer

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Crea el checkpointer al arrancar y lo cierra al apagar.

    Se cierra en el ``finally`` para liberar la conexión aiosqlite (su thread no-daemon
    bloquearía el exit del proceso si quedara abierto).
    """
    app.state.checkpointer = await create_checkpointer(settings.checkpointer_db_path)
    try:
        yield
    finally:
        await close_checkpointer(app.state.checkpointer)


app = FastAPI(title="Chorum API", version="0.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graphs.router)
app.include_router(executions.router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness check: devuelve 200 mientras el proceso esté vivo."""
    return {"status": "ok"}
