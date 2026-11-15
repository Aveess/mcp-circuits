"""Netlist del decodificador 0-7 hecho con compuertas (punto 4 del taller).

El taller pide construir directamente con compuertas las siete funciones
combinacionales de Q2 Q1 Q0 que controlan los segmentos a..g, y expresa la
tabla en logica positiva (1 = segmento encendido). Este modulo guarda ese
netlist como dato unico: de aqui salen el cableado de la fixture, la tabla de
verdad del reporte y la comprobacion que hace el sketch en la simulacion.

Dos netlists, misma tabla:

- **v1 (``GATES``/``XOR_GATES``)**: 35 NAND de 2 entradas en 8 x 74HC00 y 3 XOR
  en 1 x 74HC86. La NAND es universal y con ella se hace AND y OR; es lo que se
  construyo y se verifico primero.
- **v2 (``GATES_V2``/``XOR_GATES_V2``)**: las expresiones tal como se escriben,
  con AND/OR/NOT/XOR reales: 6 NOT (1 x 74HC04), 3 XOR (1 x 74HC86), 5 AND
  (2 x 74HC08) y 9 OR (3 x 74HC32). Siete integrados y el diseno se lee como el
  enunciado. Las ranuras sobrantes van con las entradas a GND (una entrada CMOS
  nunca flota).

Expresiones del taller (verificadas contra su tabla, 8/8 filas)::

    a = Q1 + NOT(Q2 XOR Q0)
    b = NOT Q2 + NOT(Q1 XOR Q0)
    c = Q2 + NOT Q1 + Q0
    d = e + Q0(Q2 XOR Q1)
    e = NOT Q0 (Q1 + NOT Q2)
    f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)
    g = (Q2 XOR Q1) + Q1 NOT Q0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

__all__ = [
    "Gate",
    "GATES",
    "XOR_GATES",
    "GATES_V2",
    "XOR_GATES_V2",
    "SEGMENT_OUTPUT",
    "SEGMENT_OUTPUT_V2",
    "SEGMENTS",
    "LIT_TABLE",
    "evaluate",
    "evaluate_v2",
    "segment_mask",
    "signal_nets",
    "signal_nets_v2",
    "chip_type",
]

SEGMENTS = "abcdefg"


@dataclass(frozen=True)
class Gate:
    chip: str
    slot: int
    out: str
    a: str
    b: str
    kind: str = "nand"  # "nand" | "xor" | "and" | "or" | "not"


# Orden topologico: cada compuerta solo usa senales ya producidas arriba
# (mas las base Q0/Q1/Q2/GND/Vcc). Las tres primeras son los inversores de
# Q que las expresiones del taller necesitan.
GATES: tuple[Gate, ...] = (
    # Inversores de Q con NAND(x, x).
    Gate("u1", 1, "nQ0", "Q0", "Q0"),
    Gate("u1", 2, "nQ1", "Q1", "Q1"),
    Gate("u1", 3, "nQ2", "Q2", "Q2"),
    # a = Q1 + NOT(Q2 XOR Q0)
    Gate("u1", 4, "fa", "nQ1", "X20"),
    # b = NOT Q2 + NOT(Q1 XOR Q0)
    Gate("u2", 1, "fb", "Q2", "X10"),
    # c = Q2 + NOT Q1 + Q0  ->  t = NOT(Q1 NOT Q0); y = NOT t; c = NOT(nQ2 y)
    Gate("u2", 2, "t", "Q1", "nQ0"),
    Gate("u2", 3, "y", "t", "t"),
    Gate("u2", 4, "fc", "nQ2", "y"),
    # e = NOT Q0 (Q1 + NOT Q2)  ->  p = NOT(NOT Q1 Q2); q = NOT(NOT Q0 p); e = NOT q
    Gate("u3", 1, "p", "nQ1", "Q2"),
    Gate("u3", 2, "q", "nQ0", "p"),
    Gate("u3", 3, "fe", "q", "q"),
    # d = e + Q0(Q2 XOR Q1)  ->  v = NOT(Q0 X21); d = NOT(q v)
    Gate("u3", 4, "v", "Q0", "X21"),
    Gate("u4", 1, "fd", "q", "v"),
    # f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)
    Gate("u4", 2, "t2", "nQ1", "nQ0"),
    Gate("u4", 3, "p2", "Q1", "Q0"),
    Gate("u4", 4, "q2", "Q2", "p2"),
    Gate("u5", 1, "ff", "t2", "q2"),
    # g = (Q2 XOR Q1) + Q1 NOT Q0  ->  wx = NOT X21; g = NOT(wx t)
    Gate("u5", 2, "wx", "X21", "X21"),
    Gate("u5", 3, "fg", "wx", "t"),
    # RESET activo en alto (lo maneja el Uno) -> R de los JK activo en bajo.
    Gate("u5", 4, "nR", "RESET", "RESET"),
    # Inversores de cada segmento para el display de anodo comun (LOW = luce).
    Gate("u6", 1, "na", "fa", "fa"),
    Gate("u6", 2, "nb", "fb", "fb"),
    Gate("u6", 3, "nc", "fc", "fc"),
    Gate("u6", 4, "nd", "fd", "fd"),
    Gate("u7", 1, "ne", "fe", "fe"),
    Gate("u7", 2, "nf", "ff", "ff"),
    Gate("u7", 3, "ng", "fg", "fg"),
)

XOR_GATES: tuple[Gate, ...] = (
    Gate("x1", 1, "X20", "Q2", "Q0", kind="xor"),
    Gate("x1", 2, "X10", "Q1", "Q0", kind="xor"),
    Gate("x1", 3, "X21", "Q2", "Q1", kind="xor"),
)

# Salida logica positiva -> compuerta que la entrega antes del inversor.
SEGMENT_OUTPUT: dict[str, str] = {seg: f"f{seg}" for seg in SEGMENTS}


# --- Netlist v2: las expresiones del taller con AND/OR/NOT/XOR reales --------
#
# Inversores primero porque las demas compuertas los consumen; el XOR despues.
# El orden de la tupla no hace falta para evaluar (el evaluador resuelve por
# disponibilidad de senales), pero se lee de arriba abajo como el enunciado.
GATES_V2: tuple[Gate, ...] = (
    # u1: 74HC04, los seis inversores del diseno.
    Gate("u1", 1, "q0n", "Q0", "Q0", kind="not"),
    Gate("u1", 2, "q1n", "Q1", "Q1", kind="not"),
    Gate("u1", 3, "q2n", "Q2", "Q2", kind="not"),
    Gate("u1", 4, "nX20", "X20", "X20", kind="not"),
    Gate("u1", 5, "nX10", "X10", "X10", kind="not"),
    Gate("u1", 6, "nR", "RESET", "RESET", kind="not"),
    # u4: 74HC32 (OR). Las sumas de un solo termino negativo.
    Gate("u4", 1, "e1", "Q1", "q2n", kind="or"),      # e = q0n (Q1 + q2n)
    Gate("u4", 2, "fa", "Q1", "nX20", kind="or"),     # a = Q1 + NOT(Q2 XOR Q0)
    Gate("u4", 3, "fb", "q2n", "nX10", kind="or"),    # b = q2n + NOT(Q1 XOR Q0)
    Gate("u4", 4, "c1", "Q2", "q1n", kind="or"),
    # u5: 74HC32 (OR).
    Gate("u5", 1, "fc", "c1", "Q0", kind="or"),       # c = Q2 + q1n + Q0
    Gate("u5", 2, "f1", "q1n", "q0n", kind="or"),     # f = q1n q0n + Q2 (q1n + q0n)
    Gate("u5", 3, "fd", "fe", "d2", kind="or"),       # d = e + Q0 (Q2 XOR Q1)
    Gate("u5", 4, "ff", "f2", "f3", kind="or"),
    # u6: 74HC32 (OR). Un solo OR: g = (Q2 XOR Q1) + Q1 q0n.
    Gate("u6", 1, "fg", "X21", "g2", kind="or"),
    # u2: 74HC08 (AND).
    Gate("u2", 1, "fe", "q0n", "e1", kind="and"),     # e = q0n (Q1 + q2n)
    Gate("u2", 2, "d2", "Q0", "X21", kind="and"),     # Q0 (Q2 XOR Q1)
    Gate("u2", 3, "f2", "q1n", "q0n", kind="and"),    # q1n q0n
    Gate("u2", 4, "f3", "Q2", "f1", kind="and"),      # Q2 (q1n + q0n)
    # u3: 74HC08 (AND).
    Gate("u3", 1, "g2", "Q1", "q0n", kind="and"),     # Q1 q0n
)

XOR_GATES_V2: tuple[Gate, ...] = (
    Gate("x1", 1, "X20", "Q2", "Q0", kind="xor"),
    Gate("x1", 2, "X10", "Q1", "Q0", kind="xor"),
    Gate("x1", 3, "X21", "Q2", "Q1", kind="xor"),
)

# Salida logica positiva del decodificador v2 (antes de la resistencia del
# segmento). En catodo comun el segmento luce con HIGH, asi que esta es la
# senal que lee el sketch y la que va al display.
SEGMENT_OUTPUT_V2: dict[str, str] = {seg: f"f{seg}" for seg in SEGMENTS}

_CHIP_BY_KIND: dict[str, str] = {
    "nand": "nand-gate",
    "and": "and-gate",
    "or": "or-gate",
    "not": "not-gate",
    "xor": "xor-gate",
}


def chip_type(kind: str) -> str:
    """Familia de integrado que implementa una compuerta (``"and"`` -> ``"and-gate"``)."""
    return _CHIP_BY_KIND[kind]


def _eval(gates, xor_gates, q2: int, q1: int, q0: int, reset: int) -> dict[str, int]:
    values: dict[str, int] = {
        "Q0": int(bool(q0)),
        "Q1": int(bool(q1)),
        "Q2": int(bool(q2)),
        "RESET": int(bool(reset)),
        "GND": 0,
        "Vcc": 1,
    }
    pending = list(gates) + list(xor_gates)
    while pending:
        resolved = False
        for gate in pending[:]:
            if gate.a not in values or gate.b not in values:
                continue
            x, y = values[gate.a], values[gate.b]
            if gate.kind == "xor":
                values[gate.out] = x ^ y
            elif gate.kind == "and":
                values[gate.out] = 1 if (x and y) else 0
            elif gate.kind == "or":
                values[gate.out] = 1 if (x or y) else 0
            elif gate.kind == "not":
                values[gate.out] = 0 if x else 1
            else:
                values[gate.out] = 0 if (x and y) else 1
            pending.remove(gate)
            resolved = True
        if not resolved:
            missing = sorted({gate.a for gate in pending} | {gate.b for gate in pending})
            raise ValueError(f"senales sin productor en el netlist: {missing}")
    return values


def evaluate(q2: int, q1: int, q0: int, reset: int = 0) -> dict[str, int]:
    """Evalua el netlist v1 para un estado Q2 Q1 Q0 (0/1).

    ``reset`` es la entrada del taller (activa en alto); por defecto queda
    inactiva, que es como se evalua la tabla de segmentos.
    """
    return _eval(GATES, XOR_GATES, q2, q1, q0, reset)


def evaluate_v2(q2: int, q1: int, q0: int, reset: int = 0) -> dict[str, int]:
    """Evalua el netlist v2 y devuelve ademas ``mask`` (a..g, 1 = encendido)."""
    values = _eval(GATES_V2, XOR_GATES_V2, q2, q1, q0, reset)
    mask = 0
    for index, segment in enumerate(SEGMENTS):
        if values[SEGMENT_OUTPUT_V2[segment]]:
            mask |= 1 << index
    values["mask"] = mask
    return values


def segment_mask(q2: int, q1: int, q0: int) -> int:
    """Mascara a..g (bit 0 = a) con 1 = segmento encendido."""
    values = evaluate(q2, q1, q0)
    mask = 0
    for index, segment in enumerate(SEGMENTS):
        if values[SEGMENT_OUTPUT[segment]]:
            mask |= 1 << index
    return mask


# Tabla del taller, derivada del netlist (no copiada a mano: si el netlist
# cambia, esta tabla cambia con el y el test lo nota).
LIT_TABLE: tuple[int, ...] = tuple(
    segment_mask((value >> 2) & 1, (value >> 1) & 1, value & 1)
    for value in range(8)
)


def _node(gate: Gate, side: str) -> str:
    return f"{gate.chip}.{gate.slot}{side}"


def signal_nets(producers: Mapping[str, str]) -> list[list[str]]:
    """Una net por senal: nodo productor primero, luego cada consumidor.

    ``producers`` mapea las senales base (Q0, Q1, Q2, GND, Vcc) a su nodo de
    origen en el circuito; las salidas de compuerta salen del propio netlist.
    Las senales que nadie consume (na..ng, nR) no producen net: la fixture las
    cablea a su destino a mano.
    """
    return _signal_nets(GATES, XOR_GATES, producers)


def signal_nets_v2(producers: Mapping[str, str]) -> list[list[str]]:
    """Igual que :func:`signal_nets` sobre el netlist v2."""
    return _signal_nets(GATES_V2, XOR_GATES_V2, producers)


def _inputs(gate: Gate) -> list[tuple[str, str]]:
    """Lados realmente cableados de una compuerta (el inversor tiene uno)."""
    if gate.kind == "not":
        return [("A", gate.a)]
    return [("A", gate.a), ("B", gate.b)]


def _signal_nets(gates, xor_gates, producers: Mapping[str, str]) -> list[list[str]]:
    source: dict[str, str] = dict(producers)
    for gate in gates + xor_gates:
        source[gate.out] = f"{gate.chip}.{gate.slot}Y"

    consumers: dict[str, list[str]] = {}
    for gate in gates + xor_gates:
        for side, signal in _inputs(gate):
            if signal not in source:
                raise ValueError(f"senal sin productor: {signal}")
            consumers.setdefault(signal, []).append(_node(gate, side))

    nets: list[list[str]] = []
    for signal, nodes in consumers.items():
        nets.append([source[signal]] + nodes)
    return nets
