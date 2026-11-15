"""Decodificador 0-7 con compuertas: la tabla del taller es el contrato.

El punto 4 pide construir las siete funciones combinacionales directamente con
compuertas. Este modulo guarda el netlist (que compuerta produce que senal y
quien la consume) y evalua la tabla de verdad, de modo que el cableado de la
fixture y la verificacion del sketch salen del mismo dato.

Expresiones del taller (activas en alto), verificadas contra su tabla:
    a = Q1 + NOT(Q2 XOR Q0)
    b = NOT Q2 + NOT(Q1 XOR Q0)
    c = Q2 + NOT Q1 + Q0
    d = e + Q0(Q2 XOR Q1)
    e = NOT Q0 (Q1 + NOT Q2)
    f = NOT Q1 NOT Q0 + Q2(NOT Q1 + NOT Q0)
    g = (Q2 XOR Q1) + Q1 NOT Q0
"""

from __future__ import annotations

import pytest

from tinkercad_brain.decoder7 import (
    GATES,
    LIT_TABLE,
    SEGMENT_OUTPUT,
    XOR_GATES,
    evaluate,
    segment_mask,
    signal_nets,
)

# Mascara a..g (bit 0 = a) con 1 = segmento encendido, que es la convencion
# del taller. El display real es de anodo comun y el circuito invierte, pero
# la tabla del punto 4 se expresa en logica positiva.
TABLA = {0: 0x3F, 1: 0x06, 2: 0x5B, 3: 0x4F, 4: 0x66,
         5: 0x6D, 6: 0x7D, 7: 0x07}


@pytest.mark.parametrize("valor,mascara", sorted(TABLA.items()))
def test_la_tabla_del_taller_en_las_ocho_filas(valor, mascara):
    q2, q1, q0 = (valor >> 2) & 1, (valor >> 1) & 1, valor & 1
    assert segment_mask(q2, q1, q0) == mascara
    assert LIT_TABLE[valor] == mascara


def test_evaluate_devuelve_la_salida_de_cada_compuerta():
    senales = evaluate(1, 1, 0)  # digito 6
    for segmento, salida in SEGMENT_OUTPUT.items():
        # La compuerta entrega el valor logico positivo del segmento.
        assert senales[salida] == (TABLA[6] >> "abcdefg".index(segmento)) & 1


def test_hay_veintisiete_nand_en_siete_chips_sin_repetir_ranura():
    assert len(GATES) == 27
    assert len(XOR_GATES) == 3
    ocupadas = {(g.chip, g.slot) for g in GATES}
    assert len(ocupadas) == 27
    assert {chip for chip, _ in ocupadas} == {f"u{i}" for i in range(1, 8)}


def test_toda_entrada_tiene_productor():
    producidas = {g.out for g in GATES} | {g.out for g in XOR_GATES}
    base = {"Q0", "Q1", "Q2", "RESET", "GND", "Vcc"}
    for gate in GATES + XOR_GATES:
        for entrada in (gate.a, gate.b):
            assert entrada in producidas or entrada in base, (gate, entrada)


def test_signal_nets_una_net_por_senal_con_el_productor_primero():
    producers = {"Q0": "ff1.1Q", "Q1": "ff2.1Q", "Q2": "ff2.2Q",
                 "RESET": "uno.D9", "GND": "uno.GND1", "Vcc": "uno.5V"}
    nets = signal_nets(producers)
    por_senal = {}
    for net in nets:
        assert len(net) >= 2
        assert len(set(net)) == len(net)
        por_senal.setdefault(net[0], []).append(net)

    # Cada salida de compuerta que alguien consume encabeza su net.
    for gate in GATES + XOR_GATES:
        consumidores = [
            f"{g.chip}.{g.slot}{lado}"
            for g in GATES + XOR_GATES
            for lado, entrada in (("A", g.a), ("B", g.b))
            if entrada == gate.out
        ]
        if not consumidores:
            continue
        net = next(n for n in nets if n[0] == f"{gate.chip}.{gate.slot}Y")
        assert net[1:] == consumidores


def test_los_xor_producen_las_tres_senales_que_pide_el_netlist():
    assert {g.out for g in XOR_GATES} == {"X20", "X10", "X21"}
