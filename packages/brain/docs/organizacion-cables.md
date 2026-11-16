# Organización de cableado

Guía operativa para todo circuito construido por el proyecto, desde el más fácil.
Estado = qué hace hoy el código; **Aspiracional** = regla vigente al diseñar/revisar,
aún no implementada en código.

## Reglas

| # | Regla | Estado hoy |
|---|---|---|
| 1 | Orden de construcción: 1) alimentación, 2) tierra, 3) señales. | **En código:** `builder._ordered_colored_wires` agrupa en ese orden (0 alimentación, 1 tierra, 2 señal) y ordena por primer extremo dentro de cada grupo, para que el ruteo sea estable. |
| 2 | Colores: tierra negro; 5V/3V3 rojo; señales en paleta rotativa, sin repetir el color del vecino. | **En código:** `builder._wire_group` decide por extremo (5V/riel `T+`/`B+`/fuente → rojo; GND/riel `T-`/`B-` → negro; resto → paleta). Un terminal `+` solo cuenta como alimentación si la parte es fuente real (fase 37). |
| 3 | Ruteo ortogonal: cables en ángulo recto, sin diagonales largas. Uno↔placa: cada cable baja/sube a su propio carril y no pasa sobre otro componente. | **En código y medido:** el puente rutea los cables Uno↔hueco, Uno↔riel y parte-libre↔placa con `addPoint` (fase 22/36). **Bandas por lado (fase 39):** `sideLanes.top/bottom`, paso 8; el lado lo decide el hueco (filas f..j y riel `T` arriba, e..a y `B` abajo) o la `y` de la parte libre. **Holgura (fase 40):** la banda arranca en ±130, no en ±115 — el cuerpo de la placa llega a ±110 y 5 unidades de aire se veían como un cable pegado al borde. Si una parte libre cae dentro de la banda, el carril se corre 30 más allá de la parte sin entrar nunca a la placa. El lint `builder.route_band_violations` mide la polilínea que devuelve el puente y falla el build si un tramo horizontal pasa por encima de una placa. **Libre↔libre (fase 41):** estos cables también se rutean, en Z (la vertical en la columna del medio, o a 70 del origen si las dos terminales son de la misma parte). El lint `builder.diagonal_segments` falla el build si un cable que toca una parte libre o el Uno tiene un tramo diagonal. |
| 4 | Cables cortos dentro de la placa: rectos, por el hueco más cercano, sin rodeos. | **En código** para nets de 2 extremos (se dejan tal cual). Las de 3+ extremos van en estrella desde el hub: un cable hueco↔hueco lo dibuja recto el simulador y cruza los cuerpos. |
| 5 | Separación en layout: 6 columnas por bloque LED+resistencia; bloques de 3 pines ocupan 3 columnas + 1 libre de separación; ningún bloque comparte columna de inicio con otro. | **En código:** `layout.BLOCK_WIDTH=6`, `THREE_PIN_WIDTH=4`, cursor compartido. Las resistencias del banco de la segunda placa van cada 4 columnas (`SECOND_BOARD_COLUMN_STEP`). |
| 6 | Rieles: con más de 2 conexiones al mismo punto, usar riel: `T-` para tierra y `T+` para 5V, en vez de cables sueltos repetidos al Uno. | **En código (opt-in):** `"wiring": "rails"` en la fixture. Cada terminal baja al riel de su misma columna, el Uno lo alimenta una vez y los dos rieles del mismo tipo se puentean en la columna 30. Una parte de la segunda placa nunca baja al riel de la primera: va directa al pin del Uno. **Superado por la regla v3** (abajo) en los layout `v2`/`v3`: ahí el riel es obligatorio y lo alimenta la fuente, no el Uno. |
| 7 | Cada mazo en su zona: lo que alimenta al Uno y lo que sale del display no comparten banda. | **En código (fase 39):** la banda superior y la inferior tienen contadores separados. En el banco vertical de resistencias, el pin de abajo recibe el cable del Uno (banda inferior) y el de arriba alimenta el display (banda superior). |

## Regla v3: alimentación por fuente y rieles

Esta es la regla vigente en los layout `v2`/`v3` (implementada en
`layout_v3.py`), y es la que reemplaza a la fila 6 de arriba:

1. La fuente es la pieza **Power Supply** (`did 111724`, pines `Vcc`/`GND`).
   El pin de 5 V del Arduino **no** reparte alimentación: el Uno es un
   consumidor más. Su `GND1` sí cuelga del riel de tierra porque es la
   referencia de las lecturas analógicas.
2. **Rojo** de `Vcc` al riel positivo; **negro** de `GND` al riel negativo.
   Rojo y negro no se usan para señales.
3. Dos cables más, uno de cada color, al riel del **borde opuesto**: la placa
   queda alimentada de punta a punta.
4. Cada pata baja al riel de **su propia mitad** con un cable corto, en su
   misma columna, cuando esa columna tiene hueco de riel. Si no lo tiene, el
   cable va **directo al hueco de riel más cercano**; solo las patas de la
   mitad contraria usan la **fila de bus** (`_BUS_ROWS`), porque para ellas el
   riel está en el otro lado. Un bus nunca aterriza en una media columna que
   ya tenga una pata ajena: esa media columna es la pata, y tocarla es un
   corto (quemó un 74HC86 el 2026-11-15).
5. Una placa adicional se alimenta de la placa ya alimentada, nunca de la
   fuente.
6. El **Arduino no es la fuente**: por defecto no se pone, y solo entra si el
   proyecto necesita programa (pines, serial, sensores, EN/RESET).

Restricciones geométricas que la regla respeta (medidas el 2026-11-15):

- En la **placa grande** el par de filas de abajo es **un solo nodo** (`X`):
  solo una polaridad puede vivir ahí. Cuando el positivo va abajo, la tierra
  de la mitad de abajo llega por fila de bus; el cable de borde de tierra no
  existe en esa placa y el reporte lo dice.
- Los **huecos de riel de la grande no son las primeras 50 columnas**: faltan
  en 6, 12, 18, 24, 30, 31, 37, 43, 49, 55, 61 y 62. Un extremo de cable a
  `B+24` o `T+43` no resuelve en el puente, así que el layout solo elige
  columnas de `boards.rail_holes(kind)`.

## Regla v4: sin Arduino (EN y RESET en hardware)

La v4 del contador aplica la regla 6 de arriba: el micro se va y los dos
mandos que él movía pasan a piezas. Es la referencia para cualquier circuito
que no necesite programa.

- **EN** es un interruptor deslizante SPDT (`Slide Switch`, `did 58458`):
  común a las J y K, un extremo a GND y el otro a Vcc. Con el común en GND
  los flip-flops conservan el estado.
  **El extremo que va a Vcc es la clave `1`**, porque el modelo nace con el
  común en esa posición: así el diseño cuenta al abrirlo. Medido en vivo el
  2026-11-15 con el build `3akmw1EaG0p`: cableado al revés, el display se
  quedó en 0 durante 40 s de simulación y solo arrancó al deslizar el switch.
- **RESET** es un pulsador (`Pushbutton`, `did 144786`) de Vcc a la entrada
  de un inversor, con **pull-down de 10 kΩ a GND**. En reposo el inversor
  entrega 1 y las R (activas en bajo) no actúan; al apretar entrega 0.
- La fixture lo declara con `"no_arduino": true`. El puente **siempre crea
  el Uno** (`ensureDevice`), así que el build lo quita al final con
  `remove_unused_uno` si ningún cable del plan lo toca. Sin eso, el Arduino
  vacío baja la fidelidad de piezas a 26/27 aunque el cableado esté al 100 %.
- El builder **rechaza** una fixture `no_arduino` con endpoints `uno.*`: es
  contradictorio pedir que se quite y cablearlo.

### Pines de las piezas cableadas: se usan las claves del modelo

Medido el 2026-11-15 con una sonda que volcó `dev.name2terminal` en vivo. El
puente resuelve un pin por **coincidencia exacta de clave** y solo después por
`pinName`/nombre, así que los nombres que muestra la UI **no resuelven**
(`wire ... endpoint_not_resolved`):

| Pieza | Claves del modelo | Nombre en la UI |
| --- | --- | --- |
| Slide Switch | `1` | Terminal 1 |
| | `2` | Terminal 2 |
| | `3` | **Common** |
| Pushbutton | `1` / `2` | Terminal 1b / 1a (un nodo interno) |
| | `3` / `4` | Terminal 2b / 2a (el otro nodo) |

El pulsador tiene **dos patas por lado unidas internamente**: hay que cablear
una de cada lado o el botón queda puenteado. En la fixture, `btn1.1` (señal)
va a la clave `4` y `btn1.2` (tierra/Vcc) a la `2`.

Como la fixture habla el idioma de la UI y el puente el del modelo, hay **dos
espacios de nombres** y una tabla que los une: `boards.MODEL_PIN` +
`boards.model_pin(tipo, pata)`. El layout ancla la pieza con la clave del
modelo (`placements[ref]["pin"]`) y `builder._free_endpoint` traduce cada
cable; sin esa traducción los cables del interruptor salen del terminal suelto
en vez de entrar a la placa.

## Regla v5: mando montado en placa y placa apilada (fase 50)

- El interruptor del EN y el pulsador del RESET **no cuelgan de un cable**:
  van insertados en la placa chica, junto a los dos capacitores. Antes eran
  `free_parts` en (450, ±250) y sus cables cruzaban el lienzo entero.
- La placa chica va **apilada arriba de la placa 0** (la de las siete
  compuertas): misma `x`, `y = -360`. Con eso el mando queda a un cable corto
  de lo que gobierna y el diseño se lee de arriba abajo.
- **Huellas medidas** el 2026-11-16 en un diseño desechable, con el offset de
  `bbDesc.x/y` de cada pata:

  | Pieza | Patas (col, fila) desde el ancla | Consecuencia |
  | --- | --- | --- |
  | Slide Switch | `1` (-1), `common` (0), `2` (+1), todas en fila `e` | Tres columnas seguidas de la misma mitad: no cruza el canal |
  | Pushbutton | `1` (0,e), `2` (-2,e), `m1` (-2,f), `m3` (0,f) | Cada nodo interno queda en UNA columna con las dos mitades puenteadas por dentro |

  El pulsador declara también las **dos patas que no se cablean** (`m1`/`m3`,
  claves `1` y `3` del modelo). Son el mismo nodo que una pata cableada: si el
  ruteo metiera otro net en esa media columna, el corto no se ve en el dibujo.
- **Cables entre placas apiladas**: dos huecos de placas distintas casi nunca
  comparten `y`, así que la recta sería una diagonal larga sobre las dos
  protoboards. El puente los rutea en Z (`crossBoardPair`): sale del hueco al
  carril que cae en el aire entre las dos placas, corre en horizontal y baja al
  otro hueco. El carril se mide **desde el origen de la placa de abajo**
  (`LANE_BASE = 130`, paso 8) y comparte contador con la banda de las partes
  libres. Con la chica en `-360` el hueco libre va de `-110` (borde de la placa
  0) a `-250` (borde de la chica): caben ~15 carriles y hoy se usan 6.
- Los capacitores siguen en la placa chica, pero ahora al lado del mando
  (`c1` en `19f`, `c2` en `23f`).

## Regla v6: ángulos rectos, sin diagonales (fase 51)

Un cable se dibuja con tramos **verticales y horizontales**; cada giro es de
90°. Nada de diagonales, ni largas ni cortas, salvo el puente de hueco a hueco
de la misma placa (regla 4: es una recta de menos de una columna sobre el
plástico y rutearlo lo haría peor que el problema).

- **Entre placas apiladas** el cable es una Z de tres tramos: vertical desde el
  hueco hasta el carril, horizontal por el carril, vertical hasta el otro
  hueco (`crossBoardPair` en `model_build_service`). Con la placa chica en
  `-360` los carriles caen entre `-110` y `-250`, o sea en el aire entre las
  dos placas.
- **La medida es el dibujo, no la intención.** Desde la fase 51 el build
  devuelve `route_debug[*].actual`: los puntos que el editor **guardó** para
  ese cable (`w.objects` → `endpoint()`), al lado de `points`, que es la
  polilínea que el build **pidió**. Comparar los dos es lo que caza un cable
  torcido cuando el plan es ortogonal: el 2026-11-16 el lint decía
  "0 diagonales" sobre un diseño con dos cables en diagonal, porque medía la
  intención.
- **Un cable torcido se arregla reconstruyendo, no a mano.** Medido el
  2026-11-16 en `3akmw1EaG0p`: dos cables guardaban puntos fraccionarios
  (`k/97`, p. ej. `[1654.2577,-99.9588]`) que el build nunca calculó —
  geometría vieja que sobrevivió al guardado — y el rebuild los dejó exactos
  en `[1545,55] → [1545,-178] → [815,-178] → [815,-305]`. Editar los quiebres
  a mano no es confiable: `removePoint` lanza excepción y deja un punto
  huérfano (probado el mismo día).
- **Cada cable de la placa chica (mando y capacitores) sale vertical** a su
  propio riel o al hueco que comparte nodo con su pata: `sw1` (común en
  `10e`, lleva a `b2/10a`), `btn1` (señal en `16e`, lleva a `b2/16b`), y los
  dos capacitores a `T-`/`B+` en su misma columna. Esos cinco cables son
  verticales puros (`dx = 0`) y se verifican con eso, no a ojo.

## Piezas creadas por el MCP: no se mueven ni se editan

Un diseño construido por el puente no se retoca arrastrando: las piezas que
entran por el modelo (`data.createDeviceInstance` + `devices.add`) **no se
seleccionan ni se mueven** en el editor. Medido el 2026-11-16 con tres sondas:

1. una placa agregada desde la **paleta** sí se arrastra y cambia de posición;
2. una placa creada por el **modelo** no se mueve (2 intentos, 0 cambios);
3. en `3akmw1EaG0p`, arrastrar las tres placas deja las posiciones idénticas.

Los **cables sí** se pueden mover: nacen de `BendableWireData`, que el editor
registra como interactivo. No es un permiso de la cuenta ni un modo del
editor: las piezas entran al modelo por una vía que el editor no marca para
selección. Para cambiar el layout se cambia el **generador** y se reconstruye
(el build es determinista y reusa `tinkercad_id`); una pieza suelta se borra y
se vuelve a agregar desde la paleta.

## Segunda protoboard

Cuando la placa 1 no alcanza (el caso real: 8 resistencias de serie no entran en
30 columnas sin tapar los cables), la fixture declara `"board2": [refs]`:

- Solo resistencias, y no pueden ser las que van emparejadas con un LED.
- La placa 2 se coloca en `(1270, 0)`; sus huecos viajan como `b1/5d` y sus
  rieles como `b1/T+5`.
- Máximo 3 placas (`plan.boards`); no conviven con `free_parts` (las partes
  libres de la derecha viven en ese sitio).

## Por qué

- Legibilidad: quien abre el diseño en Tinkercad entiende alimentación, tierra y
  señales de un vistazo, sin seguir cada cable.
- Errores visibles: en circuitos difíciles, un cable cruzado esconde un corto.
  Si todo va ortogonal y por su carril, el cable que cruza es el sospechoso.
- Validez: un cable ordenado no arregla una parte mal alimentada. El lint de
  resistencia serie corre antes de construir.

## Criterio de aceptación visual

En el screenshot del circuito terminado:

- Sin diagonales largas cruzando componentes.
- **Cero tramos horizontales sobre una placa** (`Ruteo: 0 tramo(s)` en el build).
  Lo mide `route_band_violations`, no el ojo: el reporte dice cuántos cables
  se midieron de verdad.
- **Cero diagonales en cables de partes libres o del Uno** (`0 diagonal(es)`).
  Lo mide `diagonal_segments` sobre la polilínea de los 46 cables, no solo de
  los ruteados. Los saltos rectos entre huecos de la placa se cuentan y se
  dejan: son puentes cortos sobre el plástico.
- **`route_debug[*].actual` coincide con `points`** en los cables ruteados: si
  el editor guardó otro punto (`k/97`, desplazado, de menos), el dibujo está
  torcido aunque el lint diga cero. Si no coincide, se reconstruye el diseño.
- Cada cable del Uno baja/sube a su carril sin pasar sobre otro componente.
- Cables repartidos arriba y abajo; no todos por la misma zona.
- Sin cruces innecesarios; colores según regla 2; rieles según regla 6.
- **Ningún componente revienta en simulación.** Un display que estalla sigue
  contando: el serial no es prueba de validez eléctrica.

Si no cumple, no se da por terminado aunque simule bien.

## Qué NO hacemos todavía

- Ruteo automático de cables placa↔placa largos: hoy van por la banda global
  (ya sin rozar la placa, fase 40), no por un corredor propio entre las dos.
- Los saltos rectos entre huecos de la misma placa (`5g -> 8c`) siguen en
  diagonal: son puentes cortos y se cuentan en el reporte, pero no se rutean.
- El lint mide placas, no cuerpos de integrados ni de partes libres: un cable
  puede pasar cerca de un chip. Se mide la placa porque su caja es exacta
  (±160 × ±110); el resto de las cajas no las expone el modelo. El cable que
  cruza la fila de pines de un integrado pasa por el borde de su cuerpo y se
  ve como un puente encima del chip: es lo que haría un cable real.
- Mover componentes ya colocados: el puente no lo soporta. Si el layout sale mal,
  se reconstruye, no se arrastra.
- Nombres de parte libres de deduplicación: Tinkercad cambia `r2` por `r21` si
  ya existe; por eso la identidad viaja en `placed[ref].name` y no en el nombre.
