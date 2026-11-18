# Buzzer activo en D8 con botón en D2 (pull-up interno)
- Circuito: https://www.tinkercad.com/things/93Dj8w6iEv1/editel

## Verificación
- Fidelidad: 0.0%
- Componentes: 0.0% / Conectividad: 0.0%
- Build: **no se aplicó** (ver Fallos); lo que sigue mide el circuito que ya estaba en el editor, no uno nuevo.
- Simulación: {
  "success": true,
  "total_lines": 0,
  "lines": [],
  "raw_output": "",
  "message": "Retrieved 0 lines from Serial Monitor."
}

## Oráculo
- Sin marcas declaradas; el sketch imprime (7 líneas).

## Ruteo
- Sin tramos sobre el cuerpo de una placa (0 de 4 cables medidos, 0 ruteados).
- Sin tramos diagonales en 0 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 30.1 | 30.1 |
| tinkercad_inspect_circuit | 1 | 8.1 | 8.1 |
| tinkercad_open_circuit | 2 | 25.6 | 28.5 |
| tinkercad_read_serial_monitor | 1 | 0.2 | 0.2 |
| tinkercad_set_code | 1 | 3.3 | 3.3 |
| tinkercad_start_simulation | 1 | 0.1 | 0.1 |
| tinkercad_stop_simulation | 1 | 0.1 | 0.1 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Buzzer activo en D8 con botón en D2 (pull-up interno)
Fixture del cerebro: buzzer-activo
Diseno en Tinkercad: /things/93Dj8w6iEv1/editel

QUE HACE
  3 piezas y 4 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno      arduino-uno        Arduino Uno R3
  buzzer1  buzzer             piezo / buzzer
  btn1     pushbutton         pulsador

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D8  - buzzer1.positive
   2. buzzer1.negative  - uno.GND1
   3. uno.D2  - btn1.1
   4. btn1.2  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, INPUT_PULLUP, digitalRead, digitalWrite,
 *   tone, noTone.
```
