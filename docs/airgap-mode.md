# Modo air-gap verificable

> **Stub (Fase 0).** Se completa en la **Fase 8**. Documentará con total honestidad qué
> garantiza este modo (ausencia de tráfico de red durante la ejecución) y qué **no**
> garantiza (por ejemplo, no valida la procedencia ni la confiabilidad del modelo local en sí).

El reporte de verificación se genera a partir del log auditable real de la ejecución, nunca
inferido ni simulado (invariante 9 de [CLAUDE.md](../CLAUDE.md)). Toda llamada de red pasa
por el `PolicyEngine` (invariante 7).
