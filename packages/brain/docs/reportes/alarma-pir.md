# Alarma de movimiento con PIR, buzzer y LED
- Circuito: https://www.tinkercad.com/things/dgFz6r0k1xV/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 2,
  "lines": [
    "TEST:PIR=LISTO",
    "TEST:MOV=0"
  ],
  "raw_output": "TEST:PIR=LISTO\nTEST:MOV=0",
  "message": "Retrieved 2 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (10 de 10 cables medidos, 6 ruteados).
- Sin tramos diagonales en 10 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.4 | 4.4 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 11.1 | 12.0 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.4 | 15.4 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Alarma de movimiento con PIR, buzzer y LED
Fixture del cerebro: alarma-pir
Diseno en Tinkercad: /things/dgFz6r0k1xV/editel

QUE HACE
  5 piezas y 8 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno      arduino-uno        Arduino Uno R3
  pir1     pir-sensor         sensor PIR
  buzzer1  buzzer             piezo / buzzer
  r1       resistor           resistencia
  led1     led                LED

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - pir1.vcc
   2. pir1.gnd  - uno.GND1
   3. uno.D2  - pir1.out
   4. uno.D3  - buzzer1.positive
   5. buzzer1.negative  - uno.GND1
   6. uno.D4  - r1.1
   7. r1.2  - led1.anode
   8. led1.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalRead, digitalWrite, tone, Serial.
```
