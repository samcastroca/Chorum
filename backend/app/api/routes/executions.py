"""Endpoint REST de ejecuciones: recuperación del historial (Fase 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from app.api.deps import get_session
from app.api.schemas import ExecutionRead
from app.db.models import Execution

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/{execution_id}", response_model=ExecutionRead)
async def get_execution(execution_id: int, session: Session = Depends(get_session)) -> Execution:
    """Devuelve una ejecución por id, o 404 si no existe."""
    execution = session.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Ejecución no encontrada."
        )
    return execution
