# Plan de desarrollo — Plataforma low-code multi-agente (nombre provisional: Chorum)

> Hoja de ruta completa del proyecto, dividida en fases secuenciales, pensada para ejecutarse
> principalmente con Claude Code. Cada fase incluye objetivo, entregables, tareas detalladas,
> criterios de aceptación y un prompt inicial sugerido.
>
> **Cambio respecto a la versión anterior de este plan**: se integraron tres features
> diferenciadoras (marcadas con 🌟) directamente en las fases donde técnicamente corresponden,
> en vez de dejarlas como añadidos al final. Esto implicó renumerar algunas fases e insertar
> tres nuevas: **Fase 4 (time-travel debugging)**, **Fase 8 (modo air-gap verificable)**, y
> **Fase 10 (evals integrados al editor)**. Si ya empezaste a trabajar con la numeración
> anterior, usa este documento como la versión vigente.
>
> Recomendación de flujo de trabajo: una fase = una rama (`feature/fase-N-nombre`) = una o varias
> sesiones de Claude Code = un PR. No saltes de fase sin haber cerrado los criterios de
> aceptación anteriores — esto importa especialmente ahora porque las fases 🌟 dependen
> directamente de decisiones de diseño tomadas en fases previas.

---

## Fase 0 — Fundación del repositorio

**Objetivo**: esqueleto del monorepo, licencia, CI mínimo y convenciones antes de escribir lógica de negocio.

### Entregables
- Estructura de carpetas del monorepo
- Licencia Apache 2.0
- `CLAUDE.md` en la raíz
- CI básico (lint + build)
- `.env.example`
- `docker-compose.yml` esqueleto

### Tareas
1. Crear estructura de monorepo:
   ```
   /backend        (Python, FastAPI)
   /frontend       (React + TypeScript + Vite)
   /docs           (documentación de usuario y arquitectura)
   /examples       (grafos de ejemplo)
   /scripts        (setup.sh, dev scripts)
   /.github/workflows
   CLAUDE.md
   README.md
   LICENSE
   docker-compose.yml
   .env.example
   ```
2. Backend: `uv`, `pyproject.toml`, `ruff`, `mypy`.
3. Frontend: Vite + React + TypeScript, ESLint + Prettier, Tailwind.
4. Pre-commit hooks (ruff, prettier).
5. `README.md` inicial.
6. GitHub Actions: lint en cada PR.
7. `LICENSE` (Apache 2.0).

### Criterios de aceptación
- `docker compose up` no falla.
- CI en verde en un PR de prueba.
- `CLAUDE.md` presente y completo.

### Prompt sugerido para Claude Code
```
Estoy iniciando un proyecto open source: una plataforma low-code para construir agentes de IA
multi-agente, con backend en Python/FastAPI y frontend en React/TypeScript, orquestación con
LangGraph, y soporte híbrido de modelos locales (Ollama) y APIs externas.

Quiero que generes la estructura inicial de un monorepo con:
- /backend (FastAPI, gestionado con uv, ruff para lint/format, mypy para type checking)
- /frontend (Vite + React + TypeScript, ESLint + Prettier, Tailwind)
- /docs, /examples, /scripts, /.github/workflows

Configura pre-commit hooks para lint automático, un workflow de GitHub Actions que corra lint
en ambos proyectos, y un docker-compose.yml esqueleto con servicios backend/frontend/db (vacíos
por ahora). Usa licencia Apache 2.0.

No implementes lógica de negocio todavía. Antes de escribir código, muéstrame el plan de
archivos que vas a crear.
```

---

## Fase 1 — Motor de orquestación (core, sin UI)

**Objetivo**: el corazón del sistema funcionando por API/CLI. La decisión de diseño más cara
de revertir de todo el proyecto vive aquí — y ahora incluye un requisito nuevo: el estado
debe ser **checkpointeable y editable en cualquier punto**, porque de eso depende la Fase 4
(time-travel debugging). No se puede añadir esto después sin rediseñar el core.

### Entregables
- Esquema de datos para representar un grafo de agentes (Pydantic models)
- Integración con LangGraph como motor de ejecución, **con checkpointing habilitado desde el diseño inicial**
- Endpoint mínimo para ejecutar un grafo definido en JSON
- Suite de tests unitarios del motor

### Tareas
1. **Diseñar el esquema del grafo**:
   - `AgentNode`: id, tipo (`agent`, `tool`, `condition`, `code`, `human_in_loop`, `start`, `end`), config específica del tipo
   - Nodos `agent`: prompt de sistema, referencia a proveedor de modelo, herramientas permitidas, política de memoria
   - `Edge`: origen, destino, condición opcional
   - `GraphDefinition`: nodos + edges + esquema del estado compartido
2. Implementar `compile_graph(definition) -> CompiledGraph` que traduce el esquema propio a un `StateGraph` de LangGraph.
3. **Configurar un checkpointer de LangGraph (ej. `SqliteSaver` en desarrollo) desde el día uno**, no como mejora futura — cada paso de ejecución debe quedar persistido con su `thread_id` y su estado completo, de forma que sea recuperable y editable más adelante.
4. Implementar ejecución básica: dado un `GraphDefinition` e input inicial, correr el grafo y devolver el estado final.
5. Manejo de errores: reintentos, propagación, nodo de fallback.
6. Tests: pipeline lineal, grafo con condición, grafo con ciclo (verificar límite de iteraciones) — y un test adicional que verifique que, dado un `thread_id` de una ejecución pasada, se puede recuperar el estado exacto en cada checkpoint.
7. Documentar el esquema del grafo en `/docs/graph-schema.md`.

### Criterios de aceptación
- Un grafo de 3 agentes en JSON se ejecuta correctamente desde un script o test.
- Un grafo con ciclo respeta el límite de iteraciones configurado.
- Dado el `thread_id` de una ejecución ya terminada, puedes recuperar el estado del sistema tal como estaba en cualquiera de sus pasos intermedios (esto es lo que habilita la Fase 4).
- Cobertura de tests del módulo core > 80%.

### Prompt sugerido para Claude Code
```
Vamos a implementar el motor de orquestación core del proyecto, sin API ni UI todavía —
solo la lógica de negocio en /backend/app/core/.

Necesito que diseñes con Pydantic el esquema de datos para representar un grafo de agentes:
- GraphDefinition: nodos + edges + esquema del estado compartido
- Tipos de nodo: agent, tool, condition, code, human_in_loop, start, end
- Edges pueden tener una condición opcional evaluada contra el estado

Luego implementa una función que compile este esquema propio a un StateGraph de LangGraph,
y una función de ejecución que corra el grafo dado un input inicial.

REQUISITO IMPORTANTE: configura un checkpointer de LangGraph (SqliteSaver para desarrollo)
desde el inicio, no como algo a agregar después. Cada paso de ejecución debe quedar
persistido con su thread_id de forma que, dado ese thread_id, se pueda recuperar el estado
exacto del sistema en cualquier checkpoint intermedio, no solo el estado final. Esto es
un requisito de arquitectura, no opcional — habilita una feature de debugging que
construiremos en una fase posterior.

Antes de escribir código: muéstrame el diseño propuesto del esquema Pydantic completo y
explícame cómo vas a exponer la recuperación de checkpoints intermedios. Quiero validar
esto antes de que implementes la ejecución.

Después de mi aprobación, implementa con tests unitarios cubriendo: pipeline lineal,
grafo con condición, grafo con ciclo, y recuperación de estado desde un checkpoint
intermedio de una ejecución ya terminada.
```

---

## Fase 2 — Backend API y persistencia

**Objetivo**: exponer el motor vía HTTP, y poder guardar/cargar grafos.

### Entregables
- Endpoints REST: CRUD de grafos, endpoint de ejecución
- Modelo de base de datos (SQLite para MVP, migrable a Postgres)
- Migraciones (Alembic)

### Tareas
1. Modelos de DB (SQLModel): `graphs` (definición serializada, versión, metadata), `executions` (historial, estado final, timestamps, `thread_id` de LangGraph para poder cruzar con los checkpoints de la Fase 1).
2. Endpoints: `POST/GET/PUT /graphs`, `POST /graphs/{id}/execute`, `GET /executions/{id}`.
3. Validación de la definición del grafo al guardar contra el schema de Fase 1.
4. Alembic desde el día uno.
5. Tests de integración de los endpoints.

### Criterios de aceptación
- Puedes crear un grafo vía API, ejecutarlo, y recuperar el historial de ejecución.
- Migraciones corren limpio desde cero.

### Prompt sugerido para Claude Code
```
Ahora vamos a exponer el motor de orquestación (ya implementado en /backend/app/core/) vía
API REST con FastAPI, y agregar persistencia.

Necesito:
1. Modelos de base de datos con SQLModel para `graphs` (definición del grafo serializada,
   versión, nombre, timestamps) y `executions` (referencia al grafo, thread_id de LangGraph,
   estado final, status, timestamps).
2. Configura Alembic para migraciones.
3. Implementa los endpoints: POST/GET/PUT /graphs, POST /graphs/{id}/execute, GET /executions/{id}.
4. Al guardar un grafo, valida la definición contra el schema de Fase 1 y devuelve errores
   claros (400) si es inválido.
5. Tests de integración con TestClient cubriendo el flujo completo.

Asegúrate de que el thread_id de LangGraph quede almacenado y asociado a la ejecución —
lo necesitaremos en una fase posterior para recuperar checkpoints intermedios.
```

---

## Fase 3 — Streaming y observabilidad

**Objetivo**: ver la ejecución en tiempo real, no solo el resultado final.

### Entregables
- WebSocket que emite eventos de ejecución en vivo
- Almacenamiento de trazas
- Endpoint para consultar la traza completa de una ejecución pasada

### Tareas
1. Usar `astream_events` de LangGraph para capturar eventos nodo por nodo.
2. Endpoint WebSocket `/ws/executions/{id}` que reenvía eventos al cliente.
3. Formato de evento: tipo (`node_start`, `node_end`, `node_error`, `state_update`), payload, timestamp.
4. Persistir cada evento en `execution_events`.
5. Endpoint `GET /executions/{id}/trace`.
6. Tests: verificar orden y contenido de eventos.

### Criterios de aceptación
- Conectado al WebSocket, ves en tiempo real qué nodo se está ejecutando.
- Puedes reconstruir la traza completa desde la DB, aunque ya no esté corriendo.

### Prompt sugerido para Claude Code
```
Vamos a agregar observabilidad en tiempo real a la ejecución de grafos.

Necesito:
1. Modificar la ejecución del grafo para usar astream_events de LangGraph, capturando
   eventos por nodo (inicio, fin, error, actualización de estado).
2. Un endpoint WebSocket /ws/executions/{id} que reenvía estos eventos en tiempo real.
3. Persistir cada evento en una tabla execution_events para reconstruir la traza después.
4. Un endpoint GET /executions/{id}/trace que devuelve la secuencia completa de eventos.

Diseña primero el formato del evento (JSON) que se va a emitir tanto por WebSocket como
almacenado en DB — deben ser el mismo formato. Muéstrame ese diseño antes de implementar.
```

---

## 🌟 Fase 4 — Time-travel debugging

**Objetivo**: esta es una de las tres features que diferencian el proyecto de todo lo demás
en el mercado (abierto o cerrado). Aprovecha el checkpointing de LangGraph configurado en
la Fase 1 para permitir pausar una ejecución en cualquier nodo, inspeccionar o editar el
estado, y reanudar desde ahí — sin reiniciar todo el grafo desde cero.

### Por qué importa (contexto de negocio, no solo técnico)
En un grafo de 6 pasos que falla en el paso 5, la alternativa sin esto es "corregir el
prompt y volver a ejecutar todo el grafo", pagando de nuevo el costo en tokens y tiempo de
los pasos 1 a 4. Con time-travel, congelas la ejecución en el paso 4, editas el estado o la
config del nodo 5, y reanudas solo desde ahí.

### Entregables
- Endpoint para listar los checkpoints disponibles de una ejecución (thread_id)
- Endpoint para obtener el estado completo en un checkpoint específico
- Endpoint para "bifurcar" una ejecución: tomar el estado de un checkpoint, aplicarle una
  edición manual, y reanudar la ejecución del grafo desde ahí como una nueva ejecución
  (sin perder la traza original)
- UI en el canvas: en la vista de "historial de ejecución", poder seleccionar cualquier
  nodo pasado, ver/editar el estado en ese punto, y lanzar una reanudación desde ahí

### Tareas
1. Backend: `GET /executions/{id}/checkpoints` — lista los checkpoints (nodo, timestamp, resumen del estado) de un `thread_id` dado.
2. Backend: `GET /executions/{id}/checkpoints/{checkpoint_id}` — estado completo serializado en ese punto.
3. Backend: `POST /executions/{id}/checkpoints/{checkpoint_id}/resume` — recibe una edición opcional del estado, crea un nuevo `thread_id` derivado del checkpoint elegido, y reanuda la ejecución del grafo desde ese punto usando el mecanismo de checkpoint restoration de LangGraph.
4. Definir claramente qué partes del estado son editables de forma segura (ej. el output textual de un nodo) vs. cuáles no deberían editarse a mano (ej. metadata interna de LangGraph) — documentar esto explícitamente.
5. Frontend: en la vista de historial/traza de una ejecución, cada nodo pasado debe ser clickeable, mostrando su estado en un panel editable, con un botón "reanudar desde aquí".
6. Frontend: dejar claro visualmente que una ejecución "bifurcada" es una rama nueva relacionada con la original, no la misma ejecución sobrescrita (para no confundir al usuario sobre qué pasó con los datos anteriores).
7. Tests: ejecutar un grafo de al menos 4 nodos, forzar un fallo a propósito en el nodo 3, bifurcar desde el checkpoint del nodo 2 con una corrección, y verificar que la ejecución bifurcada llega a un resultado correcto sin re-ejecutar los nodos 1 y 2.

### Criterios de aceptación
- Puedes ver todos los checkpoints intermedios de una ejecución pasada.
- Puedes editar el estado en un checkpoint específico y reanudar la ejecución solo desde ahí, verificable porque los nodos anteriores no se vuelven a ejecutar (y por lo tanto no generan nuevas llamadas a modelos, medible en el contador de tokens/costo).
- La UI distingue claramente la ejecución original de la bifurcada.

### Prompt sugerido para Claude Code
```
Vamos a implementar la feature de "time-travel debugging" — es una de las características
diferenciadoras principales del proyecto, así que quiero que la implementación sea sólida,
no un prototipo.

El motor ya tiene checkpointing de LangGraph habilitado desde la Fase 1. Necesito:

1. GET /executions/{id}/checkpoints — lista los checkpoints disponibles de una ejecución
   (nodo asociado, timestamp, resumen breve del estado en ese punto).
2. GET /executions/{id}/checkpoints/{checkpoint_id} — estado completo serializado en ese
   checkpoint específico.
3. POST /executions/{id}/checkpoints/{checkpoint_id}/resume — recibe una edición opcional
   del estado (JSON parcial a mergear), y reanuda la ejecución del grafo desde ese
   checkpoint como una NUEVA ejecución (nuevo thread_id derivado), sin perder ni sobrescribir
   la traza de la ejecución original.

Antes de implementar: explícame qué partes del estado interno de LangGraph son seguras de
editar manualmente desde afuera y cuáles no deberían exponerse como editables — necesito
entender los límites de esto antes de construir la UI encima. Documenta esto en
/docs/time-travel.md.

Después de mi aprobación, implementa con un test que: ejecute un grafo de 4+ nodos, fuerce
un fallo en el nodo 3, bifurque desde el checkpoint del nodo 2 con una corrección al estado,
y verifique que la ejecución bifurcada NO vuelve a ejecutar los nodos 1 y 2 (puedes
verificarlo con un contador de invocaciones mockeado en los nodos).
```

> **Nota**: no conviertas esto en la primera cosa que construyes — depende de que la Fase 1
> haya sentado bien las bases de checkpointing y de que la Fase 3 (streaming) ya te dé una
> vista de traza sobre la cual construir la interacción de "click en un nodo pasado".

---

## Fase 5 — Canvas visual (frontend)

**Objetivo**: el builder low-code real.

### Entregables
- Canvas interactivo con React Flow
- Paneles de configuración por tipo de nodo
- Guardado/carga de grafos contra el backend
- Vista de ejecución en vivo (nodos que se iluminan según el WebSocket de Fase 3)
- Vista de historial con soporte para time-travel (Fase 4)

### Tareas
1. Setup de React Flow, nodos custom por tipo (`agent`, `tool`, `condition`, `code`, `human_in_loop`).
2. Panel lateral de configuración específico por tipo de nodo (selectores de modelo/herramientas con mocks hasta fases 6 y 7).
3. Serialización canvas ↔ `GraphDefinition`.
4. Conexión al WebSocket de ejecución: resaltar nodo activo, error, completado.
5. Vista de historial de ejecuciones con la interacción de time-travel de la Fase 4 (seleccionar checkpoint, editar, reanudar).
6. Toolbar: guardar, ejecutar, ver historial.
7. Tests de componentes (Vitest + Testing Library).

### Criterios de aceptación
- Puedes armar un grafo de 3 nodos desde la UI, guardarlo, y volver a cargarlo sin perder información.
- Al ejecutar, ves el flujo iluminándose nodo por nodo en tiempo real.
- Puedes hacer time-travel desde la UI sobre una ejecución pasada.

### Prompt sugerido para Claude Code
```
Vamos a construir el canvas visual del builder usando React Flow, en /frontend/src/.

Necesito:
1. Nodos custom para: agent, tool, condition, code, human_in_loop, cada uno con estilo
   visual distintivo.
2. Panel lateral de configuración específico según el tipo de nodo seleccionado (selectores
   de modelo/herramientas con datos mock por ahora).
3. Serialización canvas -> GraphDefinition y viceversa.
4. Integración con el WebSocket de ejecución: nodo activo resaltado, con estados
   "corriendo", "completado", "error".
5. Una vista de historial de ejecuciones que permita seleccionar cualquier checkpoint de
   una ejecución pasada (usando los endpoints de la Fase 4), ver/editar su estado, y
   reanudar desde ahí.
6. Toolbar con guardar, ejecutar, e historial.

Antes de implementar, muéstrame un boceto de los nodos custom y de cómo se vería la
interacción de time-travel en la vista de historial, para validar la dirección antes de
que escribas el código.
```

---

## Fase 6 — Capa de modelos (híbrida local/API)

**Objetivo**: que cada agente pueda usar Ollama local o una API externa, configurable por nodo.

### Entregables
- Interfaz `ModelProvider` común
- Implementaciones: `OllamaProvider`, `AnthropicProvider`, `OpenAIProvider`
- UI para configurar proveedor/modelo por agente
- Servicio Ollama en `docker-compose.yml` (perfil opcional)

### Tareas
1. Definir interfaz `ModelProvider` (método común de generación con soporte de tool calling).
2. Implementar providers para Ollama, Anthropic, OpenAI. API keys por variables de entorno.
3. Endpoint `GET /providers`.
4. UI: selector de proveedor + modelo, reemplazando el mock de Fase 5.
5. Manejo de errores claro por proveedor.
6. Agregar servicio `ollama` a `docker-compose.yml` como perfil opcional.

### Criterios de aceptación
- Dos agentes en el mismo grafo, uno local y otro con API externa, ejecutan correctamente.
- Errores de configuración son claros y accionables.

### Prompt sugerido para Claude Code
```
Vamos a implementar la capa de modelos híbrida (local + API) en /backend/app/models/.

Necesito:
1. Una interfaz ModelProvider con un método común de generación, incluyendo tool calling.
2. Implementaciones: OllamaProvider, AnthropicProvider, OpenAIProvider. API keys desde
   variables de entorno, nunca hardcodeadas ni logueadas.
3. Un endpoint GET /providers que devuelve qué proveedores están disponibles según la
   configuración del entorno, y para Ollama, qué modelos están descargados localmente.
4. Manejo de errores específico y claro por proveedor.
5. Actualiza docker-compose.yml agregando ollama como perfil opcional.

Después, actualiza el panel de configuración de nodos agent en el frontend para usar el
endpoint /providers real en vez del mock.
```

---

## Fase 7 — Capa de herramientas y sandbox de código

**Objetivo**: que los agentes puedan actuar en el mundo real.

### Entregables
- Sistema de registro de herramientas con schema tipado
- Herramientas built-in: búsqueda web, HTTP request, lectura de archivos restringida
- Nodo de código Python con sandbox
- UI para seleccionar herramientas por agente

### Tareas
1. Schema de herramienta (nombre, descripción, JSON Schema de parámetros).
2. Herramientas built-in: HTTP request, búsqueda web, lectura de archivo restringida a directorio permitido.
3. Sandbox para el nodo de código: subprocess con timeout, sin acceso a red por defecto, sin acceso a filesystem fuera de un directorio temporal aislado por ejecución.
4. **Instrumentar el sandbox y todo el sistema de herramientas para que cada intento de acceso a red quede registrado de forma auditable** (qué nodo, qué destino, si fue permitido o bloqueado) — esto es un requisito nuevo que prepara el terreno para la Fase 8 (air-gap verificable): no basta con bloquear, hay que poder demostrar qué se bloqueó y qué no.
5. UI: checklist de herramientas en nodos `agent`; editor de código embebido en nodos `code`.
6. Tests de seguridad del sandbox.

### Criterios de aceptación
- Un agente puede llamar a una herramienta real y el resultado influye en su siguiente paso.
- Un nodo de código que intenta hacer algo prohibido falla de forma controlada.
- Cada intento de acceso a red (permitido o bloqueado) queda en un log auditable, consultable después.

### Prompt sugerido para Claude Code
```
Vamos a implementar el sistema de herramientas (tools) y el sandbox de ejecución de código
en /backend/app/tools/.

Necesito:
1. Un schema para definir herramientas (nombre, descripción, JSON Schema de parámetros).
2. Herramientas built-in: HTTP request genérico, búsqueda web, lectura de archivo
   restringida a un directorio permitido.
3. Para el nodo "code": sandbox basado en subprocess con timeout configurable, sin acceso
   a red por defecto, sin acceso a filesystem fuera de un directorio temporal aislado.
4. IMPORTANTE: instrumenta todo intento de acceso a red (desde el sandbox Y desde las
   herramientas built-in tipo HTTP request) para que quede registrado en un log auditable:
   qué nodo lo originó, a qué destino, timestamp, y si fue permitido o bloqueado. Esto lo
   vamos a usar en una fase posterior para un "modo air-gap verificable" — necesito que el
   mecanismo de logging quede centralizado en un solo punto (no repetido por cada
   herramienta) para poder construir la política de enforcement encima después.

Antes de implementar el sandbox, dame un análisis explícito de qué garantías de seguridad
ofrece este approach y cuáles no, documentado en /docs/security.md.

Incluye tests que verifiquen bloqueo de: acceso a red no autorizado, acceso a filesystem
fuera del directorio permitido, y timeout excedido — y que verifiquen que cada intento
bloqueado efectivamente aparece en el log auditable.
```

---

## 🌟 Fase 8 — Modo air-gap verificable

**Objetivo**: la segunda feature diferenciadora. No es una opción de configuración pasiva
("puedes usar modelos locales si quieres"), sino una **política de enforcement activa y
auditable**: cuando el modo air-gap está activo, la plataforma garantiza — y puede demostrar
con evidencia — que ninguna ejecución tocó la red.

### Por qué importa
Cualquier herramienta permite "no configurar" una API externa. Ninguna herramienta del
mercado (investigado en la conversación previa) ofrece una garantía verificable de que un
grafo completo, incluyendo todos sus nodos y herramientas, no hizo ninguna llamada de red
durante una ejecución específica. Esto es lo que le importa a un usuario con datos
sensibles: no "confía en que no lo hicimos", sino "aquí está la prueba de que no pasó".

### Entregables
- Motor de políticas (`PolicyEngine`) que se evalúa antes de cualquier llamada de red desde
  cualquier tipo de nodo (agente vía `ModelProvider`, herramientas HTTP, sandbox de código)
- Toggle de "modo air-gap" a nivel de grafo (o global)
- Certificado de ejecución: al terminar una ejecución en modo air-gap, un reporte firmado/
  verificable que enumera todos los intentos de red detectados (idealmente ninguno) basado
  en el log auditable de la Fase 7
- UI: indicador visual claro de que un grafo está en modo air-gap, y advertencia si algún
  nodo de ese grafo referencia un `ModelProvider` no local (esto debería bloquearse al
  guardar el grafo, no solo al ejecutarlo)

### Tareas
1. Diseñar `PolicyEngine` como un punto único de verificación que se invoca desde: `ModelProvider` (antes de cualquier llamada HTTP a un proveedor externo), herramientas HTTP built-in, y el sandbox de código (ya instrumentado en Fase 7).
2. El toggle de air-gap a nivel de grafo debe validarse en dos momentos: (a) al guardar el grafo, rechazando si algún nodo referencia un proveedor no-local mientras el modo está activo; (b) en tiempo de ejecución, como doble verificación (defensa en profundidad, no confiar solo en la validación de guardado).
3. Endpoint `GET /executions/{id}/airgap-report` — genera el reporte de verificación: lista de todos los intentos de red detectados durante la ejecución (debería estar vacía si todo funcionó), timestamp de generación, hash del log de eventos para que el reporte sea verificable/no manipulable después.
4. UI: badge visible en el canvas y en la vista de ejecución cuando un grafo está en modo air-gap. Bloqueo visual al intentar agregar un nodo con proveedor externo a un grafo air-gap.
5. Documentar en `/docs/airgap-mode.md` exactamente qué garantiza este modo y qué no (ej. no protege contra un modelo local que fue entrenado con exfiltración de datos como backdoor — el alcance es "no hubo tráfico de red durante la ejecución", no "el modelo es confiable").
6. Tests: grafo con un nodo mal configurado que intenta usar un proveedor externo estando en modo air-gap → debe fallar al guardar. Grafo correctamente local → el reporte de verificación debe mostrar cero intentos de red.

### Criterios de aceptación
- No es posible guardar un grafo con modo air-gap activo si algún nodo referencia un proveedor externo.
- Después de ejecutar un grafo en modo air-gap, puedes descargar/consultar un reporte que demuestra que no hubo tráfico de red.
- La documentación es honesta sobre los límites de esta garantía.

### Prompt sugerido para Claude Code
```
Vamos a implementar el "modo air-gap verificable" — la segunda feature diferenciadora
principal del proyecto. El objetivo no es solo "permitir modelos locales" (ya lo hacemos
desde la Fase 6), sino ofrecer una garantía activa y auditable de que una ejecución no
tocó la red en absoluto.

Ya tenemos, desde la Fase 7, un log auditable centralizado de todo intento de acceso a red
(desde ModelProvider, herramientas HTTP, y el sandbox de código). Necesito:

1. Un PolicyEngine que se invoque como punto único de verificación antes de cualquier
   llamada de red desde cualquier componente del sistema.
2. Un toggle de "modo air-gap" a nivel de GraphDefinition, validado en dos momentos:
   al guardar el grafo (rechazar si algún nodo referencia un proveedor no-local) y en
   tiempo de ejecución como verificación redundante.
3. GET /executions/{id}/airgap-report — reporte de verificación post-ejecución: lista de
   intentos de red detectados (debería estar vacía), timestamp, y un hash del log de
   eventos para que el reporte no pueda alterarse después sin detección.
4. Actualiza el frontend: badge visible cuando un grafo está en modo air-gap, y bloqueo
   al intentar agregar un nodo con proveedor externo a un grafo en ese modo.

Antes de implementar, escribe /docs/airgap-mode.md explicando con total honestidad qué
garantiza este modo (ausencia de tráfico de red durante la ejecución) y qué NO garantiza
(por ejemplo, no valida la procedencia o confiabilidad del modelo local en sí). Quiero
revisar ese documento antes de que implementes el enforcement.
```

---

## Fase 9 — Patrones multi-agente como plantillas

**Objetivo**: bajar la fricción de "pantalla vacía" con ejemplos reales, y de paso, un buen
test de integración end-to-end de todo lo construido hasta ahora (incluyendo time-travel y
air-gap).

### Entregables
- 3-4 grafos de ejemplo completos en `/examples/`
- Import/export de grafos

### Tareas
1. Construir los ejemplos: investigador+verificador con loop, triage de tickets con router, pipeline de revisión de código con nodo de código real.
2. Al menos uno de los ejemplos debe estar configurado en modo air-gap (ej. el de triage, usando solo modelo local) para servir como demo funcional de la Fase 8.
3. Exportar cada uno como JSON en `/examples/`, con README describiendo qué hace.
4. Import/export de grafos vía UI y endpoint.
5. Seed automático: si la DB está vacía al arrancar, cargar estos ejemplos.

### Criterios de aceptación
- Un usuario nuevo ve al menos un ejemplo ya cargado y puede ejecutarlo sin configurar nada más que sus API keys (o nada, si prueba el ejemplo air-gap).

### Prompt sugerido para Claude Code
```
Vamos a crear plantillas de ejemplo que se cargan automáticamente en el primer arranque.

Necesito:
1. Import/export de grafos como JSON (endpoint + botones en la UI).
2. Crear 3 grafos de ejemplo funcionales: (a) investigador + verificador con loop de
   corrección, (b) router de triage con 2-3 agentes especialistas — este debe usar
   SOLO modelos locales y tener el modo air-gap activado, como demo funcional de esa
   feature, (c) pipeline de revisión de código con nodo de código real corriendo un linter.
3. Seed automático: si la base de datos está vacía al arrancar, cargar estos ejemplos
   desde /examples/*.json.

Documenta cada ejemplo con un README corto explicando qué hace y qué necesita configurado.
```

---

## 🌟 Fase 10 — Evals integrados al editor

**Objetivo**: la tercera feature diferenciadora. Permitir que cada grafo tenga casos de
prueba adjuntos, que se ejecutan automáticamente y detectan regresiones cuando editas un
prompt o cambias la configuración de un nodo — sin salir del builder ni usar otra herramienta.

### Entregables
- Modelo de datos para "casos de prueba" (`EvalCase`) asociados a un grafo: input, criterio de éxito (puede ser texto exacto, un patrón, o — más interesante — una evaluación con LLM tipo "juez")
- Runner de evals: ejecuta todos los casos de prueba de un grafo y produce un reporte pass/fail
- Integración con el flujo de guardado: opción de correr evals automáticamente antes de confirmar cambios importantes a un grafo (ej. cambio de prompt en un nodo agent)
- UI: panel de evals junto al canvas, con historial de resultados por versión del grafo

### Tareas
1. Diseñar `EvalCase`: input inicial del grafo, criterio de éxito. Al menos dos tipos de criterio: (a) determinístico (el output final contiene/coincide con cierto valor), (b) evaluado por LLM ("juez" que recibe el output y una rúbrica en lenguaje natural, y devuelve pass/fail con justificación — reutilizar la capa `ModelProvider` de la Fase 6 para esto).
2. Runner: dado un grafo y su lista de `EvalCase`, ejecutarlos todos (en paralelo cuando sea posible) y producir un reporte con resultado por caso.
3. Endpoint `POST /graphs/{id}/evals/run` y `GET /graphs/{id}/evals/history`.
4. Integrar con el versionado de grafos (si ya existe de una fase de hardening posterior, o como mejora incremental): cada corrida de evals debe quedar asociada a la versión específica del grafo que se evaluó, para poder comparar "¿esta edición mejoró o empeoró los resultados?".
5. UI: panel de evals en el builder, con botón "correr evals" y vista de resultados históricos por versión.
6. Tests del runner de evals en sí (meta-tests: verificar que el runner detecta correctamente un caso que debería fallar).

### Criterios de aceptación
- Puedes definir al menos 3 casos de prueba para un grafo.
- Al correr los evals, obtienes un reporte claro de qué casos pasaron y cuáles no.
- Si editas un prompt de un agente y eso rompe un caso que antes pasaba, el próximo run de evals lo detecta.

### Prompt sugerido para Claude Code
```
Vamos a implementar evaluaciones (evals) integradas al editor — la tercera feature
diferenciadora principal del proyecto. El objetivo es que un usuario pueda definir casos
de prueba para un grafo y detectar regresiones al editar prompts, sin salir del builder.

Necesito:
1. Un modelo EvalCase asociado a un GraphDefinition: input inicial del grafo, y un criterio
   de éxito. Soporta dos tipos de criterio: determinístico (el output contiene/coincide con
   un valor esperado) y evaluado por LLM (un "juez" que recibe el output final y una rúbrica
   en lenguaje natural, y devuelve pass/fail con justificación — reutiliza la interfaz
   ModelProvider ya implementada para esto, no crees un cliente de LLM nuevo).
2. Un runner que, dado un grafo y su lista de EvalCase, los ejecute todos (en paralelo
   cuando el tipo de caso lo permita) y produzca un reporte con resultado por caso.
3. Endpoints POST /graphs/{id}/evals/run y GET /graphs/{id}/evals/history, donde cada
   corrida queda asociada a la versión del grafo evaluada.
4. Un panel en el frontend junto al canvas: definir casos de prueba, botón "correr evals",
   y vista de resultados históricos que permita comparar si una edición reciente mejoró o
   empeoró los resultados.

Antes de implementar el criterio evaluado por LLM, muéstrame el prompt que le vas a dar al
"juez" — quiero revisar que sea lo suficientemente robusto antes de que dependamos de él
para detectar regresiones reales.
```

---

## Fase 11 — Empaquetado y developer experience

**Objetivo**: "un comando y funciona", para usuarios finales y para nuevos contribuidores.

### Tareas
1. Completar `docker-compose.yml` real (todos los servicios, healthchecks, volúmenes persistentes).
2. Script `scripts/setup.sh` para instalación sin Docker.
3. Wizard inicial en la UI: configurar al menos una API key o confirmar modelos locales (y mencionar el modo air-gap como opción destacada en el wizard — es una de las cosas que distingue al proyecto, vale la pena que se note desde el primer minuto).
4. `README.md` completo con GIF/capturas (incluyendo una demo corta de time-travel debugging y del reporte air-gap — son las mejores cartas de presentación del proyecto).
5. GitHub Actions: build y publish de imágenes Docker multi-arquitectura en cada release.
6. `CONTRIBUTING.md`.

### Criterios de aceptación
- Clonar + `docker compose up` deja el builder funcionando en menos de 5 minutos.

### Prompt sugerido para Claude Code
```
Vamos a preparar el proyecto para distribución open source fácil de instalar.

Necesito:
1. Completar docker-compose.yml con todos los servicios, healthchecks, y volúmenes
   persistentes.
2. Un script scripts/setup.sh para desarrollo sin Docker.
3. Un wizard de primera configuración en el frontend que guíe a configurar al menos un
   proveedor de modelo, destacando el modo air-gap como opción para quien no quiere
   configurar ninguna API externa.
4. Un GitHub Actions workflow que en cada tag de release construya y publique imágenes
   Docker multi-arquitectura en GitHub Container Registry.
5. Un CONTRIBUTING.md.

Verifica que `docker compose up` desde un clon limpio deja el sistema funcional sin pasos
manuales adicionales más allá de configurar proveedores de modelo.
```

---

## Fase 12 — Hardening y preparación final para lanzamiento público

### Tareas
1. Auditoría de seguridad enfocada en: sandbox de código, `PolicyEngine`/modo air-gap (verificar que realmente no tiene fugas), manejo de secrets, validación de inputs.
2. Cobertura de tests en rutas críticas del core, evals runner, y policy engine.
3. Rate limiting básico en la API.
4. Documentación de arquitectura completa en `/docs/`.
5. `CODE_OF_CONDUCT.md`, plantillas de issues/PRs.
6. Preparar anuncio de lanzamiento.

### Prompt sugerido para Claude Code
```
Estamos preparando el lanzamiento público del proyecto. Necesito una auditoría de seguridad
enfocada en: el sandbox de ejecución de código, el PolicyEngine del modo air-gap (verifica
específicamente que no haya ninguna ruta de red que no pase por el punto de verificación
centralizado), el manejo de API keys y secrets, y la validación de inputs en los endpoints.

Revisa el código existente y dame un reporte de hallazgos priorizado por severidad, sin
hacer cambios todavía. Presta especial atención al PolicyEngine — es la pieza de la que
depende toda la garantía del modo air-gap, así que un fallo ahí socava la promesa central
de esa feature.
```

---

## Fase 13 — Extensiones (post-lanzamiento, priorizar según feedback real)

Features de "fase 2" identificadas pero no priorizadas para el lanzamiento inicial:

- **Guardrails locales modulares**: capa de checks (PII, contenido sensible) ejecutados con modelos pequeños locales, adjuntables a cualquier nodo — extiende naturalmente el modo air-gap.
- **Contabilidad de costo/tokens por nodo y por ejecución**, con límites de presupuesto configurables que pausan ejecuciones.
- Multi-usuario/auth real.
- Marketplace de herramientas/plantillas compartidas por la comunidad.
- Versionado completo de grafos con diff visual (si no se adelantó parte de esto durante la Fase 10).
- Export a código Python standalone.
- Soporte para frameworks de orquestación adicionales a LangGraph.

No planifiques esta fase en detalle todavía — prioriza según qué pida la comunidad una vez el proyecto esté público.

---

## Recomendaciones generales de trabajo con Claude Code

- **Una sesión, una fase (o sub-tarea clara)**. Sesiones largas que saltan de tema pierden contexto útil.
- **Pide diseño antes que código en las decisiones caras de revertir**: esquema del grafo (Fase 1), sandbox (Fase 7), PolicyEngine de air-gap (Fase 8), el prompt del "juez" de evals (Fase 10).
- **Revisa diffs, no solo que "funcione"**, especialmente en Fase 7 y Fase 8 — son las piezas de seguridad de las que depende la credibilidad del proyecto.
- **Usa `CLAUDE.md` como memoria persistente**, actualízalo cuando tomes decisiones de arquitectura nuevas.
- **Commits pequeños y frecuentes** por sub-tarea.
- Las fases marcadas con 🌟 son las que justifican la existencia del proyecto frente a alternativas ya maduras — no las apures ni las dejes a medias por cansancio hacia el final del roadmap.
