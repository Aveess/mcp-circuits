# Contador 0-7 v3: alimentacion por fuente y rieles
- Circuito: https://www.tinkercad.com/things/kSakfQXHtmU/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: ver bloque

## Serial de la simulación
```text
{
  "success": true,
  "total_lines": 10,
  "lines": [
    "READY",
    "TEST:PERIODO=376",
    "TEST:DIGITO=0",
    "TEST:DIGITO=1",
    "TEST:DIGITO=2",
    "TEST:DIGITO=3",
    "TEST:DIGITO=4",
    "TEST:DIGITO=5",
    "TEST:DIGITO=6",
    "TEST:DIGITO=7"
  ],
  "raw_output": "READY\nTEST:PERIODO=376\nTEST:DIGITO=0\nTEST:DIGITO=1\nTEST:DIGITO=2\nTEST:DIGITO=3\nTEST:DIGITO=4\nTEST:DIGITO=5\nTEST:DIGITO=6\nTEST:DIGITO=7",
  "message": "Retrieved 10 lines from Serial Monitor."
}
```

## Oráculo
- Esperado, en orden: `TEST:PERIODO=` → `TEST:DIGITO=0` → `TEST:DIGITO=1` → `TEST:DIGITO=2` → `TEST:DIGITO=3` → `TEST:DIGITO=4` → `TEST:DIGITO=5` → `TEST:DIGITO=6` → `TEST:DIGITO=7`
- Observado: todas las marcas aparecieron en orden.

## Ruteo
- Sin tramos sobre el cuerpo de una placa (191 de 191 cables medidos, 16 ruteados).
- Sin tramos diagonales en 191 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 15.3 | 15.3 |
| tinkercad_inspect_circuit | 1 | 0.4 | 0.4 |
| tinkercad_list_circuits | 1 | 7.6 | 7.6 |
| tinkercad_open_circuit | 2 | 13.1 | 13.2 |
| tinkercad_read_serial_monitor | 6 | 1.5 | 3.2 |
| tinkercad_set_code | 1 | 17.4 | 17.4 |
| tinkercad_set_component_property_model | 12 | 1.3 | 6.6 |
| tinkercad_start_simulation | 1 | 21.6 | 21.6 |
| tinkercad_stop_simulation | 1 | 2.3 | 2.3 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador 0-7 v3: alimentacion por fuente y rieles
Fixture del cerebro: contador-0-7-jk-v3

QUE HACE
 *   Taller 3 - Contador 0 a 7 con flip-flops JK (v3).
 *   Contador: tres flip-flops del 74HC73 en cascada. El 555 entrega el
 *   reloj (~1 Hz) al primero; Q0 relojea al segundo y Q1 al tercero.
 *   Q0 es el bit menos significativo. Los JK disparan en flanco de
 *   bajada, como pide el taller. R es activo en bajo: el inversor u1.6
 *   produce nR desde RESET.
 *   EN (D8) va a J y K de las tres etapas: con EN=1 basculan; con EN=0
 *   conservan el estado. RESET (D9, activo en alto) llega al inversor y
 *   de ahi a las tres R: vuelve a 000 sin esperar flanco.
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
 *   luce con HIGH, asi que el sketch lee el nodo de la compuerta tal cual
 *   (en la v1 habia un inversor y se leia LOW). Las dos patas del comun
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
 *   El sketch no bloquea el conteo: en el setup mide el periodo, pulsa
 *   RESET una vez para arrancar en 000 y suelta EN; el loop solo lee y
 *   anuncia cada digito (TEST:DIGITO). No vuelve a tocar EN ni RESET, asi
 *   que el display cuenta desde el primer flanco y nada lo detiene. Las
 *   cuatro pruebas del punto 5 se demuestran midiendo (v1) en vez de
 *   moverlas desde el sketch, que dejaba la pantalla en 0 mientras
 *   corrian.
 *   Cada lectura se valida con una guarda: se lee Q, luego los segmentos
 *   y otra vez Q; si Q cambio en medio, el flanco del acarreo asincrono
 *   cayo dentro de la muestra y se descarta. La muestra valida se
 *   re-comprueba 5 ms despues antes de comparar con la tabla.
 *   Los dos capacitores van insertados en una Breadboard Small al costado
 *   derecho de la placa grande, no sueltos en el lienzo: C1 entre
 *   THR/TRIG y GND, C2 en CTRL. Sus dos patas caen en huecos vecinos de
 *   la misma fila, asi que cada uno ocupa dos columnas y se cablea con un
 *   puente corto mas un cable largo hasta la placa del 555.
 *   ALIMENTACION (v3). La fuente es la pieza Power Supply que esta a la
 *   izquierda de la primera placa, no el 5V del Uno: un cable ROJO de su
 *   positivo al riel positivo y uno NEGRO de su tierra al negativo; del
 *   borde derecho salen otros dos (rojo al riel positivo del otro
 *   extremo,
 *   negro al negativo) para que la placa entera quede alimentada. Cada
 *   integrado toca el riel de su propia mitad con un cable corto en su
 *   misma columna, y la segunda placa se alimenta de la primera con los
 *   mismos dos cables. Rojo es siempre positivo y negro siempre tierra:
 *   un cable rojo de senal es un error de armado.
 *   El par de rieles de ABAJO de la placa grande es un solo nodo en el
 *   modelo (sus dos filas se llaman X), asi que no se usa para positivo y
 *   tierra a la vez: la mitad de abajo se alimenta con una bajada al
 *   borde
 *   derecho y una fila de bus. En una placa chica, que si tiene los
 *   cuatro
 *   rieles separados, la bajada va de riel a riel.
 *   La tierra del Uno sigue en la net de tierra (es la referencia de las
 *   lecturas analogicas); su pin de 5V queda sin usar.

COMPONENTES (ref  tipo  pieza)
  ps1  power-supply       power-supply
  uno  arduino-uno        Arduino Uno R3
  t1   timer-555          temporizador 555
  r1   resistor           resistencia
  r2   resistor           resistencia
  c1   capacitor          capacitor
  c2   capacitor          capacitor
  ff1  flip-flop-jk       74HC73 (biestable JK)
  ff2  flip-flop-jk       74HC73 (biestable JK)
  u1   not-gate           NOT 74HC04
  u2   and-gate           AND 74HC08
  u3   and-gate           AND 74HC08
  u4   or-gate            OR 74HC32
  u5   or-gate            OR 74HC32
  u6   or-gate            OR 74HC32
  x1   xor-gate           74HC86 (4 XOR)
  ra   resistor           resistencia
  rb   resistor           resistencia
  rc   resistor           resistencia
  rd   resistor           resistencia
  re   resistor           resistencia
  rf   resistor           resistencia
  rg   resistor           resistencia
  seg  seven-segment      display 7 segmentos

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. ps1.Vcc
      - t1.Vcc
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
   2. uno.GND1
      - t1.GND
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
   3. r1.2  - r2.1  - t1.DIS
   4. r2.2  - t1.THR  - t1.TRIG  - c1.1
   5. t1.CTRL  - c2.1
   6. t1.OUT  - ff1.1CP  - uno.D2
   7. ff1.1Q
      - u1.1A
      - u5.1B
      - u2.2A
      - x1.1B
      - x1.2B
      - ff2.1CP
      - uno.D3
   8. ff2.1Q
      - u1.2A
      - u4.1A
      - u4.2A
      - u3.1A
      - x1.2A
      - x1.3B
      - ff2.2CP
      - uno.D4
   9. ff2.2Q  - u1.3A  - u4.4A  - u2.4A  - x1.1A  - x1.3A  - uno.D5
  10. x1.1Y  - u1.4A
  11. x1.2Y  - u1.5A
  12. uno.D9  - u1.6A
  13. u1.3Y  - u4.1B  - u4.3A
  14. u1.4Y  - u4.2B
  15. u1.5Y  - u4.3B
  16. u1.2Y  - u4.4B  - u5.2A  - u2.3A
  17. u4.4Y  - u5.1A
  18. u1.1Y  - u5.2B  - u2.1A  - u2.3B  - u3.1B
  19. u2.1Y  - u5.3A  - re.1  - uno.A4
  20. u2.2Y  - u5.3B
  21. u2.3Y  - u5.4A
  22. u2.4Y  - u5.4B
  23. x1.3Y  - u6.1A  - u2.2B
  24. u3.1Y  - u6.1B
  25. u4.1Y  - u2.1B
  26. u5.2Y  - u2.4B
  27. uno.D8  - ff1.1J  - ff1.1K  - ff2.1J  - ff2.1K  - ff2.2J  - ff2.2K
  28. u1.6Y  - ff1.1R  - ff2.1R  - ff2.2R
  29. u4.2Y  - ra.1  - uno.A0
  30. ra.2  - seg.d
  31. u4.3Y  - rb.1  - uno.A1
  32. rb.2  - seg.e
  33. u5.1Y  - rc.1  - uno.A2
  34. rc.2  - seg.f
  35. u5.3Y  - rd.1  - uno.A3
  36. rd.2  - seg.a
  37. re.2  - seg.b
  38. u5.4Y  - rf.1  - uno.A5
  39. rf.2  - seg.c
  40. u6.1Y  - rg.1  - uno.D6
  41. rg.2  - seg.g

COMO SE VERIFICA (serial del simulador)
 *   El serial demuestra el conteo, que es lo unico que hace el sketch:
 *   TEST:PERIODO=<ms> periodo medido del reloj 555 en D2.
 *   TEST:DIGITO=0..7 los ocho digitos salen en orden, sin saltos.
 *   TEST:DEMO=OK la tanda anunciada termino.
 *   Si el display se quedara en 0, el serial tampoco avanzaria: el
 *   conteo lo lleva el hardware (555 + JK), no el sketch.
 *   El serial debe imprimir, en orden: TEST:PERIODO=, TEST:DIGITO=0,
 *   TEST:DIGITO=1, TEST:DIGITO=2, TEST:DIGITO=3, TEST:DIGITO=4,
 *   TEST:DIGITO=5, TEST:DIGITO=6, TEST:DIGITO=7.

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
 *   - Si el circuito no arranca, lo primero es la fuente: el LED de la
 *   placa tiene que encender. Sin rojo en el riel positivo y negro en el
 *   negativo, todo lo demas es ruido.
 *   - Si una parte de la placa esta muerta y la otra no, falta el puente
 *   del borde opuesto: el riel de arriba esta alimentado y el de abajo
 *   no. En la placa grande ese puente es la bajada de la ultima columna
 *   mas la fila de bus.
 *   - Un cable rojo o negro que no sea de alimentacion es un error de
 *   armado, no una decision de dibujo: los colores son la unica forma de
 *   leer la alimentacion en una foto.
```
