# Motor DC con transistor NPN, resistencia de base y diodo flyback
- Circuito: https://www.tinkercad.com/things/73azwj2IJDE/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 4,
  "lines": [
    "READY",
    "TEST:MOTOR=ON",
    "TEST:MOTOR=OFF",
    "TEST:MOTOR=ON"
  ],
  "raw_output": "READY\nTEST:MOTOR=ON\nTEST:MOTOR=OFF\nTEST:MOTOR=ON",
  "message": "Retrieved 4 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (7 de 7 cables medidos, 6 ruteados).
- Sin tramos diagonales en 7 cables medidos.
- 1 salto(s) recto(s) entre huecos de la placa (max. 60 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.3 | 5.3 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.6 | 11.0 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 16.6 | 16.6 |
| tinkercad_start_simulation | 1 | 5.7 | 5.7 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Motor DC con transistor NPN, resistencia de base y diodo flyback
Fixture del cerebro: motor-dc-transistor
Diseno en Tinkercad: /things/73azwj2IJDE/editel

QUE HACE
  5 piezas y 5 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno     arduino-uno        Arduino Uno R3
  motor1  dc-motor           motor DC
  q1      transistor-npn     transistor-npn
  d1      diode              diode
  r1      resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D9  - r1.1
   2. r1.2  - q1.base
   3. q1.emitter  - uno.GND1
   4. q1.collector  - motor1.negative  - d1.anode
   5. motor1.positive  - uno.5V  - d1.cathode

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, analogWrite.
```
