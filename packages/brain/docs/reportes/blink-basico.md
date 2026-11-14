# Blink básico: LED en D13 con resistencia en serie
- Circuito: https://www.tinkercad.com/things/2tMhkuosDyj/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 10,
  "lines": [
    "READY",
    "TEST:ON",
    "TEST:OFF",
    "TEST:ON",
    "TEST:OFF",
    "TEST:ON",
    "TEST:OFF",
    "TEST:ON",
    "TEST:OFF",
    "TEST:ON"
  ],
  "raw_output": "READY\nTEST:ON\nTEST:OFF\nTEST:ON\nTEST:OFF\nTEST:ON\nTEST:OFF\nTEST:ON\nTEST:OFF\nTEST:ON",
  "message": "Retrieved 10 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (3 de 3 cables medidos, 2 ruteados).
- Sin tramos diagonales en 3 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 3.7 | 3.7 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.9 | 11.5 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.8 | 15.8 |
| tinkercad_start_simulation | 1 | 5.5 | 5.5 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Blink básico: LED en D13 con resistencia en serie
Fixture del cerebro: blink-basico
Diseno en Tinkercad: /things/2tMhkuosDyj/editel

QUE HACE
  3 piezas y 3 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  led1  led                LED
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D13  - r1.1
   2. r1.2  - led1.anode
   3. led1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalWrite, delay.
```
