# Contador 0-7 con 3 JK, reloj 555 y decodificador de compuertas
- Circuito: https://www.tinkercad.com/things/4bJNKia4pfj/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: ver bloque

## Serial de la simulación
```text
{
  "success": true,
  "total_lines": 9,
  "lines": [
    "READY",
    "TEST:PERIODO=1014",
    "TEST:RESET=OK",
    "TEST:CICLO=OK",
    "TEST:EN0=OK",
    "TEST:REANUDA=OK",
    "TEST:RESET_MEDIO=OK",
    "TEST:DECODER=OK",
    "TEST:FIN=OK"
  ],
  "raw_output": "READY\nTEST:PERIODO=1014\nTEST:RESET=OK\nTEST:CICLO=OK\nTEST:EN0=OK\nTEST:REANUDA=OK\nTEST:RESET_MEDIO=OK\nTEST:DECODER=OK\nTEST:FIN=OK",
  "message": "Retrieved 9 lines from Serial Monitor."
}
```

## Oráculo
- Esperado, en orden: `TEST:PERIODO=` → `TEST:RESET=OK` → `TEST:CICLO=OK` → `TEST:EN0=OK` → `TEST:REANUDA=OK` → `TEST:RESET_MEDIO=OK` → `TEST:DECODER=OK` → `TEST:FIN=OK`
- Observado: todas las marcas aparecieron en orden.

## Ruteo
- Sin tramos sobre el cuerpo de una placa (140 de 140 cables medidos, 139 ruteados).
- Sin tramos diagonales en 140 cables medidos.
- 1 salto(s) recto(s) entre huecos de la placa (max. 60 unidades); son puentes, se dejan.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 9.7 | 9.7 |
| tinkercad_inspect_circuit | 1 | 0.2 | 0.2 |
| tinkercad_list_circuits | 1 | 7.9 | 7.9 |
| tinkercad_open_circuit | 2 | 10.2 | 11.3 |
| tinkercad_read_serial_monitor | 1 | 1.3 | 1.3 |
| tinkercad_set_code | 1 | 13.7 | 13.7 |
| tinkercad_set_component_property_model | 11 | 1.3 | 2.6 |
| tinkercad_start_simulation | 1 | 55.7 | 55.7 |
| tinkercad_stop_simulation | 1 | 1.4 | 1.4 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Contador 0-7 con 3 JK, reloj 555 y decodificador de compuertas
Fixture del cerebro: contador-0-7-jk

QUE HACE
 *   Taller 3 - Contador 0 a 7 con tres flip-flops JK.
 *   Contador: tres 74HC73 en cascada. El 555 entrega el reloj (~1 Hz) al
 *   primer JK; Q0 relojea al segundo y Q1 al tercero. Q0 es el bit menos
 *   significativo. Los JK disparan en flanco de bajada, igual que pide el
 *   taller. R de cada JK es activo en bajo: u5.4 lo invierte desde RESET.
 *   EN (D8) va a J y K de las tres etapas: con EN=1 basculan; con EN=0
 *   conservan el estado. RESET (D9, activo en alto) llega a u5.4 y de ahi
 *   a
 *   las tres R: vuelve a 000 sin esperar flanco.
 *   Decodificador (punto 4), expresiones del taller:
 *   a = Q1 + NOT(Q2 XOR Q0)
 *   b = NOT Q2 + NOT(Q1 XOR Q0)
 *   c = Q2 + NOT Q1 + Q0
 *   d = e + Q0(Q2 XOR Q1)
 *   e = NOT Q0 (Q1 + NOT Q2)
 *   f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)
 *   g = (Q2 XOR Q1) + Q1 NOT Q0
 *   Las siete salidas se construyen con 27 NAND de 2 entradas (7 x
 *   74HC00)
 *   mas 3 XOR (1 x 74HC86). Cada salida se invierte otra vez (na..ng)
 *   porque
 *   el display es de anodo comun: un segmento luce cuando su pin va a
 *   LOW.
 *   El pin de la compuerta tambien se lee en A0..A5 y D6 para que el
 *   sketch
 *   compare el decodificador con la tabla de verdad.
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
 *   Pruebas del punto 5 que ejecuta el sketch:
 *   1. RESET -> 000 y digito 0.
 *   2. EN=1 -> dos ciclos completos 0..7..0..7..0.
 *   3. EN=0 -> el numero se mantiene varios flancos; al volver EN a 1
 *   continua desde ese valor.
 *   4. RESET en un valor intermedio -> vuelve a 0.
 *   Cada lectura se toma con dos muestras iguales separadas 60 ms: el
 *   acarreo
 *   entre JK es asincrono y el display pasa por un transitorio.

COMPONENTES (ref  tipo  pieza)
  uno  arduino-uno        Arduino Uno R3
  t1   timer-555          temporizador 555
  r1   resistor           resistencia
  r2   resistor           resistencia
  c1   capacitor          capacitor
  c2   capacitor          capacitor
  ff1  flip-flop-jk       74HC73 (biestable JK)
  ff2  flip-flop-jk       74HC73 (biestable JK)
  x1   xor-gate           74HC86 (4 XOR)
  u1   nand-gate          74HC00 (4 NAND)
  u2   nand-gate          74HC00 (4 NAND)
  u3   nand-gate          74HC00 (4 NAND)
  u4   nand-gate          74HC00 (4 NAND)
  u5   nand-gate          74HC00 (4 NAND)
  u6   nand-gate          74HC00 (4 NAND)
  u7   nand-gate          74HC00 (4 NAND)
  ra   resistor           resistencia
  rb   resistor           resistencia
  rc   resistor           resistencia
  rd   resistor           resistencia
  re   resistor           resistencia
  rf   resistor           resistencia
  rg   resistor           resistencia
  seg  seven-segment      display 7 segmentos

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.5V
      - t1.Vcc
      - t1.Reset
      - r1.1
      - seg.com1
      - ff1.Vcc
      - ff2.Vcc
      - x1.Vcc
      - u1.Vcc
      - u2.Vcc
      - u3.Vcc
      - u4.Vcc
      - u5.Vcc
      - u6.Vcc
      - u7.Vcc
   2. uno.GND1
      - t1.GND
      - c1.2
      - c2.2
      - ff1.GND
      - ff2.GND
      - x1.GND
      - u1.GND
      - u2.GND
      - u3.GND
      - u4.GND
      - u5.GND
      - u6.GND
      - u7.GND
      - ff1.2J
      - ff1.2K
      - ff1.2CP
      - ff1.2R
      - u7.4A
      - u7.4B
      - x1.4A
      - x1.4B
   3. r1.2  - r2.1  - t1.DIS
   4. r2.2  - t1.THR  - t1.TRIG  - c1.1
   5. t1.CTRL  - c2.1
   6. t1.OUT  - ff1.1CP  - uno.D2
   7. ff1.1Q
      - u1.1A
      - u1.1B
      - u3.4A
      - u4.3B
      - x1.1B
      - x1.2B
      - ff2.1CP
      - uno.D3
   8. ff2.1Q
      - u1.2A
      - u1.2B
      - u2.2A
      - u4.3A
      - x1.2A
      - x1.3B
      - ff2.2CP
      - uno.D4
   9. ff2.2Q
      - u1.3A
      - u1.3B
      - u2.1A
      - u3.1B
      - u4.4A
      - x1.1A
      - x1.3A
      - uno.D5
  10. u1.2Y  - u1.4A  - u3.1A  - u4.2A
  11. x1.1Y  - u1.4B
  12. x1.2Y  - u2.1B
  13. u1.1Y  - u2.2B  - u3.2A  - u4.2B
  14. u2.2Y  - u2.3A  - u2.3B  - u5.3B
  15. u1.3Y  - u2.4A
  16. u2.3Y  - u2.4B
  17. u3.1Y  - u3.2B
  18. u3.2Y  - u3.3A  - u3.3B  - u4.1A
  19. x1.3Y  - u3.4B  - u5.2A  - u5.2B
  20. u3.4Y  - u4.1B
  21. u4.3Y  - u4.4B
  22. u4.2Y  - u5.1A
  23. u4.4Y  - u5.1B
  24. u5.2Y  - u5.3A
  25. uno.D9  - u5.4A  - u5.4B
  26. u1.4Y  - u6.1A  - u6.1B
  27. u2.1Y  - u6.2A  - u6.2B
  28. u2.4Y  - u6.3A  - u6.3B
  29. u4.1Y  - u6.4A  - u6.4B
  30. u3.3Y  - u7.1A  - u7.1B
  31. u5.1Y  - u7.2A  - u7.2B
  32. u5.3Y  - u7.3A  - u7.3B
  33. uno.D8  - ff1.1J  - ff1.1K  - ff2.1J  - ff2.1K  - ff2.2J  - ff2.2K
  34. u5.4Y  - ff1.1R  - ff2.1R  - ff2.2R
  35. u6.1Y  - ra.1  - uno.A0
  36. ra.2  - seg.a
  37. u6.2Y  - rb.1  - uno.A1
  38. rb.2  - seg.b
  39. u6.3Y  - rc.1  - uno.A2
  40. rc.2  - seg.c
  41. u6.4Y  - rd.1  - uno.A3
  42. rd.2  - seg.d
  43. u7.1Y  - re.1  - uno.A4
  44. re.2  - seg.e
  45. u7.2Y  - rf.1  - uno.A5
  46. rf.2  - seg.f
  47. u7.3Y  - rg.1  - uno.D6
  48. rg.2  - seg.g

COMO SE VERIFICA (serial del simulador)
 *   El serial demuestra el sistema completo, no solo el conteo:
 *   TEST:PERIODO=<ms> periodo medido del reloj 555 en D2.
 *   TEST:RESET=OK tras RESET el contador esta en 000 y el display en 0.
 *   TEST:CICLO=OK dos vueltas completas 0..7..0..7..0 con EN=1.
 *   TEST:EN0=OK con EN=0 el valor no cambia en tres periodos.
 *   TEST:REANUDA=OK al volver EN a 1 continua desde el valor detenido.
 *   TEST:RESET_MEDIO=OK RESET en un valor intermedio devuelve 000.
 *   TEST:DECODER=OK cada lectura estable coincide con la tabla de verdad.
 *   TEST:FIN=OK la secuencia de pruebas termino.
 *   El serial debe imprimir, en orden: TEST:PERIODO=, TEST:RESET=OK,
 *   TEST:CICLO=OK, TEST:EN0=OK, TEST:REANUDA=OK, TEST:RESET_MEDIO=OK,
 *   TEST:DECODER=OK, TEST:FIN=OK.

NOTAS
 *   Interpretacion y diagnostico (punto 6):
 *   - La frecuencia del 555 es f = 1.44 / ((R1 + 2 R2) C). Con R1 = 10k,
 *   R2 = 68k y C = 10 uF da ~0.99 Hz. El valor real se mide en la
 *   simulacion y se imprime en TEST:PERIODO.
 *   - Q0 conmuta a f/2, Q1 a f/4 y Q2 a f/8: cada etapa divide entre dos.
 *   Por eso el numero cambia a la frecuencia del reloj pero cada bit lo
 *   hace a la suya; el contador completo avanza un digito por flanco.
 *   - Si el display muestra valores intermedios al cambiar de digito es
 *   el
 *   transitorio del acarreo asincrono: el bit bajo cambia antes que el
 *   alto y la combinacion pasa por estados que no son el conteo. Se lee
 *   el numero despues de que se propague, no en el instante del flanco.
 *   - Si el conteo se repite 0,1,2,3 y vuelve a 0, Q2 nunca bascula:
 *   revisar
 *   el reloj de la tercera etapa (Q1 -> CP de la tercera) y que su R no
 *   este activa. El sintoma es de cableado del reloj, no del
 *   decodificador.
 *   - Si un segmento queda siempre apagado o siempre encendido, el
 *   problema
 *   esta en su compuerta o en su resistencia serie, no en el contador: la
 *   tabla de verdad impresa permite comparar segmento por segmento.
```
