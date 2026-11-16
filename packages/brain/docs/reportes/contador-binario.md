# Contador binario 4 bits 74HC93 con LEDs
- Circuito: https://www.tinkercad.com/things/fCB0eO8cBbn/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 18,
  "lines": [
    "TEST:CONTADOR=LISTO",
    "TEST:CONTADOR=1",
    "TEST:CONTADOR=2",
    "TEST:CONTADOR=3",
    "TEST:CONTADOR=4",
    "TEST:CONTADOR=5",
    "TEST:CONTADOR=6",
    "TEST:CONTADOR=7",
    "TEST:CONTADOR=8",
    "TEST:CONTADOR=9",
    "TEST:CONTADOR=10",
    "TEST:CONTADOR=11",
    "TEST:CONTADOR=12",
    "TEST:CONTADOR=13",
    "TEST:CONTADOR=14",
    "TEST:CONTADOR=15",
    "TEST:CONTADOR=0",
    "TEST:CONTADOR=FIN"
  ],
  "raw_output": "TEST:CONTADOR=LISTO\nTEST:CONTADOR=1\nTEST:CONTADOR=2\nTEST:CONTADOR=3\nTEST:CONTADOR=4\nTEST:CONTADOR=5\nTEST:CONTADOR=6\nTEST:CONTADOR=7\nTEST:CONTADOR=8\nTEST:CONTADOR=9\nTEST:CONTADOR=10\nTEST:CONTADOR=11\nTEST:CONTADOR=12\nTEST:CONTADOR=13\nTEST:CONTADOR=14\nTEST:CONTADOR=15\nTEST:CONTADOR=0\nTEST:CONTADOR=FIN",
  "message": "Retrieved 18 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (22 de 22 cables medidos, 18 ruteados).
- Sin tramos diagonales en 22 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 9.2 | 9.2 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.5 | 11.7 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.7 | 15.7 |
| tinkercad_start_simulation | 1 | 5.8 | 5.8 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador binario 4 bits 74HC93 con LEDs
Fixture del cerebro: contador-binario
Diseno en Tinkercad: /things/fCB0eO8cBbn/editel

QUE HACE
  10 piezas y 12 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  n1    binary-counter     74HC93 (contador binario)
  led1  led                LED
  led2  led                LED
  led3  led                LED
  led4  led                LED
  r1    resistor           resistencia
  r2    resistor           resistencia
  r3    resistor           resistencia
  r4    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - n1.Vcc
   2. uno.GND1
      - n1.GND
      - led1.cathode
      - led2.cathode
      - led3.cathode
      - led4.cathode
   3. uno.D3  - n1.MR1  - n1.MR2
   4. uno.D2  - n1.CP0
   5. n1.Q0  - n1.CP1  - uno.D4  - r1.1
   6. n1.Q1  - uno.D5  - r2.1
   7. n1.Q2  - uno.D6  - r3.1
   8. n1.Q3  - uno.D7  - r4.1
   9. r1.2  - led1.anode
  10. r2.2  - led2.anode
  11. r3.2  - led3.anode
  12. r4.2  - led4.anode

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: digitalWrite, digitalRead, Serial.
```
