# Arquitectura

> **Stub (Fase 0).** El diagrama completo de capas y el flujo de ejecución se documentan a
> medida que se implementan. Ver el resumen de arquitectura en el
> [README](../README.md#arquitectura-resumen) y las capas descritas en
> [CLAUDE.md](../CLAUDE.md).

## Capas (resumen)

1. Canvas visual (frontend)
2. Backend API (FastAPI + WebSocket)
3. Orquestador (LangGraph + checkpointing)
4. Capa de modelos (`ModelProvider`)
5. Capa de herramientas (tools + sandbox + logging de red)
6. `PolicyEngine` (modo air-gap)
7. Observabilidad (eventos por transición de nodo)
8. Evals (runner de casos de prueba)
