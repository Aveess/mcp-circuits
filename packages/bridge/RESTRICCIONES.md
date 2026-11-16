# Restricciones del MCP de Tinkercad

Lo que este servidor puede hacer y, mas util, lo que **no** puede. Todo lo que
esta aca esta medido en vivo sobre la cuenta real; cuando algo es una
suposicion, lo dice.

El documento para agentes es [AGENTS.md](./AGENTS.md). Este es para personas
que van a usar el servidor o a construir un circuito con el.

---

## 1. La regla de alimentacion (no negociable)

Un circuito se arma como se arma una placa de verdad. No es estetica: un
cable de alimentacion mal puesto se ve perfecto en la foto y no funciona.

```
  [Power Supply]
   Vcc (rojo) ─────────────► riel +  (borde cercano, columna 1)
   GND (negro) ────────────► riel −  (borde cercano, columna 1)
                                  │
                                  │  dos cables al borde opuesto
                                  ▼
                            riel + / riel −  del otro extremo
                                  │
                                  │  bajadas cortas, en la misma columna
                            pata de cada componente
```

1. La fuente es la pieza **Power Supply** (did `111724`, pines `Vcc` y `GND`).
   **No** se usa el pin de 5 V del Arduino para repartir: el Uno es un
   consumidor mas.
2. **Rojo** va del positivo al riel positivo. **Negro** va de la tierra al
   riel negativo. Rojo y negro **no se usan para senales**, nunca.
3. Del borde opuesto salen otros dos cables (uno de cada color) para que la
   placa quede alimentada de punta a punta. Sin ellos, media placa esta
   muerta y el sintoma es "unas cosas andan y otras no".
4. Cada componente toca con un cable **corto** el riel de su propia mitad, en
   su misma columna. No se tienden tiradas largas hasta la fuente.
5. Una placa adicional se alimenta **de la placa ya alimentada**, con los
   mismos dos cables y los mismos colores. La fuente alimenta una sola placa.

### 1.1 Cuando aparece el Arduino (y cuando no)

La fuente reemplaza al Uno **como fuente de energia**, no como controlador.
Son dos papeles distintos y conviene no confundirlos:

- **Por defecto no hay Arduino.** Un circuito que se resuelve con hardware
  (reloj, compuertas, display, LEDs) se arma sin placa programable.
- **El Uno entra solo si el proyecto necesita programa**: leer o escribir
  pines, hablar por el monitor serial, atender un sensor, o manejar senales
  de control como EN y RESET. En ese caso se dice en la descripcion del
  circuito por que esta.
- **Cuando esta, no alimenta nada.** Sus pines de 5 V y GND no reparten
  energia: eso lo hace la fuente. Lo unico que se cuelga es su `GND` como
  referencia comun, y si el proyecto lo pide, su `5V` recibe de la fuente.
- **El panel de control y la evidencia tambien son motivo.** Si el taller
  pide demostrar la secuencia por el monitor serial, sin micro no hay
  monitor. Si te piden quitar el Arduino, avisa que se pierden las senales
  de control y el serial: el circuito puede seguir contando solo, pero deja
  de poder demostrarse.

Ejemplo medido: en el contador 0-7 v3 (`kSakfQXHtmU`) el Uno **se queda**
porque maneja EN (D8) y RESET (D9), lee el reloj del 555 en D2 y emite
`TEST:DIGITO` por serial; la energia sale de la `Power Supply`. Los cables
largos de alimentacion que antes salian del Uno desaparecieron: pasaron de
18 tiradas a 2.

Ejemplo medido: en el contador 0-7 **v4** (`3akmw1EaG0p`) el Uno **no esta**.
EN lo mueve un interruptor deslizante y RESET un pulsador con pull-down e
inversor (ver `docs/organizacion-cables.md`, regla v4). Como el build
**siempre crea el Uno** (`ensureDevice`), la fixture lo declara con
`"no_arduino": true` y el puente lo quita al final con
`remove_unused_uno: true`. Sin ese paso el Arduino vacio baja la fidelidad de
piezas a 26/27 (96.3 %) aunque el cableado este al 100 %: el Uno cuenta como
componente que la fixture no declara.

Lo que se pierde al quitar el micro se dice antes: **no hay monitor serial**.
La evidencia pasa a ser la captura del display. Si alguien pide `TEST:DIGITO`
en un circuito sin micro, ese dato ya no existe.

Donde la regla no se puede cumplir entera, se dice:

- En la **placa grande** las dos filas de riel de abajo se llaman las dos `X`
  y son **un solo nodo**. Ahi solo puede ir una polaridad: el positivo abajo,
  la tierra arriba, y la tierra de la mitad de abajo llega por fila de bus.
  Poner positivo y tierra en ese par es un corto que el simulador **no**
  reporta como error de armado.
- En la **placa chica** los cuatro rieles son nodos distintos y la regla se
  cumple completa: dos rieles por lado y los dos cables de borde.

Placas **apiladas** (fase 50): los `boards` no tienen que estar uno al lado
del otro. Si dos placas comparten `x` y difieren en `y`, un cable entre
huecos de una y otra se tiende recto como una diagonal larga sobre las dos
proboards. El puente lo rutea en Z (`crossBoardPair`) por el carril que cae
en el aire entre las dos, y deja **aire suficiente**: la banda arranca a 130
del origen de la placa de abajo y avanza de 8 en 8, con el cuerpo en +-110,
asi que menos de ~240 entre las dos deja pocos carriles. La decision de
rutear se toma en `plan_wire_style(..., boards=...)`, **no** solo en el JS:
el plan manda `route` explicito y el JS lo respeta.

## 2. Lo que se mide y lo que no

- `tinkercad_build_circuit_model` devuelve una **fidelidad pin a pin**: que
  cada pata este donde la fixture dice y que los cables unan los nodos
  declarados. Un 100 % no dice nada de si el circuito funciona.
- Los **rieles** no son pines: el modelo los agrupa por nombre (`X`, `Y`,
  `Z` en la grande) y el verificador los trata como un nodo por fila. Por eso
  un cable entre dos filas que el modelo funde es decorativo, no crea nada.
- `tinkercad_inspect_schematic_connections` devuelve `total_nets: 0` con
  cableado de protoboard: **no sirve** como oraculo de nets.
- `tinkercad_validate_circuit_pre_simulation` detecta sobrecorriente y
  motores mal conectados. **No detecta cortos de 5 V con GND.**
- Que una pata este en el hueco correcto no significa que el cable este
  bonito: el ruteo se mide aparte (`route_debug`, diagonales, tramos sobre
  placa).

## 3. Geometria de las placas (medida)

| | Breadboard Small (`111211`) | Breadboard Large (`116648`) |
|---|---|---|
| Columnas utiles | 30 | 62 (el modelo llama `A98/A99` a las dos extremas) |
| Paso | 10 unidades | 10 unidades |
| Filas | `a`..`j`, `a` = +55 | `A`..`J`, **al reves**: `A` = −55 |
| Rieles | 4 filas de 30 huecos | 4 filas de **50** huecos, **salteados** |
| Nodos de riel | 4 (`T±`, `B±`) | 3: `Y` arriba, `Z` arriba, `X` = las **dos** filas de abajo |
| Media columna | los 5 huecos de una mitad son un nodo | igual |

- Los 50 huecos de riel de la grande **no son las primeras 50 columnas**: el
  riel llega hasta la columna 60 (ultimo hueco en x=295) y falta en 6, 12, 18,
  24, 30, 31, 37, 43, 49, 55, 61 y 62 (medido el 2026-11-15 con una sonda
  sobre el editor). Un extremo como `B+24` o `T+43` esta dentro del rango y
  aun asi **no resuelve**: el build lo reporta como `endpoint not resolved` y
  ese cable no se tiende. El puente valida la columna contra `rail_holes`;
  `rail_columns` es la ultima columna con riel (60), no el numero de huecos.

- Un hueco **vacio** devuelve `net = null` hasta que algo lo toca: eso no
  prueba que no comparta nodo. La pregunta se contesta tendiendo dos cables y
  comparando.
- Las filas de arriba son `a`..`e` (y > 0). El modelo de la grande las
  rotula al reves; el puente ubica los huecos por `y`, no por letra.

## 4. Piezas con trampa

- **Display 7 segmentos** (`129710`): solo entra en la placa grande **girado
  180°**, y girarlo gira el dibujo de los segmentos (la pata `d` queda donde
  el dibujo pone la `a`). Electricamente puede estar perfecto y mostrar el
  numero invertido: se verifica con captura.
- **Comunes del display**: Tinkercad guarda las dos patas como `Common`.
  Declarar las dos baja la fidelidad sin que falte un cable; se declara una
  sola y el display enciende igual (son el mismo nodo interno).
- **Potenciometro de contraste**: la posicion del knob es estado de
  simulacion, no propiedad del modelo. Con el `VO` a GND se lee perfecto; no
  se intenta "mover el knob" desde el MCP.
- **Power Supply**: existe y se coloca (`add_component` con
  `component_name="Power supply"`), pero **no aparece** en
  `tinkercad_list_available_components`. El catalogo del buscador no es el
  catalogo real.
- **Nombres de pines**: lo que `inspect` llama `Vcc`/`GND`, el guardado lo
  llama `Power`/`Ground`, `Common`, `Row 1`, `Terminal 1`... Sin alias por
  tipo, la conectividad medida se queda a medias aunque el cableado este
  bien.
- **Nombres de partes**: el editor deduplica al reconstruir (`r2` pasa a
  `r21`). La identidad es el nombre que devuelve el build, no la ref de la
  fixture.

## 5. Tiempo, sesion y guardado

- **Una sesion, un build.** El perfil persistente (`.tinkercad_profile/`)
  tiene un solo contexto logueado: dos builds en paralelo se pelean la misma
  pagina. Se espera a que termine uno.
- **El simulador va mas lento que el tiempo real**: 0,05× al cargar y 0,2–1×
  una vez asentado. Un sketch que necesita 20 s simulados puede tardar
  minutos. Nunca se declara muerto un circuito tras un `sleep` fijo: se
  arranca la simulacion, se lee el serial y se sondea hasta que aparezcan las
  marcas, con un tope.
- **La simulacion puede arrancar antes de que el codigo este listo**: una
  corrida devuelve 2 de 8 marcas y al reabrir el mismo diseno devuelven las 8.
  Antes de culpar al cableado, se reintenta `stop` + `start`.
- **Guardar codigo es debounced.** `set_code` espera el flush de ShareJS y
  relee para confirmar. Puede quedar un op pendiente en 1 que no impide
  guardar: una recarga lo devuelve a 0.
- **Abrir un diseno a veces no monta el editor** (pagina en "Initializing").
  `open_circuit` recarga hasta 3 veces; si igual falla, responde
  `success: false`, `reason: "editor_not_mounted"`. Es un hipo del servidor
  de Tinkercad, no del cableado.

## 6. Limites duros del cerebro

- **3 placas** por circuito (`_MAX_BOARDS`).
- **8 colores** de senal (azul, verde, naranja, amarillo, purpura, turquesa,
  rosa, marron). Rojo y negro estan reservados por la regla del punto 1.
- Una **media columna** no puede llevar dos nets: es un corto que la foto no
  muestra. El layout lo rechaza antes de construir.
- El cableado v2/v3 va **en fila**: mismo renglon o misma columna. Un cable
  que avanza en columna y fila a la vez es una diagonal y se mide como
  defecto.

## 7. Lo que este servidor no hace

- No hay API oficial de Circuits: se maneja el editor real. Si Autodesk
  cambia el DOM o el modelo, algo se rompe.
- No exporta un netlist ni un esquematico utilizable.
- No sube archivos ni bibliotecas de piezas.
- No valida el diseno electrico mas alla de lo que la simulacion demuestre.
- No borra disenos ajenos: `tinkercad_delete_circuit` borra lo que se le
  pide, y lo que se le pide tiene que ser tuyo.

## 8. Antes de decir "listo"

1. Fidelidad **1.0** (o el numero medido, con la causa si no llega).
2. **0 diagonales**, 0 tramos sobre placa, y cuantos cables se midieron.
3. Las marcas del **serial** en orden (`TEST:...`), no "deberia".
4. **Captura** del display o del actuador cuando el resultado es visual.
5. El reporte en `docs/reportes/<id>.md` con la URL del diseno.
