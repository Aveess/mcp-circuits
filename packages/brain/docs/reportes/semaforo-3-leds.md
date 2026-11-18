# Semáforo: LEDs rojo, amarillo y verde en D11, D10 y D9
- Circuito: https://www.tinkercad.com/things/hGHU2MiJnDJ/editel

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

## Ruteo
- Sin tramos sobre el cuerpo de una placa (0 de 9 cables medidos, 0 ruteados).
- Sin tramos diagonales en 0 cables medidos.

## Herramientas
| tool | n | mediana (s) | peor (s) |
| --- | --- | --- | --- |
| tinkercad_build_circuit_model | 1 | 30.0 | 30.0 |
| tinkercad_inspect_circuit | 1 | 8.1 | 8.1 |
| tinkercad_open_circuit | 2 | 25.8 | 28.5 |
| tinkercad_read_serial_monitor | 1 | 0.2 | 0.2 |
| tinkercad_set_code | 1 | 3.3 | 3.3 |
| tinkercad_start_simulation | 1 | 0.1 | 0.1 |
| tinkercad_stop_simulation | 1 | 0.1 | 0.1 |

## Fallos
Sin fallos.

## Documentación embebida en el circuito

```
CONTADOR / CIRCUITO: Semáforo: LEDs rojo, amarillo y verde en D11, D10 y D9
Fixture del cerebro: semaforo-3-leds
Diseno en Tinkercad: /things/hGHU2MiJnDJ/editel

QUE HACE
  7 piezas y 9 nets. El titulo de arriba resume el comportamiento; el cableado de abajo es el que esta dibujado en el lienzo.

COMPONENTES (ref  tipo  pieza)
  uno           arduino-uno        Arduino Uno R3
  led_rojo      led                LED
  led_amarillo  led                LED
  led_verde     led                LED
  r1            resistor           resistencia
  r2            resistor           resistencia
  r3            resistor           resistencia

CABLEADO (cada linea es un nodo: todo esto va unido)
   1. uno.D11  - r1.1
   2. r1.2  - led_rojo.anode
   3. led_rojo.cathode  - uno.GND1
   4. uno.D10  - r2.1
   5. r2.2  - led_amarillo.anode
   6. led_amarillo.cathode  - uno.GND1
   7. uno.D9  - r3.1
   8. r3.2  - led_verde.anode
   9. led_verde.cathode  - uno.GND1

COMO SE VERIFICA (serial del simulador)
 *   El sketch usa: pinMode, digitalWrite, delay.
```
