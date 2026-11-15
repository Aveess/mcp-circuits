# Layout v2 del contador 0‑7 — diseño

Fecha: 2026‑11‑15 · Proyecto: asistente Tinkercad · Fixture base: `contador-0-7-jk`

## Qué se busca y por qué

Eddie comparó el circuito que construye el MCP con el que armó un compañero para la
misma consigna (taller 3, puntos 5 y 6). El del compañero se lee como un armado
humano: integrados apoyados en la breadboard, cables cortos y paralelos, varias placas,
el display clavado al final de la placa de compuertas. El nuestro deja los integrados
flotando en fila y rutea unos 40 carriles largos alrededor del lienzo.

La v2 construye **el mismo circuito** (mismas funciones, mismos oráculos) con un
dibujo que se lea como el del compañero, sin perder nada de la verificación: fidelidad
100 %, oráculo completo y ningún componente que estalle en simulación.

## Decisiones ya tomadas

- La v1 (`4bJNKia4pfj`) queda **intacta**; la v2 es un **diseño nuevo**.
- Se usa la **breadboard grande** (`did 116648`).
- Las expresiones del punto 4 se mantienen; el decodificador se arma con
  AND/OR/NOT/XOR y el display va en **cátodo común** (aprobado por Eddie).

## Hechos medidos (no supuestos)

### Placa grande (`did 116648`)

1. **Huecos de conexión: 640**, en **64 posiciones de columna** (x −315…315 a paso 10)
   × 10 filas. De esas columnas, **62 tienen nombre** (`<fila><col>`, col 1 = x −295,
   col 62 = x 315); las dos extremas (x −315, −305) el modelo las nombra `A98/A99`,
   así que se evitan.
2. **Las filas van al revés que en la Small**: `A` = y −55 (abajo) … `J` = y +55
   (arriba). En la Small `a` = +55 … `j` = −55.
3. **Rieles: 4 filas de 50 huecos** (x −295…295), pero los dos de abajo **comparten
   nombre `X` y son el mismo nodo** (medido). Nombres: `X` (−85 y −95), `Y` (+85),
   `Z` (+95). Por el nombre duplicado **no se usan para alimentación**.
4. **La media columna es un nodo**, igual que en la Small:
   `F6` e `I6` comparten `Net_0`; `E6` (otra mitad) es `Net_1`. Medido con dos cables
   independientes y con control en la Small (`f6` ≡ `i6`, `e6` aparte).
   Mitades: `F…J` (arriba, y ≥ +15) y `A…E` (abajo, y ≤ −15).
5. **Insertar un DIP con las patas en una sola mitad cortocircuita el chip.** En la
   Small pasó con el ancla en `f` (`1A` y `Vcc` en la misma mitad, `Net_5`). La regla
   es anclar de modo que las dos hileras caigan una en cada mitad: en la Small ancla
   en fila `e`, en la grande en fila `F` (y = +15).
6. **Huellas medidas** (ancla = pin 1):
   - **DIP‑14** (74HC00/08/32/86): 7 columnas; pines 1‑7 en la fila del ancla, 8‑14 en
     la fila de 30 unidades al otro lado (`Vcc` en la columna del ancla, `GND` 6
     columnas a la derecha).
   - **DIP‑8 555**: 4 columnas; las dos hileras están **3 filas** apartadas (en la Small
     `b` y `e`, no `e` y `f`). Para que caigan una en cada mitad hay que anclar el
     `CTRL` en la fila de **abajo** (`f` en la Small, `f` en la grande): así la otra
     hilera queda en `e`. Anclarlo en `e` deja `Vcc` y `GND` en la misma mitad (corto).
     Reparto: `CTRL` (0), `THR` (−1), `DIS` (−2), `Vcc` (−3) en la fila del ancla;
     `Reset` (0), `OUT` (−1), `TRIG` (−2), `GND` (−3) en la otra.
   - **Resistencia**: pin 1 en `<col>e`, pin 2 en `<col>g` — misma columna, 40
     unidades, cruzando el canal central (una pata en cada mitad).
   - **Display 7 segmentos**, ancla en `<col>e`: 10 patas en 5 columnas
     (`col−1 … col+3`), repartidas así: `a` `<col>e`, `b` `<col−1>e`,
     `com2` `<col+1>e`, `f` `<col+2>e`, `g` `<col+3>e`,
     `dp` `<col−1>i`, `c` `<col>i`, `com1` `<col+1>i`, `d` `<col+2>i`,
     `e` `<col+3>i`. Una pata por media columna: no hay cortes.
7. El display tiene la propiedad **`common`** con opciones `anode`/`cathode`;
   `set_property(..., "common", "cathode")` devuelve success y persiste.
8. Chips reales y etiquetas guardadas (del diseño del compañero): **74HC08** AND
   (114702→116702), **74HC32** OR (116721), **74HC04** NOT (116701), **74HC86** XOR
   (116727). Etiquetas: `Input nA`, `Input nB`, `Output n`, `Ground`, `Power`; el
   inversor usa `Input n` / `Output n`.
9. **La fidelidad se mide pin a pin**: `derive_nets` solo devuelve nets de pines de
   componentes; los huecos sirven para *unir*. Por eso el cerebro no necesita hablar
   el vocabulario de nombres del modelo, solo su propia geometría.

## Enfoques considerados

**A. Chips insertados + saltos cortos hueco‑hueco (elegido).** Cada integrado se
inserta con las dos hileras en mitades distintas. Cada net se dibuja como una cadena
de puentes entre las medias columnas donde caen sus patas, ordenadas por columna; si
dos patas de la misma net caen en la misma media columna, no hace falta cable. La
placa hace de patch panel y los cables largos desaparecen.

**B. Insertar con las dos hileras en la misma mitad.** Descartado: corta el chip
(medido, hecho 5).

**C. Solo cosmético: peinar los carriles actuales.** Descartado: el circuito sigue
leyéndose como una maraña y no hay ninguna pata en la placa.

## Reglas de la v2

1. **Placas:** dos `Breadboard` grandes. Placa 1: los 6 integrados del decodificador y
   el display al final con sus 7 resistencias. Placa 2: los tres JK y el 555. Si un
   chip no entra, se abre una tercera placa (el reparto exacto lo decide el constructor).
2. **Inserción:** ancla de los DIP en la fila que deja una hilera por mitad (`e` en la
   Small, `F` en la grande); los chips no se solapan y dejan 1‑2 columnas libres entre
   sí.
3. **Sin cortos:** una media columna pertenece a **una sola net**. Las patas de los
   chips ya cumplen (una pata por media columna); el asignador nunca termina un puente
   en una media columna de otra net.
4. **Cables:** puentes hueco‑hueco cortos, ordenados por columna; solo salen del
   tablero los del Uno y los de alimentación entre placas.
5. **Alimentación:** sin rieles en la grande (nombre `X` duplicado). Bus de 5 V y de
   GND en medias columnas libres al borde de cada placa, unidas por puentes cortos;
   cada chip y cada común del display baja al bus con un puente.
6. **Colores por función:** rojo 5 V, negro GND, un color por net de señal; todos los
   puentes de una misma net comparten color.
7. **Display:** cátodo común; cada segmento por su resistencia de 220 Ω; los dos
   comunes a GND; `dp` sin conectar. **El nodo que lee el sketch es la salida de la
   compuerta, antes de la resistencia** (en la v1 se leía el inversor justo por eso:
   leer el pin del display daba la máscara al revés).
8. **Uno:** fuera de la placa, a la izquierda, con cables cortos al borde.

## Qué queda a criterio de quien construye

- Orden de los chips en cada placa y reparto concreto de columnas.
- Si el 555 va con los JK o en una placa aparte.
- Cómo se documenta el mapa de columnas en el reporte.

## Riesgos y cómo se controlan

- **Corto por media columna compartida** → lint que verifica, antes de construir, que
  ninguna media columna reciba dos nets.
- **Chip que no entra** → el asignador abre otra placa; nunca lo deja flotando.
- **Regresión de fidelidad** → el runner mide igual que siempre y el oráculo del serial
  sigue siendo el juez.
- **No perder calidad** → los cuatro defectos de la fase 46 ya tienen test.

## Fuera de alcance

- El documento para la persona (trabajo siguiente, pedido aparte).
- La optimización del tiempo de build (trabajo posterior).
- Tocar la v1 o reemplazarla como evidencia.
