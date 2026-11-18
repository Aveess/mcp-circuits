# Botón con pull-up interno en D2 y LED indicador en D13
- Circuito: https://www.tinkercad.com/things/lp8O5143UNj/editel

## Verificación
- Fidelidad: 0.0% — **no se pudo leer** el circuito en 3 intentos; este porcentaje no mide el cableado
- Componentes: 0.0% / Conectividad: 0.0%
- Simulación: {
  "success": true,
  "total_lines": 0,
  "lines": [],
  "raw_output": "",
  "message": "Retrieved 0 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (5 de 5 cables medidos, 4 ruteados).
- Sin tramos diagonales en 5 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 2 | 38.0 | 63.2 |
| tinkercad_inspect_circuit | 6 | 8.1 | 8.1 |
| tinkercad_open_circuit | 3 | 23.5 | 26.1 |
| tinkercad_read_serial_monitor | 1 | 0.2 | 0.2 |
| tinkercad_set_code | 1 | 21.9 | 21.9 |
| tinkercad_start_simulation | 1 | 0.1 | 0.1 |
| tinkercad_stop_simulation | 1 | 0.1 | 0.1 |

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
