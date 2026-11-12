# Cuenta regresiva — entrega miercoles 2026-11-18

Criterio de "proyecto cumplido": describir un circuito simple (LED/boton/semaforo)
-> queda construido y guardado en Tinkercad -> se verifica solo (nets tras recarga
+ simulacion con assertions) -> queda documentado (reporte + screenshot + SVG).
Todo lo demas es secundario frente a eso.

- [x] Fase 0: lectura/nets/simulacion medidos en vivo (2 circuitos)
- [x] Ronda 4: nets derivadas con protoboard + verificador de comportamiento + builder fixture->spec->MCP
- [ ] Vivo: construir 3 circuitos mas con el builder (boton, semaforo, servo o sensor)
- [x] Documentador minimo: reporte markdown por circuito desde el journal
- [ ] Cierre: benchmark chico (esos circuitos), README de uso, demo reproducible

## Regla de organizacion (2026-11-11, pedida por Eddie)

Los cables se rutean organizados SIEMPRE, desde los circuitos faciles:
- Orden de construccion: alimentacion, tierra, senales.
- Colores: tierra negro, 5V/3V3 rojo, senales paleta rotativa sin repetir vecinos.
- Geometria: cables del Uno salen en angulo recto con carriles separados
  (nada de diagonales cruzadas); cada cable con su carril para no solaparse.
- Layout con separacion entre bloques (ya: 6 columnas por LED, 1 libre entre
  bloques de 3 pines).
Criterio de aceptacion: screenshot legible, cables sin cruces innecesarios.
