# Faro automatico con rele SPDT, NPN y LDR
- Circuito: https://www.tinkercad.com/things/aF67dwSGoqC/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 16,
  "lines": [
    "TEST:FARO=LISTO",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:RELE=OFF",
    "TEST:FOCO=0",
    "TEST:FARO=FIN"
  ],
  "raw_output": "TEST:FARO=LISTO\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:RELE=OFF\nTEST:FOCO=0\nTEST:FARO=FIN",
  "message": "Retrieved 16 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (19 de 19 cables medidos, 12 ruteados).
- Sin tramos diagonales en 19 cables medidos.
- 1 salto(s) recto(s) entre huecos de la placa (max. 60 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 6.8 | 6.8 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.1 | 10.4 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.5 | 15.5 |
| tinkercad_start_simulation | 1 | 5.6 | 5.6 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Faro automatico con rele SPDT, NPN y LDR
Fixture del cerebro: faro-rele-ldr
Diseno en Tinkercad: /things/aF67dwSGoqC/editel

QUE HACE
  8 piezas y 11 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno    arduino-uno        Arduino Uno R3
  ldr1   photoresistor      fotorresistencia (LDR)
  r1     resistor           resistencia
  r2     resistor           resistencia
  q1     transistor-npn     transistor-npn
  d1     diode              diode
  k1     relay-spdt         rele SPDT
  lamp1  light-bulb         bombilla

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - ldr1.1
   2. ldr1.2  - uno.A0  - r1.1
   3. r1.2  - uno.GND1
   4. uno.D2  - r2.1
   5. r2.2  - q1.base
   6. q1.emitter  - uno.GND1
   7. q1.collector  - k1.COIL2  - d1.anode
   8. k1.COIL1  - uno.5V  - d1.cathode
   9. uno.5V  - k1.COM1
  10. k1.R1  - lamp1.1  - uno.A1
  11. lamp1.2  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: analogRead, digitalWrite, Serial.
```
