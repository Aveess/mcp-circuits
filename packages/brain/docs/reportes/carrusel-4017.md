# Carrusel de 4 LEDs con 74HC4017
- Circuito: https://www.tinkercad.com/things/ij6ypc8wB5x/editel

## Verificación
- Fidelidad: 100.0%
- Componentes: 100.0% / Conectividad: 100.0%
- Simulación: {
  "success": true,
  "total_lines": 10,
  "lines": [
    "TEST:4017=LISTO",
    "TEST:4017=1",
    "TEST:4017=2",
    "TEST:4017=3",
    "TEST:4017=0",
    "TEST:4017=1",
    "TEST:4017=2",
    "TEST:4017=3",
    "TEST:4017=0",
    "TEST:4017=FIN"
  ],
  "raw_output": "TEST:4017=LISTO\nTEST:4017=1\nTEST:4017=2\nTEST:4017=3\nTEST:4017=0\nTEST:4017=1\nTEST:4017=2\nTEST:4017=3\nTEST:4017=0\nTEST:4017=FIN",
  "message": "Retrieved 10 lines from Serial Monitor."
}

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 4.7 | 4.7 |
| tinkercad_inspect_circuit | 1 | 0.1 | 0.1 |
| tinkercad_open_circuit | 2 | 9.4 | 10.6 |
| tinkercad_read_serial_monitor | 1 | 1.1 | 1.1 |
| tinkercad_set_code | 1 | 15.9 | 15.9 |
| tinkercad_start_simulation | 1 | 5.4 | 5.4 |
| tinkercad_stop_simulation | 1 | 1.2 | 1.2 |

## Fallos
Sin fallos.
