# Biestable D 74HC74 como divisor por 2
- Circuito: https://www.tinkercad.com/things/euU4CI6HwhX/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 10,
  "lines": [
    "TEST:FF=LISTO",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=1",
    "TEST:FF=0",
    "TEST:FF=TOGGLE-OK"
  ],
  "raw_output": "TEST:FF=LISTO\nTEST:FF=1\nTEST:FF=0\nTEST:FF=1\nTEST:FF=0\nTEST:FF=1\nTEST:FF=0\nTEST:FF=1\nTEST:FF=0\nTEST:FF=TOGGLE-OK",
  "message": "Retrieved 10 lines from Serial Monitor."
}

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 5.1 | 5.1 |
| tinkercad_inspect_circuit | 1 | 0.0 | 0.0 |
| tinkercad_open_circuit | 2 | 10.5 | 11.4 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 17.0 | 17.0 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.
