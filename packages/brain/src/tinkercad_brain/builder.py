"""Builder: fixture (components/nets) -> llamada al modelo del puente.

Traduce una fixture a los argumentos de la tool
`tinkercad_build_circuit_model(parts, wires, code)` del puente, donde los
wires son dicts {"from", "to", "color"} de extremos por hueco ("uno.D13",
"1i", "led1.anode" ya traducido a su hueco, etc.), ordenados alimentacion,
tierra y senales para un ruteo ortogonal por carriles estable. El Arduino
no va como part: el puente crea el Uno. Solo stdlib + modulos del proyecto.
"""

from __future__ import annotations

import json
import re

from tinkercad_brain.fase0.component_map import TYPE_MAP
from tinkercad_brain.fase0.probe import ProbeStep, run_steps
from tinkercad_brain.layout import LayoutError, plan_layout

__all__ = ["BuildError", "DID_BY_TYPE", "fixture_to_model_call", "build_circuit"]


class BuildError(Exception):
    """La fixture no puede convertirse en una llamada al modelo completa."""


# Mapa inverso de TYPE_MAP: slug de fixture -> nombre visible en Tinkercad.
_TYPE_BY_SLUG: dict[str, str] = {slug: name for name, slug in TYPE_MAP.items()}

# Tabla DID minima verificada (el puente crea el Uno: arduino-uno no es part).
DID_BY_TYPE: dict[str, int] = {
    "led": 58422,
    "resistor": 53184,
    "pushbutton": 144786,
    "servo": 142073,
    "potentiometer": 45547,
    "tmp36": 112324,
    "ultrasonic-hcsr04": 219295,
    "led-rgb-common-cathode": 58456,
    "transistor-npn": 58468,
    "diode": 58320,
    "dc-motor": 114158,
    "l293d": 112326,
    "battery-9v": 116841,
    # Verificados en vivo (circuito cZcqbZ3eNlA).
    "buzzer": 114067,
    "photoresistor": 116691,
    # LCD 16x2 verificado en vivo (circuito ib98EAPoqPP, modo 4 bits).
    "lcd-16x2": 113878,
    # Display 7 segmentos (uno digito, catodo comun) verificado en vivo.
    "seven-segment": 129710,
    # 74HC595 (8-Bit Shift Register) verificado en vivo: did 116695.
    "shift-register": 116695,
    # 74HC86 (Quad XOR) y 74HC00 (Quad NAND) verificados en vivo.
    "xor-gate": 116727,
    "nand-gate": 116696,
    # 74HC74 (Dual D Flip-Flop) verificado en vivo: did 116725.
    "flip-flop-d": 116725,
    # 555 Timer (did 116689) y capacitor (did 57752) verificados en vivo.
    "timer-555": 116689,
    "capacitor": 57752,
    # 74HC93 (4-Bit Binary Counter) verificado en vivo: did 116728.
    "binary-counter": 116728,
    # 74HC4017 (Johnson Decade Counter) verificado en vivo: did 129343.
    "decade-counter": 129343,
    # Relay SPDT verificado en vivo: did 122167.
    "relay-spdt": 122167,
    # Bombilla (Light bulb) verificada en vivo: did 116693.
    "light-bulb": 116693,
    # PIR Sensor verificado en vivo: did 234203.
    "pir-sensor": 234203,
    # Keypad 4x4 verificado en vivo: did 203761.
    "keypad-4x4": 203761,
}

# Types que el builder ya soporta pero TYPE_MAP (component_map, otro
# modulo) aun no registra: solo se usan para no rechazarlos por nombre.
_BUILDER_ONLY_TYPES = frozenset({"l293d", "battery-9v"})

# Partes de 3 pines en fila unica: orden fisico (nombre de fixture) y
# nombre real del pin en Tinkercad. El primer pin va en el `at` del
# placement; los demas a +1 y +2 columnas en la misma fila.
_THREE_PIN_PINS: dict[str, tuple[tuple[str, str], ...]] = {
    "servo": (("gnd", "Ground"), ("vcc", "Power"), ("signal", "Signal")),
    "potentiometer": (("1", "term0"), ("2", "wiper"), ("3", "term1")),
    "tmp36": (("vcc", "Vcc"), ("vout", "Vout"), ("gnd", "Gnd")),
    # Reales verificados en colocacion: collector/base/emitter en minuscula.
    "transistor-npn": (
        ("collector", "collector"), ("base", "base"), ("emitter", "emitter")
    ),
}

# Motor DC libre (sin huecos): supuesto a verificar en vivo, los
# terminales del DC Motor en Tinkercad se llaman "1" y "2" (catalogo
# netchuu); positive->"1", negative->"2". El puente los resuelve.
_MOTOR_TERMINALS: dict[str, str] = {"positive": "1", "negative": "2"}

# Bateria 9V libre (sin huecos, como el motor): terminales reales
# verificados en vivo "+" y "-".
_BATTERY_TERMINALS: dict[str, str] = {"positive": "+", "negative": "-"}

# L293D (16 pines, verificado en vivo): ancla Enable1 en <B>f deja en la
# fila f (B..B+7) la primera tupla y en la fila i (B..B+7) la segunda.
# Mapa explicito fixture -> pin real (capitalizado, sin reglas magicas).
_L293D_ROW_F: tuple[tuple[str, str], ...] = (
    ("enable1", "Enable1"), ("input1", "Input1"), ("output1", "Output1"),
    ("gnd", "GND"), ("gnd1", "GND1"), ("output2", "Output2"),
    ("input2", "Input2"), ("vs", "Vs"),
)
_L293D_ROW_I: tuple[tuple[str, str], ...] = (
    ("vss", "Vss"), ("input4", "Input4"), ("output4", "Output4"),
    ("gnd3", "GND3"), ("gnd2", "GND2"), ("output3", "Output3"),
    ("input3", "Input3"), ("enable2", "Enable2"),
)
_L293D_REAL_BY_FIXTURE: dict[str, str] = dict(_L293D_ROW_F + _L293D_ROW_I)
# fixture pin -> (fila, desplazamiento de columna desde el ancla)
_L293D_PIN_HOLES: dict[str, tuple[str, int]] = {
    **{pin: ("f", i) for i, (pin, _real) in enumerate(_L293D_ROW_F)},
    **{pin: ("i", i) for i, (pin, _real) in enumerate(_L293D_ROW_I)},
}
# Angulo 180 (verificado en vivo, ancla Enable1 en 17f): la fila f baja
# de columna (enable1=17f ... vs=10f) y la opuesta pasa a ser la fila e
# espejada (vss=17e ... enable2=10e).
_L293D_PIN_HOLES_180: dict[str, tuple[str, int]] = {
    **{pin: ("f", -i) for i, (pin, _real) in enumerate(_L293D_ROW_F)},
    **{pin: ("e", -i) for i, (pin, _real) in enumerate(_L293D_ROW_I)},
}

# HC-SR04 (4 pines): evidencia en vivo DID 219295, pin real "pos" en un
# hueco de la fila d deja pos=+0, trig=+1, echo=+2, neg=+3 columnas.
_FOUR_PIN_PINS: dict[str, tuple[tuple[str, str], ...]] = {
    "ultrasonic-hcsr04": (
        ("vcc", "pos"), ("trig", "trig"), ("echo", "echo"), ("gnd", "neg")
    ),
}

# LED RGB catodo comun (4 pines): evidencia en vivo DID 58456, pin real
# "terminal-red" en un hueco de la fila i deja red=+0, cathode=+1,
# blue=+2, green=+3 columnas, misma fila (ojo: blue antes que green).
_RGB_PINS: dict[str, tuple[tuple[str, str], ...]] = {
    "led-rgb-common-cathode": (
        ("red", "terminal-red"),
        ("cathode", "terminal-cathode"),
        ("blue", "terminal-blue"),
        ("green", "terminal-green"),
    ),
}

_LINEAR_PIN_PINS: dict[str, tuple[tuple[str, str], ...]] = {
    **_THREE_PIN_PINS,
    **_FOUR_PIN_PINS,
    **_RGB_PINS,
}

# Piezo (did 114067, verificado en vivo en cZcqbZ3eNlA): ancla "+" en un
# hueco de fila cualquiera; angle 0 deja "-" 5 columnas a la derecha, misma
# fila. Nombre real del terminal en Tinkercad: "+" y "-".
_BUZZER_ANCHOR = "positive"
_BUZZER_REAL_PINS: dict[str, str] = {"positive": "+", "negative": "-"}
_BUZZER_NEGATIVE_OFFSET = 5

# Photoresistor (did 116691, verificado en vivo en cZcqbZ3eNlA, type real
# "Photoresistor (LDR)"): ancla "terminal-1" en un hueco de fila cualquiera;
# angle 0 deja "terminal-2" 1 columna a la derecha, misma fila.
_PHOTORESISTOR_ANCHOR = "1"
_PHOTORESISTOR_REAL_PINS: dict[str, str] = {
    "1": "terminal-1", "2": "terminal-2",
}
_PHOTORESISTOR_SECOND_OFFSET = 1

# LCD 16x2 (did 113878, type real "LCD 16 x 2", verificado en vivo en
# ib98EAPoqPP): 16 terminales en UNA fila. El display NO va montado en la
# protoboard: el layout lo emite libre (`free`) sobre la placa y los
# cables terminan en sus terminales reales (lcd1.RS, lcd1.DB4, ...). El
# mapa de abajo se usa para validar el pin y, en la rama de compatibilidad
# con `at`, para derivar huecos. Los nombres reales son los mismos de la
# fixture (mapa identidad), pero se declaran explicitos para rechazar
# pines desconocidos en vez de rutear un terminal inventado.
_LCD_ANCHOR = "GND"
_LCD_REAL_PINS: dict[str, str] = {
    "GND": "GND", "VDD": "VDD", "VO": "VO", "RS": "RS", "RW": "RW", "E": "E",
    "DB0": "DB0", "DB1": "DB1", "DB2": "DB2", "DB3": "DB3",
    "DB4": "DB4", "DB5": "DB5", "DB6": "DB6", "DB7": "DB7",
    "LED+": "LED+", "LED-": "LED-",
}
_LCD_PIN_OFFSETS: dict[str, int] = {
    pin: index for index, pin in enumerate(_LCD_REAL_PINS)
}

# Display 7 segmentos (did 129710, un digito, catodo comun). Igual que el
# LCD, va libre fuera de la placa: 10 terminales. Los nombres reales
# coinciden con los de la fixture (a..g, dp, com1, com2).
_SEVEN_SEG_REAL_PINS: dict[str, str] = {
    "a": "a", "b": "b", "c": "c", "d": "d", "e": "e", "f": "f", "g": "g",
    "dp": "dp", "com1": "com1", "com2": "com2",
}

# 74HC595 (did 116695, type real "8-Bit Shift Register [74HC595]"): 16
# terminales. Va libre fuera de la placa, como el display, y los cables
# terminan en el pin real del integrado (ic.Q0, ic.STCP...). Los nombres de
# la fixture son los del catalogo para no traducir nada.
_SHIFT_REGISTER_REAL_PINS: dict[str, str] = {
    "Q0": "Q0", "Q1": "Q1", "Q2": "Q2", "Q3": "Q3",
    "Q4": "Q4", "Q5": "Q5", "Q6": "Q6", "Q7": "Q7",
    "Q7S": "Q7S", "DS": "DS", "SHCP": "SHCP", "STCP": "STCP",
    "OE": "OE", "MR": "MR", "Vcc": "Vcc", "GND": "GND",
}

# Compuertas logicas (14 pines). Van libres fuera de la placa, como el 595:
# sus terminales se cablean directo y no hace falta geometria de huecos. Los
# nombres de la fixture son los del catalogo, asi que el mapa es identidad
# (explicito para rechazar un pin inventado).
_XOR_REAL_PINS: dict[str, str] = {
    "1A": "1A", "1B": "1B", "1Y": "1Y",
    "2A": "2A", "2B": "2B", "2Y": "2Y",
    "3A": "3A", "3B": "3B", "3Y": "3Y",
    "4A": "4A", "4B": "4B", "4Y": "4Y",
    "Vcc": "Vcc", "GND": "GND",
}
_NAND_REAL_PINS: dict[str, str] = {
    "1A": "1A", "1B": "1B", "1Y": "1Y",
    "2A": "2A", "2B": "2B", "2Y": "2Y",
    "3A": "3A", "3B": "3B", "3Y": "3Y",
    "4A": "4A", "4B": "4B", "4Y": "4Y",
    "Vcc": "Vcc", "GND": "GND",
}
_FLIP_FLOP_D_REAL_PINS: dict[str, str] = {
    "1D": "1D", "1CP": "1CP", "1RD": "1RD", "1SD": "1SD",
    "1Q": "1Q", "1NQ": "1NQ",
    "2D": "2D", "2CP": "2CP", "2RD": "2RD", "2SD": "2SD",
    "2Q": "2Q", "2NQ": "2NQ",
    "Vcc": "Vcc", "GND": "GND",
}
# 555 Timer (8 pines, DIP): los nombres del catalogo son los de la fixture
# (CTRL, Reset, OUT, THR, GND, DIS, TRIG, Vcc). Va libre como los integrados.
_TIMER_555_REAL_PINS: dict[str, str] = {
    "CTRL": "CTRL", "Reset": "Reset", "OUT": "OUT", "THR": "THR",
    "GND": "GND", "DIS": "DIS", "TRIG": "TRIG", "Vcc": "Vcc",
}
# Capacitor (2 terminales). Va libre junto al 555: sus patas se cablean
# directo y no hace falta conocer el paso de huecos de la placa.
_CAPACITOR_REAL_PINS: dict[str, str] = {"1": "1", "2": "2"}
# 74HC93 (14 pines): contador binario de 4 bits con dos resets (MR1/MR2,
# activos en alto) y dos relojes (CP0 y CP1, ambos por flanco de bajada).
_BINARY_COUNTER_REAL_PINS: dict[str, str] = {
    "CP0": "CP0", "CP1": "CP1", "MR1": "MR1", "MR2": "MR2",
    "Q0": "Q0", "Q1": "Q1", "Q2": "Q2", "Q3": "Q3",
    "Vcc": "Vcc", "GND": "GND",
}
# 74HC4017 (16 pines): contador Johnson de 10 salidas one-hot. CP0 sube,
# CP1n habilita en bajo y MR resetea en alto. Q5-9n es el acarreo.
# Relay SPDT: dos polos con contacto propio. COIL1/COIL2 excitan la bobina;
# COM1-R1 es el contacto normalmente abierto y COM2-R2 el normalmente
# cerrado (medido en vivo en bDUH17ymla2: con la bobina en alto enciende
# la bombilla del polo 1, con la bobina en bajo la del polo 2).
_RELAY_REAL_PINS: dict[str, str] = {
    "COIL1": "COIL1", "COIL2": "COIL2",
    "COM1": "COM1", "R1": "R1",
    "COM2": "COM2", "R2": "R2",
}
# Bombilla: dos terminales sin polaridad, se cablea directo.
_LIGHT_BULB_REAL_PINS: dict[str, str] = {"1": "1", "2": "2"}
# PIR: modulo libre de 3 pines; el puente los resuelve por nombre de inspect.
_PIR_REAL_PINS: dict[str, str] = {"out": "out", "vcc": "vcc", "gnd": "gnd"}
# Servo libre (``"free_parts"``): mismos nombres que usa el montaje en
# placa, verificados en vivo en servo-potenciometro y parking.
_SERVO_REAL_PINS: dict[str, str] = {
    "gnd": "Ground", "vcc": "Power", "signal": "Signal",
}
# Keypad 4x4: matriz de 4 filas por 4 columnas, sin alimentacion. Los
# nombres de inspect (row1..row4, column1..column4) son los que acepta el
# puente; el guardado los etiqueta "Row 1".."Column 4" (ver breadboard_nets).
_KEYPAD_REAL_PINS: dict[str, str] = {
    **{f"row{i}": f"row{i}" for i in range(1, 5)},
    **{f"column{i}": f"column{i}" for i in range(1, 5)},
}

_DECADE_COUNTER_REAL_PINS: dict[str, str] = {
    "CP0": "CP0", "CP1n": "CP1n", "MR": "MR",
    "Q0": "Q0", "Q1": "Q1", "Q2": "Q2", "Q3": "Q3", "Q4": "Q4",
    "Q5": "Q5", "Q6": "Q6", "Q7": "Q7", "Q8": "Q8", "Q9": "Q9",
    "Q5-9n": "Q5-9n", "Vcc": "Vcc", "GND": "GND",
}
# Pines de las partes que van libres y se cablean a su terminal real (sin
# geometria de huecos). Incluye integrados logicos y actuadores que no se
# montan en la placa.
_FREE_PART_PINS: dict[str, dict[str, str]] = {
    "relay-spdt": _RELAY_REAL_PINS,
    "light-bulb": _LIGHT_BULB_REAL_PINS,
    "pir-sensor": _PIR_REAL_PINS,
    "keypad-4x4": _KEYPAD_REAL_PINS,
    "servo": _SERVO_REAL_PINS,
    "xor-gate": _XOR_REAL_PINS,
    "nand-gate": _NAND_REAL_PINS,
    "flip-flop-d": _FLIP_FLOP_D_REAL_PINS,
    "timer-555": _TIMER_555_REAL_PINS,
    "capacitor": _CAPACITOR_REAL_PINS,
    "binary-counter": _BINARY_COUNTER_REAL_PINS,
    "decade-counter": _DECADE_COUNTER_REAL_PINS,
}

_HOLE_RE = re.compile(r"([0-9]+)([a-j])")

_POWER_ENDPOINTS = frozenset({"uno.5V", "uno.3V3", "uno.VIN"})
_RAIL_POWER_RE = re.compile(r"[TB]\+(?:[1-9]|[12][0-9]|30)?")
_RAIL_GROUND_RE = re.compile(r"[TB]-(?:[1-9]|[12][0-9]|30)?")
_SIGNAL_PALETTE = (
    "blue", "green", "orange", "yellow", "purple", "turquoise", "pink", "brown",
)


def _wire_group(first: str, second: str) -> int:
    endpoints = (first, second)
    if any(
        e in _POWER_ENDPOINTS
        or _RAIL_POWER_RE.fullmatch(e)
        or e.endswith(".+")  # terminal positivo de bateria libre (bat1.+)
        for e in endpoints
    ):
        return 0
    if any(
        e.startswith("uno.GND")
        or _RAIL_GROUND_RE.fullmatch(e)
        or e.endswith(".-")  # terminal negativo de bateria libre (bat1.-)
        for e in endpoints
    ):
        return 1
    return 2


# ---------------------------------------------------------------- rieles
# La protoboard tiene dos pares de rieles de alimentacion: arriba (T+/T-) y
# abajo (B+/B-). El puente acepta "T+5" como extremo y el verificador los
# lee como un nodo unico por riel (derive_nets los agrupa por letra), asi
# que un cable del Uno al riel y una bajada corta por terminal sustituye a
# una tirada larga por cada tap.
_RAIL_TOP_POWER = "T+"
_RAIL_BOTTOM_POWER = "B+"
_RAIL_TOP_GROUND = "T-"
_RAIL_BOTTOM_GROUND = "B-"
# Los dos rieles del mismo tipo se puentean en el borde derecho, donde no
# hay cuerpos de componentes.
_RAIL_BRIDGE_COLUMN = 30
_UPPER_ROWS = frozenset("fghij")
# Geometria de la placa en el puente: hueco de la columna c en
# x = 725 + 10*(c-1) (ORIGIN.x - 145 + 10*(c-1)).
_BOARD_FIRST_COLUMN_X = 725
_BOARD_COLUMN_PITCH = 10
_MAX_RAIL_COLUMN = 30


def _net_kind(endpoints):
    """'power', 'ground' o None: una net de senal nunca va por riel."""
    if any(e in _POWER_ENDPOINTS for e in endpoints):
        return "power"
    if any(e.startswith("uno.GND") for e in endpoints):
        return "ground"
    return None


def _rail_kinds(nets):
    """Tipos de riel que usa el circuito, decidido a nivel de circuito.

    La topologia por defecto es la estrella desde el pin del Uno: un mazo
    de cables paralelos por net, verificada en todo el benchmark. El riel
    es opt-in (``"wiring": "rails"`` en la fixture) porque cambia el
    cableado de un circuito ya verificado.

    Un tipo va por riel cuando en el circuito hay **varias tiradas** de ese
    tipo: o aparece en dos o mas nets (tres nets de GND en el faro), o su
    net tiene tres o mas extremos (un unico 5V que alimenta LCD, servo y
    resistencia). Con una sola tirada de dos extremos el riel solo agrega
    cables (tap + alimentacion + puente) sin quitar ningun cruce.
    """
    nets_by_kind = {}
    widest = {}
    for endpoints in nets:
        kind = _net_kind(endpoints)
        if kind is None:
            continue
        nets_by_kind[kind] = nets_by_kind.get(kind, 0) + 1
        widest[kind] = max(widest.get(kind, 0), len(endpoints))
    return {
        kind
        for kind, count in nets_by_kind.items()
        if count >= 2 or widest[kind] >= 3
    }


def _rail_tap(endpoint, top, bottom, placements):
    """Riel y columna donde baja este extremo (misma columna: vertical)."""
    if endpoint.startswith("uno."):
        # El Uno esta a la izquierda de la placa: columna 1 del riel de
        # arriba, un tramo corto y ruteado por el puente.
        return top, 1
    match = _HOLE_RE.fullmatch(endpoint)
    if match is not None:
        column, row = int(match.group(1)), match.group(2)
        return (top if row in _UPPER_ROWS else bottom), column
    ref = endpoint.split(".", 1)[0]
    placement = placements.get(ref)
    if placement is not None and "free" in placement:
        # Las partes libres bajan al riel en la columna mas cercana a su x
        # para que la bajada no cruce el lienzo. Las que viven encima de la
        # placa (y < 0: display, teclado, integrados) van al riel de arriba;
        # las que viven a la altura de la placa o debajo (servo, motor)
        # bajan al de abajo en vez de trepar por encima de todo.
        free = placement["free"]
        column = round((free["x"] - _BOARD_FIRST_COLUMN_X) / _BOARD_COLUMN_PITCH) + 1
        # La ultima columna esta reservada al puente de rieles: pedirla haria
        # que el asignador diera la vuelta y bajara el servo en la columna 1,
        # al otro extremo de la placa.
        column = min(max(column, 1), _MAX_RAIL_COLUMN - 1)
        rail = bottom if free.get("y", 0) > 0 else top
        return rail, column
    return top, 1


def _rail_rails(kind):
    if kind == "power":
        return _RAIL_TOP_POWER, _RAIL_BOTTOM_POWER
    return _RAIL_TOP_GROUND, _RAIL_BOTTOM_GROUND


def _rail_wires(taps, kind, uno_endpoint, placements):
    """Cablea todos los taps de un tipo: un cable por terminal, uno del Uno
    al riel y, si se usan los dos rieles, el puente del borde.

    Se decide por circuito (no por net) porque todos los taps comparten el
    mismo nodo: repetir el cable del Uno al riel una vez por net dibujaria
    tres cables encima del mismo punto. Cada tap usa una columna libre del
    riel: dos cables al mismo hueco se ven como uno solo y el puente no
    garantiza aceptar dos terminales en el mismo punto.
    """
    top, bottom = _rail_rails(kind)
    pairs = []
    sides = set()
    seen = set()
    used = {}  # riel -> columnas ocupadas

    def _libre(side, proposed):
        """Columna libre mas cercana a la propuesta, buscando a los lados.

        Buscar solo hacia la derecha y dar la vuelta al llegar al final
        mandaba los taps de un LCD a la columna 2: el cable cruzaba todo el
        riel en vez de bajar junto a su parte. Se prueba proposed, +1, -1,
        +2, -2... y la ultima columna queda reservada al puente de rieles.
        """
        ocupadas = used.setdefault(side, set())
        for offset in range(_MAX_RAIL_COLUMN):
            for column in (proposed + offset, proposed - offset):
                if not 1 <= column < _RAIL_BRIDGE_COLUMN:
                    continue
                if column in ocupadas:
                    continue
                ocupadas.add(column)
                return column
        raise BuildError("no queda columna libre en el riel")

    feed_column = _libre(top, 1) if uno_endpoint is not None else None
    # Orden determinista: la columna de cada tap no puede depender del orden
    # en que la fixture declara sus nets.
    for endpoint in sorted(set(taps)):
        side, proposed = _rail_tap(endpoint, top, bottom, placements)
        column = _libre(side, proposed)
        pair = (endpoint, f"{side}{column}")
        if pair in seen:
            continue
        seen.add(pair)
        pairs.append(pair)
        sides.add(side)
    if uno_endpoint is not None:
        sides.add(top)
        pairs.append((uno_endpoint, f"{top}{feed_column}"))
    if len(sides) > 1:
        pairs.append(
            (f"{top}{_RAIL_BRIDGE_COLUMN}", f"{bottom}{_RAIL_BRIDGE_COLUMN}")
        )
    return pairs


def _star_pairs(endpoints, free_refs=()):
    """Empareja una net en estrella desde su hub.

    El puente solo rutea por carriles los cables que tocan un pin del Uno o
    un terminal de una parte libre; un cable hueco-hueco sale recto y cruza
    en diagonal por encima de los cuerpos. Por eso toda la net de 3+ extremos
    cuelga del mismo extremo en vez de encadenarse: el primer pin del Uno
    si esta en la net, si no el terminal de una parte libre (es lo unico que
    el puente rutea), y si tampoco el primero declarado.
    """
    # Las nets de 2 extremos se dejan tal cual (un cable, sin cadena que
    # romper): asi se conserva la orientacion declarada en la fixture.
    if len(endpoints) < 3:
        return [tuple(endpoints)] if len(endpoints) == 2 else []
    free_refs = set(free_refs)
    hub = next(
        (endpoint for endpoint in endpoints if endpoint.startswith("uno.")),
        next(
            (
                endpoint
                for endpoint in endpoints
                if endpoint.split(".", 1)[0] in free_refs
            ),
            endpoints[0],
        ),
    )
    pairs = []
    seen = {hub}
    for endpoint in endpoints:
        if endpoint in seen:
            continue
        seen.add(endpoint)
        pairs.append((hub, endpoint))
    return pairs


def _ordered_colored_wires(pairs) -> list[dict[str, str]]:
    grouped: dict[int, list[tuple[str, str]]] = {0: [], 1: [], 2: []}
    for first, second in pairs:
        grouped[_wire_group(first, second)].append((first, second))
    wires = []
    signal_index = 0
    for group in (0, 1, 2):
        for first, second in sorted(grouped[group], key=lambda wire: wire[0]):
            if group == 0:
                color = "red"
            elif group == 1:
                color = "black"
            else:
                color = _SIGNAL_PALETTE[signal_index % len(_SIGNAL_PALETTE)]
                signal_index += 1
            wires.append({"from": first, "to": second, "color": color})
    return wires


def _shift_hole(hole: str, columns: int, endpoint: str) -> str:
    match = _HOLE_RE.fullmatch(hole)
    if match is None:
        raise BuildError(f"hueco de layout invalido {hole!r} para {endpoint!r}")
    column = int(match.group(1)) + columns
    if not 1 <= column <= 30:
        raise BuildError(
            f"hueco derivado fuera de la protoboard para {endpoint!r}: "
            f"{column}{match.group(2)}"
        )
    return f"{column}{match.group(2)}"


def _translate_endpoint(endpoint, placements, type_by_ref) -> str:
    if not isinstance(endpoint, str) or "." not in endpoint:
        raise BuildError(f"extremo de net invalido: {endpoint!r}")
    ref, pin = endpoint.split(".", 1)
    if ref == "uno":
        return endpoint
    placement = placements.get(ref)
    if placement is None:
        raise BuildError(f"extremo sin placement: {endpoint!r}")
    ctype = type_by_ref.get(ref)
    if ctype == "dc-motor":
        terminal = _MOTOR_TERMINALS.get(pin)
        if terminal is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return f"{ref}.{terminal}"
    if ctype == "battery-9v":
        terminal = _BATTERY_TERMINALS.get(pin)
        if terminal is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return f"{ref}.{terminal}"
    if ctype == "lcd-16x2" and "free" in placement:
        # Modulo libre: el cable termina en el terminal real del display,
        # no en un hueco. Solo se valida el pin (y su nombre real).
        terminal = _LCD_REAL_PINS.get(pin)
        if terminal is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return f"{ref}.{terminal}"
    if ctype == "seven-segment" and "free" in placement:
        terminal = _SEVEN_SEG_REAL_PINS.get(pin)
        if terminal is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return f"{ref}.{terminal}"
    if ctype == "shift-register" and "free" in placement:
        terminal = _SHIFT_REGISTER_REAL_PINS.get(pin)
        if terminal is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return f"{ref}.{terminal}"
    logic_pins = _FREE_PART_PINS.get(ctype)
    if logic_pins is not None and "free" in placement:
        terminal = logic_pins.get(pin)
        if terminal is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return f"{ref}.{terminal}"
    at = placement["at"]
    # Geometria derivada de la receta de layout (ver layout.plan_layout):
    if ctype == "l293d":
        holes = (
            _L293D_PIN_HOLES_180
            if placement.get("angle") == 180
            else _L293D_PIN_HOLES
        )
        hole_spec = holes.get(pin)
        if hole_spec is not None:
            row, offset = hole_spec
            match = _HOLE_RE.fullmatch(at)
            if match is None:
                raise BuildError(
                    f"hueco de layout invalido {at!r} para {endpoint!r}"
                )
            column = int(match.group(1)) + offset
            if not 1 <= column <= 30:
                raise BuildError(
                    f"hueco derivado fuera de la protoboard para "
                    f"{endpoint!r}: {column}{row}"
                )
            return f"{column}{row}"
    elif ctype == "diode":
        if pin == "anode":
            return at
        if pin == "cathode":
            return _shift_hole(at, -4, endpoint)
    elif ctype == "led":
        if pin == "anode":
            return at
        if pin == "cathode":
            return _shift_hole(at, 1, endpoint)
    elif ctype == "resistor":
        if pin == "1":
            return at
        if pin == "2":
            return _shift_hole(at, 4, endpoint)
    elif ctype == "buzzer":
        # Geometria verificada en vivo: ancla "+" (angle 0) y "-" a +5.
        if placement.get("pin") != _BUZZER_ANCHOR:
            raise BuildError(
                f"ancla inesperada para {endpoint!r} (type {ctype!r}): "
                f"{placement.get('pin')!r} (se esperaba {_BUZZER_ANCHOR!r})"
            )
        if pin == "positive":
            return at
        if pin == "negative":
            return _shift_hole(at, _BUZZER_NEGATIVE_OFFSET, endpoint)
        raise BuildError(
            f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
        )
    elif ctype == "photoresistor":
        # Geometria verificada en vivo: terminal-1 en el ancla y
        # terminal-2 a +1 columna, misma fila.
        if placement.get("pin") != _PHOTORESISTOR_ANCHOR:
            raise BuildError(
                f"ancla inesperada para {endpoint!r} (type {ctype!r}): "
                f"{placement.get('pin')!r} "
                f"(se esperaba {_PHOTORESISTOR_ANCHOR!r})"
            )
        if pin == "1":
            return at
        if pin == "2":
            return _shift_hole(at, _PHOTORESISTOR_SECOND_OFFSET, endpoint)
        raise BuildError(
            f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
        )
    elif ctype == "lcd-16x2":
        # Compatibilidad con fixtures/layouts viejos: si el placement trae
        # `at` (LCD montado en la placa), 16 terminales en una fila con
        # ancla "GND" en el `at` y el resto a +1..+15 columnas (angle 0).
        if placement.get("pin") != _LCD_ANCHOR:
            raise BuildError(
                f"ancla inesperada para {endpoint!r} (type {ctype!r}): "
                f"{placement.get('pin')!r} (se esperaba {_LCD_ANCHOR!r})"
            )
        offset = _LCD_PIN_OFFSETS.get(pin)
        if offset is None:
            raise BuildError(
                f"pin sin terminal conocido: {endpoint!r} (type {ctype!r})"
            )
        return at if offset == 0 else _shift_hole(at, offset, endpoint)
    elif ctype in _LINEAR_PIN_PINS:
        for index, (fixture_pin, _real_pin) in enumerate(_LINEAR_PIN_PINS[ctype]):
            if pin == fixture_pin:
                return at if index == 0 else _shift_hole(at, index, endpoint)
    elif ctype == "pushbutton":
        # Geometria verificada en vivo (circuito bWmMIRN5dwi): el boton
        # se coloca con pin "1" en <c>f; sus columnas utiles son la del
        # ancla <c> y la <c+2>. En la fixture, btn.1 es el lado de la
        # senal y btn.2 el de tierra, pero en el circuito real que
        # funciono la senal entro por <c+2> y la tierra por <c>. La fila
        # j es un hueco libre de la misma columna en la mitad superior;
        # cualquier hueco de esa columna conecta con el terminal.
        if pin not in ("1", "2"):
            raise BuildError(
                f"geometria de pin de pushbutton desconocida: {endpoint!r} "
                f"(solo se conocen los pines '1' y '2' en {at})"
            )
        match = _HOLE_RE.fullmatch(at)
        if match is None:
            raise BuildError(
                f"hueco de layout invalido {at!r} para {endpoint!r}"
            )
        column = int(match.group(1)) + (2 if pin == "1" else 0)
        if not 1 <= column <= 30:
            raise BuildError(
                f"hueco derivado fuera de la protoboard para "
                f"{endpoint!r}: {column}j"
            )
        return f"{column}j"
    else:
        raise BuildError(
            f"geometria de pines desconocida para {endpoint!r} "
            f"(type {ctype!r} sin receta de huecos)"
        )
    raise BuildError(f"pin sin hueco conocido: {endpoint!r} (type {ctype!r})")


def fixture_to_model_call(fixture: dict, code: str | None = None) -> dict:
    """Convierte una fixture en {"parts", "wires", "code"} para el puente.

    Lanza BuildError si algun componente queda sin layout (no se construye
    a medias), si un type colocado no tiene DID conocido, o si una net usa
    un pin cuya geometria de huecos se desconoce.
    """
    try:
        layout = plan_layout(fixture)
    except LayoutError as exc:
        raise BuildError(str(exc)) from exc

    unplaced = layout["unplaced"]
    if unplaced:
        raise BuildError(
            "sin layout para: " + ", ".join(str(ref) for ref in unplaced)
        )

    placements = layout["placements"]
    type_by_ref = {c["ref"]: c["type"] for c in fixture["components"]}

    parts = []
    for ref, placement in placements.items():
        ctype = type_by_ref.get(ref)
        if ctype not in _TYPE_BY_SLUG and ctype not in _BUILDER_ONLY_TYPES:
            raise BuildError(f"type sin nombre conocido para ref {ref!r}: {ctype!r}")
        did = DID_BY_TYPE.get(ctype)
        if did is None:
            raise BuildError(
                f"type sin DID conocido para ref {ref!r}: {ctype!r}"
            )
        if "free" in placement:
            # Modulos libres (motor DC, bateria 9V, LCD 16x2): sin hueco,
            # sin `pin` de ancla; el puente los coloca por coordenadas.
            # El puente lee la rotacion de `part.angle` (no de `free`), y
            # `spec.validate_spec` exige `free` == {x, y}: el angulo del
            # placement sale a nivel de part.
            free = dict(placement["free"])
            angle = free.pop("angle", None)
            part = {"ref": ref, "did": did, "free": free}
            if angle is not None:
                part["angle"] = angle
            parts.append(part)
            continue
        part_pin = placement["pin"]
        real_by_fixture = None
        if ctype in _LINEAR_PIN_PINS:
            real_by_fixture = dict(_LINEAR_PIN_PINS[ctype])
        elif ctype == "l293d":
            real_by_fixture = _L293D_REAL_BY_FIXTURE
        elif ctype == "buzzer":
            real_by_fixture = _BUZZER_REAL_PINS
        elif ctype == "photoresistor":
            real_by_fixture = _PHOTORESISTOR_REAL_PINS
        elif ctype == "lcd-16x2":
            real_by_fixture = _LCD_REAL_PINS
        if real_by_fixture is not None:
            if part_pin not in real_by_fixture:
                raise BuildError(
                    f"pin ancla sin nombre real para ref {ref!r}: "
                    f"{part_pin!r} (type {ctype!r})"
                )
            part_pin = real_by_fixture[part_pin]
        parts.append(
            {
                "ref": ref,
                "did": did,
                "at": placement["at"],
                "pin": part_pin,
                "angle": placement["angle"],
            }
        )

    free_refs = {
        ref for ref, placement in placements.items() if "free" in placement
    }
    translated_nets = []
    for net in fixture.get("nets") or []:
        if not isinstance(net, (list, tuple)) or len(net) < 2:
            raise BuildError(f"net invalida (se esperaban 2+ extremos): {net!r}")
        translated_nets.append(
            [
                _translate_endpoint(endpoint, placements, type_by_ref)
                for endpoint in net
            ]
        )
    wiring = fixture.get("wiring")
    if wiring not in (None, "rails"):
        raise BuildError(
            f"wiring desconocido: {wiring!r} (esperado None o 'rails')"
        )
    rail_kinds = _rail_kinds(translated_nets) if wiring == "rails" else set()
    rail_taps = {kind: [] for kind in rail_kinds}
    rail_uno = {}
    pairs = []
    for translated in translated_nets:
        kind = _net_kind(translated)
        if kind is not None and kind in rail_kinds:
            for endpoint in translated:
                if endpoint.startswith("uno."):
                    rail_uno[kind] = endpoint
                else:
                    rail_taps[kind].append(endpoint)
            continue
        pairs.extend(_star_pairs(translated, free_refs))
    for kind in sorted(rail_kinds):
        pairs.extend(
            _rail_wires(rail_taps[kind], kind, rail_uno.get(kind), placements)
        )

    return {"parts": parts, "wires": _ordered_colored_wires(pairs), "code": code}


def build_circuit(fixture, code, call_tool) -> dict:
    """Construye el circuito en el puente y luego lo inspecciona.

    El circuito ya debe estar abierto: no se hace open/create. Si el paso
    del modelo devuelve ``success: false`` en su JSON, se registra y se
    devuelve igual (no se lanza).
    """
    model_call = fixture_to_model_call(fixture, code)
    steps = [
        ProbeStep(tool="tinkercad_build_circuit_model", arguments=model_call),
        ProbeStep(tool="tinkercad_inspect_circuit", arguments={}),
    ]
    records = run_steps(steps, call_tool)

    raw = records[0].output if records else ""
    try:
        model_result = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        model_result = raw
    return {"model_result": model_result, "records": records}
