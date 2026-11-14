# Temporizador 555 en astable (reloj de ~14 Hz)
- Circuito: https://www.tinkercad.com/things/abIk7XRpSR4/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 5,
  "lines": [
    "TEST:555=LISTO",
    "TEST:555=ALTO,73173",
    "TEST:555=BAJO,427",
    "TEST:555=FREQ,13.6",
    "TEST:555=OK"
  ],
  "raw_output": "TEST:555=LISTO\nTEST:555=ALTO,73173\nTEST:555=BAJO,427\nTEST:555=FREQ,13.6\nTEST:555=OK",
  "message": "Retrieved 5 lines from Serial Monitor."
}

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.3 | 4.3 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 10.6 | 11.3 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.6 | 15.6 |
| tinkercad_set_component_property_model | 2 | 1.3 | 1.3 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.
