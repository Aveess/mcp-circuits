# Contador 0-9 con 74HC595 y display 7 segmentos
- Circuito: https://www.tinkercad.com/things/kBGbtwAbFlz/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 11,
  "lines": [
    "TEST:595=LISTO",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7",
    "TEST:DIGITO=8",
    "TEST:DIGITO=9"
  ],
  "raw_output": "TEST:595=LISTO\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7\nTEST:DIGITO=8\nTEST:DIGITO=9",
  "message": "Retrieved 11 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (22 de 22 cables medidos, 22 ruteados).
- Sin tramos diagonales en 22 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 6.9 | 6.9 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.9 | 12.2 |
| tinkercad_read_serial_monitor | 1 | 1.4 | 1.4 |
| tinkercad_set_code | 1 | 15.7 | 15.7 |
| tinkercad_start_simulation | 1 | 5.5 | 5.5 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador 0-9 con 74HC595 y display 7 segmentos
Fixture del cerebro: desplazador-595
Diseno en Tinkercad: /things/kBGbtwAbFlz/editel

QUE HACE
  10 piezas y 20 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno  arduino-uno        Arduino Uno R3
  ic   shift-register     74HC595 (registro de desplazamiento)
  seg  seven-segment      display 7 segmentos
  r1   resistor           resistencia
  r2   resistor           resistencia
  r3   resistor           resistencia
  r4   resistor           resistencia
  r5   resistor           resistencia
  r6   resistor           resistencia
  r7   resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - ic.Vcc  - ic.MR
   2. ic.GND  - ic.OE  - uno.GND1
   3. uno.D11  - ic.DS
   4. uno.D8  - ic.SHCP
   5. uno.D12  - ic.STCP
   6. ic.Q0  - r1.1
   7. r1.2  - seg.a
   8. ic.Q1  - r2.1
   9. r2.2  - seg.b
  10. ic.Q2  - r3.1
  11. r3.2  - seg.c
  12. ic.Q3  - r4.1
  13. r4.2  - seg.d
  14. ic.Q4  - r5.1
  15. r5.2  - seg.e
  16. ic.Q5  - r6.1
  17. r6.2  - seg.f
  18. ic.Q6  - r7.1
  19. r7.2  - seg.g
  20. seg.com1  - uno.5V

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: shiftOut, digitalWrite, Serial, delay.
```
