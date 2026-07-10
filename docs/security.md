# Seguridad

> **Stub (Fase 0).** Se completa en la **Fase 7**. Documentará las garantías del sandbox de
> ejecución de código (subprocess con timeout, sin acceso a red por defecto, sin acceso a
> filesystem fuera de un directorio temporal aislado por ejecución) y, explícitamente, qué
> garantías **no** ofrece.

El nodo de código siempre ejecuta en el sandbox aislado, nunca en el proceso principal
(invariante 3 de [CLAUDE.md](../CLAUDE.md)). El sandbox y el `PolicyEngine` son las piezas
de seguridad centrales del proyecto y requieren cobertura de tests especialmente alta.
