# Organización de cableado

Guía operativa para todo circuito construido por el proyecto, desde el más fácil.
Estado = qué hace hoy el código; **Aspiracional** = regla vigente al diseñar/revisar,
aún no implementada en código.

## Reglas

| # | Regla | Estado hoy |
|---|---|---|
| 1 | Orden de construcción: 1) alimentación, 2) tierra, 3) señales. | **En código:** `builder._ordered_colored_wires` agrupa en ese orden (0 alimentación, 1 tierra, 2 señal) y ordena por primer extremo dentro de cada grupo, para que el ruteo sea estable. |
| 2 | Colores: tierra negro; 5V/3V3 rojo; señales en paleta rotativa, sin repetir el color del vecino. | **En código:** `builder._wire_group` decide por extremo (5V/riel `T+`/`B+`/fuente → rojo; GND/riel `T-`/`B-` → negro; resto → paleta). Un terminal `+` solo cuenta como alimentación si la parte es fuente real (fase 37). |
| 3 | Ruteo ortogonal: cables en ángulo recto, sin diagonales largas. Uno↔placa: cada cable baja/sube a su propio carril y no pasa sobre otro componente. | **En código:** el puente rutea los cables Uno↔hueco, Uno↔riel y parte-libre↔placa con `addPoint` (fase 22/36). **Bandas por lado (fase 39):** `sideLanes.top/bottom`, base 115 y paso 8; el lado lo decide el hueco (filas f..j y riel `T` arriba, e..a y `B` abajo) o la `y` de la parte libre. Cada banda crece por su cuenta. |
| 4 | Cables cortos dentro de la placa: rectos, por el hueco más cercano, sin rodeos. | **En código** para nets de 2 extremos (se dejan tal cual). Las de 3+ extremos van en estrella desde el hub: un cable hueco↔hueco lo dibuja recto el simulador y cruza los cuerpos. |
| 5 | Separación en layout: 6 columnas por bloque LED+resistencia; bloques de 3 pines ocupan 3 columnas + 1 libre de separación; ningún bloque comparte columna de inicio con otro. | **En código:** `layout.BLOCK_WIDTH=6`, `THREE_PIN_WIDTH=4`, cursor compartido. Las resistencias del banco de la segunda placa van cada 4 columnas (`SECOND_BOARD_COLUMN_STEP`). |
| 6 | Rieles: con más de 2 conexiones al mismo punto, usar riel: `T-` para tierra y `T+` para 5V, en vez de cables sueltos repetidos al Uno. | **En código (opt-in):** `"wiring": "rails"` en la fixture. Cada terminal baja al riel de su misma columna, el Uno lo alimenta una vez y los dos rieles del mismo tipo se puentean en la columna 30. Una parte de la segunda placa nunca baja al riel de la primera: va directa al pin del Uno. |
| 7 | Cada mazo en su zona: lo que alimenta al Uno y lo que sale del display no comparten banda. | **En código (fase 39):** la banda superior y la inferior tienen contadores separados. En el banco vertical de resistencias, el pin de abajo recibe el cable del Uno (banda inferior) y el de arriba alimenta el display (banda superior). |

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
- Cada cable del Uno baja/sube a su carril sin pasar sobre otro componente.
- Cables repartidos arriba y abajo; no todos por la misma zona.
- Sin cruces innecesarios; colores según regla 2; rieles según regla 6.
- **Ningún componente revienta en simulación.** Un display que estalla sigue
  contando: el serial no es prueba de validez eléctrica.

Si no cumple, no se da por terminado aunque simule bien.

## Qué NO hacemos todavía

- Ruteo automático de cables placa↔placa largos (el de 5V/GND al display cruza
  la placa 1 por el carril superior).
- Mover componentes ya colocados: el puente no lo soporta. Si el layout sale mal,
  se reconstruye, no se arrastra.
- Nombres de parte libres de deduplicación: Tinkercad cambia `r2` por `r21` si
  ya existe; por eso la identidad viaja en `placed[ref].name` y no en el nombre.
