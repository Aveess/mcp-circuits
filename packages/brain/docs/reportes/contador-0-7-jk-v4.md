# Contador 0-7 v4: sin Arduino, EN por interruptor y RESET por pulsador
- Circuito: https://www.tinkercad.com/things/3akmw1EaG0p/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: ver bloque

## Serial de la simulación
```text
{
  "success": true,
  "total_lines": 0,
  "lines": [],
  "raw_output": "",
  "message": "Retrieved 0 lines from Serial Monitor."
}
```

## Oráculo
- Circuito **sin sketch**: no hay monitor serial que verificar; el comportamiento se comprueba en el circuito (display, LED, movimiento).

## Ruteo
- Sin tramos sobre el cuerpo de una placa (185 de 185 cables medidos, 7 ruteados).
- Sin tramos diagonales en 185 cables medidos.
- 6 salto(s) recto(s) entre huecos de la placa (max. 70 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 15.5 | 15.5 |
| tinkercad_inspect_circuit | 1 | 0.2 | 0.2 |
| tinkercad_open_circuit | 2 | 16.2 | 18.3 |
| tinkercad_read_serial_monitor | 1 | 7.6 | 7.6 |
| tinkercad_set_component_property_model | 13 | 1.3 | 3.4 |
| tinkercad_start_simulation | 1 | 32.7 | 32.7 |
| tinkercad_stop_simulation | 1 | 4.0 | 4.0 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador 0-7 v4: sin Arduino, EN por interruptor y RESET por pulsador
Fixture del cerebro: contador-0-7-jk-v4
Diseno en Tinkercad: /things/3akmw1EaG0p/editel

QUE HACE
 *   Taller 3 - Contador 0 a 7 con flip-flops JK (v4, sin Arduino).
 *   Contador: tres flip-flops del 74HC73 en cascada. El 555 entrega el
 *   reloj (~1 Hz) al primero; Q0 relojea al segundo y Q1 al tercero.
 *   Q0 es el bit menos significativo. Los JK disparan en flanco de
 *   bajada, como pide el taller. R es activo en bajo: el inversor u1.6
 *   produce nR desde RESET.
 *   SIN ARDUINO (v4). El contador es 100 % hardware: 555 como reloj, tres
 *   74HC73 en cascada, el decodificador de compuertas y el display. La
 *   alimentacion viene de la pieza Power Supply, no de un micro.
 *   EN es el interruptor deslizante SW1: su terminal comun va a J y K de
 *   las tres etapas, un extremo a GND y el otro a Vcc. Con el comun en
 *   GND
 *   los flip-flops conservan el estado y el conteo se detiene; con el
 *   comun
 *   en Vcc basculan con cada flanco y el conteo sigue. SW1 nace en la
 *   posicion de Vcc: al abrir el diseno ya esta contando y deslizarlo lo
 *   detiene (medido en vivo: al reves el display se quedaba en 0).
 *   RESET es el pulsador SW2: esta entre Vcc y la entrada del inversor
 *   u1.6, que tiene una resistencia de 10k a GND (pull-down). En reposo
 *   esa entrada vale 0, la salida del inversor vale 1 y las tres R de los
 *   JK estan inactivas. Al apretar, la salida baja a 0 y los tres JK
 *   vuelven a 000 en el acto, sin esperar flanco de reloj.
 *   Decodificador (punto 4) con las expresiones del taller tal como
 *   estan escritas:
 *   a = Q1 + NOT(Q2 XOR Q0)
 *   b = NOT Q2 + NOT(Q1 XOR Q0)
 *   c = Q2 + NOT Q1 + Q0
 *   d = e + Q0(Q2 XOR Q1)
 *   e = NOT Q0 (Q1 + NOT Q2)
 *   f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)
 *   g = (Q2 XOR Q1) + Q1 NOT Q0
 *   Se arma con compuertas reales: 1 x 74HC04 (seis inversores), 1 x
 *   74HC86 (tres XOR), 2 x 74HC08 (AND) y 3 x 74HC32 (OR). Las entradas
 *   sobrantes de los integrados van a GND: una entrada CMOS nunca queda
 *   flotando.
 *   El display es de CATODO COMUN: el comun a GND y cada segmento a la
 *   salida de su compuerta por una resistencia de 220 ohmios. Un segmento
 *   luce con HIGH: el nodo de la compuerta es el que manda el segmento
 *   (en la v1 habia un inversor y se activaba con LOW). Las dos patas del
 *   comun
 *   son el mismo nodo interno del display: se cablea una sola, como en la
 *   v1, y encienden todos los segmentos.
 *   El display va GIRADO 180 GRADOS sobre la placa: es la unica postura
 *   en la que sus diez patas caen en huecos. Al girarlo giran tambien sus
 *   segmentos, asi que la senal del segmento a entra por la pata d, la de
 *   b por la e y la de c por la f; la g queda igual. Asi el numero se lee
 *   derecho mirando la placa. En la tabla de abajo, a..g son los
 *   segmentos que se ven, no los nombres de las patas.
 *   Tabla (1 = segmento encendido, convencion del taller):
 *   digito Q2Q1Q0 a b c d e f g
 *   0 000 1 1 1 1 1 1 0
 *   1 001 0 1 1 0 0 0 0
 *   2 010 1 1 0 1 1 0 1
 *   3 011 1 1 1 1 0 0 1
 *   4 100 0 1 1 0 0 1 1
 *   5 101 1 0 1 1 0 1 1
 *   6 110 1 0 1 1 1 1 1
 *   7 111 1 1 1 0 0 0 0
 *   No hay micro, no hay codigo y no hay monitor serial. La prueba de que
 *   cuenta es mirar el display: 0, 1, 2, 3, 4, 5, 6, 7 y otra vez 0, un
 *   digito por flanco de bajada del 555 (aproximadamente cada 0,4 s).
 *   Los dos capacitores van insertados en una Breadboard Small al costado
 *   derecho de la placa grande, no sueltos en el lienzo: C1 entre
 *   THR/TRIG y GND, C2 en CTRL. Sus dos patas caen en huecos vecinos de
 *   la misma fila, asi que cada uno ocupa dos columnas y se cablea con un
 *   puente corto mas un cable largo hasta la placa del 555.

COMPONENTES (ref  tipo  pieza)
  ps1   power-supply       power-supply
  sw1   slideswitch        slideswitch
  btn1  pushbutton         pulsador
  rpd   resistor           resistencia
  t1    timer-555          temporizador 555
  r1    resistor           resistencia
  r2    resistor           resistencia
  c1    capacitor          capacitor
  c2    capacitor          capacitor
  ff1   flip-flop-jk       74HC73 (biestable JK)
  ff2   flip-flop-jk       74HC73 (biestable JK)
  u1    not-gate           NOT 74HC04
  u2    and-gate           AND 74HC08
  u3    and-gate           AND 74HC08
  u4    or-gate            OR 74HC32
  u5    or-gate            OR 74HC32
  u6    or-gate            OR 74HC32
  x1    xor-gate           74HC86 (4 XOR)
  ra    resistor           resistencia
  rb    resistor           resistencia
  rc    resistor           resistencia
  rd    resistor           resistencia
  re    resistor           resistencia
  rf    resistor           resistencia
  rg    resistor           resistencia
  seg   seven-segment      display 7 segmentos

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. t1.Vcc
      - t1.Reset
      - r1.1
      - ff1.Vcc
      - ff2.Vcc
      - u1.Vcc
      - u2.Vcc
      - u3.Vcc
      - u4.Vcc
      - u5.Vcc
      - u6.Vcc
      - x1.Vcc
      - ps1.Vcc
      - sw1.1
      - btn1.2
   2. t1.GND
      - c1.2
      - c2.2
      - ff1.GND
      - ff2.GND
      - seg.com1
      - u1.GND
      - u2.GND
      - u3.GND
      - u4.GND
      - u5.GND
      - u6.GND
      - x1.GND
      - ff1.2J
      - ff1.2K
      - ff1.2CP
      - ff1.2R
      - u3.2A
      - u3.2B
      - u3.3A
      - u3.3B
      - u3.4A
      - u3.4B
      - u6.2A
      - u6.2B
      - u6.3A
      - u6.3B
      - u6.4A
      - u6.4B
      - x1.4A
      - x1.4B
      - ps1.GND
      - sw1.2
      - rpd.2
   3. r1.2  - r2.1  - t1.DIS
   4. r2.2  - t1.THR  - t1.TRIG  - c1.1
   5. t1.CTRL  - c2.1
   6. t1.OUT  - ff1.1CP
   7. ff1.1Q  - u1.1A  - u5.1B  - u2.2A  - x1.1B  - x1.2B  - ff2.1CP
   8. ff2.1Q
      - u1.2A
      - u4.1A
      - u4.2A
      - u3.1A
      - x1.2A
      - x1.3B
      - ff2.2CP
   9. ff2.2Q  - u1.3A  - u4.4A  - u2.4A  - x1.1A  - x1.3A
  10. x1.1Y  - u1.4A
  11. x1.2Y  - u1.5A
  12. u1.3Y  - u4.1B  - u4.3A
  13. u1.4Y  - u4.2B
  14. u1.5Y  - u4.3B
  15. u1.2Y  - u4.4B  - u5.2A  - u2.3A
  16. u4.4Y  - u5.1A
  17. u1.1Y  - u5.2B  - u2.1A  - u2.3B  - u3.1B
  18. u2.1Y  - u5.3A  - re.1
  19. u2.2Y  - u5.3B
  20. u2.3Y  - u5.4A
  21. u2.4Y  - u5.4B
  22. x1.3Y  - u6.1A  - u2.2B
  23. u3.1Y  - u6.1B
  24. u4.1Y  - u2.1B
  25. u5.2Y  - u2.4B
  26. sw1.common
      - ff1.1J
      - ff1.1K
      - ff2.1J
      - ff2.1K
      - ff2.2J
      - ff2.2K
  27. u1.6Y  - ff1.1R  - ff2.1R  - ff2.2R
  28. u4.2Y  - ra.1
  29. ra.2  - seg.d
  30. u4.3Y  - rb.1
  31. rb.2  - seg.e
  32. u5.1Y  - rc.1
  33. rc.2  - seg.f
  34. u5.3Y  - rd.1
  35. rd.2  - seg.a
  36. re.2  - seg.b
  37. u5.4Y  - rf.1
  38. rf.2  - seg.c
  39. u6.1Y  - rg.1
  40. rg.2  - seg.g
  41. btn1.1  - rpd.1  - u1.6A

COMO SE VERIFICA (serial del simulador)
 *   Esta version no tiene micro: no hay serial y el oraculo del runner no
 *   aplica. La verificacion es visual, con la simulacion corriendo:
 *   - el display muestra los digitos 0..7 en orden y vuelve a 0;
 *   - con EN en un extremo el numero se queda quieto y con EN en el otro
 *   sigue contando;
 *   - al apretar RESET el display salta a 0 y sigue desde ahi.

NOTAS
 *   Interpretacion y diagnostico (punto 6):
 *   - La frecuencia del 555 es f = 1.44 / ((R1 + 2 R2) C). Con R1=10k,
 *   R2=22k y C=10 uF da ~2.7 Hz: un digito cada 0,37 s, pensado para
 *   que el conteo se vea tambien con el simulador lento. El valor real
 *   se mide y se imprime en TEST:PERIODO.
 *   - Q0 conmuta a f/2, Q1 a f/4 y Q2 a f/8: cada etapa divide entre
 *   dos. Por eso el numero cambia a la frecuencia del reloj pero cada
 *   bit lo hace a la suya; el contador avanza un digito por flanco.
 *   - Si el display muestra valores intermedios al cambiar de digito es
 *   el transitorio del acarreo asincrono: el bit bajo cambia antes que
 *   el alto y la combinacion pasa por estados que no son el conteo. Se
 *   lee el numero despues de que se propague, no en el flanco.
 *   - Si el conteo se repite 0,1,2,3 y vuelve a 0, Q2 nunca bascula:
 *   revisar el reloj de la tercera etapa (Q1 -> CP de la tercera) y que
 *   su R no este activa. El sintoma es de cableado del reloj, no del
 *   decodificador.
 *   - Si un segmento queda siempre apagado o siempre encendido, el
 *   problema esta en su compuerta o en su resistencia serie, no en el
 *   contador: la tabla de verdad impresa permite comparar segmento por
 *   segmento.
 *   - El display es de catodo comun: si se cablea como si fuera de
 *   anodo, la mascara sale complementada y TEST:DECODER falla.
 *   - Si el numero se ve invertido en la placa, el cableado del display
 *   se hizo como si la pieza estuviera derecha: girada 180 grados, el
 *   segmento a es la pata d, b es e y c es f. El serial no lo detecta
 *   (lee las compuertas), asi que hay que mirar el display.
 *   - Si el display no se mueve nunca, lo primero es EN: con el comun del
 *   interruptor en GND (J=K=0) el contador esta en pausa a proposito.
 *   Cambiar el interruptor al otro extremo y volver a mirar.
 *   - Si el display esta clavado en 0 y no sale de ahi, el reset quedo
 *   activo: revisar que la resistencia de 10k del nodo del pulsador vaya
 *   a GND y no a Vcc. Con el pull-down al reves el inversor entrega 0
 *   permanente y los JK no cuentan.
 *   - Sin Arduino no hay monitor serial. Si alguien pide TEST:DIGITO, ese
 *   dato ya no existe en este circuito: se mira el display.
```
