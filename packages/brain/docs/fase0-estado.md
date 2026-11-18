# Fase 0 — estado (2026-11-11)

## Infraestructura (sin login) — aprobada por tester independiente

| Pieza | Evidencia |
|---|---|
| probe harness (Agente A) | tests propios + del tester en verde |
| fixtures ground-truth, 10 circuitos (Agente B) | coherencia LED→resistencia verificada por el tester sobre datos reales |
| metrics: fidelidad con castigo a extras, latencia, classify (Agente C) | 15 tests adversarios del tester pasaron tras los fixes |
| Suite integrada | 49 passed (orquestador + re-verificación del tester) |
| Puente MCP por stdio | 46 tools listadas; Chromium de Playwright instalado; `tinkercad_auth_status` responde |

## Bloqueante único para la Fase 0 viva

`authenticated: false` — falta login de Tinkercad en el perfil persistente del
navegador. Sin eso no se puede medir: fidelidad de lectura (meta ≥95%),
latencias, ni granularidad del error de compilación.

## Regla de decisión (del plan v3)

Si la fidelidad medida es <90%, el diagnosticador sale del alcance y el
proyecto queda en construir + verificar.
