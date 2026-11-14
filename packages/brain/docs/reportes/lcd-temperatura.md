# Termometro TMP36 en pantalla LCD 16x2 en modo 4 bits
- Circuito: https://www.tinkercad.com/things/9hZJgbsYOC5/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 9,
  "lines": [
    "TEST:LCD=LISTO",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78",
    "TEST:TEMP=24.78"
  ],
  "raw_output": "TEST:LCD=LISTO\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78\nTEST:TEMP=24.78",
  "message": "Retrieved 9 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (16 de 16 cables medidos, 16 ruteados).
- Sin tramos diagonales en 16 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.5 | 4.5 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.1 | 10.4 |
| tinkercad_read_serial_monitor | 1 | 1.3 | 1.3 |
| tinkercad_set_code | 1 | 15.9 | 15.9 |
| tinkercad_start_simulation | 1 | 5.5 | 5.5 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Termometro TMP36 en pantalla LCD 16x2 en modo 4 bits
Fixture del cerebro: lcd-temperatura
Diseno en Tinkercad: /things/9hZJgbsYOC5/editel

QUE HACE
  4 piezas y 10 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  tmp1  tmp36              tmp36
  lcd1  lcd-16x2           LCD 16x2
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - lcd1.VDD  - r1.1  - tmp1.vcc
   2. lcd1.GND  - lcd1.VO  - lcd1.RW  - lcd1.LED-  - tmp1.gnd  - uno.GND1
   3. r1.2  - lcd1.LED+
   4. uno.D12  - lcd1.RS
   5. uno.D11  - lcd1.E
   6. uno.D5  - lcd1.DB4
   7. uno.D4  - lcd1.DB5
   8. uno.D3  - lcd1.DB6
   9. uno.D2  - lcd1.DB7
  10. tmp1.vout  - uno.A0

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: LiquidCrystal, analogRead, print, setCursor, Serial.
```
