# Media suma con compuertas XOR y NAND
- Circuito: https://www.tinkercad.com/things/4z8ZkFcpmuC/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 5,
  "lines": [
    "TEST:LOGICA=LISTO",
    "TEST:HA=0,0,0,0",
    "TEST:HA=0,1,1,0",
    "TEST:HA=1,0,1,0",
    "TEST:HA=1,1,0,1"
  ],
  "raw_output": "TEST:LOGICA=LISTO\nTEST:HA=0,0,0,0\nTEST:HA=0,1,1,0\nTEST:HA=1,0,1,0\nTEST:HA=1,1,0,1",
  "message": "Retrieved 5 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (20 de 20 cables medidos, 18 ruteados).
- Sin tramos diagonales en 20 cables medidos.
- 2 salto(s) recto(s) entre huecos de la placa (max. 70 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.6 | 5.6 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.2 | 11.1 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 16.2 | 16.2 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Media suma con compuertas XOR y NAND
Fixture del cerebro: media-suma-logica
Diseno en Tinkercad: /things/4z8ZkFcpmuC/editel

QUE HACE
  8 piezas y 11 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno    arduino-uno        Arduino Uno R3
  xor1   xor-gate           74HC86 (4 XOR)
  nand1  nand-gate          74HC00 (4 NAND)
  nand2  nand-gate          74HC00 (4 NAND)
  led1   led                LED
  led2   led                LED
  r1     resistor           resistencia
  r2     resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - xor1.Vcc  - nand1.Vcc  - nand2.Vcc
   2. uno.GND1  - xor1.GND  - nand1.GND  - nand2.GND
   3. uno.D2  - xor1.1A  - nand1.1A
   4. uno.D3  - xor1.1B  - nand1.1B
   5. xor1.1Y  - uno.D4  - led1.anode
   6. nand1.1Y  - nand2.1A  - nand2.1B
   7. nand2.1Y  - uno.D5  - led2.anode
   8. led1.cathode  - r1.1
   9. r1.2  - uno.GND1
  10. led2.cathode  - r2.1
  11. r2.2  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: digitalWrite, digitalRead, Serial.
```
