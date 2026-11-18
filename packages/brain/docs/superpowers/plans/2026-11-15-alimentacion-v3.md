# Regla de alimentacion por fuente + v3 del contador (plan)

**Goal:** que el MCP cablee siempre la alimentacion igual (fuente -> riel
positivo/negativo -> puente al extremo opuesto -> taps cortos por componente),
y demostrarlo reconstruyendo el contador 0-7 como **v3** sin tocar v1 ni v2.

**Architecture:** la regla vive en el cerebro (`layout_v3.py`), que reusa el
layout v2 para piezas y senales y **reescribe solo las nets de alimentacion**.
El puente solo necesita aceptar los rieles de la placa grande (hoy los rechaza
por tabla). La fuente es la pieza `Power Supply` (did 111724, pines `Vcc`/`GND`).

**Tech stack:** Python 3.14 (pytest), Playwright + MCP stdio del puente.

**Spec:** este documento + `docs/organizacion-cables.md`.

## Global Constraints

- v1 (`4bJNKia4pfj`) y v2 (`jWUw1co8IZH`) no se tocan: ni fixtures ni diseños.
- Colores obligatorios: **rojo** solo positivo, **negro** solo tierra; senales
  con la paleta. Un cable de senal rojo o negro es un error.
- Una sola fuente de poder por circuito: `Power Supply`. El 5V del Uno no
  alimenta rieles (el Uno cuelga su GND de la tierra comun).
- Placas adicionales se alimentan **de la placa ya alimentada**, no de la fuente.
- Todo deterministico: reordenar las nets no cambia el cableado.

## Review Focus

1. Rieles del par de abajo de la placa grande: el modelo los nombra `X`/`X`.
   Si son el mismo nodo, el puente rojo/negro de abajo es un **corto**. Se mide
   en la corrida real; si aparece, se cae al plan B (bajada por columna de bus).
2. Dos taps en el mismo hueco de riel se dibujan como un cable: cada tap pide
   columna libre.
3. `ps1.GND` y `uno.GND1` tienen que quedar en la misma net o no hay niveles.
4. Los integrados CMOS no pueden quedar sin Vcc/GND: la net de la v2 los incluye
   a todos y la v3 no puede perder ninguno.
5. El display sigue girado 180 grados: la v3 hereda `_PIN_GIRADO` de la v2.

---

### Task 1: rieles de la placa grande en el puente

**Files:** Modify `tinkercad-mcp/src/services/model_build_service.py` (BOARD_KINDS),
`tinkercad-mcp/tests/test_model_build_service.py`.

**Interfaces:** `BOARD_KINDS[116648]["rails"] = {"T+": 85, "T-": 95, "B+": -85, "B-": -95}`;
`parseRail` acepta `T+5`, `b2/B-40` sobre la grande.

- [x] Test: `T+5` sobre 116648 se resuelve a `{x: 725+?, y: 85}` y `B-40` a `y=-95`.
- [x] Run: falla (rails vacios).
- [x] Implementar la tabla.
- [x] Run: pasa; suite completa del puente en verde (333 OK, commit `cfd3b96`).

### Task 2: `layout_v3` (regla de alimentacion)

**Files:** Create `tinkercad-brain/src/tinkercad_brain/layout_v3.py`,
`tinkercad-brain/tests/test_layout_v3.py`. Modify `boards.py` (rieles de LARGE).

**Interfaces:**
`plan_nets_v3(fixture, placements) -> {"wires", "taps", "errors", ...}`,
`power_wires(fixture, placements, boards) -> list[dict]`.

- [x] Tests de la regla (6 aserciones de la Review Focus).
- [x] Run: fallan (modulo nuevo).
- [x] Implementar.
- [x] Run: pasan (14 en `tests/test_layout_v3.py`).

### Task 3: fixture y sketch de la v3

**Files:** Create `contador_jk_v3.py`, `tests/test_contador_jk_v3.py`;
Modify `builder.py` (`layout == "v3"`), `scripts/demo_build.py` (presets v3: R2=22k).

- [x] Test del contrato de la fixture (ps1 presente, vcc/gnd, oraculo).
- [x] Implementar.
- [x] Run: pasa; suite del cerebro completa en verde salvo el id en vivo (2100 passed, 16 skip, 1 xfail; el unico fallo es el `tinkercad_id` que nace del build).

### Task 4: build en vivo de la v3

- [x] `python scripts/demo_build.py contador-0-7-jk-v3` (diseño nuevo, sin id).
  Primer intento: `kSakfQXHtmU`, 97.6 % y oraculo OK, pero 5 cables con
  `endpoint not resolved` — todos a columnas **sin hueco de riel** (24, 37, 43,
  49), no a columnas fuera de rango. El hallazgo esta en `boards.rail_holes`
  (50 de 60 columnas, saltos cada seis) y replicado en el puente.
  Segundo intento: fallan 58 y 60 (o sea los ultimos huecos) porque
  `rail_columns` valia 50 — el **numero** de huecos en vez de la **ultima
  columna** con riel. La tabla de huecos manda; `rail_columns` pasa a 60.
- [x] Verificar: fidelidad 1.0, 0 diagonales, `oracle_ok`, display 0..7 en captura.
- [x] Si el par de abajo da corto: cambiar `BOTTOM_RAILS = False` y bajar por
  columna de bus; volver a medir. (No hizo falta: `_home_sides` ya deja una
  sola polaridad en el par `X` y la tierra de la mitad de abajo por fila de
  bus. El problema era otro.)

### Task 5: documentacion para personas y para agentes

**Files:** Create `tinkercad-mcp/RESTRICCIONES.md`, `tinkercad-mcp/AGENTS.md`.

- [x] Restricciones (persona que usa el MCP): como se usa, que necesita, que no
  se puede, la regla de alimentacion, costos y tiempos.
- [x] AGENTS.md (agente): reglas duras, flujo obligatorio, verificacion, la regla
  de alimentacion como no negociable.
