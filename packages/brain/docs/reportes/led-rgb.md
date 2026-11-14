# LED RGB de cátodo común con PWM en D9, D10 y D11
- Circuito: https://www.tinkercad.com/things/i525BUubYAE/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 6,
  "lines": [
    "READY",
    "TEST:COLOR=RED",
    "TEST:COLOR=GREEN",
    "TEST:COLOR=BLUE",
    "TEST:COLOR=RED",
    "TEST:COLOR=GREEN"
  ],
  "raw_output": "READY\nTEST:COLOR=RED\nTEST:COLOR=GREEN\nTEST:COLOR=BLUE\nTEST:COLOR=RED\nTEST:COLOR=GREEN",
  "message": "Retrieved 6 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (7 de 7 cables medidos, 4 ruteados).
- Sin tramos diagonales en 7 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.3 | 4.3 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 8.9 | 10.1 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.6 | 15.6 |
| tinkercad_start_simulation | 1 | 5.3 | 5.3 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: LED RGB de cátodo común con PWM en D9, D10 y D11
Fixture del cerebro: led-rgb
Diseno en Tinkercad: /things/i525BUubYAE/editel

QUE HACE
  5 piezas y 7 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  rgb1  led-rgb-common-cathode led-rgb-common-cathode
  r1    resistor           resistencia
  r2    resistor           resistencia
  r3    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D9  - r1.1
   2. r1.2  - rgb1.red
   3. uno.D10  - r2.1
   4. r2.2  - rgb1.green
   5. uno.D11  - r3.1
   6. r3.2  - rgb1.blue
   7. rgb1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, analogWrite.
```
