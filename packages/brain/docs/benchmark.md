# Benchmark — circuitos construidos y verificados en Tinkercad

Última pasada: 2026-11-14, todos reconstruidos con el runner (reutiliza el
circuito por el `tinkercad_id` de la fixture y construye con reemplazo
limpio; el match por título queda solo como respaldo). Fidelidad = score de
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
| 13 | LCD 16x2 en modo 4 bits (contador) | cpySiVSE9vr | 100% | `TEST:LCD=LISTO` + `TEST:SEG=N` (mismo valor que muestra la pantalla) |
| 14 | Termómetro TMP36 en LCD 16x2 | 9hZJgbsYOC5 | 100% | `TEST:TEMP=24.78` (mismo valor que muestra la pantalla) |
| 15 | Medidor de distancia con LCD y alarma | blN5d8qCr2z | 100% | `TEST:DIST=110.1` + `TEST:ALARMA=ON` (mismo valor en pantalla) |
| 16 | Contador 0-9 en display 7 segmentos | gfgLntRuWJv | 100% | `TEST:DIGITO=0..9` y el display muestra el mismo dígito |
| 17 | Contador 0-9 con 74HC595 y display 7 segmentos | kBGbtwAbFlz | 100% | `TEST:595=LISTO` + `TEST:DIGITO=0..9` (los bits salen por `shiftOut`) |
| 18 | Media suma con compuertas XOR y NAND | 4z8ZkFcpmuC | 100% | `TEST:LOGICA=LISTO` + `TEST:HA=a,b,suma,acarreo` con la tabla 00/01/10/11 |
| 19 | Biestable D 74HC74 como divisor por 2 | euU4CI6HwhX | 100% | `TEST:FF=TOGGLE-OK` (Q alterna en cada flanco de reloj) |
| 20 | Temporizador 555 en astable (reloj de ~14 Hz) | abIk7XRpSR4 | 100% | `TEST:555=ALTO,73173` + `BAJO,427` + `FREQ,13.6` + `TEST:555=OK` |
| 21 | Contador binario 4 bits 74HC93 con LEDs | fCB0eO8cBbn | 100% | `TEST:CONTADOR=1..15,0` + `FIN` (secuencia de 16 pulsos) |
| 22 | Carrusel de 4 LEDs con 74HC4017 | ij6ypc8wB5x | 100% | `TEST:4017=1,2,3,0` ciclando + `LISTO` (Q4 -> MR hace la vuelta en 4 pasos) |
| 23 | Faro automatico con rele SPDT, NPN y LDR (con rieles) | aF67dwSGoqC | 100% | `TEST:LUZ=6` + `TEST:RELE=ON` + `TEST:FOCO=1` y tras apagar `RELE=OFF` + `FOCO=0` |
| 24 | Alarma de movimiento con PIR, buzzer y LED | dgFz6r0k1xV | 100% | `TEST:PIR=LISTO` + `TEST:MOV=0`; con estimulo: `MOV=1` (LED encendido, buzer sonando) y `MOV=0` al soltar |
| 25 | Cerradura con teclado 4x4 y dos LEDs | g3KZdQc0DFu | 100% | `TEST:KP=LISTO` + `TEST:CLAVE=ESPERANDO`; con estimulo: `TECLA=1..4` + `CLAVE=OK` (LED de apertura) y `1111` + `CLAVE=FALLA` (LED de rechazo) |
| 26 | Caja fuerte con teclado 4x4 y LCD 16x2 | 9wyFlvHHzIo | 100% | `TEST:KP=LISTO` + `TEST:CLAVE=ESPERANDO`; con estimulo: `TECLA=1..4` + `CLAVE=OK` + `PANTALLA=ABIERTO` y `1111` + `CLAVE=FALLA` + `PANTALLA=DENEGADO` |
| 27 | Control de acceso con teclado, LCD y servo (servo libre) | cjjQKLuBQ2I | 100% | `TEST:KP=LISTO` + `CLAVE=ESPERANDO` + `SERVO=0`; con estimulo: `TECLA=1..4` + `CLAVE=OK` + `SERVO=90` + `PANTALLA=ABIERTO` y `1111` + `CLAVE=FALLA` + `SERVO=0` + `PANTALLA=DENEGADO` (asta del servo girada en la captura) |
| 28 | Contador 0-7 lento con reloj 555 y compuertas AND/OR/XOR, con banco de resistencias en una segunda placa | jApuXFjHQsc | 100% | `TEST:COMPUERTAS=LISTO` + `TEST:DIGITO=0..7..0` (un pulso cada ~1,7 s; la cadena AND/OR de compuertas arma el pulso que cuenta el Uno; el display ya no estalla) |

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
- **Nivel 5 (13-15):** bus de 4 bits y salida de texto. El LCD 16x2 va como
  módulo fuera de la placa (`free`, arriba de la placa): 16 terminales en una
  fila y un cuerpo de ~25 columnas que taparía las filas f..c, así que se
  monta con cables en vez de ensartarlo en la protoboard. Eso deja la placa
  entera para el sensor y permite combinaciones sensor + display: el 14 mide
  temperatura con un TMP36 y el 15 integra sensado, umbral y actuador
  (HC-SR04, display y alarma sonora) con dos cuerpos grandes conviviendo.
- **Nivel 6 (19-22):** lógica secuencial con chips que el drawer sí tiene:
  biestable D 74HC74 como divisor, 555 astable como reloj, contador binario
  74HC93 y contador Johnson 4017 en anillo. Todos los integrados van libres
  en fila sobre la placa (`x=560+200*i`, `y=-230`): apilados en la misma `x`
  el mazo de cables sube en columna. La vuelta en anillo del 4017 es
  hardware puro (Q4 -> MR), el Uno solo relojea y lee.
- **Nivel 7 (27-28):** combinaciones de chip + display. El 27 ya no monta el
  servo en la placa (`"free_parts"`) y el 28 junta cuatro piezas que antes
  vivían separadas: 555 como reloj lento, compuertas (74HC00 para el AND y el
  OR, 74HC86 como inversor) armando el pulso, y display 7 segmentos. Con dos
  o más integrados el display se corre a la derecha de la fila de chips para
  que los cuerpos no se toquen (ver fase 38).
- **Rieles (opt-in, fase 31):** cuando una fixture declara  `"wiring": "rails"` y reparte 5V o GND en dos o más nets, cada terminal
  baja al riel de la placa en su misma columna y el Uno alimenta el riel
  una sola vez; si se usan los dos rieles del mismo tipo se puentean en la
  columna 30. El default sigue siendo la estrella. Aplicado a `faro-rele-ldr`.
- **Fase 40 (sin circuito nuevo):** la regla "ningún cable sobre el cuerpo de
  una placa" pasó de mirarse en la captura a medirse. Los carriles subieron de
  ±115 a ±130 (el cuerpo llega a ±110 y quedaban 5 unidades de aire) y el
  puente devuelve la polilínea de cada cable; `route_band_violations` la
  revisa y el build falla si un tramo horizontal pasa sobre una placa. Encontró
  un defecto real en `lcd-distancia` (cable del piezo en y=106) que no era el
  anotado en la fase 39. Los reportes dicen cuántos cables se midieron.
- **Fase 39 (28, corregido):** el display de 7 segmentos de ánodo común
  estallaba en el simulador: común a 5V y segmentos directos a los pines del
  Uno, sin resistencia serie. El conteo seguía funcionando, así que el
  oráculo no lo veía. Ahora cada segmento lleva 220Ω y las siete
  resistencias viven en una **segunda protoboard** (`"board2": [refs]`)
  como banco vertical: el pin de abajo recibe el cable del Uno (banda
  inferior) y el de arriba sale al display (banda superior). El builder
  rechaza cualquier segmento o LED colgado directo de un pin o de 5V/GND.
- **Fase 36 (sin circuito nuevo):** las cinco filas con LCD se
  reconstruyeron con el cableado lateral. El LCD vive en `x=1100` y sus
  cables salen de lado antes de bajar; el display de 7 segmentos sigue en
  `870` porque sus terminales miran abajo. Los taps de alimentación buscan
  la columna libre mas cercana, asi que el GND del LCD cae en `T-26..T-29`
  junto a su parte y no al otro extremo del riel.
- **Fase 37 (sin circuito nuevo):** el piezo deja la placa cuando comparte
  circuito con el HC-SR04 (dos cuerpos grandes no caben sin que uno tape al
  otro) y el sensor recupera su columna 18. Con el sensor en 10 su cuerpo
  tapaba las filas altas sobre las columnas 3..20, donde caia el pin 2 de
  la resistencia del LCD. Los `+`/`-` de una parte que no es fuente ya no
  se pintan como alimentacion: el cable al piezo libre va en verde.
- **Nivel 11 (27):** tres bloques integrados y **colocacion libre** de
  una parte grande. La fixture pide `"free_parts": ["sv1"]` y el servo
  deja de montarse: va a la derecha de la placa y a su altura, con sus
  nets de alimentacion bajando al **riel de abajo**, no al de arriba. La
  posicion se midio en vivo (sonda `1altWwNOQdW`): en la fila del display
  el cable de senal lo cruza, y una fila mas arriba el cuerpo del servo se
  monta encima del teclado. El cerrojo se abre a 90 grados y vuelve solo a
  0; el LCD muestra ABIERTO / DENEGADO.
- **Nivel 10 (26):** integracion de bloques. Primer circuito con dos
  bloques ya verificados conviviendo: entrada matricial (D2..D9) y salida
  de texto (LCD en 4 bits sobre A0..A5, que el simulador trata como
  digitales). El reparto de pines es lo que hace posible el circuito: los
  digitales libres no alcanzan para los dos. La alimentacion va por rieles
  en vertical; verificado en pantalla con `ABIERTO` y `DENEGADO`.
- **Nivel 9 (25):** entrada matricial. El teclado 4x4 se barre a mano
  (`INPUT_PULLUP`, una fila en LOW por vuelta) sin libreria. El simulador
  solo cierra la matriz mientras el boton del mouse esta **presionado**:
  un click suelto no registra la tecla y el sketch espera a que se suelte
  para que una pulsacion mantenida valga una sola tecla. El oraculo de
  teclas lo produce `scripts/keypad_stimulus.py`.
- **Nivel 8 (24):** sensado de movimiento. El PIR no tiene valor fijo:
  el runner solo puede leer el reposo (`MOV=0`), asi que el oraculo de
  movimiento lo produce un paso de interaccion (`scripts/pir_stimulus.py`
  arrastra el punto de deteccion dentro del cono del sensor). El sketch
  imprime **solo los cambios** de estado, de modo que el serial se lee como
  una bitacora: `LISTO`, `MOV=0`, `MOV=1`, `MOV=0`.
- **Nivel 7 (23):** conmutacion de carga. El rele SPDT lo mueve un NPN con
  resistencia de base y diodo de recirculacion (un pin del Uno no puede con
  la bobina), el contacto COM1-R1 alimenta una bombilla y A1 lee el nodo del
  contacto: asi el serial demuestra las dos posiciones y no solo el
  encendido. Rele y bombilla van libres en la fila de partes libres.
- **Cableado:** las nets de 3+ extremos se emparejan en estrella desde el pin
  del Uno, no en cadena. Un cable hueco-hueco lo dibuja recto el simulador y
  cruzaba en diagonal por encima de los cuerpos; colgado del mismo extremo el
  puente lo rutea por carriles.

## Latencias

Las latencias por herramienta de cada corrida quedan en su reporte
individual (`docs/reportes/<fixture>.md`). Las caras siguen siendo
`tinkercad_create_circuit` (~10-18 s), `tinkercad_set_code` (~17 s) y
`tinkercad_open_circuit` (~9-12 s); `tinkercad_inspect_circuit` ronda 0.1-0.2 s
y es lo que se usa masivamente para verificar.

## Pendientes conocidos

- El contraste del LCD va con `VO` a GND: el potenciómetro en su posición por
  defecto deja la pantalla en blanco en el simulador (y su cuerpo tapa el
  display). Falta poder fijar el wiper por propiedad para usar pot real.
- El 7 segmentos directo no entra: 7 resistencias son 42 columnas para una
  placa de 30. Se resuelve con el 74HC595 (circuito 17) o con el banco en
  una segunda protoboard (circuito 28).
- Dos cuerpos grandes (HC-SR04 + piezo) comparten placa: el sensor cede la
  mitad derecha (arranca en la columna 10) porque su módulo se dibuja mucho
  más ancho que sus cuatro pines.
- El sampler de píxeles (brillo de LED) no calibra en headless; el oráculo
  real es el serial.
- Los saltos rectos entre huecos de la misma placa (`5g -> 8c`) siguen en
  diagonal a propósito: son puentes cortos sobre el plástico. El reporte los
  cuenta y no rompen el build.
