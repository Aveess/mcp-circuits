# Contador 0-7 lento: reloj 555 y compuertas AND/OR/XOR
- Circuito: https://www.tinkercad.com/things/jApuXFjHQsc/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 38,
  "lines": [
    "TEST:COMPUERTAS=LISTO",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4"
  ],
  "raw_output": "TEST:COMPUERTAS=LISTO\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4",
  "message": "Retrieved 38 lines from Serial Monitor."
}

## Ruteo
- Sin tramos sobre el cuerpo de una placa (41 de 41 cables medidos, 39 ruteados).
- Sin tramos diagonales en 41 cables medidos.
- 1 salto(s) recto(s) entre huecos de la placa (max. 60 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 8.1 | 8.1 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.4 | 11.3 |
| tinkercad_read_serial_monitor | 1 | 2.6 | 2.6 |
| tinkercad_set_code | 1 | 16.2 | 16.2 |
| tinkercad_set_component_property_model | 9 | 1.3 | 2.5 |
| tinkercad_start_simulation | 1 | 29.2 | 29.2 |
| tinkercad_stop_simulation | 1 | 2.4 | 2.4 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador 0-7 lento: reloj 555 y compuertas AND/OR/XOR
Fixture del cerebro: contador-555-compuertas
Diseno en Tinkercad: /things/jApuXFjHQsc/editel

QUE HACE
 *   El 555 funciona como reloj (aprox. un pulso cada dos segundos). Su
 *   salida no va directo al Arduino: pasa por un AND con la senal MARCHA
 *   (D8), asi el conteo se congela cuando MARCHA esta en bajo, y por un
 *   OR
 *   con un pulsador, asi cada tecla avanza un digito a mano. El Uno solo
 *   cuenta los flancos que llegan a D2 y dibuja el digito 0..7 en el
 *   display de 7 segmentos, que vuelve a 0 despues del 7.
 *   Cada segmento lleva su resistencia de 220 ohmios, y las siete viven
 *   en
 *   la segunda protoboard como banco vertical: el pin de abajo recibe el
 *   cable del Uno (por debajo de las placas) y el de arriba sale al
 *   display
 *   (por arriba). Asi los cables no se amontonan en una sola zona.
 *   Las compuertas no son decorativas: el AND se arma con una NAND (u1)
 *   mas
 *   una XOR (u2) usada como inversor, y el OR con dos NAND (u1). Esa es
 *   la
 *   forma clasica de conseguir AND y OR cuando solo hay NAND.

COMPONENTES (ref  tipo  pieza)
  uno   arduino-uno        Arduino Uno R3
  t1    timer-555          temporizador 555
  r1    resistor           resistencia
  c1    capacitor          capacitor
  u1    nand-gate          74HC00 (4 NAND)
  u2    xor-gate           74HC86 (4 XOR)
  btn1  pushbutton         pulsador
  r2    resistor           resistencia
  r3    resistor           resistencia
  r4    resistor           resistencia
  r5    resistor           resistencia
  r6    resistor           resistencia
  r7    resistor           resistencia
  r8    resistor           resistencia
  seg   seven-segment      display 7 segmentos

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V  - t1.Vcc  - t1.Reset  - r1.1  - u1.Vcc  - u2.Vcc  - seg.com1
   2. uno.GND1  - t1.GND  - c1.2  - u1.GND  - u2.GND  - btn1.2
   3. r1.2  - t1.DIS  - t1.THR  - t1.TRIG  - c1.1
   4. t1.OUT  - u1.1A
   5. uno.D8  - u1.1B
   6. u1.1Y  - u2.1A
   7. u2.1B  - uno.5V
   8. u2.1Y  - u1.3A  - u1.3B
   9. u1.3Y  - u1.4A
  10. btn1.1  - u1.4B  - uno.D12
  11. u1.4Y  - uno.D2
  12. uno.D4  - r2.1
  13. r2.2  - seg.a
  14. uno.D5  - r3.1
  15. r3.2  - seg.b
  16. uno.D6  - r4.1
  17. r4.2  - seg.c
  18. uno.D7  - r5.1
  19. r5.2  - seg.d
  20. uno.D9  - r6.1
  21. r6.2  - seg.e
  22. uno.D10  - r7.1
  23. r7.2  - seg.f
  24. uno.D11  - r8.1
  25. r8.2  - seg.g

COMO SE VERIFICA (serial del simulador)
 *   TEST:COMPUERTAS=LISTO al arrancar y TEST:DIGITO=0.
 *   Cada pulso del 555 o del pulsador imprime TEST:DIGITO=1..7 y vuelve
 *   a 0: en 5 s de simulacion se ve el ciclo completo.

NOTAS
 *   El display es de anodo comun: comun a 5V y segmento en LOW. Sin
 *   resistencia serie el simulador lo hace estallar aunque el conteo
 *   siga: 220 ohmios por segmento, uno por net, y el banco va en la
 *   segunda placa.
 *   El pulsador cuelga de D12 con INPUT_PULLUP: el nodo tambien entra al
 *   OR, asi que el pull-up interno del micro hace de resistencia del
 *   circuito. Sin el, la linea queda flotante y el paso manual no
 *   funciona.
 *   R=68k y C=10uF dan el pulso lento; con 10k el conteo se ve borroso.
```
