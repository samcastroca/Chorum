# Ejemplos

Grafos de ejemplo en JSON, listos para importar en el builder.

- [`linear_pipeline.json`](./linear_pipeline.json) — **(Fase 1)** pipeline lineal de 3
  agentes. Demo del motor de orquestación: se ejecuta con
  [`scripts/run_example.py`](../scripts/run_example.py) sin necesidad de API/UI ni modelos
  (los nodos usan placeholders deterministas por ahora).

> El set completo de ejemplos curados se arma en la **Fase 9**, incluyendo al menos uno
> configurado en modo air-gap (solo modelos locales) como demo funcional de esa feature.

Ejemplos previstos:

- Investigador + verificador con loop de corrección.
- Router de triage con agentes especialistas (modo air-gap, solo modelos locales).
- Pipeline de revisión de código con un nodo de código real.
