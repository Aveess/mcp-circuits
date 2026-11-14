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
   Regla: el LCD se coloca primero (columna 1, fila j, ocupando 18 columnas)
   y los bloques que caerian debajo (piezo, LDR, ultrasonico, boton, 3 pines,
   L293D) se rechazan con un error claro en vez de quedar ocultos.
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
- Resultado: `lcd-contador` y `lcd-temperatura` (TMP36 + display, `9hZJgbsYOC5`)
  al 100%, con el display mostrando exactamente el valor del oraculo serial.
