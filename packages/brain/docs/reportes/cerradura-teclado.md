# Cerradura con teclado 4x4 y dos LEDs
- Circuito: https://www.tinkercad.com/things/g3KZdQc0DFu/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 2,
  "lines": [
    "TEST:KP=LISTO",
    "TEST:CLAVE=ESPERANDO"
  ],
  "raw_output": "TEST:KP=LISTO\nTEST:CLAVE=ESPERANDO",
  "message": "Retrieved 2 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (15 de 15 cables medidos, 11 ruteados).
- Sin tramos diagonales en 15 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.2 | 5.2 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.5 | 10.4 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 16.9 | 16.9 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Cerradura con teclado 4x4 y dos LEDs
Fixture del cerebro: cerradura-teclado
Diseno en Tinkercad: /things/g3KZdQc0DFu/editel

QUE HACE
  6 piezas y 14 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  kp1   keypad-4x4         teclado 4x4
  r1    resistor           resistencia
  led1  led                LED
  r2    resistor           resistencia
  led2  led                LED

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D2  - kp1.row1
   2. uno.D3  - kp1.row2
   3. uno.D4  - kp1.row3
   4. uno.D5  - kp1.row4
   5. uno.D6  - kp1.column1
   6. uno.D7  - kp1.column2
   7. uno.D8  - kp1.column3
   8. uno.D9  - kp1.column4
   9. uno.D10  - r1.1
  10. r1.2  - led1.anode
  11. led1.cathode  - uno.GND1
  12. uno.D11  - r2.1
  13. r2.2  - led2.anode
  14. led2.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalRead, digitalWrite, INPUT_PULLUP,
 *   Serial.
```
