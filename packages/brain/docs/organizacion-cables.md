# Organización de cableado

Guía operativa para todo circuito construido por el proyecto, desde el más fácil.
Estado = qué hace hoy el código; **Aspiracional** = regla vigente al diseñar/revisar,
aún no implementada en código.

## Reglas

| # | Regla | Estado hoy |
|---|---|---|
| 1 | Orden de construcción: 1) alimentación, 2) tierra, 3) señales. | Aspiracional: `builder.py:160-169` emite los wires en el orden de las `nets` de la fixture, sin reordenar. Escribir las nets en ese orden. |
| 2 | Colores: tierra negro; 5V/3V3 rojo; señales en paleta rotativa, sin repetir el color del vecino. | Aspiracional: `builder.py` no emite color (wires = solo par de extremos). Aplicar al revisar/ajustar en Tinkercad. |
| 3 | Ruteo ortogonal: cables en ángulo recto, sin diagonales largas. Uno↔placa: cada cable baja/sube a su propio carril y no pasa sobre otro componente. | Aspiracional: no hay ruteo ni geometría en `builder.py`; el puente dibuja entre extremos. Se controla por layout (regla 5) y revisión visual. |
| 4 | Cables cortos dentro de la placa: rectos, por el hueco más cercano, sin rodeos. | Aspiracional (misma causa que 3). |
| 5 | Separación en layout: 6 columnas por bloque LED+resistencia; bloques de 3 pines ocupan 3 columnas + 1 libre de separación; ningún bloque comparte columna de inicio con otro. | **En código:** `layout.py:7` (`BLOCK_WIDTH=6`), `layout.py:16-17,146` (`THREE_PIN_WIDTH=4`), cursor compartido en `layout.py:109-148`. |
| 6 | Rieles: con más de 2 conexiones al mismo punto, usar riel: `T-` para tierra y `T+` para 5V, en vez de cables sueltos repetidos al Uno. | Parcial: la sintaxis de rieles `T+/T-/B+/B-` (columna opcional) está validada en `spec.py:5-6,80` y las nets por riel se derivan en `breadboard_nets.py`. Aspiracional: `builder.py` no colapsa nets a rieles automáticamente; hay que declararlo en la fixture/spec. |

## Por qué

- Legibilidad: quien abre el diseño en Tinkercad entiende alimentación, tierra y
  señales de un vistazo, sin seguir cada cable.
- Errores visibles: en circuitos difíciles, un cable cruzado esconde un corto.
  Si todo va ortogonal y por su carril, el cable que cruza es el sospechoso.

## Criterio de aceptación visual

En el screenshot del circuito terminado:

- Sin diagonales largas cruzando componentes.
- Cada cable del Uno baja/sube a su carril sin pasar sobre otro componente.
- Sin cruces innecesarios; colores según regla 2; rieles según regla 6.

Si no cumple, no se da por terminado aunque simule bien.

## Qué NO hacemos todavía

- Ruteo automático de cables placa↔placa largos.
- Mover componentes ya colocados: el puente no lo soporta. Si el layout sale mal,
  se reconstruye, no se arrastra.
