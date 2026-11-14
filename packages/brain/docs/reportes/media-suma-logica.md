# Media suma con compuertas XOR y NAND
- Circuito: https://www.tinkercad.com/things/4z8ZkFcpmuC/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 5,
  "lines": [
    "TEST:LOGICA=LISTO",
    "TEST:HA=0,0,0,0",
    "TEST:HA=0,1,1,0",
    "TEST:HA=1,0,1,0",
    "TEST:HA=1,1,0,1"
  ],
  "raw_output": "TEST:LOGICA=LISTO\nTEST:HA=0,0,0,0\nTEST:HA=0,1,1,0\nTEST:HA=1,0,1,0\nTEST:HA=1,1,0,1",
  "message": "Retrieved 5 lines from Serial Monitor."
}

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 7.4 | 7.4 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.7 | 11.5 |
| tinkercad_read_serial_monitor | 1 | 1.2 | 1.2 |
| tinkercad_set_code | 1 | 15.5 | 15.5 |
| tinkercad_start_simulation | 1 | 5.5 | 5.5 |
| tinkercad_stop_simulation | 1 | 1.3 | 1.3 |

## Fallos
Sin fallos.
