# Servo en D9 controlado por potenciómetro en A0
- Circuito: https://www.tinkercad.com/things/9Rpc2a0C6te/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 50,
  "lines": [
    "READY",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180",
    "TEST:ANGLE=180"
  ],
  "raw_output": "READY\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180\nTEST:ANGLE=180",
  "message": "Retrieved 50 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (6 de 6 cables medidos, 6 ruteados).
- Sin tramos diagonales en 6 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 2 | 8.5 | 11.1 |
| tinkercad_inspect_circuit | 6 | 8.1 | 8.1 |
| tinkercad_open_circuit | 3 | 19.3 | 32.3 |
| tinkercad_read_serial_monitor | 1 | 2.3 | 2.3 |
| tinkercad_set_code | 1 | 17.9 | 17.9 |
| tinkercad_start_simulation | 1 | 6.5 | 6.5 |
| tinkercad_stop_simulation | 1 | 2.2 | 2.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Servo en D9 controlado por potenciómetro en A0
Fixture del cerebro: servo-potenciometro
Diseno en Tinkercad: /things/9Rpc2a0C6te/editel

QUE HACE
  3 piezas y 6 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno     arduino-uno        Arduino Uno R3
  servo1  servo              micro servo
  pot1    potentiometer      potenciometro

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D9  - servo1.signal
   2. uno.5V  - servo1.vcc
   3. servo1.gnd  - uno.GND1
   4. uno.5V  - pot1.1
   5. pot1.2  - uno.A0
   6. pot1.3  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: Servo, analogRead, map, write.
```
