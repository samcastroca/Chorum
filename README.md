# Chorum

> ⚠️ **Estado: en desarrollo temprano (Fase 0).** El proyecto está en construcción y aún
> no es funcional. Este README es inicial y se irá actualizando a medida que avance el
> [plan de desarrollo](PLAN_DESARROLLO.md).

**Chorum** (nombre provisional) es una plataforma **open source, low-code y self-hosted**
para construir sistemas multi-agente de IA relativamente complejos. Armás grafos de agentes
visualmente en un canvas drag-and-drop: cada agente puede usar un modelo local (Ollama) o
una API externa (Anthropic, OpenAI), tiene acceso a herramientas (búsqueda web, HTTP,
ejecución de código) y el sistema soporta patrones de orquestación con ciclos —
supervisor/router, pipeline, debate y grafos de estado generales.

## Por qué Chorum

El mercado de builders visuales de agentes (n8n, Langflow, Flowise, y las opciones cerradas
como OpenAI AgentKit o Vellum) ya está maduro. Chorum no intenta competir en cantidad de
integraciones ni en pulido general de UI: apuesta a **tres features concretas** que, al
diseñar el proyecto, no estaban bien resueltas en ninguna otra opción, abierta o cerrada.

### 🌟 Time-travel debugging
Pausá una ejecución en cualquier checkpoint, editá el estado y reanudá desde ahí — sin
re-ejecutar los pasos anteriores. Si un grafo de 6 pasos falla en el paso 5, no pagás de
nuevo los tokens de los pasos 1–4: congelás la ejecución, corregís y seguís desde el punto
exacto.

### 🌟 Modo air-gap verificable
No es solo "no configurar una API externa": es una garantía **activa y auditable** de que
una ejecución no tocó la red. Al terminar, obtenés un reporte de verificación generado a
partir del log real de la ejecución, que enumera cualquier intento de acceso a red
detectado (idealmente, ninguno). Pensado para quien trabaja con datos sensibles y necesita
prueba, no confianza.

### 🌟 Evals integrados al editor
Adjuntá casos de prueba a cada grafo y detectá regresiones al editar prompts o cambiar la
configuración de un nodo, sin salir del builder. Los criterios de éxito pueden ser
determinísticos o evaluados por un LLM "juez".

## Stack técnico

| Capa      | Tecnologías                                                                 |
|-----------|-----------------------------------------------------------------------------|
| Backend   | Python · FastAPI · LangGraph (checkpointing desde el core) · SQLModel · Alembic · `uv` · `ruff` · `mypy` |
| Frontend  | React · TypeScript · Vite · React Flow · Tailwind · Vitest + Testing Library |
| Infra     | Docker Compose · Ollama (servicio opcional para modelos locales)            |
| Licencia  | Apache 2.0                                                                   |

## Arquitectura (resumen)

De arriba hacia abajo:

1. **Canvas visual** — armado de grafos y navegación del historial para time-travel debugging.
2. **Backend API** (FastAPI + WebSocket) — CRUD de grafos, ejecución, streaming, checkpoints, evals.
3. **Orquestador** — compila la definición del grafo a un `StateGraph` de LangGraph con checkpointing persistente.
4. **Capa de modelos** — abstracción `ModelProvider` para Ollama y APIs externas.
5. **Capa de herramientas** — registro de tools tipadas, sandbox de código y logging auditable de red.
6. **PolicyEngine** — punto único de verificación de red; base del modo air-gap.
7. **Observabilidad** — cada transición de nodo emite eventos (WebSocket + persistidos).
8. **Evals** — runner de casos de prueba asociados a un grafo.

Documentación detallada (a medida que se construya) en [`/docs`](docs/).

## Estructura del repositorio

```
/backend      # FastAPI + motor de orquestación (core, models, tools, policy, evals, db)
/frontend     # React + React Flow (canvas, panels, history, api, store)
/docs         # arquitectura, esquema de grafo, time-travel, air-gap, seguridad
/examples     # grafos de ejemplo en JSON (incluido al menos uno en modo air-gap)
/scripts      # setup y scripts de desarrollo
CLAUDE.md     # contexto persistente para desarrollo asistido con Claude Code
PLAN_DESARROLLO.md  # hoja de ruta completa por fases
```

## Puesta en marcha

> El proyecto aún no arranca — estos comandos son la referencia hacia la que apunta el
> desarrollo y se validarán en las fases correspondientes del plan.

```bash
# Todo junto (desarrollo)
docker compose up

# Con modelos locales (Ollama)
docker compose --profile local-models up

# Backend
cd backend && uv sync
cd backend && uv run pytest

# Frontend
cd frontend && npm install
cd frontend && npm run dev
```

## Estado y hoja de ruta

El desarrollo está organizado en fases secuenciales descritas en
[PLAN_DESARROLLO.md](PLAN_DESARROLLO.md). Las tres features diferenciadoras (🌟) están
integradas en las fases donde técnicamente corresponden:

- **Fase 4** — Time-travel debugging
- **Fase 8** — Modo air-gap verificable
- **Fase 10** — Evals integrados al editor

Actualmente el repositorio está en la **Fase 0** (fundación: estructura, licencia,
convenciones y CI).

## Contribuir

Todavía no hay guía de contribución (`CONTRIBUTING.md` llega en la Fase 11). Mientras tanto,
si querés seguir el proyecto o proponer ideas, abrí un issue.

## Licencia

[Apache 2.0](LICENSE).
