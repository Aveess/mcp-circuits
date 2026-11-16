# Caja fuerte con teclado 4x4 y LCD 16x2
- Circuito: https://www.tinkercad.com/things/9wyFlvHHzIo/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 2,
  "lines": [
    "TEST:KP=LISTO",
    "TEST:CLAVE=ESPERANDO"
  ],
  "raw_output": "TEST:KP=LISTO\nTEST:CLAVE=ESPERANDO",
  "message": "Retrieved 2 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (23 de 23 cables medidos, 22 ruteados).
- Sin tramos diagonales en 23 cables medidos.
- 1 salto(s) recto(s) entre huecos de la placa (max. 60 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.8 | 5.8 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 9.4 | 10.0 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 15.4 | 15.4 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Caja fuerte con teclado 4x4 y LCD 16x2
Fixture del cerebro: clave-lcd
Diseno en Tinkercad: /things/9wyFlvHHzIo/editel

QUE HACE
  4 piezas y 17 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  kp1   keypad-4x4         teclado 4x4
  lcd1  lcd-16x2           LCD 16x2
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
   9. uno.5V  - lcd1.VDD  - r1.1
  10. uno.GND1  - lcd1.GND  - lcd1.VO  - lcd1.RW  - lcd1.LED-
  11. r1.2  - lcd1.LED+
  12. uno.A0  - lcd1.RS
  13. uno.A1  - lcd1.E
  14. uno.A2  - lcd1.DB4
  15. uno.A3  - lcd1.DB5
  16. uno.A4  - lcd1.DB6
  17. uno.A5  - lcd1.DB7

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalRead, digitalWrite, INPUT_PULLUP,
 *   LiquidCrystal, Serial.
```
