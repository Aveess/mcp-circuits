# Biestable D 74HC74 como divisor por 2
- Circuito: https://www.tinkercad.com/things/euU4CI6HwhX/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 10,
  "lines": [
    "TEST:FF=LISTO",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=TOGGLE-OK"
  ],
  "raw_output": "TEST:FF=LISTO\nTEST:FF=1\nTEST:FF=0\nTEST:FF=1\nTEST:FF=0\nTEST:FF=1\nTEST:FF=0\nTEST:FF=1\nTEST:FF=0\nTEST:FF=TOGGLE-OK",
  "message": "Retrieved 10 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (14 de 14 cables medidos, 13 ruteados).
- Sin tramos diagonales en 14 cables medidos.
- 1 salto(s) recto(s) entre huecos de la placa (max. 20 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.2 | 4.2 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 9.6 | 10.3 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.9 | 15.9 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Biestable D 74HC74 como divisor por 2
Fixture del cerebro: biestable-d
Diseno en Tinkercad: /things/euU4CI6HwhX/editel

QUE HACE
  4 piezas y 7 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  ff    flip-flop-d        74HC74 (biestable D)
  led1  led                LED
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - ff.Vcc  - ff.1RD  - ff.1SD  - ff.2RD  - ff.2SD
   2. uno.GND1  - ff.GND  - ff.2D  - ff.2CP
   3. uno.D2  - ff.1CP
   4. ff.1NQ  - ff.1D
   5. ff.1Q  - uno.D4  - led1.anode
   6. led1.cathode  - r1.1
   7. r1.2  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: digitalWrite, digitalRead, Serial.
```
