# Medidor de distancia con LCD 16x2 y alarma sonora
- Circuito: https://www.tinkercad.com/things/blN5d8qCr2z/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 19,
  "lines": [
    "TEST:LCD=LISTO",
    "TEST:DIST=110.3",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.1",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.3",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.1",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.3",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.1",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.2",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.3",
    "TEST:ALARMA=ON",
    "TEST:DIST=110.1",
    "TEST:ALARMA=ON"
  ],
  "raw_output": "TEST:LCD=LISTO\nTEST:DIST=110.3\nTEST:ALARMA=ON\nTEST:DIST=110.1\nTEST:ALARMA=ON\nTEST:DIST=110.3\nTEST:ALARMA=ON\nTEST:DIST=110.1\nTEST:ALARMA=ON\nTEST:DIST=110.3\nTEST:ALARMA=ON\nTEST:DIST=110.1\nTEST:ALARMA=ON\nTEST:DIST=110.2\nTEST:ALARMA=ON\nTEST:DIST=110.3\nTEST:ALARMA=ON\nTEST:DIST=110.1\nTEST:ALARMA=ON",
  "message": "Retrieved 19 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (19 de 19 cables medidos, 19 ruteados).
- Sin tramos diagonales en 19 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 6.5 | 6.5 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 10.0 | 10.8 |
| tinkercad_read_serial_monitor | 1 | 1.4 | 1.4 |
| tinkercad_set_code | 1 | 16.1 | 16.1 |
| tinkercad_start_simulation | 1 | 5.7 | 5.7 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Medidor de distancia con LCD 16x2 y alarma sonora
Fixture del cerebro: lcd-distancia
Diseno en Tinkercad: /things/blN5d8qCr2z/editel

QUE HACE
  5 piezas y 12 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno      arduino-uno        Arduino Uno R3
  us1      ultrasonic-hcsr04  ultrasonic-hcsr04
  lcd1     lcd-16x2           LCD 16x2
  r1       resistor           resistencia
  buzzer1  buzzer             piezo / buzzer

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - lcd1.VDD  - r1.1  - us1.vcc
   2. lcd1.GND
      - lcd1.VO
      - lcd1.RW
      - lcd1.LED-
      - us1.gnd
      - buzzer1.negative
      - uno.GND1
   3. r1.2  - lcd1.LED+
   4. uno.D12  - lcd1.RS
   5. uno.D11  - lcd1.E
   6. uno.D5  - lcd1.DB4
   7. uno.D4  - lcd1.DB5
   8. uno.D3  - lcd1.DB6
   9. uno.D2  - lcd1.DB7
  10. uno.D7  - us1.trig
  11. uno.D6  - us1.echo
  12. uno.D8  - buzzer1.positive

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: LiquidCrystal, pulseIn, tone, noTone, print, Serial.
```
