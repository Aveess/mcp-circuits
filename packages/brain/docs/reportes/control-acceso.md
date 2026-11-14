# Control de acceso con teclado, LCD y servo
- Circuito: https://www.tinkercad.com/things/cjjQKLuBQ2I/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 3,
  "lines": [
    "TEST:KP=LISTO",
    "TEST:CLAVE=ESPERANDO",
    "TEST:SERVO=0"
  ],
  "raw_output": "TEST:KP=LISTO\nTEST:CLAVE=ESPERANDO\nTEST:SERVO=0",
  "message": "Retrieved 3 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (25 de 25 cables ruteados medidos).

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 6.4 | 6.4 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.0 | 10.6 |
| tinkercad_read_serial_monitor | 1 | 1.3 | 1.3 |
| tinkercad_set_code | 1 | 16.7 | 16.7 |
| tinkercad_start_simulation | 1 | 5.5 | 5.5 |
| tinkercad_stop_simulation | 1 | 1.4 | 1.4 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Control de acceso con teclado, LCD y servo
Fixture del cerebro: control-acceso
Diseno en Tinkercad: /things/cjjQKLuBQ2I/editel

QUE HACE
  5 piezas y 18 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  kp1   keypad-4x4         teclado 4x4
  lcd1  lcd-16x2           LCD 16x2
  sv1   servo              micro servo
  r1    resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D2  - kp1.row1
   2. uno.D3  - kp1.row2
   3. uno.D4  - kp1.row3
   4. uno.D5  - kp1.row4
   5. uno.D6  - kp1.column1
   6. uno.D7  - kp1.column2
   7. uno.D8  - kp1.column3
   8. uno.D9  - kp1.column4
   9. uno.5V  - lcd1.VDD  - r1.1  - sv1.vcc
  10. uno.GND1  - lcd1.GND  - lcd1.VO  - lcd1.RW  - lcd1.LED-  - sv1.gnd
  11. r1.2  - lcd1.LED+
  12. uno.A0  - lcd1.RS
  13. uno.A1  - lcd1.E
  14. uno.A2  - lcd1.DB4
  15. uno.A3  - lcd1.DB5
  16. uno.A4  - lcd1.DB6
  17. uno.A5  - lcd1.DB7
  18. uno.D10  - sv1.signal

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalRead, digitalWrite, INPUT_PULLUP,
 *   LiquidCrystal, Servo, Serial.
```
