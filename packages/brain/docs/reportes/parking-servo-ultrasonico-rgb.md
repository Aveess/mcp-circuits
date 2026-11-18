# Barrera de estacionamiento: HC-SR04 mide, servo abre, RGB indica estado
- Circuito: https://www.tinkercad.com/things/2xxjwQBZuOH/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 52,
  "lines": [
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=110.53",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=110.57",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=110.57",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=111.33",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=111.33",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.05",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.05",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.10",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=112.08",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90",
    "TEST:DIST=111.33",
    "TEST:ESTADO=ABIERTO",
    "TEST:SERVO=90"
  ],
  "raw_output": "TEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=110.53\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=110.57\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=110.57\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=111.33\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=111.33\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.05\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.05\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.10\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=112.08\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90\nTEST:DIST=111.33\nTEST:ESTADO=ABIERTO\nTEST:SERVO=90",
  "message": "Retrieved 50 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (14 de 14 cables medidos, 11 ruteados).
- Sin tramos diagonales en 14 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.4 | 5.4 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.8 | 10.2 |
| tinkercad_read_serial_monitor | 1 | 1.4 | 1.4 |
| tinkercad_set_code | 1 | 15.9 | 15.9 |
| tinkercad_start_simulation | 1 | 5.6 | 5.6 |
| tinkercad_stop_simulation | 1 | 1.6 | 1.6 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Barrera de estacionamiento: HC-SR04 mide, servo abre, RGB indica estado
Fixture del cerebro: parking-servo-ultrasonico-rgb
Diseno en Tinkercad: /things/2xxjwQBZuOH/editel

QUE HACE
  7 piezas y 11 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno     arduino-uno        Arduino Uno R3
  rgb1    led-rgb-common-cathode led-rgb-common-cathode
  r1      resistor           resistencia
  r2      resistor           resistencia
  r3      resistor           resistencia
  servo1  servo              micro servo
  us1     ultrasonic-hcsr04  ultrasonic-hcsr04

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - us1.vcc  - servo1.vcc
   2. us1.gnd  - servo1.gnd  - rgb1.cathode  - uno.GND1
   3. uno.D7  - us1.trig
   4. uno.D6  - us1.echo
   5. uno.D9  - servo1.signal
   6. uno.D10  - r1.1
   7. r1.2  - rgb1.red
   8. uno.D11  - r2.1
   9. r2.2  - rgb1.green
  10. uno.D3  - r3.1
  11. r3.2  - rgb1.blue

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: Servo, pulseIn, write, pinMode, digitalWrite.
```
