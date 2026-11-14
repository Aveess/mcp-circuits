# Pantalla LCD 16x2 en modo 4 bits con contador de segundos
- Circuito: https://www.tinkercad.com/things/cpySiVSE9vr/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 5,
  "lines": [
    "TEST:LCD=LISTO",
    "TEST:SEG=1",
    "TEST:SEG=2",
    "TEST:SEG=3",
    "TEST:SEG=4"
  ],
  "raw_output": "TEST:LCD=LISTO\nTEST:SEG=1\nTEST:SEG=2\nTEST:SEG=3\nTEST:SEG=4",
  "message": "Retrieved 5 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (13 de 13 cables ruteados medidos).

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.8 | 4.8 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.6 | 9.9 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 15.8 | 15.8 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Pantalla LCD 16x2 en modo 4 bits con contador de segundos
Fixture del cerebro: lcd-contador
Diseno en Tinkercad: /things/cpySiVSE9vr/editel

QUE HACE
  3 piezas y 9 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  lcd1  lcd-16x2           LCD 16x2
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - lcd1.VDD  - r1.1
   2. lcd1.GND  - lcd1.VO  - lcd1.RW  - lcd1.LED-  - uno.GND1
   3. r1.2  - lcd1.LED+
   4. uno.D12  - lcd1.RS
   5. uno.D11  - lcd1.E
   6. uno.D5  - lcd1.DB4
   7. uno.D4  - lcd1.DB5
   8. uno.D3  - lcd1.DB6
   9. uno.D2  - lcd1.DB7

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: LiquidCrystal, begin, print, setCursor, Serial.
```
