"""Netlist del decodificador 0-7 hecho con compuertas (punto 4 del taller).

El taller pide construir directamente con compuertas las siete funciones
combinacionales de Q2 Q1 Q0 que controlan los segmentos a..g, y expresa la
tabla en logica positiva (1 = segmento encendido). Este modulo guarda ese
netlist como dato unico: de aqui salen el cableado de la fixture, la tabla de
verdad del reporte y la comprobacion que hace el sketch en la simulacion.

Reparto fisico: 27 NAND de 2 entradas en 7 x 74HC00 y 3 XOR en 1 x 74HC86.
La ranura 4 del u7 y la del 74HC86 quedan sin usar con entradas a GND (una
entrada CMOS nunca flota).

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
    "SEGMENT_OUTPUT",
    "SEGMENTS",
    "LIT_TABLE",
    "evaluate",
    "segment_mask",
    "signal_nets",
]

SEGMENTS = "abcdefg"


@dataclass(frozen=True)
class Gate:
    chip: str
    slot: int
    out: str
    a: str
    b: str
    kind: str = "nand"  # "nand" | "xor"


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


def evaluate(q2: int, q1: int, q0: int, reset: int = 0) -> dict[str, int]:
    """Evalua el netlist para un estado Q2 Q1 Q0 (0/1).

    ``reset`` es la entrada del taller (activa en alto); por defecto queda
    inactiva, que es como se evalua la tabla de segmentos.
    """
    values: dict[str, int] = {
        "Q0": int(bool(q0)),
        "Q1": int(bool(q1)),
        "Q2": int(bool(q2)),
        "RESET": int(bool(reset)),
        "GND": 0,
        "Vcc": 1,
    }
    pending = list(GATES) + list(XOR_GATES)
    while pending:
        resolved = False
        for gate in pending[:]:
            if gate.a not in values or gate.b not in values:
                continue
            if gate.kind == "xor":
                values[gate.out] = values[gate.a] ^ values[gate.b]
            else:
                values[gate.out] = 0 if (values[gate.a] and values[gate.b]) else 1
            pending.remove(gate)
            resolved = True
        if not resolved:
            missing = sorted({gate.a for gate in pending} | {gate.b for gate in pending})
            raise ValueError(f"senales sin productor en el netlist: {missing}")
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
    source: dict[str, str] = dict(producers)
    for gate in GATES + XOR_GATES:
        source[gate.out] = f"{gate.chip}.{gate.slot}Y"

    consumers: dict[str, list[str]] = {}
    for gate in GATES + XOR_GATES:
        for side, signal in (("A", gate.a), ("B", gate.b)):
            if signal not in source:
                raise ValueError(f"senal sin productor: {signal}")
            consumers.setdefault(signal, []).append(_node(gate, side))

    nets: list[list[str]] = []
    for signal, nodes in consumers.items():
        nets.append([source[signal]] + nodes)
    return nets
