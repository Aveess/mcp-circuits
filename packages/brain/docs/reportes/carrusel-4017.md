# Carrusel de 4 LEDs con 74HC4017
- Circuito: https://www.tinkercad.com/things/ij6ypc8wB5x/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 10,
  "lines": [
    "TEST:4017=LISTO",
    "TEST:4017=1",
    "TEST:4017=2",
    "TEST:4017=3",
    "TEST:4017=0",
    "TEST:4017=1",
    "TEST:4017=2",
    "TEST:4017=3",
    "TEST:4017=0",
    "TEST:4017=FIN"
  ],
  "raw_output": "TEST:4017=LISTO\nTEST:4017=1\nTEST:4017=2\nTEST:4017=3\nTEST:4017=0\nTEST:4017=1\nTEST:4017=2\nTEST:4017=3\nTEST:4017=0\nTEST:4017=FIN",
  "message": "Retrieved 10 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (21 de 21 cables medidos, 17 ruteados).
- Sin tramos diagonales en 21 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.5 | 5.5 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.5 | 10.0 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 15.4 | 15.4 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Carrusel de 4 LEDs con 74HC4017
Fixture del cerebro: carrusel-4017
Diseno en Tinkercad: /things/ij6ypc8wB5x/editel

QUE HACE
  10 piezas y 12 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  n1    decade-counter     4017 (contador de decadas)
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
      - n1.CP1n
      - led1.cathode
      - led2.cathode
      - led3.cathode
      - led4.cathode
   3. n1.Q4  - n1.MR
   4. uno.D2  - n1.CP0
   5. n1.Q0  - uno.D4  - r1.1
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
