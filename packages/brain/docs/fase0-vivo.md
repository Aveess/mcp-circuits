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
