# tinkercad-brain

Asistente personal y local para construir circuitos Arduino en **Tinkercad
Circuits**, verificarlos automáticamente y documentarlos. Un solo usuario,
uso local. Todo circuito producido termina como diseño guardado en
Tinkercad (`tinkercad.com/things/<id>/editel`), recargable y editable a
mano: esa es la regla de diseño número uno.

## Arquitectura

| Pieza | Repo | Qué hace |
|---|---|---|
| El puente (las manos) | `Aveess/tinkercad-mcp-bridge` (privado) | Servidor MCP en Python/Playwright con 49 tools. Fork de ezhil-kumaran saneado para Linux + tools propias: construcción por huecos directa en el modelo del editor (`tinkercad_build_circuit_model`) con ruteo ortogonal por carriles, y sampler de simulación |
| El cerebro (este repo) | `Aveess/tinkercad-brain` (privado) | Spec por huecos validada, planner de layout, builder, derivación de nets con continuidad de protoboard, comparación por equivalencia eléctrica, verificador por serial instrumentado, documentador |

Las dos capas hablan **MCP sobre stdio**. El cerebro nunca importa al
puente en producción.

## Cómo se construye un circuito

1. Se describe el circuito como fixture/spec (componentes, nets, código).
2. `layout.plan_layout` asigna huecos de protoboard por bloques
   (LED+resistencia de 6 en 6, 3 pines en fila c, HC-SR04 en fila d desde
   la columna 18, botón cruzando el gap, piezo y LDR en una segunda pasada
   al extremo derecho porque su cuerpo es un disco grande que tapa
   vecinos).
3. `builder.fixture_to_model_call` lo traduce a la llamada del puente:
   partes con DID real, wires `{from, to, color}` ordenados
   alimentación → tierra → señales (negro/rojo/paleta).
4. El puente coloca directo en `circuit_editor.data` con insert-wires,
   espera la persistencia ShareJS (`numberPending == 0`) y rutea los
   cables del Uno en ángulo recto con carriles propios.
5. Tras recargar, `inspect_circuit` + `breadboard_nets.derive_nets`
   reconstruyen el circuito real y `metrics.compare_connectivity`
   lo compara por equivalencia eléctrica (tierras del Uno unificadas,
   alias de pines por tipo, cortos detectados).
6. El comportamiento se verifica en simulación con el **oráculo
   serial instrumentado**: los sketches generan trazas `TEST:...`
   (`TEST:ON/OFF`, `TEST:ANGLE=`, `TEST:TEMP=`, `TEST:DIST=`) que el
   verificador evalúa. (La lectura de LED por píxel existe pero no
   calibra en headless: no se usa como verdad.)
7. `documenter` genera el reporte Markdown del build en
   `docs/reportes/`.

## Circuitos ya construidos y verificados

Ver `docs/benchmark.md` (17 circuitos en cinco niveles, todos al 100% de
fidelidad: blink, semáforo, botón, servo, TMP36, ultrasónico, RGB, motor con
transistor, motor con L293D y batería, buzzer con botón, LDR en luz nocturna,
una barrera de parking con sensor + servo + RGB, un LCD 16x2 en modo 4 bits, un
termómetro TMP36 que muestra la lectura en ese LCD, un medidor de distancia
con display y alarma sonora, un contador 0-9 en display 7 segmentos y ese
mismo contador con un registro de desplazamiento 74HC595)
y los reportes individuales en `docs/reportes/`.

## Puesta en marcha

Puente (una sola vez):

```bash
cd ~/Documentos/StartUp/TInkercad/tinkercad-mcp
.venv/bin/python -m src.cli.login_cli   # login interactivo, queda en el perfil
.venv/bin/playwright install chromium
```

Cerebro:

```bash
cd ~/Documentos/StartUp/TInkercad/tinkercad-brain
.venv/bin/pytest -q
```

## Reglas del proyecto

- Cableado organizado siempre: orden alimentación/tierra/señales,
  colores por convención, ruteo ortogonal con carriles. Guía en
  `docs/organizacion-cables.md`.
- Ningún agente se aprueba a sí mismo: cada ronda de desarrollo la
  cierra un tester independiente que no escribe código de producción.
- Sin secretos en los repos: la sesión de Tinkercad vive solo en el
  perfil persistente del navegador.
