# Cuenta regresiva — entrega miercoles 2026-11-18

Criterio de "proyecto cumplido": describir un circuito simple (LED/boton/semaforo)
-> queda construido y guardado en Tinkercad -> se verifica solo (nets tras recarga
+ simulacion con assertions) -> queda documentado (reporte + screenshot + SVG).
Todo lo demas es secundario frente a eso.

- [x] Fase 0: lectura/nets/simulacion medidos en vivo (2 circuitos)
- [x] Ronda 4: nets derivadas con protoboard + verificador de comportamiento + builder fixture->spec->MCP
- [x] Vivo: boton, semaforo, servo, tmp36, ultrasonico construidos con el builder
- [x] Documentador minimo: reporte markdown por circuito desde el journal
- [x] Cierre: benchmark (docs/benchmark.md) y README de demo

## Regla de organizacion (2026-11-11, pedida por Eddie)

Los cables se rutean organizados SIEMPRE, desde los circuitos faciles:
- Orden de construccion: alimentacion, tierra, senales.
- Colores: tierra negro, 5V/3V3 rojo, senales paleta rotativa sin repetir vecinos.
- Geometria: cables del Uno salen en angulo recto con carriles separados
  (nada de diagonales cruzadas); cada cable con su carril para no solaparse.
- Layout con separacion entre bloques (ya: 6 columnas por LED, 1 libre entre
  bloques de 3 pines).
Criterio de aceptacion: screenshot legible, cables sin cruces innecesarios.
