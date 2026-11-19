# tinkercad-brain

> Proyecto **no oficial**, sin relación con Autodesk. «Tinkercad» es marca de
> Autodesk y aquí solo se usa para nombrar el simulador al que apunta.

Asistente personal y local para construir circuitos Arduino en **Tinkercad
Circuits**, verificarlos automáticamente y documentarlos. Un solo usuario,
uso local. Todo circuito producido termina como diseño guardado en
Tinkercad (`tinkercad.com/things/<id>/editel`), recargable y editable a
mano: esa es la regla de diseño número uno.

## Arquitectura

| Pieza | Dónde | Qué hace |
|---|---|---|
| El puente (las manos) | [`packages/bridge`](../bridge) | Servidor MCP en Python/Playwright con 50 tools. Base de [`ezhil-kumaran/Tinkercad-mcp`](https://github.com/ezhil-kumaran/Tinkercad-mcp) saneada para Linux + tools propias: construcción por huecos directa en el modelo del editor (`tinkercad_build_circuit_model`) con ruteo ortogonal por carriles, y sampler de simulación |
| El cerebro (este paquete) | `packages/brain` | Spec por huecos validada, planner de layout, builder, derivación de nets con continuidad de protoboard, comparación por equivalencia eléctrica, verificador por serial instrumentado, documentador |

Las dos capas hablan **MCP sobre stdio**. El cerebro nunca importa al
puente en producción.

## Cómo se construye un circuito

1. Se describe el circuito como fixture/spec (componentes, nets, código).
2. `layout.plan_layout` asigna huecos de protoboard por bloques
   (LED+resistencia de 6 en 6, 3 pines en fila c, HC-SR04 en fila d desde
   la columna 18, botón cruzando el gap, piezo y LDR en una segunda pasada
   al extremo derecho porque su cuerpo es un disco grande que tapa
   vecinos). Con `"board2": [refs]` una segunda protoboard recibe el banco
   vertical de resistencias (banco de 4 columnas por pieza en la fila d, el
   pin 2 cae en la f) y los huecos viajan como `b1/5d`.
3. `builder.fixture_to_model_call` lo traduce a la llamada del puente:
   partes con DID real, wires `{from, to, color}` ordenados
   alimentación → tierra → señales (negro/rojo/paleta). Antes de nada
   corre el lint de resistencia serie: un LED o un segmento colgado
   directo de un pin o de 5V/GND no se construye (en el simulador
   revienta y el serial sigue contando, así que el oráculo no lo ve).
4. El puente coloca directo en `circuit_editor.data` con insert-wires,
   espera la persistencia ShareJS (`numberPending == 0`) y rutea los
   cables del Uno en ángulo recto con carriles propios, repartidos en dos
   bandas (arriba/abajo de la placa) que crecen por separado, con 130
   unidades de holgura sobre el cuerpo de la placa. Devuelve el nombre real
   que el editor dejó en cada parte (`placed[ref].name`): Tinkercad
   deduplica (`r2` → `r21`) y el nombre no sirve como identidad. También
   devuelve la polilínea de cada cable ruteado.
5. `builder.route_band_violations` revisa esas polilíneas: un tramo
   horizontal no puede caer sobre el cuerpo de una placa (un vertical sí:
   así se entra a un hueco). Si hay alguno, el build no da `OK`.
6. Tras recargar, `inspect_circuit` + `breadboard_nets.derive_nets`
   reconstruyen el circuito real y `metrics.compare_connectivity`
   lo compara por equivalencia eléctrica (tierras del Uno unificadas,
   alias de pines por tipo, cortos detectados). Las refs salen del mapa
   `nombre → ref` que devolvió el build, no de la posición de creación.
7. El comportamiento se verifica en simulación con el **oráculo
   serial instrumentado**: los sketches generan trazas `TEST:...`
   (`TEST:ON/OFF`, `TEST:ANGLE=`, `TEST:TEMP=`, `TEST:DIST=`) que el
   verificador evalúa. (La lectura de LED por píxel existe pero no
   calibra en headless: no se usa como verdad.)
7. `documenter` genera el reporte Markdown del build en
   `docs/reportes/`. Antes de enviar el sketch, `circuit_doc` le antepone
   un bloque de documentación generado desde la fixture (título, piezas,
   cableado net por net y el oráculo serial), así que el diseño guardado
   se explica solo al abrir el editor de código.

## Circuitos ya construidos y verificados

Ver `docs/benchmark.md` (28 circuitos en doce niveles, todos al 100% de
fidelidad: blink, semáforo, botón, servo, TMP36, ultrasónico, RGB, motor con
transistor, motor con L293D y batería, buzzer con botón, LDR en luz nocturna,
una barrera de parking con sensor + servo + RGB, un LCD 16x2 en modo 4 bits, un
termómetro TMP36 que muestra la lectura en ese LCD, un medidor de distancia
con display y alarma sonora, un contador 0-9 en display 7 segmentos, ese
mismo contador con un registro de desplazamiento 74HC595, una media suma con
compuertas, un biestable D como divisor, un 555 como reloj, un contador
binario 74HC93, un carrusel de LEDs con el contador Johnson 4017 y un faro
automatico con rele SPDT movido por un NPN, una alarma de movimiento con
PIR, una cerradura con teclado 4x4, una caja fuerte con teclado y LCD y un
control de acceso con teclado, LCD y servo (servo en colocacion libre), y un
contador 0-7 lento con reloj 555 y compuertas AND/OR/XOR con las siete
resistencias de serie del display en una segunda protoboard. Los
cables del LCD salen de lado antes de bajar, asi que no pasan por detras de
su propio cuerpo; y cuando un piezo comparte circuito con el sensor
ultrasonico el piezo va libre, para que su cuerpo no tape la placa)
y los reportes individuales en `docs/reportes/`.

## Puesta en marcha

Todo sale del `setup.sh` de la raíz del monorepo (venv + dependencias +
Chromium + este paquete en modo editable). Después, el login del puente, una
sola vez:

```bash
cd ../..                                  # raíz de mcp-circuits
.venv/bin/python -m src.cli.login_cli     # login interactivo, queda en el perfil
```

El cerebro busca el puente en `packages/bridge`; si vive en otra ruta,
`TINKERCAD_BRIDGE` manda, y `demo_build.py` además acepta `--bridge`.

Suite:

```bash
cd packages/brain && ../../.venv/bin/python -m pytest -q
```

## Reglas del proyecto

- Cableado organizado siempre: orden alimentación/tierra/señales,
  colores por convención, ruteo ortogonal con carriles. Guía en
  `docs/organizacion-cables.md`.
- Ningún agente se aprueba a sí mismo: cada ronda de desarrollo la
  cierra un tester independiente que no escribe código de producción.
- Sin secretos en los repos: la sesión de Tinkercad vive solo en el
  perfil persistente del navegador.

## Si lo usas, cuéntalo

No hay telemetría: el repo no manda nada a ningún lado y no me entero de quién
lo clona. Si te sirvió, **abre un issue contando qué armaste y qué se rompió**.
Es la única señal de uso que existe.

## Créditos

Este repo se apoya en trabajo ajeno, y se dice explícitamente:

| Proyecto | Licencia | Qué se tomó |
|---|---|---|
| [`ezhil-kumaran/Tinkercad-mcp`](https://github.com/ezhil-kumaran/Tinkercad-mcp) | MIT | Es la base del **puente** (`packages/bridge`): servidor MCP, Playwright, catálogo de componentes y la mayoría de las tools. El trabajo propio encima le agregó el build por huecos, el ruteo ortogonal y el sampler |
| [`sethski/tinkercad-mcp-server`](https://github.com/sethski/tinkercad-mcp-server) | MIT | Proyecto previo (Node/TypeScript) del que nace la idea: manejar el editor real de Tinkercad con un navegador porque no hay API pública |

Todo lo demás —el planner de layout por huecos, la derivación de nets con
continuidad de protoboard, la comparación por equivalencia eléctrica, el
oráculo serial instrumentado, los generadores de informes y la documentación—
es de este paquete. Si reutilizas cualquiera de las dos capas, conserva los
avisos de copyright: la MIT lo exige.
