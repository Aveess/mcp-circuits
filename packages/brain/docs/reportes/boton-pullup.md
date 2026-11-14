# Botón con pull-up interno en D2 y LED indicador en D13
- Circuito: https://www.tinkercad.com/things/lp8O5143UNj/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 1,
  "lines": [
    "READY"
  ],
  "raw_output": "READY",
  "message": "Retrieved 1 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (5 de 5 cables medidos, 4 ruteados).
- Sin tramos diagonales en 5 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.6 | 5.6 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 9.6 | 10.8 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.9 | 15.9 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Botón con pull-up interno en D2 y LED indicador en D13
Fixture del cerebro: boton-pullup
Diseno en Tinkercad: /things/lp8O5143UNj/editel

QUE HACE
  4 piezas y 5 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  btn1  pushbutton         pulsador
  led1  led                LED
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D2  - btn1.1
   2. btn1.2  - uno.GND1
   3. uno.D13  - r1.1
   4. r1.2  - led1.anode
   5. led1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, INPUT_PULLUP, digitalRead, digitalWrite.
```
