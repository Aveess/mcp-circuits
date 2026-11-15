"""Geometria de las dos breadboards del catalogo y huellas de las piezas.

La fidelidad del puente se mide pin a pin, asi que la placa no aparece en el
circuito: sirve para **unir** patas. Pero para tender puentes cortos hay que
saber donde cae cada pata, y eso es esta tabla.

Todo esta medido en vivo el 2026-11-15 sobre disenos desechables (creados y
borrados). Ver ``docs/superpowers/specs/2026-11-15-layout-v2-design.md``:

- Small (did 111211): 30 columnas, x de -145 a 145 a paso 10, rieles
  ``T+/T-/B+/B-`` en y -85/-95 y 85/95.
- Large (did 116648): 62 columnas utiles, x de -295 a 315; el modelo rotula
  las dos extremas ``A98/A99`` (x -315/-305) y no se usan. **Sin rieles
  utilizables**: los dos de abajo comparten nombre ``X`` y son el mismo nodo.
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


SMALL = Board("small", 111211, 30, -145, ROW_Y, {"T-": -95, "T+": -85, "B-": 85, "B+": 95})
LARGE = Board("large", 116648, 62, -295, ROW_Y, {})

_BY_KIND: Dict[str, Board] = {"small": SMALL, "large": LARGE}


def board(kind: str) -> Board:
    """Tabla de la placa por nombre (``"small"`` / ``"large"``)."""
    return _BY_KIND[kind]


def columns(kind: str) -> range:
    """Columnas utiles, 1..N."""
    return range(1, board(kind).columns + 1)


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

FOOTPRINTS: Dict[str, Dict[str, Tuple[int, str]]] = {
    "dip14": _DIP14,
    "dip14-jk": _DIP14_JK,
    "dip14-not": _DIP14_NOT,
    "dip8-555": _DIP8_555,
    "resistor": _RESISTOR,
    "capacitor": _CAPACITOR,
    "display-7seg": _DISPLAY_7SEG,
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
    "timer-555": "dip8-555",
    "seven-segment": "display-7seg",
    "resistor": "resistor",
    "capacitor": "capacitor",
}


def footprint(name: str) -> Dict[str, Tuple[int, str]]:
    """Copia de la huella de una pieza (nadie muta la tabla del layout)."""
    return dict(FOOTPRINTS[name])


def footprint_for(ctype: str) -> Dict[str, Tuple[int, str]]:
    """Huella de un tipo de la fixture (``"and-gate"`` -> DIP-14 de compuertas)."""
    return footprint(_FOOTPRINT_BY_TYPE[ctype])
