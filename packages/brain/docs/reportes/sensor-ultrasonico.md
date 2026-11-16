# Sensor ultrasónico HC-SR04 (Trig D7, Echo D6) con LED de proximidad
- Circuito: https://www.tinkercad.com/things/2ly9vcxYUyc/editel

## Verificación
- Fidelidad: 0.0%
- Componentes: 0.0% / Conectividad: 0.0%
- Build: **no se aplicó** (ver Fallos); lo que sigue mide el circuito que ya estaba en el editor, no uno nuevo.
- Simulación: {
  "success": true,
  "total_lines": 0,
  "lines": [],
  "raw_output": "",
  "message": "Retrieved 0 lines from Serial Monitor."
}

## Oráculo
- Sin marcas declaradas; el sketch imprime (7 líneas).

## Ruteo
- Sin tramos sobre el cuerpo de una placa (0 de 7 cables medidos, 0 ruteados).
- Sin tramos diagonales en 0 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 30.0 | 30.0 |
| tinkercad_inspect_circuit | 1 | 8.1 | 8.1 |
| tinkercad_open_circuit | 2 | 26.2 | 26.8 |
| tinkercad_read_serial_monitor | 1 | 0.2 | 0.2 |
| tinkercad_set_code | 1 | 20.9 | 20.9 |
| tinkercad_set_component_property_model | 1 | 24.5 | 24.5 |
| tinkercad_start_simulation | 1 | 0.1 | 0.1 |
| tinkercad_stop_simulation | 1 | 0.1 | 0.1 |

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
