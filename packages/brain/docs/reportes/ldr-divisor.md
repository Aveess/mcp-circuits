# LDR en divisor de tensión con resistencia de 10k en A0 y LED en D13
- Circuito: https://www.tinkercad.com/things/lo9VkvBdWmT/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 43,
  "lines": [
    "READY",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6",
    "TEST:LED=ON",
    "TEST:LUZ=6"
  ],
  "raw_output": "READY\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6\nTEST:LED=ON\nTEST:LUZ=6",
  "message": "Retrieved 43 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (7 de 7 cables medidos, 6 ruteados).
- Sin tramos diagonales en 7 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.5 | 4.5 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.7 | 10.2 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.9 | 15.9 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: LDR en divisor de tensión con resistencia de 10k en A0 y LED en D13
Fixture del cerebro: ldr-divisor
Diseno en Tinkercad: /things/lo9VkvBdWmT/editel

QUE HACE
  5 piezas y 6 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  ldr1  photoresistor      fotorresistencia (LDR)
  r1    resistor           resistencia
  led1  led                LED
  r2    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - ldr1.1
   2. ldr1.2  - uno.A0  - r2.1
   3. r2.2  - uno.GND1
   4. uno.D13  - r1.1
   5. r1.2  - led1.anode
   6. led1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, analogRead, digitalWrite.
```
