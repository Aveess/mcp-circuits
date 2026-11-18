# Temporizador 555 en astable (reloj de ~14 Hz)
- Circuito: https://www.tinkercad.com/things/abIk7XRpSR4/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 5,
  "lines": [
    "TEST:555=LISTO",
    "TEST:555=ALTO,73173",
    "TEST:555=BAJO,427",
    "TEST:555=FREQ,13.6",
    "TEST:555=OK"
  ],
  "raw_output": "TEST:555=LISTO\nTEST:555=ALTO,73173\nTEST:555=BAJO,427\nTEST:555=FREQ,13.6\nTEST:555=OK",
  "message": "Retrieved 5 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (10 de 10 cables medidos, 10 ruteados).
- Sin tramos diagonales en 10 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.2 | 5.2 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 9.9 | 10.8 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.5 | 15.5 |
| tinkercad_set_component_property_model | 2 | 1.1 | 1.3 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Temporizador 555 en astable (reloj de ~14 Hz)
Fixture del cerebro: temporizador-555
Diseno en Tinkercad: /things/abIk7XRpSR4/editel

QUE HACE
  4 piezas y 4 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno  arduino-uno        Arduino Uno R3
  t1   timer-555          temporizador 555
  r1   resistor           resistencia
  c1   capacitor          capacitor

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - t1.Vcc  - t1.Reset  - r1.1
   2. uno.GND1  - t1.GND  - c1.2
   3. r1.2  - t1.DIS  - t1.THR  - t1.TRIG  - c1.1
   4. t1.OUT  - uno.D2

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pulseIn, Serial.
```
