"""Bootstrap de la aplicación FastAPI de Chorum.

Fase 0: solo se expone ``GET /health`` para que el contenedor arranque y el CI valide el
bootstrap del proceso. La lógica de negocio (motor de orquestación, API de grafos,
streaming, checkpoints, evals) se agrega en las fases siguientes bajo ``app/``.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Chorum API", version="0.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Liveness check: devuelve 200 mientras el proceso esté vivo."""
    return {"status": "ok"}
