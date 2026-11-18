"""Geometria de las dos breadboards del catalogo y huellas de las piezas.

La fidelidad del puente se mide pin a pin, asi que la placa no aparece en el
circuito: sirve para **unir** patas. Pero para tender puentes cortos hay que
saber donde cae cada pata, y eso es esta tabla.

Todo esta medido en vivo el 2026-11-15 sobre disenos desechables (creados y
borrados). Ver ``docs/superpowers/specs/2026-11-15-layout-v2-design.md``:

- Small (did 111211): 30 columnas, x de -145 a 145 a paso 10, rieles
  ``T+/T-/B+/B-`` en y -85/-95 y 85/95.
- Large (did 116648): 62 columnas utiles, x de -295 a 315; el modelo rotula
  las dos extremas ``A98/A99`` (x -315/-305) y no se usan. Tiene **cuatro
  filas de riel de 50 huecos**: y +85 (``Y``) y +95 (``Z``) arriba, y -85/-95
  abajo, donde **el modelo rotula las dos ``X``** (un solo nodo): ese par no
  sirve para llevar positivo y tierra a la vez.
- Filas: paso 10, ``a`` = +55 ... ``j`` = -55, en las dos placas. La grande
  las rotula al reves (``A`` = -55); el puente ubica los huecos por ``y``, asi
  que el cerebro habla siempre la convencion de abajo.
- Media columna: los cinco huecos de una mitad de la misma columna son **un
  solo nodo** (medido: ``f6`` == ``i6`` en la Small, ``F6`` == ``I6`` en la
  grande). Por eso ``half_holes`` no es decorativo: es el nodo.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Tuple

ROW_Y: Dict[str, int] = {
    "a": 55,
    "b": 45,
    "c": 35,
    "d": 25,
    "e": 15,
    "f": -15,
    "g": -25,
    "h": -35,
    "i": -45,
    "j": -55,
}

# Las filas de arriba (y > 0) y las de abajo. Ojo: en la placa grande el
# modelo las llama al reves; nosotros hablamos y, no nombres del modelo.
_TOP_ROWS: Tuple[str, ...] = ("a", "b", "c", "d", "e")
_BOTTOM_ROWS: Tuple[str, ...] = ("f", "g", "h", "i", "j")


class Board(NamedTuple):
    kind: str
    did: int
    columns: int
    x0: int
    row_y: Dict[str, int]
    rails: Dict[str, int]
    # Huecos por riel. 0 = los mismos que tiene la placa. La grande declara
    # 50: sus cuatro filas de riel son mas cortas que las 62 columnas.
    rail_columns: int = 0
    # Columnas que SI tienen hueco de riel, vacio = 1..columns. La grande no
    # los tiene seguidos: medido el 2026-11-15, son 50 huecos repartidos en las
    # primeras 60 columnas con un salto cada seis (6, 12, 18, 24, 30, 31, 37,
    # 43, 49, 55) y dos al final (61, 62). Un cable a un hueco que no existe no
    # se puede tender: el endpoint no resuelve y el build se cae a medias.
    rail_holes: Tuple[int, ...] = ()


SMALL = Board(
    "small", 111211, 30, -145, ROW_Y,
    {"T-": -95, "T+": -85, "B-": 85, "B+": 95},
    30, tuple(range(1, 31)),
)
LARGE = Board(
    "large", 116648, 62, -295, ROW_Y,
    {"T+": 85, "T-": 95, "B+": -85, "B-": -95},
    # El riel llega hasta la columna 60 (ultimo hueco en x=295), y de esas 60
    # columnas solo 50 tienen hueco: la lista de abajo manda.
    60,
    (1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 19, 20, 21, 22, 23,
     25, 26, 27, 28, 29, 32, 33, 34, 35, 36, 38, 39, 40, 41, 42, 44, 45, 46,
     47, 48, 50, 51, 52, 53, 54, 56, 57, 58, 59, 60),
)

_BY_KIND: Dict[str, Board] = {"small": SMALL, "large": LARGE}


def board(kind: str) -> Board:
    """Tabla de la placa por nombre (``"small"`` / ``"large"``)."""
    return _BY_KIND[kind]


def columns(kind: str) -> range:
    """Columnas utiles, 1..N."""
    return range(1, board(kind).columns + 1)


def rail_holes(kind: str) -> Tuple[int, ...]:
    """Columnas que tienen hueco en el riel (la grande los tiene salteados)."""
    b = board(kind)
    return tuple(b.rail_holes) or tuple(columns(kind))


def _check_col(kind: str, col: int) -> Board:
    b = board(kind)
    if not isinstance(col, int) or isinstance(col, bool) or not 1 <= col <= b.columns:
        raise ValueError(f"{kind}: columna fuera de rango (1..{b.columns}): {col!r}")
    return b


def _check_row(row: str) -> str:
    fila = str(row).lower()
    if fila not in ROW_Y:
        raise ValueError(f"fila desconocida: {row!r} (a..j)")
    return fila


def x_of(kind: str, col: int) -> int:
    """x relativa al origen de la placa del hueco ``col`` (paso 10)."""
    b = _check_col(kind, col)
    return b.x0 + 10 * (col - 1)


def hole(kind: str, col: int, row: str) -> str:
    """Nombre del hueco en el lenguaje del puente: ``"6e"``."""
    _check_col(kind, col)
    return f"{col}{_check_row(row)}"


def half(row: str) -> str:
    """Mitad fisica de la fila: ``"top"`` (y > 0) o ``"bottom"``."""
    fila = _check_row(row)
    return "top" if fila in _TOP_ROWS else "bottom"


def half_holes(col: int, h: str) -> List[str]:
    """Los cinco huecos de la media columna, de arriba a abajo.

    Esos cinco huecos son el mismo nodo; el orden es el del dibujo para que
    los puentes se tiendan sin cruzar.
    """
    if h not in ("top", "bottom"):
        raise ValueError(f"mitad desconocida: {h!r} (top/bottom)")
    filas = _TOP_ROWS if h == "top" else _BOTTOM_ROWS
    return [f"{col}{fila}" for fila in filas]


# Huella = {pin de fixture -> (delta de columna, fila)}, ancla en el pin 1.
# Medidas en vivo, no deducidas del datasheet: lo que importa es donde reporta
# el modelo cada pata al insertar la pieza.

_DIP14 = {
    "1A": (0, "e"),
    "1B": (1, "e"),
    "1Y": (2, "e"),
    "2A": (3, "e"),
    "2B": (4, "e"),
    "2Y": (5, "e"),
    "GND": (6, "e"),
    "3Y": (6, "f"),
    "3A": (5, "f"),
    "3B": (4, "f"),
    "4Y": (3, "f"),
    "4A": (2, "f"),
    "4B": (1, "f"),
    "Vcc": (0, "f"),
}

# DIP-16 de los dos integrados del proyecto final de Sistemas Digitales,
# medidos en vivo el 2026-11-16 sobre el diseno desechable
# bFxL8AFHD9k (`build_circuit_model` con una pata anclada y lectura de
# `placed[ref].holes`; no se dedujo del datasheet).
#
# CD4511 ("7-Segment Decoder [CD4511]", did 121827). Anclado por `AIN` en
# `10e` el modelo devolvio las 16 patas asi: fila de arriba (e) las ocho
# entradas/controles y fila de abajo (f) los siete segmentos mas Vcc. Las
# entradas BCD se llaman AIN/BIN/CIN/DIN en el modelo (prefijo `IN` para no
# chocar con los segmentos) y los segmentos A..G; aca se declaran en
# minuscula para que un segmento se llame igual en la fixture y en el
# display (`seg.d`), y `_FREE_PART_PINS` traduce si la pieza va libre.
_DIP16_4511 = {
    "BIN": (-6, "e"),
    "CIN": (-5, "e"),
    "LT": (-4, "e"),
    "BI": (-3, "e"),
    "LE": (-2, "e"),
    "DIN": (-1, "e"),
    "AIN": (0, "e"),
    "GND": (1, "e"),
    "Vcc": (-6, "f"),
    "f": (-5, "f"),
    "g": (-4, "f"),
    "a": (-3, "f"),
    "b": (-2, "f"),
    "c": (-1, "f"),
    "d": (0, "f"),
    "e": (1, "f"),
}

# 74HC283 ("4-Bit full adder [74HC283]", did `ic74hc283`; es el unico
# integrado del catalogo sin `did` numerico). Anclado por `A0` en `25e`:
# fila e = A0..A3/S1/B0..B3/CIN/GND desordenados por el dibujo del chip,
# fila f = la otra mitad. Los ocho pines de cada fila caen en columnas
# distintas, asi que no hay medias columnas compartidas.
_DIP16_283 = {
    "S1": (-4, "e"),
    "B1": (-3, "e"),
    "A1": (-2, "e"),
    "S0": (-1, "e"),
    "A0": (0, "e"),
    "B0": (1, "e"),
    "CIN": (2, "e"),
    "GND": (3, "e"),
    "Vcc": (-4, "f"),
    "B2": (-3, "f"),
    "A2": (-2, "f"),
    "S2": (-1, "f"),
    "A3": (0, "f"),
    "B3": (1, "f"),
    "S3": (2, "f"),
    "COUT": (3, "f"),
}

# El 74HC04 (Hex Inverter, medido en vivo el 2026-11-15 en 2rI5SQHDHcD) ocupa
# el mismo DIP-14 pero con OTRA numeracion: seis compuertas de una entrada, asi
# que 1A/1Y van en las columnas 0 y 1 y no en 0 y 2. Comparte geometria, no
# nombres: por eso tiene su propia tabla.
_DIP14_NOT = {
    "1A": (0, "e"),
    "1Y": (1, "e"),
    "2A": (2, "e"),
    "2Y": (3, "e"),
    "3A": (4, "e"),
    "3Y": (5, "e"),
    "GND": (6, "e"),
    "4Y": (6, "f"),
    "4A": (5, "f"),
    "5Y": (4, "f"),
    "5A": (3, "f"),
    "6Y": (2, "f"),
    "6A": (1, "f"),
    "Vcc": (0, "f"),
}

# El 555 tambien tiene las hileras a 30 unidades (30 y no 20): anclado por
# `CTRL` en la fila de abajo la otra hilera queda arriba, una en cada mitad.
# Anclarlo en `e` deja `Vcc` y `GND` en la misma mitad (corto medido).
_DIP8_555 = {
    "CTRL": (0, "f"),
    "THR": (-1, "f"),
    "DIS": (-2, "f"),
    "Vcc": (-3, "f"),
    "Reset": (0, "e"),
    "OUT": (-1, "e"),
    "TRIG": (-2, "e"),
    "GND": (-3, "e"),
}

_RESISTOR = {"1": (0, "e"), "2": (0, "g")}
# LED generico (did 58422): las dos patas caen en la MISMA fila, a una columna
# de distancia. Medido en vivo el 2026-11-17 en una sonda desechable
# (7qLmhgFGPeP, ya borrada):
#   led anclado por `anode` en `10i` a 0 grados   -> {"anode": "10i", "cathode": "9i"}
#   led anclado por `anode` en `20i` a 180 grados -> {"anode": "20i", "cathode": "21i"}
# La tabla va en el angulo que usa el layout (180, ver `layout_v2._ANGLE`): el
# puente NO gira la huella, solo pasa `angle` a la pieza. Se elige 180 porque
# deja el anodo a la IZQUIERDA y el catodo a la derecha: con la resistencia en
# serie a la izquierda, el puente al anodo no pasa por encima del hueco del
# catodo (que es otro net).
_LED = {"anode": (0, "i"), "cathode": (1, "i")}
# Capacitor ceramico (did 57752): las dos patas caen en huecos vecinos de la
# MISMA fila, no una encima de la otra. Medido en vivo el 2026-11-15 en una
# sonda desechable (avLAlMuZhih, ya borrada): anclado en `10e` el puente
# responde `{'1': '10e', '2': '11e'}` con angulo 0; en `10f`, `{'1': '10f',
# '2': '11f'}`. O sea (0, +1 columna) en la fila del ancla.
# El ancla va en `f` (mitad de abajo) a proposito: asi cada net del capacitor
# enlaza con la placa grande por un solo cable horizontal y no hace falta
# cruzar el canal en la placa chica.
_CAPACITOR = {"1": (0, "f"), "2": (1, "f")}

# El 74HC73 (medido en vivo el 2026-11-15, fqm2OOLKTr3) tambien tiene las dos
# hileras a 30 unidades: anclado por `1J` en la fila de abajo, la otra queda
# arriba. Ojo: no es la huella del DIP-14 de compuertas, cuyas hileras caen en
# `e` y `f`; aca la de arriba es `e` y la de abajo `f`, pero repartidas al
# reves (1J abajo).
_DIP14_JK = {
    "1J": (0, "f"),
    "1NQ": (1, "f"),
    "1Q": (2, "f"),
    "GND": (3, "f"),
    "2K": (4, "f"),
    "2Q": (5, "f"),
    "2NQ": (6, "f"),
    "1CP": (0, "e"),
    "1R": (1, "e"),
    "1K": (2, "e"),
    "Vcc": (3, "e"),
    "2CP": (4, "e"),
    "2R": (5, "e"),
    "2J": (6, "e"),
}

# El 74HC74 (did 116725) es un DIP-14 con las hileras a 20 unidades, como el
# de compuertas, medido en vivo el 2026-11-17 sobre el desechable 9NMhuctcriI:
# anclado por `1D` en `10e`, la fila `e` lleva 1RD/1D/1CP/1SD/1Q/1NQ/GND y la
# fila `f` Vcc/2RD/2D/2CP/2SD/2Q/2NQ. A diferencia del 74HC73, dispara en
# flanco de subida y tiene preset y reset activos en bajo por cada mitad.
_DIP14_DFF = {
    "1RD": (-1, "e"),
    "1D": (0, "e"),
    "1CP": (1, "e"),
    "1SD": (2, "e"),
    "1Q": (3, "e"),
    "1NQ": (4, "e"),
    "GND": (5, "e"),
    "Vcc": (-1, "f"),
    "2RD": (0, "f"),
    "2D": (1, "f"),
    "2CP": (2, "f"),
    "2SD": (3, "f"),
    "2Q": (4, "f"),
    "2NQ": (5, "f"),
}

# 10 patas en 5 columnas, una por media columna: la fila `e` para cinco
# segmentos y la `i` para los otros cinco. No hay dos patas en el mismo nodo.
_DISPLAY_7SEG = {
    "a": (0, "e"),
    "b": (-1, "e"),
    "com2": (1, "e"),
    "f": (2, "e"),
    "g": (3, "e"),
    "dp": (-1, "i"),
    "c": (0, "i"),
    "com1": (1, "i"),
    "d": (2, "i"),
    "e": (3, "i"),
}

# Las dos piezas del mando de la v4 se montan en la placa chica. Medido en
# vivo el 2026-11-16 sobre un diseno desechable (sondeo de `name2terminal`
# de los dos devices, `bbDesc.x/y` en unidades de la placa):
#
#   Slideswitch (did 58458): clave 1 (-10, 0), 3 (0, 0), 2 (+10, 0)
#                            (3 = Common, y el switch nace con el comun en 1)
#   Pushbutton  (did 144786): clave 1 (-10,-15), 2 (-10,+15),
#                                  3 (+10,-15), 4 (+10,+15)
#                             (1-2 un nodo interno, 3-4 el otro)
#
# OJO con los dos espacios de nombres: la **fixture** llama a las patas del
# pulsador `1` (senal) y `2` (Vcc), que en el modelo son las claves `4` y `2`;
# al interruptor lo llama `common`/`1`/`2` y el modelo usa `3`/`1`/`2`. Las
# huellas de abajo van en el espacio de la FIXTURE (el layout y las nets
# hablan ese), y `MODEL_PIN` traduce a la clave del modelo cuando hay que
# pedirsela al puente.
#
# El interruptor tiene las tres patas en **una sola fila** (y = 0 relativo a
# su origen): insertado, las tres caen en la fila del ancla y en tres columnas
# seguidas. El pulsador cae justo en las filas `e` (+15) y `f` (-15), o sea
# una pata por mitad del canal: cada nodo interno queda en UNA columna, con
# las dos mitades puenteadas por dentro de la pieza. Por eso la huella del
# pulsador declara tambien las dos patas que la fixture no cablea (`m1`/`m3`,
# las claves 1 y 3 del modelo): su media columna es el mismo nodo que una
# pata cableada, y si el ruteo metiera otro net ahi seria un corto invisible.
_SLIDESWITCH = {"1": (-1, "e"), "common": (0, "e"), "2": (1, "e")}
_PUSHBUTTON = {
    "1": (0, "e"),     # modelo 4 (Terminal 2a): senal del RESET
    "2": (-2, "e"),    # modelo 2 (Terminal 1a): Vcc
    "m1": (-2, "f"),   # modelo 1: mismo nodo interno que "2"
    "m3": (0, "f"),    # modelo 3: mismo nodo interno que "1"
}

# Pata de la fixture -> clave del modelo (lo que resuelve el puente).
MODEL_PIN: Dict[str, Dict[str, str]] = {
    "slideswitch": {"common": "3", "1": "1", "2": "2"},
    "pushbutton": {"1": "4", "2": "2"},
}


def model_pin(ctype: str, pin: str) -> str:
    """Clave del modelo para una pata de la fixture (identidad si no hay mapa)."""
    return MODEL_PIN.get(str(ctype), {}).get(str(pin), str(pin))


FOOTPRINTS: Dict[str, Dict[str, Tuple[int, str]]] = {
    "dip14": _DIP14,
    "dip14-jk": _DIP14_JK,
    "dip14-dff": _DIP14_DFF,
    "dip14-not": _DIP14_NOT,
    "dip16-4511": _DIP16_4511,
    "dip16-283": _DIP16_283,
    "dip8-555": _DIP8_555,
    "resistor": _RESISTOR,
    "led": _LED,
    "capacitor": _CAPACITOR,
    "display-7seg": _DISPLAY_7SEG,
    "slideswitch": _SLIDESWITCH,
    "pushbutton": _PUSHBUTTON,
}

# Huella por tipo de pieza de la fixture. Las compuertas comparten el DIP-14
# de 74HC00/08/32/86 (mismos nombres de pin y mismas hileras e/f).
_FOOTPRINT_BY_TYPE: Dict[str, str] = {
    "and-gate": "dip14",
    "or-gate": "dip14",
    "not-gate": "dip14-not",
    "xor-gate": "dip14",
    "nand-gate": "dip14",
    "flip-flop-jk": "dip14-jk",
    "flip-flop-d": "dip14-dff",
    "timer-555": "dip8-555",
    "seven-segment": "display-7seg",
    "resistor": "resistor",
    "led": "led",
    "capacitor": "capacitor",
    "slideswitch": "slideswitch",
    "pushbutton": "pushbutton",
    # Proyecto final de Sistemas Digitales: los dos DIP-16 medidos el
    # 2026-11-16 (ver `_DIP16_4511` / `_DIP16_283`).
    "bcd-decoder": "dip16-4511",
    "four-bit-adder": "dip16-283",
}


def footprint(name: str) -> Dict[str, Tuple[int, str]]:
    """Copia de la huella de una pieza (nadie muta la tabla del layout)."""
    return dict(FOOTPRINTS[name])


def footprint_for(ctype: str) -> Dict[str, Tuple[int, str]]:
    """Huella de un tipo de la fixture (``"and-gate"`` -> DIP-14 de compuertas)."""
    return footprint(_FOOTPRINT_BY_TYPE[ctype])
