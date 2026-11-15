# Fase 0 en vivo — primera corrida (2026-11-11)

Circuito: "Fase0 blink-basico" — https://www.tinkercad.com/things/j7EqK1vq0nj-fase0-blink-basico/editel
Artefactos crudos (locales, no versionados): ~/jarvis_data/logs/tinkercad-fase0/live*.json

## Hallazgos verificados

| # | Hallazgo | Evidencia |
|---|---|---|
| 1 | El login funcionó, pero `auth_status` daba falso negativo: Tinkercad ya no usa las cookies que ezhil esperaba (`_tcad_session_colab` / `_circuits_session_colab` son las reales) y la sesión tarda en restaurarse | Fix en el puente `b508b7e`: cookies reales + espera 3s. Verificado `authenticated: true` dos veces seguidas, suite del puente 154/154 |
| 2 | `inspect_circuit` lee el modelo real en vivo: 3 componentes, pines, posiciones | live2.json |
| 3 | `inspect_schematic_connections` devuelve las nets correctas: D13–R1.1, R1.2–LED.anode, LED.cathode–GND1 (3/3) | live4.json |
| 4 | Simulación arranca y el Serial Monitor imprime `READY` | live4.json |
| 5 | `connect_verified_netlist` falló con LED fuera de protoboard: 1 de 3 cables persistió, error `terminal_element_not_found_in_svg` en `anode` | live3.json |
| 6 | `connect_component_pins` sí completó el cableado, pero reporta nombres de pin poco fiables (pidió `anode`, reportó `Cathode`) aunque la net final quedó correcta | live4.json vs inspect |
| 7 | Los `instance_id` cambian entre sesiones (_260 → _262): no sirven como identidad estable | live2 vs live3 |
| 8 | `validate_circuit_pre_simulation` dijo "listo" con el LED sin cablear: su veredicto es débil, no es oráculo | live3.json |
| 9 | Error de compilación (falta `;`): la simulación simplemente no arranca, `error: null`. Se distingue compila/no-compila, pero no la causa | live5.json |
| 10 | Sin protoboard el layout es pobre: componentes flotantes (ver screenshot) | screenshots/fase0_blink.png en el puente |

## Conclusión parcial

La fidelidad de lectura (componentes + nets vía esquemático) funcionó en el primer
circuito real. El cuello de botella se movió: ahora es la **colocación/cableado
sobre protoboard** y la **identidad estable de componentes**, no la lectura.
Esto refuerza portar de netchuu la spec por huecos y la colocación en el modelo.

## Segunda corrida: build directo en el modelo (2026-11-11)

Circuito "Fase0 modelo-directo blink": https://www.tinkercad.com/things/aBcCq6HfA2P/editel

- Nueva tool del puente `tinkercad_build_circuit_model` (47 tools): coloca por
  huecos en el modelo interno, sin clics. Resistencia 1g-5g, LED anode 5i /
  cathode 6i, cables al Uno y al riel.
- Bug encontrado y corregido: sin esperar `shareJsDoc.numberPending() == 0`
  las partes desaparecían al recargar. Con la espera, persisten (verificado
  tras recarga: Uno + protoboard + resistencia + LED, 13 cables).
- Simulación imprime READY.
- Pendiente: `inspect_schematic_connections` devuelve `nets: []` en este
  circuito con protoboard, mientras que en el blink sin protoboard dio 3/3.
  Hipótesis: la agrupación esquemática no resuelve continuidad a través de
  los terminales del protoboard. Es el próximo frente de investigación.

## Tercera y cuarta corrida: sampler y oraculo serial (2026-11-11)

- Nueva tool del puente `tinkercad_simulate_samples` (48 tools): muestrea brillo
  de LED por screenshot/PIL. En vivo arrancó y leyó serial READY, pero el brillo
  dio identico en las 4 muestras (0.5728): la lectura por pixel NO esta
  calibrada en headless y no es oraculo confiable todavia.
- El oraculo que si funciona: sketch instrumentado (sketches.blink_sketch) con
  trazas por serial. En vivo: READY, TEST:ON, TEST:OFF alternando 5 ciclos.
  Esa es la via de verificacion de comportamiento adoptada.
- Semaforo (dlhJ966IRvA) y boton (bWmMIRN5dwi) construidos en protoboard con
  el builder; conectividad 1.0 y 0.8 (el 0.8 es por nombres de pin del
  pushbutton, no por electricidad). Reportes en docs/reportes/.

## Quinta corrida: servo + potenciometro (2026-11-11)

https://www.tinkercad.com/things/9Rpc2a0C6te/editel — servo en D9 controlado por
potenciometro en A0, construido con builder+layout de 3 pines. Tras recarga:
conectividad 1.0 (hubo que enseñar a derive_nets los alias por tipo: el
"Terminal 2" del potenciometro es el pin 3, el de la resistencia es el 2).
Simulacion: TEST:ANGLE=180 (el potenciometro arranca al maximo en Tinkercad).

## Sexta corrida: organizacion de cables + TMP36 (2026-11-11)

Regla nueva de Eddie: cableado organizado siempre. Implementado en 3 capas:
cerebro ordena (alimentacion, tierra, senales) y colorea (negro tierra, rojo
5V, paleta senales); el puente rutea ortogonal con carriles (route_debug por
cable, nada silencioso). Prueba limpia: "Fase organizada blink v3"
(https://www.tinkercad.com/things/2tMhkuosDyj/editel) — routed 2/2, foto con
ambos cables por carril horizontal bajando a la placa.
TMP36 (https://www.tinkercad.com/things/3Dh7FcuvaEQ/editel): routed 5/5,
serial TEST:TEMP=24.78, conectividad 1.0 tras agregar el nombre real
"Temperature Sensor [TMP36]" al mapa y los alias Power/GND por tipo.

## Correcciones tras prueba de Eddie (2026-11-11, noche)

Reporte de Eddie: el foco del ultrasonico no prendia, el TMP no dejaba mover
la temperatura, y el RGB no tenia cables. Diagnostico con evidencia:

- **RGB**: el circuito `4ugNSKCOlv3` era solo la exploracion de geometria:
  LED RGB puesto sin resistencias, sin cables y sin codigo. Se completo ahi
  mismo y despues se reconstruyo limpio en `6CynuRekrD2` "RGB colores"
  (3 resistencias en filas g/h/j, cables ruteados 4/4, ciclo
  RED/GREEN/BLUE por serial verificado).
- **Ultrasonico**: el sensor media bien; el LED no prendia porque el umbral
  de 20 cm quedaba al borde (la distancia deriva 17-28 cm entre sesiones).
  Se agrego al puente `tinkercad_set_component_property_model` (49 tools)
  para fijar "Target Y" directo en el modelo, y el umbral del sketch subio
  a 40 cm con margen. Circuito renombrado "Ultrasonico LED por distancia":
  arranca con el objeto a ~22 cm y el LED ENCENDIDO; alejar el objeto a
  mas de 40 cm lo apaga.
- **TMP36**: la temperatura solo se mueve durante la simulacion (limite de
  Tinkercad, no del circuito). El diseno original arrancaba en 24.78 con
  umbral 25 (apagado y confuso). Nuevo circuito `dRSUU84fqhP` "TMP36
  temperatura LED" con umbral 20: LED encendido al arrancar; bajar la
  temperatura a menos de 20 lo apaga.

Nota: quedo un circuito TMP36 duplicado de una corrida interrumpida; no hay
tool de borrado en el puente, se puede eliminar a mano desde el dashboard.

## Limpieza de cuenta y ruteo de libres (2026-11-12)

Reporte de Eddie: muchos proyectos a medias/duplicados, y los cables de la
bateria y el motor salian diagonales. Correcciones:
- El runner ahora reutiliza el circuito por titulo exacto (no crea otro) y
  construye con reemplazo limpio (clear_existing en el puente, que conserva
  el Uno y borra el resto en un edit separado). Probado: reconstruir
  "Motor L293D bateria 9V v3" devolvio la MISMA url con score 100%.
- El ruteo ortogonal se extendio a partes libres: motor y bateria ya salen
  en angulo recto (foto l293d_reuse.png).
- 11 duplicados/exploraciones renombrados a "BORRAR - ..." (el puente no
  tiene borrado; quedan agrupados para borrar desde el dashboard).

## Nivel 2 y 3 de circuitos (2026-11-13)

Se sumaron tres circuitos que suben la complejidad y dos componentes con
geometria no trivial, todos verificados en vivo al 100%:

- **Buzzer activo con boton** (93Dj8w6iEv1): Piezo did 114067; su "-" cae 5
  columnas a la derecha del "+" (ancla). Su cuerpo es un disco grande que
  tapaba el boton: ahora se coloca en segunda pasada desde la columna 24.
- **LDR divisor en luz nocturna** (lo9VkvBdWmT): Photoresistor (LDR) did
  116691; "terminal-2" cae 1 columna a la derecha de "terminal-1". La
  resistencia del divisor se coloca 3 columnas a la derecha del ancla y el
  LDR tambien va al extremo derecho (columna 22) por el disco.
- **Barrera de parking** (2xxjwQBZuOH): HC-SR04 + servo + RGB. El RGB se
  coloca primero y el layout lo reubica en la primera ventana libre de 8
  columnas si el cursor ya paso, asi el fixture no depende del orden.

Lecciones:
1. Los refs derivados por `derive_nets` DEBEN ser identicos a los de
   `normalize_circuit` (photoresistor1, no ldr1): `compare_connectivity`
   alinea por tipo+orden y un prefijo distinto deja los endpoints opacos
   (la conectividad cayo a 0.66 sin que el cableado estuviera mal).
2. El ref de una resistencia sigue el orden fisico en `inspect`, no el
   orden de la fixture: en `ldr-divisor` la resistencia del divisor es r2.
3. En el simulador el LDR arranca a oscuras (analogRead = 6) y el
   ultrasonico mide ~112 cm segun los objetos de la escena. Los sketches se
   eligen para que el circuito arranque en un estado observable (luz
   nocturna encendida, barrera abierta) sin mentir sobre la logica.
4. Un disco grande (piezo, LDR, HC-SR04) siempre al extremo derecho y en la
   ultima pasada del planner: tapar un LED o un boton se ve como un
   circuito roto aunque la conectividad sea 1.0.

## Nivel 5: LCD 16x2 en modo 4 bits (2026-11-13)

Primer circuito con salida de texto y bus de 4 bits. `cpySiVSE9vr`, 100% de
fidelidad y oraculo serial `TEST:SEG=N` que coincide con lo que muestra la
pantalla.

Hechos medidos en vivo:
1. `LiquidCrystal` SI esta soportada por el simulador de Tinkercad.
2. El potenciometro de contraste en su posicion por defecto (wiper al 50%)
   deja la pantalla EN BLANCO. Con `VO` a GND se lee perfecto. El circuito
   va sin potenciometro y el sketch lo documenta.
3. El cuerpo del LCD mide ~25 columnas y tapa las filas f..c de la placa.
   Esa medicion llevo a ensartarlo en la fila j con reserva de columnas y
   guarda de oclusion; **quedo superada en la fase 21** (ver abajo): hoy el
   display va como modulo libre y no ocupa ni tapa nada de la placa.
4. Los cables etiquetan los pines del LCD con nombres humanos (`Ground`,
   `Power`, `Contrast`, `Register Select`, `Read/Write`, `Enable`,
   `LED Anode`, `LED Cathode`) distintos de los de `inspect_circuit`
   (`GND`, `VDD`, `VO`, `RS`, `RW`, `E`, `LED+`, `LED-`): hacen falta alias
   por tipo o la conectividad se cae a 44% sin que el cableado este mal.

## Fase 21: el LCD pasa a modulo libre (2026-11-13)

El LCD ensartado en la protoboard tapaba las filas f..c en ~25 columnas: no se
podia combinar con sensores. Medido en vivo que `free` funciona (el LCD queda
fuera de la placa, con cables de terminal a terminal), se cambio el contrato:

- El LCD se emite como `{"free": {"x": 870, "y": -230, "angle": 0}}` (arriba
  de la placa; un segundo LCD se apila en y=-430).
- Desaparecen la reserva de columnas y la guarda de oclusion: piezo, LDR,
  ultrasonico, boton, 3 pines y L293D vuelven a colocarse junto al display.
- El builder emite el part sin `pin`/`at` y rutea los cables del LCD por
  terminal real (`lcd1.RS`, `lcd1.DB4`...). La rama con `at` queda solo por
  compatibilidad.
- El `free` del part lleva solo `{x, y}` y el angulo va a nivel de part:
  es lo que lee el puente y lo que exige `spec.validate_spec`.
- Resultado: `lcd-contador` y `lcd-temperatura` (TMP36 + display, `9hZJgbsYOC5`)
  al 100%, con el display mostrando exactamente el valor del oraculo serial.

## Fase 22: nivel 6 y cableado en estrella (2026-11-13/14)

`lcd-distancia` (`blN5d8qCr2z`): HC-SR04 + display + alarma sonora. Layout y
builder lo resolvieron sin cambios; solo hizo falta el sketch
(`TEST:DIST=110.1` + `TEST:ALARMA=ON`, mismo valor en pantalla).

Dos defectos visuales que la conectividad al 100% no veia:

1. Los cables de las nets de 4+ extremos se encadenaban (`a-b`, `b-c`, ...) y
   un eslabon hueco-hueco lo dibuja recto el simulador: cruzaba en diagonal
   sobre el TMP36 y el HC-SR04. Ahora cada net de 3+ extremos se empareja en
   estrella desde su hub (el primer pin del Uno si esta en la net), y el
   puente rutea todos esos cables por carriles. Las nets de 2 extremos se
   dejan tal cual.
2. Con dos cuerpos grandes en la misma placa, el disco del piezo tapaba el
   transductor derecho del HC-SR04. Regla de entonces: si el piezo esta
   presente, el sensor arranca en la columna 10 y el piezo conserva el
   extremo derecho (24e). **Correccion (fase 37):** esa regla se retiro.
   Con el sensor en 10 su cuerpo tapa las filas altas sobre las columnas
   3..20 y ahi caia la resistencia del LCD. Ahora el que cede es el piezo,
   que se va libre. Detalle en la fase 37.

## Fase 23: display 7 segmentos (2026-11-14)

Contador 0-9 en un display de un dígito (`gfgLntRuWJv`, 100%). El display
(did 129710) es una parte libre como el LCD (`x=870`, `y=-230`), así que no
ocupa columnas ni tapa la placa; sus 10 terminales se cablean directo
(`seg.a`, `seg.com1`...).

Hallazgos en vivo:

- **Siete resistencias en una placa de 30 columnas**: cada bloque de
  resistencia ocupa 6 columnas y solo caben 4 arriba del canal. Ahora las
  resistencias sueltas (sin LED) desbordan a la mitad inferior en la fila `e`
  y caben 4 + 3 sin archivar ninguna.
- **El display es de ánodo común en el simulador**: con el común a GND y los
  segmentos en HIGH no se enciende nada. Con el común a 5V y el segmento en
  LOW se enciende; el sketch invierte la tabla (`!DIGITOS[d][i]`).
- **Nombres de pin**: `inspect` devuelve `a..g, dp, com1, com2`, pero el
  cableado guardado etiqueta `A..G, DP, Common`. Sin alias en
  `breadboard_nets`, la conectividad se queda en 73.3%.
- **La reparación de cables no sirve con partes libres**: reenvía solo
  `wires` y, tras el borrado limpio, los terminales de la parte libre ya no
  existen. En circuitos con partes libres se reconstruye completo.
- Verificación visual: el "0" y el "3" del contador se comprobaron en captura,
  lo que cubre los siete segmentos.
- **Correcciones de la ronda 16 de tester** (independiente, 132 casos):
  - `hold_ms` pasó de 1000 a 400 ms: el ciclo de 10 dígitos dura 4 s y entra
    en la ventana de 5 s del runner. Antes el oráculo solo veía `0..4`; ahora
    el reporte guardado trae `TEST:DIGITO=0..9` completo.
  - El LCD y el display comparten un único apilado `FREE_MODULE_*`; así el
    segundo nunca cae encima del primero (antes se separaban solo 30 px).
  - `spec.PIN_TABLE` ya tiene `seven-segment` y `lcd-16x2`: la capa spec
    rechaza un pin inventado igual que el builder.
  - Docstring y comentario de la tabla dicen ánodo común, que es lo que
    emite el sketch y lo que confirma el simulador.

### Un solo diseño por circuito: `tinkercad_id` clavado en la fixture

El runner reusaba por **título**, y el título del diseño no siempre coincide
con el de la fixture (`Motor DC con transistor` vs `Motor DC con transistor
NPN, resistencia de base y diodo flyback`). Resultado: dos circuitos
duplicados (`iJSJ56Ckug6`, `92KSAB7E01N`) al re-verificar los motores; se
borraron y se volvieron a construir en sus ids originales.

Ahora cada fixture de `fixtures/fase0/circuits.json` lleva su `tinkercad_id`
y `demo_build` lo pasa como `preferred_id`: el build abre ese circuito
directo, sin listar ni buscar por título, y lo reemplaza en limpio. Si el id
ya no existe, cae al match por título de siempre. Verificado en vivo:
`siete-segmentos` reconstruido al 100% en `gfgLntRuWJv` sin crear diseño
nuevo (el dashboard siguió con 19 diseños).

## Fase 24: 74HC595 + display 7 segmentos (2026-11-14)

Contador 0-9 en el mismo display, pero los 7 segmentos ya no cuelgan de 7
pines del Uno: los maneja un 74HC595 (`kBGbtwAbFlz`, 100%) con tres pines
(DS, SHCP, STCP). Oráculo: `TEST:595=LISTO` + `TEST:DIGITO=0..9`.

Hallazgos en vivo:

- **El integrado también puede ir libre**: did 116695, 16 terminales
  (`Q0..Q7`, `Q7S`, `DS`, `SHCP`, `STCP`, `OE`, `MR`, `Vcc`, `GND`). Se
  coloca en `x=560, y=-230`, a la izquierda del display y a la misma altura,
  y se cablea directo a sus terminales. No hace falta montarlo en la placa
  ni resolver su geometría de huecos.
- **Nombres de pin**: `inspect` dice `Q0`, `DS`, `SHCP`, `STCP`, `OE`, `MR`,
  `Vcc`, `GND`; el cableado guardado usa nombres humanos (`Output 1`... por
  `Q0`, `Input` por `DS`, `Shift Register Clock` por `SHCP`, `Output Register
  Clock` por `STCP`, `Output Enable` por `OE`, `Shift Register Clear` por
  `MR`, `Power`, `Ground`). Sin esos alias la conectividad medida fue 40%
  aunque el circuito ya funcionaba en simulación.
- **`Vcc` no puede caer al alias genérico**: el alias general convierte
  `Vcc` en `vcc` y la net deja de coincidir con la fixture. El tipo
  `shift-register` fija `Vcc` -> `Vcc`.
- **Anodo comun otra vez**: la tabla del sketch se emite ya invertida
  (`0x40` para el 0, `0x00` para el 8) y se manda con
  `shiftOut(DS, SHCP, MSBFIRST, ...)` + pulso de latch en STCP.
- Verificación visual: el display mostró 4 mientras el serial emitía
  `TEST:DIGITO=4`; en la corrida por MCP se vieron 3, 6 y 9 con su serial
  correspondiente.

## Fase 25: compuertas lógicas — media suma (2026-11-14)

Primer circuito con lógica discreta: la SUMA sale de un XOR (74HC86) y el
ACARREO de dos NAND (74HC00) en cascada — el primero hace NAND(A,B) y el
segundo, con sus dos entradas atadas, lo invierte a AND. Circuito
`4z8ZkFcpmuC`, 100%, oráculo `TEST:LOGICA=LISTO` + `TEST:HA=a,b,suma,acarreo`
con la tabla completa:

| A | B | SUMA | ACARREO |
|---|---|---|---|
| 0 | 0 | 0 | 0 |
| 0 | 1 | 1 | 0 |
| 1 | 0 | 1 | 0 |
| 1 | 1 | 0 | 1 |

Hallazgos en vivo:

- **Las compuertas también van libres**: 74HC86 (did 116727) y 74HC00 (did
  116696) son DIP de 14 pines; se colocan en el apilado de integrados
  (`x=560`, desde `y=-230` hacia arriba de 200 en 200) y se cablean a sus
  terminales reales. Cero geometría de huecos.
- **Nombres de pin**: `inspect` dice `1A`, `1B`, `1Y`, `Vcc`, `GND`; el
  cableado guardado los etiqueta `Input 1A`, `Input 1B`, `Output 1`, `Power`
  y `Ground`. Sin alias por tipo la conectividad mide 36.4% con el circuito
  perfecto; con alias, 100%.
- **El alias genérico vuelve a morder**: `Power` caía a `vcc` y `Ground` a
  `gnd`, en minúscula, mientras la fixture usa `Vcc`/`GND`. Cada tipo fija
  los suyos.
- **No existen 74HC08/74HC32/74HC04 en el drawer**, aunque el catálogo local
  del puente los liste. Con NAND se construyen NOT, AND y OR (De Morgan),
  así que la fase usa NAND como universal.
- Los LEDs de suma y acarreo se verifican con el serial (no por brillo):
  en la captura, con A=1 y B=1, el LED de acarreo es el encendido
  (promedio de rojo 184 vs 143 del apagado).

Nota para el proyecto real: el mismo patrón sirve para cualquier combinación
(comparadores, sumadores completos, decodificadores) sin depender de chips
que Tinkercad no tiene.

## Fase 26: biestable D 74HC74 (2026-11-14)

Segundo circuito de lógica secuencial: el 74HC74 se cablea como biestable T
(1D atado a 1NQ) y el Uno le da el reloj. Cada flanco de subida debe
invertir Q. Circuito `euU4CI6HwhX`, 100%.

Oráculo: el sketch imprime cada muestra (`TEST:FF=1`, `TEST:FF=0`...) y un
veredicto calculado por él mismo, `TEST:FF=TOGGLE-OK`, que exige que cada
muestra difiera de la anterior. No depende del estado inicial.

Hallazgos en vivo:

- **El registro también va libre**: 74HC74 (did 116725), 14 pines, en el
  apilado de integrados (`x=560`, `y=-230`). 1RD y 1SD a 5V (inactivos);
  la mitad 2 se deja estable con 2D y 2CP a GND y 2RD/2SD a 5V.
- **Nombres de pin**: `inspect` dice `1D`, `1CP`, `1RD`, `1SD`, `1Q`, `1NQ`;
  el guardado los etiqueta `Input 1`, `Clock 1`, `Reset 1`, `Set 1`,
  `Output 1`, `Inverted Output 1`. Sin alias, conectividad 28.6%.
- **Leer Q antes del primer pulso no es fiable**: el pin flota hasta que el
  biestable arranca y el primer `digitalRead` puede devolver cualquier cosa,
  así que un veredicto que compare contra esa lectura previa da FAIL aunque
  la secuencia sea correcta. El oráculo compara solo muestras consecutivas.
- Verificación en vivo: 8 muestras alternando 1,0,1,0,1,0,1,0 y
  `TEST:FF=TOGGLE-OK`.

Con esto quedan cubiertos los dos bloques combinacional (fase 25) y
secuencial (fase 26) antes del 555 y los contadores.

## Fase 27: 555 en astable (2026-11-14)

Reloj de ~14 Hz con el 555: R=10k de Vcc al nodo de tiempo, C=10uF del nodo
a GND y DIS/THR/TRIG atados al nodo (astable de una sola resistencia).
Circuito `abIk7XRpSR4`, 100%.

Oráculo: el Uno mide con `pulseIn` y emite la evidencia completa:
`TEST:555=ALTO,73173`, `TEST:555=BAJO,427`, `TEST:555=FREQ,13.6` y el
veredicto `TEST:555=OK` (alto 40..200 ms y periodo 40..400 ms).

Hallazgos en vivo:

- **Los valores se fijan por prefijo, no por unidad**: el cuarto argumento
  de `setProperty` es el prefijo. `resistance=10` con `k` da 10 kΩ y
  `capacitance=10` con `u` da 10 µF (el modelo guarda `unit: "ohm"/"F"` y
  `prefix: "k"/"u"`). Los presets del runner ahora pasan `unit` opcional,
  sin cambiar la forma de los presets que no lo usan.
- **El capacitor también va libre**: sus dos patas se cablean por terminal
  (`c1.1`, `c1.2`), así que no hace falta conocer el paso de huecos de la
  placa. Comparte el apilado de integrados (`x=560`, de 200 en 200).
- **Nombres de pin del 555**: `inspect` dice `CTRL/Reset/OUT/THR/GND/DIS/
  TRIG/Vcc`; el cableado guardado usa `Power`, `Reset`, `Ground`,
  `Discharge`, `Threshold`, `Trigger`, `Out` y `Control`. Sin alias, la
  conectividad daba 0%.
- **Medición real**: alto 73.17 ms (teórico 69.3 ms), bajo 427 µs (descarga
  por el transistor interno) y 13.6 Hz. El `pulseIn` del simulador es
  fiable a esta escala; el timeout de 500 ms acota el peor caso (555 que no
  oscila) a 1.5 s dentro de la ventana de 5 s.

Con esto queda la familia de tiempo: compuertas (fase 25), biestable (26) y
555 (27). Falta el contador para cerrar el bloque del proyecto real.

## Fase 28: contador binario 4 bits 74HC93 (2026-11-14)

Contador completo con display binario: Q0 se cablea a CP1 (ripple), el Uno
da el reloj en CP0 y pulsa el reset en MR1/MR2. Los cuatro bits encienden
un LED con su resistencia. Circuito `fCB0eO8cBbn`, 100%.

Oráculo: el sketch resetea, da 16 flancos de bajada y tras cada uno imprime
el nibble en decimal; el reporte tiene la secuencia exacta:

| Pulsos | 1 | 2 | 3 | ... | 14 | 15 | 16 |
|---|---|---|---|---|---|---|---|
| `TEST:CONTADOR=` | 1 | 2 | 3 | ... | 14 | 15 | 0 |

Cierra con `FIN`.

Hallazgos en vivo:

- **El 74HC93 no trae el ripple interno**: hay que cablear Q0 -> CP1 a
  mano; CP0 solo mueve el bit 0. Con Q0 a CP1 el contador llega a 15.
- **El reset es activo en alto y hay dos (MR1 y MR2)**: ambos al mismo pin
  del Uno, que el sketch pulsa al arrancar. Sin ese reset el estado inicial
  depende del simulador.
- **Etiquetas del guardado**: `Clock 0`, `Clock 1`, `Reset 1`, `Reset 2`,
  `Output Bit 0..3` y `Power`/`Ground`. Sin alias, conectividad 33.3%.
- **Emparejamiento LED-resistencia**: el layout empareja el LED con la
  resistencia que está en la net del **ánodo**. Con la resistencia en el
  cátodo (como en la media suma) el layout las trata como bloques sueltos y
  los cables salen diagonales. Poniendo R en el ánodo, cada LED queda justo
  encima de su resistencia y el cable es vertical de 2 filas.
- El `loop` sigue dando pulsos lentos (1.2 s por cuenta) sin serial: así la
  captura muestra los LEDs contando en binario (en t=3 s estaba encendido
  solo el LED de Q1: cuenta 2).

Con esto queda cubierta la familia del proyecto: compuertas, biestable,
tiempo (555) y conteo.

## Ajuste de layout: integrados libres en fila (2026-11-14)

Los integrados que no caben en la placa iban apilados en la misma `x`
(`y=-230, -430, -630`). Con tres compuertas eso deja una torre de chips y
el mazo de cables sube en una columna: en la media suma se veía como un
poste encima del hueco entre el Uno y la placa.

- Tinkercad **no tiene** breadboard mediana ni grande: `Breadboard` y
  `Breadboard Large` no existen en el drawer; solo `Breadboard Small`
  (did 111211, 30 columnas). Por eso no se pueden montar los integrados
  en placa sin sacrificar los LEDs.
- Regla nueva: varios integrados van en **fila horizontal** sobre la placa
  (`x=560 + 200*i`, `y=-230`). El router reparte cada chip por el bus
  superior con una bajada corta, en peine.
- Circuito afectado y reconstruido: `media-suma-logica` (`4z8ZkFcpmuC`),
  100%, tabla de verdad completa (`TEST:HA=0,0,0,0` ... `1,1,0,1`).
  Los circuitos de un solo integrado no cambian de posición.

Lección: el apilado vertical solo funciona para dos piezas; de tres en
adelante conviene una fila (o una rejilla) porque el cableado del puente
vive en carriles horizontales.

## Fase 29: carrusel de 4 LEDs con 74HC4017 (2026-11-14)

Primer circuito donde el chip hace la secuencia solo: el 4017 es un
contador Johnson con salidas one-hot y Q4 cableado a `MR` (reset). El
Uno únicamente da el reloj en `CP0` y lee qué salida está activa; la
vuelta en 4 pasos es hardware, no software. `CP1n` (clock enable activo
en bajo) va a GND o el contador no avanza.

- Circuito: `carrusel-4017` (`ij6ypc8wB5x`), 100% de fidelidad.
- Oráculo serial completo en la ventana del runner (10 líneas):
  `TEST:4017=LISTO` + `1,2,3,0,1,2,3,0` + `FIN`.
  Con `step_ms=500` el ciclo son 4 s y el `FIN` se queda fuera de los
  5 s del runner; con 400 ms cierra en 3.3 s. Es la misma lección de la
  fase 28, ahora parametrizada en el default del sketch.
- Evidencia visual: se comparó el brillo del cuerpo de cada LED contra el
  estado apagado. En t=1 s enciende el LED4 (+11 de brillo medio) y en
  t=2 s el LED2, con los otros tres en el valor apagado: el carrusel
  avanza de uno en uno. En este simulador un LED rojo encendido se ve
  sólo un poco más brillante, por eso la comprobación es numérica y no
  a ojo.
- Alias del guardado (descubiertos en vivo): `Power`, `Ground`, `Clock`,
  `Clock Enable`, `Reset` y `Output 1`..`Output 10`, donde `Output 1` es
  Q0 y `Output 5` es Q4. Sin alias la conectividad se queda en 33.3%.

Lección: un contador con reset por realimentación de la última salida
(Q4 -> MR) es el patrón para cualquier anillo de N pasos; el Uno no
necesita saber cuántas salidas hay, sólo leer las que usa. Y las
etiquetas del 4017 están numeradas 1..10, no 0..9: un alias corrido un
paso convierte el anillo de 4 en uno de 3 o 5.

## Fase 30: faro automático con relé SPDT y LDR (2026-11-14)

Primer circuito que conmuta una carga: el LDR decide, un NPN mueve la
bobina del relé y el contacto alimenta una bombilla.

- Circuito: `faro-rele-ldr` (`aF67dwSGoqC`), 100% de fidelidad.
- El pin del Uno **no** puede con la bobina: el driver es NPN con
  resistencia de 1k en la base, emisor a GND y diodo de recirculación
  entre `COIL1` y `COIL2`.
- Contactos medidos en vivo (`bDUH17ymla2`): `COM1-R1` está **abierto**
  en reposo y cierra al energizar; `COM2-R2` está **cerrado** en reposo
  y abre al energizar. El faro usa el polo NA.
- Oráculo de 16 líneas: `TEST:FARO=LISTO`, cuatro veces
  `TEST:LUZ=6` / `TEST:RELE=ON` / `TEST:FOCO=1`, luego `TEST:RELE=OFF` /
  `TEST:FOCO=0` y `TEST:FARO=FIN`. El `FOCO` no es una suposición: `A1`
  está cableado al nodo del contacto, así que 1 significa que el
  contacto cerró y 0 que abrió. Esa es la forma de tener oráculo serial
  de un actuador que no habla.
- Verificación visual: bombilla encendida (glow amarillo) en t=1 s.
- Alias del guardado: el relé usa la numeración física `Terminal 1..12`
  (COIL1=8, COIL2=5, COM1=12, R1=6, COM2=1, R2=7) y la bombilla
  `Terminal 1/2`. Sin alias la conectividad se cae a 0.
- Rele y bombilla van libres en la fila de partes libres (`x=560`,
  `x=760`, `y=-230`): el relé tiene dos filas de terminales y el vidrio
  de la bombilla taparía la placa.

Pendiente que se ve en la captura: las nets de 5V y GND con tres o más
extremos cruzan el lienzo de lado a lado. Un humano usaría los rieles de
la protoboard.

Lección: un actuador sin salida propia necesita un nodo sensado (aquí
`A1` en el contacto) para que el serial pueda afirmar algo; el brillo
del píxel no es oráculo.

## Fase 31: rieles de la protoboard para 5V y GND (2026-11-14)

En el faro las nets de 5V y GND con tres extremos salían como tiradas
largas paralelas cruzando el lienzo (se ve en la captura de la fase 30).
Un humano usa los rieles de alimentación de la placa; ahora el puente
también.

- Riel por tipo: `T+`/`B+` para 5V y `T-`/`B-` para GND, con la columna
  como sufijo (`T+11`). El puente ya aceptaba ese formato y `derive_nets`
  agrupa todas las columnas del mismo riel en un solo nodo.
- Bajada vertical: la mitad superior (f..j) baja al riel de arriba y la
  inferior (a..e) al de abajo, siempre en la **misma columna** del hueco,
  para que el cable sea vertical y no cruce el cuerpo de la placa.
  Las partes libres (relé, bombilla) siempre al riel de arriba.
- Un solo cable del Uno al riel por tipo (`uno.5V -> T+1`,
  `uno.GND1 -> T-1`) y, si se usan los dos rieles del mismo tipo, un
  puente en la columna 30 (borde derecho).
- Cada tap toma una columna libre: dos cables al mismo hueco se dibujan
  como uno y el puente no garantiza aceptar dos terminales en el mismo
  punto. Las columnas se asignan en orden de endpoint, no de declaración,
  para que reordenar las nets no cambie el cableado.
- El riel es **opt-in** por fixture (`"wiring": "rails"`). El default
  sigue siendo la estrella desde el pin del Uno: está verificada en los
  23 circuitos y cambiar su topología por gusto es riesgo sin ganancia.
  Solo se aplica al tipo de alimentación que aparece en dos o más nets;
  con una sola net no hay tiradas que evitar y el riel solo agrega cables.
- Circuito reconstruido: `faro-rele-ldr` (`aF67dwSGoqC`), 100% de
  fidelidad, mismo oráculo de 16 líneas y bombilla encendida. Comparado
  contra la captura anterior: desaparecen las tres tiradas rojas y las
  tres negras que cruzaban la placa.
- Verificación del riel inferior: la conectividad al 100% exige que
  `B+22` (5V del LDR) y `T+11` (cátodo del diodo) sean el mismo nodo, y
  eso solo pasa si el puente `T+30 - B+30` está cableado. El serial no
  puede demostrarlo solo porque a oscuras el divisor del LDR lee ~0 con
  y sin 5V.

Lección: los rieles son la forma humana de repartir alimentación; el
puente ya sabe rutear por carriles, pero solo si el extremo es un riel o
un pin del Uno. Y la decisión de usar riel es del circuito, no de la net:
una net de 4 extremos sigue siendo un mazo corto desde el pin; varias
nets de 5V son las que se ven mal.

## Fase 32: alarma de movimiento con PIR (2026-11-14)

Primer sensor **sin valor fijo**: el PIR no mide una magnitud, entrega un
nivel cuando algo se mueve dentro de su cono. Eso rompe el supuesto del
runner (arrancar la simulación y leer el serial), porque el estímulo no lo
puede dar el sketch.

- Circuito: `alarma-pir` (`dgFz6r0k1xV`), 100% de fidelidad, con rieles
  (tres nets de GND y una de 5V).
- El PIR va libre (`x=560, y=-230`); buzzer en la columna 24 (disco
  grande), resistencia + LED en 1g/5i.
- Sketch: `pinMode` del PIR, `tone`/`noTone` en el buzzer y LED en D4. No
  imprime en cada vuelta: **solo cuando el estado cambia**, además del
  estado inicial. El serial queda como bitácora, no como muro de ceros.
- Oráculo del runner (5 s, reposo): `TEST:PIR=LISTO` + `TEST:MOV=0`.
- Oráculo con estímulo (`scripts/pir_stimulus.py`): al seleccionar el PIR
  aparece su cono de detección con un punto arrastrable; al arrastrarlo
  dentro del cono el serial pasa a `TEST:MOV=1`, y al soltarlo vuelve a
  `TEST:MOV=0`. Secuencia completa verificada: reposo → movimiento →
  reposo.
- Verificación visual: el LED de D4 pasa de brillo 137 a 152 y su cuerpo
  se ve saturado en la captura del momento de detección.
- Alias del guardado: `Signal`/`Power`/`Ground` (inspect devuelve
  `out`/`vcc`/`gnd`). Sin alias la conectividad se cae.

Lección: para un sensor de evento el oráculo no es "leer un valor" sino
"provocar el evento y leer la transición". El paso de interacción vive en
un script propio (`scripts/pir_stimulus.py`) y no en el runner: el runner
sigue siendo ciego a la interacción, y por eso el reporte guarda el
reposo mientras la evidencia del movimiento queda en una corrida aparte,
con su screenshot. Prometer en el reporte algo que el runner no puede
observar sería mentir con formato.

## Fase 33: cerradura con teclado 4x4 (2026-11-14)

Segunda capacidad de **entrada** y la primera matriz: el teclado 4x4 no
tiene pines de alimentación, son cuatro filas y cuatro columnas que hay
que barrer.

- Circuito: `cerradura-teclado` (`g3KZdQc0DFu`), 100% de fidelidad, con
  rieles. Filas a D2..D5, columnas a D6..D9, LED de apertura en D10 y de
  rechazo en D11, cada uno con su resistencia.
- Barrido sin librería: `INPUT_PULLUP` en las columnas, una fila en LOW
  por vuelta, `delay(2)` para que el pin se estabilice. No se usó
  `<Keypad.h>` porque no está verificado en el simulador.
- **Hallazgo en vivo:** el simulador solo cierra la matriz mientras el
  botón del mouse está **presionado**. Un click suelto, un doble click o
  un click seguido de lectura no registran nada; hay que mantener
  (`mouse.down()`, esperar, `mouse.up()`). Y como la tecla queda cerrada
  todo ese tiempo, el sketch **espera a que se suelte** antes de devolver
  el carácter: una pulsación mantenida vale una sola tecla. Sin esa espera
  la misma tecla se reporta decenas de veces y la clave nunca cierra.
- Mapa físico medido pulsando las 16 teclas: la matriz es fila-mayor,
  `f1c1`=1 ... `f1c4`=A, `f4c1`=*, `f4c4`=D. No hay sorpresa de cableado.
- Oráculo del runner (5 s, reposo): `TEST:KP=LISTO` +
  `TEST:CLAVE=ESPERANDO`. El teclado necesita manos, así que el oráculo
  real lo produce `scripts/keypad_stimulus.py`: mantiene 1-2-3-4 y lee
  `TEST:TECLA=1..4` + `TEST:CLAVE=OK`; luego 1-1-1-1 y lee
  `TEST:CLAVE=FALLA`.
- Verificación visual por píxel (los LEDs rojos del simulador apenas se
  distinguen a ojo): con la clave correcta el LED de D10 sube de brillo
  medio 126 a 135 y el de D11 queda en 94; con la incorrecta, D11 sube a
  115 y D10 baja a 126.
- Alias del guardado: `Row 1..4` / `Column 1..4` (inspect devuelve
  `row1..4` / `column1..4`).

Lección: un componente de entrada no se verifica leyendo, se verifica
accionándolo. Y cuando el estímulo es una pulsación, la duración importa:
el simulador no tiene "click", tiene "botón abajo". El sketch tiene que
estar escrito para eso, no para un teclado ideal.

## Fase 34: caja fuerte con teclado y LCD (2026-11-14)

Primer circuito que **integra dos bloques** ya verificados por separado:
entrada matricial (teclado 4x4) y salida de texto (LCD 16x2 en 4 bits).

- Circuito: `clave-lcd` (`9wyFlvHHzIo`), 100% de fidelidad, con rieles.
- Reparto de pines: el teclado ocupa D2..D9 y el LCD los analógicos
  A0..A5. No alcanzan los digitales libres para los dos, y se verificó en
  vivo que `LiquidCrystal` sobre A0..A5 funciona como digital (sonda
  `6cqYV514HA4`: el display mostró "PINES A OK / t=1s" y el serial imprimió
  el contador). Ese sondeo fue barato y evitó diseñar a ciegas.
- El LCD muestra la clave enmascarada (`*` por tecla) y el resultado
  (`ABIERTO` / `DENEGADO`); el serial imprime además
  `TEST:PANTALLA=<texto>` para que el oráculo no dependa de leer píxeles.
- Oráculo del runner (5 s, reposo): `TEST:KP=LISTO` +
  `TEST:CLAVE=ESPERANDO`. Con estímulo (`scripts/keypad_stimulus.py`):
  1-2-3-4 → `TECLA=1..4`, `CLAVE=OK`, `PANTALLA=ABIERTO`; 1-1-1-1 →
  `CLAVE=FALLA`, `PANTALLA=DENEGADO`. Verificado también en la captura del
  display en los dos estados.
- El estímulo espera 1.8 s entre intentos: el sketch bloquea 1.5 s
  mostrando el resultado y la primera tecla del intento siguiente se
  perdía. Es el mismo patrón que la ventana de 5 s del runner: el sketch
  tiene que caber en el tiempo del que lo observa.
- Regla de rieles afinada: un tipo va por riel si aparece en **dos o más
  nets** o si su net tiene **tres o más extremos**. Antes solo miraba lo
  primero, y este circuito tenía un único 5V con tres consumos (el LCD, su
  retroiluminación y el Uno) que se dibujaba como tirada larga. Los otros
  tres circuitos con riel conservan su cableado exacto (19, 10 y 15
  cables).

Nota de diseño: la versión anterior de esta fase incluía un **servo** como
cerrojo. Se descartó tras verlo montado: en una placa densa el cuerpo del
servo tapa los taps del riel (parece desconectado) y su cable de señal
rodea el Uno entero porque los pines digitales están arriba y el servo
abajo. El servo ya está verificado en dos circuitos; integrarlo pide
colocación libre de partes grandes, que es trabajo aparte.

Lección: integrar no es sumar cables, es repartir recursos. El pin, la
columna y el riel son escasos, y el primer choque aparece ahí, no en el
código. Y cuando una parte no encaja, sacarla del circuito es una decisión
de diseño válida; maquillarla con un cable largo, no.

## Fase 35: partes libres y control de acceso (2026-11-14)

Cierra la deuda que dejó la fase 34: una parte grande puede salirse de la
placa sin quedar colgada en un sitio arbitrario.

- Circuito: `control-acceso` (`cjjQKLuBQ2I`), 100% de fidelidad, con
  rieles. Teclado en D2..D9, LCD en 4 bits sobre A0..A5 y servo en D10.
- **API nueva en la fixture:** `"free_parts": ["sv1"]`. Es opt-in, como
  `"wiring": "rails"`: un servo montado en la placa ya está verificado en
  `servo-potenciometro` y `parking-servo-ultrasonico-rgb` y no se mueve.
- **Dónde va una parte libre:** a la derecha de la placa y a la altura de
  la placa (`x=1250`, `y=60`), apiladas hacia abajo de 200 en 200. No es
  una corazonada: se midió en vivo con tres servos en el mismo circuito
  (sonda `1altWwNOQdW`). En `(1250,-230)`, la fila del display, el cable
  de señal lo cruza; en `(560,-430)` el cuerpo del servo se monta **encima
  del teclado** (los cuerpos miden ~200 unidades de alto, no 200 de fila
  libre); en `(1250,60)` el cable corre por debajo de la placa sin tocar
  nada.
- **Riel según altura:** una parte libre con `y > 0` baja al riel de
  **abajo** (`sv1.Power -> B+29`, `sv1.Ground -> B-29`); las que viven
  encima de la placa siguen bajando al de arriba. La columna propuesta se
  limita a 29 porque la 30 está reservada al puente de borde: pedirla hacía
  que el asignador diera la vuelta y bajara el servo en la columna 1, al
  otro extremo.
- **Pines del servo libre:** `Ground` / `Power` / `Signal`, los mismos
  nombres que ya usa el montaje en placa; sin alias la conectividad no
  cierra.
- Oráculo del runner (5 s, reposo): `TEST:KP=LISTO` +
  `TEST:CLAVE=ESPERANDO` + `TEST:SERVO=0`. Con estímulo: 1-2-3-4 →
  `TECLA=1..4`, `CLAVE=OK`, `SERVO=90`, `PANTALLA=ABIERTO`; 1-1-1-1 →
  `CLAVE=FALLA`, `SERVO=0`, `PANTALLA=DENEGADO`. El asta del servo se ve
  girada a 45° en la captura de ABIERTO y vertical en la de cerrado: el
  actuador se verifica moviéndose, no leyendo un número.
- El estímulo ya no lee el serial a media impresión: `_linea_completa`
  sondea hasta que `PANTALLA=` tiene valor entero (antes leyó `A` en vez de
  `ABIERTO`). Y si el sketch escribe la pantalla, el oráculo la exige: el
  display no se aprueba solo con la captura.

**Deuda que sigue abierta al cerrar la fase (resuelta en la 36):** las 16
terminales del LCD 16x2 miran hacia **arriba**, y el módulo va encima de la
placa. El puente dibujaba la bajada del terminal al riel en vertical, así
que ese tramo pasaba por detrás del cuerpo del display: los cables
aparecían saliendo por el borde inferior en vez de nacer en su pin. Se veía
igual en `lcd-contador`, `lcd-temperatura`, `lcd-distancia`, `clave-lcd` y
aquí. El arreglo no era mover el display solo: era que el ruteo de una
parte libre salga primero de lado y después baje, y eso se hizo en la fase
36 (abajo).

Lección: una parte libre no se coloca "donde sobre sitio", se coloca donde
su cable no cruce nada. Y el criterio hay que medirlo con el cuerpo real:
los cuerpos son más altos que el paso de la fila, así que apilar de 200 en
200 en la misma x no garantiza nada.

## Fase 36: el LCD sale de lado (2026-11-14)

Cierra la deuda de la fase 34/35. El arreglo tiene dos mitades, y las dos
se midieron antes de escribirlas.

- **Puente (`tinkercad-mcp`):** una parte libre con terminales arriba sale
  primero **de lado** y después baja. La tabla `FREE_ESCAPE` (por `did`)
  escribe el desplazamiento una sola vez en Python y se inyecta en el JS
  que corre en la página, así que se puede testear sin abrir navegador.
  El escape se mide desde el **origen** de la parte, no desde el pin: cada
  pin daría una `x` distinta y el abanico cruzaría a los vecinos. Y se
  escalona 8 unidades por carril para que dos cables no se dibujen uno
  encima del otro.
- **Layout:** el LCD pasa de `x=870` a `x=1100` (`LCD_FREE_X`). En 870 el
  teclado de `clave-lcd` queda a 310 unidades y el abanico de salida le
  pasa por encima al cuerpo; en 1100 hay ~390 de aire a su izquierda. El
  display de 7 segmentos **no** se mueve (sus terminales miran abajo) y
  sigue en 870. El apilado sigue siendo compartido entre tipos: un LCD y un
  display en el mismo circuito nunca comparten altura, aunque ya no
  compartan columna.
- **Taps del riel:** el asignador busca la columna libre más cercana a la
  propuesta (`proposed, +1, -1, +2, -2...`) en vez de avanzar solo a la
  derecha y dar la vuelta al llegar al final. Antes, los cuatro GND del LCD
  caían en `T-2..T-4`, al otro extremo del riel y con cables cruzando toda
  la placa; ahora caen en `T-26..T-29`, junto a su parte. La columna 30
  sigue reservada al puente de borde.
- **Verificado en vivo:** los cinco circuitos con LCD reconstruidos al
  100%: `lcd-contador` (`cpySiVSE9vr`), `lcd-temperatura` (`9hZJgbsYOC5`),
  `lcd-distancia` (`blN5d8qCr2z`), `clave-lcd` (`9wyFlvHHzIo`) y
  `control-acceso` (`cjjQKLuBQ2I`). En las capturas los cables nacen en el
  borde superior del módulo, salen por la izquierda del cuerpo y bajan sin
  pasar por detrás del display. Suite del cerebro 1786 verdes; puente 252.

**Deuda que sigue abierta al cerrar la fase (resuelta en la 37):** en
`lcd-distancia` un cable turquesa termina detrás del cuerpo del HC-SR04.
Se comprobó que **no** lo causa el escape: reconstruir el circuito con
`FREE_ESCAPE = {}` deja esa línea idéntica (misma captura). El cuerpo del
sensor está sobre las filas altas y el cable llega desde arriba. Al
instrumentar los puntos de ruta por cable se vio que la línea sale del
hueco `5g` (pin 2 de la resistencia del LCD), que queda dentro del cuerpo.
La fase 37 lo cierra moviendo el cuerpo, no el cable.

## Fase 37: el piezo cede la placa (2026-11-14)

Cierra la deuda de la fase 36. El diagnóstico salió de los puntos de ruta
reales, no de mirar la captura: el cable que "terminaba" en el sensor era
`5g -> lcd1.LED+`, y `5g` es el pin 2 de la resistencia de backlight del
LCD, que cae debajo del cuerpo.

**Geometría medida** (captura + calibración con los rieles, escala ≈0,74
px/unidad): el cuerpo del HC-SR04 se dibuja unos 17 huecos de ancho
alrededor de sus cuatro pines, 7 columnas a la izquierda de `vcc` y 10 a
la derecha, y tapa las filas altas `j..f`. Con el sensor en `10d` esa
sombra es `3..20`, justo donde cae `5g`.

**Por qué no alcanzaba con mover el hueco.** El carril lo elige la parte
libre (el LCD está en `y=-230`, así que todos sus cables van por arriba),
no el hueco. Cualquier hueco dentro de `3..20` obliga al cable a subir por
dentro del cuerpo hasta el carril; bajarlo a la fila `e` solo alargaba el
tramo escondido. El cuerpo es el que tiene que moverse.

**La regla nueva:** dos cuerpos grandes no comparten placa. El piezo tiene
dos cables y se va libre a la derecha (`FREE_RIGHT_X/Y` = 1250/60, el
mecanismo de la fase 35); el sensor recupera la columna 18, que es la
posición verificada en vivo donde su cuerpo no tapa nada. Se retiró
`ULTRASONIC_MIN_COLUMN_WITH_PIEZO`: el sensor ya no negocia su columna con
el piezo.

- **Puente de pines:** el piezo entra en `_FREE_PART_PINS` con sus
  terminales reales (`+` y `-`), los mismos que usa montado en la placa.
- **Color:** `_wire_group` trataba cualquier extremo que termina en `+`
  como alimentación. Con el piezo libre eso pintaba de rojo el cable de
  `uno.D8 -> buzzer1.+`, que es una señal. Ahora `+`/`-` son
  alimentación/tierra solo si la parte es una fuente real (`bat1`); el
  positivo del piezo sigue la paleta de señal (verde) y su negativo es
  negro por venir de `uno.GND1`.
- **Verificado en vivo:**
  - Los 27 model calls comparados contra `HEAD` con el código anterior en
    un worktree: **solo cambia `lcd-distancia`**. Los otros dos circuitos
    con sensor (`sensor-ultrasonico`, `parking-servo-ultrasonico-rgb`) no
    tienen piezo y su cableado es idéntico byte a byte.
  - `lcd-distancia` (`blN5d8qCr2z`) reconstruido al 100% con el oráculo
    completo (`TEST:LCD=LISTO`, `TEST:DIST=110.1..110.3`,
    `TEST:ALARMA=ON`). En la captura el pin 2 de la resistencia se ve, el
    cable azul sube por la columna 5 fuera del cuerpo del sensor, y el
    piezo libre se cablea en verde/negro sin cruzar nada.
  - `sensor-ultrasonico` y `parking-servo-ultrasonico-rgb` reconstruidos
    al 100% (sin cambios de spec, como prueba de que el builder sigue
    sano).
  - Cerebro 1798 verdes + 5 skip + 1 xfail; puente 252.

**Lección:** si el carril lo decide un extremo, mover el otro extremo no
cambia la ruta: hay que mover el cuerpo que estorba. Y una terminal con
nombre `+` no es una fuente: el color tiene que mirar el tipo de parte.

## Fase 38: documentación dentro del circuito y contador 555 con compuertas (2026-11-14)

Dos entregas en una fase: el diseño guardado empieza a explicarse solo, y el
circuito 28 junta cuatro piezas que hasta ahora vivían separadas (555,
compuertas y display).

### 38a · `circuit_doc`: la explicación viaja dentro del proyecto

El circuito se puede reabrir en Tinkercad, pero la explicación vivía solo en
`docs/reportes/`. Ahora `demo_build` le antepone al sketch un bloque de
comentario generado **desde la propia fixture**: título, piezas, cableado net
por net y el oráculo serial con el que se verifica. Al abrir el editor de
código del diseño se lee qué hace y cómo está cableado, y como sale de la
fixture no puede desincronizarse del dibujo.

- `render_circuit_doc(fixture)` arma las líneas; `documented_code(fixture, code)`
  las envuelve en `/* ... */` y deja el sketch intacto debajo.
- Es idempotente (marca `/* === DOCUMENTACION DEL CIRCUITO ===` al inicio):
  documentar dos veces no duplica.
- `select_code` sigue devolviendo el sketch puro, así los tests que fijan el
  texto exacto no cambian.
- El reporte Markdown guarda el mismo bloque (`## Documentación embebida`),
  para leerlo desde el repo sin abrir el navegador.
- Campos nuevos y opcionales en la fixture: `doc` (párrafos), `oracle`
  (líneas del oráculo), `notes` (advertencias). Sin ellos, el bloque se arma
  con el título, las piezas y las nets: las 28 fixtures quedan documentadas.

### 38b · Contador 0-7 lento con reloj 555 y compuertas AND/OR/XOR

`jApuXFjHQsc` (100%): `uno, t1 (555), r1, c1, u1 (74HC00), u2 (74HC86),
btn1, seg (7 segmentos)`, con rieles.

**Por qué el decodificador va en software.** Se probó el drawer con
`Seven Segment Decoder`, `BCD to 7 segment decoder`, `7447`, `4511` y
`7 segment decoder`: **no existen** en Tinkercad. Decodificar 3 bits a los 7
segmentos con NAND cuesta ~50 compuertas (13 chips de 4), y con 13 cuerpos el
lienzo deja de ser un circuito para volverse un peine de cables. La decisión
honesta: las compuertas hacen trabajo real en la **cadena del pulso** (que es
donde un AND y un OR tienen sentido) y la tabla del display queda en el
sketch.

**Cadena de reloj:**

```
555 OUT --+--> NAND(u1.1) --> XOR(u2.1, pata a 5V) = AND(reloj, MARCHA) = pulso
          |                        |
          |                        +--> NAND(u1.3) = NOT pulso
          |                                            |
btn1 -----+--------------------------> NAND(u1.4) = OR(pulso, boton) --> D2
```

- `MARCHA` (D8) en bajo congela el conteo: el AND lo corta.
- El pulsador entra al OR y avanza un dígito a mano. Su nodo cuelga de
  **D12 con `INPUT_PULLUP`**: el pull-up interno del micro hace de
  resistencia del circuito.
- El AND se arma con NAND + XOR (una XOR con una pata a 5V es un inversor) y
  el OR con dos NAND: la forma clásica cuando solo hay NAND.

**El bug que cazó la prueba de red.** El primer cableado metía la XOR también
en el pulsador y el reposo quedaba invertido: D2 en alto sin nada apretado.
Se vio antes de construir, evaluando las compuertas net a net para las 8
combinaciones de `(reloj, MARCHA, botón)`
(`tests/test_fase38_contador_compuertas.py`). La regla que queda: *una cadena
de compuertas se prueba con tabla de verdad, no mirando el dibujo*.

**Dos resistencias = preset ambiguo.** Con la resistencia del pull-up en la
placa había dos `Resistor` y `set_component_property_model` responde
`ambiguous component name`; el preset se perdía y el 555 quedaba con su valor
por defecto. La herramienta resuelve por nombre exacto, no por ref, así que la
salida fue sacar la resistencia: `INPUT_PULLUP`.

**Layout: el display no comparte altura con la fila de integrados.** Con tres
chips (560, 760, 960) el ancla 870 caía dentro del cuerpo del tercero. Regla
nueva: si el ancla del display queda a menos de `IC_DISPLAY_CLEARANCE` (300)
de un chip, el display se corre a `max(chip_x) + 300`. Con un solo chip no se
mueve (595 en 560 → display en 870, 310 de aire, sin regresión).

**Medido en vivo:**
- Fidelidad 100% (componentes y conectividad), sin fallos de tools.
- Oráculo `TEST:COMPUERTAS=LISTO` + `TEST:DIGITO=0..7` en ciclo. Con
  `sim_wait_seconds: 20` la ventana del runner alcanza para el ciclo
  completo; con la ventana de 5 s solo entraban dos dígitos.
- Una corrida aparte de 25 s confirmó dos vueltas completas (0→7→0→5), o sea
  que la vuelta a 0 la hace el sketch con `% 8`.
- El pulso real queda en ~1,7 s por dígito (teórico 2 Hz con R=68k y C=10uF):
  el simulador es más lento que la fórmula y el valor se ajustó midiendo, no
  calculando.

## Fase 39: el display deja de estallar y los cables se reparten (2026-11-14)

El circuito 28 contaba bien y explotaba. Los dos síntomas venían del mismo
lugar: el display de 7 segmentos es de **ánodo común** (común a 5V y segmento
en LOW) y los siete segmentos colgaban de pines del Uno sin resistencia. En el
simulador eso revienta el componente; el conteo sigue, así que el oráculo
serial no lo detecta. "Funciona" y "es válido" no eran lo mismo.

### 39a · Resistencia serie obligatoria (lint en el builder)

`_series_resistor_errors` revisa las nets de dos extremos: si un segmento del
display (o el ánodo de un LED) cuelga directo de `uno.*`, de 5V/GND o de un
riel, el build falla antes de tocar Tinkercad. Si el otro extremo es una
resistencia, o la salida de un integrado (595, 555), pasa: ahí la limitación
es otra y no se opina.

Las siete resistencias son de 220Ω, una por net (`uno.Dx → rN.1`,
`rN.2 → seg.x`), y el sketch no cambia: la resistencia no toca la lógica.

### 39b · Segunda protoboard para el banco de resistencias

Ocho resistencias no caben en la placa 1 sin apilar bloques sobre los cables
(la de 555 más siete). La fixture lo pide con `"board2": ["r2", ..., "r8"]`
(opt-in, solo resistencias) y el planner devuelve `boards` con la placa 1 en
`(870, 0)` y la 2 en `(1270, 0)`; los huecos de la placa 2 viajan como
`b1/5d` y el puente acepta `bN/` en huecos y rieles.

El banco va **vertical**: `angle 0`, ancla en la fila `d` y el pin 2 cae en la
`f`. El pin 1 mira a la mitad de abajo y el 2 a la de arriba, así el cable del
Uno entra por la banda inferior y el del display sale por la superior: cada
mitad de la placa tiene su mazo. Las columnas van 1, 5, 9, ... porque los
cuerpos de las resistencias miden cuatro columnas.

Guardas: `board2` con algo que no sea resistencia, con refs inexistentes,
repetidas, o junto a `free_parts` (las partes libres de la derecha viven justo
donde va la placa 2) falla con `LayoutError`. Una resistencia del banco
tampoco puede ser la de un LED.

### 39c · Bandas por lado en el puente

Antes los carriles eran una numeración única (`115 + lane*5`): los cables
ruteados crecían en una sola zona. Ahora cada banda lleva su contador
(`sideLanes.top/bottom`, base 115, paso 8) y el lado lo decide el hueco
(fila f..j o riel T) o la `y` de la parte libre. Dos cables arriba ya no
empujan abajo.

### 39d · La identidad no puede ser el nombre

La conectividad daba 36% con el cableado perfecto: las refs se asignaban por
posición de creación y el orden físico no sigue el de la fixture (r1↔D4).
Se intentó que el nombre del dispositivo fuera la ref (`dev.setName`), pero
Tinkercad **deduplica**: con otro `r2` en el documento, `setName("r2")` deja
`r21`. Y el sufijo aparece justo al reconstruir, que es cuando importa.

La solución no es adivinar el nombre sino **preguntarlo**: el build lee el
nombre después de asignarlo y lo devuelve en `placed[ref].name`; el runner
arma `{nombre: ref}` y se lo pasa a `normalize_circuit` y `derive_nets`
(firma nueva `refs_by_name`). Los presets usan el mismo mapa, así que
`r2 = 220Ω` aterriza en `r21`.

Con eso: **100% de fidelidad**, presets aplicados sin fallos y el oráculo
`TEST:COMPUERTAS=LISTO` + `TEST:DIGITO=0..7..0` en una sola corrida
(`sim_wait_seconds: 28`). Capturas revisadas: dos protoboards alineadas, siete
resistencias verticales, mazo superior y mazo inferior separados, y el display
mostrando el dígito sin explotar.

Lección: **un actuador que explota sigue contando**. El oráculo funcional no
reemplaza la validez eléctrica; el lint tiene que estar en el camino de
construcción, no en la lista de deseos.

## Fase 40: el cable ya no roza la placa, y se mide (2026-11-14)

La fase 39 cerró con una deuda escrita a mano: "el cable de 5V/GND al display
cruza la placa 1 por el carril superior". Mirando la captura no había forma de
decidir si cruzaba o solo pasaba cerca. Se resolvió de la única manera que
sirve: midiendo.

### 40a · La holgura que faltaba

Los carriles arrancaban en `BASE_Y ± 115`. El cuerpo de la protoboard llega a
±110 (filas j..a = -55..+55, rieles -95..+95, plástico hasta ~110). Eran cinco
unidades de aire: en pantalla, un cable apoyado en el borde. Ahora la banda
arranca en **±130**.

### 40b · La parte libre también es un obstáculo

Un cable hacia/desde una parte libre sale por el carril de su banda. Si la
parte vive **dentro** de la banda (o casi sobre el borde), el carril se corre
30 más allá de la parte —pero nunca hacia la placa—. Las dos ramas hacen falta:

- Integrados y display en `y=-230`: quedan fuera de la banda, así que el
  corredor es la banda (cae limpio entre la placa y ellos). Correrlo "30 más
  allá de la parte" los mandaba a -260, cinco unidades encima de los cuerpos
  de los chips: peor que el problema.
- El piezo de `lcd-distancia` en `y=76`: correrlo 30 más allá lo metía en la
  placa (`+106 < 110`). Ahí el carril baja a la banda (+130) y sube al pin
  desde afuera.

La primera versión de esta regla tenía solo la segunda rama y el primer build
en vivo lo cantó: `uno.GND1 -> buzzer1.-` en `y=106` sobre la placa.

### 40c · La regla 3 ahora se mide

El puente devuelve en `route_debug[*].points` la polilínea completa de cada
cable ruteado (extremo → quiebres → extremo). `builder.route_band_violations`
la recorre: un tramo **vertical** puede cruzar la placa (así se entra a un
hueco, es lo normal); un tramo **horizontal** no puede caer dentro de
±125 del origen de una placa si su `x` pisa el ancho (±160).

El resultado entra en el `ok` del build y en el reporte:

```
Ruteo: 0 tramo(s) sobre una placa (31 de 31 cables medidos)
```

El contador importa: un "0 cruces" sin saber cuántos cables se midieron no es
evidencia, podría ser que no llegó ninguna polilínea.

### 40d · Lo que encontró

El lint cazó un defecto que nadie había visto y que no era el documentado:
`uno.GND1 -> buzzer1.-` pasaba por encima de la placa en `lcd-distancia`
(el cable del piezo), por la regla del corredor mal escrita. `lcd-distancia`
quedó en **OK: False** con 100% de fidelidad hasta corregirlo. Después:

| circuito | fidelidad | ruteo |
|---|---|---|
| contador-555-compuertas | 100% | 0 cruces (31/31 medidos) |
| lcd-distancia | 100% | 0 cruces (19/19) |
| control-acceso | 100% | 0 cruces (25/25) |
| siete-segmentos | 100% | 0 cruces (15/15) |
| lcd-contador | 100% | 0 cruces (13/13) |
| lcd-temperatura | 100% | 0 cruces (16/16) |
| clave-lcd | 100% | 0 cruces (22/22) |

Lección: **una deuda anotada a ojo se cierra midiendo, no mirando mejor**. Y
el instrumento encontró otra cosa distinta a la deuda anotada.

## Fase 41: el cable entre partes libres se rutea (2026-11-14)

Eddie miró el circuito 28 terminado y dijo: **"se ve un poco torcido"**. La
primera sospecha fue la alineación de los integrados y era falsa: el modelo
tenía los tres chips en la misma fila (`y=-230`, pines en `-245..-215`). Lo
torcido eran los **cables**.

### 41a · El síntoma, medido en la captura

El zoom a la fila de integrados mostró dos diagonales largas: naranja del
555 al capacitor, cian del 74HC00 al 74HC86. No eran casualidad: eran
exactamente los cables cuyos dos extremos son **partes libres**.

### 41b · La causa raíz

`plan_wire_style` (Python) y la rama equivalente del JS ruteaban solo tres
combinaciones:

- `uno ↔ placa` (hueco o riel),
- `libre ↔ placa`,
- `libre ↔ uno`.

Un cable `libre ↔ libre` caía por defecto: el puente no lo tocaba y Tinkercad
dibujaba la recta entre los dos pines. Con los pines en filas distintas, esa
recta es una diagonal larga. Eran **15 cables** en las cinco fixtures con
partes libres: temporizador-555 (3), media-suma-logica (2), biestable-d (1),
carrusel-4017 (1), contador-555-compuertas (8).

### 41c · El arreglo

El cable entre dos partes libres sale del pin, corre en horizontal hasta una
columna libre y baja/sube hasta la fila del otro pin: un **Z** de tres tramos.

- Dos partes distintas: la vertical va en la **columna del medio** entre los
  dos cuerpos (no hay carril ni placa que estorbe).
- Misma parte (dos pines del mismo integrado): la vertical va a **70 unidades
  del origen** del cuerpo (`FREE_FREE_ESCAPE`), o al `FREE_ESCAPE` declarado
  si la parte es ancha (el LCD usa −154).
- Los dos pines en la **misma fila**: no se agrega quiebre, la recta ya es
  ortogonal y se guarda la polilínea para poder medirla.

### 41d · La regla, medida

`route_debug` ahora trae la polilínea de **todos** los cables, también de los
que no se rutean (`routed: false, reason: "straight"`). Con eso el cerebro
mide cada tramo y distingue dos cosas que antes se confundían:

| Qué | Cómo se mide | Rompe el build |
|---|---|---|
| Diagonal en cable de parte libre o del Uno | `builder.diagonal_segments`, `blocking=True` | Sí |
| Salto recto entre huecos de la placa (`5g -> 8c`) | mismo lint, `blocking=False` | No (se cuenta) |
| Horizontal sobre el cuerpo de una placa | `builder.route_band_violations` (fase 40) | Sí |

El denominador del reporte cambió de "cables ruteados" a **total de cables**:
antes decía `31 de 31` escondiendo 15 que el puente no tocaba.

### 41e · El bug que apareció al medir

Con la polilínea de los cables rectos en `route_debug`, el puente empezó a
convertir cualquier `routed: false` en error de build. Resultado: el circuito
28 salía con **100% de fidelidad, cero cruces, cero diagonales y
`OK: False`**, sin decir por qué. Dos arreglos:

1. `reason: "straight"` no es un fallo; el cerebro decide si ese tramo es
   diagonal.
2. El resultado lleva un dict `checks` con cada condición y el CLI imprime
   `Fallos: build_ok` más los `build_errors` crudos. Un "OK: False" mudo es
   un defecto de diagnóstico, no un detalle.

### 41f · Verificado en vivo

Los cinco circuitos con cables libre↔libre reconstruidos con el runner
(reutiliza id, no crea duplicados):

| Circuito | ID | Fidelidad | Cables medidos | Ruteados | Diagonales | Saltos | OK |
|---|---|---|---|---|---|---|---|
| contador-555-compuertas | `jApuXFjHQsc` | 100% | 41/41 | 39 | 0 | 1 | Sí |
| temporizador-555 | `abIk7XRpSR4` | 100% | 10/10 | 10 | 0 | 0 | Sí |
| media-suma-logica | `4z8ZkFcpmuC` | 100% | 20/20 | 18 | 0 | 2 | Sí |
| biestable-d | `euU4CI6HwhX` | 100% | 14/14 | 13 | 0 | 1 | Sí |
| carrusel-4017 | `ij6ypc8wB5x` | 100% | 21/21 | 17 | 0 | 0 | Sí |

Captura del 28 con el zoom a la fila de chips: las dos diagonales ya no
están; el naranja 555→capacitor y el cian 74HC00→74HC86 ahora son Z.

Lección: **un cable que "no se ve" no es un cable que no existe**. Si el
router no lo toca, Tinkercad lo dibuja a su manera; la única forma de saberlo
es que el puente devuelva la geometría de lo que construyó y que el cerebro
la mida.

## Fase 42: el sampler mira el LED y no el plástico (2026-11-14)

El sampler de simulación (`tinkercad_simulate_samples`) existía desde la
fase 0 y nunca se había calibrado: heredaba un umbral de brillo de otra
implementación. Esta fase lo midió con datos y encontró que el problema no
era el umbral.

### 42a · El síntoma, medido

Con `blink-basico` (`2tMhkuosDyj`) la simulación arranca, el serial dice
`TEST:ON / TEST:OFF / TEST:ON` y el sampler devolvía **`on: true` en todas
las muestras**, incluidos los instantes en que el LED estaba apagado.

Un barrido de diferencias entre la captura con la simulación parada y las
capturas en marcha localizó el LED: se enciende en **(876,487)** y pasa de
`RGB(128,32,32)` a `RGB(207,132,132)` (delta 100 en el canal máximo). El
sampler medía en **(861,484)** — el promedio del ánodo (843,492) y el
cátodo (879,477).

Quince píxeles a la izquierda del LED está el **plástico blanco de la
protoboard**: brillo 208, constante, apagado o encendido. Con el umbral en
144, plástico (208) siempre gana: el sampler reportaba "encendido" un LED
que no estaba mirando. No era el umbral, era el punto.

### 42b · El cuerpo, no el hueco

El ancla de un terminal es el **hueco de la protoboard** donde entra la
pata; el LED dibujado está en otro sitio. El modelo no expone la caja de la
parte (`dev.breadboard()`, `subdevice`, `module` son modelos sin nodo), pero
el DOM sí: cada parte es un `g[id^="id_"]` y el terminal que ya se resuelve
es su descendiente.

`resolve_terminal` devuelve ahora `body` (caja en px de pantalla, vía
`getBoundingClientRect`). Para el LED: `[869,475,12,23]` → centro
**(875,487)**, a 1 px del píxel que se enciende. El sampler usa el centro
del cuerpo y lo informa (`led_position.source: "body"`); si no hay cuerpo
cae al promedio de pines y lo dice (`"pins"`).

### 42c · El clasificador: píxeles que emiten

Con el punto correcto, el brillo medio seguía sin servir: el plástico mide
208 y el LED encendido 207. Lo que sí separa es **brillo + saturación**:
un píxel emite si `max(R,G,B) > 150` y `max - min > 40`.

| Zona | RGB | max | saturación | ¿emite? |
|---|---|---|---|---|
| lente apagado | (128,32,32) | 128 | 96 | no (falta brillo) |
| lente encendido | (207,132,132) | 207 | 75 | sí |
| plástico | (208,208,208) | 208 | 0 | no (falta color) |

El clasificador es la **fracción** de la ventana 9x9 que emite, con umbral
**0.12**. Medido en tres circuitos:

| Circuito | Componente | Apagado | Encendido |
|---|---|---|---|
| blink-basico | `led1` | 0.000 | 0.52 – 0.59 |
| semaforo-3-leds | `led_amarillo` | 0.012 | 0.53 |
| boton-pullup | `led1` | 0.025 | (no se pulsó) |

Cada muestra informa `measured_at_px`, `window_px`, `led.lit` (fracción) y
`led.brightness` (brillo medio, para leerlo como humano). Una ventana fuera
de la captura es error `led_offscreen`, no un "apagado".

### 42d · El bug de fondo: `anode` contiene `a`

El primer intento de usar el cuerpo dio una caja de 34x7 (un resistor
acostado): `resolve_terminal("LED","anode")` resolvía el `Terminal 1` del
**resistor en serie**, no el ánodo del LED. Los alias de una sola letra se
comparaban con `includes`, así que cualquier pin con una `a` caía en
`terminal1` (y con una `b`, en `terminal2`). Corregido a igualdad exacta en
los tres sitios del JS. Efecto colateral: `connect_component_pins` también
cableaba el hueco del resistor cuando le pedías el ánodo.

### 42e · Verificado en vivo

- `blink-basico`: `source: "body"`, mide en (875,487); 0.59 / 0.52 / 0.00 /
  0.59 / 0.57 / 0.00 … siguiendo el parpadeo y el serial.
- `semaforo-3-leds`: `led_amarillo` apagado 0.012 durante rojo y verde,
  0.53 al encenderse a los 1000 ms (`TEST:YELLOW`).
- `boton-pullup`: LED en reposo, 0.025 constante, nunca "encendido".
- Suites: puente 293 tests, cerebro 1879.

Lección: **una propiedad que la UI muestra no siempre está en el modelo**,
y un promedio de dos puntos no es el cuerpo de una parte. Y un alias de una
letra comparado con `includes` encuentra cualquier cosa.

## Fase 43: "no pude leer" no es "0%" (2026-11-14)

La fase 42 cerró el sampler y de paso dejó a la vista un problema más viejo:
al reconstruir `blink-basico` el runner reportaba **`Score: 0.0%` / `OK:
False`** con el circuito intacto (4 dispositivos, 10 cables, verificado
leyéndolo aparte). Un 0% acusa al cableado; aquí no había nada mal.

### 43a · El síntoma y el orden de los hechos

El reporte mostraba `tinkercad_inspect_circuit | 0.1 s` — la inspección
respondía **rápido y vacía**, no tardaba ni fallaba. O sea: el puente decía
`success: true` con 0 componentes y 0 cables porque en ese instante la
página no tenía el diseño montado.

Medido con una sonda que abre el circuito y mira el DOM cada segundo:

| Circuito | `open_circuit` retorna | devices visibles |
|---|---|---|
| blink-basico | 12.7 s | 4 a los ~3.4 s |
| semaforo-3-leds | 13.6 s | 8 a los ~4.5 s |

En los dos casos, al volver de `open_circuit` había `window.circuit_editor`
pero **ni `#breadboardTab` ni devices**. El editor existe antes que el
diseño; la espera fija de 3 s no alcanzaba.

### 43b · El arreglo, en la fuente

`CircuitsService._wait_for_design_mounted` espera a que existan
`circuit_editor.data.devices` **y** `#breadboardTab`. Se usa en dos sitios:

- `open_circuit`, después de encontrar el canvas (antes dormía 3 s a ciegas);
- `inspect_circuit`, antes de evaluar (8 s de tope).

Es *best-effort*: si expira, se inspecciona igual y se declara lo que haya.
Un vacío declarado es mejor que una excepción.

### 43c · Y en el cerebro, para que un vacío nunca sea un cero

Aunque el puente ya espera, el runner no puede confiar en que siempre
funcione: `_measure` reabre el circuito y reintenta la inspección hasta 3
veces (1.5 s) cuando la fixture espera componentes y la lectura vino vacía.
La medida lleva `read_attempts` y `read_failed`, y el build falla por
`checks["fidelity_readable"]`.

Dos reglas que evitan reportes mentirosos:

- Si el **build falló**, no se culpa a la lectura: el circuito puede estar
  vacío de verdad y la causa es otra (`build_ok` ya lo dice).
- El reporte escribe "**no se pudo leer** el circuito en N intentos; este
  porcentaje no mide el cableado", y el CLI lista `fidelity_readable` en
  `Fallos:`.

### 43d · Verificado en vivo

- `blink-basico` (`2tMhkuosDyj`): **100% de fidelidad, `OK: True`**, serial
  de 11 líneas. Antes de la fase: 0% con `read_failed` en 3 intentos.
- `semaforo-3-leds` (`hGHU2MiJnDJ`): 100% / `OK: True` (9 de 9 cables).
- Suites: puente **297 tests**, cerebro **1885 verdes**.

Lección: una lectura vacía y un circuito vacío se parecen, y confundirlos
convierte un fallo de tiempo en una acusación falsa. El cero tiene que
significar "medí y no estaba", nunca "no llegué a mirar".
