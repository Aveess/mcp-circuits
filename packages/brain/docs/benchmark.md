# Benchmark — circuitos construidos y verificados en Tinkercad

Generado desde los registros locales de corridas en vivo (~/jarvis_data/logs/tinkercad-fase0/live*.json).

| Circuito | ID Tinkercad | Fidelidad (conectividad) | Oraculo de comportamiento |
|---|---|---|---|
| Blink sin protoboard | j7EqK1vq0nj | 1.0 (clasica, nets exactas) | READY |
| Blink en protoboard | aBcCq6HfA2P | 1.0 | TEST:ON/OFF alternando |
| Semaforo 3 LEDs | dlhJ966IRvA | 1.0 | READY |
| Boton pull-up + LED | bWmMIRN5dwi | 0.8 (nombres de pin del boton) | READY |
| Servo + potenciometro | 9Rpc2a0C6te | 1.0 | TEST:ANGLE=180 |
| TMP36 + LED | 3Dh7FcuvaEQ | 1.0 | TEST:TEMP=24.78 |
| Ultrasonico HC-SR04 + LED | 0W49xkaR18y | 1.0 | TEST:DIST~112 cm |
| Blink organizado v3 | 2tMhkuosDyj | 1.0 | TEST:ON/OFF, ruteo 2/2 |

## Latencias observadas (todas las corridas, en segundos)

| tool | n | mediana | peor |
|---|---|---|---|
| tinkercad_auth_status | 1 | 10.664 | 10.664 |
| tinkercad_list_available_components | 3 | 0.007 | 0.01 |
| tinkercad_build_circuit | 1 | 52.206 | 52.206 |
| tinkercad_inspect_circuit | 9 | 0.039 | 0.062 |
| tinkercad_create_circuit | 6 | 18.0315 | 21.404 |
| tinkercad_build_circuit_model | 10 | 4.295 | 6.713 |
| tinkercad_set_code | 10 | 16.4085 | 18.405 |
| tinkercad_open_circuit | 16 | 11.309000000000001 | 12.603 |
| tinkercad_start_simulation | 11 | 5.436 | 7.201 |
| tinkercad_read_serial_monitor | 11 | 1.071 | 35.085 |
| tinkercad_take_screenshot | 7 | 0.209 | 0.403 |
| tinkercad_stop_simulation | 10 | 1.2429999999999999 | 1.45 |
| tinkercad_simulate_samples | 1 | 10.062 | 10.062 |
| tinkercad_open_serial_monitor | 2 | 0.9565 | 0.978 |
| tinkercad_zoom_canvas | 4 | 0.831 | 0.856 |
| tinkercad_list_circuits | 1 | 6.824 | 6.824 |
| tinkercad_get_circuit_info | 1 | 0.046 | 0.046 |
| tinkercad_inspect_schematic_connections | 5 | 0.027 | 0.029 |
| tinkercad_connect_verified_netlist | 1 | 14.195 | 14.195 |
| tinkercad_validate_circuit_pre_simulation | 1 | 1.242 | 1.242 |
| tinkercad_verify_schematic_connections | 1 | 0.021 | 0.021 |
| tinkercad_get_code | 2 | 0.603 | 1.174 |
| tinkercad_get_simulation_status | 3 | 0.109 | 0.111 |
| tinkercad_resolve_terminal | 1 | 0.197 | 0.197 |
| tinkercad_connect_component_pins | 2 | 0.3755 | 0.389 |

Total de llamadas registradas: 120. Fallos registrados: 6 (ver reportes por circuito en docs/reportes/).
