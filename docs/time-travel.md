# Time-travel debugging

> **Stub (Fase 0).** Se completa en la **Fase 4**. Documentará qué partes del estado de una
> ejecución son seguras de editar manualmente al reanudar desde un checkpoint, y cuáles no
> deberían exponerse como editables (metadata interna de LangGraph).

Depende del checkpointing de LangGraph habilitado desde la Fase 1. Una ejecución bifurcada
por time-travel nunca sobrescribe la original (invariante 8 de [CLAUDE.md](../CLAUDE.md)).
