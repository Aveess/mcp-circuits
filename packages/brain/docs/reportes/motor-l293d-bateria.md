# Motor DC con driver L293D y batería de 9V, velocidad por potenciómetro en A0
- Circuito: https://www.tinkercad.com/things/kJPyfC1VQaM/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 19,
  "lines": [
    "READY",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255",
    "TEST:SPEED=255"
  ],
  "raw_output": "READY\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255\nTEST:SPEED=255",
  "message": "Retrieved 19 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (12 de 12 cables medidos, 12 ruteados).
- Sin tramos diagonales en 12 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.7 | 5.7 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.0 | 11.1 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 16.0 | 16.0 |
| tinkercad_start_simulation | 1 | 5.6 | 5.6 |
| tinkercad_stop_simulation | 1 | 1.5 | 1.5 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Motor DC con driver L293D y batería de 9V, velocidad por potenciómetro en A0
Fixture del cerebro: motor-l293d-bateria
Diseno en Tinkercad: /things/kJPyfC1VQaM/editel

QUE HACE
  5 piezas y 11 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno     arduino-uno        Arduino Uno R3
  drv1    l293d              l293d
  bat1    battery-9v         bateria 9V
  motor1  dc-motor           motor DC
  pot1    potentiometer      potenciometro

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D9  - drv1.enable1
   2. uno.D7  - drv1.input1
   3. uno.D8  - drv1.input2
   4. uno.5V  - drv1.vss
   5. uno.GND1  - drv1.gnd  - bat1.negative
   6. bat1.positive  - drv1.vs
   7. drv1.output1  - motor1.positive
   8. drv1.output2  - motor1.negative
   9. uno.5V  - pot1.1
  10. pot1.2  - uno.A0
  11. pot1.3  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalWrite, analogWrite, analogRead.
```
