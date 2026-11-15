"""Decodificador v2: las mismas expresiones del taller, ahora con AND/OR/NOT/XOR.

La v1 las construyo con NAND (universal) porque el catalogo que se probo entonces
solo ofrecia eso. La v2 usa las compuertas del taller tal como se escriben, para
que el diseno se lea como el enunciado: `a = Q1 + NOT(Q2 XOR Q0)` es un OR de
verdad y quien lo mira lo reconoce.

Los chips y las expresiones son de la spec `2026-11-15-layout-v2-design.md`.
"""

from __future__ import annotations

import pytest

from tinkercad_brain.decoder7 import (
    GATES,
    GATES_V2,
    LIT_TABLE,
    SEGMENT_OUTPUT_V2,
    SEGMENTS,
    XOR_GATES,
    XOR_GATES_V2,
    chip_type,
    evaluate_v2,
    signal_nets_v2,
)

# Limite de compuertas por integrado (DIP-14): 4 en las de 2 entradas, 6 en
# el 74HC04.
_LIMITE = {"not-gate": 6, "and-gate": 4, "or-gate": 4, "xor-gate": 4, "nand-gate": 4}

# Los seis chips del decodificador v2, con su familia.
_CHIPS = {
    "u1": "not-gate",   # 74HC04: q0n, q1n, q2n, nX20, nX10, nR
    "u2": "and-gate",   # 74HC08
    "u3": "and-gate",   # 74HC08
    "u4": "or-gate",    # 74HC32
    "u5": "or-gate",    # 74HC32
    "u6": "or-gate",    # 74HC32
    "x1": "xor-gate",   # 74HC86
}


def test_v2_da_la_misma_tabla_que_v1_en_los_ocho_estados():
    for valor in range(8):
        q2, q1, q0 = (valor >> 2) & 1, (valor >> 1) & 1, valor & 1
        assert evaluate_v2(q2, q1, q0)["mask"] == LIT_TABLE[valor], valor


def test_v2_usa_una_familia_por_chip_y_no_pasa_de_su_limite():
    # 4 compuertas de 2 entradas o 6 inversores por DIP-14. La cuenta no es
    # negociable: 6 NOT -> 1 chip; 3 XOR -> 1; 5 AND -> 2; 9 OR -> 3.
    uso: dict[str, int] = {}
    for gate in GATES_V2 + XOR_GATES_V2:
        uso[gate.chip] = uso.get(gate.chip, 0) + 1
        assert chip_type(gate.kind) == _CHIPS[gate.chip], (gate.chip, gate.kind)

    assert set(uso) == set(_CHIPS), uso
    for chip, n in uso.items():
        assert n <= _LIMITE[_CHIPS[chip]], (chip, n)
    assert len(uso) == 7


def test_v2_cubre_las_cuatro_familias_del_enunciado():
    tipos = {chip_type(g.kind) for g in GATES_V2 + XOR_GATES_V2}

    assert tipos == {"not-gate", "and-gate", "or-gate", "xor-gate"}


def test_los_inversores_tienen_una_sola_entrada():
    for gate in GATES_V2:
        if gate.kind == "not":
            assert gate.a == gate.b, gate


def test_v2_no_deja_entradas_de_compuerta_sin_productor():
    nets = signal_nets_v2(
        {"Q0": "ff1.1Q", "Q1": "ff2.1Q", "Q2": "ff2.2Q",
         "GND": "uno.GND1", "Vcc": "uno.5V", "RESET": "uno.D9"}
    )

    assert nets
    # Productor primero, consumidores despues, y ningun nodo repetido: un
    # consumidor que aparezca dos veces significa un cable duplicado.
    for net in nets:
        assert len(net) == len(set(net)), net
        assert len(net) >= 2, net
    productores = {net[0] for net in nets}
    assert len(productores) == len(nets)


def test_cada_entrada_del_netlist_esta_cableada_una_vez():
    nets = signal_nets_v2(
        {"Q0": "Q0", "Q1": "Q1", "Q2": "Q2", "GND": "GND", "Vcc": "Vcc",
         "RESET": "RESET"}
    )
    consumidores = [nodo for net in nets for nodo in net[1:]]
    esperados = []
    for gate in GATES_V2 + XOR_GATES_V2:
        esperados.append(f"{gate.chip}.{gate.slot}A")
        if gate.kind != "not":
            esperados.append(f"{gate.chip}.{gate.slot}B")

    assert sorted(consumidores) == sorted(esperados)


def test_la_salida_de_cada_segmento_existe_en_el_netlist():
    senales = {gate.out for gate in GATES_V2 + XOR_GATES_V2}

    assert set(SEGMENT_OUTPUT_V2) == set(SEGMENTS)
    for salida in SEGMENT_OUTPUT_V2.values():
        assert salida in senales


def test_evaluate_v2_respeta_el_reset_y_lo_entrega_invertido():
    # El JK resetea en bajo: nR es el inversor de la entrada del Uno.
    assert evaluate_v2(0, 0, 0)["nR"] == 1
    assert evaluate_v2(0, 0, 0, reset=1)["nR"] == 0


def test_el_netlist_v1_sigue_intacto():
    # La v1 se construyo y se verifico con esto: no puede cambiar de gratis.
    assert len(GATES) == 27
    assert len(XOR_GATES) == 3
    assert all(g.kind == "nand" for g in GATES)


@pytest.mark.parametrize("kind", ["nand", "and", "or", "not", "xor"])
def test_chip_type_nombra_el_integrado(kind):
    assert chip_type(kind) == f"{kind}-gate"
