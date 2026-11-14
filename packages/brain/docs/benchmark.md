# Benchmark — circuitos construidos y verificados en Tinkercad

Última pasada: 2026-11-13, todos reconstruidos con el runner (reutiliza el
circuito por título y construye con reemplazo limpio). Fidelidad = score de
`compare_connectivity` (componentes + equivalencia eléctrica). El oráculo de
comportamiento es siempre el serial instrumentado en simulación, nunca el
píxel del LED.

| # | Circuito | ID Tinkercad | Fidelidad | Oráculo observado |
|---|---|---|---|---|
| 1 | Blink organizado v3 | 2tMhkuosDyj | 100% | `TEST:ON`/`TEST:OFF` alternando |
| 2 | Semáforo 3 LEDs | hGHU2MiJnDJ | 100% | fases `TEST:RED`/`YELLOW`/`GREEN` |
| 3 | Botón pull-up + LED | lp8O5143UNj | 100% | `TEST:PRESSED` al apretar |
| 4 | Servo + potenciómetro | 9Rpc2a0C6te | 100% | `TEST:ANGLE=0..180` |
| 5 | TMP36 + LED | 2Z7ubKF9ieN | 100% | `TEST:TEMP=24.78`, LED encendido |
| 6 | Ultrasónico HC-SR04 + LED | 2ly9vcxYUyc | 100% | `TEST:DIST=7.46` + `TEST:LED=ON` |
| 7 | RGB (3 resistencias) | i525BUubYAE | 100% | `TEST:RED/GREEN/BLUE` |
| 8 | Motor DC con transistor + diodo | 73azwj2IJDE | 100% | `TEST:MOTOR=0..255` |
| 9 | Motor con L293D + batería 9V | kJPyfC1VQaM | 100% | `TEST:MOTOR`, `TEST:SENTIDO` |
| 10 | Buzzer activo con botón | 93Dj8w6iEv1 | 100% | `TEST:SILENCIO` / `TEST:PRESSED` (tone/noTone) |
| 11 | LDR divisor, luz nocturna | lo9VkvBdWmT | 100% | `TEST:LUZ=6` + `TEST:LED=ON` |
| 12 | Barrera de parking (HC-SR04 + servo + RGB) | 2xxjwQBZuOH | 100% | `TEST:DIST=112` + `TEST:ESTADO=ABIERTO` + `TEST:SERVO=90` |

## Qué agrega cada nivel

- **Nivel 1 (1-4):** salida digital, entrada digital, PWM y entrada analógica
  con un solo actuador.
- **Nivel 2 (5-7):** sensores analógicos y buses de pines (LCD no, todavía;
  sí sensores de 3-4 pines y RGB con tres resistencias).
- **Nivel 3 (8-9):** carga inductiva con transistor y diodo flyback, y driver
  de potencia con alimentación externa (batería 9V) compartiendo tierra.
- **Nivel 4 (10-12):** componentes con geometría no trivial (piezo de 5
  columnas, fotorresistencia de 1 columna) y un circuito de integración con
  tres subsistemas: sensor de distancia, actuador (servo) e indicador (RGB).

## Latencias

Las latencias por herramienta de cada corrida quedan en su reporte
individual (`docs/reportes/<fixture>.md`). Las caras siguen siendo
`tinkercad_create_circuit` (~10-18 s), `tinkercad_set_code` (~17 s) y
`tinkercad_open_circuit` (~9-12 s); `tinkercad_inspect_circuit` ronda 0.1-0.2 s
y es lo que se usa masivamente para verificar.

## Pendientes conocidos

- Sin herramienta de borrado en el puente: los circuitos de exploración se
  renombran `BORRAR - ...` y se eliminan desde el dashboard.
- El sampler de píxeles (brillo de LED) no calibra en headless; el oráculo
  real es el serial.
