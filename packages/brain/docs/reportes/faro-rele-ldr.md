# Faro automatico con rele SPDT, NPN y LDR
- Circuito: https://www.tinkercad.com/things/aF67dwSGoqC/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 16,
  "lines": [
    "TEST:FARO=LISTO",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:LUZ=6",
    "TEST:RELE=ON",
    "TEST:FOCO=1",
    "TEST:RELE=OFF",
    "TEST:FOCO=0",
    "TEST:FARO=FIN"
  ],
  "raw_output": "TEST:FARO=LISTO\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:LUZ=6\nTEST:RELE=ON\nTEST:FOCO=1\nTEST:RELE=OFF\nTEST:FOCO=0\nTEST:FARO=FIN",
  "message": "Retrieved 16 lines from Serial Monitor."
}

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 6.7 | 6.7 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.9 | 10.7 |
| tinkercad_read_serial_monitor | 1 | 1.0 | 1.0 |
| tinkercad_set_code | 1 | 18.3 | 18.3 |
| tinkercad_start_simulation | 1 | 5.3 | 5.3 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.
