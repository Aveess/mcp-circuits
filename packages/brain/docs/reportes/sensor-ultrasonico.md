# Sensor ultrasónico HC-SR04 (Trig D7, Echo D6) con LED de proximidad
- Circuito: https://www.tinkercad.com/things/2ly9vcxYUyc/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 37,
  "lines": [
    "READY",
    "TEST:DIST=7.29",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON",
    "TEST:DIST=7.50",
    "TEST:LED=ON",
    "TEST:DIST=7.65",
    "TEST:LED=ON",
    "TEST:DIST=7.46",
    "TEST:LED=ON"
  ],
  "raw_output": "READY\nTEST:DIST=7.29\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON\nTEST:DIST=7.50\nTEST:LED=ON\nTEST:DIST=7.65\nTEST:LED=ON\nTEST:DIST=7.46\nTEST:LED=ON",
  "message": "Retrieved 37 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (7 de 7 cables medidos, 6 ruteados).
- Sin tramos diagonales en 7 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.7 | 4.7 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 8.8 | 9.7 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.5 | 15.5 |
| tinkercad_set_component_property_model | 1 | 1.2 | 1.2 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.4 | 1.4 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Sensor ultrasónico HC-SR04 (Trig D7, Echo D6) con LED de proximidad
Fixture del cerebro: sensor-ultrasonico
Diseno en Tinkercad: /things/2ly9vcxYUyc/editel

QUE HACE
  4 piezas y 7 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  us1   ultrasonic-hcsr04  ultrasonic-hcsr04
  led1  led                LED
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - us1.vcc
   2. us1.gnd  - uno.GND1
   3. uno.D7  - us1.trig
   4. uno.D6  - us1.echo
   5. uno.D13  - r1.1
   6. r1.2  - led1.anode
   7. led1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalWrite, pulseIn, digitalRead.
```
