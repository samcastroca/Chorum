# Esquema del grafo (`GraphDefinition`)

El `GraphDefinition` es la **única fuente de verdad** sobre qué puede ejecutar el sistema
(invariante 1 de [CLAUDE.md](../CLAUDE.md)). El canvas visual serializa/deserializa contra
este esquema, y el motor de orquestación (`backend/app/core/`) lo compila a un `StateGraph`
de LangGraph con checkpointing habilitado desde el diseño (base del time-travel debugging,
Fase 4).

Implementación: [`backend/app/core/schema.py`](../backend/app/core/schema.py). Todos los
modelos son Pydantic v2 y rechazan claves desconocidas (`extra="forbid"`).

## Estructura general

```jsonc
{
  "name": "mi-grafo",
  "version": 1,
  "state_schema": [ /* StateChannel[] */ ],
  "nodes":        [ /* Node[] */ ],
  "edges":        [ /* Edge[] */ ],
  "max_iterations": 25            // cota de ciclos -> recursion_limit de LangGraph
}
```

## Estado compartido — `state_schema`

Lista de canales. Cada canal se traduce a un campo del estado (`TypedDict`) de LangGraph.

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `name` | `str` | — | Clave del canal en el estado. |
| `type` | `str`\|`int`\|`float`\|`bool`\|`list`\|`dict`\|`any` | `any` | Tipo del valor. |
| `reducer` | `replace`\|`append` | `replace` | `append` acumula (`Annotated[list, operator.add]`); útil para logs/mensajes. `replace` sobrescribe. |
| `description` | `str \| null` | `null` | Documentación opcional. |

Un canal `append` arranca en `[]` y los nodos le suman elementos; un canal `replace` guarda
el último valor escrito.

## Nodos — `nodes`

Unión discriminada por `type`. Campos comunes: `id` (único, no puede empezar con `__`),
`label` (opcional). Config por tipo:

| `type` | Campos propios | Comportamiento (Fase 1) |
|---|---|---|
| `start` | — | Punto de entrada. Se mapea al sentinel `START`. Exactamente uno por grafo. |
| `end` | — | Nodo terminal (sin edges salientes). Se mapea a `END`. Al menos uno. |
| `agent` | `system_prompt`, `provider_id?`, `allowed_tools[]`, `memory_policy`, `output_key` | Invoca un modelo vía `ModelProvider` (Fase 6). **Hoy** un placeholder determinista; nunca llama a un SDK. `provider_id` es una **referencia**, jamás una API key (invariante 5). |
| `tool` | `tool_name`, `arguments{}`, `output_key` | Ejecuta una tool registrada (Fase 7). Hoy placeholder. |
| `condition` | — | Nodo de ruteo puro (identidad sobre el estado). El ruteo vive en sus edges salientes. |
| `code` | `code`, `output_key` | **No ejecuta** el código in-process (invariante 3): eso solo ocurre en el sandbox de la Fase 7. Hoy devuelve un marcador. |
| `human_in_loop` | `prompt?`, `input_key` | Pausa la ejecución (`interrupt_before`): el estado queda checkpointeado, listo para reanudar (Fase 4). |

## Edges — `edges`

Aristas dirigidas con condición opcional.

```jsonc
{ "source": "nodo_a", "target": "nodo_b", "condition": null }
```

- **Sin condición**: arista incondicional. Varias aristas incondicionales desde un mismo
  origen producen fan-out (ejecución en paralelo).
- **Con condición**: se compilan como ruteo condicional. Varias condicionales desde el mismo
  origen (o desde un nodo `condition`) se evalúan **en orden**; gana la primera que matchea.
  Una arista **sin** condición desde ese mismo origen actúa como *default*; si no hay default
  y ninguna matchea, se enruta a `END`.

## Condiciones — declarativas, sin `eval`

Como el `GraphDefinition` proviene de JSON del usuario, las condiciones **nunca** se evalúan
con `eval`/`exec`. Son estructuras declarativas (ver
[`conditions.py`](../backend/app/core/conditions.py)).

**Comparación** (hoja):

```jsonc
{ "field": "score", "op": "gte", "value": 10 }
```

- `field`: *dotted path* dentro del estado (ej. `"result.ok"`). Su canal raíz debe estar
  declarado en `state_schema`.
- `op`: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `not_in`, `contains`, `truthy`, `falsy`,
  `exists`. Los operadores de orden sobre tipos incomparables dan `false` (no error). Un campo
  ausente da `false`, salvo `exists`/`falsy`/`ne`/`not_in` que tienen semántica definida.
- `value`: operando; no se usa en `truthy`/`falsy`/`exists`.

**Grupo** (combina con AND entre sus claves; grupo vacío = `true`):

```jsonc
{ "all": [ /* … */ ], "any": [ /* … */ ], "not": { /* … */ } }
```

## Ejecución y checkpointing

`run_graph(definition, input, *, checkpointer)` compila y ejecuta de forma asíncrona,
persistiendo **un checkpoint por paso** bajo un `thread_id`. La recuperación de cualquier
paso intermedio de una ejecución ya terminada se hace con:

- `list_checkpoints(compiled, thread_id)` → resumen de cada checkpoint.
- `get_state_at(compiled, thread_id, checkpoint_id)` → estado exacto en ese punto.

Ver [`time-travel.md`](./time-travel.md) para la feature de bifurcación (Fase 4) que se
construye encima. Un grafo de ejemplo ejecutable está en
[`examples/linear_pipeline.json`](../examples/linear_pipeline.json)
(correr con [`scripts/run_example.py`](../scripts/run_example.py)).
