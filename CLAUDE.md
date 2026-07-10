# CLAUDE.md

Este archivo da contexto persistente a Claude Code sobre el proyecto. Léelo por completo
antes de empezar cualquier tarea. Si tomas una decisión de arquitectura nueva durante el
desarrollo, actualiza este archivo en el mismo commit/PR — este documento debe reflejar
siempre el estado real del proyecto, no quedar desactualizado.

## Qué es este proyecto

Chorum (nombre provisional) es una plataforma **open source, low-code, self-hosted**
para construir agentes de IA multi-agente relativamente complejos. El usuario arma grafos
de agentes visualmente (canvas tipo drag-and-drop), cada agente puede usar un modelo local
(Ollama) o una API externa (Anthropic, OpenAI), tiene acceso a herramientas (web search,
HTTP, ejecución de código), y el sistema soporta patrones de orquestación con ciclos
(supervisor/router, pipeline, debate, grafos de estado generales).

### Lo que diferencia a este proyecto (no perder de vista esto)

El mercado de builders visuales de agentes (n8n, Langflow, Flowise, y las opciones cerradas
como OpenAI AgentKit o Vellum) ya está maduro y bien financiado. Este proyecto no compite en
lista de integraciones ni en pulido de UI general — compite en tres features concretas que,
al momento de diseñar este documento, no existen (bien resueltas) en ninguna otra opción,
abierta o cerrada:

1. **Time-travel debugging**: pausar una ejecución en cualquier checkpoint, editar el
   estado, y reanudar desde ahí sin re-ejecutar los pasos anteriores. Depende de que el
   checkpointing de LangGraph esté bien diseñado desde el core (ver `/backend/app/core/`).
2. **Modo air-gap verificable**: garantía activa y auditable (no solo "no configuraste una
   API externa") de que una ejecución no tocó la red. Depende del `PolicyEngine` en
   `/backend/app/policy/`.
3. **Evals integrados al editor**: casos de prueba adjuntos a cada grafo que detectan
   regresiones al editar prompts, sin salir del builder. Depende del runner en
   `/backend/app/evals/`.

Cualquier decisión de diseño que dificulte estas tres features debe cuestionarse
explícitamente antes de proceder — son la razón de ser del proyecto, no features más.

## Stack técnico

- **Backend**: Python, FastAPI, LangGraph como motor de orquestación (con checkpointing
  habilitado desde el core, no opcional), SQLModel + Alembic para persistencia (SQLite en
  desarrollo, Postgres-compatible), `uv` como gestor de paquetes, `ruff` para lint/format,
  `mypy` para type checking.
- **Frontend**: React + TypeScript, Vite, React Flow para el canvas, Tailwind para estilos,
  Vitest + Testing Library para tests.
- **Infra**: Docker Compose para desarrollo y distribución, Ollama como servicio opcional
  para modelos locales.
- **Licencia**: Apache 2.0.

## Arquitectura (capas, de arriba hacia abajo)

1. **Canvas visual** (frontend) — el usuario arma el grafo arrastrando nodos, y también
   navega el historial de ejecuciones para hacer time-travel debugging.
2. **Backend API** (FastAPI + WebSocket) — CRUD de grafos, ejecución, streaming de eventos,
   endpoints de checkpoints/time-travel, endpoints de evals.
3. **Orquestador** (motor propio sobre LangGraph) — compila la definición de grafo del
   usuario a un `StateGraph` ejecutable, con checkpointing persistente por `thread_id`.
4. **Capa de modelos** — abstracción `ModelProvider` con implementaciones para Ollama
   (local) y APIs externas, seleccionable por agente. Punto de verificación obligatorio
   del `PolicyEngine` antes de cualquier llamada externa.
5. **Capa de herramientas** — registro de tools con schema tipado, sandbox de ejecución de
   código Python, y logging auditable centralizado de todo intento de acceso a red (usado
   tanto para debugging normal como para los reportes del modo air-gap).
6. **PolicyEngine** — punto único de verificación invocado desde la capa de modelos y la
   capa de herramientas antes de cualquier operación de red. Es lo que hace el modo
   air-gap una garantía verificable y no una simple opción de configuración.
7. **Observabilidad** — cada transición de nodo emite eventos (WebSocket en vivo +
   persistidos en DB) para reconstruir la traza de cualquier ejecución.
8. **Evals** — runner que ejecuta casos de prueba asociados a un grafo, reutilizando
   `ModelProvider` cuando el criterio de éxito requiere un LLM "juez".

Ver `/docs/architecture.md` para el diagrama completo, `/docs/graph-schema.md` para el
esquema de datos del grafo, `/docs/time-travel.md`, `/docs/airgap-mode.md`, y
`/docs/security.md` para el detalle de cada feature diferenciadora.

## Estructura de carpetas

```
/backend
  /app
    /core       # motor de orquestación, esquema de grafo, compilación a LangGraph,
                # checkpointing (base de time-travel debugging)
    /api        # routers de FastAPI, incluyendo endpoints de checkpoints/resume y evals
    /models     # ModelProvider y sus implementaciones (ollama, anthropic, openai)
    /tools      # registro de herramientas + sandbox de código + logging auditable de red
    /policy     # PolicyEngine — punto único de verificación para el modo air-gap
    /evals      # EvalCase, runner de evaluaciones, integración con ModelProvider como juez
    /db         # modelos SQLModel, migraciones Alembic
  /tests
/frontend
  /src
    /canvas     # React Flow, nodos custom
    /panels     # formularios de configuración por tipo de nodo, panel de evals
    /history    # vista de historial de ejecuciones y time-travel debugging
    /api        # cliente HTTP/WebSocket hacia el backend
    /store      # estado global (Zustand o similar — decidir en Fase 5)
  /tests
/docs
/examples         # grafos de ejemplo en JSON (al menos uno configurado en modo air-gap)
/scripts
PLAN_DESARROLLO.md
```

## Convenciones de código

### Python (backend)
- Type hints obligatorios en funciones públicas. `mypy` debe pasar sin errores.
- Modelos de datos con Pydantic v2 (para schemas de API) y SQLModel (para modelos de DB).
- Formato y lint con `ruff` — correr `ruff format` antes de cada commit.
- Async por defecto en endpoints de FastAPI y en cualquier código que llame a APIs de
  modelos externos (I/O bound).
- Nunca loguear API keys, tokens, ni contenido completo de prompts/respuestas de usuario
  en logs de nivel INFO o superior.
- Tests con `pytest`, fixtures compartidas en `conftest.py`. Cada módulo nuevo en `/core`,
  `/models`, `/tools`, `/policy`, o `/evals` necesita tests — no es opcional. Los módulos
  `/policy` y `/tools` (sandbox) requieren cobertura especialmente alta por ser las piezas
  de seguridad del proyecto.

### TypeScript / React (frontend)
- Componentes funcionales con hooks, no class components.
- Props tipadas explícitamente (no `any`).
- Un componente por archivo, nombre de archivo = nombre de componente.
- Estilos con Tailwind, evitar CSS-in-JS o archivos `.css` sueltos salvo casos justificados.
- Tests de componentes con Testing Library, enfocados en comportamiento del usuario.

### Git
- Ramas: `feature/fase-N-descripcion-corta` o `fix/descripcion-corta`.
- Commits pequeños y descriptivos.
- No mezclar cambios de múltiples fases/features en un mismo commit.

## Invariantes de arquitectura (no romper sin discutirlo explícitamente)

Estas son decisiones de diseño deliberadas. Si una tarea parece requerir romper alguna,
detente y pregunta antes de proceder.

1. **El `GraphDefinition` es la única fuente de verdad** sobre qué puede ejecutar el
   sistema. El canvas visual serializa/deserializa contra este esquema.
2. **Todo acceso a modelos pasa por la interfaz `ModelProvider`**. Ningún código de
   negocio llama directo al SDK de Anthropic/OpenAI o a la API HTTP de Ollama.
3. **El nodo de código (`code`) SIEMPRE ejecuta en el sandbox aislado**, nunca en el
   proceso principal del backend.
4. **Cada ejecución de grafo debe ser observable**: cualquier cambio a la lógica de
   ejecución debe seguir emitiendo eventos compatibles con el formato de Fase 3.
5. **API keys y secrets nunca se guardan en la base de datos de grafos** — solo
   referencias a variables de entorno o a un gestor de secrets. El `GraphDefinition` de un
   agente referencia un `provider_id`, nunca una key en texto plano.
6. **El checkpointing de LangGraph no es opcional ni se puede deshabilitar por
   conveniencia** — toda la feature de time-travel debugging depende de que cada paso de
   ejecución quede persistido de forma recuperable. Si una optimización de performance
   sugiere deshabilitar checkpoints, la respuesta correcta es optimizar el checkpointer,
   no quitarlo.
7. **Ninguna llamada de red (desde `ModelProvider`, herramientas HTTP, o el sandbox de
   código) puede evitar pasar por el `PolicyEngine`**. Si se agrega un nuevo tipo de nodo
   o herramienta que hace I/O de red, su integración con el `PolicyEngine` es parte
   obligatoria de esa tarea, no un follow-up.
8. **Una ejecución bifurcada por time-travel (`resume` desde un checkpoint) nunca
   sobrescribe la ejecución original** — siempre crea una nueva ejecución/thread_id
   derivado, preservando la traza previa intacta.
9. **El reporte de verificación del modo air-gap debe ser generado a partir del log
   auditable real de la ejecución**, nunca inferido o simulado — si el log no capturó
   algo, el reporte debe poder reflejar esa incertidumbre en vez de asumir que no pasó
   nada.

## Cómo agregar cosas nuevas (recetas)

**Nuevo tipo de nodo**: agregar el tipo en el enum de `NodeType` (core), implementar su
lógica de compilación a LangGraph, agregar el componente custom de React Flow, agregar su
formulario de configuración en `/frontend/src/panels`. Si el nodo hace I/O de red,
integrarlo con el `PolicyEngine` desde el mismo PR. Actualizar `/docs/graph-schema.md`.

**Nuevo proveedor de modelo**: implementar la interfaz `ModelProvider` en
`/backend/app/models/`, registrarlo en el factory de providers, agregar sus variables de
entorno esperadas a `.env.example`, actualizar el endpoint `/providers`, asegurar que sus
llamadas pasen por el `PolicyEngine`.

**Nueva herramienta built-in**: definir su schema en `/backend/app/tools/`, registrarla en
el tool registry, agregar tests verificando su comportamiento y sus límites. Si hace
llamadas de red, integrarla con el logging auditable y el `PolicyEngine`.

**Nuevo tipo de criterio de eval**: extender `EvalCase` en `/backend/app/evals/`,
implementar su lógica de evaluación en el runner, agregar tests con casos que deberían
pasar y casos que deberían fallar (para verificar que el criterio realmente discrimina).

## Comandos útiles

```bash
# Backend
cd backend && uv sync                    # instalar dependencias
cd backend && uv run pytest              # correr tests
cd backend && uv run ruff check --fix .  # lint + autofix
cd backend && uv run alembic upgrade head  # aplicar migraciones

# Frontend
cd frontend && npm install
cd frontend && npm run dev
cd frontend && npm run test
cd frontend && npm run lint

# Todo junto (desarrollo)
docker compose up

# Con modelos locales
docker compose --profile local-models up
```

## Qué NO hacer

- No agregues dependencias nuevas sin que estén justificadas por la tarea actual —
  mantener el proyecto liviano de instalar es un objetivo explícito.
- No implementes autenticación/multi-usuario todavía — fuera de alcance hasta que se
  decida explícitamente (ver Fase 13 del plan de desarrollo).
- No relajes las restricciones del sandbox de código "para que sea más fácil probar" —
  si el sandbox estorba en desarrollo, la solución es mejorar el sandbox, no debilitarlo.
- No agregues una ruta de red nueva (nuevo proveedor, nueva herramienta, nueva integración)
  sin pasarla por el `PolicyEngine` — esto rompería silenciosamente la garantía del modo
  air-gap para cualquier usuario que lo esté usando.
- No deshabilites ni "simplifiques" el checkpointing de LangGraph para ganar performance —
  rompería time-travel debugging de forma silenciosa (el grafo seguiría funcionando, solo
  dejaría de ser posible bifurcar ejecuciones pasadas, y probablemente nadie lo notaría
  hasta que alguien lo necesite).
- No mergees a `main` sin que CI esté en verde.
