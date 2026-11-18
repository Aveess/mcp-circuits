# Sensor de temperatura TMP36 en A0 con LED de alarma en D13
- Circuito: https://www.tinkercad.com/things/2Z7ubKF9ieN/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 9,
  "lines": [
    "READY",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78"
  ],
  "raw_output": "READY\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78",
  "message": "Retrieved 9 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (6 de 6 cables medidos, 5 ruteados).
- Sin tramos diagonales en 6 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.0 | 4.0 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 10.1 | 11.2 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 15.4 | 15.4 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Sensor de temperatura TMP36 en A0 con LED de alarma en D13
Fixture del cerebro: temperatura-tmp36
Diseno en Tinkercad: /things/2Z7ubKF9ieN/editel

QUE HACE
  4 piezas y 6 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  tmp1  tmp36              tmp36
  led1  led                LED
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - tmp1.vcc
   2. tmp1.vout  - uno.A0
   3. tmp1.gnd  - uno.GND1
   4. uno.D13  - r1.1
   5. r1.2  - led1.anode
   6. led1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, analogRead, digitalWrite, Serial.
```
