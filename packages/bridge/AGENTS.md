# AGENTS.md — reglas para el agente que usa este MCP

Este repositorio es un servidor MCP que maneja **Tinkercad Circuits** a traves
del editor real (Playwright). Antes de usarlo, lee
[RESTRICCIONES.md](./RESTRICCIONES.md): ahi esta lo que el editor mide y lo que
no, y las trampas ya pagadas.

Estas reglas no son sugerencias. Si algo de aca se rompe, el circuito se ve
bien en la foto y no funciona en la simulacion.

---

## 1. Palabra del usuario manda, pero la alimentacion tiene una sola forma

Eddie fijo la regla de alimentacion y es **obligatoria** en todo circuito que
se construya o se modifique:

1. La fuente es la pieza **Power Supply** (`did 111724`, pines `Vcc` y `GND`).
   **Nunca** se reparte alimentacion desde el pin de 5 V del Arduino.
2. **Rojo** = positivo, **negro** = tierra. Esos dos colores no se usan para
   senales, sin excepciones.
3. De la fuente salen dos cables al riel de la placa: rojo al positivo, negro
   al negativo, entrando por el borde (columna 1), no por el medio.
4. Dos cables mas, del mismo color, van al riel del **borde opuesto** para que
   la placa quede alimentada entera. Si esa placa no puede llevar esa
   polaridad en ese borde (ver RESTRICCIONES §1), se dice en el reporte y se
   usa fila de bus; no se inventa un cable decorativo y se calla.
5. Cada componente toca el riel de **su propia mitad** con un cable corto en
   su misma columna. Nada de tiradas largas hasta la fuente.
6. Una placa extra se alimenta **de la placa ya alimentada**, no de la fuente.

**El Arduino no es la fuente.** Por defecto **no se pone**: solo entra si el
proyecto necesita programa (leer/escribir pines, serial, sensores, EN/RESET) y
en ese caso se dice por que esta. Cuando esta, sigue siendo un consumidor: sus
5 V y GND no reparten energia y solo su GND se cuelga como referencia comun.
Si te piden quitar el Arduino de un circuito que lo usa para control o para
el monitor serial, avisa que se pierden esas dos cosas antes de quitarlo.

Si te piden algo que contradice esto, hazlo pero **dilo antes**: "esto rompe
la regla de alimentacion porque ...". No lo hagas en silencio.

## 2. Verificar antes de afirmar

- "Fidelidad 1.0" y "funciona" son dos cosas distintas. La primera la dice el
  build; la segunda la dice el **serial** y la **captura**.
- Un `0.0` solo vale como "medi y no estaba". Si el editor no monto el
  diseno, es `success: false` con `reason: "editor_not_mounted"` y **no** es
  un cableado mal hecho. No conviertas un "no pude leer" en un cero.
- Antes de declarar terminado: fidelidad, 0 diagonales, las marcas del serial
  **en orden**, y captura cuando el resultado es visual. Si falta una, di
  cual.
- Un circuito que explota sigue contando pines: la fidelidad no prueba
  validez electrica. Para eso estan la simulacion y el serial.

## 3. Como se construye (orden que funciona)

1. `tinkercad_auth_status` y, si hace falta, `tinkercad_login`.
2. `tinkercad_create_circuit` (o `tinkercad_open_circuit` con el id guardado:
   reusar por id, **nunca** crear un duplicado por titulo).
3. `tinkercad_build_circuit_model` con `parts`, `wires`, `boards` y `code`.
   Los extremos son huecos (`"12d"`, `"b1/7h"`) o rieles (`"T+5"`,
   `"b2/B-40"`), no pines inventados.
   - Un circuito **sin micro** se construye sin `code` (o con `code: null`) y
     con `remove_unused_uno: true`: el build crea el Uno igual, y esa opcion
     lo quita al final si ningun cable del plan lo toca. El resultado trae
     `removed_uno`. Sin ella, el Arduino vacio resta fidelidad de piezas.
   - Los pines de una **parte libre** se piden por la **clave del modelo**,
     no por el nombre de la UI. Medido: `Slide Switch` usa `1`/`2`/`3`
     (3 = Common) y `Pushbutton` usa `1`..`4` (1/2 un lado, 3/4 el otro).
     "Common" o "Terminal 2a" fallan con `endpoint_not_resolved`.
   - Un **interruptor deslizante** nace con el comun en la clave `1`: si de
     esa posicion cuelga el estado "apagado", el circuito arranca muerto y
     solo cambia con un clic en el simulador. Para que algo se vea
     funcionando al abrir el diseno, la clave `1` va a la posicion activa
     (medido en vivo, build `3akmw1EaG0p`: el display se quedo en 0).
   - Los `boards` pueden estar **apilados** (misma `x`, distinta `y`), no solo
     uno al lado del otro. Un cable entre huecos de placas con distinta `y`
     sale diagonal si se deja recto: el build lo rutea en Z por el carril que
     cae en el aire entre las dos (`crossBoardPair`). Deja **aire suficiente**
     entre los cuerpos: la banda arranca a 130 del origen de la placa de abajo
     y avanza de 8 en 8, y el cuerpo mide +-110, asi que dos placas a menos de
     ~240 de distancia dejan pocos carriles.
   - Un cable entre huecos de la **misma** placa se deja recto a proposito (es
     un puente corto sobre el plastico); el ruteo en Z solo aplica entre
     placas distintas.
   - **Angulos rectos, sin excepciones:** todo cable es vertical u horizontal
     y cada giro es de 90°. Antes de dar por bueno un diseño, compara
     `route_debug[*].actual` con `points` en los cables ruteados: si el editor
     guardo otro punto, el cable esta torcido aunque el reporte diga
     `0 diagonal(es)`. Se arregla **reconstruyendo**, no editando los quiebres
     a mano (`removePoint` lanza excepcion y deja puntos huerfanos).
   - **Las piezas creadas por este MCP no se pueden mover ni editar** en el
     editor: entran por el modelo (`createDeviceInstance`) y no quedan
     seleccionables (medido el 2026-11-16: 0 cambios tras 2 intentos de
     arrastre). Las de la **paleta** sí se arrastran, y los **cables** también.
     Si hay que cambiar el layout, se cambia en el generador y se reconstruye
     el mismo `tinkercad_id`; no pierdas tiempo arrastrando piezas del build.
4. `tinkercad_set_component_property_model` por **nombre real** de la parte
   (con siete resistencias, "Resistor" es ambiguo y el preset se pierde).
5. `tinkercad_set_code` (espera el flush y relee: no lo saltes).
6. `tinkercad_start_simulation` y `tinkercad_read_serial_monitor` **sondeando**
   hasta que aparezcan las marcas, con tope. El simulador va a 0,05–1×.
7. `tinkercad_simulate_samples` / `tinkercad_take_screenshot` para lo visual.

## 4. Descubrir una pieza se mide, no se adivina

`tinkercad_list_available_components` **no** es el catalogo real (no lista
"Power supply", por ejemplo). Para saber si una pieza existe y como se llaman
sus pines:

1. crea un circuito **desechable** con un titulo que empiece con `BORRAR -`;
2. `tinkercad_add_component` con el nombre que crees que tiene;
3. `tinkercad_inspect_circuit` y lee `type`, `did` y los pines reales;
4. `tinkercad_delete_circuit` para borrarlo;
5. anota el did y los alias en el catalogo del cerebro, con la fecha y el
   circuito donde se midio.

Un did inventado no falla con un error claro: coloca otra cosa.

## 5. Errores que ya pagamos (no los repitas)

- **Display 7 segmentos**: solo entra girado 180°, y girarlo intercambia las
  patas (`a`↔`d`, `b`↔`e`, `c`↔`f`). Se verifica con captura, no con el
  netlist.
- **Comunes del display**: declara uno; los dos bajan la fidelidad sin que
  falte un cable.
- **Nombres de pines**: el guardado usa nombres humanos (`Power`, `Ground`,
  `Common`, `Row 1`, `Terminal 1`). Sin alias por tipo, la conectividad mide
  a medias.
- **Nombres de partes**: el editor deduplica (`r2` → `r21`). Usa el nombre
  que devuelve el build.
- **Potenciometro**: la posicion del knob es estado de simulacion, no
  propiedad del modelo. No intentes fijarla.
- **Serial incompleto al arrancar**: si la simulacion arranco antes de que el
  codigo estuviera listo, reintenta `stop` + `start` antes de culpar al
  cableado.
- **Rieles salteados en la placa grande**: tiene 50 huecos de riel repartidos
  en 60 columnas, no 50 seguidos. `B+24`, `T+37`, `B+49`, `T+43` no existen
  aunque la columna este en rango; el build responde `endpoint not resolved`
  y el cable simplemente no se tiende. Antes de cablear a un riel, consulta
  `rail_holes` de `BOARD_KINDS` (o usa solo columnas 1..5, 7..11, 13..17...).
- **El interruptor deslizante se arrastra, no se clica.** La pieza mide ~9.5
  px en pantalla y sus dos detentes estan al 24 % y al 76 % de la caja. Un clic
  al centro cae entre las dos: el tirador queda a medio camino, la entrada del
  XOR flota y el CD4511 muestra segmentos que no son ningun digito, de forma
  **estable** (repetir el clic en el mismo punto no lo arregla). Se arrastra
  desde la posicion actual del tirador hasta el detente (`x + w*0.78` = 1,
  `x + w*0.20` = 0) y un `Escape` antes de cada arrastre cierra el popover
  (medido el 2026-11-17 en el proyecto final `0IItPdytJkx`).
- **El CD4511 del simulador dibuja el seis sin el segmento `a`.** Con la
  magnitud 6 el SVG enciende `c,d,e,f,g` y la captura muestra un 6 legible
  (forma alternativa del seis). Un lector que solo acepte `a,c,d,e,f,g` marca
  ese estado como ilegible y el banco falla sin que el circuito tenga nada
  malo (medido el 2026-11-17, mismo circuito).
- **Un tap de alimentacion en la media columna de una pata ajena quema el
  integrado.** La placa une los cinco huecos de la mitad, asi que bajar el 5V
  al hueco `a58` es conectar el 5V a la pata que este en `e58`/`f58`. En el
  contador v3 (`kSakfQXHtmU`) el bus del 5V bajo por la columna de `x1.4Y`
  (salida del XOR en bajo) y el 74HC86 revento en la simulacion **sin** que
  la secuencia del display se viera afectada. Si una pata queda en una
  columna sin hueco de riel, el cable va **directo al hueco de riel mas
  cercano**, no por una fila de bus.

## 6. Prohibido

- Escribir credenciales, cookies o el contenido de `.tinkercad_profile/` en
  reportes, commits, capturas o respuestas.
- Correr dos builds en paralelo contra la misma cuenta: comparten la pagina y
  se pisan.
- Borrar disenos que no creaste tu. `tinkercad_delete_circuit` no pregunta.
- Declarar "funciona" sin serial y sin captura.
- Tocar los circuitos ya entregados (v1 `4bJNKia4pfj`, v2 `jWUw1co8IZH`) ni
  sus fixtures: si hay que cambiar algo, se hace una version nueva.
- `git add -A` a ciegas: puede haber trabajo a medias de otra sesion.

## 7. Higiene del repositorio

- Un commit por cambio con sentido, con el motivo: que cambio y por que.
- Suite real antes de empujar: `python -m unittest discover tests` (336 tests)
  y `python examples/check_mcp_stdio.py` para el camino MCP por stdio.
- Si un test viejo fija un contrato que la medicion nueva contradice,
  reescribelo **dejando el motivo escrito**; no lo borres.
- Un cambio de geometria o de alias se re-verifica en vivo: la tabla que vive
  solo en el JS no se prueba sin navegador.

## 8. Donde esta la verdad

| Que | Donde |
|---|---|
| Fixtures y cableado esperado | repo del cerebro: `fixtures/fase0/circuits.json` |
| El circuito medido y su URL | repo del cerebro: `docs/reportes/<id>.md` |
| Geometria de las placas | `src/services/model_build_service.py` (`BOARD_KINDS`, `ROW_Y`) |
| Reglas de layout y reparto de rieles | cerebro: `layout_v3.py` |
| Este documento | `AGENTS.md` |

Si una afirmacion de estos documentos ya no se sostiene contra el codigo,
corrigela en el mismo commit que tu cambio.
