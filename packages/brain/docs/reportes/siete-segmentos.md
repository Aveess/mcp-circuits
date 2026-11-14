# Contador 0-9 en display 7 segmentos con 7 resistencias
- Circuito: https://www.tinkercad.com/things/gfgLntRuWJv/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 12,
  "lines": [
    "TEST:7SEG=LISTO",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7",
    "TEST:DIGITO=8",
    "TEST:DIGITO=9",
    "TEST:DIGITO=0"
  ],
  "raw_output": "TEST:7SEG=LISTO\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7\nTEST:DIGITO=8\nTEST:DIGITO=9\nTEST:DIGITO=0",
  "message": "Retrieved 12 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (15 de 15 cables ruteados medidos).

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 6.2 | 6.2 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.6 | 10.7 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 17.0 | 17.0 |
| tinkercad_start_simulation | 1 | 5.5 | 5.5 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador 0-9 en display 7 segmentos con 7 resistencias
Fixture del cerebro: siete-segmentos
Diseno en Tinkercad: /things/gfgLntRuWJv/editel

QUE HACE
  9 piezas y 15 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno  arduino-uno        Arduino Uno R3
  seg  seven-segment      display 7 segmentos
  r1   resistor           resistencia
  r2   resistor           resistencia
  r3   resistor           resistencia
  r4   resistor           resistencia
  r5   resistor           resistencia
  r6   resistor           resistencia
  r7   resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D2  - r1.1
   2. r1.2  - seg.a
   3. uno.D3  - r2.1
   4. r2.2  - seg.b
   5. uno.D4  - r3.1
   6. r3.2  - seg.c
   7. uno.D5  - r4.1
   8. r4.2  - seg.d
   9. uno.D6  - r5.1
  10. r5.2  - seg.e
  11. uno.D7  - r6.1
  12. r6.2  - seg.f
  13. uno.D8  - r7.1
  14. r7.2  - seg.g
  15. seg.com1  - uno.5V

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalWrite, Serial, delay.
```
